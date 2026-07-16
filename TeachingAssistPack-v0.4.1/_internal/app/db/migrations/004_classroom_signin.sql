ALTER TABLE classroom_sessions ADD COLUMN actual_started_at TEXT;
ALTER TABLE classroom_sessions ADD COLUMN actual_ended_at TEXT;
ALTER TABLE classroom_sessions ADD COLUMN ended_by TEXT;

CREATE TABLE IF NOT EXISTS sign_in_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('normal', 'late', 'absent')),
    sign_time TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sign_in_records_session ON sign_in_records(session_id);
CREATE INDEX IF NOT EXISTS idx_sign_in_records_student ON sign_in_records(student_id);

CREATE TABLE IF NOT EXISTS evaluation_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    initialized_at TEXT NOT NULL DEFAULT (datetime('now')),
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);
