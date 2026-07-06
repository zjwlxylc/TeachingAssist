from datetime import datetime, timedelta
from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.backup import create_backup


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _now() -> datetime:
    return datetime.now()


def _to_db_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("T", " ")
    if len(normalized) == 16:
        normalized = f"{normalized}:00"
    return datetime.strptime(normalized[:19], TIME_FORMAT)


def _load_session(connection: Any, session_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT s.*, c.name AS course_name, cl.name AS class_name
        FROM classroom_sessions s
        JOIN courses c ON c.id = s.course_id
        JOIN classes cl ON cl.id = s.class_id
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        raise AppError("课堂不存在", code="SESSION_NOT_FOUND", status_code=404)
    return _row_to_dict(row)


def _roster_count(connection: Any, session: dict[str, Any]) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM course_students
        WHERE course_id = ? AND class_id = ?
        """,
        (session["course_id"], session["class_id"]),
    ).fetchone()
    return int(row["total"] if row else 0)


def _start_session_in_connection(connection: Any, session: dict[str, Any], started_at: datetime) -> None:
    if session["status"] == "ended":
        return
    if _roster_count(connection, session) <= 0:
        return
    connection.execute(
        """
        UPDATE classroom_sessions
        SET status = 'active',
            actual_started_at = COALESCE(actual_started_at, ?),
            updated_at = datetime('now')
        WHERE id = ? AND status = 'pending'
        """,
        (_to_db_time(started_at), session["id"]),
    )


def _end_session_in_connection(connection: Any, session: dict[str, Any], ended_at: datetime, ended_by: str) -> None:
    if session["status"] == "ended":
        return
    connection.execute(
        """
        UPDATE classroom_sessions
        SET status = 'ended',
            actual_ended_at = COALESCE(actual_ended_at, ?),
            ended_by = COALESCE(ended_by, ?),
            updated_at = datetime('now')
        WHERE id = ? AND status <> 'ended'
        """,
        (_to_db_time(ended_at), ended_by, session["id"]),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO sign_in_records(session_id, student_id, status)
        SELECT ?, cs.student_id, 'absent'
        FROM course_students cs
        WHERE cs.course_id = ? AND cs.class_id = ?
        """,
        (session["id"], session["course_id"], session["class_id"]),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO evaluation_tasks(session_id, status, notes)
        VALUES (?, 'pending', 'Initialized after classroom ended')
        """,
        (session["id"],),
    )


def refresh_session_statuses() -> list[int]:
    now = _now()
    changed: list[int] = []
    sessions_to_backup: list[int] = []
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM classroom_sessions
            WHERE status <> 'ended'
            """
        ).fetchall()
        for row in rows:
            session = _row_to_dict(row)
            end_time = _parse_time(session.get("end_time"))
            start_time = _parse_time(session.get("start_time"))
            if end_time and end_time <= now:
                _end_session_in_connection(connection, session, now, "auto")
                changed.append(int(session["id"]))
                sessions_to_backup.append(int(session["id"]))
            elif session["status"] == "pending" and start_time and start_time <= now:
                before = connection.total_changes
                _start_session_in_connection(connection, session, now)
                if connection.total_changes > before:
                    changed.append(int(session["id"]))

    for _session_id in sessions_to_backup:
        try:
            create_backup("class_ended")
        except Exception:
            pass
    return changed


def start_session(session_id: int) -> dict[str, Any]:
    refresh_session_statuses()
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        if session["status"] == "ended":
            raise AppError("课堂已结束，不能重新开始", code="SESSION_ALREADY_ENDED")
        if session["status"] == "active":
            return get_session_public(session_id)
        if _roster_count(connection, session) <= 0:
            raise AppError("请先导入本课堂学生名单", code="ROSTER_REQUIRED")
        _start_session_in_connection(connection, session, _now())
    return get_session_public(session_id)


def end_session(session_id: int) -> dict[str, Any]:
    refresh_session_statuses()
    should_backup = False
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        if session["status"] != "ended":
            _end_session_in_connection(connection, session, _now(), "teacher")
            should_backup = True
    backup_results: list[dict[str, object]] = []
    if should_backup:
        try:
            backup_results = create_backup("class_ended")
        except Exception as exc:
            backup_results = [{"status": "failed", "message": str(exc)}]
    result = get_sign_in_summary(session_id)
    result["backup_results"] = backup_results
    return result


def get_session_public(session_id: int) -> dict[str, Any]:
    refresh_session_statuses()
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        session["roster_count"] = _roster_count(connection, session)
    return session


def list_active_sessions() -> list[dict[str, Any]]:
    refresh_session_statuses()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.*, c.name AS course_name, cl.name AS class_name,
                   COUNT(cs.student_id) AS roster_count
            FROM classroom_sessions s
            JOIN courses c ON c.id = s.course_id
            JOIN classes cl ON cl.id = s.class_id
            LEFT JOIN course_students cs ON cs.course_id = s.course_id AND cs.class_id = s.class_id
            WHERE s.status = 'active'
            GROUP BY s.id
            ORDER BY COALESCE(s.actual_started_at, s.start_time, s.created_at) DESC, s.id DESC
            LIMIT 20
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def student_sign_in(session_id: int, student_number: str, name: str, ip_address: str | None, user_agent: str | None) -> dict[str, Any]:
    refresh_session_statuses()
    student_number = student_number.strip()
    name = name.strip()
    if not student_number or not name:
        raise AppError("学号和姓名不能为空", code="STUDENT_ID_NAME_REQUIRED")

    with get_connection() as connection:
        session = _load_session(connection, session_id)
        if session["status"] == "pending":
            raise AppError("课堂尚未开始，暂不能签到", code="SESSION_NOT_ACTIVE", status_code=409)
        if session["status"] == "ended":
            raise AppError("课堂已结束，不能签到", code="SESSION_ENDED", status_code=409)

        student = connection.execute(
            """
            SELECT s.*
            FROM students s
            JOIN course_students cs ON cs.student_id = s.id
            WHERE s.student_id = ?
              AND cs.course_id = ?
              AND cs.class_id = ?
              AND s.is_active = 1
            """,
            (student_number, session["course_id"], session["class_id"]),
        ).fetchone()
        if student is None:
            raise AppError("未找到该学号，或不在本课堂名单中", code="STUDENT_NOT_FOUND", status_code=404)
        if str(student["name"]).strip() != name:
            raise AppError("学号与姓名不匹配", code="STUDENT_NAME_MISMATCH", status_code=409)

        existing = connection.execute(
            """
            SELECT r.*, s.student_id AS student_number, s.name AS student_name
            FROM sign_in_records r
            JOIN students s ON s.id = r.student_id
            WHERE r.session_id = ? AND r.student_id = ?
            """,
            (session_id, student["id"]),
        ).fetchone()
        if existing is not None:
            result = _row_to_dict(existing)
            result["duplicate"] = True
            return result

        started_at = _parse_time(session.get("actual_started_at")) or _parse_time(session.get("start_time")) or _now()
        deadline = started_at + timedelta(minutes=int(session.get("sign_in_deadline_minutes") or 15))
        sign_time = _now()
        status = "late" if sign_time > deadline else "normal"
        cursor = connection.execute(
            """
            INSERT INTO sign_in_records(session_id, student_id, status, sign_time, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, student["id"], status, _to_db_time(sign_time), ip_address, user_agent),
        )
        row = connection.execute(
            """
            SELECT r.*, s.student_id AS student_number, s.name AS student_name
            FROM sign_in_records r
            JOIN students s ON s.id = r.student_id
            WHERE r.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    result = _row_to_dict(row)
    result["duplicate"] = False
    return result


def get_sign_in_summary(session_id: int) -> dict[str, Any]:
    refresh_session_statuses()
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        rows = connection.execute(
            """
            SELECT s.id AS student_pk, s.student_id AS student_number, s.name AS student_name,
                   cl.name AS class_name, r.id AS record_id, r.status, r.sign_time,
                   r.ip_address, r.user_agent
            FROM course_students cs
            JOIN students s ON s.id = cs.student_id
            JOIN classes cl ON cl.id = s.class_id
            LEFT JOIN sign_in_records r ON r.session_id = ? AND r.student_id = s.id
            WHERE cs.course_id = ? AND cs.class_id = ?
            ORDER BY s.student_id
            """,
            (session_id, session["course_id"], session["class_id"]),
        ).fetchall()

    records = [_row_to_dict(row) for row in rows]
    total = len(records)
    normal = sum(1 for item in records if item.get("status") == "normal")
    late = sum(1 for item in records if item.get("status") == "late")
    absent = sum(1 for item in records if item.get("status") == "absent")
    signed = normal + late
    unsigned = total - signed - absent
    return {
        "session": session,
        "stats": {
            "total": total,
            "signed": signed,
            "normal": normal,
            "late": late,
            "absent": absent,
            "unsigned": unsigned,
        },
        "records": records,
    }
