from tests.conftest import (
    auth_headers,
    create_admin_user,
    create_owner_user,
    create_station_user,
    get_token,
    register_user,
)


def test_change_password_success(client, unique_username):
    register_user(client, unique_username, password="Password123")
    token = get_token(client, unique_username, "Password123")
    resp = client.put(
        "/api/v1/auth/password",
        json={"old_password": "Password123", "new_password": "NewPassword456"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    # 旧密码失效，新密码可登录
    old_login = client.post("/api/v1/auth/login", data={"username": unique_username, "password": "Password123"})
    assert old_login.status_code == 401
    new_login = client.post("/api/v1/auth/login", data={"username": unique_username, "password": "NewPassword456"})
    assert new_login.status_code == 200


def test_change_password_wrong_old(client, unique_username):
    register_user(client, unique_username, password="Password123")
    token = get_token(client, unique_username, "Password123")
    resp = client.put(
        "/api/v1/auth/password",
        json={"old_password": "WrongOld123", "new_password": "NewPassword456"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"]


def test_change_password_too_short(client, unique_username):
    register_user(client, unique_username, password="Password123")
    token = get_token(client, unique_username, "Password123")
    resp = client.put(
        "/api/v1/auth/password",
        json={"old_password": "Password123", "new_password": "short"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_change_password_requires_auth(client):
    resp = client.put(
        "/api/v1/auth/password",
        json={"old_password": "x1", "new_password": "whatever123"},
    )
    assert resp.status_code == 401


# ---------- 用户管理模块 ----------

def test_admin_create_station_user(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_resp = client.post(
        "/api/v1/stations",
        json={"name": "用户管理站", "address": "地址", "phone": "010", "allowed_vehicle_types": "small_car", "daily_capacity": 40},
        headers=auth_headers(admin_token),
    )
    station_id = station_resp.json()["id"]
    resp = client.post(
        "/api/v1/users",
        json={"username": "staff_managed", "password": "Password123", "role": "station", "station_id": station_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "station"
    assert data["station_id"] == station_id


def test_create_station_user_without_station_id_rejected(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.post(
        "/api/v1/users",
        json={"username": "staff_orphan", "password": "Password123", "role": "station"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


def test_create_user_short_password_rejected(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.post(
        "/api/v1/users",
        json={"username": "weak_pw_user", "password": "short", "role": "owner"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


def test_list_users_admin_only(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, unique_username)
    owner_token = get_token(client, unique_username)
    resp = client.get("/api/v1/users", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    resp2 = client.get("/api/v1/users", headers=auth_headers(owner_token))
    assert resp2.status_code == 403


def test_get_user_404(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.get("/api/v1/users/99999", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_create_user_duplicate_username(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    create_owner_user(db, unique_username)
    resp = client.post(
        "/api/v1/users",
        json={"username": unique_username, "password": "Password123", "role": "owner"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_get_user_success(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, "owner_get_user")
    resp = client.get(f"/api/v1/users/{owner.id}", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["username"] == owner.username


# ---------- 用户更新 / 删除 ----------

def test_update_user_success(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, unique_username)
    resp = client.put(
        f"/api/v1/users/{owner.id}",
        json={"real_name": "新的姓名", "phone": "18800000000"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["real_name"] == "新的姓名"
    assert data["phone"] == "18800000000"


def test_update_user_role_requires_station_id(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, unique_username)
    resp = client.put(
        f"/api/v1/users/{owner.id}",
        json={"role": "station"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


def test_update_user_station_id_without_station_role_rejected(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = client.post(
        "/api/v1/stations",
        json={"name": "更新检验站", "address": "地址", "phone": "010", "allowed_vehicle_types": "small_car", "daily_capacity": 40},
        headers=auth_headers(admin_token),
    ).json()
    owner = create_owner_user(db, unique_username)
    resp = client.put(
        f"/api/v1/users/{owner.id}",
        json={"station_id": station["id"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


def test_change_station_user_role_clears_station_id(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = client.post(
        "/api/v1/stations",
        json={"name": "角色切换检验站", "address": "地址", "phone": "010", "allowed_vehicle_types": "small_car", "daily_capacity": 40},
        headers=auth_headers(admin_token),
    ).json()
    staff = create_station_user(db, f"staff_{unique_username}", station["id"])
    resp = client.put(
        f"/api/v1/users/{staff.id}",
        json={"role": "owner"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"
    assert resp.json()["station_id"] is None


def test_update_user_404(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.put(
        "/api/v1/users/99999",
        json={"real_name": "不存在"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


def test_update_user_requires_admin(client, db, unique_username):
    admin = create_admin_user(db)
    owner = create_owner_user(db, unique_username)
    owner_token = get_token(client, unique_username)
    resp = client.put(
        f"/api/v1/users/{owner.id}",
        json={"real_name": "越权"},
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 403


def test_delete_user_success(client, db, unique_username):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, unique_username)
    resp = client.delete(f"/api/v1/users/{owner.id}", headers=auth_headers(admin_token))
    assert resp.status_code == 204
    get_resp = client.get(f"/api/v1/users/{owner.id}", headers=auth_headers(admin_token))
    assert get_resp.status_code == 404


def test_delete_admin_protected(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.delete(f"/api/v1/users/{admin.id}", headers=auth_headers(admin_token))
    assert resp.status_code == 400


def test_delete_user_404(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.delete("/api/v1/users/99999", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_delete_user_with_vehicles_conflict(client, db, unique_username, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    owner = create_owner_user(db, unique_username)
    owner_token = get_token(client, unique_username)
    vehicle_resp = client.post(
        "/api/v1/vehicles",
        json={"plate_number": unique_plate, "vehicle_type": "small_car"},
        headers=auth_headers(owner_token),
    )
    assert vehicle_resp.status_code == 201

    resp = client.delete(f"/api/v1/users/{owner.id}", headers=auth_headers(admin_token))
    assert resp.status_code == 409
    assert "无法删除" in resp.json()["detail"]
