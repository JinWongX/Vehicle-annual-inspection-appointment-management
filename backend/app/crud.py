from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from . import models, schemas, auth


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role,
        phone=user.phone,
        real_name=user.real_name,
        station_id=user.station_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def calculate_next_inspection_date(register_date: date) -> date:
    """从注册日期起，按周年逐年递增，返回最近一次应年检的日期。

    - 今天登记的车辆：首次年检应为一周年后，避免刚登记就“今日到期/已逾期”。
    - 未来登记的车辆（边界输入）：直接返回注册日期。
    - 过去登记的车辆：返回最近一个大于等于今天的周年日（周年日可为今天）。
    """
    today = date.today()
    if register_date == today:
        try:
            return register_date.replace(year=register_date.year + 1)
        except ValueError:
            # 处理闰年 2 月 29 日转入非闰年的情况
            return date(register_date.year + 1, 3, 1)
    candidate = register_date
    while candidate < today:
        try:
            candidate = candidate.replace(year=candidate.year + 1)
        except ValueError:
            # 处理闰年 2 月 29 日转入非闰年的情况
            candidate = date(candidate.year + 1, 3, 1)
    return candidate


def update_user(db: Session, user: models.User, updates: schemas.UserUpdate) -> models.User:
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_station(db: Session, station: schemas.StationCreate) -> models.Station:
    db_station = models.Station(**station.model_dump())
    db.add(db_station)
    db.commit()
    db.refresh(db_station)
    return db_station


def get_station_by_id(db: Session, station_id: int) -> Optional[models.Station]:
    return db.query(models.Station).filter(models.Station.id == station_id).first()


def list_stations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Station]:
    return db.query(models.Station).offset(skip).limit(limit).all()


def update_station(db: Session, station: models.Station, updates: schemas.StationUpdate) -> models.Station:
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(station, key, value)
    db.commit()
    db.refresh(station)
    return station


def delete_station(db: Session, station: models.Station):
    db.delete(station)
    db.commit()


def create_vehicle(db: Session, vehicle: schemas.VehicleCreate, owner_id: int) -> models.Vehicle:
    db_vehicle = models.Vehicle(**vehicle.model_dump(), owner_id=owner_id)
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Optional[models.Vehicle]:
    return db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()


def get_vehicle_by_plate(db: Session, plate_number: str) -> Optional[models.Vehicle]:
    return db.query(models.Vehicle).filter(models.Vehicle.plate_number == plate_number).first()


def list_vehicles(db: Session, skip: int = 0, limit: int = 100) -> List[models.Vehicle]:
    return db.query(models.Vehicle).offset(skip).limit(limit).all()


def list_vehicles_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.Vehicle]:
    return db.query(models.Vehicle).filter(models.Vehicle.owner_id == owner_id).offset(skip).limit(limit).all()


def update_vehicle(db: Session, vehicle: models.Vehicle, updates: schemas.VehicleUpdate) -> models.Vehicle:
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle: models.Vehicle):
    db.delete(vehicle)
    db.commit()


def create_appointment(db: Session, appointment: schemas.AppointmentCreate) -> models.Appointment:
    db_appointment = models.Appointment(**appointment.model_dump())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_appointment_by_id(db: Session, appointment_id: int) -> Optional[models.Appointment]:
    return db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()


def list_appointments(db: Session, skip: int = 0, limit: int = 100) -> List[models.Appointment]:
    return db.query(models.Appointment).offset(skip).limit(limit).all()


def list_appointments_by_owner(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> List[models.Appointment]:
    return (
        db.query(models.Appointment)
        .join(models.Vehicle)
        .filter(models.Vehicle.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_appointments_by_station(
    db: Session, station_id: int, skip: int = 0, limit: int = 100
) -> List[models.Appointment]:
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.station_id == station_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_appointment(db: Session, appointment: models.Appointment, updates: schemas.AppointmentUpdate) -> models.Appointment:
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(appointment, key, value)
    db.commit()
    db.refresh(appointment)
    return appointment


def delete_appointment(db: Session, appointment: models.Appointment):
    db.delete(appointment)
    db.commit()


def count_appointments_in_slot(
    db: Session,
    station_id: int,
    appointment_date: date,
    time_slot: str,
    exclude_id: Optional[int] = None,
) -> int:
    query = db.query(models.Appointment).filter(
        models.Appointment.station_id == station_id,
        models.Appointment.appointment_date == appointment_date,
        models.Appointment.time_slot == time_slot,
        models.Appointment.status != "cancelled",
    )
    if exclude_id is not None:
        query = query.filter(models.Appointment.id != exclude_id)
    return query.count()


def get_active_appointment_for_vehicle(db: Session, vehicle_id: int) -> Optional[models.Appointment]:
    return (
        db.query(models.Appointment)
        .filter(
            models.Appointment.vehicle_id == vehicle_id,
            models.Appointment.status.in_(["booked", "checking"]),
        )
        .first()
    )


def create_inspection_report(db: Session, report: schemas.InspectionReportCreate) -> models.InspectionReport:
    db_report = models.InspectionReport(
        appointment_id=report.appointment_id,
        result=report.result,
        overall_comment=report.overall_comment,
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    for item in report.items or []:
        db_item = models.InspectionItem(
            report_id=db_report.id,
            item_name=item.item_name,
            result=item.result,
            comment=item.comment,
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_report)
    return db_report


def create_inspection_report_and_complete(
    db: Session,
    report: schemas.InspectionReportCreate,
) -> models.InspectionReport:
    """在同一事务内完成：创建报告 + 插入检测项 + 预约状态流转为 completed。

    任一步失败整体回滚，避免产生"报告存在但预约仍 checking"的脏数据。
    """
    db_report = models.InspectionReport(
        appointment_id=report.appointment_id,
        result=report.result,
        overall_comment=report.overall_comment,
    )
    db.add(db_report)
    db.flush()

    for item in report.items or []:
        db_item = models.InspectionItem(
            report_id=db_report.id,
            item_name=item.item_name,
            result=item.result,
            comment=item.comment,
        )
        db.add(db_item)

    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == report.appointment_id
    ).first()
    if appointment:
        appointment.status = "completed"

    db.commit()
    db.refresh(db_report)
    return db_report


def get_report_by_id(db: Session, report_id: int) -> Optional[models.InspectionReport]:
    return db.query(models.InspectionReport).filter(models.InspectionReport.id == report_id).first()


def get_report_by_appointment_id(db: Session, appointment_id: int) -> Optional[models.InspectionReport]:
    return db.query(models.InspectionReport).filter(models.InspectionReport.appointment_id == appointment_id).first()


def list_reports(db: Session, skip: int = 0, limit: int = 100) -> List[models.InspectionReport]:
    return db.query(models.InspectionReport).offset(skip).limit(limit).all()


def list_reports_by_owner(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> List[models.InspectionReport]:
    return (
        db.query(models.InspectionReport)
        .join(models.Appointment)
        .join(models.Vehicle)
        .filter(models.Vehicle.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_reports_by_station(
    db: Session, station_id: int, skip: int = 0, limit: int = 100
) -> List[models.InspectionReport]:
    return (
        db.query(models.InspectionReport)
        .join(models.Appointment)
        .filter(models.Appointment.station_id == station_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
