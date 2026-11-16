from datetime import date, timedelta

from tests.conftest import (
    auth_headers,
    create_admin_user,
    create_owner_user,
    create_station_user,
    get_token,
)


def _create_station(client, admin_token, **kwargs):
    payload = {
        "name": "预约检测站",
        "address": "测试地址",
        "phone": "010-12345678",
        "allowed_vehicle_types": "small_car",
        "daily_capacity": 40,
        **kwargs,
    }
    return client.post("/api/v1/stations", json=payload, headers=auth_headers(admin_token))


def _create_vehicle(client, owner_token, plate_number: str, **kwargs):
    payload = {
        "plate_number": plate_number,
        "vehicle_type": "small_car",
        "register_date": (date.today() - timedelta(days=365)).isoformat(),
        "usage_nature": "non_operational",
        **kwargs,
    }
    return client.post("/api/v1/vehicles", json=payload, headers=auth_headers(owner_token))


def _create_appointment(client, owner_token, vehicle_id: int, station_id: int, days_ahead: int = 5, slot: str = "08:00-10:00"):
    payload = {
        "vehicle_id": vehicle_id,
        "station_id": station_id,
        "appointment_date": (date.today() + timedelta(days=days_ahead)).isoformat(),
        "time_slot": slot,
    }
    return client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))


def test_create_appointment_success(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_appt")
    owner_token = get_token(client, "owner_appt")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    resp = _create_appointment(client, owner_token, vehicle["id"], station["id"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "booked"
    assert data["time_slot"] == "08:00-10:00"


def test_create_appointment_past_date(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_past")
    owner_token = get_token(client, "owner_past")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    payload = {
        "vehicle_id": vehicle["id"],
        "station_id": station["id"],
        "appointment_date": (date.today() - timedelta(days=1)).isoformat(),
        "time_slot": "08:00-10:00",
    }
    resp = client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))
    assert resp.status_code == 400
    assert "past" in resp.json()["detail"]


def test_create_appointment_over_30_days(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_30")
    owner_token = get_token(client, "owner_30")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    payload = {
        "vehicle_id": vehicle["id"],
        "station_id": station["id"],
        "appointment_date": (date.today() + timedelta(days=31)).isoformat(),
        "time_slot": "08:00-10:00",
    }
    resp = client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))
    assert resp.status_code == 400
    assert "30 days" in resp.json()["detail"]


def test_create_appointment_duplicate_active(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_dup_appt")
    owner_token = get_token(client, "owner_dup_appt")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    resp1 = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=5)
    assert resp1.status_code == 201

    resp2 = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=6)
    assert resp2.status_code == 400
    assert "active appointment" in resp2.json()["detail"]


def test_cancel_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_cancel")
    owner_token = get_token(client, "owner_cancel")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    resp = client.post(
        f"/api/v1/appointments/{appt['id']}/cancel",
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # 取消后可再次预约同一车辆
    resp2 = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=7)
    assert resp2.status_code == 201


def test_checkin_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_checkin")
    owner_token = get_token(client, "owner_checkin")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    station_user = create_station_user(db, "staff_checkin", station["id"])
    station_token = get_token(client, "staff_checkin")

    resp = client.post(
        f"/api/v1/appointments/{appt['id']}/checkin",
        headers=auth_headers(station_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "checking"


def test_checkin_by_owner_forbidden(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_no_checkin")
    owner_token = get_token(client, "owner_no_checkin")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    resp = client.post(
        f"/api/v1/appointments/{appt['id']}/checkin",
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 403


def test_appointment_response_includes_nested_vehicle_and_station(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_nested")
    owner_token = get_token(client, "owner_nested")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    resp = _create_appointment(client, owner_token, vehicle["id"], station["id"])
    assert resp.status_code == 201
    data = resp.json()
    # 前端依赖嵌套对象展示车牌/检测站名称
    assert data["vehicle"]["plate_number"] == unique_plate
    assert data["vehicle"]["vehicle_type"] == "small_car"
    assert data["station"]["name"] == "预约检测站"

    resp2 = client.get("/api/v1/appointments", headers=auth_headers(owner_token))
    assert resp2.status_code == 200
    item = resp2.json()[0]
    assert item["vehicle"]["plate_number"] == unique_plate
    assert item["station"]["name"] == "预约检测站"


def test_owner_cannot_hard_delete_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_no_delete")
    owner_token = get_token(client, "owner_no_delete")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    resp = client.delete(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(owner_token))
    assert resp.status_code == 403


def test_admin_cannot_delete_appointment_with_report(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_del_report")
    owner_token = get_token(client, "owner_del_report")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    station_user = create_station_user(db, "staff_del_report", station["id"])
    station_token = get_token(client, "staff_del_report")
    client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(station_token))
    resp_report = client.post(
        "/api/v1/reports",
        json={"appointment_id": appt["id"], "result": "pass", "items": []},
        headers=auth_headers(station_token),
    )
    assert resp_report.status_code == 201

    resp = client.delete(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 409


def test_delete_appointment_by_admin_success(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_admin_del")
    owner_token = get_token(client, "owner_admin_del")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    resp = client.delete(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 204
    resp2 = client.get(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(admin_token))
    assert resp2.status_code == 404


def test_create_appointment_vehicle_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_vnf")
    owner_token = get_token(client, "owner_vnf")
    payload = {
        "vehicle_id": 9999,
        "station_id": station["id"],
        "appointment_date": (date.today() + timedelta(days=5)).isoformat(),
        "time_slot": "08:00-10:00",
    }
    resp = client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))
    assert resp.status_code == 404
    assert "Vehicle not found" in resp.json()["detail"]


def test_owner_cannot_book_others_vehicle(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner_a = create_owner_user(db, "owner_a")
    owner_a_token = get_token(client, "owner_a")
    owner_b = create_owner_user(db, "owner_b")
    owner_b_token = get_token(client, "owner_b")

    vehicle = _create_vehicle(client, owner_a_token, unique_plate).json()
    resp = _create_appointment(client, owner_b_token, vehicle["id"], station["id"])
    assert resp.status_code == 403
    assert "Permission denied" in resp.json()["detail"]


def test_create_appointment_station_not_found(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, "owner_snf")
    owner_token = get_token(client, "owner_snf")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    payload = {
        "vehicle_id": vehicle["id"],
        "station_id": 9999,
        "appointment_date": (date.today() + timedelta(days=5)).isoformat(),
        "time_slot": "08:00-10:00",
    }
    resp = client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))
    assert resp.status_code == 404
    assert "Station not found" in resp.json()["detail"]


def test_create_appointment_unsupported_vehicle_type(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token, allowed_vehicle_types="truck").json()
    owner = create_owner_user(db, "owner_unsupported")
    owner_token = get_token(client, "owner_unsupported")
    vehicle = _create_vehicle(client, owner_token, unique_plate, vehicle_type="small_car").json()
    resp = _create_appointment(client, owner_token, vehicle["id"], station["id"])
    assert resp.status_code == 400
    assert "does not support" in resp.json()["detail"]


def test_create_appointment_slot_full(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token, daily_capacity=4).json()

    owner = create_owner_user(db, "owner_full")
    owner_token = get_token(client, "owner_full")
    vehicle1 = _create_vehicle(client, owner_token, "鲁B11111").json()
    vehicle2 = _create_vehicle(client, owner_token, "鲁C22222").json()

    resp1 = _create_appointment(client, owner_token, vehicle1["id"], station["id"], slot="08:00-10:00")
    assert resp1.status_code == 201
    resp2 = _create_appointment(client, owner_token, vehicle2["id"], station["id"], slot="08:00-10:00")
    assert resp2.status_code == 400
    assert "No remaining slots" in resp2.json()["detail"]


def test_list_appointments_station_scope(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token, name="站A").json()
    station_b = _create_station(client, admin_token, name="站B").json()

    owner = create_owner_user(db, "owner_scope")
    owner_token = get_token(client, "owner_scope")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    _create_appointment(client, owner_token, vehicle["id"], station_a["id"], days_ahead=6)
    staff_b = create_station_user(db, "staff_b", station_b["id"])
    staff_b_token = get_token(client, "staff_b")

    resp = client.get("/api/v1/appointments", headers=auth_headers(staff_b_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_get_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.get("/api/v1/appointments/9999", headers=auth_headers(admin_token))
    assert resp.status_code == 404
    assert "Appointment not found" in resp.json()["detail"]


def test_station_cannot_cancel_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token).json()
    station_b = _create_station(client, admin_token, name="站B_cancel").json()

    owner = create_owner_user(db, "owner_st_cancel")
    owner_token = get_token(client, "owner_st_cancel")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"]).json()

    staff_b = create_station_user(db, "staff_b_cancel", station_b["id"])
    staff_b_token = get_token(client, "staff_b_cancel")
    resp = client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers(staff_b_token))
    assert resp.status_code == 403


def test_cancel_completed_appointment_rejected(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_cancel_done")
    owner_token = get_token(client, "owner_cancel_done")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    staff = create_station_user(db, "staff_cancel_done", station["id"])
    staff_token = get_token(client, "staff_cancel_done")
    client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_token))
    client.post(
        "/api/v1/reports",
        json={"appointment_id": appt["id"], "result": "pass", "items": []},
        headers=auth_headers(staff_token),
    )

    resp = client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers(owner_token))
    assert resp.status_code == 400
    assert "cannot be cancelled" in resp.json()["detail"]


def test_checkin_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    staff = create_station_user(db, "staff_cnf", station["id"])
    staff_token = get_token(client, "staff_cnf")
    resp = client.post("/api/v1/appointments/9999/checkin", headers=auth_headers(staff_token))
    assert resp.status_code == 404


def test_checkin_wrong_station_forbidden(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token).json()
    station_b = _create_station(client, admin_token, name="站B_checkin").json()

    owner = create_owner_user(db, "owner_wrong_station")
    owner_token = get_token(client, "owner_wrong_station")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"]).json()

    staff_b = create_station_user(db, "staff_b_checkin", station_b["id"])
    staff_b_token = get_token(client, "staff_b_checkin")
    resp = client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_b_token))
    assert resp.status_code == 403


def test_checkin_cancelled_appointment_rejected(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_checkin_cancel")
    owner_token = get_token(client, "owner_checkin_cancel")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers(owner_token))

    staff = create_station_user(db, "staff_checkin_cancel", station["id"])
    staff_token = get_token(client, "staff_checkin_cancel")
    resp = client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_token))
    assert resp.status_code == 400
    assert "Only booked" in resp.json()["detail"]


def test_update_appointment_by_admin(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_update")
    owner_token = get_token(client, "owner_update")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    new_date = (date.today() + timedelta(days=10)).isoformat()
    resp = client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"appointment_date": new_date, "time_slot": "15:00-17:00"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["appointment_date"] == new_date
    assert data["time_slot"] == "15:00-17:00"


def test_update_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.put(
        "/api/v1/appointments/9999",
        json={"appointment_date": (date.today() + timedelta(days=5)).isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


def test_owner_cannot_update_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_no_update")
    owner_token = get_token(client, "owner_no_update")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    resp = client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"time_slot": "10:00-12:00"},
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 403


def test_station_cannot_update_other_station_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token).json()
    station_b = _create_station(client, admin_token, name="站B_update").json()

    owner = create_owner_user(db, "owner_cross_update")
    owner_token = get_token(client, "owner_cross_update")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"]).json()

    staff_b = create_station_user(db, "staff_b_update", station_b["id"])
    staff_b_token = get_token(client, "staff_b_update")
    resp = client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"time_slot": "10:00-12:00"},
        headers=auth_headers(staff_b_token),
    )
    assert resp.status_code == 403


def test_delete_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.delete("/api/v1/appointments/9999", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_list_appointments_owner_scope(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner_a = create_owner_user(db, "owner_scope_a")
    owner_a_token = get_token(client, "owner_scope_a")
    owner_b = create_owner_user(db, "owner_scope_b")
    owner_b_token = get_token(client, "owner_scope_b")

    vehicle_a = _create_vehicle(client, owner_a_token, unique_plate).json()
    _create_appointment(client, owner_a_token, vehicle_a["id"], station["id"], days_ahead=6)

    resp = client.get("/api/v1/appointments", headers=auth_headers(owner_b_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_owner_cannot_view_others_appointment(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner_a = create_owner_user(db, "owner_appt_a")
    owner_a_token = get_token(client, "owner_appt_a")
    owner_b = create_owner_user(db, "owner_appt_b")
    owner_b_token = get_token(client, "owner_appt_b")

    vehicle = _create_vehicle(client, owner_a_token, unique_plate).json()
    appt = _create_appointment(client, owner_a_token, vehicle["id"], station["id"]).json()
    resp = client.get(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(owner_b_token))
    assert resp.status_code == 403


def test_station_cannot_view_other_station_appointment_detail(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token).json()
    station_b = _create_station(client, admin_token, name="站B_detail_appt").json()

    owner = create_owner_user(db, "owner_cross_appt")
    owner_token = get_token(client, "owner_cross_appt")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"]).json()

    staff_b = create_station_user(db, "staff_b_appt", station_b["id"])
    staff_b_token = get_token(client, "staff_b_appt")
    resp = client.get(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(staff_b_token))
    assert resp.status_code == 403


def test_cancel_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.post("/api/v1/appointments/9999/cancel", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_list_appointments_admin_sees_all(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_admin_appt")
    owner_token = get_token(client, "owner_admin_appt")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=6)

    resp = client.get("/api/v1/appointments", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_appointment_success(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_get_appt")
    owner_token = get_token(client, "owner_get_appt")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    resp = client.get(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(owner_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == appt["id"]


# ---------- Phase 修复补充：状态机 / 时段枚举 / 删除约束 ----------

def test_update_appointment_cannot_change_status_or_station(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_stat_lock")
    owner_token = get_token(client, "owner_stat_lock")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    resp = client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"status": "completed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "Cannot change station or status" in resp.json()["detail"]


def test_update_appointment_only_booked_can_reschedule(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_resched")
    owner_token = get_token(client, "owner_resched")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    staff = create_station_user(db, "staff_resched", station["id"])
    staff_token = get_token(client, "staff_resched")
    client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_token))
    # 已到站登记（checking）后不可改期
    resp = client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"appointment_date": (date.today() + timedelta(days=8)).isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "Only booked" in resp.json()["detail"]


def test_create_appointment_rejects_invalid_time_slot(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_bad_slot")
    owner_token = get_token(client, "owner_bad_slot")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    resp = client.post(
        "/api/v1/appointments",
        json={
            "vehicle_id": vehicle["id"],
            "station_id": station["id"],
            "appointment_date": (date.today() + timedelta(days=5)).isoformat(),
            "time_slot": "99:00-00:00",
        },
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 400
    assert "Invalid time slot" in resp.json()["detail"]


def test_delete_checking_appointment_rejected(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_del_checking")
    owner_token = get_token(client, "owner_del_checking")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()

    staff = create_station_user(db, "staff_del_checking", station["id"])
    staff_token = get_token(client, "staff_del_checking")
    client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_token))

    resp = client.delete(f"/api/v1/appointments/{appt['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 409
    assert "仅可删除" in resp.json()["detail"]


def test_reschedule_appointment_checks_slot_capacity(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    # 容量 4，每时段 1 个名额
    station = _create_station(client, admin_token, daily_capacity=4).json()
    owner = create_owner_user(db, "owner_cap_resched")
    owner_token = get_token(client, "owner_cap_resched")

    v1 = _create_vehicle(client, owner_token, unique_plate).json()
    appt1 = _create_appointment(client, owner_token, v1["id"], station["id"], slot="08:00-10:00").json()

    # 另一车主在改期目标日期（今天+7）占满 08:00-10:00 名额
    owner2 = create_owner_user(db, "owner_cap_resched2")
    owner2_token = get_token(client, "owner_cap_resched2")
    v2 = _create_vehicle(client, owner2_token, "鲁A88888").json()
    _create_appointment(client, owner2_token, v2["id"], station["id"], days_ahead=7, slot="08:00-10:00")

    new_date = (date.today() + timedelta(days=7)).isoformat()
    resp = client.put(
        f"/api/v1/appointments/{appt1['id']}",
        json={"appointment_date": new_date, "time_slot": "08:00-10:00"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "No remaining slots" in resp.json()["detail"]
