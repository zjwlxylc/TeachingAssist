import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.classroom import router
from app.core.config import AppSettings
from app.core.exceptions import AppError, add_exception_handlers
from app.db import session as db
from app.db.migrations import run_migrations
from app.services import classroom


class ManualSignInTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        settings = AppSettings(storage={"local_root": Path(directory)}).normalized()
        self.enterContext(patch.object(db, "get_settings", return_value=settings))
        self.now = datetime(2026, 9, 26, 10)
        self.enterContext(patch.object(classroom, "_now", side_effect=lambda: self.now))
        run_migrations()
        with db.get_connection() as c:
            c.execute("INSERT INTO courses(id,name) VALUES(1,'Course')")
            c.executemany("INSERT INTO classes(id,name) VALUES(?,?)", [(1, 'A'), (2, 'B')])
            c.execute("INSERT INTO classroom_sessions(id,course_id,title,session_no,status,actual_started_at) VALUES(1,1,'Lesson',1,'active','2026-09-26 08:00:00')")
            c.executemany("INSERT INTO session_classes(session_id,class_id) VALUES(1,?)", [(1,), (2,)])
            for i in range(1, 6):
                c.execute("INSERT INTO students(id,student_id,name,class_id) VALUES(?,?,?,?)", (i, str(i), 'Student', 1 if i < 3 else 2))

    def sign(self, number):
        return classroom.student_sign_in(1, str(number), 'Student', None, None)

    def test_multiple_classes_pause_resume_and_preserve_records(self):
        self.assertEqual(self.sign(1)['status'], 'late')  # Existing automatic rule.
        opened = classroom.set_sign_in_mode(1, 'open')
        self.assertEqual(opened['sign_in_mode'], 'open')
        self.assertEqual(opened['actual_started_at'], '2026-09-26 08:00:00')
        self.assertEqual(self.sign(2)['status'], 'normal')
        classroom.set_sign_in_mode(1, 'paused')
        self.assertEqual(classroom.get_session_public(1)['status'], 'active')
        self.assertEqual(self.sign(3)['status'], 'late')
        classroom.set_sign_in_mode(1, 'open')
        self.now += timedelta(days=1)
        self.assertEqual(self.sign(4)['status'], 'normal')  # No old deadline after resume.
        self.assertEqual(self.sign(3)['status'], 'late')  # Cannot erase earlier tardiness.
        self.assertEqual(self.sign(2)['status'], 'normal')
        self.assertEqual(classroom.get_session_public(1)['sign_in_mode'], 'open')
        self.assertEqual(run_migrations(), [])

    def test_inactive_class_and_invalid_mode_rejected(self):
        for state in ('pending', 'ended'):
            with db.get_connection() as c:
                c.execute('UPDATE classroom_sessions SET status=? WHERE id=1', (state,))
            with self.assertRaises(AppError):
                classroom.set_sign_in_mode(1, 'open')
        with self.assertRaises(AppError):
            classroom.set_sign_in_mode(1, 'unknown')

    def test_teacher_only_api(self):
        from app.api.deps import require_teacher
        app = FastAPI()
        add_exception_handlers(app)
        app.include_router(router)
        with TestClient(app) as client:
            path = '/classroom/sessions/1/sign-in-mode'
            self.assertEqual(client.put(path, json={'mode': 'paused'}).status_code, 401)
            app.dependency_overrides[require_teacher] = lambda: {'name': 'Test teacher'}
            response = client.put(path, json={'mode': 'paused'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['data']['sign_in_mode'], 'paused')
            self.assertEqual(self.sign(5)['status'], 'late')
            self.assertEqual(client.put(path, json={'mode': 'invalid'}).status_code, 422)

    def test_student_session_restores_attendance_and_rejects_invalid_token(self):
        app = FastAPI()
        add_exception_handlers(app)
        app.include_router(router)
        with TestClient(app) as client:
            path = '/classroom/student/session'
            self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get(path, headers={'Authorization': 'Bearer wrong'}).status_code, 401)
            signed = self.sign(1)
            response = client.get(path, headers={'Authorization': 'Bearer ' + signed['token']})
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()['data']
            self.assertEqual((data['student_number'], data['student_name'], data['status']), ('1', 'Student', 'late'))
            self.assertEqual(client.delete(path, headers={'Authorization': 'Bearer ' + signed['token']}).status_code, 200)
            self.assertEqual(client.get(path, headers={'Authorization': 'Bearer ' + signed['token']}).status_code, 401)
