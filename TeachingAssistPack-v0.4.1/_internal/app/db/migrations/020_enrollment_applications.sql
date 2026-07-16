-- 020 学生注册申请表
-- 学生在签到时若不在名单中，可提交注册申请，由教师审批后加入课堂

CREATE TABLE IF NOT EXISTS enrollment_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_number TEXT NOT NULL,
    name TEXT NOT NULL,
    major TEXT,
    college TEXT,
    grade TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'auto_merged')),
    rejection_reason TEXT,
    assigned_class_id INTEGER,
    auto_signed_in INTEGER NOT NULL DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at TEXT,
    ip_address TEXT,
    user_agent TEXT,
    device_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_class_id) REFERENCES classes(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_enrollment_applications_session_status
    ON enrollment_applications(session_id, status);

CREATE INDEX IF NOT EXISTS idx_enrollment_applications_student_session
    ON enrollment_applications(student_number, session_id);

CREATE INDEX IF NOT EXISTS idx_enrollment_applications_created
    ON enrollment_applications(created_at DESC);
