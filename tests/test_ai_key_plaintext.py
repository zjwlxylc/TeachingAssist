import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

from app.core.config import AppSettings
from app.db import session as db
from app.db.migrations import run_migrations
from app.services import ai


class AiKeyPlaintextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = AppSettings(storage={"local_root": Path(self.temp.name)}).normalized()
        self.db_patch = mock.patch.object(db, "get_settings", return_value=self.settings)
        self.ai_patch = mock.patch.object(ai, "get_settings", return_value=self.settings, create=True)
        self.db_patch.start()
        self.ai_patch.start()
        run_migrations()

    def tearDown(self):
        self.ai_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def test_new_provider_key_is_saved_plainly_without_creating_key_file(self):
        saved = ai.save_provider({
            "provider_name": "local-test",
            "display_name": "Local Test",
            "base_url": "https://example.test/v1",
            "model_name": "test-model",
            "api_key": "sample-provider-key",
            "enabled": True,
        })
        with db.get_connection() as connection:
            stored = connection.execute("SELECT api_key FROM ai_provider_configs WHERE id = ?", (saved["id"],)).fetchone()[0]
        self.assertEqual(stored, "sample-provider-key")
        self.assertFalse((self.settings.storage.local_root / "ai_secret.key").exists())
        self.assertEqual(saved["api_key_masked"], "****")

    def test_legacy_encrypted_key_is_migrated_to_plaintext_when_old_file_exists(self):
        old_key = Fernet.generate_key()
        (self.settings.storage.local_root / "ai_secret.key").write_bytes(old_key)
        encrypted = "enc::" + Fernet(old_key).encrypt(b"legacy-provider-key").decode("ascii")
        with db.get_connection() as connection:
            connection.execute("UPDATE ai_provider_configs SET api_key = ? WHERE id = 1", (encrypted,))
        self.assertEqual(ai.migrate_legacy_api_keys(), 1)
        with db.get_connection() as connection:
            stored = connection.execute("SELECT api_key FROM ai_provider_configs WHERE id = 1").fetchone()[0]
        self.assertEqual(stored, "legacy-provider-key")

    def test_legacy_encrypted_key_without_old_file_requires_reentry(self):
        encrypted = "enc::" + Fernet(Fernet.generate_key()).encrypt(b"unavailable-key").decode("ascii")
        with db.get_connection() as connection:
            connection.execute("UPDATE ai_provider_configs SET api_key = ?, enabled = 1, is_active = 1 WHERE id = 1", (encrypted,))
        self.assertEqual(ai.migrate_legacy_api_keys(), 0)
        with db.get_connection() as connection:
            active = ai._active_provider(connection)
        self.assertIsNone(active["api_key"])
        provider = next(item for item in ai.get_ai_overview()["providers"] if item["id"] == 1)
        self.assertFalse(provider["api_key_set"])
        self.assertFalse((self.settings.storage.local_root / "ai_secret.key").exists())


if __name__ == "__main__":
    unittest.main()
