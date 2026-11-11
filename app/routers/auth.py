"""注册与登录。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas import TokenOut, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """注册：只保存密码哈希。"""
    db_user = User(
        username=user.username,
        password_hash=hash_password(user.password),
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise AppError(409, "USERNAME_CONFLICT", "用户名已存在") from None
        raise
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """登录：用表单提交（Swagger 的 Authorize 按钮要求这种格式）。

    用户名或密码错误都返回同一个 401，避免泄露「用户名是否存在」。
    """
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "用户名或密码错误")

    return TokenOut(access_token=create_access_token(user.id))
