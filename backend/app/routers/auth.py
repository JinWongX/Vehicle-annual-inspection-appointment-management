import time
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import schemas, auth, crud
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# 简单的进程内登录限流：key=(ip, username) -> (失败计数, 首次失败时间戳)
# 达到阈值后在窗口内返回 429，缓解暴力破解。多实例部署需改为共享存储（如 Redis）。
_LOGIN_FAILURES: Dict[Tuple[str, str], Tuple[int, float]] = {}
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 900  # 15 分钟


def _check_login_rate_limit(request: Request, username: str):
    client_ip = request.client.host if request.client else "unknown"
    key = (client_ip, username)
    now = time.time()
    record = _LOGIN_FAILURES.get(key)
    if record:
        count, first_ts = record
        if now - first_ts > _LOGIN_WINDOW_SECONDS:
            _LOGIN_FAILURES.pop(key, None)
            count, first_ts = 0, now
        elif count >= _LOGIN_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登录失败次数过多，请 15 分钟后再试",
            )
    return key


def _record_login_failure(key: Tuple[str, str]):
    now = time.time()
    count, first_ts = _LOGIN_FAILURES.get(key, (0, now))
    _LOGIN_FAILURES[key] = (count + 1, first_ts)


def _clear_login_failures(key: Tuple[str, str]):
    _LOGIN_FAILURES.pop(key, None)


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):
    key = _check_login_rate_limit(request, form_data.username)
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        _record_login_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    _clear_login_failures(key)
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserRegister, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    db_user = crud.create_user(
        db,
        schemas.UserCreate(
            username=user.username,
            password=user.password,
            role="owner",
            phone=user.phone,
            real_name=user.real_name,
            station_id=None,
        ),
    )
    return db_user


@router.put("/password", response_model=schemas.UserResponse)
def change_password(
    payload: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if not auth.verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
    current_user.hashed_password = auth.get_password_hash(payload.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user=Depends(auth.get_current_user)):
    return current_user
