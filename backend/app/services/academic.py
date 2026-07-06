import json
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.core.exceptions import AppError
from app.db.session import get_connection


MAX_EXCEL_SIZE = 10 * 1024 * 1024
STANDARD_FIELDS = {
    "student_id": "学号",
    "name": "姓名",
    "class_name": "班级",
    "major": "专业",
    "college": "学院",
    "grade": "年级",
}
REQUIRED_FIELDS = {"student_id", "name", "class_name"}


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def list_courses() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.name, c.teacher_id, c.teacher_name, c.created_at, c.updated_at,
                   COUNT(DISTINCT cc.class_id) AS class_count,
                   COUNT(DISTINCT cs.student_id) AS student_count
            FROM courses c
            LEFT JOIN course_classes cc ON cc.course_id = c.id
            LEFT JOIN course_students cs ON cs.course_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.id DESC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_course(name: str, teacher_id: int | None, teacher_name: str | None) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise AppError("课程名称不能为空", code="COURSE_NAME_REQUIRED")
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO courses(name, teacher_id, teacher_name)
            VALUES (?, ?, ?)
            """,
            (name, teacher_id, teacher_name.strip() if teacher_name else None),
        )
        row = connection.execute("SELECT * FROM courses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row)


def list_classes(course_id: int | None = None) -> list[dict[str, Any]]:
    if course_id:
        sql = """
            SELECT cl.id, cl.name, cl.created_at, cl.updated_at,
                   COUNT(DISTINCT s.id) AS student_count
            FROM classes cl
            JOIN course_classes cc ON cc.class_id = cl.id
            LEFT JOIN students s ON s.class_id = cl.id AND s.is_active = 1
            WHERE cc.course_id = ?
            GROUP BY cl.id
            ORDER BY cl.name
        """
        params: tuple[Any, ...] = (course_id,)
    else:
        sql = """
            SELECT cl.id, cl.name, cl.created_at, cl.updated_at,
                   COUNT(DISTINCT s.id) AS student_count
            FROM classes cl
            LEFT JOIN students s ON s.class_id = cl.id AND s.is_active = 1
            GROUP BY cl.id
            ORDER BY cl.name
        """
        params = ()
    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_class(name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise AppError("班级名称不能为空", code="CLASS_NAME_REQUIRED")
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO classes(name)
            VALUES (?)
            ON CONFLICT(name) DO UPDATE SET updated_at = datetime('now')
            """,
            (name,),
        )
        row = connection.execute("SELECT * FROM classes WHERE name = ?", (name,)).fetchone()
    return _row_to_dict(row)


def link_course_class(course_id: int, class_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        course = connection.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        klass = connection.execute("SELECT id FROM classes WHERE id = ?", (class_id,)).fetchone()
        if course is None:
            raise AppError("课程不存在", code="COURSE_NOT_FOUND", status_code=404)
        if klass is None:
            raise AppError("班级不存在", code="CLASS_NOT_FOUND", status_code=404)
        connection.execute(
            "INSERT OR IGNORE INTO course_classes(course_id, class_id) VALUES (?, ?)",
            (course_id, class_id),
        )
        row = connection.execute(
            """
            SELECT cc.id, cc.course_id, cc.class_id, c.name AS course_name, cl.name AS class_name, cc.created_at
            FROM course_classes cc
            JOIN courses c ON c.id = cc.course_id
            JOIN classes cl ON cl.id = cc.class_id
            WHERE cc.course_id = ? AND cc.class_id = ?
            """,
            (course_id, class_id),
        ).fetchone()
    return _row_to_dict(row)


def list_sessions(course_id: int | None = None) -> list[dict[str, Any]]:
    from app.services.classroom import refresh_session_statuses

    refresh_session_statuses()
    params: tuple[Any, ...] = ()
    where = ""
    if course_id:
        where = "WHERE s.course_id = ?"
        params = (course_id,)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT s.*, c.name AS course_name, cl.name AS class_name,
                   COUNT(cs.student_id) AS roster_count
            FROM classroom_sessions s
            JOIN courses c ON c.id = s.course_id
            JOIN classes cl ON cl.id = s.class_id
            LEFT JOIN course_students cs ON cs.course_id = s.course_id AND cs.class_id = s.class_id
            {where}
            GROUP BY s.id
            ORDER BY COALESCE(s.start_time, s.created_at) DESC, s.id DESC
            """,
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_session(payload: dict[str, Any]) -> dict[str, Any]:
    course_id = int(payload["course_id"])
    class_id = int(payload["class_id"])
    title = str(payload["title"]).strip()
    session_no = int(payload["session_no"])
    if not title:
        raise AppError("课堂标题不能为空", code="SESSION_TITLE_REQUIRED")
    if session_no <= 0:
        raise AppError("课次必须大于 0", code="SESSION_NO_INVALID")

    with get_connection() as connection:
        linked = connection.execute(
            "SELECT id FROM course_classes WHERE course_id = ? AND class_id = ?",
            (course_id, class_id),
        ).fetchone()
        if linked is None:
            raise AppError("请先关联课程和班级", code="COURSE_CLASS_NOT_LINKED")
        try:
            cursor = connection.execute(
                """
                INSERT INTO classroom_sessions(
                    course_id, class_id, title, session_no, start_time, end_time,
                    is_makeup, schedule_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    class_id,
                    title,
                    session_no,
                    payload.get("start_time"),
                    payload.get("end_time"),
                    1 if payload.get("is_makeup") else 0,
                    payload.get("schedule_note"),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise AppError("同一课程班级下课次已存在", code="SESSION_NO_EXISTS") from exc
            raise
        row = connection.execute("SELECT * FROM classroom_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row)


def parse_excel_upload(file_name: str, file_size: int, content: bytes) -> dict[str, Any]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".xls", ".xlsx"}:
        raise AppError("仅支持 .xls/.xlsx 格式", code="EXCEL_FORMAT_UNSUPPORTED")
    if file_size > MAX_EXCEL_SIZE:
        raise AppError("文件超过 10MB", code="EXCEL_FILE_TOO_LARGE")
    if suffix == ".xls":
        raise AppError("当前环境暂不支持旧版 .xls，请另存为 .xlsx 后上传", code="XLS_NOT_SUPPORTED")

    workbook = load_workbook(filename=BytesIO(content), read_only=True, data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        raise AppError("Excel 内容为空", code="EXCEL_EMPTY")

    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    if not any(headers):
        raise AppError("Excel 表头为空", code="EXCEL_HEADER_EMPTY")

    data_rows: list[dict[str, str]] = []
    for row_index, row in enumerate(rows[1:], start=2):
        item: dict[str, str] = {"__row_number": str(row_index)}
        has_value = False
        for index, header in enumerate(headers):
            if not header:
                continue
            value = row[index] if index < len(row) else None
            normalized = "" if value is None else str(value).strip()
            if normalized:
                has_value = True
            item[header] = normalized
        if has_value:
            data_rows.append(item)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO student_import_jobs(file_name, file_size, headers_json, sample_rows_json, rows_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                file_name,
                file_size,
                json.dumps(headers, ensure_ascii=False),
                json.dumps(data_rows[:5], ensure_ascii=False),
                json.dumps(data_rows, ensure_ascii=False),
            ),
        )
        job_id = cursor.lastrowid

    return {
        "job_id": job_id,
        "file_name": file_name,
        "file_size": file_size,
        "headers": headers,
        "sample_rows": data_rows[:5],
        "total_rows": len(data_rows),
        "standard_fields": STANDARD_FIELDS,
        "required_fields": sorted(REQUIRED_FIELDS),
    }


def _load_import_job(job_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM student_import_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise AppError("导入任务不存在", code="IMPORT_JOB_NOT_FOUND", status_code=404)
    job = _row_to_dict(row)
    job["headers"] = json.loads(str(job["headers_json"]))
    job["rows"] = json.loads(str(job["rows_json"]))
    return job


def preview_import(job_id: int, mapping: dict[str, str]) -> dict[str, Any]:
    preview = _build_import_preview(_load_import_job(job_id), mapping)
    preview.pop("all_rows", None)
    return preview


def _build_import_preview(job: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    reverse_mapping = {standard: source for source, standard in mapping.items() if standard}
    missing = sorted(REQUIRED_FIELDS - set(reverse_mapping))
    if missing:
        raise AppError("必填字段未完成映射：" + "、".join(STANDARD_FIELDS[item] for item in missing), code="IMPORT_MAPPING_REQUIRED")

    seen: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    errors = 0
    warnings = 0
    for raw in job["rows"]:
        normalized = {
            field: str(raw.get(source, "")).strip()
            for field, source in reverse_mapping.items()
        }
        row_errors: list[str] = []
        row_warnings: list[str] = []
        row_number = int(raw.get("__row_number", "0"))
        if not normalized.get("student_id"):
            row_errors.append("学号为空")
        if not normalized.get("name"):
            row_errors.append("姓名为空")
        if not normalized.get("class_name"):
            row_errors.append("班级为空")
        student_number = normalized.get("student_id", "")
        if student_number:
            if student_number in seen:
                row_errors.append(f"学号重复，首次出现在第 {seen[student_number]} 行")
            else:
                seen[student_number] = row_number
        with get_connection() as connection:
            exists = connection.execute(
                "SELECT id FROM students WHERE student_id = ?",
                (student_number,),
            ).fetchone() if student_number else None
        if exists:
            row_warnings.append("学号已存在，确认导入时会更新学生信息")
        errors += len(row_errors)
        warnings += len(row_warnings)
        rows.append(
            {
                "row_number": row_number,
                "data": normalized,
                "errors": row_errors,
                "warnings": row_warnings,
                "valid": not row_errors,
            }
        )

    return {
        "job_id": job["id"],
        "total_rows": len(rows),
        "valid_rows": sum(1 for row in rows if row["valid"]),
        "error_count": errors,
        "warning_count": warnings,
        "all_rows": rows,
        "rows": rows[:50],
    }


def confirm_import(job_id: int, course_id: int, mapping: dict[str, str], import_valid_only: bool = True) -> dict[str, Any]:
    job = _load_import_job(job_id)
    preview = _build_import_preview(job, mapping)
    if preview["error_count"] and not import_valid_only:
        raise AppError("存在错误数据，不能全部导入", code="IMPORT_HAS_ERRORS")

    imported = 0
    skipped = 0
    failed = 0
    with get_connection() as connection:
        course = connection.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        if course is None:
            raise AppError("课程不存在", code="COURSE_NOT_FOUND", status_code=404)

        for row in preview["all_rows"]:
            if not row["valid"]:
                skipped += 1
                continue
            data = row["data"]
            try:
                connection.execute(
                    """
                    INSERT INTO classes(name)
                    VALUES (?)
                    ON CONFLICT(name) DO UPDATE SET updated_at = datetime('now')
                    """,
                    (data["class_name"],),
                )
                class_row = connection.execute("SELECT id FROM classes WHERE name = ?", (data["class_name"],)).fetchone()
                class_id = int(class_row["id"])
                connection.execute(
                    "INSERT OR IGNORE INTO course_classes(course_id, class_id) VALUES (?, ?)",
                    (course_id, class_id),
                )
                connection.execute(
                    """
                    INSERT INTO students(student_id, name, class_id, major, college, grade)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id) DO UPDATE SET
                        name = excluded.name,
                        class_id = excluded.class_id,
                        major = excluded.major,
                        college = excluded.college,
                        grade = excluded.grade,
                        is_active = 1,
                        updated_at = datetime('now')
                    """,
                    (
                        data["student_id"],
                        data["name"],
                        class_id,
                        data.get("major"),
                        data.get("college"),
                        data.get("grade"),
                    ),
                )
                student = connection.execute(
                    "SELECT id FROM students WHERE student_id = ?",
                    (data["student_id"],),
                ).fetchone()
                connection.execute(
                    """
                    INSERT OR IGNORE INTO course_students(course_id, class_id, student_id)
                    VALUES (?, ?, ?)
                    """,
                    (course_id, class_id, int(student["id"])),
                )
                imported += 1
            except Exception:
                failed += 1
    return {"imported": imported, "skipped": skipped, "failed": failed, "total": preview["total_rows"]}


def list_students(course_id: int | None = None, class_id: int | None = None) -> list[dict[str, Any]]:
    params: list[Any] = []
    joins = ""
    where = ["s.is_active = 1"]
    if course_id:
        joins = "JOIN course_students cs ON cs.student_id = s.id"
        where.append("cs.course_id = ?")
        params.append(course_id)
    if class_id:
        where.append("s.class_id = ?")
        params.append(class_id)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT s.id, s.student_id, s.name, s.major, s.college, s.grade,
                   s.class_id, cl.name AS class_name, s.created_at, s.updated_at
            FROM students s
            JOIN classes cl ON cl.id = s.class_id
            {joins}
            WHERE {' AND '.join(where)}
            ORDER BY cl.name, s.student_id
            LIMIT 500
            """,
            tuple(params),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]
