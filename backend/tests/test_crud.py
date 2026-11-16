from datetime import date, timedelta

from app import crud, schemas


def test_calculate_next_inspection_date_leap_year():
    """闰年 2 月 29 日注册的车辆，在非闰年应跳至 3 月 1 日。"""
    register_date = date(2020, 2, 29)
    next_date = crud.calculate_next_inspection_date(register_date)
    assert next_date >= date.today()
    assert (next_date.month, next_date.day) == (3, 1)


def test_calculate_next_inspection_date_future_register_date():
    """未来注册日期直接返回自身（边界分支）。"""
    future = date.today() + timedelta(days=7)
    assert crud.calculate_next_inspection_date(future) == future


def test_calculate_next_inspection_date_today_registration():
    """今天登记的新车，首次年检应在一周年后，而非“今日到期”。"""
    today = date.today()
    next_date = crud.calculate_next_inspection_date(today)
    assert next_date > today
    assert (next_date.month, next_date.day) == (today.month, today.day) or (
        # 闰年 2/29 转入非闰年 3/1
        (today.month, today.day) == (2, 29) and (next_date.month, next_date.day) == (3, 1)
    )


def test_update_user(db):
    user = crud.create_user(
        db,
        schemas.UserCreate(
            username="crud_user",
            password="Password123",
            role="owner",
            phone="13800000000",
            real_name="原始",
        ),
    )
    updated = crud.update_user(
        db, user, schemas.UserUpdate(real_name="更新后", phone="13900000000")
    )
    assert updated.real_name == "更新后"
    assert updated.phone == "13900000000"


def test_delete_user(db):
    user = crud.create_user(
        db,
        schemas.UserCreate(
            username="del_user",
            password="Password123",
            role="owner",
            phone="13800000000",
            real_name="待删除",
        ),
    )
    crud.delete_user(db, user)
    assert crud.get_user_by_username(db, "del_user") is None


def test_count_appointments_in_slot_exclude_id(db):
    """count_appointments_in_slot 的 exclude_id 分支。"""
    station = crud.create_station(
        db,
        schemas.StationCreate(
            name="容量站",
            address="地址",
            phone="010",
            allowed_vehicle_types="small_car",
            daily_capacity=40,
        ),
    )
    owner = crud.create_user(
        db,
        schemas.UserCreate(
            username="owner_count",
            password="Password123",
            role="owner",
            phone="13800000000",
            real_name="车主",
        ),
    )
    vehicle = crud.create_vehicle(
        db,
        schemas.VehicleCreate(
            plate_number="鲁D00001",
            vehicle_type="small_car",
            register_date=date(2022, 1, 1),
            usage_nature="non_operational",
        ),
        owner_id=owner.id,
    )
    appt_date = date.today() + timedelta(days=5)
    appt = crud.create_appointment(
        db,
        schemas.AppointmentCreate(
            vehicle_id=vehicle.id,
            station_id=station.id,
            appointment_date=appt_date,
            time_slot="08:00-10:00",
        ),
    )
    assert crud.count_appointments_in_slot(db, station.id, appt_date, "08:00-10:00") == 1
    assert (
        crud.count_appointments_in_slot(
            db, station.id, appt_date, "08:00-10:00", exclude_id=appt.id
        )
        == 0
    )


def test_get_report_by_id_and_list_reports(db):
    """覆盖 crud.get_report_by_id 与 crud.list_reports 的分支。"""
    station = crud.create_station(
        db,
        schemas.StationCreate(
            name="报告站",
            address="地址",
            phone="010",
            allowed_vehicle_types="small_car",
            daily_capacity=40,
        ),
    )
    owner = crud.create_user(
        db,
        schemas.UserCreate(
            username="owner_report_crud",
            password="Password123",
            role="owner",
            phone="13800000000",
            real_name="车主",
        ),
    )
    vehicle = crud.create_vehicle(
        db,
        schemas.VehicleCreate(
            plate_number="鲁E00001",
            vehicle_type="small_car",
            register_date=date(2022, 1, 1),
            usage_nature="non_operational",
        ),
        owner_id=owner.id,
    )
    appt = crud.create_appointment(
        db,
        schemas.AppointmentCreate(
            vehicle_id=vehicle.id,
            station_id=station.id,
            appointment_date=date.today() + timedelta(days=5),
            time_slot="08:00-10:00",
        ),
    )
    report = crud.create_inspection_report(
        db,
        schemas.InspectionReportCreate(
            appointment_id=appt.id, result="pass", overall_comment="", items=[]
        ),
    )
    assert crud.get_report_by_id(db, report.id) is not None
    assert crud.get_report_by_id(db, 9999) is None
    assert report in crud.list_reports(db)
