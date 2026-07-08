import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from app.core.exceptions import AppError
from app.db.session import get_connection


LOCK_THRESHOLD = 5
LOCK_MINUTES = 5
TOKEN_HOURS = 12


def _now() -> datetime:
    return datetime.now()


def _to_db_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_db_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2_sha256$200000${}${}".format(
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, password_hash: str) -> bool:
    algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(digest_b64.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_teacher() -> dict[str, object]:
    # 纯查询：迁移 002 已保证 teachers(id=1) 存在并完成名称修正，
    # 不应在读取路径里做 INSERT/UPDATE，否则并发时可能触发未捕获的 IntegrityError(500)。
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM teachers WHERE id = 1").fetchone()
    if row is None:
        raise AppError("教师账户不存在，请检查数据库初始化", code="TEACHER_NOT_FOUND")
    return dict(row)


def get_auth_status() -> dict[str, object]:
    teacher = _get_teacher()
    locked_until = _parse_db_time(teacher.get("locked_until"))
    return {
        "password_set": bool(teacher.get("password_hash")),
        "locked": bool(locked_until and locked_until > _now()),
        "locked_until": _to_db_time(locked_until) if locked_until else None,
        "failed_login_count": teacher.get("failed_login_count", 0),
    }


def setup_teacher_password(password: str, confirm_password: str) -> dict[str, object]:
    if password != confirm_password:
        raise AppError("两次输入的密码不一致", code="PASSWORD_MISMATCH")
    if len(password) < 6:
        raise AppError("密码长度不能少于 6 位", code="PASSWORD_TOO_SHORT")

    teacher = _get_teacher()
    if teacher.get("password_hash"):
        raise AppError("教师密码已设置，请直接登录", code="PASSWORD_ALREADY_SET")

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
    return _issue_token(1)


def login_teacher(password: str) -> dict[str, object]:
    teacher = _get_teacher()
    if not teacher.get("password_hash"):
        raise AppError("请先设置教师密码", code="PASSWORD_NOT_SET", status_code=409)

    locked_until = _parse_db_time(teacher.get("locked_until"))
    if locked_until and locked_until > _now():
        raise AppError("密码错误次数过多，请稍后再试", code="TEACHER_LOCKED", status_code=423)

    if not _verify_password(password, str(teacher["password_hash"])):
        failed_count = int(teacher.get("failed_login_count") or 0) + 1
        lock_until = _now() + timedelta(minutes=LOCK_MINUTES) if failed_count >= LOCK_THRESHOLD else None
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE teachers
                SET failed_login_count = ?, locked_until = ?, updated_at = datetime('now')
                WHERE id = 1
                """,
                (failed_count, _to_db_time(lock_until) if lock_until else None),
            )
        if lock_until:
            raise AppError("连续 5 次密码错误，已锁定 5 分钟", code="TEACHER_LOCKED", status_code=423)
        raise AppError("密码错误", code="PASSWORD_INCORRECT", status_code=401)

    with get_connection() as connection:
        connection.execute(
            "UPDATE teachers SET failed_login_count = 0, locked_until = NULL, updated_at = datetime('now') WHERE id = 1"
        )
    return _issue_token(1)


def _issue_token(teacher_id: int) -> dict[str, object]:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(hours=TOKEN_HOURS)
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO auth_tokens(teacher_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (teacher_id, _token_hash(token), _to_db_time(expires_at)),
        )
    return {
        "token": token,
        "token_type": "bearer",
        "expires_at": _to_db_time(expires_at),
        "teacher": {"id": teacher_id, "name": "教师"},
    }


def validate_token(token: str) -> dict[str, object] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT t.id, t.name, a.expires_at
            FROM auth_tokens a
            JOIN teachers t ON t.id = a.teacher_id
            WHERE a.token_hash = ? AND a.revoked_at IS NULL
            """,
            (_token_hash(token),),
        ).fetchone()
    if row is None:
        return None
    expires_at = _parse_db_time(row["expires_at"])
    if expires_at is None or expires_at <= _now():
        return None
    return {"id": row["id"], "name": row["name"]}


def revoke_teacher_tokens(teacher_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE auth_tokens SET revoked_at = datetime('now') WHERE teacher_id = ? AND revoked_at IS NULL",
            (teacher_id,),
        )
