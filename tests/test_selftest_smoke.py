from __future__ import annotations

import unittest

from scripts.selftest_smoke import setup_teacher


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _DefaultPasswordClient:
    def get(self, path: str) -> _Response:
        if path != "/api/v1/auth/status":
            raise AssertionError(path)
        return _Response({"data": {"password_set": True}})

    def post(self, path: str, json: dict[str, str]) -> _Response:
        if path != "/api/v1/auth/login":
            raise AssertionError(path)
        if json != {"password": "test123"}:
            raise AssertionError(json)
        return _Response({"data": {"token": "teacher-token"}})


class SelftestTeacherLoginTests(unittest.TestCase):
    def test_setup_teacher_uses_configured_password_when_already_initialized(self) -> None:
        token = setup_teacher(_DefaultPasswordClient())

        self.assertEqual(token, "teacher-token")


if __name__ == "__main__":
    unittest.main()
