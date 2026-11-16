from datetime import date, timedelta

from tests.conftest import (
    auth_headers,
    create_admin_user,
    create_owner_user,
    create_station_user,
    get_token,
)


def _create_station(client, token, **kwargs):
    payload = {
        "name": "测试检测站",
        "address": "测试路1号",
        "phone": "010-12345678",
        "allowed_vehicle_types": "small_car",
        "daily_capacity": 40,
        **kwargs,
    }
    return client.post("/api/v1/stations", json=payload, headers=auth_headers(token))


def test_create_station_by_admin(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    resp = _create_station(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试检测站"
    assert data["allowed_vehicle_types"] == "small_car"
    assert data["daily_capacity"] == 40


def test_create_station_by_owner_forbidden(client, db, unique_username):
    create_owner_user(db, unique_username)
    token = get_token(client, unique_username)
    resp = _create_station(client, token)
    assert resp.status_code == 403


def test_list_stations(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    _create_station(client, token, name="站点A")
    _create_station(client, token, name="站点B")
    resp = client.get("/api/v1/stations", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_station(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    created = _create_station(client, token).json()
    resp = client.get(f"/api/v1/stations/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_update_station(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    created = _create_station(client, token).json()
    resp = client.put(
        f"/api/v1/stations/{created['id']}",
        json={"daily_capacity": 80, "address": "更新地址"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_capacity"] == 80
    assert data["address"] == "更新地址"


def test_delete_station(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    created = _create_station(client, token).json()
    resp = client.delete(f"/api/v1/stations/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 204
    resp = client.get(f"/api/v1/stations/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_station_with_appointments_conflict(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    from tests.conftest import create_owner_user
    create_owner_user(db, "owner_del_station")
    owner_token = get_token(client, "owner_del_station")
    vehicle = client.post(
        "/api/v1/vehicles",
        json={"plate_number": unique_plate, "vehicle_type": "small_car", "register_date": "2024-01-01"},
        headers=auth_headers(owner_token),
    ).json()
    target_date = (date.today() + timedelta(days=5)).isoformat()
    appt = client.post(
        "/api/v1/appointments",
        json={"vehicle_id": vehicle["id"], "station_id": station["id"], "appointment_date": target_date, "time_slot": "08:00-10:00"},
        headers=auth_headers(owner_token),
    )
    assert appt.status_code == 201

    resp = client.delete(f"/api/v1/stations/{station['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 409
    assert "无法删除" in resp.json()["detail"]


def test_delete_station_with_staff_conflict(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    create_station_user(db, "staff_del_station", station["id"])
    resp = client.delete(f"/api/v1/stations/{station['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 409


def test_filter_stations_by_vehicle_type(client, db):
    admin = create_admin_user(db)
    token = get_token(client, admin.username, "admin123")
    _create_station(client, token, name="小型车检测站", allowed_vehicle_types="small_car")
    _create_station(client, token, name="大型车检测站", allowed_vehicle_types="large_car")

    owner_user = create_owner_user(db, "owner_filter")
    owner_token = get_token(client, "owner_filter")

    target_date = date.today() + timedelta(days=5)
    resp = client.get(
        "/api/v1/stations/available",
        params={"vehicle_type": "small_car", "date": target_date.isoformat()},
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["station"]["name"] == "小型车检测站"
    assert len(data[0]["time_slots"]) == 4
    # 日检测能力 40，共分为 4 个时段，每时段 10 个名额
    assert data[0]["time_slots"][0]["remaining"] == 10


def test_update_station_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.put(
        "/api/v1/stations/9999",
        json={"daily_capacity": 80},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


def test_delete_station_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.delete("/api/v1/stations/9999", headers=auth_headers(admin_token))
    assert resp.status_code == 404
