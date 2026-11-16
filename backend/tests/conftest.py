import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 将 backend 目录加入 Python 路径，使 app 模块可导入
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 使用独立测试数据库，避免污染生产数据库
TEST_DB_PATH = Path(__file__).parent / "test_vehicle_inspection.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# 必须在设置 DATABASE_URL 之后导入应用，否则 database 模块会使用生产库
from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """在测试会话开始时创建表，结束时清理测试数据库文件。"""
    # 如存在上次未清理的测试数据库文件，先删除以保证测试会话独立
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # 释放连接池后再删除文件，避免 Windows 下文件被占用
    engine.dispose()
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db():
    """每个测试函数开始时重置表数据，返回数据库 session。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """提供 FastAPI TestClient，数据库已重置。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def unique_username():
    return f"user_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def unique_plate():
    return f"鲁A{uuid.uuid4().hex[:5].upper()}"


# ---------- 便捷函数 ----------

def register_user(client: TestClient, username: str, password: str = "password123", **kwargs):
    payload = {"username": username, "password": password, **kwargs}
    return client.post("/api/v1/auth/register", json=payload)


def login_user(client: TestClient, username: str, password: str = "password123"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def get_token(client: TestClient, username: str, password: str = "password123") -> str:
    resp = login_user(client, username, password)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_admin_user(db, username: str = "admin", password: str = "admin123"):
    from app import auth, crud, schemas

    return crud.create_user(
        db,
        schemas.UserCreate(
            username=username,
            password=password,
            role="admin",
            phone="13800000000",
            real_name="管理员",
        ),
    )


def create_owner_user(db, username: str, password: str = "password123"):
    from app import crud, schemas

    return crud.create_user(
        db,
        schemas.UserCreate(
            username=username,
            password=password,
            role="owner",
            phone="13900000000",
            real_name="车主",
        ),
    )


def create_station_user(db, username: str, station_id: int, password: str = "password123"):
    from app import crud, schemas

    return crud.create_user(
        db,
        schemas.UserCreate(
            username=username,
            password=password,
            role="station",
            phone="13700000000",
            real_name="检测员",
            station_id=station_id,
        ),
    )
