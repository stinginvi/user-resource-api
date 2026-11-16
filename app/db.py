"""数据库：异步 Engine + AsyncSession。

Day 4 起全部走异步：
- 驱动从 psycopg 换成 asyncpg
- Session 换成 AsyncSession
- 所有数据库操作都要 await
"""

import os
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("缺少 DATABASE_URL，请检查项目根目录的 .env")

# 统一成异步驱动名
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每个请求一个 AsyncSession。"""
    async with SessionLocal() as session:
        yield session
