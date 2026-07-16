-- 016 课堂互动发言 AI 安全分析
-- 1) 全局开关：是否对学生课堂互动发言做 AI 甄别（默认关闭）
ALTER TABLE ai_safety_settings ADD COLUMN interaction_moderation_enabled INTEGER NOT NULL DEFAULT 0;

-- 2) 被 AI 判定违规、尚未上墙的学生发言审核日志（仅教师可见，可放行/忽略）
CREATE TABLE interaction_moderation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    student_name TEXT NOT NULL,
    content TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_interaction_moderation_log_session_status
    ON interaction_moderation_log (session_id, status);
