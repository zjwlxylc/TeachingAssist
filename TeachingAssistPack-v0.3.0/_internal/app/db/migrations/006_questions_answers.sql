CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    question_type TEXT NOT NULL CHECK(question_type IN ('single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer')),
    status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('draft', 'published', 'closed')),
    start_time TEXT,
    deadline TEXT,
    correct_answer_json TEXT,
    keywords_json TEXT,
    score REAL NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    published_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_key TEXT NOT NULL,
    content TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(question_id, option_key),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    answer_json TEXT,
    answer_text TEXT,
    status TEXT NOT NULL CHECK(status IN ('draft', 'submitted', 'timeout')),
    is_correct INTEGER,
    score REAL NOT NULL DEFAULT 0,
    submit_version INTEGER NOT NULL DEFAULT 1,
    is_latest INTEGER NOT NULL DEFAULT 1,
    started_at TEXT,
    submitted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER,
    student_id INTEGER,
    action_type TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_session ON questions(session_id, status, id);
CREATE INDEX IF NOT EXISTS idx_question_options_question ON question_options(question_id, display_order);
CREATE INDEX IF NOT EXISTS idx_question_answers_question_latest ON question_answers(question_id, is_latest, status);
CREATE INDEX IF NOT EXISTS idx_question_answers_student ON question_answers(student_id, question_id, is_latest);
CREATE INDEX IF NOT EXISTS idx_question_action_logs_session ON question_action_logs(session_id, question_id, student_id);
