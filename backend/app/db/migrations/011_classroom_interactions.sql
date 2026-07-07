CREATE TABLE IF NOT EXISTS interaction_settings (
    session_id INTEGER PRIMARY KEY,
    student_messages_enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS classroom_interaction_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    sender_role TEXT NOT NULL CHECK(sender_role IN ('teacher', 'student')),
    sender_student_id INTEGER,
    sender_name TEXT NOT NULL,
    content TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_student_id) REFERENCES students(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_messages_session ON classroom_interaction_messages(session_id, is_deleted, id);

ALTER TABLE sign_in_records RENAME TO sign_in_records_old;

CREATE TABLE sign_in_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('normal', 'late', 'absent', 'leave')),
    sign_time TEXT,
    ip_address TEXT,
    user_agent TEXT,
    device_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

INSERT INTO sign_in_records(
    id, session_id, student_id, status, sign_time, ip_address, user_agent, device_hash, created_at, updated_at
)
SELECT id, session_id, student_id, status, sign_time, ip_address, user_agent, device_hash, created_at, updated_at
FROM sign_in_records_old;

DROP TABLE sign_in_records_old;

CREATE INDEX IF NOT EXISTS idx_sign_in_records_session ON sign_in_records(session_id);
CREATE INDEX IF NOT EXISTS idx_sign_in_records_student ON sign_in_records(student_id);

ALTER TABLE sign_in_change_logs RENAME TO sign_in_change_logs_old;

CREATE TABLE sign_in_change_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL CHECK(new_status IN ('normal', 'late', 'absent', 'leave')),
    reason TEXT,
    operator_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

INSERT INTO sign_in_change_logs(
    id, session_id, student_id, previous_status, new_status, reason, operator_name, created_at
)
SELECT id, session_id, student_id, previous_status, new_status, reason, operator_name, created_at
FROM sign_in_change_logs_old;

DROP TABLE sign_in_change_logs_old;

CREATE INDEX IF NOT EXISTS idx_sign_in_change_logs_session ON sign_in_change_logs(session_id, created_at);
