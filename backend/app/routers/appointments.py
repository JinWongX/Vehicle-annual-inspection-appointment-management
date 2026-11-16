from datetime import date, timedelta
import threading

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, auth, crud
from ..database import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])

TIME_SLOTS = ["08:00-10:00", "10:00-12:00", "13:00-15:00", "15:00-17:00"]

# 名额校验与预约创建的临界区锁：
# check-then-act 非原子，并发请求可能同时通过容量检查导致超额预约。
# 单进程部署下使用进程内锁串行化该临界区（多实例部署需改用数据库唯一约束或分布式锁）。
_booking_lock = threading.Lock()


def _slot_capacity(daily_capacity: int) -> int:
    return max(1, daily_capacity // len(TIME_SLOTS))


@router.post("/", response_model=schemas.AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    vehicle = crud.get_vehicle_by_id(db, appointment.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.role == "owner" and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    today = date.today()
    if appointment.appointment_date < today:
        raise HTTPException(status_code=400, detail="Appointment date cannot be in the past")
    if appointment.appointment_date > today + timedelta(days=30):
        raise HTTPException(status_code=400, detail="Appointment date cannot be more than 30 days in the future")
    if appointment.time_slot not in TIME_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid time slot")

    station = crud.get_station_by_id(db, appointment.station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    allowed_types = [
        t.strip().lower()
        for t in (station.allowed_vehicle_types or "").split(",")
        if t.strip()
    ]
    if vehicle.vehicle_type.strip().lower() not in allowed_types:
        raise HTTPException(status_code=400, detail="Station does not support this vehicle type")

    # 以下"活跃预约存在性 + 时段名额 + 写入"处于同一临界区，
    # 避免并发请求同时通过"无活跃预约"与"名额未满"检查导致超额/重复预约。
    slot_capacity = _slot_capacity(station.daily_capacity)
    with _booking_lock:
        active_appointment = crud.get_active_appointment_for_vehicle(db, appointment.vehicle_id)
        if active_appointment:
            raise HTTPException(
                status_code=400,
                detail=f"Vehicle already has an active appointment (id={active_appointment.id})",
            )
        booked_count = crud.count_appointments_in_slot(
            db,
            appointment.station_id,
            appointment.appointment_date,
            appointment.time_slot,
        )
        if booked_count >= slot_capacity:
            raise HTTPException(status_code=400, detail="No remaining slots for selected date and time")
        return crud.create_appointment(db, appointment)


@router.get("/", response_model=List[schemas.AppointmentResponse])
def list_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    # 归属过滤下沉到 SQL，避免全量拉取后内存截断导致分页错乱
    if current_user.role == "owner":
        return crud.list_appointments_by_owner(db, current_user.id, skip=skip, limit=limit)
    if current_user.role == "station":
        return crud.list_appointments_by_station(db, current_user.station_id, skip=skip, limit=limit)
    return crud.list_appointments(db, skip=skip, limit=limit)


@router.get("/{appointment_id}", response_model=schemas.AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == "owner" and appointment.vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == "station" and appointment.station_id != current_user.station_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return appointment


@router.post("/{appointment_id}/cancel", response_model=schemas.AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != "admin" and (
        current_user.role != "owner" or appointment.vehicle.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if appointment.status not in ["booked", "checking"]:
        raise HTTPException(status_code=400, detail="Appointment cannot be cancelled")
    return crud.update_appointment(
        db, appointment, schemas.AppointmentUpdate(status="cancelled")
    )


@router.post("/{appointment_id}/checkin", response_model=schemas.AppointmentResponse)
def checkin_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role not in ["station", "admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == "station" and appointment.station_id != current_user.station_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if appointment.status != "booked":
        raise HTTPException(status_code=400, detail="Only booked appointments can be checked in")
    return crud.update_appointment(
        db, appointment, schemas.AppointmentUpdate(status="checking")
    )


@router.put("/{appointment_id}", response_model=schemas.AppointmentResponse)
def update_appointment(
    appointment_id: int,
    updates: schemas.AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == "owner":
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == "station" and appointment.station_id != current_user.station_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    # 不允许通过该接口修改检测站归属或直接篡改状态机（状态只能经 cancel/checkin/录入结果流转）
    if updates.station_id is not None or updates.status is not None:
        raise HTTPException(status_code=400, detail="Cannot change station or status directly")
    # 仅 booked 预约可调整日期/时段
    if appointment.status != "booked":
        raise HTTPException(status_code=400, detail="Only booked appointments can be rescheduled")
    today = date.today()
    new_date = updates.appointment_date or appointment.appointment_date
    new_slot = updates.time_slot or appointment.time_slot
    if new_date < today:
        raise HTTPException(status_code=400, detail="Appointment date cannot be in the past")
    if new_date > today + timedelta(days=30):
        raise HTTPException(status_code=400, detail="Appointment date cannot be more than 30 days in the future")
    if new_slot not in TIME_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid time slot")
    # 车队容量重校验（排除自身）
    slot_capacity = _slot_capacity(appointment.station.daily_capacity)
    with _booking_lock:
        booked_count = crud.count_appointments_in_slot(
            db,
            appointment.station_id,
            new_date,
            new_slot,
            exclude_id=appointment.id,
        )
        if booked_count >= slot_capacity:
            raise HTTPException(status_code=400, detail="No remaining slots for selected date and time")
        return crud.update_appointment(
            db,
            appointment,
            schemas.AppointmentUpdate(appointment_date=new_date, time_slot=new_slot),
        )


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.inspection_report:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该预约已生成检测报告，无法删除",
        )
    if appointment.status not in ("booked", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="仅可删除已预约或已取消的预约",
        )
    crud.delete_appointment(db, appointment)
    return None
