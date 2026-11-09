"""用户接口：/users 下的增删改查。"""

import psycopg
from fastapi import APIRouter, Depends, Query

from app.db import get_conn
from app.errors import AppError
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["users"])

USER_COLUMNS = "id, username, created_at"


@router.get("/users", response_model=list[UserOut])
def list_users(limit: int = Query(10, ge=1, le=100), conn=Depends(get_conn)):
    """查用户列表，limit 控制返回条数。"""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users ORDER BY id LIMIT %s",
            (limit,),
        )
        return cur.fetchall()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, conn=Depends(get_conn)):
    """按 id 查一个用户。"""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    return row


@router.post("/users", status_code=201, response_model=UserOut)
def create_user(user: UserCreate, conn=Depends(get_conn)):
    """新建用户。唯一约束由数据库兜底，冲突时返回 409。"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO users (username) VALUES (%s) RETURNING {USER_COLUMNS}",
                (user.username,),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise AppError(409, "USERNAME_CONFLICT", "用户名已存在") from None


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user: UserUpdate, conn=Depends(get_conn)):
    """修改用户。只更新客户端真正传了的字段。"""
    data = user.model_dump(exclude_unset=True, exclude_none=True)
    if "username" not in data:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET username = %s WHERE id = %s RETURNING {USER_COLUMNS}",
                (data["username"], user_id),
            )
            row = cur.fetchone()
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise AppError(409, "USERNAME_CONFLICT", "用户名已存在") from None

    if row is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    return row


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, conn=Depends(get_conn)):
    """删除用户，连带删掉他的笔记（数据库外键 CASCADE）。"""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        deleted = cur.rowcount
    conn.commit()

    if deleted == 0:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
