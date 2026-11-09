"""笔记接口。

归属关系用嵌套路由表达：
- /users/{user_id}/notes  某个用户的笔记
- /notes/{note_id}        单条笔记

W5 加了登录以后，这里会再收紧成「只能操作自己的笔记」。
"""

import psycopg
from fastapi import APIRouter, Depends

from app.db import get_conn
from app.errors import AppError
from app.schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(tags=["notes"])

NOTE_COLUMNS = "id, user_id, title, content, created_at, updated_at"


def ensure_user_exists(conn, user_id: int) -> None:
    """父资源不存在时，子集合也不该存在。"""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        if cur.fetchone() is None:
            raise AppError(404, "USER_NOT_FOUND", "用户不存在")


@router.post("/users/{user_id}/notes", status_code=201, response_model=NoteOut)
def create_note(user_id: int, note: NoteCreate, conn=Depends(get_conn)):
    """给某个用户建一条笔记。"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO notes (user_id, title, content) "
                f"VALUES (%s, %s, %s) RETURNING {NOTE_COLUMNS}",
                (user_id, note.title, note.content),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        raise AppError(404, "USER_NOT_FOUND", "用户不存在") from None


@router.get("/users/{user_id}/notes", response_model=list[NoteOut])
def list_notes(user_id: int, conn=Depends(get_conn)):
    """查某个用户的全部笔记。"""
    ensure_user_exists(conn, user_id)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {NOTE_COLUMNS} FROM notes WHERE user_id = %s ORDER BY id",
            (user_id,),
        )
        return cur.fetchall()


@router.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, conn=Depends(get_conn)):
    """按 id 查一条笔记。"""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {NOTE_COLUMNS} FROM notes WHERE id = %s",
            (note_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")
    return row


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, note: NoteUpdate, conn=Depends(get_conn)):
    """修改笔记，只更新传了的字段，并刷新 updated_at。"""
    data = note.model_dump(exclude_unset=True, exclude_none=True)
    allowed = {"title", "content"}
    cols = [col for col in data if col in allowed]
    if not cols:
        raise AppError(422, "NO_FIELDS_TO_UPDATE", "没有要修改的字段")

    # 列名来自上面的白名单，不是用户输入；值仍然用 %s 传
    set_clause = ", ".join(f"{col} = %s" for col in cols) + ", updated_at = now()"
    values = [data[col] for col in cols] + [note_id]

    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE notes SET {set_clause} WHERE id = %s RETURNING {NOTE_COLUMNS}",
            values,
        )
        row = cur.fetchone()
    conn.commit()

    if row is None:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")
    return row


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, conn=Depends(get_conn)):
    """删除一条笔记。"""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        deleted = cur.rowcount
    conn.commit()

    if deleted == 0:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")
