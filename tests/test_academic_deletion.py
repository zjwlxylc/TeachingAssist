import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_teacher
from app.api.routes.academic import router
from app.core.config import AppSettings
from app.core.exceptions import add_exception_handlers
from app.db import session as db
from app.db.migrations import run_migrations


class AcademicDeletionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.settings = AppSettings(storage={'local_root': self.root}).normalized()
        self.enterContext(patch.object(db, 'get_settings', return_value=self.settings))
        run_migrations()
        self.app = FastAPI()
        add_exception_handlers(self.app)
        self.app.include_router(router)
        self.app.dependency_overrides[require_teacher] = lambda: {'id': 1, 'name': 'Teacher'}
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=False))
        with db.get_connection() as c:
            c.execute("INSERT INTO courses(id,name) VALUES(1,'Course')")
            c.executemany("INSERT INTO classes(id,name) VALUES(?,?)", [(1, 'A'), (2, 'B')])
            c.executemany("INSERT INTO course_classes(course_id,class_id) VALUES(1,?)", [(1,), (2,)])
            c.executemany("INSERT INTO classroom_sessions(id,course_id,title,session_no,status) VALUES(?,1,?,?,'pending')", [(1, 'Lesson', 1), (2, 'Other', 2)])
            c.executemany("INSERT INTO session_classes(session_id,class_id) VALUES(?,?)", [(1, 1), (2, 2)])
            c.executemany("INSERT INTO students(id,student_id,name,class_id) VALUES(?,?,?,?)", [(1, '001', 'One', 1), (2, '002', 'Two', 2)])

    def preview(self, kind='sessions', id=1):
        r = self.client.get(f'/academic/{kind}/{id}/deletion-preview')
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['data']

    def delete(self, kind='sessions', id=1, preview=None, name=None):
        p = preview or self.preview(kind, id)
        return self.client.request('DELETE', f'/academic/{kind}/{id}', json={
            'confirmation_name': p['name'] if name is None else name,
            'preview_token': p['preview_token'],
        })

    def test_teacher_only(self):
        self.app.dependency_overrides.clear()
        for kind in ('classes', 'sessions'):
            self.assertEqual(self.client.get(f'/academic/{kind}/1/deletion-preview').status_code, 401)
            self.assertEqual(self.client.request('DELETE', f'/academic/{kind}/1', json={'confirmation_name': 'A', 'preview_token': 'x'}).status_code, 401)

    def test_name_confirmation_and_session_scope(self):
        self.assertEqual(self.delete(name='wrong').status_code, 409)
        self.assertEqual(self.delete().status_code, 200)
        with db.get_connection() as c:
            self.assertEqual(c.execute('SELECT id FROM classroom_sessions').fetchall()[0][0], 2)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM students').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM classes').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM courses').fetchone()[0], 1)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.client.get('/academic/sessions/1/deletion-preview').status_code, 404)

    def test_active_and_changed_data_rejected(self):
        p = self.preview()
        with db.get_connection() as c:
            c.execute("UPDATE classroom_sessions SET status='active' WHERE id=1")
        self.assertFalse(self.preview()['can_delete'])
        self.assertEqual(self.delete(preview=p).status_code, 409)
        with db.get_connection() as c:
            c.execute("UPDATE classroom_sessions SET status='ended' WHERE id=1")
            c.execute("INSERT INTO announcements(session_id,sender_role,sender_name,content) VALUES(1,'teacher','T','before')")
        p = self.preview()
        with db.get_connection() as c:
            c.execute("UPDATE announcements SET content='after' WHERE session_id=1")
        self.assertEqual(self.delete(preview=p).json()['code'], 'DELETE_PREVIEW_CHANGED')
        self.assertEqual(self.delete().status_code, 200)

    def test_class_links_and_moved_student_history_block_deletion(self):
        p = self.preview('classes')
        self.assertFalse(p['can_delete'])
        self.assertIn('Lesson', str(p['blockers']))
        self.assertEqual(self.delete('classes').status_code, 409)
        self.assertEqual(self.delete().status_code, 200)
        with db.get_connection() as c:
            c.execute("INSERT INTO sign_in_records(session_id,student_id,status) VALUES(2,1,'normal')")
        p = self.preview('classes')
        self.assertFalse(p['can_delete'])
        self.assertIn('Other', str(p['blockers']))

    def test_class_roster_and_messages_removed_and_name_reusable(self):
        self.assertEqual(self.delete().status_code, 200)
        with db.get_connection() as c:
            c.execute("INSERT INTO private_messages(sender_role,sender_student_id,sender_name,receiver_role,content) VALUES('student',1,'One','teacher','hello')")
        p = self.preview('classes')
        self.assertTrue(p['can_delete'])
        self.assertEqual(p['counts']['students'], 1)
        self.assertEqual(p['counts']['private_messages'], 1)
        self.assertEqual(self.delete('classes', preview=p).status_code, 200)
        with db.get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM private_messages').fetchone()[0], 0)
            self.assertEqual([r[0] for r in c.execute('SELECT id FROM students')], [2])
            self.assertEqual(c.execute('SELECT COUNT(*) FROM course_classes').fetchone()[0], 1)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.client.post('/academic/classes', json={'name': 'A'}).status_code, 200)

    def test_session_removes_non_fk_records_and_scoped_attachments(self):
        from app.services import academic_deletion
        self.enterContext(patch.object(academic_deletion, 'get_settings', return_value=self.settings))
        attachment = self.root / 'uploads' / 'homework' / '1' / 'a.txt'
        attachment.parent.mkdir(parents=True)
        attachment.write_text('owned')
        outside = self.root / 'keep.txt'
        outside.write_text('keep')
        with db.get_connection() as c:
            c.execute("INSERT INTO sign_in_records(session_id,student_id,status) VALUES(1,1,'normal')")
            c.execute("INSERT INTO student_sessions(student_id,session_id,token_hash,expires_at) VALUES(1,1,'token','2099-01-01')")
            c.execute("INSERT INTO interaction_moderation_log(session_id,student_id,student_name,content) VALUES(1,1,'One','text')")
            c.execute("INSERT INTO homework(id,session_id,title,deadline) VALUES(1,1,'HW','2099-01-01')")
            for path in (attachment, outside):
                c.execute("INSERT INTO homework_attachments(homework_id,original_name,stored_name,file_path,file_size) VALUES(1,'a','a',?,1)", (str(path),))
        p = self.preview()
        self.assertEqual(p['counts']['homework_attachments'], 2)
        r = self.delete(preview=p)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(attachment.exists())
        self.assertTrue(outside.exists())
        self.assertEqual(r.json()['data']['retained_file_count'], 1)
        with db.get_connection() as c:
            for table in ('sign_in_records', 'student_sessions', 'interaction_moderation_log', 'homework', 'homework_attachments'):
                self.assertEqual(c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0, table)

    def test_transaction_rolls_back_on_delete_failure(self):
        with db.get_connection() as c:
            c.execute("INSERT INTO student_sessions(student_id,session_id,token_hash,expires_at) VALUES(1,1,'token','2099-01-01')")
            c.execute("CREATE TRIGGER reject_delete BEFORE DELETE ON classroom_sessions BEGIN SELECT RAISE(ABORT,'test'); END")
        self.assertEqual(self.delete().status_code, 500)
        with db.get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM student_sessions').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM classroom_sessions').fetchone()[0], 2)

    def test_late_student_work_cannot_recreate_orphans_after_deletion(self):
        from app.core.exceptions import AppError
        from app.services.student_auth import create_student_session
        from app.services.interactions import _insert_moderation_log
        self.assertEqual(self.delete().status_code, 200)
        with self.assertRaises(AppError):
            create_student_session(1, 1)
        with self.assertRaises(AppError):
            _insert_moderation_log(1, {'id': 1}, 'One', 'late result', {'safe': False})

    def test_populated_classroom_cascade_and_other_classroom_preserved(self):
        with db.get_connection() as c:
            for i in (1, 2):
                c.execute("INSERT INTO questions(id,session_id,title,content,question_type) VALUES(?,?, 'Q','body','short_answer')", (i, i))
                c.execute("INSERT INTO question_options(question_id,option_key,content) VALUES(?,'A','answer')", (i,))
                c.execute("INSERT INTO question_answers(id,question_id,session_id,student_id,status) VALUES(?,?,?,?,'submitted')", (i, i, i, i))
                c.execute("INSERT INTO homework(id,session_id,title,deadline) VALUES(?,?,'HW','2099-01-01')", (i, i))
                c.execute("INSERT INTO homework_submissions(id,homework_id,session_id,student_id,status) VALUES(?,?,?,?,'submitted')", (i, i, i, i))
                c.execute("INSERT INTO homework_review_records(submission_id,score) VALUES(?,10)", (i,))
                c.execute("INSERT INTO learning_evaluations(session_id,student_id,level) VALUES(?,?,'good')", (i, i))
                c.execute("INSERT INTO enrollment_applications(session_id,student_number,name) VALUES(?,'new','Applicant')", (i,))
                c.execute("INSERT INTO ai_failure_tasks(scenario,source_type,source_id) VALUES('review','question_answer',?)", (i,))
                c.execute("INSERT INTO ai_content_safety_logs(source_type,source_id,action,original_length,sanitized_length) VALUES('ai_chat',?,'pass',1,1)", (i,))
        p = self.preview()
        self.assertEqual(self.delete(preview=p).status_code, 200)
        with db.get_connection() as c:
            for table in ('questions','question_options','question_answers','homework','homework_submissions',
                          'homework_review_records','learning_evaluations','enrollment_applications',
                          'ai_failure_tasks','ai_content_safety_logs'):
                self.assertEqual(c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 1, table)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_shared_attachment_is_retained(self):
        from app.services import academic_deletion
        self.enterContext(patch.object(academic_deletion, 'get_settings', return_value=self.settings))
        path = self.root / 'uploads' / 'homework' / 'shared.txt'
        path.parent.mkdir(parents=True)
        path.write_text('shared')
        with db.get_connection() as c:
            for i in (1, 2):
                c.execute("INSERT INTO homework(id,session_id,title,deadline) VALUES(?,?,'HW','2099-01-01')", (i, i))
                c.execute("INSERT INTO homework_attachments(homework_id,original_name,stored_name,file_path,file_size) VALUES(?,'a','a',?,1)", (i, str(path)))
        self.assertEqual(self.delete().status_code, 200)
        self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
