import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.config import AppSettings
from app.db import session as db_session
from app.db.migrations import run_migrations
from app.services import questions


class QuestionAnswersDetailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = AppSettings(storage={"local_root": Path(self.temp_dir.name)}).normalized()
        self.settings_patcher = mock.patch.object(db_session, "get_settings", return_value=self.settings)
        self.settings_patcher.start()
        run_migrations()

        with db_session.get_connection() as connection:
            connection.execute("INSERT INTO courses(id, name) VALUES (1, 'C 语言程序设计')")
            connection.execute("INSERT INTO classes(id, name) VALUES (1, '测试班')")
            connection.execute(
                "INSERT INTO classroom_sessions(id, course_id, title, session_no, status) "
                "VALUES (1, 1, '指针基础知识', 1, 'active')"
            )
            connection.execute(
                "INSERT INTO students(id, student_id, name, class_id) VALUES (1, '20250002', '李四', 1)"
            )
            connection.execute(
                "INSERT INTO students(id, student_id, name, class_id) VALUES (2, '20250001', '张三', 1)"
            )
            connection.execute(
                "INSERT INTO questions(id, session_id, title, content, question_type, status) "
                "VALUES (1, 1, '定义一个指针变量 p', '请写出定义语句', 'short_answer', 'published')"
            )
            connection.execute(
                "INSERT INTO question_answers(question_id, session_id, student_id, answer_text, status, "
                "is_latest, submitted_at) VALUES (1, 1, 1, 'int *p;', 'submitted', 1, '2026-08-08 10:01:00')"
            )
            connection.execute(
                "INSERT INTO question_answers(question_id, session_id, student_id, answer_text, status, "
                "is_latest, submitted_at) VALUES (1, 1, 2, 'int* p;', 'submitted', 1, '2026-08-08 10:02:00')"
            )

    def tearDown(self) -> None:
        self.settings_patcher.stop()
        self.temp_dir.cleanup()

    def test_returns_answer_details_ordered_by_student_id(self) -> None:
        result = questions.get_question_answers_detail(1)

        self.assertEqual(result["question"]["title"], "定义一个指针变量 p")
        self.assertEqual(result["total"], 2)
        self.assertEqual(
            [answer["student_number"] for answer in result["answers"]],
            ["20250001", "20250002"],
        )
        self.assertEqual(result["answers"][0]["student_name"], "张三")


if __name__ == "__main__":
    unittest.main()
