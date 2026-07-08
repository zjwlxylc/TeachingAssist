import csv
import json
import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.backup import create_backup
from app.services import student_auth


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
logger = logging.getLogger(__name__)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _check_device_fingerprint(
    connection: Any, session_id: int, student_id: int, device_hash: str, ip_address: str | None
) -> dict[str, Any] | None:
    """检测同一浏览器会话是否被多人用于签到，并结合 IP 做辅助判断"""
    # 检查同一浏览器会话 ID 是否已被其他学生使用
    other_records = connection.execute(
        """
        SELECT DISTINCT s.student_id, s.name, df.ip_address, df.sign_in_count
        FROM device_fingerprints df
        JOIN students s ON s.id = df.student_id
        WHERE df.session_id = ? AND df.device_hash = ? AND df.student_id != ?
        """,
        (session_id, device_hash, student_id),
    ).fetchall()

    if not other_records:
        return None

    student_count = len(other_records) + 1
    alert_level = "critical" if student_count >= 3 else "warning"

    # IP 辅助判断：同一浏览器 + 同一 IP → 证据更充分
    same_ip = all(
        row["ip_address"] and row["ip_address"] == ip_address
        for row in other_records
    ) if ip_address else False

    student_ids = [student_id] + [row["student_id"] for row in other_records]
    connection.execute(
        """
        INSERT INTO device_sharing_alerts(session_id, device_hash, student_count, student_ids_json, alert_level)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id, device_hash) DO UPDATE SET
            student_count = excluded.student_count,
            student_ids_json = excluded.student_ids_json,
            alert_level = excluded.alert_level,
            updated_at = datetime('now')
        """,
        (session_id, device_hash, student_count, json.dumps(student_ids), alert_level),
    )

    other_names = [f"{row['name']}({row['student_id']})" for row in other_records[:3]]
    ip_note = "，且 IP 地址相同" if same_ip else ""
    message = f"该浏览器已被 {', '.join(other_names)} 等 {len(other_records)} 人使用过{ip_note}"

    return {
        "level": alert_level,
        "message": message,
        "device_shared": True,
        "shared_with_count": len(other_records),
        "ip_matched": same_ip,
    }


def _record_device_fingerprint(
    connection: Any,
    session_id: int,
    student_id: int,
    device_hash: str,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """记录浏览器会话 ID"""
    existing = connection.execute(
        """
        SELECT id, sign_in_count FROM device_fingerprints
        WHERE session_id = ? AND student_id = ? AND device_hash = ?
        """,
        (session_id, student_id, device_hash),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE device_fingerprints
            SET sign_in_count = sign_in_count + 1,
                last_seen_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (existing["id"],),
        )
    else:
        connection.execute(
            """
            INSERT INTO device_fingerprints(
                session_id, student_id, device_hash, ip_address, user_agent
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, student_id, device_hash, ip_address, user_agent),
        )


def _now() -> datetime:
    return datetime.now()


def _to_db_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("T", " ")
        if len(normalized) == 16:
            normalized = f"{normalized}:00"
        return datetime.strptime(normalized[:19], TIME_FORMAT)
    except (ValueError, IndexError):
        return None


def _load_session(connection: Any, session_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT s.*, c.name AS course_name,
               (SELECT GROUP_CONCAT(cl.name) FROM session_classes sc JOIN classes cl ON cl.id = sc.class_id WHERE sc.session_id = s.id) AS class_name
        FROM classroom_sessions s
        JOIN courses c ON c.id = s.course_id
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
        FROM students s
        WHERE s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?) AND s.is_active = 1
        """,
        (session["id"],),
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
        SELECT ?, s.id, 'absent'
        FROM students s
        WHERE s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?) AND s.is_active = 1
        """,
        (session["id"], session["id"]),
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
            logger.warning("Auto backup after session %s ended failed", _session_id, exc_info=True)
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
    try:
        from app.services.evaluation import calculate_session

        calculate_session(session_id, "temporary")
    except Exception:
        pass
    result = get_sign_in_summary(session_id)
    result["backup_results"] = backup_results
    return result


def get_session_public(session_id: int) -> dict[str, Any]:
    # 注意：不在读路径刷新状态，避免 GET 请求产生写库副作用（由后台 session_status_worker 周期性刷新）。
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        session["roster_count"] = _roster_count(connection, session)
    return session


def list_active_sessions() -> list[dict[str, Any]]:
    # 注意：状态由后台 session_status_worker 周期性刷新，这里只做纯读，避免读路径写副作用。
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.*, c.name AS course_name,
                   (SELECT GROUP_CONCAT(cl.name) FROM session_classes sc JOIN classes cl ON cl.id = sc.class_id WHERE sc.session_id = s.id) AS class_name,
                   (SELECT COUNT(*) FROM students st WHERE st.class_id IN (SELECT class_id FROM session_classes WHERE session_id = s.id) AND st.is_active = 1) AS roster_count
            FROM classroom_sessions s
            JOIN courses c ON c.id = s.course_id
            WHERE s.status = 'active'
            ORDER BY COALESCE(s.actual_started_at, s.start_time, s.created_at) DESC, s.id DESC
            LIMIT 20
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def student_sign_in(
    session_id: int,
    student_number: str,
    name: str,
    ip_address: str | None,
    user_agent: str | None,
    device_hash: str | None = None,
) -> dict[str, Any]:
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
            WHERE s.student_id = ?
              AND s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?)
              AND s.is_active = 1
            """,
            (student_number, session["id"]),
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
            # 重复签到也发放/轮换令牌，保证学生拿到有效私信身份
            result["token"] = student_auth.create_student_session(int(student["id"]), session_id)
            return result

        # 浏览器会话检测
        device_warning = None
        if device_hash:
            device_warning = _check_device_fingerprint(connection, session_id, int(student["id"]), device_hash, ip_address)

        started_at = _parse_time(session.get("actual_started_at")) or _parse_time(session.get("start_time")) or _now()
        deadline = started_at + timedelta(minutes=int(session.get("sign_in_deadline_minutes") or 15))
        sign_time = _now()
        status = "late" if sign_time > deadline else "normal"
        cursor = connection.execute(
            """
            INSERT INTO sign_in_records(session_id, student_id, status, sign_time, ip_address, user_agent, device_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, student["id"], status, _to_db_time(sign_time), ip_address, user_agent, device_hash),
        )

        # 记录浏览器会话 ID
        if device_hash:
            _record_device_fingerprint(
                connection,
                session_id,
                int(student["id"]),
                device_hash,
                ip_address,
                user_agent,
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
    if device_warning:
        result["device_warning"] = device_warning
    # 发放学生会话令牌，用于私信读/发鉴权（替代仅靠学号+姓名的弱身份）
    result["token"] = student_auth.create_student_session(int(student["id"]), session_id)
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
            FROM students s
            JOIN classes cl ON cl.id = s.class_id
            LEFT JOIN sign_in_records r ON r.session_id = ? AND r.student_id = s.id
            WHERE s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?) AND s.is_active = 1
            ORDER BY s.student_id
            """,
            (session_id, session_id),
        ).fetchall()

    records = [_row_to_dict(row) for row in rows]
    total = len(records)
    normal = sum(1 for item in records if item.get("status") == "normal")
    late = sum(1 for item in records if item.get("status") == "late")
    absent = sum(1 for item in records if item.get("status") == "absent")
    leave = sum(1 for item in records if item.get("status") == "leave")
    signed = normal + late
    unsigned = total - signed - absent - leave
    return {
        "session": session,
        "stats": {
            "total": total,
            "signed": signed,
            "normal": normal,
            "late": late,
            "absent": absent,
            "leave": leave,
            "unsigned": unsigned,
        },
        "records": records,
    }


def update_sign_in_status(
    session_id: int,
    student_pk: int,
    status: str,
    reason: str | None = None,
    operator_name: str | None = None,
) -> dict[str, Any]:
    if status not in {"normal", "late", "absent", "leave"}:
        raise AppError("签到状态不支持", code="SIGN_IN_STATUS_UNSUPPORTED")
    with get_connection() as connection:
        session = _load_session(connection, session_id)
        student = connection.execute(
            """
            SELECT s.*
            FROM students s
            WHERE s.id = ? AND s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?)
            """,
            (student_pk, session["id"]),
        ).fetchone()
        if student is None:
            raise AppError("学生不在本课堂名单中", code="STUDENT_NOT_IN_SESSION", status_code=404)
        previous = connection.execute(
            "SELECT * FROM sign_in_records WHERE session_id = ? AND student_id = ?",
            (session_id, student_pk),
        ).fetchone()
        previous_status = previous["status"] if previous else None
        sign_time = _to_db_time(_now()) if status in {"normal", "late"} else None
        connection.execute(
            """
            INSERT INTO sign_in_records(session_id, student_id, status, sign_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, student_id) DO UPDATE SET
                status = excluded.status,
                sign_time = excluded.sign_time,
                updated_at = datetime('now')
            """,
            (session_id, student_pk, status, sign_time),
        )
        connection.execute(
            """
            INSERT INTO sign_in_change_logs(session_id, student_id, previous_status, new_status, reason, operator_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, student_pk, previous_status, status, reason, operator_name or "教师"),
        )
    return get_sign_in_summary(session_id)


def list_sign_in_change_logs(session_id: int) -> list[dict[str, Any]]:
    get_session_public(session_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT l.*, s.student_id AS student_number, s.name AS student_name
            FROM sign_in_change_logs l
            JOIN students s ON s.id = l.student_id
            WHERE l.session_id = ?
            ORDER BY l.created_at DESC, l.id DESC
            LIMIT 200
            """,
            (session_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def export_sign_ins(session_id: int) -> dict[str, Any]:
    summary = get_sign_in_summary(session_id)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["student_number", "student_name", "class_name", "status", "sign_time", "ip_address", "device_hash"],
    )
    writer.writeheader()
    for record in summary["records"]:
        writer.writerow(
            {
                "student_number": record["student_number"],
                "student_name": record["student_name"],
                "class_name": record["class_name"],
                "status": record.get("status") or "absent",
                "sign_time": record.get("sign_time") or "",
                "ip_address": record.get("ip_address") or "",
                "device_hash": (record.get("device_hash") or "")[:12],
            }
        )
    return {
        "file_name": f"sign_in_session_{session_id}.csv",
        "content_type": "text/csv",
        "content": output.getvalue(),
        "total": len(summary["records"]),
    }


def get_device_sharing_alerts(session_id: int) -> list[dict[str, Any]]:
    """获取设备共享警告列表"""
    get_session_public(session_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT dsa.*,
                   GROUP_CONCAT(s.name || '(' || s.student_id || ')', ', ') as student_list
            FROM device_sharing_alerts dsa
            JOIN device_fingerprints df ON df.session_id = dsa.session_id AND df.device_hash = dsa.device_hash
            JOIN students s ON s.id = df.student_id
            WHERE dsa.session_id = ?
            GROUP BY dsa.id
            ORDER BY dsa.student_count DESC, dsa.created_at DESC
            """,
            (session_id,),
        ).fetchall()
    alerts = []
    for row in rows:
        alert = _row_to_dict(row)
        alert["student_ids"] = json.loads(alert.get("student_ids_json") or "[]")
        alerts.append(alert)
    return alerts


def review_device_alert(alert_id: int, reviewed_by: str, notes: str | None = None) -> dict[str, Any]:
    """标记设备共享警告为已审核"""
    with get_connection() as connection:
        alert = connection.execute(
            "SELECT * FROM device_sharing_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
        if alert is None:
            raise AppError("警告记录不存在", code="ALERT_NOT_FOUND", status_code=404)
        connection.execute(
            """
            UPDATE device_sharing_alerts
            SET reviewed = 1, reviewed_by = ?, reviewed_at = datetime('now'), notes = ?
            WHERE id = ?
            """,
            (reviewed_by, notes, alert_id),
        )
        updated = connection.execute(
            "SELECT * FROM device_sharing_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
    return _row_to_dict(updated)
