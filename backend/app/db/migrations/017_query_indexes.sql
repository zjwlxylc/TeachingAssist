-- 017: 补齐高频查询索引，降低签到/公告/问答/作业/私信等读路径的全表扫描。
-- 全部使用 IF NOT EXISTS，可安全重复执行。

CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id);

CREATE INDEX IF NOT EXISTS idx_sign_in_records_session ON sign_in_records(session_id);

CREATE INDEX IF NOT EXISTS idx_device_fingerprints_lookup
    ON device_fingerprints(session_id, student_id, device_hash);

CREATE INDEX IF NOT EXISTS idx_announcements_session ON announcements(session_id);

CREATE INDEX IF NOT EXISTS idx_questions_session ON questions(session_id);

CREATE INDEX IF NOT EXISTS idx_question_answers_question ON question_answers(question_id);

CREATE INDEX IF NOT EXISTS idx_homework_session ON homework(session_id);

CREATE INDEX IF NOT EXISTS idx_private_messages_sender_student
    ON private_messages(sender_role, sender_student_id);

CREATE INDEX IF NOT EXISTS idx_private_messages_receiver_student
    ON private_messages(receiver_role, receiver_student_id);

CREATE INDEX IF NOT EXISTS idx_classroom_sessions_status ON classroom_sessions(status);
