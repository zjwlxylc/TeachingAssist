import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.config import AppSettings
from app.db import session as db_session
from app.db.migrations import run_migrations
from app.services import auth


class DefaultTeacherPasswordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = AppSettings(storage={"local_root": Path(self.temp_dir.name)}).normalized()
        self.settings_patcher = mock.patch.object(db_session, "get_settings", return_value=self.settings)
        self.settings_patcher.start()
        run_migrations()

    def tearDown(self) -> None:
        self.settings_patcher.stop()
        self.temp_dir.cleanup()

    def teacher_password_hash(self) -> str | None:
        with db_session.get_connection() as connection:
            row = connection.execute("SELECT password_hash FROM teachers WHERE id = 1").fetchone()
        return row["password_hash"] if row else None

    def test_default_teacher_password_setting_is_test123(self) -> None:
        self.assertTrue(hasattr(AppSettings(), "auth"))
        self.assertEqual(AppSettings().auth.default_teacher_password, "test123")

    def test_initializes_default_password_when_teacher_password_is_empty(self) -> None:
        initializer = getattr(auth, "initialize_default_teacher_password", None)
        self.assertIsNotNone(initializer)

        changed = initializer("test123")

        self.assertTrue(changed)
        self.assertTrue(auth._verify_password("test123", self.teacher_password_hash() or ""))

    def test_initialization_preserves_existing_password(self) -> None:
        auth.setup_teacher_password("custom456", "custom456")
        initializer = getattr(auth, "initialize_default_teacher_password", None)
        self.assertIsNotNone(initializer)

        changed = initializer("test123")

        password_hash = self.teacher_password_hash() or ""
        self.assertFalse(changed)
        self.assertTrue(auth._verify_password("custom456", password_hash))
        self.assertFalse(auth._verify_password("test123", password_hash))


if __name__ == "__main__":
    unittest.main()
