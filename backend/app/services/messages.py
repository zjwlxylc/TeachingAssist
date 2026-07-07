from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.realtime import message_manager


MAX_MESSAGE_LENGTH = 500


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _validate_content(content: str) -> str:
    value = content.strip()
    if not value:
        raise AppError("私信内容不能为空", code="MESSAGE_CONTENT_REQUIRED")
    if len(value) > MAX_MESSAGE_LENGTH:
        raise AppError(f"私信内容不能超过 {MAX_MESSAGE_LENGTH} 字", code="MESSAGE_CONTENT_TOO_LONG")
    return value


def _lookup_student(connection: Any, student_number: str, name: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT id, student_id, name, class_id FROM students WHERE student_id = ? AND name = ? AND is_active = 1",
        (student_number.strip(), name.strip()),
    ).fetchone()
    return _row_to_dict(row) if row else None


def _load_message(connection: Any, message_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT id, sender_role, sender_student_id, sender_name, receiver_role,
               receiver_student_id, content, is_deleted, read_at, created_at, updated_at
        FROM private_messages
        WHERE id = ?
        """,
        (message_id,),
    ).fetchone()
    if row is None:
        raise AppError("私信不存在", code="MESSAGE_NOT_FOUND", status_code=404)
    return _row_to_dict(row)


async def send_student_message(student_number: str, name: str, content: str) -> dict[str, Any]:
    content = _validate_content(content)
    with get_connection() as connection:
        student = _lookup_student(connection, student_number, name)
        if student is None:
            raise AppError("未找到该学号，或姓名不匹配", code="STUDENT_NOT_FOUND", status_code=404)
        cursor = connection.execute(
            """
            INSERT INTO private_messages(
                sender_role, sender_student_id, sender_name, receiver_role, receiver_student_id, content
            )
            VALUES ('student', ?, ?, 'teacher', NULL, ?)
            """,
            (student["id"], name.strip(), content),
        )
        message = _load_message(connection, int(cursor.lastrowid))
    await message_manager.broadcast("teacher", {"type": "message.created", "message": message})
    return message


async def reply_to_student(student_pk: int, teacher_name: str, content: str) -> dict[str, Any]:
    content = _validate_content(content)
    with get_connection() as connection:
        student = connection.execute(
            "SELECT id, student_id, name FROM students WHERE id = ? AND is_active = 1",
            (student_pk,),
        ).fetchone()
        if student is None:
            raise AppError("学生不存在或已停用", code="STUDENT_NOT_FOUND", status_code=404)
        cursor = connection.execute(
            """
            INSERT INTO private_messages(
                sender_role, sender_student_id, sender_name, receiver_role, receiver_student_id, content
            )
            VALUES ('teacher', NULL, ?, 'student', ?, ?)
            """,
            (teacher_name.strip() or "教师", student["id"], content),
        )
        message = _load_message(connection, int(cursor.lastrowid))
    await message_manager.broadcast(f"student:{student['id']}", {"type": "message.created", "message": message})
    return message


def resolve_student_pk(student_number: str, name: str) -> int:
    with get_connection() as connection:
        student = _lookup_student(connection, student_number, name)
        if student is None:
            raise AppError("未找到该学号，或姓名不匹配", code="STUDENT_NOT_FOUND", status_code=404)
    return int(student["id"])


def list_conversations() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                stu.id AS student_pk,
                stu.student_id AS student_number,
                stu.name AS student_name,
                cls.name AS class_name,
                last_m.content AS last_message,
                last_m.created_at AS last_at,
                agg.unread_count AS unread_count,
                agg.total_count AS total_count
            FROM (
                SELECT
                    CASE
                        WHEN m.sender_role = 'student' THEN m.sender_student_id
                        ELSE m.receiver_student_id
                    END AS sid,
                    MAX(m.id) AS last_id,
                    SUM(CASE WHEN m.receiver_role = 'teacher' AND m.read_at IS NULL THEN 1 ELSE 0 END) AS unread_count,
                    COUNT(*) AS total_count
                FROM private_messages m
                WHERE (m.sender_role = 'student' AND m.sender_student_id IS NOT NULL)
                   OR (m.receiver_role = 'student' AND m.receiver_student_id IS NOT NULL)
                GROUP BY sid
            ) agg
            JOIN students stu ON stu.id = agg.sid
            LEFT JOIN classes cls ON cls.id = stu.class_id
            LEFT JOIN private_messages last_m ON last_m.id = agg.last_id
            ORDER BY agg.last_id DESC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_teacher_thread(student_pk: int) -> dict[str, Any]:
    with get_connection() as connection:
        student = connection.execute(
            "SELECT id, student_id, name FROM students WHERE id = ?", (student_pk,)
        ).fetchone()
        if student is None:
            raise AppError("学生不存在", code="STUDENT_NOT_FOUND", status_code=404)
        connection.execute(
            """
            UPDATE private_messages
            SET read_at = datetime('now'), updated_at = datetime('now')
            WHERE receiver_role = 'teacher' AND sender_student_id = ? AND read_at IS NULL
            """,
            (student_pk,),
        )
        rows = connection.execute(
            """
            SELECT id, sender_role, sender_student_id, sender_name, receiver_role,
                   receiver_student_id, content, is_deleted, read_at, created_at, updated_at
            FROM private_messages
            WHERE (sender_student_id = ? OR receiver_student_id = ?) AND is_deleted = 0
            ORDER BY id ASC
            """,
            (student_pk, student_pk),
        ).fetchall()
    return {
        "student": {"id": student["id"], "student_id": student["student_id"], "name": student["name"]},
        "messages": [_row_to_dict(row) for row in rows],
    }


def get_student_thread(student_pk: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE private_messages
            SET read_at = datetime('now'), updated_at = datetime('now')
            WHERE receiver_role = 'student' AND receiver_student_id = ? AND read_at IS NULL
            """,
            (student_pk,),
        )
        rows = connection.execute(
            """
            SELECT id, sender_role, sender_student_id, sender_name, receiver_role,
                   receiver_student_id, content, is_deleted, read_at, created_at, updated_at
            FROM private_messages
            WHERE (sender_student_id = ? OR receiver_student_id = ?) AND is_deleted = 0
            ORDER BY id ASC
            """,
            (student_pk, student_pk),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_unread_count() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS cnt FROM private_messages WHERE receiver_role = 'teacher' AND read_at IS NULL AND is_deleted = 0"
        ).fetchone()
    return {"unread_count": int(row["cnt"])}
