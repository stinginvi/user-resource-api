"""笔记接口：SQLAlchemy ORM 异步版。

归属关系用嵌套路由表达：
- /users/{user_id}/notes  某个用户的笔记
- /notes/{note_id}        单条笔记

权限：只能操作自己的笔记。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import AppError
from app.models import Note, User
from app.schemas import NoteCreate, NoteOut, NotePage, NoteUpdate
from app.security import get_current_user

router = APIRouter(tags=["notes"])


async def _ensure_user_exists(db: AsyncSession, user_id: int) -> None:
    """父资源不存在时，子集合也不该存在。"""
    if await db.get(User, user_id) is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")


def _ensure_owner(user_id: int, current_user: User) -> None:
    """不是自己的笔记就拒绝。"""
    if user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")


@router.post("/users/{user_id}/notes", status_code=201, response_model=NoteOut)
async def create_note(
    user_id: int,
    note: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """给当前用户建一条笔记。"""
    _ensure_owner(user_id, current_user)

    db_note = Note(user_id=user_id, title=note.title, content=note.content)
    db.add(db_note)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23503":
            raise AppError(404, "USER_NOT_FOUND", "用户不存在") from None
        raise

    await db.refresh(db_note)
    return db_note


@router.get("/users/{user_id}/notes", response_model=NotePage)
async def list_notes(
    user_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查当前用户的笔记，分页返回。"""
    _ensure_owner(user_id, current_user)
    await _ensure_user_exists(db, user_id)

    total = await db.scalar(
        select(func.count()).select_from(Note).where(Note.user_id == user_id)
    )

    result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id)
        .order_by(Note.id)
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return NotePage(items=items, total=total, limit=limit, offset=offset)


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按 id 查一条笔记。"""
    note = await db.get(Note, note_id)
    if note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    if note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")
    return note


@router.put("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: int,
    note: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改笔记。"""
    data = note.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    db_note = await db.get(Note, note_id)
    if db_note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    if db_note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")

    for field, value in data.items():
        setattr(db_note, field, value)
    await db.commit()
    await db.refresh(db_note)
    return db_note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除笔记。"""
    db_note = await db.get(Note, note_id)
    if db_note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    if db_note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")

    await db.delete(db_note)
    await db.commit()
