from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services import ai as ai_service
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
            WHERE s.student_id = ?
              AND s.name = ?
              AND s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?)
              AND s.is_active = 1
            """,
            (student_number.strip(), name.strip(), session["id"]),
        ).fetchone()
        if student is None:
            raise AppError("未找到该学号，或姓名不匹配", code="STUDENT_NOT_FOUND", status_code=404)
        sign_in = connection.execute(
            "SELECT status FROM sign_in_records WHERE session_id = ? AND student_id = ?",
            (session_id, student["id"]),
        ).fetchone()
        if sign_in is None or sign_in["status"] not in {"normal", "late"}:
            raise AppError("完成正常或迟到签到后才能参与课堂互动", code="INTERACTION_SIGN_IN_REQUIRED", status_code=409)

        # 全局开关：课堂互动发言 AI 甄别
        moderation_row = connection.execute(
            "SELECT interaction_moderation_enabled FROM ai_safety_settings WHERE id = 1"
        ).fetchone()
        moderation_enabled = bool(moderation_row["interaction_moderation_enabled"]) if moderation_row else False

        if moderation_enabled:
            try:
                verdict = ai_service.moderate_content(content)
            except AppError as exc:
                if exc.code != "AI_MODERATION_UNAVAILABLE":
                    raise
                # AI 不可用：兜底放行，记降级任务，不阻断课堂
                ai_service.record_failure_task(
                    "interaction_moderation",
                    source_type="student_interaction",
                    source_id=session_id,
                    reason="AI 甄别不可用，跳过发言安全分析，直接放行",
                    payload={"student_id": student["id"], "name": name.strip(), "content": content},
                )
            else:
                if not verdict["safe"]:
                    # 违规：写审核日志(pending)，不入库不上墙，广播给整房，再抛错给学生
                    cursor = connection.execute(
                        """
                        INSERT INTO interaction_moderation_log(
                            session_id, student_id, student_name, content, reason, status
                        )
                        VALUES (?, ?, ?, ?, ?, 'pending')
                        """,
                        (session_id, student["id"], name.strip(), content, verdict.get("reason") or ""),
                    )
                    log_id = int(cursor.lastrowid)
                    await manager.broadcast(
                        session_id,
                        {
                            "type": "interaction.moderated",
                            "session_id": session_id,
                            "log_id": log_id,
                            "student_id": student["id"],
                            "student_name": name.strip(),
                            "content": content,
                            "reason": verdict.get("reason") or "",
                        },
                    )
                    raise AppError(
                        "内容未通过审核，未上墙"
                        + (f"：{verdict['reason']}" if verdict.get("reason") else ""),
                        code="INTERACTION_MODERATED_BLOCKED",
                    )
                # 合规：继续正常入库

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


def list_moderation_logs(session_id: int, status: str | None = None) -> list[dict[str, Any]]:
    get_session_public(session_id)
    where = ["session_id = ?"]
    params: list[Any] = [session_id]
    if status:
        where.append("status = ?")
        params.append(status)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, session_id, student_id, student_name, content, reason, status, reviewed_at, created_at
            FROM interaction_moderation_log
            WHERE {' AND '.join(where)}
            ORDER BY id DESC
            LIMIT 200
            """,
            tuple(params),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


async def review_moderation_log(
    session_id: int, log_id: int, approve: bool, teacher_name: str = "教师"
) -> dict[str, Any]:
    """教师复核被 AI 拦截的发言：approve 则原内容放行上墙，否则标记忽略。"""
    get_session_public(session_id)
    with get_connection() as connection:
        log = connection.execute(
            "SELECT * FROM interaction_moderation_log WHERE id = ? AND session_id = ?",
            (log_id, session_id),
        ).fetchone()
        if log is None:
            raise AppError("审核记录不存在", code="MODERATION_LOG_NOT_FOUND", status_code=404)
        if log["status"] != "pending":
            raise AppError("该记录已处理", code="MODERATION_LOG_ALREADY_REVIEWED", status_code=409)
        new_status = "approved" if approve else "rejected"
        connection.execute(
            "UPDATE interaction_moderation_log SET status = ?, reviewed_at = datetime('now') WHERE id = ?",
            (new_status, log_id),
        )
        message = None
        if approve:
            cursor = connection.execute(
                """
                INSERT INTO classroom_interaction_messages(
                    session_id, sender_role, sender_student_id, sender_name, content
                )
                VALUES (?, 'student', ?, ?, ?)
                """,
                (session_id, log["student_id"], log["student_name"], log["content"]),
            )
            message = _load_message(connection, int(cursor.lastrowid))
    if approve and message is not None:
        await manager.broadcast(
            session_id,
            {
                "type": "interaction.message.created",
                "session_id": session_id,
                "message": message,
            },
        )
    return {"log_id": log_id, "status": new_status, "message": message}
