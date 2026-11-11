"""数据库：Engine + Session。

SQLAlchemy 自带连接池，不再需要手写 psycopg_pool。
一个请求一个 Session，请求结束自动 close。
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("缺少 DATABASE_URL，请检查项目根目录的 .env")

# SQLAlchemy 需要一个驱动名：postgresql+psycopg 表示用 psycopg 3
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,        # 常驻连接
    max_overflow=10,    # 高峰期最多再借 10 条
    pool_pre_ping=True, # 借出前先探活，避免用到已断开的连接
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,  # commit 后对象属性仍可读，不需要再查一次
)


def get_db():
    """FastAPI 依赖：每个请求一个 Session，用完关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
