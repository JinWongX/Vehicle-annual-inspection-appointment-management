import csv
import io
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models, schemas, auth, crud
from ..database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


def _generate_sticker_code(report: models.InspectionReport) -> str:
    if report.result == "pass" and report.appointment and report.appointment.vehicle:
        plate = report.appointment.vehicle.plate_number
        created_str = report.created_at.strftime("%Y%m%d")
        return f"VIC-{created_str}-{report.id}-{plate}"
    return ""


def _build_report_query(
    db: Session,
    start_date: date,
    end_date: date,
    station_id: Optional[int] = None,
):
    query = (
        db.query(models.InspectionReport)
        .join(models.Appointment)
        .filter(models.Appointment.appointment_date.between(start_date, end_date))
    )
    if station_id is not None:
        query = query.filter(models.Appointment.station_id == station_id)
    return query


@router.post("/", response_model=schemas.InspectionReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report: schemas.InspectionReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("station", "admin")),
):
    appointment = crud.get_appointment_by_id(db, report.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == "station" and appointment.station_id != current_user.station_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    # 已存在报告优先于状态校验：报告一旦生成该预约必然已 completed，
    # 重复录入应优先提示“已存在报告”。
    existing_report = crud.get_report_by_appointment_id(db, report.appointment_id)
    if existing_report:
        raise HTTPException(status_code=400, detail="Report already exists for this appointment")
    if appointment.status != "checking":
        raise HTTPException(
            status_code=400,
            detail="Appointment must be checked in (checking status) before recording results",
        )
    # 创建报告 + 插入检测项 + 预约状态流转 completed 在同一事务内原子完成，
    # 任一步失败整体回滚，避免脏数据。
    db_report = crud.create_inspection_report_and_complete(db, report)
    db_report.sticker_code = _generate_sticker_code(db_report)
    return db_report


@router.get("/", response_model=List[schemas.InspectionReportResponse])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    # 归属过滤下沉到 SQL，避免全量拉取后内存截断导致分页错乱
    if current_user.role == "owner":
        reports = crud.list_reports_by_owner(db, current_user.id, skip=skip, limit=limit)
    elif current_user.role == "station":
        reports = crud.list_reports_by_station(db, current_user.station_id, skip=skip, limit=limit)
    else:
        reports = crud.list_reports(db, skip=skip, limit=limit)
    for r in reports:
        r.sticker_code = _generate_sticker_code(r)
    return reports


@router.get("/statistics", response_model=schemas.InspectionStatisticsResponse)
def get_statistics(
    start_date: date = Query(..., description="统计开始日期"),
    end_date: date = Query(..., description="统计结束日期"),
    station_id: Optional[int] = Query(None, description="检测站 ID"),
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be later than end_date")

    base_query = _build_report_query(db, start_date, end_date, station_id)
    total_count = base_query.count()
    pass_count = base_query.filter(models.InspectionReport.result == "pass").count()
    fail_count = base_query.filter(models.InspectionReport.result == "fail").count()
    retest_count = base_query.filter(models.InspectionReport.result == "retest").count()
    pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0.0

    fail_reasons_rows = (
        db.query(models.InspectionItem.item_name, func.count(models.InspectionItem.id))
        .join(models.InspectionReport)
        .join(models.Appointment)
        .filter(
            models.InspectionItem.result == "fail",
            models.Appointment.appointment_date.between(start_date, end_date),
        )
    )
    if station_id is not None:
        fail_reasons_rows = fail_reasons_rows.filter(models.Appointment.station_id == station_id)
    fail_reasons_rows = fail_reasons_rows.group_by(models.InspectionItem.item_name).all()
    fail_reasons = {name: count for name, count in fail_reasons_rows}

    return schemas.InspectionStatisticsResponse(
        total_count=total_count,
        pass_count=pass_count,
        fail_count=fail_count,
        retest_count=retest_count,
        pass_rate=pass_rate,
        fail_reasons=fail_reasons,
    )


@router.get("/export")
def export_reports(
    format: str = Query(..., pattern="^(excel|csv)$", description="导出格式"),
    station_id: Optional[int] = Query(None, description="检测站 ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be later than end_date")

    reports = _build_report_query(db, start_date, end_date, station_id).all()
    headers = ["车牌", "检测站", "预约日期", "检测结果", "检测项目", "备注"]
    rows = [headers]
    for report in reports:
        plate = report.appointment.vehicle.plate_number
        station_name = report.appointment.station.name
        appointment_date = report.appointment.appointment_date.isoformat()
        result = report.result
        items = ", ".join(f"{item.item_name}({item.result})" for item in report.items)
        comment = report.overall_comment or ""
        rows.append([plate, station_name, appointment_date, result, items, comment])

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        content = output.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=reports.csv"},
        )

    # excel
    wb = Workbook()
    ws = wb.active
    ws.title = "检测报告"
    for row in rows:
        ws.append(row)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reports.xlsx"},
    )


@router.get("/{report_id}", response_model=schemas.InspectionReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    report = crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "owner" and report.appointment.vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == "station" and report.appointment.station_id != current_user.station_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    report.sticker_code = _generate_sticker_code(report)
    return report
