-- 学生会话令牌：签到后发放，用于私信读/发的身份鉴权，杜绝仅凭学号+姓名冒名。
CREATE TABLE IF NOT EXISTS student_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    UNIQUE(student_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_student_sessions_token ON student_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_student_sessions_student ON student_sessions(student_id);
