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
        "name": "校验检测站",
        "address": "测试地址",
        "phone": "010-12345678",
        "allowed_vehicle_types": "small_car",
        "daily_capacity": 40,
        **kwargs,
    }
    return client.post("/api/v1/stations", json=payload, headers=auth_headers(admin_token))


def _create_vehicle(client, owner_token, plate_number, **kwargs):
    payload = {
        "plate_number": plate_number,
        "vehicle_type": "small_car",
        "register_date": (date.today() - timedelta(days=365)).isoformat(),
        "usage_nature": "non_operational",
        **kwargs,
    }
    return client.post("/api/v1/vehicles", json=payload, headers=auth_headers(owner_token))


# ---------- 车牌 / 使用性质 校验 ----------

def test_create_vehicle_rejects_short_plate(client, db):
    admin = create_admin_user(db)
    owner = create_owner_user(db, "owner_short_plate")
    token = get_token(client, "owner_short_plate")
    admin_token = get_token(client, admin.username, "admin123")
    _create_station(client, admin_token)  # 需要至少一个有效站点（车型匹配）
    resp = _create_vehicle(client, token, "AB1")  # 长度 < 5
    assert resp.status_code == 422


def test_create_vehicle_rejects_invalid_usage_nature(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    _create_station(client, admin_token)
    owner = create_owner_user(db, "owner_bad_usage")
    token = get_token(client, "owner_bad_usage")
    resp = _create_vehicle(client, token, unique_plate, usage_nature="weird")
    assert resp.status_code == 422


def test_update_vehicle_rejects_invalid_usage_nature(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    _create_station(client, admin_token)
    owner = create_owner_user(db, "owner_upd_bad_usage")
    token = get_token(client, "owner_upd_bad_usage")
    vehicle = _create_vehicle(client, token, unique_plate).json()
    resp = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"usage_nature": "invalid"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


# ---------- 检测站容量 校验 ----------

def test_create_station_rejects_zero_capacity(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = _create_station(client, admin_token, daily_capacity=0)
    assert resp.status_code == 422


def test_update_station_rejects_negative_capacity(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    resp = client.put(
        f"/api/v1/stations/{station['id']}",
        json={"daily_capacity": -5},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


# ---------- 检测报告字段 校验 ----------

def test_create_report_rejects_empty_item_name(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    owner = create_owner_user(db, "owner_rep_item")
    owner_token = get_token(client, "owner_rep_item")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = client.post(
        "/api/v1/appointments",
        json={
            "vehicle_id": vehicle["id"],
            "station_id": station["id"],
            "appointment_date": (date.today() + timedelta(days=5)).isoformat(),
            "time_slot": "08:00-10:00",
        },
        headers=auth_headers(owner_token),
    ).json()
    staff = create_station_user(db, "staff_rep_item", station["id"])
    staff_token = get_token(client, "staff_rep_item")
    client.post(f"/api/v1/appointments/{appt['id']}/checkin", headers=auth_headers(staff_token))

    resp = client.post(
        "/api/v1/reports",
        json={
            "appointment_id": appt["id"],
            "result": "pass",
            "items": [{"item_name": "", "result": "pass"}],
        },
        headers=auth_headers(staff_token),
    )
    assert resp.status_code == 422