"""学生会话令牌服务。

设计要点：
- 签到成功后发放一次性随机令牌（URL-safe），库内只存 SHA-256 哈希 + 过期时间，不存明文。
- 令牌用于学生私信的读/发身份鉴权，替代（加固）原先仅靠“学号+姓名”的弱身份校验，
  避免他人凭已知学号姓名冒名读取/发送私信。
- 令牌与 (student_id, session_id) 唯一绑定，重复签到会轮换令牌（覆盖旧哈希）。
- 默认有效期 12 小时；过期或哈希不匹配一律返回 None（调用方按 401 处理）。
"""

import hashlib
import secrets
import time

from typing import Any

from app.db.session import get_connection

STUDENT_TOKEN_TTL_SECONDS = 12 * 3600


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_student_session(student_id: int, session_id: int) -> str:
    """为已签到的学生创建/轮换会话令牌，返回明文令牌（仅此一次返回，库内只存哈希）。"""
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + STUDENT_TOKEN_TTL_SECONDS))
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO student_sessions(student_id, session_id, token_hash, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, session_id)
            DO UPDATE SET token_hash = excluded.token_hash, created_at = datetime('now'), expires_at = excluded.expires_at
            """,
            (int(student_id), int(session_id), token_hash, expires_at),
        )
    return token


def resolve_student_by_token(token: str | None) -> dict[str, Any] | None:
    """校验令牌，返回 {student_id, session_id} 或 None（无效/过期）。"""
    if not token:
        return None
    token_hash = _hash_token(token)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT student_id, session_id, expires_at FROM student_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    expires = data.get("expires_at") or ""
    # 简易时间比较：格式 "%Y-%m-%d %H:%M:%S" 字符串按字典序即时间序
    if expires and expires < time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()):
        return None
    return {"student_id": int(data["student_id"]), "session_id": int(data["session_id"])}


def verify_student_token_for_session(token: str | None, expected_session_id: int) -> int | None:
    """校验令牌且要求令牌绑定的 session 与当前资源一致，返回 student 主键或 None。

    用于学生端 PII 读取（反馈/草稿/答题），既防止冒名，也防止跨课堂令牌复用。
    无令牌或令牌不匹配时返回 None，调用方据此回退到“学号+姓名”兜底逻辑。
    """
    identity = resolve_student_by_token(token)
    if identity is None:
        return None
    if int(identity["session_id"]) != int(expected_session_id):
        return None
    return int(identity["student_id"])

