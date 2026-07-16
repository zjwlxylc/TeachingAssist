CREATE TABLE IF NOT EXISTS student_import_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    report_type TEXT NOT NULL DEFAULT 'error' CHECK(report_type IN ('error', 'warning', 'summary')),
    rows_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (job_id) REFERENCES student_import_jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sign_in_change_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL CHECK(new_status IN ('normal', 'late', 'absent')),
    reason TEXT,
    operator_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

ALTER TABLE question_answers ADD COLUMN is_draft INTEGER NOT NULL DEFAULT 0;
ALTER TABLE question_answers ADD COLUMN ai_feedback_status TEXT NOT NULL DEFAULT 'none';
ALTER TABLE question_answers ADD COLUMN ai_feedback_json TEXT;
ALTER TABLE question_answers ADD COLUMN quality_score REAL NOT NULL DEFAULT 0;
ALTER TABLE question_answers ADD COLUMN bonus_total REAL NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS question_bonus_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    participation_score REAL NOT NULL DEFAULT 1,
    correct_score REAL NOT NULL DEFAULT 2,
    timeliness_score REAL NOT NULL DEFAULT 0.5,
    timeliness_percent REAL NOT NULL DEFAULT 30,
    max_quality_score REAL NOT NULL DEFAULT 3,
    session_cap REAL NOT NULL DEFAULT 20,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS question_bonus_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL UNIQUE,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    participation_score REAL NOT NULL DEFAULT 0,
    correct_score REAL NOT NULL DEFAULT 0,
    timeliness_score REAL NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT 0,
    total_score REAL NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (answer_id) REFERENCES question_answers(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

ALTER TABLE homework_submissions ADD COLUMN ai_score REAL;
ALTER TABLE homework_submissions ADD COLUMN ai_feedback_json TEXT;
ALTER TABLE homework_submissions ADD COLUMN ai_confidence REAL;
ALTER TABLE homework_submissions ADD COLUMN final_score REAL;
ALTER TABLE homework_submissions ADD COLUMN final_feedback TEXT;
ALTER TABLE homework_submissions ADD COLUMN grade_published_at TEXT;

CREATE TABLE IF NOT EXISTS homework_review_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homework_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued', 'running', 'completed', 'manual_required')),
    total_count INTEGER NOT NULL DEFAULT 0,
    reviewed_count INTEGER NOT NULL DEFAULT 0,
    manual_count INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (homework_id) REFERENCES homework(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluation_weight_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    attendance_weight REAL NOT NULL DEFAULT 20,
    question_weight REAL NOT NULL DEFAULT 35,
    homework_weight REAL NOT NULL DEFAULT 25,
    message_weight REAL NOT NULL DEFAULT 10,
    activity_weight REAL NOT NULL DEFAULT 10,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learning_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    version_type TEXT NOT NULL DEFAULT 'temporary' CHECK(version_type IN ('temporary', 'final')),
    version_no INTEGER NOT NULL DEFAULT 1,
    attendance_score REAL NOT NULL DEFAULT 0,
    question_score REAL NOT NULL DEFAULT 0,
    homework_score REAL NOT NULL DEFAULT 0,
    message_score REAL NOT NULL DEFAULT 0,
    activity_score REAL NOT NULL DEFAULT 0,
    total_score REAL NOT NULL DEFAULT 0,
    level TEXT NOT NULL,
    advice TEXT,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    raw_data_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id, version_type, version_no),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recovery_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('interruption', 'extend_questions', 'reopen_sign_in', 'cached_request_replayed')),
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    action_taken TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_student_import_reports_job ON student_import_reports(job_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sign_in_change_logs_session ON sign_in_change_logs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_question_bonus_session_student ON question_bonus_records(session_id, student_id);
CREATE INDEX IF NOT EXISTS idx_homework_review_jobs_homework ON homework_review_jobs(homework_id, created_at);
CREATE INDEX IF NOT EXISTS idx_learning_evaluations_session ON learning_evaluations(session_id, version_type, version_no);
CREATE INDEX IF NOT EXISTS idx_recovery_events_session ON recovery_events(session_id, created_at);

INSERT OR IGNORE INTO question_bonus_settings(id) VALUES (1);
INSERT OR IGNORE INTO evaluation_weight_settings(id) VALUES (1);
