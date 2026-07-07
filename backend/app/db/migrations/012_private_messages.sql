CREATE TABLE IF NOT EXISTS private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_role TEXT NOT NULL CHECK(sender_role IN ('teacher', 'student')),
    sender_student_id INTEGER,
    sender_name TEXT NOT NULL,
    receiver_role TEXT NOT NULL CHECK(receiver_role IN ('teacher', 'student')),
    receiver_student_id INTEGER,
    content TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (sender_student_id) REFERENCES students(id) ON DELETE SET NULL,
    FOREIGN KEY (receiver_student_id) REFERENCES students(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pm_receiver
    ON private_messages(receiver_role, receiver_student_id, read_at);
CREATE INDEX IF NOT EXISTS idx_pm_sender
    ON private_messages(sender_role, sender_student_id);
