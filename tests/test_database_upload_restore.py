import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_teacher
from app.api.routes.system import router
from app.core.config import AppSettings
from app.core.exceptions import add_exception_handlers
from app.db import session as db
from app.db.migrations import run_migrations
from app.services import backup


class DatabaseUploadRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.stack = ExitStack()
        self.settings = AppSettings(storage={"local_root": Path(self.temp.name)}).normalized()
        self.stack.enter_context(mock.patch.object(db, "get_settings", return_value=self.settings))
        self.stack.enter_context(mock.patch.object(backup, "get_settings", return_value=self.settings))
        self.stack.enter_context(mock.patch.object(backup, "detect_removable_root", return_value=None))
        run_migrations()
        app = FastAPI()
        add_exception_handlers(app)
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[require_teacher] = lambda: {"id": 1}
        self.app = app
        self.client = self.stack.enter_context(TestClient(app))

    def tearDown(self):
        self.stack.close()
        self.temp.cleanup()

    def test_selected_usb_backup_replaces_local_database_and_preserves_safety_copy(self):
        with db.get_connection() as connection:
            connection.execute("INSERT INTO classes(name) VALUES ('USB class')")
        usb_backup = Path(self.temp.name) / "usb" / "backup" / "chosen.db"
        usb_backup.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.settings.storage.database_path)) as live, closing(sqlite3.connect(usb_backup)) as saved:
            live.backup(saved)
        with db.get_connection() as connection:
            connection.execute("DELETE FROM classes WHERE name = 'USB class'")
            connection.execute("INSERT INTO classes(name) VALUES ('Current PC class')")

        response = self.client.post(
            "/api/v1/system/backups/upload-restore",
            files={"file": ("chosen.db", usb_backup.read_bytes(), "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        with db.get_connection() as connection:
            names = [row[0] for row in connection.execute("SELECT name FROM classes")]
            self.assertEqual(names, ["USB class"])
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        with closing(sqlite3.connect(data["safety_backup"])) as safety:
            self.assertEqual(safety.execute("SELECT name FROM classes").fetchone()[0], "Current PC class")
        self.assertEqual(self.settings.storage.database_path.name, "teaching_assist.db")
        self.assertEqual(list(self.settings.storage.backups_dir.glob("incoming_*.db")), [])

    def test_invalid_file_does_not_replace_database(self):
        with db.get_connection() as connection:
            connection.execute("INSERT INTO classes(name) VALUES ('Keep current')")
        response = self.client.post(
            "/api/v1/system/backups/upload-restore",
            files={"file": ("bad.db", b"not a sqlite database", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 422, response.text)
        with db.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT name FROM classes").fetchone()[0], "Keep current")
        self.assertEqual(list(self.settings.storage.backups_dir.glob("incoming_*.db")), [])

    def test_upload_requires_teacher_authentication(self):
        self.app.dependency_overrides.clear()
        response = self.client.post(
            "/api/v1/system/backups/upload-restore",
            files={"file": ("selected.db", b"not used", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(list(self.settings.storage.backups_dir.glob("incoming_*.db")), [])

    def test_older_backup_is_migrated_before_teaching_resumes(self):
        old_backup = Path(self.temp.name) / "older.db"
        with closing(sqlite3.connect(self.settings.storage.database_path)) as live, closing(sqlite3.connect(old_backup)) as saved:
            live.backup(saved)
        with closing(sqlite3.connect(old_backup)) as saved:
            saved.execute("ALTER TABLE classroom_sessions DROP COLUMN sign_in_mode")
            saved.execute("DELETE FROM schema_migrations WHERE version = '021_manual_sign_in'")
            saved.execute("INSERT INTO classes(name) VALUES ('Older USB class')")
            saved.commit()

        response = self.client.post(
            "/api/v1/system/backups/upload-restore",
            files={"file": ("older.db", old_backup.read_bytes(), "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with db.get_connection() as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(classroom_sessions)")}
            self.assertIn("sign_in_mode", columns)
            self.assertEqual(connection.execute("SELECT name FROM classes").fetchone()[0], "Older USB class")

    def test_backup_with_unknown_migration_version_replaces_current_data(self):
        with db.get_connection() as connection:
            connection.execute("INSERT INTO classes(name) VALUES ('Keep current')")
        future_backup = Path(self.temp.name) / "future.db"
        with closing(sqlite3.connect(self.settings.storage.database_path)) as live, closing(sqlite3.connect(future_backup)) as saved:
            live.backup(saved)
        with closing(sqlite3.connect(future_backup)) as saved:
            saved.execute("INSERT INTO schema_migrations(version) VALUES ('999_future')")
            saved.execute("DELETE FROM classes")
            saved.execute("INSERT INTO classes(name) VALUES ('Selected USB data')")
            saved.commit()

        response = self.client.post(
            "/api/v1/system/backups/upload-restore",
            files={"file": ("future.db", future_backup.read_bytes(), "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with db.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT name FROM classes").fetchone()[0], "Selected USB data")

    def test_migration_failure_rolls_back_to_previous_local_database(self):
        with db.get_connection() as connection:
            connection.execute("INSERT INTO classes(name) VALUES ('Keep current')")
        selected = Path(self.temp.name) / "selected.db"
        with closing(sqlite3.connect(self.settings.storage.database_path)) as live, closing(sqlite3.connect(selected)) as saved:
            live.backup(saved)
        with closing(sqlite3.connect(selected)) as saved:
            saved.execute("DELETE FROM classes")
            saved.execute("INSERT INTO classes(name) VALUES ('USB data')")
            saved.commit()

        with mock.patch.object(backup, "run_migrations", side_effect=RuntimeError("migration failed"), create=True):
            response = self.client.post(
                "/api/v1/system/backups/upload-restore",
                files={"file": ("selected.db", selected.read_bytes(), "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 500, response.text)
        with db.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT name FROM classes").fetchone()[0], "Keep current")
        self.assertEqual(list(self.settings.storage.backups_dir.glob("incoming_*.db")), [])


if __name__ == "__main__":
    unittest.main()
