CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    deadline TEXT NOT NULL,
    grading_criteria TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('unpublished', 'active', 'closed', 'archived')),
    allow_late INTEGER NOT NULL DEFAULT 0,
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS homework_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homework_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (homework_id) REFERENCES homework(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS homework_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homework_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    text_content TEXT,
    status TEXT NOT NULL CHECK(status IN ('submitted', 'late', 'pending_review', 'ai_reviewed', 'teacher_reviewed', 'published')),
    submit_version INTEGER NOT NULL DEFAULT 1,
    is_latest INTEGER NOT NULL DEFAULT 1,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (homework_id) REFERENCES homework(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS homework_submission_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (submission_id) REFERENCES homework_submissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS homework_review_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    reviewer_type TEXT NOT NULL DEFAULT 'teacher',
    score REAL,
    feedback TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (submission_id) REFERENCES homework_submissions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_homework_session ON homework(session_id, status, deadline);
CREATE INDEX IF NOT EXISTS idx_homework_submissions_homework_latest ON homework_submissions(homework_id, is_latest, status);
CREATE INDEX IF NOT EXISTS idx_homework_submissions_student ON homework_submissions(student_id, homework_id, is_latest);
CREATE INDEX IF NOT EXISTS idx_homework_submission_files_submission ON homework_submission_files(submission_id);
