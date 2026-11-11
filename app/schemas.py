"""请求与响应的数据契约。

原则：输入模型和输出模型分开。
- 输入模型（Create/Update）：客户端能传什么
- 输出模型（Out）：服务端返回什么，多一个字段都不给
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# 用户名规则：3–32 位，只允许字母、数字、下划线、连字符
USERNAME_PATTERN = r"^[a-zA-Z0-9_-]+$"


class UserCreate(BaseModel):
    """注册请求体。id、created_at 由服务端决定；密码只存哈希。"""

    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """PUT /users/{id} 的请求体。全部可选，只改传了的字段。"""

    username: str | None = Field(
        default=None, min_length=3, max_length=32, pattern=USERNAME_PATTERN
    )


class UserOut(BaseModel):
    """所有返回用户的接口都按这个形状说话。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class NoteCreate(BaseModel):
    """POST /users/{user_id}/notes 的请求体。"""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=10000)


class NoteUpdate(BaseModel):
    """PUT /notes/{note_id} 的请求体，字段全部可选。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=10000)


class NoteOut(BaseModel):
    """笔记的对外形状。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class NotePage(BaseModel):
    """分页结果：当前页数据 + 总数 + 分页参数。"""

    items: list[NoteOut]
    total: int
    limit: int
    offset: int


class LoginIn(BaseModel):
    """登录请求体。"""

    username: str
    password: str


class TokenOut(BaseModel):
    """登录成功后返回的 token。"""

    access_token: str
    token_type: str = "bearer"
