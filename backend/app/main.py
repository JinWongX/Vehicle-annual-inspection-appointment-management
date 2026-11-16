import logging
import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from .routers import auth, users, stations, vehicles, appointments, reports
from .database import engine, Base

logger = logging.getLogger(__name__)

# CORS 白名单：默认仅允许本地开发前端来源，生产环境通过 CORS_ORIGINS 环境变量配置。
# 使用 Bearer Token 鉴权（非 Cookie），无需 allow_credentials=True；
# 通配符 "*" 与 credentials=True 同时使用违反 CORS 规范，已移除。
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]


def create_application() -> FastAPI:
    application = FastAPI(
        title="车辆年检预约管理系统",
        description="Vehicle Annual Inspection Appointment Management System API",
        version="1.0.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(stations.router, prefix="/api/v1")
    application.include_router(vehicles.router, prefix="/api/v1")
    application.include_router(appointments.router, prefix="/api/v1")
    application.include_router(reports.router, prefix="/api/v1")

    # 统一异常处理：数据库唯一/外键冲突 → 400（不暴露堆栈），其他未知异常 → 500 通用信息
    @application.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("IntegrityError on %s: %s", request.url.path, exc.orig)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "数据冲突或违反唯一约束，请检查提交内容"},
        )

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "服务器内部错误，请稍后重试"},
        )

    return application


app = create_application()


@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
