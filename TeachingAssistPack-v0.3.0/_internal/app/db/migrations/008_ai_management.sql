CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    model_name TEXT NOT NULL,
    api_key TEXT,
    http_proxy TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 0,
    last_status TEXT NOT NULL DEFAULT 'unknown' CHECK(last_status IN ('unknown', 'available', 'unavailable', 'disabled')),
    last_checked_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_check_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER,
    status TEXT NOT NULL CHECK(status IN ('available', 'unavailable', 'disabled')),
    message TEXT,
    latency_ms INTEGER,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (provider_id) REFERENCES ai_provider_configs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ai_safety_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    max_length INTEGER NOT NULL DEFAULT 2000,
    blocked_keywords_json TEXT NOT NULL DEFAULT '[]',
    keyword_action TEXT NOT NULL DEFAULT 'replace' CHECK(keyword_action IN ('replace', 'block')),
    display_strategy TEXT NOT NULL DEFAULT 'review_first' CHECK(display_strategy IN ('review_first', 'direct_with_report')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_content_safety_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id INTEGER,
    action TEXT NOT NULL CHECK(action IN ('pass', 'replace', 'block', 'truncate')),
    matched_keywords_json TEXT NOT NULL DEFAULT '[]',
    original_length INTEGER NOT NULL,
    sanitized_length INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_failure_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario TEXT NOT NULL,
    source_type TEXT,
    source_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending_manual' CHECK(status IN ('pending_manual', 'template_generated', 'resolved')),
    reason TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_provider_active ON ai_provider_configs(is_active, enabled);
CREATE INDEX IF NOT EXISTS idx_ai_check_logs_provider ON ai_check_logs(provider_id, checked_at);
CREATE INDEX IF NOT EXISTS idx_ai_failure_tasks_status ON ai_failure_tasks(status, scenario);

INSERT OR IGNORE INTO ai_safety_settings(id, max_length, blocked_keywords_json, keyword_action, display_strategy)
VALUES (1, 2000, '[]', 'replace', 'review_first');

INSERT OR IGNORE INTO ai_provider_configs(
    id, provider_name, display_name, base_url, model_name, enabled, is_active, last_status
)
VALUES
    (1, 'deepseek', 'DeepSeek', 'https://api.deepseek.com/v1', 'deepseek-chat', 0, 1, 'disabled'),
    (2, 'zhipu', '智谱 GLM', 'https://open.bigmodel.cn/api/paas/v4', 'glm-4-flash', 0, 0, 'disabled'),
    (3, 'qwen', '通义千问', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen-plus', 0, 0, 'disabled'),
    (4, 'openai', 'OpenAI', 'https://api.openai.com/v1', 'gpt-4o-mini', 0, 0, 'disabled');
