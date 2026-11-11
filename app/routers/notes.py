"""笔记接口：SQLAlchemy ORM 版。

Day 5：加上「只能操作自己的笔记」。
六个 TODO 都是 1–2 行的判断，你来写。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Note, User
from app.schemas import NoteCreate, NoteOut, NotePage, NoteUpdate
from app.security import get_current_user

router = APIRouter(tags=["notes"])


def _ensure_user_exists(db: Session, user_id: int) -> None:
    """父资源不存在时，子集合也不该存在。"""
    if db.get(User, user_id) is None:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")


def _ensure_owner(user_id: int, current_user: User) -> None:
    """不是自己的笔记就拒绝。

    TODO 1：
    - 如果 user_id != current_user.id
    - 就 raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")
    """
    if user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")
    ...


@router.post("/users/{user_id}/notes", status_code=201, response_model=NoteOut)
def create_note(
    user_id: int,
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """给当前用户建一条笔记。"""
    # TODO 2：调用 _ensure_owner(user_id, current_user)
    _ensure_owner(user_id, current_user)
    db_note = Note(user_id=user_id, title=note.title, content=note.content)
    db.add(db_note)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23503":
            raise AppError(404, "USER_NOT_FOUND", "用户不存在") from None
        raise
    db.refresh(db_note)
    return db_note


@router.get("/users/{user_id}/notes", response_model=NotePage)
def list_notes(
    user_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查当前用户的笔记，分页返回。"""
    _ensure_owner(user_id, current_user)
    _ensure_user_exists(db, user_id)

    # TODO 7：查这个用户一共有多少条笔记
    # 提示：select(func.count()).select_from(Note).where(Note.user_id == user_id)
    #       db.scalar(...) 拿结果
    total = db.scalar(select(func.count()).select_from(Note).where(Note.user_id == user_id))

    # TODO 8：查当前页的笔记
    # 提示：select(Note).where(Note.user_id == user_id).order_by(Note.id)
    #       再 .limit(limit).offset(offset)
    #       db.scalars(...).all()
    items = db.scalars(select(Note).where(Note.user_id == user_id).order_by(Note.id).limit(limit).offset(offset)).all()

    return NotePage(items=items, total=total, limit=limit, offset=offset)


@router.get("/notes/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按 id 查一条笔记。"""
    note = db.get(Note, note_id)
    if note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    # TODO 4：如果 note.user_id != current_user.id，raise 403
    if note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")
    return note


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    note: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改笔记。"""
    data = note.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    db_note = db.get(Note, note_id)
    if db_note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    # TODO 5：归属判断，规则同 TODO 4
    if db_note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")

    for field, value in data.items():
        setattr(db_note, field, value)
    db.commit()
    db.refresh(db_note)
    return db_note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除笔记。"""
    db_note = db.get(Note, note_id)
    if db_note is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")

    # TODO 6：归属判断，规则同 TODO 4
    if db_note.user_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "只能操作自己的笔记")

    db.delete(db_note)
    db.commit()
