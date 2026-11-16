"""
车辆年检预约管理系统端到端跑批脚本。

独立启动 FastAPI 服务（使用独立测试数据库），模拟完整业务流程，
最后输出跑批成功/失败结果。
"""

import atexit
import os
import subprocess
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path

import httpx

# ---------- 路径与测试数据库配置 ----------

SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
TEST_DB_PATH = SCRIPT_DIR / "batch_vehicle_inspection.db"

sys.path.insert(0, str(BACKEND_DIR))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.auth import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402

API_BASE = "http://127.0.0.1:8000"
API_TIMEOUT = 10

PASS = True
FAIL = False


# ---------- 工具函数 ----------

def log_step(step_no: int, desc: str, ok: bool, detail: str = ""):
    status = "✅ 成功" if ok else "❌ 失败"
    print(f"[步骤 {step_no}] {desc}: {status}")
    if detail:
        print(f"         详情: {detail}")
    return ok


def kill_process_on_port(port: int = 8000):
    """清理占用指定端口的残留进程，确保跑批可独立运行。"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pid = result.stdout.strip()
        if pid and pid.isdigit():
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, timeout=5)
            print(f"已终止占用 {port} 端口的进程 {pid}")
            time.sleep(1)
    except Exception:
        pass


def ensure_admin_exists():
    """在测试数据库中创建默认管理员账号。"""
    # 每次跑批前清理旧测试数据库，确保结果可复现
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except Exception as e:
        print(f"警告：无法删除旧测试数据库: {e}")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                phone="",
                real_name="管理员",
                station_id=None,
            )
            db.add(admin)
            db.commit()
            print("已创建默认管理员: admin / admin123")
        else:
            print("默认管理员已存在")
    finally:
        db.close()


def start_server():
    """启动后端服务子进程，使用测试数据库。"""
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def stop():
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    atexit.register(stop)

    # 等待服务就绪
    print("等待后端服务启动...")
    for i in range(30):
        try:
            r = httpx.get(f"{API_BASE}/health", timeout=1)
            if r.status_code == 200:
                print("后端服务已就绪")
                return proc
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("后端服务启动失败")


def register_owner(session: httpx.Client, username: str, password: str):
    resp = session.post(
        f"{API_BASE}/api/v1/auth/register",
        json={"username": username, "password": password, "phone": "13800138000", "real_name": "车主"},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def login(session: httpx.Client, username: str, password: str):
    resp = session.post(
        f"{API_BASE}/api/v1/auth/login",
        data={"username": username, "password": password},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    return token


def create_station(session: httpx.Client, name: str, allowed_types: str, capacity: int):
    payload = {
        "name": name,
        "address": "跑批测试路 1 号",
        "phone": "010-12345678",
        "allowed_vehicle_types": allowed_types,
        "daily_capacity": capacity,
    }
    resp = session.post(f"{API_BASE}/api/v1/stations", json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def register_vehicle(session: httpx.Client, plate_number: str):
    payload = {
        "plate_number": plate_number,
        "vehicle_type": "small_car",
        "register_date": (date.today() - timedelta(days=365 * 2)).isoformat(),
        "usage_nature": "non_operational",
    }
    resp = session.post(f"{API_BASE}/api/v1/vehicles", json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def query_available_stations(session: httpx.Client, vehicle_type: str, target_date: date):
    resp = session.get(
        f"{API_BASE}/api/v1/stations/available",
        params={"vehicle_type": vehicle_type, "date": target_date.isoformat()},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def create_appointment(session: httpx.Client, vehicle_id: int, station_id: int, target_date: date, time_slot: str):
    payload = {
        "vehicle_id": vehicle_id,
        "station_id": station_id,
        "appointment_date": target_date.isoformat(),
        "time_slot": time_slot,
    }
    resp = session.post(f"{API_BASE}/api/v1/appointments", json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def create_station_staff(session: httpx.Client, username: str, station_id: int, password: str):
    payload = {
        "username": username,
        "password": password,
        "role": "station",
        "phone": "13700137000",
        "real_name": "检测站工作人员",
        "station_id": station_id,
    }
    resp = session.post(f"{API_BASE}/api/v1/users", json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def checkin_appointment(session: httpx.Client, appointment_id: int):
    resp = session.post(
        f"{API_BASE}/api/v1/appointments/{appointment_id}/checkin",
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def create_inspection_report(session: httpx.Client, appointment_id: int):
    payload = {
        "appointment_id": appointment_id,
        "result": "fail",
        "overall_comment": "跑批检测：灯光不合格，其余项目合格",
        "items": [
            {"item_name": "制动性能", "result": "pass", "comment": "合格"},
            {"item_name": "灯光", "result": "fail", "comment": "亮度不足"},
            {"item_name": "尾气排放", "result": "pass", "comment": "达标"},
        ],
    }
    resp = session.post(f"{API_BASE}/api/v1/reports", json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_report(session: httpx.Client, report_id: int):
    resp = session.get(f"{API_BASE}/api/v1/reports/{report_id}", timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_statistics(session: httpx.Client, start_date: date, end_date: date):
    resp = session.get(
        f"{API_BASE}/api/v1/reports/statistics",
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def export_reports(session: httpx.Client, file_format: str, start_date: date, end_date: date):
    resp = session.get(
        f"{API_BASE}/api/v1/reports/export",
        params={"format": file_format, "start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("content-type", "")


# ---------- 主流程 ----------

def main():
    print("=" * 60)
    print("车辆年检预约管理系统 - 端到端跑批脚本")
    print("=" * 60)

    kill_process_on_port(8000)
    ensure_admin_exists()
    server_proc = start_server()

    results = []
    owner_session = httpx.Client(follow_redirects=True)
    admin_session = httpx.Client(follow_redirects=True)
    staff_session = httpx.Client(follow_redirects=True)

    try:
        # 1. 注册车主账号并登录
        owner_name = f"batch_owner_{int(time.time())}"
        owner_password = "Owner@123"
        register_owner(owner_session, owner_name, owner_password)
        login(owner_session, owner_name, owner_password)
        results.append(log_step(1, "注册车主账号并登录", PASS, f"用户名: {owner_name}"))

        # 2. 管理员登录并创建检测站
        login(admin_session, "admin", "admin123")
        station = create_station(admin_session, "跑批检测站", "small_car", 40)
        station_id = station["id"]
        results.append(log_step(2, "管理员登录并创建检测站", PASS, f"站点 ID: {station_id}"))

        # 3. 车主登记车辆
        plate = f"鲁A{int(time.time()) % 100000:05d}"
        vehicle = register_vehicle(owner_session, plate)
        vehicle_id = vehicle["id"]
        results.append(log_step(3, "车主登记车辆", PASS, f"车牌: {plate}, 车辆 ID: {vehicle_id}"))

        # 4. 查询可约检测站与时段
        target_date = date.today() + timedelta(days=5)
        available = query_available_stations(owner_session, "small_car", target_date)
        assert len(available) > 0, "未找到可预约检测站"
        selected_station = available[0]["station"]
        selected_slot = available[0]["time_slots"][0]["time_slot"]
        results.append(
            log_step(
                4,
                "查询可约检测站与时段",
                PASS,
                f"站点: {selected_station['name']}, 时段: {selected_slot}, 日期: {target_date}",
            )
        )

        # 5. 提交预约
        appointment = create_appointment(owner_session, vehicle_id, station_id, target_date, selected_slot)
        appointment_id = appointment["id"]
        results.append(
            log_step(5, "提交预约", PASS, f"预约 ID: {appointment_id}, 状态: {appointment['status']}")
        )

        # 6. 创建检测站工作人员账号并登录
        staff_name = f"batch_staff_{int(time.time())}"
        staff_password = "Staff@123"
        create_station_staff(admin_session, staff_name, station_id, staff_password)
        login(staff_session, staff_name, staff_password)
        results.append(log_step(6, "创建检测站工作人员账号并登录", PASS, f"用户名: {staff_name}"))

        # 7. 到站登记
        checked_in = checkin_appointment(staff_session, appointment_id)
        results.append(log_step(7, "到站登记", PASS, f"状态: {checked_in['status']}"))

        # 8. 录入检测结果（含 pass/fail 检测项）
        report = create_inspection_report(staff_session, appointment_id)
        results.append(
            log_step(
                8,
                "录入检测结果",
                PASS,
                f"报告 ID: {report['id']}, 结果: {report['result']}, 检测项数: {len(report['items'])}",
            )
        )

        # 9. 查看检测报告
        viewed_report = get_report(staff_session, report["id"])
        results.append(
            log_step(9, "查看检测报告", PASS, f"合格标志: {viewed_report.get('sticker_code') or '无'}")
        )

        # 10. 查询统计报表
        start = date.today()
        end = date.today() + timedelta(days=30)
        stats = get_statistics(admin_session, start, end)
        results.append(
            log_step(
                10,
                "查询统计报表",
                PASS,
                f"总数: {stats['total_count']}, 合格: {stats['pass_count']}, "
                f"不合格: {stats['fail_count']}, 合格率: {stats['pass_rate']:.2f}%",
            )
        )

        # 11. 导出 Excel
        excel_bytes, excel_ct = export_reports(admin_session, "excel", start, end)
        results.append(
            log_step(11, "导出 Excel", PASS, f"大小: {len(excel_bytes)} bytes, Content-Type: {excel_ct}")
        )

        # 12. 导出 CSV
        csv_bytes, csv_ct = export_reports(admin_session, "csv", start, end)
        results.append(
            log_step(12, "导出 CSV", PASS, f"大小: {len(csv_bytes)} bytes, Content-Type: {csv_ct}")
        )

    except Exception as e:
        results.append(log_step(len(results) + 1, f"流程执行", FAIL, str(e)))
        traceback.print_exc()

    # 清理：关闭会话、停止服务、删除测试数据库
    owner_session.close()
    admin_session.close()
    staff_session.close()
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()

    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except Exception:
        pass

    print("=" * 60)
    if all(results):
        print("🎉 跑批成功：所有步骤均通过")
        return 0
    else:
        passed = sum(results)
        total = len(results)
        print(f"⚠️ 跑批失败：共 {total} 步，通过 {passed} 步，失败 {total - passed} 步")
        return 1


if __name__ == "__main__":
    sys.exit(main())
