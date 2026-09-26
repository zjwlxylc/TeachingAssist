-- Preserve existing deadline behavior until the teacher chooses manual control.
ALTER TABLE classroom_sessions ADD COLUMN sign_in_mode TEXT NOT NULL DEFAULT 'automatic'
    CHECK(sign_in_mode IN ('automatic', 'open', 'paused'));
