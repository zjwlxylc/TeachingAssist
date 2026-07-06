import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings


BAD_KEYWORDS = ("stage", "smoke", "alice", "bob", "test", "demo", "示例", "测试")
ACADEMIC_TABLES = (
    "courses",
    "classes",
    "students",
    "classroom_sessions",
    "questions",
    "homework",
    "student_import_jobs",
    "student_import_reports",
)


def looks_corrupted(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if "\ufffd" in text:
        return True
    question_count = text.count("?")
    visible_count = sum(1 for char in text if not char.isspace())
    return question_count >= 2 and visible_count > 0 and question_count / visible_count >= 0.3


def looks_trial_name(value: object) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return looks_corrupted(text) or any(keyword in text for keyword in BAD_KEYWORDS)


def ids_for(connection: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> set[int]:
    return {int(row["id"]) for row in connection.execute(sql, params).fetchall()}


def collect_targets(connection: sqlite3.Connection) -> dict[str, set[int]]:
    targets = {table: set() for table in ACADEMIC_TABLES}

    targets["courses"] |= ids_for(connection, "SELECT id FROM courses WHERE lower(name) LIKE '%stage%' OR lower(name) LIKE '%smoke%'")
    targets["courses"] |= {int(row["id"]) for row in connection.execute("SELECT id, name, teacher_name FROM courses").fetchall() if looks_trial_name(row["name"]) or looks_trial_name(row["teacher_name"])}

    targets["classes"] |= ids_for(connection, "SELECT id FROM classes WHERE lower(name) LIKE '%stage%' OR lower(name) LIKE '%smoke%'")
    targets["classes"] |= {int(row["id"]) for row in connection.execute("SELECT id, name FROM classes").fetchall() if looks_trial_name(row["name"])}

    targets["students"] |= ids_for(connection, "SELECT id FROM students WHERE lower(name) IN ('alice', 'bob')")
    targets["students"] |= {int(row["id"]) for row in connection.execute("SELECT id, student_id, name, major, college FROM students").fetchall() if looks_trial_name(row["student_id"]) or looks_trial_name(row["name"]) or looks_trial_name(row["major"]) or looks_trial_name(row["college"])}

    targets["classroom_sessions"] |= ids_for(
        connection,
        "SELECT id FROM classroom_sessions WHERE lower(title) LIKE '%stage%' OR lower(title) LIKE '%smoke%'",
    )
    targets["classroom_sessions"] |= {int(row["id"]) for row in connection.execute("SELECT id, title FROM classroom_sessions").fetchall() if looks_trial_name(row["title"])}

    if targets["courses"]:
        placeholders = ",".join("?" for _ in targets["courses"])
        targets["classroom_sessions"] |= ids_for(connection, f"SELECT id FROM classroom_sessions WHERE course_id IN ({placeholders})", tuple(targets["courses"]))
    if targets["classes"]:
        placeholders = ",".join("?" for _ in targets["classes"])
        targets["classroom_sessions"] |= ids_for(connection, f"SELECT id FROM classroom_sessions WHERE class_id IN ({placeholders})", tuple(targets["classes"]))
        targets["students"] |= ids_for(connection, f"SELECT id FROM students WHERE class_id IN ({placeholders})", tuple(targets["classes"]))

    targets["questions"] |= {int(row["id"]) for row in connection.execute("SELECT id, title, content FROM questions").fetchall() if looks_trial_name(row["title"]) or looks_trial_name(row["content"])}
    targets["homework"] |= {int(row["id"]) for row in connection.execute("SELECT id, title, description, grading_criteria FROM homework").fetchall() if looks_trial_name(row["title"]) or looks_trial_name(row["description"]) or looks_trial_name(row["grading_criteria"])}
    targets["student_import_jobs"] |= {
        int(row["id"])
        for row in connection.execute(
            "SELECT id, file_name, headers_json, sample_rows_json, rows_json FROM student_import_jobs"
        ).fetchall()
        if looks_trial_name(row["file_name"])
        or looks_trial_name(row["headers_json"])
        or looks_trial_name(row["sample_rows_json"])
        or looks_trial_name(row["rows_json"])
    }

    if targets["student_import_jobs"]:
        placeholders = ",".join("?" for _ in targets["student_import_jobs"])
        targets["student_import_reports"] |= ids_for(
            connection,
            f"SELECT id FROM student_import_reports WHERE job_id IN ({placeholders})",
            tuple(targets["student_import_jobs"]),
        )

    if targets["classroom_sessions"]:
        placeholders = ",".join("?" for _ in targets["classroom_sessions"])
        params = tuple(targets["classroom_sessions"])
        targets["questions"] |= ids_for(connection, f"SELECT id FROM questions WHERE session_id IN ({placeholders})", params)
        targets["homework"] |= ids_for(connection, f"SELECT id FROM homework WHERE session_id IN ({placeholders})", params)

    return targets


def count_rows(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ACADEMIC_TABLES
    }


def delete_ids(connection: sqlite3.Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    cursor = connection.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", tuple(ids))
    return int(cursor.rowcount if cursor.rowcount is not None else 0)


def cleanup_orphan_links(connection: sqlite3.Connection) -> dict[str, int]:
    deleted: dict[str, int] = {}
    cursor = connection.execute(
        """
        DELETE FROM course_students
        WHERE course_id NOT IN (SELECT id FROM courses)
           OR class_id NOT IN (SELECT id FROM classes)
           OR student_id NOT IN (SELECT id FROM students)
           OR class_id != (SELECT class_id FROM students WHERE students.id = course_students.student_id)
        """
    )
    deleted["course_students_orphans"] = int(cursor.rowcount if cursor.rowcount is not None else 0)
    cursor = connection.execute(
        """
        DELETE FROM course_classes
        WHERE course_id NOT IN (SELECT id FROM courses)
           OR class_id NOT IN (SELECT id FROM classes)
        """
    )
    deleted["course_classes_orphans"] = int(cursor.rowcount if cursor.rowcount is not None else 0)
    cursor = connection.execute(
        """
        DELETE FROM classes
        WHERE id NOT IN (SELECT class_id FROM students)
          AND id NOT IN (SELECT class_id FROM course_classes)
        """
    )
    deleted["classes_orphans"] = int(cursor.rowcount if cursor.rowcount is not None else 0)
    return deleted


def print_summary(title: str, values: dict[str, int] | dict[str, set[int]]) -> None:
    print(title)
    for key in sorted(values):
        value = values[key]
        if isinstance(value, set):
            print(f"  {key}: {len(value)} {sorted(value)}")
        else:
            print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean obvious trial/smoke/corrupted academic data.")
    parser.add_argument("--apply", action="store_true", help="Apply deletion. Without this flag only prints a preview.")
    args = parser.parse_args()

    database_path = get_settings().storage.database_path
    if database_path is None:
        raise RuntimeError("Database path is not configured")

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        before = count_rows(connection)
        targets = collect_targets(connection)

    print(f"Database: {database_path}")
    print_summary("Before:", before)
    print_summary("Matched trial/corrupted records:", targets)

    if not args.apply:
        print("Preview only. Re-run with --apply to clean these records.")
        return

    backup_path = database_path.with_suffix(database_path.suffix + f".trial-cleanup-{datetime.now():%Y%m%d%H%M%S}.bak")
    shutil.copy2(database_path, backup_path)
    wal_path = Path(str(database_path) + "-wal")
    shm_path = Path(str(database_path) + "-shm")
    if wal_path.exists():
        shutil.copy2(wal_path, Path(str(backup_path) + "-wal"))
    if shm_path.exists():
        shutil.copy2(shm_path, Path(str(backup_path) + "-shm"))

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        targets = collect_targets(connection)
        deleted = {
            "questions": delete_ids(connection, "questions", targets["questions"]),
            "homework": delete_ids(connection, "homework", targets["homework"]),
            "student_import_reports": delete_ids(connection, "student_import_reports", targets["student_import_reports"]),
            "student_import_jobs": delete_ids(connection, "student_import_jobs", targets["student_import_jobs"]),
            "classroom_sessions": delete_ids(connection, "classroom_sessions", targets["classroom_sessions"]),
            "students": delete_ids(connection, "students", targets["students"]),
            "courses": delete_ids(connection, "courses", targets["courses"]),
        }
        deleted.update(cleanup_orphan_links(connection))
        deleted["classes"] = delete_ids(connection, "classes", collect_targets(connection)["classes"])
        second_pass = cleanup_orphan_links(connection)
        for key, value in second_pass.items():
            deleted[key] = deleted.get(key, 0) + value
        connection.commit()
        after = count_rows(connection)

    print(f"Backup: {backup_path}")
    print_summary("Deleted:", deleted)
    print_summary("After:", after)


if __name__ == "__main__":
    main()
