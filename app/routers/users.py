"""用户接口：SQLAlchemy ORM 异步版。"""

import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete, cache_get, cache_set, redis_client, user_key
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter(tags=["users"])

# 空值缓存的标记：查到 None 时存这个字符串，而不是不存
NULL_MARKER = "__NULL__"


@router.get("/users", response_model=list[UserOut])
async def list_users(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """查用户列表，limit 控制返回条数。"""
    result = await db.execute(select(User).order_by(User.id).limit(limit))
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """按 id 查一个用户：缓存 → 抢锁 → 查库 → 空值缓存。"""
    key = user_key(user_id)

    # 1. 查缓存
    cached = await cache_get(key)
    if cached is not None:
        if cached == NULL_MARKER:
            raise AppError(404, "USER_NOT_FOUND", "用户不存在")
        return UserOut.model_validate_json(cached)

    # 2. 防击穿：抢锁，只有拿到锁的请求去查库
    lock_key = f"lock:{key}"
    if not await redis_client.set(lock_key, "1", nx=True, ex=10):
        await asyncio.sleep(0.1)
        cached = await cache_get(key)
        if cached is not None:
            if cached == NULL_MARKER:
                raise AppError(404, "USER_NOT_FOUND", "用户不存在")
            return UserOut.model_validate_json(cached)

    # 3. 查库
    user = await db.get(User, user_id)
    if user is None:
        # 防穿透：空值也缓存，TTL 短
        await cache_set(key, NULL_MARKER, ttl=60)
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")

    await cache_set(key, UserOut.model_validate(user).model_dump_json())
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """修改用户。只更新客户端真正传了的字段。"""
    data = user.model_dump(exclude_unset=True, exclude_none=True)
    if "username" not in data:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    db_user = await db.get(User, user_id)
    if db_user is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")

    db_user.username = data["username"]
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise AppError(409, "USERNAME_CONFLICT", "用户名已存在") from None
        raise

    await db.refresh(db_user)
    # 写操作后删缓存，下次读自然回填
    await cache_delete(user_key(user_id))
    return db_user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """删除用户，连带删掉他的笔记（数据库外键 CASCADE）。"""
    db_user = await db.get(User, user_id)
    if db_user is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")

    await db.delete(db_user)
    await db.commit()
    await cache_delete(user_key(user_id))
