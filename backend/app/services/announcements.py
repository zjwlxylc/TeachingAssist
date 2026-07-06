from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.classroom import get_session_public
from app.services.realtime import manager


MAX_CONTENT_LENGTH = 500


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _load_announcement(announcement_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT a.*, s.title AS session_title
            FROM announcements a
            JOIN classroom_sessions s ON s.id = a.session_id
            WHERE a.id = ?
            """,
            (announcement_id,),
        ).fetchone()
    if row is None:
        raise AppError("公告不存在", code="ANNOUNCEMENT_NOT_FOUND", status_code=404)
    return _row_to_dict(row)


def list_announcements(session_id: int, last_message_id: int | None = None, include_deleted: bool = False) -> list[dict[str, Any]]:
    get_session_public(session_id)
    where = ["session_id = ?"]
    params: list[Any] = [session_id]
    if last_message_id:
        where.append("id > ?")
        params.append(last_message_id)
    if not include_deleted:
        where.append("is_deleted = 0")
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, session_id, sender_role, sender_name, content, is_pinned,
                   is_deleted, created_at, updated_at
            FROM announcements
            WHERE {' AND '.join(where)}
            ORDER BY is_pinned DESC, id DESC
            LIMIT 200
            """,
            tuple(params),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


async def publish_announcement(session_id: int, content: str, sender_name: str = "教师") -> dict[str, Any]:
    get_session_public(session_id)
    content = content.strip()
    if not content:
        raise AppError("公告内容不能为空", code="ANNOUNCEMENT_CONTENT_REQUIRED")
    if len(content) > MAX_CONTENT_LENGTH:
        raise AppError("公告内容不能超过 500 字", code="ANNOUNCEMENT_TOO_LONG")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO announcements(session_id, sender_role, sender_name, content)
            VALUES (?, 'teacher', ?, ?)
            """,
            (session_id, sender_name.strip() or "教师", content),
        )
        announcement_id = cursor.lastrowid
    announcement = _load_announcement(int(announcement_id))
    await manager.broadcast(
        session_id,
        {
            "type": "announcement.created",
            "session_id": session_id,
            "announcement": announcement,
        },
    )
    return announcement
