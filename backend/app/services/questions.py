import json
from datetime import datetime
from typing import Any

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.classroom import get_session_public
from app.services.realtime import manager


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "fill_blank", "short_answer"}
CHOICE_TYPES = {"single_choice", "multiple_choice", "true_false"}
MAX_CONTENT_LENGTH = 2000


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _to_db_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("T", " ")
    if len(normalized) == 16:
        normalized = f"{normalized}:00"
    return datetime.strptime(normalized[:19], TIME_FORMAT)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_answer_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def _load_question(connection: Any, question_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT q.*, s.title AS session_title
        FROM questions q
        JOIN classroom_sessions s ON s.id = q.session_id
        WHERE q.id = ?
        """,
        (question_id,),
    ).fetchone()
    if row is None:
        raise AppError("问题不存在", code="QUESTION_NOT_FOUND", status_code=404)
    question = _row_to_dict(row)
    question["correct_answer"] = _json_loads(question.get("correct_answer_json"), None)
    question["keywords"] = _json_loads(question.get("keywords_json"), [])
    question["options"] = _load_options(connection, question_id)
    return question


def _load_options(connection: Any, question_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, question_id, option_key, content, is_correct, display_order, created_at
        FROM question_options
        WHERE question_id = ?
        ORDER BY display_order, option_key
        """,
        (question_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _public_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = {
        "id": question["id"],
        "session_id": question["session_id"],
        "title": question["title"],
        "content": question["content"],
        "question_type": question["question_type"],
        "status": question["status"],
        "start_time": question["start_time"],
        "deadline": question["deadline"],
        "score": question["score"],
        "created_at": question["created_at"],
        "published_at": question["published_at"],
        "updated_at": question["updated_at"],
        "options": [
            {
                "id": option["id"],
                "option_key": option["option_key"],
                "content": option["content"],
                "display_order": option["display_order"],
            }
            for option in question.get("options", [])
        ],
    }
    if include_answer:
        result["correct_answer"] = question.get("correct_answer")
        result["keywords"] = question.get("keywords", [])
    return result


def _validate_session_active(session_id: int) -> dict[str, Any]:
    session = get_session_public(session_id)
    if session["status"] != "active":
        raise AppError("课堂未处于进行中，不能发布或提交问答", code="SESSION_NOT_ACTIVE", status_code=409)
    return session


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = _normalize_text(payload.get("title"))
    content = _normalize_text(payload.get("content"))
    question_type = _normalize_text(payload.get("question_type"))
    if not title:
        raise AppError("问题标题不能为空", code="QUESTION_TITLE_REQUIRED")
    if not content:
        raise AppError("问题内容不能为空", code="QUESTION_CONTENT_REQUIRED")
    if len(content) > MAX_CONTENT_LENGTH:
        raise AppError("问题内容不能超过 2000 字", code="QUESTION_CONTENT_TOO_LONG")
    if question_type not in QUESTION_TYPES:
        raise AppError("题型不支持", code="QUESTION_TYPE_UNSUPPORTED")

    score = float(payload.get("score") or 1)
    if score <= 0:
        raise AppError("题目分值必须大于 0", code="QUESTION_SCORE_INVALID")

    correct_answer = payload.get("correct_answer")
    options = payload.get("options") or []
    keywords = _normalize_answer_list(payload.get("keywords") or [])
    if question_type in CHOICE_TYPES:
        if question_type == "true_false" and not options:
            options = [
                {"option_key": "T", "content": "正确", "is_correct": correct_answer in [True, "true", "T", "正确"]},
                {"option_key": "F", "content": "错误", "is_correct": correct_answer in [False, "false", "F", "错误"]},
            ]
        if len(options) < 2:
            raise AppError("客观题至少需要两个选项", code="QUESTION_OPTIONS_REQUIRED")
        normalized_options = []
        correct_keys: list[str] = []
        seen_keys: set[str] = set()
        for index, option in enumerate(options):
            key = _normalize_text(option.get("option_key")).upper()
            text = _normalize_text(option.get("content"))
            if not key:
                key = chr(ord("A") + index)
            if not text:
                raise AppError("选项内容不能为空", code="QUESTION_OPTION_CONTENT_REQUIRED")
            if key in seen_keys:
                raise AppError("选项标识不能重复", code="QUESTION_OPTION_DUPLICATED")
            seen_keys.add(key)
            is_correct = bool(option.get("is_correct"))
            if is_correct:
                correct_keys.append(key)
            normalized_options.append(
                {
                    "option_key": key,
                    "content": text,
                    "is_correct": 1 if is_correct else 0,
                    "display_order": int(option.get("display_order") or index),
                }
            )
        if not correct_keys and correct_answer is not None:
            correct_keys = _normalize_answer_list(correct_answer)
            for option in normalized_options:
                option["is_correct"] = 1 if option["option_key"] in correct_keys else 0
        if question_type == "single_choice" and len(correct_keys) != 1:
            raise AppError("单选题必须且只能设置一个正确答案", code="QUESTION_SINGLE_ANSWER_REQUIRED")
        if question_type == "multiple_choice" and not correct_keys:
            raise AppError("多选题至少需要一个正确答案", code="QUESTION_MULTI_ANSWER_REQUIRED")
        if question_type == "true_false" and len(correct_keys) != 1:
            raise AppError("判断题必须设置正确或错误", code="QUESTION_TRUE_FALSE_ANSWER_REQUIRED")
        correct_answer = sorted(correct_keys)
    else:
        normalized_options = []
        if question_type == "fill_blank":
            correct_answer = _normalize_answer_list(correct_answer)
            if not correct_answer and not keywords:
                raise AppError("填空题需设置标准答案或关键词", code="QUESTION_FILL_ANSWER_REQUIRED")
        else:
            correct_answer = _normalize_text(correct_answer)

    return {
        "title": title,
        "content": content,
        "question_type": question_type,
        "options": normalized_options,
        "correct_answer": correct_answer,
        "keywords": keywords,
        "score": score,
        "start_time": payload.get("start_time"),
        "deadline": payload.get("deadline"),
    }


def _log_action(
    connection: Any,
    session_id: int,
    question_id: int | None,
    student_id: int | None,
    action_type: str,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO question_action_logs(session_id, question_id, student_id, action_type, details_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, question_id, student_id, action_type, json.dumps(details or {}, ensure_ascii=False)),
    )


async def create_question(session_id: int, payload: dict[str, Any], teacher_name: str = "教师") -> dict[str, Any]:
    _validate_session_active(session_id)
    data = _validate_payload(payload)
    now = datetime.now()
    start_time = _parse_time(data.get("start_time")) or now
    deadline = _parse_time(data.get("deadline"))
    if deadline and deadline <= start_time:
        raise AppError("截止时间必须晚于开始时间", code="QUESTION_DEADLINE_INVALID")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO questions(
                session_id, title, content, question_type, status, start_time, deadline,
                correct_answer_json, keywords_json, score, published_at
            )
            VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                data["title"],
                data["content"],
                data["question_type"],
                _to_db_time(start_time),
                _to_db_time(deadline) if deadline else None,
                json.dumps(data["correct_answer"], ensure_ascii=False),
                json.dumps(data["keywords"], ensure_ascii=False),
                data["score"],
                _to_db_time(now),
            ),
        )
        question_id = int(cursor.lastrowid)
        for option in data["options"]:
            connection.execute(
                """
                INSERT INTO question_options(question_id, option_key, content, is_correct, display_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    option["option_key"],
                    option["content"],
                    option["is_correct"],
                    option["display_order"],
                ),
            )
        _log_action(connection, session_id, question_id, None, "publish_question", {"teacher_name": teacher_name})
        question = _load_question(connection, question_id)

    await manager.broadcast(
        session_id,
        {
            "type": "question.published",
            "session_id": session_id,
            "question": _public_question(question),
        },
    )
    return _public_question(question, include_answer=True)


def list_questions(session_id: int, include_answer: bool = True, public_only: bool = False) -> list[dict[str, Any]]:
    get_session_public(session_id)
    where = "WHERE q.session_id = ?"
    if public_only:
        where += " AND q.status = 'published'"
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT q.*
            FROM questions q
            {where}
            ORDER BY q.id DESC
            """,
            (session_id,),
        ).fetchall()
        questions = []
        for row in rows:
            question = _row_to_dict(row)
            question["correct_answer"] = _json_loads(question.get("correct_answer_json"), None)
            question["keywords"] = _json_loads(question.get("keywords_json"), [])
            question["options"] = _load_options(connection, int(question["id"]))
            questions.append(_public_question(question, include_answer=include_answer))
    return questions


def _resolve_student(connection: Any, session: dict[str, Any], student_number: str, name: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT s.*
        FROM students s
        JOIN course_students cs ON cs.student_id = s.id
        WHERE s.student_id = ?
          AND cs.course_id = ?
          AND cs.class_id = ?
          AND s.is_active = 1
        """,
        (student_number.strip(), session["course_id"], session["class_id"]),
    ).fetchone()
    if row is None:
        raise AppError("未找到该学号，或不在本课堂名单中", code="STUDENT_NOT_FOUND", status_code=404)
    student = _row_to_dict(row)
    if str(student["name"]).strip() != name.strip():
        raise AppError("学号与姓名不匹配", code="STUDENT_NAME_MISMATCH", status_code=409)
    return student


def _grade_answer(question: dict[str, Any], answer: Any, status: str) -> tuple[int | None, float]:
    if status != "submitted":
        return None, 0
    question_type = question["question_type"]
    score = float(question.get("score") or 1)
    correct_answer = question.get("correct_answer")
    keywords = question.get("keywords") or []

    if question_type in {"single_choice", "true_false"}:
        expected = set(_normalize_answer_list(correct_answer))
        actual = set(_normalize_answer_list(answer))
        is_correct = expected == actual and len(actual) == 1
        return (1 if is_correct else 0), score if is_correct else 0
    if question_type == "multiple_choice":
        expected = set(_normalize_answer_list(correct_answer))
        actual = set(_normalize_answer_list(answer))
        is_correct = expected == actual
        return (1 if is_correct else 0), score if is_correct else 0
    if question_type == "fill_blank":
        actual_text = _normalize_text(answer).lower()
        standard_answers = [_normalize_text(item).lower() for item in _normalize_answer_list(correct_answer)]
        keyword_answers = [_normalize_text(item).lower() for item in keywords]
        is_correct = actual_text in standard_answers if standard_answers else False
        if not is_correct and keyword_answers:
            is_correct = all(keyword in actual_text for keyword in keyword_answers)
        return (1 if is_correct else 0), score if is_correct else 0
    return None, 0


async def submit_answer(
    question_id: int,
    student_number: str,
    name: str,
    answer: Any,
    action: str = "submit_answer",
) -> dict[str, Any]:
    if action not in {"start_answer", "save_draft", "submit_answer", "timeout_submit", "view_feedback"}:
        raise AppError("答题行为不支持", code="QUESTION_ACTION_UNSUPPORTED")
    if not student_number.strip() or not name.strip():
        raise AppError("学号和姓名不能为空", code="STUDENT_ID_NAME_REQUIRED")

    with get_connection() as connection:
        question = _load_question(connection, question_id)
        session = get_session_public(int(question["session_id"]))
        if session["status"] != "active":
            raise AppError("课堂未处于进行中，不能提交答案", code="SESSION_NOT_ACTIVE", status_code=409)
        if question["status"] != "published":
            raise AppError("问题未发布或已关闭", code="QUESTION_NOT_OPEN", status_code=409)
        student = _resolve_student(connection, session, student_number, name)

        now = datetime.now()
        deadline = _parse_time(question.get("deadline"))
        status = "draft" if action in {"start_answer", "save_draft"} else "submitted"
        if action == "timeout_submit" or (deadline and now > deadline and status == "submitted"):
            status = "timeout"

        is_correct, answer_score = _grade_answer(question, answer, status)
        latest = connection.execute(
            """
            SELECT submit_version
            FROM question_answers
            WHERE question_id = ? AND student_id = ? AND is_latest = 1
            """,
            (question_id, student["id"]),
        ).fetchone()
        submit_version = int(latest["submit_version"]) + 1 if latest else 1
        connection.execute(
            "UPDATE question_answers SET is_latest = 0 WHERE question_id = ? AND student_id = ? AND is_latest = 1",
            (question_id, student["id"]),
        )
        answer_list = answer if isinstance(answer, list) else None
        answer_text = "" if answer is None else (json.dumps(answer, ensure_ascii=False) if isinstance(answer, list) else str(answer))
        cursor = connection.execute(
            """
            INSERT INTO question_answers(
                question_id, session_id, student_id, answer_json, answer_text, status,
                is_correct, score, submit_version, is_latest, started_at, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                question_id,
                question["session_id"],
                student["id"],
                json.dumps(answer_list if answer_list is not None else answer, ensure_ascii=False),
                answer_text,
                status,
                is_correct,
                answer_score,
                submit_version,
                _to_db_time(now) if action == "start_answer" else None,
                _to_db_time(now) if status in {"submitted", "timeout"} else None,
            ),
        )
        _log_action(connection, int(question["session_id"]), question_id, int(student["id"]), action, {"status": status})
        row = connection.execute(
            """
            SELECT qa.*, s.student_id AS student_number, s.name AS student_name
            FROM question_answers qa
            JOIN students s ON s.id = qa.student_id
            WHERE qa.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        result = _row_to_dict(row)

    await manager.broadcast(
        int(question["session_id"]),
        {
            "type": "question.answer.updated",
            "session_id": int(question["session_id"]),
            "question_id": question_id,
            "student_id": result["student_number"],
            "status": result["status"],
        },
    )
    return result


def get_question_stats(question_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        question = _load_question(connection, question_id)
        session = get_session_public(int(question["session_id"]))
        roster = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM course_students
            WHERE course_id = ? AND class_id = ?
            """,
            (session["course_id"], session["class_id"]),
        ).fetchone()
        total_students = int(roster["total"] if roster else 0)
        answers = connection.execute(
            """
            SELECT qa.*, s.student_id AS student_number, s.name AS student_name
            FROM question_answers qa
            JOIN students s ON s.id = qa.student_id
            WHERE qa.question_id = ? AND qa.is_latest = 1
            ORDER BY qa.submitted_at DESC, qa.updated_at DESC, qa.id DESC
            """,
            (question_id,),
        ).fetchall()

    answer_items = [_row_to_dict(row) for row in answers]
    submitted = [item for item in answer_items if item["status"] in {"submitted", "timeout"}]
    correct_count = sum(1 for item in submitted if item.get("is_correct") == 1)
    submitted_count = len(submitted)
    option_distribution: dict[str, int] = {}
    if question["question_type"] in CHOICE_TYPES:
        for option in question["options"]:
            option_distribution[option["option_key"]] = 0
        for item in submitted:
            for selected in _normalize_answer_list(_json_loads(item.get("answer_json"), item.get("answer_text"))):
                option_distribution[selected] = option_distribution.get(selected, 0) + 1

    typical_answers = []
    if question["question_type"] in {"fill_blank", "short_answer"}:
        counts: dict[str, int] = {}
        for item in submitted:
            text = _normalize_text(item.get("answer_text"))
            if text:
                counts[text] = counts.get(text, 0) + 1
        typical_answers = [
            {"answer": answer, "count": count}
            for answer, count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:10]
        ]

    return {
        "question": _public_question(question, include_answer=True),
        "total_students": total_students,
        "submitted_count": submitted_count,
        "draft_count": sum(1 for item in answer_items if item["status"] == "draft"),
        "correct_count": correct_count,
        "correct_rate": round((correct_count / submitted_count) * 100, 2) if submitted_count else 0,
        "option_distribution": option_distribution,
        "typical_answers": typical_answers,
        "answers": answer_items[:100],
    }
