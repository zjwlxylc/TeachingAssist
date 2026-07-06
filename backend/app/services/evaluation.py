import csv
import json
from io import StringIO
from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services import ai as ai_service
from app.services.classroom import get_session_public


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _level(total: float) -> str:
    if total >= 90:
        return "优秀"
    if total >= 75:
        return "良好"
    if total >= 60:
        return "一般"
    return "需关注"


def _template_advice(level: str, warnings: list[str]) -> str:
    if warnings:
        return f"本节课状态为{level}，请优先关注：" + "、".join(warnings) + "。"
    if level == "优秀":
        return "本节课表现优秀，请继续保持稳定参与和高质量输出。"
    if level == "良好":
        return "本节课整体表现良好，可在互动质量和作业细节上继续提升。"
    if level == "一般":
        return "本节课表现一般，建议课后回看问题和作业反馈，补齐薄弱环节。"
    return "本节课需要关注，建议及时完成课堂任务并向教师反馈遇到的困难。"


def _load_weights(connection: Any) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM evaluation_weight_settings WHERE id = 1").fetchone()
    if row is None:
        connection.execute("INSERT OR IGNORE INTO evaluation_weight_settings(id) VALUES (1)")
        row = connection.execute("SELECT * FROM evaluation_weight_settings WHERE id = 1").fetchone()
    return _row_to_dict(row)


def update_weights(payload: dict[str, Any]) -> dict[str, Any]:
    values = {
        "attendance_weight": float(payload.get("attendance_weight", 20)),
        "question_weight": float(payload.get("question_weight", 35)),
        "homework_weight": float(payload.get("homework_weight", 25)),
        "message_weight": float(payload.get("message_weight", 10)),
        "activity_weight": float(payload.get("activity_weight", 10)),
    }
    if any(value < 0 for value in values.values()) or round(sum(values.values()), 2) != 100:
        raise AppError("评估权重必须非负且总和为 100", code="EVALUATION_WEIGHTS_INVALID")
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE evaluation_weight_settings
            SET attendance_weight = ?, question_weight = ?, homework_weight = ?,
                message_weight = ?, activity_weight = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (
                values["attendance_weight"],
                values["question_weight"],
                values["homework_weight"],
                values["message_weight"],
                values["activity_weight"],
            ),
        )
        return _load_weights(connection)


def calculate_session(session_id: int, version_type: str = "temporary") -> dict[str, Any]:
    if version_type not in {"temporary", "final"}:
        raise AppError("评估版本类型不支持", code="EVALUATION_VERSION_INVALID")
    session = get_session_public(session_id)
    with get_connection() as connection:
        weights = _load_weights(connection)
        version = connection.execute(
            """
            SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version
            FROM learning_evaluations
            WHERE session_id = ? AND version_type = ?
            """,
            (session_id, version_type),
        ).fetchone()
        version_no = int(version["next_version"])
        students = connection.execute(
            """
            SELECT s.id, s.student_id, s.name
            FROM course_students cs
            JOIN students s ON s.id = cs.student_id
            WHERE cs.course_id = ? AND cs.class_id = ? AND s.is_active = 1
            ORDER BY s.student_id
            """,
            (session["course_id"], session["class_id"]),
        ).fetchall()
        for row in students:
            student = _row_to_dict(row)
            sign_in = connection.execute(
                "SELECT status FROM sign_in_records WHERE session_id = ? AND student_id = ?",
                (session_id, student["id"]),
            ).fetchone()
            status = sign_in["status"] if sign_in else None
            attendance_score = 100 if status == "normal" else 80 if status == "late" else 0

            question_row = connection.execute(
                """
                SELECT COUNT(*) AS total_questions,
                       COUNT(qa.id) AS answered,
                       AVG(CASE WHEN qa.status IN ('submitted', 'timeout') THEN qa.score ELSE 0 END) AS avg_score,
                       SUM(COALESCE(qbr.total_score, 0)) AS bonus_score
                FROM questions q
                LEFT JOIN question_answers qa
                  ON qa.question_id = q.id AND qa.student_id = ? AND qa.is_latest = 1
                LEFT JOIN question_bonus_records qbr ON qbr.answer_id = qa.id
                WHERE q.session_id = ?
                """,
                (student["id"], session_id),
            ).fetchone()
            total_questions = int(question_row["total_questions"] or 0)
            answered = int(question_row["answered"] or 0)
            question_score = 100 if total_questions == 0 else min(100, (answered / total_questions) * 60 + float(question_row["bonus_score"] or 0) * 2)

            homework_row = connection.execute(
                """
                SELECT COUNT(h.id) AS total_homework,
                       COUNT(hs.id) AS submitted,
                       AVG(COALESCE(hs.final_score, hs.ai_score)) AS avg_homework_score
                FROM homework h
                LEFT JOIN homework_submissions hs
                  ON hs.homework_id = h.id AND hs.student_id = ? AND hs.is_latest = 1
                WHERE h.session_id = ?
                """,
                (student["id"], session_id),
            ).fetchone()
            total_homework = int(homework_row["total_homework"] or 0)
            submitted_homework = int(homework_row["submitted"] or 0)
            avg_homework = homework_row["avg_homework_score"]
            if total_homework == 0:
                homework_score = 100 if version_type == "final" else 80
            elif avg_homework is not None:
                homework_score = float(avg_homework)
            else:
                homework_score = (submitted_homework / total_homework) * 70

            message_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM question_action_logs
                WHERE session_id = ? AND student_id = ?
                """,
                (session_id, student["id"]),
            ).fetchone()
            activity_count = int(message_row["total"] or 0)
            message_score = min(100, activity_count * 20)
            activity_score = min(100, activity_count * 15 + answered * 10 + submitted_homework * 15)

            total_score = (
                attendance_score * float(weights["attendance_weight"])
                + question_score * float(weights["question_weight"])
                + homework_score * float(weights["homework_weight"])
                + message_score * float(weights["message_weight"])
                + activity_score * float(weights["activity_weight"])
            ) / 100
            warnings = []
            if attendance_score == 0:
                warnings.append("缺勤")
                total_score = min(total_score, 59)
            if total_questions and answered == 0:
                warnings.append("未参与互动")
            if total_homework and submitted_homework == 0:
                warnings.append("未交作业")
            level = _level(total_score)
            advice = _template_advice(level, warnings)
            try:
                if ai_service.is_ai_available():
                    generated = ai_service.generate_structured_json(
                        "learning_advice",
                        f"为学生生成 80 字以内学习建议，返回 JSON {{\"advice\":\"...\"}}。等级：{level}，预警：{warnings}",
                        source_type="learning_evaluation",
                        source_id=session_id,
                    )
                    advice = str(generated.get("advice") or advice)
            except Exception as exc:
                ai_service.record_failure_task(
                    "learning_advice",
                    "learning_evaluation",
                    session_id,
                    str(exc),
                    {"student_id": student["student_id"], "level": level},
                )
            connection.execute(
                """
                INSERT INTO learning_evaluations(
                    session_id, student_id, version_type, version_no,
                    attendance_score, question_score, homework_score, message_score, activity_score,
                    total_score, level, advice, warnings_json, raw_data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    student["id"],
                    version_type,
                    version_no,
                    round(attendance_score, 2),
                    round(question_score, 2),
                    round(homework_score, 2),
                    round(message_score, 2),
                    round(activity_score, 2),
                    round(total_score, 2),
                    level,
                    advice,
                    json.dumps(warnings, ensure_ascii=False),
                    json.dumps(
                        {
                            "sign_in_status": status,
                            "total_questions": total_questions,
                            "answered_questions": answered,
                            "total_homework": total_homework,
                            "submitted_homework": submitted_homework,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
    return get_session_report(session_id, version_type=version_type, version_no=version_no)


def get_session_report(session_id: int, version_type: str | None = None, version_no: int | None = None) -> dict[str, Any]:
    session = get_session_public(session_id)
    with get_connection() as connection:
        weights = _load_weights(connection)
        if version_type is None or version_no is None:
            latest = connection.execute(
                """
                SELECT version_type, version_no
                FROM learning_evaluations
                WHERE session_id = ?
                ORDER BY CASE version_type WHEN 'final' THEN 2 ELSE 1 END DESC, version_no DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if latest is None:
                return {"session": session, "weights": weights, "summary": {}, "records": []}
            version_type = latest["version_type"]
            version_no = int(latest["version_no"])
        rows = connection.execute(
            """
            SELECT le.*, s.student_id AS student_number, s.name AS student_name
            FROM learning_evaluations le
            JOIN students s ON s.id = le.student_id
            WHERE le.session_id = ? AND le.version_type = ? AND le.version_no = ?
            ORDER BY s.student_id
            """,
            (session_id, version_type, version_no),
        ).fetchall()
    records = []
    distribution = {"优秀": 0, "良好": 0, "一般": 0, "需关注": 0}
    attendance_present = 0
    for row in rows:
        item = _row_to_dict(row)
        item["warnings"] = _json_loads(item.pop("warnings_json", "[]"), [])
        item["raw_data"] = _json_loads(item.pop("raw_data_json", "{}"), {})
        distribution[item["level"]] = distribution.get(item["level"], 0) + 1
        if float(item["attendance_score"]) > 0:
            attendance_present += 1
        records.append(item)
    total = len(records)
    return {
        "session": session,
        "weights": weights,
        "version_type": version_type,
        "version_no": version_no,
        "summary": {
            "total": total,
            "level_distribution": distribution,
            "attendance_rate": round(attendance_present / total * 100, 2) if total else 0,
            "average_score": round(sum(float(item["total_score"]) for item in records) / total, 2) if total else 0,
            "warnings": [item for item in records if item["warnings"]],
        },
        "records": records,
    }


def get_student_feedback(session_id: int, student_number: str, name: str) -> dict[str, Any]:
    with get_connection() as connection:
        session = get_session_public(session_id)
        student = connection.execute(
            """
            SELECT s.*
            FROM students s
            JOIN course_students cs ON cs.student_id = s.id
            WHERE s.student_id = ? AND s.name = ? AND cs.course_id = ? AND cs.class_id = ?
            """,
            (student_number.strip(), name.strip(), session["course_id"], session["class_id"]),
        ).fetchone()
        if student is None:
            raise AppError("未找到该学号，或姓名不匹配", code="STUDENT_NOT_FOUND", status_code=404)
        row = connection.execute(
            """
            SELECT *
            FROM learning_evaluations
            WHERE session_id = ? AND student_id = ?
            ORDER BY CASE version_type WHEN 'final' THEN 2 ELSE 1 END DESC, version_no DESC
            LIMIT 1
            """,
            (session_id, student["id"]),
        ).fetchone()
    if row is None:
        return {"session": session, "evaluation": None}
    item = _row_to_dict(row)
    item["warnings"] = _json_loads(item.pop("warnings_json", "[]"), [])
    item["raw_data"] = _json_loads(item.pop("raw_data_json", "{}"), {})
    return {"session": session, "evaluation": item}


def export_session(session_id: int) -> dict[str, Any]:
    report = get_session_report(session_id)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "student_number",
            "student_name",
            "attendance_score",
            "question_score",
            "homework_score",
            "message_score",
            "activity_score",
            "total_score",
            "level",
            "advice",
        ],
    )
    writer.writeheader()
    for item in report["records"]:
        writer.writerow({field: item.get(field, "") for field in writer.fieldnames})
    return {
        "file_name": f"learning_evaluation_session_{session_id}.csv",
        "content_type": "text/csv",
        "content": output.getvalue(),
        "total": len(report["records"]),
    }
