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
        "name": "报告检测站",
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


def _create_appointment(client, owner_token, vehicle_id: int, station_id: int, days_ahead: int = 5):
    payload = {
        "vehicle_id": vehicle_id,
        "station_id": station_id,
        "appointment_date": (date.today() + timedelta(days=days_ahead)).isoformat(),
        "time_slot": "08:00-10:00",
    }
    return client.post("/api/v1/appointments", json=payload, headers=auth_headers(owner_token))


def _checkin_appointment(client, station_token, appointment_id: int):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/checkin",
        headers=auth_headers(station_token),
    )


def _create_report(client, station_token, appointment_id: int, result: str = "pass"):
    payload = {
        "appointment_id": appointment_id,
        "result": result,
        "overall_comment": "测试报告",
        "items": [
            {"item_name": "制动性能", "result": "pass", "comment": "正常"},
            {"item_name": "灯光", "result": "pass" if result == "pass" else "fail", "comment": "正常" if result == "pass" else "亮度不足"},
            {"item_name": "尾气排放", "result": "pass", "comment": "达标"},
        ],
    }
    return client.post("/api/v1/reports", json=payload, headers=auth_headers(station_token))


def test_create_report_and_sticker(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_report")
    owner_token = get_token(client, "owner_report")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    station_user = create_station_user(db, "staff_report", station["id"])
    station_token = get_token(client, "staff_report")

    _checkin_appointment(client, station_token, appt["id"])

    resp = _create_report(client, station_token, appt["id"], result="pass")
    assert resp.status_code == 201
    data = resp.json()
    assert data["result"] == "pass"
    assert len(data["items"]) == 3
    assert data["sticker_code"].startswith("VIC-")
    assert unique_plate in data["sticker_code"]


def test_create_report_duplicate(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_report_dup")
    owner_token = get_token(client, "owner_report_dup")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    station_user = create_station_user(db, "staff_report_dup", station["id"])
    station_token = get_token(client, "staff_report_dup")
    _checkin_appointment(client, station_token, appt["id"])

    resp1 = _create_report(client, station_token, appt["id"])
    assert resp1.status_code == 201
    resp2 = _create_report(client, station_token, appt["id"])
    assert resp2.status_code == 400


def test_create_report_requires_checking_status(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_report_order")
    owner_token = get_token(client, "owner_report_order")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    station_user = create_station_user(db, "staff_order", station["id"])
    station_token = get_token(client, "staff_order")

    # 未到站登记（booked 状态）不允许录入报告
    resp = _create_report(client, station_token, appt["id"])
    assert resp.status_code == 400
    assert "checking" in resp.json()["detail"]


def test_report_completion_updates_appointment_status(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_report_done")
    owner_token = get_token(client, "owner_report_done")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"]).json()
    station_user = create_station_user(db, "staff_done", station["id"])
    station_token = get_token(client, "staff_done")
    _checkin_appointment(client, station_token, appt["id"])

    resp = _create_report(client, station_token, appt["id"])
    assert resp.status_code == 201
    # 报告录入后预约应自动流转为 completed
    assert resp.json()["appointment"]["status"] == "completed"

    # 车辆可再次预约（复检场景）
    resp2 = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=10)
    assert resp2.status_code == 201

    # 响应应包含嵌套的预约/车辆/检测站信息
    data = resp.json()
    assert data["appointment"]["vehicle"]["plate_number"] == unique_plate
    assert data["appointment"]["station"]["name"] == "报告检测站"


def test_statistics(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_stats")
    owner_token = get_token(client, "owner_stats")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=1).json()
    station_user = create_station_user(db, "staff_stats", station["id"])
    station_token = get_token(client, "staff_stats")
    _checkin_appointment(client, station_token, appt["id"])
    _create_report(client, station_token, appt["id"], result="fail")

    start = date.today()
    end = date.today() + timedelta(days=30)
    resp = client.get(
        "/api/v1/reports/statistics",
        params={"start_date": start.isoformat(), "end_date": end.isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["pass_count"] == 0
    assert data["fail_count"] == 1
    assert data["retest_count"] == 0
    assert data["pass_rate"] == 0.0
    assert "灯光" in data["fail_reasons"]


def test_export_excel(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_excel")
    owner_token = get_token(client, "owner_excel")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=1).json()
    station_user = create_station_user(db, "staff_excel", station["id"])
    station_token = get_token(client, "staff_excel")
    _checkin_appointment(client, station_token, appt["id"])
    _create_report(client, station_token, appt["id"])

    start = date.today()
    end = date.today() + timedelta(days=30)
    resp = client.get(
        "/api/v1/reports/export",
        params={"format": "excel", "start_date": start.isoformat(), "end_date": end.isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(resp.content) > 0


def test_export_csv(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_csv")
    owner_token = get_token(client, "owner_csv")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=1).json()
    station_user = create_station_user(db, "staff_csv", station["id"])
    station_token = get_token(client, "staff_csv")
    _checkin_appointment(client, station_token, appt["id"])
    _create_report(client, station_token, appt["id"])

    start = date.today()
    end = date.today() + timedelta(days=30)
    resp = client.get(
        "/api/v1/reports/export",
        params={"format": "csv", "start_date": start.isoformat(), "end_date": end.isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.content.decode("utf-8-sig")
    assert "车牌" in content
    assert unique_plate in content


def _setup_report(client, db, unique_plate, owner_key, staff_key, result="pass", station_kwargs=None, admin_token=None):
    if admin_token is None:
        admin = create_admin_user(db)
        admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token, **(station_kwargs or {})).json()

    owner = create_owner_user(db, owner_key)
    owner_token = get_token(client, owner_key)
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()

    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=1).json()
    staff = create_station_user(db, staff_key, station["id"])
    staff_token = get_token(client, staff_key)
    _checkin_appointment(client, staff_token, appt["id"])
    report_resp = _create_report(client, staff_token, appt["id"], result=result)
    assert report_resp.status_code == 201
    report = report_resp.json()
    return admin_token, owner_token, staff_token, station, appt, report


def test_create_report_appointment_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()
    staff = create_station_user(db, "staff_anf", station["id"])
    staff_token = get_token(client, "staff_anf")
    resp = client.post(
        "/api/v1/reports",
        json={"appointment_id": 9999, "result": "pass", "items": []},
        headers=auth_headers(staff_token),
    )
    assert resp.status_code == 404


def test_create_report_wrong_station_forbidden(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token, name="站A_report").json()
    station_b = _create_station(client, admin_token, name="站B_report").json()

    owner = create_owner_user(db, "owner_wrong_report")
    owner_token = get_token(client, "owner_wrong_report")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"]).json()

    staff_b = create_station_user(db, "staff_b_report", station_b["id"])
    staff_b_token = get_token(client, "staff_b_report")
    _checkin_appointment(client, staff_b_token, appt["id"])
    resp = client.post(
        "/api/v1/reports",
        json={"appointment_id": appt["id"], "result": "pass", "items": []},
        headers=auth_headers(staff_b_token),
    )
    assert resp.status_code == 403


def test_statistics_station_filter(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")

    plate_a = f"{unique_plate[:3]}A{unique_plate[4:]}"
    _, _, _, station_a, _, _ = _setup_report(
        client, db, plate_a, "owner_stat_a", "staff_stat_a", admin_token=admin_token
    )
    plate_b = f"{unique_plate[:3]}B{unique_plate[4:]}"
    _setup_report(client, db, plate_b, "owner_stat_b", "staff_stat_b", admin_token=admin_token)

    start = date.today()
    end = date.today() + timedelta(days=30)
    resp = client.get(
        "/api/v1/reports/statistics",
        params={"start_date": start.isoformat(), "end_date": end.isoformat(), "station_id": station_a["id"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 1


def test_statistics_invalid_date_range(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.get(
        "/api/v1/reports/statistics",
        params={"start_date": "2026-01-10", "end_date": "2026-01-01"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "later than" in resp.json()["detail"]


def test_export_invalid_date_range(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.get(
        "/api/v1/reports/export",
        params={"format": "csv", "start_date": "2026-01-10", "end_date": "2026-01-01"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "later than" in resp.json()["detail"]


def test_list_reports_owner_scope_and_fail_sticker_empty(client, db, unique_plate):
    _, owner_token, _, _, _, report = _setup_report(
        client, db, unique_plate, "owner_list_scope", "staff_list_scope", result="fail"
    )
    resp = client.get("/api/v1/reports", headers=auth_headers(owner_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == report["id"]
    assert data[0]["sticker_code"] == ""


def test_list_reports_station_scope(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")

    _, _, staff_token, _, _, report = _setup_report(
        client, db, unique_plate, "owner_station_scope", "staff_station_scope", admin_token=admin_token
    )
    # 另一名车主在另一检测站产生报告
    other_plate = f"{unique_plate[:3]}X{unique_plate[4:]}"
    _setup_report(client, db, other_plate, "owner_other_scope", "staff_other_scope", admin_token=admin_token)

    resp = client.get("/api/v1/reports", headers=auth_headers(staff_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == report["id"]

    # admin 可查看全部
    resp_admin = client.get("/api/v1/reports", headers=auth_headers(admin_token))
    assert resp_admin.status_code == 200
    assert len(resp_admin.json()) == 2


def test_get_report_detail_success(client, db, unique_plate):
    _, owner_token, _, _, _, report = _setup_report(
        client, db, unique_plate, "owner_detail", "staff_detail"
    )
    resp = client.get(f"/api/v1/reports/{report['id']}", headers=auth_headers(owner_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == report["id"]
    assert data["sticker_code"].startswith("VIC-")


def test_get_report_not_found(client, db):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    resp = client.get("/api/v1/reports/9999", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_owner_cannot_view_other_report(client, db, unique_plate):
    _, owner_token, _, _, _, _ = _setup_report(
        client, db, unique_plate, "owner_report_privacy", "staff_report_privacy"
    )
    other_owner = create_owner_user(db, "other_owner_report")
    other_owner_token = get_token(client, "other_owner_report")
    resp = client.get("/api/v1/reports", headers=auth_headers(other_owner_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_station_cannot_view_other_station_report_detail(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station_a = _create_station(client, admin_token, name="站A_detail").json()
    station_b = _create_station(client, admin_token, name="站B_detail").json()

    owner = create_owner_user(db, "owner_cross_detail")
    owner_token = get_token(client, "owner_cross_detail")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station_a["id"], days_ahead=1).json()

    staff_a = create_station_user(db, "staff_a_detail", station_a["id"])
    staff_a_token = get_token(client, "staff_a_detail")
    _checkin_appointment(client, staff_a_token, appt["id"])
    report = _create_report(client, staff_a_token, appt["id"]).json()

    staff_b = create_station_user(db, "staff_b_detail", station_b["id"])
    staff_b_token = get_token(client, "staff_b_detail")
    resp = client.get(f"/api/v1/reports/{report['id']}", headers=auth_headers(staff_b_token))
    assert resp.status_code == 403


def test_owner_cannot_view_other_report_detail(client, db, unique_plate):
    _, owner_token, _, _, _, report = _setup_report(
        client, db, unique_plate, "owner_privacy_detail", "staff_privacy_detail"
    )
    other_owner = create_owner_user(db, "other_owner_detail")
    other_owner_token = get_token(client, "other_owner_detail")
    resp = client.get(f"/api/v1/reports/{report['id']}", headers=auth_headers(other_owner_token))
    assert resp.status_code == 403


def test_create_report_duplicate_in_checking_status(client, db, unique_plate):
    admin = create_admin_user(db)
    admin_token = get_token(client, admin.username, "admin123")
    station = _create_station(client, admin_token).json()

    owner = create_owner_user(db, "owner_dup_checking")
    owner_token = get_token(client, "owner_dup_checking")
    vehicle = _create_vehicle(client, owner_token, unique_plate).json()
    appt = _create_appointment(client, owner_token, vehicle["id"], station["id"], days_ahead=1).json()

    staff = create_station_user(db, "staff_dup_checking", station["id"])
    staff_token = get_token(client, "staff_dup_checking")
    _checkin_appointment(client, staff_token, appt["id"])
    resp1 = _create_report(client, staff_token, appt["id"])
    assert resp1.status_code == 201

    # 通过 admin 将预约重置为 checking，使第二次请求同时命中 checking 与重复报告分支
    client.put(
        f"/api/v1/appointments/{appt['id']}",
        json={"status": "checking"},
        headers=auth_headers(admin_token),
    )
    resp2 = _create_report(client, staff_token, appt["id"])
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]
