-- 013: 重构领域模型
-- 学生归属班级（students.class_id 已是事实来源），课堂支持多班级。
-- course_students 已被 "students.class_id + course_classes / session_classes" 完全替代，删除。
-- classroom_sessions 移除单 class_id 列，唯一约束变为 (course_id, session_no)。
-- 注：因 class_id 参与了 UNIQUE 约束，DROP COLUMN 在重建索引时会失败，
--     故采用「建新表 -> 迁数据 -> 删旧表 -> 改名」的重建法。

CREATE TABLE IF NOT EXISTS session_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, class_id),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- 历史课堂：将单班级写入 session_classes，保留历史课堂名册
INSERT OR IGNORE INTO session_classes(session_id, class_id)
SELECT id, class_id FROM classroom_sessions WHERE class_id IS NOT NULL;

-- 重建 classroom_sessions 以移除 class_id 列
CREATE TABLE classroom_sessions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    session_no INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    start_time TEXT,
    end_time TEXT,
    sign_in_deadline_minutes INTEGER NOT NULL DEFAULT 15,
    is_makeup INTEGER NOT NULL DEFAULT 0,
    schedule_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    actual_started_at TEXT,
    actual_ended_at TEXT,
    ended_by TEXT,
    UNIQUE(course_id, session_no),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

INSERT INTO classroom_sessions_new (
    id, course_id, title, session_no, status, start_time, end_time,
    sign_in_deadline_minutes, is_makeup, schedule_note,
    created_at, updated_at, actual_started_at, actual_ended_at, ended_by
)
SELECT
    id, course_id, title, session_no, status, start_time, end_time,
    sign_in_deadline_minutes, is_makeup, schedule_note,
    created_at, updated_at, actual_started_at, actual_ended_at, ended_by
FROM classroom_sessions;

DROP TABLE classroom_sessions;
ALTER TABLE classroom_sessions_new RENAME TO classroom_sessions;

-- 删除已被替代的 course_students 表
DROP TABLE IF EXISTS course_students;
