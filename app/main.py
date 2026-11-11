"""user-resource-api 入口。

这里只负责「组装」：创建应用、挂中间件、注册异常处理、接入路由。
具体接口在 app/routers/ 下。
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request

from app.db import engine
from app.errors import register_error_handlers
from app.logging_conf import setup_logging
from app.routers import auth, notes, users

setup_logging()
logger = logging.getLogger("app.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用关闭时释放连接池。"""
    yield
    engine.dispose()


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


@app.get("/health", summary="健康检查")
def health():
    """健康检查：服务活着就返回 ok。"""
    return {"status": "ok"}


@app.get("/")
def root():
    """根路径：告诉访问者这是什么服务、文档在哪。"""
    return {"name": "user-resource-api", "docs": "/docs"}


@app.get("/time")
def server_time():
    """返回服务器当前时间。"""
    return {"time": datetime.now().isoformat()}
