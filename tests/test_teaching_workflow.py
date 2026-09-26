import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.router import api_router
from app.api.routes.announcements import ws_router
from app.core import config
from app.core.exceptions import add_exception_handlers
from app.db import session as db
from app.db.migrations import run_migrations
from app.services import auth, backup, homework, network


class TeachingWorkflowTests(unittest.TestCase):
    def test_offline_teaching_workflow(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            settings = config.AppSettings(storage={"local_root": Path(directory)}).normalized()
            for module in (config, db, backup, homework, network):
                stack.enter_context(mock.patch.object(module, "get_settings", return_value=settings))
            stack.enter_context(mock.patch.object(backup, "detect_removable_root", return_value=None))
            run_migrations()
            auth.initialize_default_teacher_password("test123")
            app = FastAPI()
            add_exception_handlers(app)
            app.include_router(api_router, prefix="/api/v1")
            app.include_router(ws_router)
            client = stack.enter_context(TestClient(app))
            headers = {}

            def call(method, path, **kwargs):
                response = client.request(method, "/api/v1" + path, headers=headers, **kwargs)
                self.assertEqual(response.status_code, 200, f"{method} {path}: {response.text}")
                self.assertTrue(response.json()["success"], response.text)
                return response.json()["data"]

            self.assertEqual(client.get('/api/v1/academic/courses').status_code, 401)
            token = call("POST", "/auth/login", json={"password": "test123"})["token"]
            headers["Authorization"] = "Bearer " + token
            course = call("POST", "/academic/courses", json={"name": "Regression course"})["id"]
            klass = call("POST", "/academic/classes", json={"name": "Regression class"})["id"]
            call("POST", "/academic/course-classes", json={"course_id": course, "class_id": klass})
            self.assertEqual(call("GET", f"/academic/classes?course_id={course}")[0]["id"], klass)
            workbook = Workbook()
            workbook.active.append(["学号", "姓名"])
            workbook.active.append(["20260001", "测试学生"])
            stream = BytesIO()
            workbook.save(stream)
            job = call("POST", "/academic/imports/excel", files={"file": ("students.xlsx", stream.getvalue())})["job_id"]
            mapping = {"学号": "student_id", "姓名": "name"}
            call("POST", f"/academic/imports/{job}/preview", json={"mapping": mapping})
            call("POST", f"/academic/imports/{job}/confirm", json={"mapping": mapping, "class_id": klass})
            students = call("GET", f"/academic/students?class_id={klass}")
            self.assertEqual(len(students), 1)
            student = {"student_id": "20260001", "name": "测试学生"}
            session = call("POST", "/academic/sessions", json={"course_id": course, "class_ids": [klass], "title": "Regression lesson", "session_no": 1})["id"]
            call("POST", f"/classroom/sessions/{session}/start")
            signed = call("POST", f"/classroom/sessions/{session}/sign-in", json=student)
            self.assertTrue(signed["token"])
            signed = call("POST", f"/classroom/sessions/{session}/sign-in", json=student)
            with client.websocket_connect(f"/ws/classroom/{session}") as ws:
                call("POST", f"/announcements/sessions/{session}", json={"content": "Regression announcement"})
                self.assertIn("Regression announcement", ws.receive_text())
            question = call("POST", f"/questions/sessions/{session}", json={"title": "Check", "content": "1+1=2", "question_type": "true_false", "correct_answer": True})["id"]
            call("POST", f"/questions/{question}/answers", json={**student, "answer": "T"})
            call("GET", f"/questions/{question}/stats")
            deadline = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
            assignment = call("POST", f"/homework/sessions/{session}", json={"title": "Regression homework", "deadline": deadline})["id"]
            attached = call("POST", f"/homework/{assignment}/attachments", files={"files": ("作业要求.txt", b"Assignment instructions", "text/plain")})
            attachment_id = attached["attachments"][0]["id"]
            downloaded = client.get(f"/api/v1/homework/attachments/{attachment_id}/download")
            self.assertEqual(downloaded.status_code, 200, downloaded.text)
            self.assertEqual(downloaded.content, b"Assignment instructions")
            self.assertIn("filename*=utf-8", downloaded.headers["content-disposition"])
            submitted = call("POST", f"/homework/{assignment}/submissions", data={**student, "text_content": "Answer"}, files={"files": ("answer.txt", b"Student answer", "text/plain")})
            submission_id = submitted["id"]
            summary = call("GET", f"/homework/{assignment}/submissions")
            file_id = summary["records"][0]["files"][0]["id"]
            file_url = f"/api/v1/homework/submission-files/{file_id}/download"
            self.assertEqual(client.get(file_url).status_code, 401)
            self.assertEqual(client.get(file_url, headers={"Authorization": "Bearer " + signed["token"]}).status_code, 401)
            self.assertEqual(client.get(file_url, headers=headers).content, b"Student answer")
            self.assertEqual(client.get("/api/v1/homework/attachments/999999/download").status_code, 404)
            with db.get_connection() as connection:
                connection.execute("UPDATE homework_attachments SET file_path = ? WHERE id = ?", (str(settings.storage.database_path), attachment_id))
            self.assertEqual(client.get(f"/api/v1/homework/attachments/{attachment_id}/download").status_code, 404)
            call("PUT", f"/homework/submissions/{submission_id}/review", json={"final_score": 90, "final_feedback": "Reviewed"})
            call("POST", f"/homework/{assignment}/publish-grades")
            call("POST", f"/homework/{assignment}/feedback", json={**student, "token": signed["token"]})
            call("PUT", f"/interactions/sessions/{session}/settings", json={"student_messages_enabled": True})
            call("POST", f"/interactions/sessions/{session}/messages/student", json={**student, "content": "Question"})
            call("POST", "/messages", json={**student, "token": signed["token"], "content": "Private question"})
            call("POST", f"/messages/students/{students[0]['id']}/reply", json={"content": "Reply"})
            call("POST", f"/evaluation/sessions/{session}/calculate", json={"version_type": "temporary"})
            for path in [f"/classroom/sessions/{session}/sign-ins.csv", f"/questions/sessions/{session}/answers.csv", f"/homework/{assignment}/submissions.csv", f"/evaluation/sessions/{session}.csv"]:
                response = client.get("/api/v1" + path, headers=headers)
                self.assertEqual(response.status_code, 200, path + ': ' + response.text)
                self.assertIn("text/csv", response.headers["content-type"])
            call("POST", f"/classroom/sessions/{session}/end")
            backups = call("POST", "/system/backups")
            self.assertTrue(all(item["status"] == "success" for item in backups))
            call("POST", "/system/backups/restore", json={"file_path": backups[0]["file_path"]})
            with db.get_connection() as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
