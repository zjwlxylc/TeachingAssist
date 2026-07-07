-- 设备指纹追踪表，用于防止同一设备替多人签到
CREATE TABLE IF NOT EXISTS device_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    device_hash TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    sign_in_count INTEGER NOT NULL DEFAULT 1,
    is_suspicious INTEGER NOT NULL DEFAULT 0,
    suspicious_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_fingerprints_session ON device_fingerprints(session_id);
CREATE INDEX IF NOT EXISTS idx_device_fingerprints_device_hash ON device_fingerprints(device_hash);
CREATE INDEX IF NOT EXISTS idx_device_fingerprints_suspicious ON device_fingerprints(is_suspicious);

-- 为签到记录添加设备指纹字段
ALTER TABLE sign_in_records ADD COLUMN device_hash TEXT;

-- 设备共享警告表
CREATE TABLE IF NOT EXISTS device_sharing_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    device_hash TEXT NOT NULL,
    student_count INTEGER NOT NULL,
    student_ids_json TEXT NOT NULL,
    alert_level TEXT NOT NULL CHECK(alert_level IN ('warning', 'critical')),
    reviewed INTEGER NOT NULL DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, device_hash),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_sharing_alerts_session ON device_sharing_alerts(session_id);
CREATE INDEX IF NOT EXISTS idx_device_sharing_alerts_reviewed ON device_sharing_alerts(reviewed);
