import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.config import AppSettings
from app.core.exceptions import AppError
from app.db import session as db_session
from app.db.migrations import run_migrations
from app.services import ai_chat


class AiClassChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = AppSettings(storage={"local_root": Path(self.temp_dir.name)}).normalized()
        self.settings_patcher = mock.patch.object(db_session, "get_settings", return_value=self.settings)
        self.settings_patcher.start()
        run_migrations()

        with db_session.get_connection() as connection:
            connection.execute("INSERT INTO courses(id, name) VALUES (1, 'C语言程序设计')")
            connection.execute("INSERT INTO classes(id, name) VALUES (1, '测试班')")
            connection.execute(
                "INSERT INTO students(id, student_id, name, class_id) VALUES (1, '20250001', '张三', 1)"
            )
            connection.execute(
                "INSERT INTO classroom_sessions(id, course_id, title, session_no, status, actual_started_at) "
                "VALUES (1, 1, '指针基础知识', 1, 'active', '2026-08-26 13:50:00')"
            )
            connection.execute("INSERT INTO session_classes(session_id, class_id) VALUES (1, 1)")
            connection.execute(
                "INSERT INTO sign_in_records(session_id, student_id, status, sign_time) "
                "VALUES (1, 1, 'normal', '2026-08-26 14:00:00')"
            )
            connection.execute("UPDATE ai_provider_configs SET is_active = 0")
            connection.execute(
                "UPDATE ai_provider_configs SET enabled = 1, is_active = 1, api_key = 'test-key' "
                "WHERE provider_name = 'agnes-ai'"
            )

    def tearDown(self) -> None:
        self.settings_patcher.stop()
        self.temp_dir.cleanup()

    def test_detects_supported_local_data_intents_without_misrouting_coursework_questions(self) -> None:
        detector = getattr(ai_chat, "_detect_data_intent", None)
        self.assertIsNotNone(detector)

        cases = {
            "我的签到情况怎么样？": "sign_in",
            "我签到了吗？": "sign_in",
            "我的签到状态是什么？": "sign_in",
            "本课堂签到状态是什么？": "sign_in",
            "本课堂迟到人数是多少？": "sign_in",
            "本课堂的作业提交情况": "homework",
            "我的作业成绩是多少？": "homework",
            "我的作业提交了吗？": "homework",
            "我的作业交了吗？": "homework",
            "查看课堂答题与判分": "answers",
            "我的答题正确率是多少？": "answers",
            "查询学习评估反馈": "evaluation",
            "我的学习评估反馈": "evaluation",
            "这次作业的要求是什么？": None,
            "提交作业时有什么格式要求？": None,
            "作业提交的命名要求是什么？": None,
            "未交作业的处理规则是什么？": None,
            "正确率如何计算？": None,
            "请假流程是什么？": None,
            "迟到规定是什么？": None,
            "作业成绩怎么算？": None,
            "作业成绩的计算公式是什么？": None,
            "签到情况包括哪些状态？": None,
            "本课堂作业成绩采用百分制吗？": None,
            "学生作业成绩由哪些部分构成？": None,
            "课堂签到情况会怎样影响平时成绩？": None,
            "班级答题正确率的意义是什么？": None,
            "本课堂作业是什么？": None,
            "课堂签到是什么？": None,
            "学生答题是什么？": None,
            "本班评估是什么？": None,
            "解释一下指针的概念": None,
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(detector(question), expected)

    def test_teacher_sign_in_query_uses_local_data_when_provider_times_out(self) -> None:
        provider_timeout = AppError("AI 网络不可达或请求超时", code="AI_NETWORK_FAILED")
        with mock.patch.object(ai_chat.ai_service, "generate_chat", side_effect=provider_timeout):
            result = ai_chat.run_ai_class_chat(
                1,
                [{"role": "user", "content": "签到情况。"}],
                "teacher",
            )

        self.assertEqual(result["intent"], "sign_in")
        self.assertFalse(result["guarded"])
        self.assertEqual(
            result["reply"],
            "本课堂签到统计：应到 1，已签 1（正常 1，迟到 0），缺勤 0，请假 0，未签 0。",
        )

    def test_student_sign_in_query_uses_local_data_when_provider_times_out(self) -> None:
        provider_timeout = AppError("AI 网络不可达或请求超时", code="AI_NETWORK_FAILED")
        with mock.patch.object(ai_chat.ai_service, "generate_chat", side_effect=provider_timeout):
            result = ai_chat.run_ai_class_chat(
                1,
                [{"role": "user", "content": "我的签到情况是怎么样的？"}],
                "student",
                {"student_number": "20250001", "name": "张三"},
            )

        self.assertEqual(result["intent"], "sign_in")
        self.assertFalse(result["guarded"])
        self.assertEqual(result["reply"], "签到状态：正常签到；签到时间：2026-08-26 14:00:00。")

    def test_course_knowledge_uses_one_generation_with_provider_latency_budget(self) -> None:
        with mock.patch.object(
            ai_chat.ai_service,
            "generate_chat",
            return_value="指针是保存内存地址的变量。",
        ) as generate_chat:
            result = ai_chat.run_ai_class_chat(
                1,
                [{"role": "user", "content": "什么是指针？"}],
                "teacher",
            )

        self.assertEqual(result["intent"], "knowledge")
        self.assertFalse(result["guarded"])
        self.assertEqual(result["reply"], "指针是保存内存地址的变量。")
        generate_chat.assert_called_once()
        self.assertEqual(generate_chat.call_args.kwargs["timeout"], 90)


if __name__ == "__main__":
    unittest.main()
