import re
import csv
import json
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services import ai as ai_service
from app.services.classroom import get_session_public


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".doc", ".docx", ".pdf", ".zip", ".txt", ".jpg", ".jpeg", ".png"}


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


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


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "upload.bin"


def _homework_upload_root(homework_id: int, submission_id: int | None = None) -> Path:
    uploads_dir = get_settings().storage.uploads_dir
    if uploads_dir is None:
        raise AppError("上传目录未配置", code="UPLOAD_DIR_NOT_CONFIGURED", status_code=500)
    path = uploads_dir / "homework" / str(homework_id)
    if submission_id is not None:
        path = path / "submissions" / str(submission_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_homework(connection: Any, homework_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT h.*, s.title AS session_title, c.name AS course_name,
               (SELECT GROUP_CONCAT(cl.name) FROM session_classes sc JOIN classes cl ON cl.id = sc.class_id WHERE sc.session_id = s.id) AS class_name
        FROM homework h
        JOIN classroom_sessions s ON s.id = h.session_id
        JOIN courses c ON c.id = s.course_id
        WHERE h.id = ?
        """,
        (homework_id,),
    ).fetchone()
    if row is None:
        raise AppError("作业不存在", code="HOMEWORK_NOT_FOUND", status_code=404)
    item = _row_to_dict(row)
    item["attachments"] = _load_homework_attachments(connection, homework_id)
    return item


def _load_homework_attachments(connection: Any, homework_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, homework_id, original_name, stored_name, file_path, file_size, mime_type, created_at
        FROM homework_attachments
        WHERE homework_id = ?
        ORDER BY id
        """,
        (homework_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _refresh_homework_status(connection: Any, homework_id: int | None = None) -> None:
    where = "status = 'active' AND deadline <= ? AND allow_late = 0"
    params: tuple[Any, ...] = (_to_db_time(_now()),)
    if homework_id is not None:
        where += " AND id = ?"
        params = (*params, homework_id)
    connection.execute(
        f"UPDATE homework SET status = 'closed', updated_at = datetime('now') WHERE {where}",
        params,
    )


def _public_homework(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "session_id": item["session_id"],
        "title": item["title"],
        "description": item["description"],
        "deadline": item["deadline"],
        "grading_criteria": item["grading_criteria"],
        "status": item["status"],
        "allow_late": item["allow_late"],
        "published_at": item["published_at"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "attachments": item.get("attachments", []),
    }


def add_homework_attachments(homework_id: int, files: list[UploadFile] | None = None) -> dict[str, Any]:
    files = [file for file in (files or []) if file.filename]
    if not files:
        raise AppError("请选择要上传的附件", code="HOMEWORK_ATTACHMENT_REQUIRED")
    with get_connection() as connection:
        _load_homework(connection, homework_id)
        target_dir = _homework_upload_root(homework_id)
        saved_files: list[dict[str, Any]] = []
        try:
            for file in files:
                saved = _save_upload(file, target_dir)
                saved_files.append(saved)
                connection.execute(
                    """
                    INSERT INTO homework_attachments(
                        homework_id, original_name, stored_name, file_path, file_size, mime_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        homework_id,
                        saved["original_name"],
                        saved["stored_name"],
                        saved["file_path"],
                        saved["file_size"],
                        saved["mime_type"],
                    ),
                )
        except Exception:
            for saved in saved_files:
                Path(saved["file_path"]).unlink(missing_ok=True)
            raise
        homework = _load_homework(connection, homework_id)
    return _public_homework(homework)


def create_homework(session_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    session = get_session_public(session_id)
    if session["status"] == "ended":
        raise AppError("课堂已结束，不能发布新作业", code="SESSION_ENDED", status_code=409)

    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    grading_criteria = str(payload.get("grading_criteria") or "").strip()
    deadline = _parse_time(payload.get("deadline"))
    allow_late = bool(payload.get("allow_late"))
    now = _now()
    if not title:
        raise AppError("作业标题不能为空", code="HOMEWORK_TITLE_REQUIRED")
    if deadline is None:
        raise AppError("作业截止时间不能为空", code="HOMEWORK_DEADLINE_REQUIRED")
    if deadline <= now:
        raise AppError("截止时间必须晚于当前时间", code="HOMEWORK_DEADLINE_BEFORE_NOW")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO homework(session_id, title, description, deadline, grading_criteria, status, allow_late, published_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                session_id,
                title,
                description,
                _to_db_time(deadline),
                grading_criteria,
                1 if allow_late else 0,
                _to_db_time(now),
            ),
        )
        item = _load_homework(connection, int(cursor.lastrowid))
    return _public_homework(item)


def list_homework(session_id: int, public_only: bool = False) -> list[dict[str, Any]]:
    get_session_public(session_id)
    with get_connection() as connection:
        _refresh_homework_status(connection)
        where = "WHERE h.session_id = ?"
        if public_only:
            where += " AND h.status IN ('active', 'closed')"
        rows = connection.execute(
            f"""
            SELECT h.*
            FROM homework h
            {where}
            ORDER BY h.id DESC
            """,
            (session_id,),
        ).fetchall()
        items = []
        for row in rows:
            item = _row_to_dict(row)
            item["attachments"] = _load_homework_attachments(connection, int(item["id"]))
            items.append(_public_homework(item))
    return items


def _resolve_student(connection: Any, session: dict[str, Any], student_number: str, name: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT s.*
        FROM students s
        WHERE s.student_id = ?
          AND s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?)
          AND s.is_active = 1
        """,
        (student_number.strip(), session["id"]),
    ).fetchone()
    if row is None:
        raise AppError("未找到该学号，或不在本课堂名单中", code="STUDENT_NOT_FOUND", status_code=404)
    student = _row_to_dict(row)
    if str(student["name"]).strip() != name.strip():
        raise AppError("学号与姓名不匹配", code="STUDENT_NAME_MISMATCH", status_code=409)
    return student


def _save_upload(file: UploadFile, target_dir: Path) -> dict[str, Any]:
    original_name = file.filename or "upload.bin"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError("文件格式不支持", code="HOMEWORK_FILE_TYPE_UNSUPPORTED")

    safe_name = _safe_filename(original_name)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    target_path = target_dir / stored_name
    size = 0
    try:
        with target_path.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise AppError("单个文件不能超过 10MB", code="HOMEWORK_FILE_TOO_LARGE")
                output.write(chunk)
        file.file.seek(0)
        return {
            "original_name": original_name,
            "stored_name": stored_name,
            "file_path": str(target_path),
            "file_size": size,
            "mime_type": file.content_type,
        }
    except AppError:
        target_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise AppError(f"文件保存失败: {str(exc)}", code="HOMEWORK_FILE_SAVE_FAILED")


def submit_homework(
    homework_id: int,
    student_number: str,
    name: str,
    text_content: str | None,
    files: list[UploadFile] | None = None,
) -> dict[str, Any]:
    files = [file for file in (files or []) if file.filename]
    text_content = (text_content or "").strip()
    if not text_content and not files:
        raise AppError("请填写提交内容或上传文件", code="HOMEWORK_SUBMISSION_EMPTY")

    saved_files: list[dict[str, Any]] = []
    with get_connection() as connection:
        _refresh_homework_status(connection, homework_id)
        homework = _load_homework(connection, homework_id)
        session = get_session_public(int(homework["session_id"]))
        student = _resolve_student(connection, session, student_number, name)
        now = _now()
        deadline = _parse_time(homework["deadline"])
        is_late = bool(deadline and now > deadline)
        if homework["status"] == "archived":
            raise AppError("作业已归档，不能提交", code="HOMEWORK_ARCHIVED", status_code=409)
        if homework["status"] == "closed" and not homework["allow_late"]:
            raise AppError("作业已截止，禁止提交", code="HOMEWORK_CLOSED", status_code=409)
        if is_late and not homework["allow_late"]:
            raise AppError("作业已截止，禁止提交", code="HOMEWORK_CLOSED", status_code=409)

        latest = connection.execute(
            """
            SELECT submit_version
            FROM homework_submissions
            WHERE homework_id = ? AND student_id = ? AND is_latest = 1
            """,
            (homework_id, student["id"]),
        ).fetchone()
        submit_version = int(latest["submit_version"]) + 1 if latest else 1
        connection.execute(
            "UPDATE homework_submissions SET is_latest = 0 WHERE homework_id = ? AND student_id = ? AND is_latest = 1",
            (homework_id, student["id"]),
        )
        cursor = connection.execute(
            """
            INSERT INTO homework_submissions(
                homework_id, session_id, student_id, text_content, status, submit_version,
                is_latest, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                homework_id,
                homework["session_id"],
                student["id"],
                text_content,
                "late" if is_late else "submitted",
                submit_version,
                _to_db_time(now),
            ),
        )
        submission_id = int(cursor.lastrowid)

        target_dir = _homework_upload_root(homework_id, submission_id)
        try:
            for file in files:
                saved = _save_upload(file, target_dir)
                saved_files.append(saved)
                connection.execute(
                    """
                    INSERT INTO homework_submission_files(
                        submission_id, original_name, stored_name, file_path, file_size, mime_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        submission_id,
                        saved["original_name"],
                        saved["stored_name"],
                        saved["file_path"],
                        saved["file_size"],
                        saved["mime_type"],
                    ),
                )
        except Exception:
            # Clean up all saved files on partial failure to prevent orphaned files
            for saved in saved_files:
                Path(saved["file_path"]).unlink(missing_ok=True)
            raise
        row = connection.execute(
            """
            SELECT hs.*, s.student_id AS student_number, s.name AS student_name
            FROM homework_submissions hs
            JOIN students s ON s.id = hs.student_id
            WHERE hs.id = ?
            """,
            (submission_id,),
        ).fetchone()

    result = _row_to_dict(row)
    result["files"] = saved_files
    return result


def get_submission_summary(homework_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        _refresh_homework_status(connection, homework_id)
        homework = _load_homework(connection, homework_id)
        session = get_session_public(int(homework["session_id"]))
        rows = connection.execute(
            """
            SELECT s.id AS student_pk, s.student_id AS student_number, s.name AS student_name,
                   hs.id AS submission_id, hs.text_content, hs.status AS submission_status,
                   hs.submit_version, hs.submitted_at, hs.created_at,
                   hs.ai_score, hs.ai_feedback_json, hs.ai_confidence,
                   hs.final_score, hs.final_feedback, hs.grade_published_at
            FROM students s
            LEFT JOIN homework_submissions hs
              ON hs.homework_id = ? AND hs.student_id = s.id AND hs.is_latest = 1
            WHERE s.class_id IN (SELECT class_id FROM session_classes WHERE session_id = ?) AND s.is_active = 1
            ORDER BY s.student_id
            """,
            (homework_id, session["id"]),
        ).fetchall()
        records = [_row_to_dict(row) for row in rows]
        for record in records:
            if record["submission_id"] is None:
                record["submission_status"] = "not_submitted"
                record["files"] = []
                continue
            record["ai_feedback"] = _json_loads(record.pop("ai_feedback_json", None), None)
            file_rows = connection.execute(
                """
                SELECT id, submission_id, original_name, stored_name, file_path, file_size, mime_type, created_at
                FROM homework_submission_files
                WHERE submission_id = ?
                ORDER BY id
                """,
                (record["submission_id"],),
            ).fetchall()
            record["files"] = [_row_to_dict(file_row) for file_row in file_rows]

    total = len(records)
    submitted = sum(1 for item in records if item["submission_status"] in {"submitted", "late", "pending_review", "ai_reviewed", "teacher_reviewed", "published"})
    late = sum(1 for item in records if item["submission_status"] == "late")
    return {
        "homework": _public_homework(homework),
        "stats": {
            "total": total,
            "submitted": submitted,
            "not_submitted": total - submitted,
            "late": late,
        },
        "records": records,
    }


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def start_ai_review(homework_id: int) -> dict[str, Any]:
    # Phase 1: Load homework and submissions (read-only)
    with get_connection() as connection:
        homework = _load_homework(connection, homework_id)
        submission_rows = connection.execute(
            """
            SELECT hs.*, s.student_id AS student_number, s.name AS student_name
            FROM homework_submissions hs
            JOIN students s ON s.id = hs.student_id
            WHERE hs.homework_id = ? AND hs.is_latest = 1
              AND hs.status IN ('submitted', 'late', 'pending_review', 'ai_reviewed', 'teacher_reviewed')
            ORDER BY hs.id
            """,
            (homework_id,),
        ).fetchall()
        submissions = [_row_to_dict(row) for row in submission_rows]

    # Phase 2: Create review job and call AI for each submission (outside read transaction)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO homework_review_jobs(homework_id, status, total_count, reviewed_count, manual_count, message)
            VALUES (?, 'running', ?, 0, 0, ?)
            """,
            (homework_id, len(submissions), "AI 批阅任务已启动"),
        )
        job_id = int(cursor.lastrowid)

    reviewed = 0
    manual = 0
    review_results: list[dict[str, Any]] = []
    for submission in submissions:
        try:
            result = ai_service.generate_structured_json(
                "homework_review",
                (
                    "请按评分标准批阅作业，仅返回 JSON，字段必须包含："
                    "score, level, strengths, problems, suggestions, comment, confidence。\n"
                    f"作业标题：{homework['title']}\n作业要求：{homework.get('description') or ''}\n"
                    f"评分标准：{homework.get('grading_criteria') or ''}\n"
                    f"学生：{submission['student_number']} {submission['student_name']}\n"
                    f"提交内容：{submission.get('text_content') or ''}"
                ),
                source_type="homework_submission",
                source_id=int(submission["id"]),
                retries=2,
            )
            required = {"score", "level", "strengths", "problems", "suggestions", "comment", "confidence"}
            if not required.issubset(result):
                raise AppError("AI 批阅结果缺少结构化字段", code="HOMEWORK_REVIEW_SCHEMA_INVALID")
            review_results.append({"submission": submission, "result": result, "success": True})
            reviewed += 1
        except Exception as exc:
            manual += 1
            ai_service.record_failure_task(
                "homework_review",
                "homework_submission",
                int(submission["id"]),
                str(exc),
                {"homework_id": homework_id},
            )
            review_results.append({"submission": submission, "error": str(exc), "success": False})

    # Phase 3: Write all review results in a single transaction
    with get_connection() as connection:
        for item in review_results:
            submission = item["submission"]
            if item["success"]:
                result = item["result"]
                score = float(result.get("score") or 0)
                confidence = float(result.get("confidence") or 0)
                connection.execute(
                    """
                    UPDATE homework_submissions
                    SET status = 'ai_reviewed', ai_score = ?, ai_feedback_json = ?, ai_confidence = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (score, json.dumps(result, ensure_ascii=False), confidence, submission["id"]),
                )
                connection.execute(
                    """
                    INSERT INTO homework_review_records(submission_id, reviewer_type, score, feedback)
                    VALUES (?, 'ai', ?, ?)
                    """,
                    (submission["id"], score, json.dumps(result, ensure_ascii=False)),
                )
            else:
                connection.execute(
                    """
                    UPDATE homework_submissions
                    SET status = 'pending_review', updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (submission["id"],),
                )
        status = "completed" if manual == 0 else "manual_required"
        connection.execute(
            """
            UPDATE homework_review_jobs
            SET status = ?, reviewed_count = ?, manual_count = ?, message = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, reviewed, manual, "AI 批阅完成" if manual == 0 else "部分提交需人工批阅", job_id),
        )
        job = connection.execute("SELECT * FROM homework_review_jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(job)


def review_submission(submission_id: int, final_score: float, final_feedback: str | None = None) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM homework_submissions WHERE id = ?", (submission_id,)).fetchone()
        if row is None:
            raise AppError("作业提交不存在", code="HOMEWORK_SUBMISSION_NOT_FOUND", status_code=404)
        connection.execute(
            """
            UPDATE homework_submissions
            SET status = 'teacher_reviewed', final_score = ?, final_feedback = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (final_score, final_feedback, submission_id),
        )
        connection.execute(
            """
            INSERT INTO homework_review_records(submission_id, reviewer_type, score, feedback)
            VALUES (?, 'teacher', ?, ?)
            """,
            (submission_id, final_score, final_feedback),
        )
        updated = connection.execute("SELECT * FROM homework_submissions WHERE id = ?", (submission_id,)).fetchone()
    return _row_to_dict(updated)


def publish_homework_grades(homework_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        _load_homework(connection, homework_id)
        connection.execute(
            """
            UPDATE homework_submissions
            SET status = 'published', grade_published_at = datetime('now'), updated_at = datetime('now')
            WHERE homework_id = ? AND is_latest = 1 AND final_score IS NOT NULL
            """,
            (homework_id,),
        )
        count = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM homework_submissions
            WHERE homework_id = ? AND is_latest = 1 AND status = 'published'
            """,
            (homework_id,),
        ).fetchone()
    return {"homework_id": homework_id, "published": int(count["total"] if count else 0)}


def get_student_homework_feedback(homework_id: int, student_number: str, name: str) -> dict[str, Any]:
    with get_connection() as connection:
        homework = _load_homework(connection, homework_id)
        session = get_session_public(int(homework["session_id"]))
        student = _resolve_student(connection, session, student_number, name)
        row = connection.execute(
            """
            SELECT *
            FROM homework_submissions
            WHERE homework_id = ? AND student_id = ? AND is_latest = 1
            """,
            (homework_id, student["id"]),
        ).fetchone()
    if row is None:
        return {"homework": _public_homework(homework), "submission": None, "published": False}
    submission = _row_to_dict(row)
    published = bool(submission.get("grade_published_at"))
    if not published:
        return {"homework": _public_homework(homework), "submission": None, "published": False}
    return {
        "homework": _public_homework(homework),
        "submission": {
            "final_score": submission.get("final_score"),
            "final_feedback": submission.get("final_feedback"),
            "grade_published_at": submission.get("grade_published_at"),
        },
        "published": True,
    }


def export_homework(homework_id: int) -> dict[str, Any]:
    summary = get_submission_summary(homework_id)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["student_number", "student_name", "status", "text_summary", "final_score", "final_feedback"],
    )
    writer.writeheader()
    for record in summary["records"]:
        writer.writerow(
            {
                "student_number": record["student_number"],
                "student_name": record["student_name"],
                "status": record["submission_status"],
                "text_summary": (record.get("text_content") or "")[:120],
                "final_score": record.get("final_score") or "",
                "final_feedback": record.get("final_feedback") or "",
            }
        )
    return {
        "file_name": f"homework_{homework_id}_submissions.csv",
        "content_type": "text/csv",
        "content": output.getvalue(),
        "total": len(summary["records"]),
    }
