"""用户接口：SQLAlchemy ORM 版。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserOut])
def list_users(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    """查用户列表，limit 控制返回条数。"""
    return db.scalars(select(User).order_by(User.id).limit(limit)).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """按 id 查一个用户。"""
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """修改用户。只更新客户端真正传了的字段。"""
    data = user.model_dump(exclude_unset=True, exclude_none=True)
    if "username" not in data:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    db_user = db.get(User, user_id)
    if db_user is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")

    db_user.username = data["username"]
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise AppError(409, "USERNAME_CONFLICT", "用户名已存在") from None
        raise
    db.refresh(db_user)
    return db_user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户，连带删掉他的笔记（数据库外键 CASCADE）。"""
    db_user = db.get(User, user_id)
    if db_user is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")

    db.delete(db_user)
    db.commit()
