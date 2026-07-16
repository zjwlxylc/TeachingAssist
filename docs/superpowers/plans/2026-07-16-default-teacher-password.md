# Default Teacher Password Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `test123` the default password for newly initialized teacher accounts and reset the current local teacher account to that password without committing the local database.

**Architecture:** Add a validated authentication setting and two focused authentication service operations: one idempotent initializer that writes only when no password exists, and one explicit reset operation that revokes existing tokens. Call the initializer after migrations during startup, then invoke the reset operation once against the configured local database.

**Tech Stack:** Python 3.13, Pydantic 2, SQLite, pytest, existing PBKDF2-SHA256 authentication service

## Global Constraints

- The default teacher password is exactly `test123`.
- Startup must never overwrite an existing teacher password.
- The local database remains at `C:\TeachingAssist\data\teaching_assist.db` and must not be staged or committed.
- No public HTTP password-reset endpoint is added.
- Existing student authentication and frontend login behavior remain unchanged.
- Stage and commit only exact task files; preserve existing ALE work and staged files.

---

### Task 1: Authentication Setting And Idempotent Initialization

**Files:**
- Create: `tests/test_default_teacher_password.py`
- Modify: `backend/app/core/config.py`
- Modify: `config/default.yaml`
- Modify: `backend/app/services/auth.py`

**Interfaces:**
- Consumes: `AppSettings.normalized()`, `auth._hash_password(password: str) -> str`, `get_connection()`
- Produces: `AuthenticationSettings.default_teacher_password: str`; `initialize_default_teacher_password(password: str) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from app.core.config import AppSettings
from app.db import session as db_session
from app.db.migrations import run_migrations
from app.services import auth


def prepare_database(tmp_path: Path, monkeypatch) -> AppSettings:
    settings = AppSettings(storage={"local_root": tmp_path}).normalized()
    monkeypatch.setattr(db_session, "get_settings", lambda: settings)
    run_migrations()
    return settings


def teacher_password_hash() -> str | None:
    with db_session.get_connection() as connection:
        row = connection.execute("SELECT password_hash FROM teachers WHERE id = 1").fetchone()
    return row["password_hash"] if row else None


def test_default_teacher_password_setting_is_test123() -> None:
    assert AppSettings().auth.default_teacher_password == "test123"


def test_initializes_default_password_when_teacher_password_is_empty(tmp_path, monkeypatch) -> None:
    prepare_database(tmp_path, monkeypatch)
    changed = auth.initialize_default_teacher_password("test123")
    assert changed is True
    assert auth._verify_password("test123", teacher_password_hash() or "")


def test_initialization_preserves_existing_password(tmp_path, monkeypatch) -> None:
    prepare_database(tmp_path, monkeypatch)
    auth.setup_teacher_password("custom456", "custom456")
    changed = auth.initialize_default_teacher_password("test123")
    password_hash = teacher_password_hash() or ""
    assert changed is False
    assert auth._verify_password("custom456", password_hash)
    assert not auth._verify_password("test123", password_hash)
```

- [ ] **Step 2: Run the tests and verify RED**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m pytest tests\test_default_teacher_password.py -v
```

Expected: FAIL because `AppSettings.auth` and `initialize_default_teacher_password` do not exist.

- [ ] **Step 3: Add the setting and minimal initializer**

Add to `backend/app/core/config.py`:

```python
class AuthenticationSettings(BaseModel):
    default_teacher_password: str = Field(default="test123", min_length=6)


class AppSettings(BaseModel):
    auth: AuthenticationSettings = Field(default_factory=AuthenticationSettings)
```

Add to `config/default.yaml`:

```yaml
auth:
  default_teacher_password: test123
```

Add to `backend/app/services/auth.py`:

```python
def initialize_default_teacher_password(password: str) -> bool:
    if len(password) < 6:
        raise AppError("密码长度不能少于 6 位", code="PASSWORD_TOO_SHORT")
    password_hash = _hash_password(password)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE teachers
            SET password_hash = ?, password_set_at = datetime('now'), failed_login_count = 0,
                locked_until = NULL, updated_at = datetime('now')
            WHERE id = 1 AND password_hash IS NULL
            """,
            (password_hash,),
        )
    return cursor.rowcount == 1
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run the Task 1 pytest command. Expected: 3 passed.

- [ ] **Step 5: Commit only Task 1 files**

```powershell
git add -- tests/test_default_teacher_password.py backend/app/core/config.py config/default.yaml backend/app/services/auth.py
git commit --only -m "feat: initialize default teacher password" -- tests/test_default_teacher_password.py backend/app/core/config.py config/default.yaml backend/app/services/auth.py
```

---

### Task 2: Explicit Teacher Password Reset

**Files:**
- Modify: `tests/test_default_teacher_password.py`
- Modify: `backend/app/services/auth.py`

**Interfaces:**
- Consumes: `auth._hash_password(password: str) -> str`, `auth.validate_token(token: str) -> dict[str, object] | None`
- Produces: `reset_teacher_password(password: str) -> None`

- [ ] **Step 1: Add the failing reset test**

```python
def test_reset_replaces_password_and_revokes_existing_tokens(tmp_path, monkeypatch) -> None:
    prepare_database(tmp_path, monkeypatch)
    token_info = auth.setup_teacher_password("custom456", "custom456")
    old_token = str(token_info["token"])
    auth.reset_teacher_password("test123")
    password_hash = teacher_password_hash() or ""
    assert auth._verify_password("test123", password_hash)
    assert not auth._verify_password("custom456", password_hash)
    assert auth.validate_token(old_token) is None
```

- [ ] **Step 2: Run the reset test and verify RED**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m pytest tests\test_default_teacher_password.py::test_reset_replaces_password_and_revokes_existing_tokens -v
```

Expected: FAIL because `reset_teacher_password` does not exist.

- [ ] **Step 3: Add the minimal reset operation**

Add to `backend/app/services/auth.py`:

```python
def reset_teacher_password(password: str) -> None:
    if len(password) < 6:
        raise AppError("密码长度不能少于 6 位", code="PASSWORD_TOO_SHORT")
    _get_teacher()
    password_hash = _hash_password(password)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE teachers
            SET password_hash = ?, password_set_at = datetime('now'), failed_login_count = 0,
                locked_until = NULL, updated_at = datetime('now')
            WHERE id = 1
            """,
            (password_hash,),
        )
        connection.execute(
            "UPDATE auth_tokens SET revoked_at = datetime('now') WHERE teacher_id = 1 AND revoked_at IS NULL"
        )
```

- [ ] **Step 4: Run the complete test module and verify GREEN**

Run the Task 1 pytest command. Expected: 4 passed.

- [ ] **Step 5: Commit only Task 2 files**

```powershell
git add -- tests/test_default_teacher_password.py backend/app/services/auth.py
git commit --only -m "feat: add controlled teacher password reset" -- tests/test_default_teacher_password.py backend/app/services/auth.py
```

---

### Task 3: Startup Integration

**Files:**
- Modify: `tests/test_default_teacher_password.py`
- Modify: `backend/app/services/startup.py`

**Interfaces:**
- Consumes: `settings.auth.default_teacher_password`, `initialize_default_teacher_password(password: str) -> bool`
- Produces: startup behavior that initializes only an empty teacher password after migrations

- [ ] **Step 1: Add the failing startup integration test**

```python
from app.services import startup


def test_startup_initializes_configured_teacher_password(tmp_path, monkeypatch) -> None:
    settings = AppSettings(storage={"local_root": tmp_path}).normalized()
    monkeypatch.setattr(db_session, "get_settings", lambda: settings)
    monkeypatch.setattr(startup, "get_ai_overview", lambda: {"active_provider": None})
    startup.run_startup_checks(settings)
    assert auth._verify_password("test123", teacher_password_hash() or "")
```

- [ ] **Step 2: Run the startup test and verify RED**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m pytest tests\test_default_teacher_password.py::test_startup_initializes_configured_teacher_password -v
```

Expected: FAIL because startup does not invoke the initializer.

- [ ] **Step 3: Call the initializer after migrations**

Modify `backend/app/services/startup.py`:

```python
from app.services.auth import initialize_default_teacher_password


def run_startup_checks(settings: AppSettings) -> dict[str, object]:
    directories = initialize_directories(settings)
    migrations = run_migrations()
    initialize_default_teacher_password(settings.auth.default_teacher_password)
    integrity = integrity_check()
```

- [ ] **Step 4: Run the complete test module and verify GREEN**

Run the Task 1 pytest command. Expected: 5 passed.

- [ ] **Step 5: Commit only Task 3 files**

```powershell
git add -- tests/test_default_teacher_password.py backend/app/services/startup.py
git commit --only -m "feat: initialize teacher password at startup" -- tests/test_default_teacher_password.py backend/app/services/startup.py
```

---

### Task 4: Reset And Verify The Current Local Account

**Files:**
- Modify local runtime data only: `C:\TeachingAssist\data\teaching_assist.db`

**Interfaces:**
- Consumes: `get_settings().auth.default_teacher_password`, `reset_teacher_password(password: str) -> None`
- Produces: current local teacher account authenticates with `test123`; previous tokens are revoked

- [ ] **Step 1: Run all backend-focused verification**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m pytest tests\test_default_teacher_password.py -v
.\.venv\Scripts\python.exe -m compileall backend\app
```

Expected: all password tests pass and compileall exits 0.

- [ ] **Step 2: Reset the configured local teacher account**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -c "from app.core.config import get_settings; from app.services.auth import reset_teacher_password; settings = get_settings(); reset_teacher_password(settings.auth.default_teacher_password); print('teacher_password_reset=true')"
```

Expected: `teacher_password_reset=true`.

- [ ] **Step 3: Verify the local hash without issuing a new token**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
@'
from app.core.config import get_settings
from app.db.session import get_connection
from app.services.auth import _verify_password

settings = get_settings()
with get_connection() as connection:
    row = connection.execute("SELECT password_hash FROM teachers WHERE id = 1").fetchone()
print(f"database_exists={settings.storage.database_path.exists()}")
print(f"matches_test123={bool(row and _verify_password(settings.auth.default_teacher_password, row['password_hash']))}")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `database_exists=True` and `matches_test123=True`.

- [ ] **Step 4: Run database initialization check**

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe scripts\init_db.py
```

Expected: `Database initialized`, SQLite integrity `ok`, and no password overwrite or migration error.

- [ ] **Step 5: Confirm repository scope**

```powershell
git status --short
git diff --name-only HEAD~3..HEAD
```

Expected: no `.db`, `.sqlite`, `.sqlite3`, `.workbuddy`, or unrelated ALE file appears in the password feature commits.
