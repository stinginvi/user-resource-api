"""user-resource-api 入口。

这里只负责「组装」：创建应用、挂中间件、注册异常处理、接入路由。
具体接口在 app/routers/ 下。
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.db import engine, get_db
from app.errors import AppError, register_error_handlers
from app.logging_conf import setup_logging
from app.routers import auth, notes, users

setup_logging()
logger = logging.getLogger("app.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用关闭时释放连接池。"""
    yield
    await engine.dispose()


app = FastAPI(
    title="user-resource-api",
    description="用户资源服务",
    version="0.1.0",
    lifespan=lifespan,
)
register_error_handlers(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """每个请求打一行日志：方法、路径、状态码、耗时。"""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        # traceback 交给 errors.py 的兜底处理器，这里只记请求本身
        logger.warning("%s %s -> 500 %.1fms", request.method, request.url.path, elapsed)
        raise

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notes.router)


@app.get("/health", summary="存活检查")
async def health():
    """liveness：进程活着就返回 200，不检查依赖。"""
    return {"status": "ok"}


@app.get("/health/ready", summary="就绪检查")
async def readiness(db: AsyncSession = Depends(get_db)):
    """readiness：数据库和 Redis 都可用才返回 200，否则 503。"""
    checks = {}

    # TODO 1：检查数据库
    # 成功：checks["database"] = "ok"
    # 失败：checks["database"] = "error"
    # 提示：await db.execute(text("SELECT 1"))
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # TODO 2：检查 Redis
    # 成功：checks["redis"] = "ok"
    # 失败：checks["redis"] = "error"
    # 提示：await redis_client.ping()
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    if any(v != "ok" for v in checks.values()):
        raise AppError(503, "NOT_READY", f"依赖不可用: {checks}")

    return {"status": "ok", "checks": checks}


@app.get("/")
def root():
    """根路径：告诉访问者这是什么服务、文档在哪。"""
    return {"name": "user-resource-api", "docs": "/docs"}


@app.get("/time")
def server_time():
    """返回服务器当前时间。"""
    return {"time": datetime.now().isoformat()}
