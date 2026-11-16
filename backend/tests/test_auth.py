import importlib
import logging

from tests.conftest import auth_headers, get_token, login_user, register_user


def test_register_new_user(client, unique_username):
    resp = register_user(client, unique_username, password="Password123")
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == unique_username
    assert data["role"] == "owner"


def test_register_duplicate_username(client, unique_username):
    register_user(client, unique_username)
    resp = register_user(client, unique_username)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(client, unique_username):
    register_user(client, unique_username, password="Password123")
    resp = login_user(client, unique_username, "Password123")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_rate_limited_after_many_failures(client, unique_username):
    from app import routers as _routers
    _LOGIN_FAILURES = _routers.auth._LOGIN_FAILURES
    _LOGIN_FAILURES.clear()  # 隔离：重置模块级限流状态

    register_user(client, unique_username, password="Password123")
    # 前 5 次失败 → 401
    for _ in range(5):
        resp = login_user(client, unique_username, "WrongPassword")
        assert resp.status_code == 401
    # 第 6 次失败 → 429 触发限流
    resp = login_user(client, unique_username, "WrongPassword")
    assert resp.status_code == 429
    assert "次数过多" in resp.json()["detail"]
    # 正确密码同样被限流拦截（窗口期内）
    resp_ok = login_user(client, unique_username, "Password123")
    assert resp_ok.status_code == 429
    _LOGIN_FAILURES.clear()


def test_login_wrong_password(client, unique_username):
    register_user(client, unique_username, password="Password123")
    resp = login_user(client, unique_username, "WrongPassword")
    assert resp.status_code == 401


def test_get_current_user(client, unique_username):
    register_user(client, unique_username)
    token = get_token(client, unique_username)
    resp = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == unique_username
    assert data["role"] == "owner"


def test_get_current_user_without_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_decode_invalid_token_returns_none():
    from app import auth
    assert auth.decode_access_token("not.a.valid_token") is None


def test_create_access_token_with_custom_expiry():
    from datetime import timedelta
    from jose import jwt as jose_jwt
    from app import auth

    token = auth.create_access_token({"sub": "test_user"}, expires_delta=timedelta(minutes=5))
    payload = jose_jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload.get("sub") == "test_user"
    assert "exp" in payload


def test_get_current_user_garbage_token(client):
    resp = client.get("/api/v1/auth/me", headers=auth_headers("garbage.token.value"))
    assert resp.status_code == 401


def test_get_current_user_missing_sub(client):
    from app import auth
    token = auth.create_access_token({})
    resp = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401


def test_get_current_user_user_not_found(client):
    from app import auth
    token = auth.create_access_token({"sub": "ghost_user_not_exist"})
    resp = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401


def test_secret_key_env_branches(monkeypatch, caplog):
    from app import auth

    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_for_coverage")
    importlib.reload(auth)
    assert auth.SECRET_KEY == "test_secret_key_for_coverage"
    assert "SECRET_KEY 环境变量未设置" not in caplog.text

    monkeypatch.delenv("SECRET_KEY")
    caplog.clear()
    importlib.reload(auth)
    assert isinstance(auth.SECRET_KEY, str) and len(auth.SECRET_KEY) > 0
    assert "SECRET_KEY 环境变量未设置" in caplog.text


def test_bcrypt_about_compatibility_shim(monkeypatch):
    import bcrypt
    from app import auth

    original = getattr(bcrypt, "__about__", None)
    if original is not None:
        monkeypatch.delattr(bcrypt, "__about__")
    try:
        importlib.reload(auth)
        assert hasattr(bcrypt, "__about__")
        assert bcrypt.__about__.__version__ == bcrypt.__version__
    finally:
        if original is not None:
            monkeypatch.setattr(bcrypt, "__about__", original)
