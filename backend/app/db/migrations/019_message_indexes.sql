-- 私信高频查询索引：标记已读/拉取会话按 sender_student_id / receiver_student_id 过滤，
-- 复合索引 (role, student_id) 带 role 在前、无法被不带 role 的 OR 查询利用，需补单列索引。
CREATE INDEX IF NOT EXISTS idx_private_messages_sender_student ON private_messages(sender_student_id);
CREATE INDEX IF NOT EXISTS idx_private_messages_receiver_student ON private_messages(receiver_student_id);
-- 教师未读计数：WHERE receiver_role='teacher' AND read_at IS NULL
CREATE INDEX IF NOT EXISTS idx_private_messages_unread_teacher ON private_messages(receiver_role, read_at);
