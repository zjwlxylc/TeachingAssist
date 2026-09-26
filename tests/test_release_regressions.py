import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_teacher
from app.api.routes.evaluation import router
from app.core.config import AppSettings
from app.core.exceptions import AppError
from app.db import session as db
from app.db.migrations import run_migrations
from app.services import backup, evaluation


class EvaluationExportRouteTests(unittest.TestCase):
    def test_csv_export_does_not_match_json_report_route(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_teacher] = lambda: {"id": 1}
        exported = {"content": "name,score\nTest,90\n", "content_type": "text/csv", "file_name": "report.csv"}
        with mock.patch.object(evaluation, "export_session", return_value=exported) as export:
            response = TestClient(app).get("/evaluation/sessions/1.csv")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/csv", response.headers["content-type"])
        export.assert_called_once_with(1)


class BackupRestoreWalTests(unittest.TestCase):
    def test_reject_unrelated_sqlite_database_before_overwriting_data(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            settings = AppSettings(storage={"local_root": Path(directory)}).normalized()
            stack.enter_context(mock.patch.object(db, "get_settings", return_value=settings))
            stack.enter_context(mock.patch.object(backup, "get_settings", return_value=settings))
            stack.enter_context(mock.patch.object(backup, "detect_removable_root", return_value=None))
            run_migrations()
            with db.get_connection() as connection:
                connection.execute("INSERT INTO classes(name) VALUES ('Keep me')")
            settings.storage.backups_dir.mkdir(parents=True, exist_ok=True)
            unrelated = settings.storage.backups_dir / "unrelated.db"
            connection = sqlite3.connect(unrelated)
            connection.execute("CREATE TABLE unrelated(value TEXT)")
            connection.close()
            with self.assertRaises(AppError):
                backup.restore_backup(str(unrelated))
            with db.get_connection() as connection:
                self.assertEqual(connection.execute("SELECT name FROM classes").fetchone()[0], "Keep me")

    def test_restore_with_open_wal_connection_preserves_latest_safety_copy(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            settings = AppSettings(storage={"local_root": Path(directory)}).normalized()
            stack.enter_context(mock.patch.object(db, "get_settings", return_value=settings))
            stack.enter_context(mock.patch.object(backup, "get_settings", return_value=settings))
            stack.enter_context(mock.patch.object(backup, "detect_removable_root", return_value=None))
            run_migrations()
            settings.storage.backups_dir.mkdir(parents=True, exist_ok=True)
            original = settings.storage.backups_dir / "original.db"
            with db.get_connection() as connection:
                connection.execute("INSERT INTO classes(name) VALUES ('Original')")
            live = db.connect()
            stack.callback(live.close)
            snapshot = sqlite3.connect(original)
            live.backup(snapshot)
            snapshot.close()
            live.execute("PRAGMA wal_autocheckpoint=0")
            live.execute("INSERT INTO classes(name) VALUES ('Latest WAL change')")
            live.commit()
            result = backup.restore_backup(str(original))
            safety = sqlite3.connect(result["safety_backup"])
            stack.callback(safety.close)
            self.assertEqual(safety.execute("SELECT count(*) FROM classes").fetchone()[0], 2)
            self.assertEqual(live.execute("SELECT name FROM classes").fetchall()[0][0], "Original")
            self.assertEqual(live.execute("SELECT count(*) FROM classes").fetchone()[0], 1)
            self.assertEqual(live.execute("PRAGMA integrity_check").fetchone()[0], "ok")
