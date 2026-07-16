import json
from datetime import datetime, timedelta
from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.classroom import get_session_public


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _parse_time(value: str | None) -> datetime:
    if not value:
        raise AppError("中断时间不能为空", code="RECOVERY_TIME_REQUIRED")
    normalized = value.replace("T", " ")
    if len(normalized) == 16:
        normalized = f"{normalized}:00"
    return datetime.strptime(normalized[:19], TIME_FORMAT)


def _to_db_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def record_interruption(session_id: int, started_at: str, ended_at: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    get_session_public(session_id)
    start = _parse_time(started_at)
    end = _parse_time(ended_at)
    if end <= start:
        raise AppError("中断结束时间必须晚于开始时间", code="RECOVERY_TIME_INVALID")
    duration = int((end - start).total_seconds())
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recovery_events(session_id, event_type, started_at, ended_at, duration_seconds, details_json)
            VALUES (?, 'interruption', ?, ?, ?, ?)
            """,
            (session_id, _to_db_time(start), _to_db_time(end), duration, json.dumps(details or {}, ensure_ascii=False)),
        )
        row = connection.execute("SELECT * FROM recovery_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
    item = _row_to_dict(row)
    item["details"] = _json_loads(item.pop("details_json", "{}"), {})
    return item


def apply_recovery_action(session_id: int, event_id: int, action: str) -> dict[str, Any]:
    if action not in {"extend_questions", "reopen_sign_in"}:
        raise AppError("恢复处理动作不支持", code="RECOVERY_ACTION_UNSUPPORTED")
    get_session_public(session_id)
    with get_connection() as connection:
        event = connection.execute(
            "SELECT * FROM recovery_events WHERE id = ? AND session_id = ?",
            (event_id, session_id),
        ).fetchone()
        if event is None:
            raise AppError("中断事件不存在", code="RECOVERY_EVENT_NOT_FOUND", status_code=404)
        duration = int(event["duration_seconds"] or 0)
        details: dict[str, Any] = {"source_event_id": event_id, "duration_seconds": duration}
        if action == "extend_questions":
            rows = connection.execute(
                "SELECT id, deadline FROM questions WHERE session_id = ? AND deadline IS NOT NULL",
                (session_id,),
            ).fetchall()
            changed = 0
            for row in rows:
                deadline = _parse_time(row["deadline"])
                new_deadline = deadline + timedelta(seconds=duration)
                connection.execute(
                    "UPDATE questions SET deadline = ?, updated_at = datetime('now') WHERE id = ?",
                    (_to_db_time(new_deadline), row["id"]),
                )
                changed += 1
            details["extended_questions"] = changed
        else:
            session = connection.execute(
                "SELECT actual_started_at, start_time, sign_in_deadline_minutes FROM classroom_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            started = _parse_time(session["actual_started_at"] or session["start_time"])
            current_minutes = int(session["sign_in_deadline_minutes"] or 15)
            new_deadline = started + timedelta(minutes=current_minutes, seconds=duration)
            new_minutes = max(current_minutes, int((new_deadline - started).total_seconds() / 60 + 0.999))
            connection.execute(
                "UPDATE classroom_sessions SET sign_in_deadline_minutes = ?, updated_at = datetime('now') WHERE id = ?",
                (new_minutes, session_id),
            )
            details["sign_in_deadline_minutes"] = new_minutes
        cursor = connection.execute(
            """
            INSERT INTO recovery_events(session_id, event_type, duration_seconds, action_taken, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, action, duration, action, json.dumps(details, ensure_ascii=False)),
        )
        row = connection.execute("SELECT * FROM recovery_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
    item = _row_to_dict(row)
    item["details"] = _json_loads(item.pop("details_json", "{}"), {})
    return item


def record_cached_replay(session_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    get_session_public(session_id)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recovery_events(session_id, event_type, action_taken, details_json)
            VALUES (?, 'cached_request_replayed', 'accepted', ?)
            """,
            (session_id, json.dumps(payload, ensure_ascii=False)),
        )
        row = connection.execute("SELECT * FROM recovery_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
    item = _row_to_dict(row)
    item["details"] = _json_loads(item.pop("details_json", "{}"), {})
    return item


def list_events(session_id: int) -> list[dict[str, Any]]:
    get_session_public(session_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM recovery_events
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (session_id,),
        ).fetchall()
    items = []
    for row in rows:
        item = _row_to_dict(row)
        item["details"] = _json_loads(item.pop("details_json", "{}"), {})
        items.append(item)
    return items
