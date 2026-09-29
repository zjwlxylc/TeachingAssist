"""Teacher-confirmed deletion with an impact preview and transactional revalidation.

Classroom records are scoped to one classroom. Classes may only be removed after
their classroom dependencies (including students' historical records) are gone.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Literal

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.session import get_connection

Kind = Literal['classes', 'sessions']
logger = logging.getLogger(__name__)

# All SQL identifiers below come from these source-controlled mappings.
SESSION_TABLES = {
    'session_classes': '课堂与班级关联',
    'sign_in_records': '签到记录',
    'sign_in_change_logs': '签到调整记录',
    'announcements': '课堂公告',
    'questions': '课堂题目',
    'question_answers': '学生答案（含历史版本）',
    'question_action_logs': '答题操作记录',
    'question_bonus_records': '答题加分记录',
    'homework': '课堂作业',
    'homework_submissions': '作业提交（含历史版本）',
    'evaluation_tasks': '评估任务',
    'learning_evaluations': '学习评估',
    'recovery_events': '中断恢复记录',
    'device_fingerprints': '签到设备记录',
    'device_sharing_alerts': '签到设备预警',
    'interaction_settings': '互动设置',
    'classroom_interaction_messages': '课堂互动消息',
    'interaction_moderation_log': '互动审核记录',
    'student_sessions': '学生登录令牌',
    'enrollment_applications': '注册申请',
}
CHILD_TABLES = {
    'question_options': ('题目选项', 'question_id IN (SELECT id FROM questions WHERE session_id = ?)'),
    'homework_attachments': ('教师作业附件', 'homework_id IN (SELECT id FROM homework WHERE session_id = ?)'),
    'homework_submission_files': ('学生作业附件', 'submission_id IN (SELECT id FROM homework_submissions WHERE session_id = ?)'),
    'homework_review_records': ('作业批阅记录', 'submission_id IN (SELECT id FROM homework_submissions WHERE session_id = ?)'),
    'homework_review_jobs': ('作业批阅任务', 'homework_id IN (SELECT id FROM homework WHERE session_id = ?)'),
}
AI_SOURCE_SCOPE = """
    (source_type IN ('student_interaction', 'learning_evaluation', 'ai_chat') AND source_id = ?1)
    OR (source_type = 'question_answer' AND source_id IN (SELECT id FROM question_answers WHERE session_id = ?1))
    OR (source_type = 'homework_submission' AND source_id IN (SELECT id FROM homework_submissions WHERE session_id = ?1))
"""
CHILD_TABLES.update({
    'ai_failure_tasks': ('本课堂 AI 失败任务', AI_SOURCE_SCOPE),
    'ai_content_safety_logs': ('本课堂 AI 安全检查记录', AI_SOURCE_SCOPE),
})
CLASS_LABELS = {
    'students': '班级学生名单（含停用学生）',
    'course_classes': '课程与班级关联',
    'private_messages': '该班学生收发的私信',
    'student_sessions': '学生登录令牌',
    'interaction_moderation_log': '互动审核记录',
}


def _rows(c: Any, table: str, where: str, id: int) -> list[dict[str, Any]]:
    return [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE {where} ORDER BY rowid', (id,))]


def _snapshot(c: Any, kind: Kind, id: int) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    table = 'classes' if kind == 'classes' else 'classroom_sessions'
    row = c.execute(f'SELECT * FROM {table} WHERE id = ?', (id,)).fetchone()
    if row is None:
        raise AppError('班级或课堂不存在，可能已被删除', code='DELETE_TARGET_NOT_FOUND', status_code=404)
    target = dict(row)
    blockers: list[dict[str, Any]] = []
    reason = ''
    records = {}
    if kind == 'sessions':
        if target['status'] not in ('pending', 'ended'):
            reason = '课堂正在进行，请先结束课堂，再删除。暂停签到不等于结束课堂。'
        for child in SESSION_TABLES:
            records[child] = _rows(c, child, 'session_id = ?', id)
        for child, (_, where) in CHILD_TABLES.items():
            records[child] = _rows(c, child, where, id)
        labels = {**SESSION_TABLES, **{k: v[0] for k, v in CHILD_TABLES.items()}}
    else:
        students = 'SELECT id FROM students WHERE class_id = ?'
        records['students'] = _rows(c, 'students', 'class_id = ?', id)
        records['course_classes'] = _rows(c, 'course_classes', 'class_id = ?', id)
        records['private_messages'] = [dict(r) for r in c.execute(
            f'SELECT * FROM private_messages WHERE sender_student_id IN ({students}) '
            f'OR receiver_student_id IN ({students}) ORDER BY id', (id, id))]
        for child in ('student_sessions', 'interaction_moderation_log'):
            records[child] = _rows(c, child, f'student_id IN ({students})', id)
        related = {r[0] for r in c.execute('SELECT session_id FROM session_classes WHERE class_id = ?', (id,))}
        related.update(r[0] for r in c.execute('SELECT session_id FROM enrollment_applications WHERE assigned_class_id = ?', (id,)))
        related.update(r[0] for r in c.execute('SELECT session_id FROM enrollment_applications WHERE student_number IN '
                                             '(SELECT student_id FROM students WHERE class_id = ?)', (id,)))
        # Students may have moved classes since attending a classroom. Deleting
        # their current class must not cascade into another classroom's history.
        for child in SESSION_TABLES:
            columns = {r['name'] for r in c.execute(f'PRAGMA table_info({child})')}
            for column in ('student_id', 'sender_student_id'):
                if column in columns:
                    related.update(r[0] for r in c.execute(
                        f'SELECT DISTINCT session_id FROM {child} WHERE {column} IN ({students})', (id,)))
        for session_id in sorted(related):
            item = c.execute('SELECT s.id, s.title, s.session_no, s.status, c.name AS course_name '
                             'FROM classroom_sessions s JOIN courses c ON c.id=s.course_id WHERE s.id=?',
                             (session_id,)).fetchone()
            if item:
                blockers.append(dict(item))
        if blockers:
            reason = '该班级仍被课堂使用，或该班学生仍有课堂记录。请先处理下列课堂；删除班级不会自动删除课堂。'
        labels = CLASS_LABELS
    fingerprint = json.dumps({'kind': kind, 'target': target, 'records': records, 'blockers': blockers},
                             ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    preview = {
        'id': id, 'kind': kind, 'name': target['name'] if kind == 'classes' else target['title'],
        'can_delete': not reason, 'reason': reason, 'blockers': blockers,
        'counts': {k: len(v) for k, v in records.items()},
        'impacts': [{'label': labels[k], 'count': len(v)} for k, v in records.items() if v],
        'preview_token': hashlib.sha256(fingerprint.encode('utf-8')).hexdigest(),
    }
    return preview, records


def preview_deletion(kind: Kind, id: int) -> dict[str, Any]:
    with get_connection() as c:
        c.execute('BEGIN')  # All counts belong to the same SQLite snapshot.
        preview, _ = _snapshot(c, kind, id)
    return preview


def _cleanup_files(files: set[str]) -> int:
    """Remove only unreferenced files beneath the configured homework directory.

    Database deletion has committed. A filesystem failure must be reported as
    retained files rather than misreporting the entire deletion as failed.
    """
    if not files:
        return 0
    retained = 0
    try:
        uploads = get_settings().storage.uploads_dir
        if uploads is None:
            return len(files)
        root = (uploads / 'homework').resolve()
        with get_connection() as c:
            c.execute('BEGIN IMMEDIATE')
            referenced = {Path(r[0]).resolve() for table in ('homework_attachments', 'homework_submission_files')
                          for r in c.execute(f'SELECT file_path FROM {table}')}
            for file in files:
                try:
                    path = Path(file).resolve()
                    if not path.is_relative_to(root) or path in referenced:
                        retained += 1
                    elif path.exists():
                        path.unlink()
                except (OSError, ValueError):
                    retained += 1
    except Exception:
        logger.warning('Attachment cleanup incomplete after classroom deletion', exc_info=True)
        return len(files)
    return retained


def delete_resource(kind: Kind, id: int, confirmation_name: str, preview_token: str) -> dict[str, Any]:
    files: set[str] = set()
    with get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        preview, records = _snapshot(c, kind, id)
        if not preview['can_delete']:
            raise AppError(preview['reason'], code='DELETE_BLOCKED', status_code=409)
        if confirmation_name != preview['name']:
            raise AppError('名称不一致，请完整输入要删除的班级名称或课堂标题', code='DELETE_NAME_MISMATCH', status_code=409)
        if preview_token != preview['preview_token']:
            raise AppError('数据已变化，请重新查看删除影响并确认', code='DELETE_PREVIEW_CHANGED', status_code=409)
        if kind == 'sessions':
            for table in ('homework_attachments', 'homework_submission_files'):
                files.update(r['file_path'] for r in records[table])
            # These two legacy tables have no foreign keys.
            for table in ('student_sessions', 'interaction_moderation_log'):
                c.execute(f'DELETE FROM {table} WHERE session_id = ?', (id,))
            for table in ('ai_failure_tasks', 'ai_content_safety_logs'):
                c.execute(f'DELETE FROM {table} WHERE {AI_SOURCE_SCOPE}', (id,))
            c.execute('DELETE FROM classroom_sessions WHERE id = ?', (id,))
        else:
            roster = 'SELECT id FROM students WHERE class_id = ?'
            c.execute(f'DELETE FROM private_messages WHERE sender_student_id IN ({roster}) '
                      f'OR receiver_student_id IN ({roster})', (id, id))
            for table in ('student_sessions', 'interaction_moderation_log'):
                c.execute(f'DELETE FROM {table} WHERE student_id IN ({roster})', (id,))
            c.execute('DELETE FROM students WHERE class_id = ?', (id,))
            c.execute('DELETE FROM classes WHERE id = ?', (id,))
    return {'id': id, 'kind': kind, 'deleted': True, 'retained_file_count': _cleanup_files(files)}
