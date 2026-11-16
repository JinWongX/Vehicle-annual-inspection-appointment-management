from datetime import date, timedelta

from tests.conftest import auth_headers, create_admin_user, create_owner_user, get_token


def _create_vehicle(client, token, **kwargs):
    payload = {
        "plate_number": f"鲁A{hash(kwargs.get('plate_number', 'TEST')) % 100000:05d}",
        "vehicle_type": "small_car",
        "register_date": (date.today() - timedelta(days=365)).isoformat(),
        "usage_nature": "non_operational",
        **kwargs,
    }
    if "plate_number" in kwargs:
        payload["plate_number"] = kwargs["plate_number"]
    return client.post("/api/v1/vehicles", json=payload, headers=auth_headers(token))


def test_create_vehicle(client, db, unique_plate):
    owner = create_owner_user(db, "owner_vehicle")
    token = get_token(client, "owner_vehicle")
    resp = _create_vehicle(client, token, plate_number=unique_plate)
    assert resp.status_code == 201
    data = resp.json()
    assert data["plate_number"] == unique_plate
    assert data["vehicle_type"] == "small_car"
    assert data["owner_id"] == owner.id


def test_create_vehicle_auto_next_inspection(client, db, unique_plate):
    register_date = date.today() - timedelta(days=400)
    owner = create_owner_user(db, "owner_auto")
    token = get_token(client, "owner_auto")
    resp = _create_vehicle(
        client,
        token,
        plate_number=unique_plate,
        register_date=register_date.isoformat(),
        next_inspection_date=None,
    )
    assert resp.status_code == 201
    data = resp.json()
    # 注册日期 anniversary 计算，应大于等于今天
    next_date = date.fromisoformat(data["next_inspection_date"])
    assert next_date >= date.today()
    # 应是从注册日期起按周年递增的日期
    years = next_date.year - register_date.year
    assert years >= 1


def test_create_vehicle_duplicate_plate(client, db, unique_plate):
    owner = create_owner_user(db, "owner_dup")
    token = get_token(client, "owner_dup")
    _create_vehicle(client, token, plate_number=unique_plate)
    resp = _create_vehicle(client, token, plate_number=unique_plate)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_list_vehicles_for_owner(client, db, unique_plate):
    owner = create_owner_user(db, "owner_list")
    token = get_token(client, "owner_list")
    _create_vehicle(client, token, plate_number=unique_plate)
    resp = client.get("/api/v1/vehicles", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["plate_number"] == unique_plate


def test_reminder_list_days_until_inspection(client, db, unique_plate):
    owner = create_owner_user(db, "owner_remind")
    token = get_token(client, "owner_remind")
    next_date = date.today() + timedelta(days=10)
    resp = _create_vehicle(
        client,
        token,
        plate_number=unique_plate,
        next_inspection_date=next_date.isoformat(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["days_until_inspection"] == 10


def test_delete_vehicle_with_appointments_conflict(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_resp = client.post(
        "/api/v1/stations",
        json={"name": "车辆删除站", "address": "地址", "phone": "010", "allowed_vehicle_types": "small_car", "daily_capacity": 40},
        headers=auth_headers(admin_token),
    )
    station_id = station_resp.json()["id"]

    owner = create_owner_user(db, "owner_del_vehicle")
    owner_token = get_token(client, "owner_del_vehicle")
    vehicle = _create_vehicle(client, owner_token, plate_number=unique_plate).json()

    target_date = (date.today() + timedelta(days=5)).isoformat()
    appt = client.post(
        "/api/v1/appointments",
        json={"vehicle_id": vehicle["id"], "station_id": station_id, "appointment_date": target_date, "time_slot": "08:00-10:00"},
        headers=auth_headers(owner_token),
    )
    assert appt.status_code == 201

    resp = client.delete(f"/api/v1/vehicles/{vehicle['id']}", headers=auth_headers(owner_token))
    assert resp.status_code == 409
    assert "无法删除" in resp.json()["detail"]


def test_delete_vehicle_without_appointments_success(client, db, unique_plate):
    owner = create_owner_user(db, "owner_del_ok")
    token = get_token(client, "owner_del_ok")
    vehicle = _create_vehicle(client, token, plate_number=unique_plate).json()
    resp = client.delete(f"/api/v1/vehicles/{vehicle['id']}", headers=auth_headers(token))
    assert resp.status_code == 204


# ---------- 覆盖率补充用例：列表权限/详情/更新/删除分支 ----------

def test_list_vehicles_admin_sees_all(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    create_owner_user(db, "owner_admin_list")
    owner_token = get_token(client, "owner_admin_list")
    _create_vehicle(client, owner_token, plate_number=unique_plate)
    resp = client.get("/api/v1/vehicles", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    plates = [v["plate_number"] for v in resp.json()]
    assert unique_plate in plates


def test_get_vehicle_not_found(client, db):
    create_owner_user(db, "owner_get_404")
    token = get_token(client, "owner_get_404")
    resp = client.get("/api/v1/vehicles/99999", headers=auth_headers(token))
    assert resp.status_code == 404


def test_owner_cannot_view_others_vehicle(client, db, unique_plate):
    create_owner_user(db, "owner_view_a")
    token_a = get_token(client, "owner_view_a")
    vehicle = _create_vehicle(client, token_a, plate_number=unique_plate).json()

    create_owner_user(db, "owner_view_b")
    token_b = get_token(client, "owner_view_b")
    resp = client.get(f"/api/v1/vehicles/{vehicle['id']}", headers=auth_headers(token_b))
    assert resp.status_code == 403


def test_update_vehicle_by_owner(client, db, unique_plate):
    create_owner_user(db, "owner_update")
    token = get_token(client, "owner_update")
    vehicle = _create_vehicle(client, token, plate_number=unique_plate).json()

    new_register = (date.today() - timedelta(days=730)).isoformat()
    resp = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"register_date": new_register, "usage_nature": "operational"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["usage_nature"] == "operational"
    # 修改注册日期后自动按周年规则重算下次年检日期
    next_date = date.fromisoformat(data["next_inspection_date"])
    assert next_date >= date.today()


def test_update_vehicle_not_found(client, db):
    create_owner_user(db, "owner_upd_404")
    token = get_token(client, "owner_upd_404")
    resp = client.put(
        "/api/v1/vehicles/99999",
        json={"usage_nature": "operational"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_owner_cannot_update_others_vehicle(client, db, unique_plate):
    create_owner_user(db, "owner_upd_a")
    token_a = get_token(client, "owner_upd_a")
    vehicle = _create_vehicle(client, token_a, plate_number=unique_plate).json()

    create_owner_user(db, "owner_upd_b")
    token_b = get_token(client, "owner_upd_b")
    resp = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"usage_nature": "operational"},
        headers=auth_headers(token_b),
    )
    assert resp.status_code == 403


def test_delete_vehicle_not_found(client, db):
    create_owner_user(db, "owner_del_404")
    token = get_token(client, "owner_del_404")
    resp = client.delete("/api/v1/vehicles/99999", headers=auth_headers(token))
    assert resp.status_code == 404


def test_owner_cannot_delete_others_vehicle(client, db, unique_plate):
    create_owner_user(db, "owner_del_a")
    token_a = get_token(client, "owner_del_a")
    vehicle = _create_vehicle(client, token_a, plate_number=unique_plate).json()

    create_owner_user(db, "owner_del_b")
    token_b = get_token(client, "owner_del_b")
    resp = client.delete(f"/api/v1/vehicles/{vehicle['id']}", headers=auth_headers(token_b))
    assert resp.status_code == 403


def test_vehicle_without_dates_days_until_inspection_none(client, db, unique_plate):
    # 未提供注册日期与下次年检日期时，days_until_inspection 计算字段应为 null
    create_owner_user(db, "owner_nodate")
    token = get_token(client, "owner_nodate")
    resp = client.post(
        "/api/v1/vehicles",
        json={"plate_number": unique_plate, "vehicle_type": "small_car"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["days_until_inspection"] is None


def test_get_vehicle_success(client, db, unique_plate):
    create_owner_user(db, "owner_get_ok")
    token = get_token(client, "owner_get_ok")
    vehicle = _create_vehicle(client, token, plate_number=unique_plate).json()
    resp = client.get(f"/api/v1/vehicles/{vehicle['id']}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["plate_number"] == unique_plate


def test_update_vehicle_without_register_date(client, db, unique_plate):
    create_owner_user(db, "owner_update_no_date")
    token = get_token(client, "owner_update_no_date")
    vehicle = _create_vehicle(client, token, plate_number=unique_plate).json()
    resp = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"usage_nature": "operational"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["usage_nature"] == "operational"
