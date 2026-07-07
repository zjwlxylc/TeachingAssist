from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.classroom import get_session_public
from app.services.realtime import manager


MAX_MESSAGE_LENGTH = 300


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _load_settings(connection: Any, session_id: int) -> dict[str, Any]:
    connection.execute(
        "INSERT OR IGNORE INTO interaction_settings(session_id) VALUES (?)",
        (session_id,),
    )
    row = connection.execute(
        "SELECT session_id, student_messages_enabled, updated_at FROM interaction_settings WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_settings(session_id: int) -> dict[str, Any]:
    get_session_public(session_id)
    with get_connection() as connection:
        return _load_settings(connection, session_id)


async def update_settings(session_id: int, student_messages_enabled: bool) -> dict[str, Any]:
    get_session_public(session_id)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO interaction_settings(session_id, student_messages_enabled)
            VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                student_messages_enabled = excluded.student_messages_enabled,
                updated_at = datetime('now')
            """,
            (session_id, 1 if student_messages_enabled else 0),
        )
        settings = _load_settings(connection, session_id)
    await manager.broadcast(
        session_id,
        {
            "type": "interaction.settings.updated",
            "session_id": session_id,
            "settings": settings,
        },
    )
    return settings


def list_messages(session_id: int, last_message_id: int | None = None) -> list[dict[str, Any]]:
    get_session_public(session_id)
    where = ["session_id = ?", "is_deleted = 0"]
    params: list[Any] = [session_id]
    if last_message_id:
        where.append("id > ?")
        params.append(last_message_id)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, session_id, sender_role, sender_student_id, sender_name,
                   content, is_deleted, created_at, updated_at
            FROM classroom_interaction_messages
            WHERE {' AND '.join(where)}
            ORDER BY id DESC
            LIMIT 200
            """,
            tuple(params),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _validate_content(content: str) -> str:
    value = content.strip()
    if not value:
        raise AppError("留言内容不能为空", code="INTERACTION_CONTENT_REQUIRED")
    if len(value) > MAX_MESSAGE_LENGTH:
        raise AppError("留言内容不能超过 300 字", code="INTERACTION_CONTENT_TOO_LONG")
    return value


def _load_message(connection: Any, message_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT id, session_id, sender_role, sender_student_id, sender_name,
               content, is_deleted, created_at, updated_at
        FROM classroom_interaction_messages
        WHERE id = ?
        """,
        (message_id,),
    ).fetchone()
    if row is None:
        raise AppError("留言不存在", code="INTERACTION_MESSAGE_NOT_FOUND", status_code=404)
    return _row_to_dict(row)


async def publish_teacher_message(session_id: int, content: str, teacher_name: str = "教师") -> dict[str, Any]:
    get_session_public(session_id)
    content = _validate_content(content)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO classroom_interaction_messages(session_id, sender_role, sender_name, content)
            VALUES (?, 'teacher', ?, ?)
            """,
            (session_id, teacher_name.strip() or "教师", content),
        )
        message = _load_message(connection, int(cursor.lastrowid))
    await manager.broadcast(
        session_id,
        {
            "type": "interaction.message.created",
            "session_id": session_id,
            "message": message,
        },
    )
    return message


async def publish_student_message(session_id: int, student_number: str, name: str, content: str) -> dict[str, Any]:
    session = get_session_public(session_id)
    content = _validate_content(content)
    with get_connection() as connection:
        settings = _load_settings(connection, session_id)
        if not bool(settings["student_messages_enabled"]):
            raise AppError("教师已暂停课堂互动", code="INTERACTION_DISABLED", status_code=409)
        student = connection.execute(
            """
            SELECT s.*
            FROM students s
            JOIN course_students cs ON cs.student_id = s.id
            WHERE s.student_id = ?
              AND s.name = ?
              AND cs.course_id = ?
              AND cs.class_id = ?
              AND s.is_active = 1
            """,
            (student_number.strip(), name.strip(), session["course_id"], session["class_id"]),
        ).fetchone()
        if student is None:
            raise AppError("未找到该学号，或姓名不匹配", code="STUDENT_NOT_FOUND", status_code=404)
        sign_in = connection.execute(
            "SELECT status FROM sign_in_records WHERE session_id = ? AND student_id = ?",
            (session_id, student["id"]),
        ).fetchone()
        if sign_in is None or sign_in["status"] not in {"normal", "late"}:
            raise AppError("完成正常或迟到签到后才能参与课堂互动", code="INTERACTION_SIGN_IN_REQUIRED", status_code=409)
        cursor = connection.execute(
            """
            INSERT INTO classroom_interaction_messages(
                session_id, sender_role, sender_student_id, sender_name, content
            )
            VALUES (?, 'student', ?, ?, ?)
            """,
            (session_id, student["id"], name.strip(), content),
        )
        message = _load_message(connection, int(cursor.lastrowid))
    await manager.broadcast(
        session_id,
        {
            "type": "interaction.message.created",
            "session_id": session_id,
            "message": message,
        },
    )
    return message
