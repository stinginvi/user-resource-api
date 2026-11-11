"""密码哈希与 JWT。

- 密码只存 argon2 哈希，永不存明文
- JWT 的 payload 是可读的 base64，只放用户 id 和过期时间
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("缺少 SECRET_KEY，请检查项目根目录的 .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """校验签名和过期时间，返回用户 id。签名错误或过期会抛 jwt 异常。"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])


# OAuth2PasswordBearer 负责从请求头 "Authorization: Bearer <token>" 里取出 token。
# tokenUrl 只用于 Swagger 的 Authorize 按钮。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """鉴权依赖：token 无效 → 401；有效 → 返回当前用户。"""
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        raise AppError(401, "INVALID_TOKEN", "token 无效或已过期") from None

    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "用户不存在")
    return user
