from typing import Any
from datetime import datetime

from app.core.exceptions import AppError
from app.db.session import get_connection
from app.services.classroom import get_session_public, student_sign_in
from app.services.realtime import manager


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _to_db_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def get_session_classes(session_id: int) -> list[dict[str, Any]]:
    """获取课堂关联的所有班级列表（用于教师审批时选择班级）"""
    get_session_public(session_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT cl.id, cl.name
            FROM classes cl
            JOIN session_classes sc ON sc.class_id = cl.id
            WHERE sc.session_id = ?
            ORDER BY cl.name
            """,
            (session_id,),
        ).fetchall()

    if not rows:
        raise AppError("课堂未关联班级，无法处理注册申请", code="SESSION_NO_CLASS")

    return [_row_to_dict(row) for row in rows]


async def create_application(
    session_id: int,
    student_number: str,
    name: str,
    major: str | None = None,
    college: str | None = None,
    grade: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_hash: str | None = None,
) -> dict[str, Any]:
    """学生提交注册申请"""
    student_number = student_number.strip()
    name = name.strip()

    if not student_number or not name:
        raise AppError("学号和姓名不能为空", code="ENROLLMENT_INFO_REQUIRED")

    session = get_session_public(session_id)
    if session["status"] != "active":
        raise AppError("课堂未开始或已结束，无法提交注册申请", code="SESSION_NOT_ACTIVE")

    with get_connection() as connection:
        # 检查学号是否已存在
        existing_student = connection.execute(
            "SELECT id, name, class_id FROM students WHERE student_id = ?",
            (student_number,),
        ).fetchone()

        if existing_student:
            # 学号已存在，检查姓名是否匹配
            if str(existing_student["name"]).strip() == name:
                # 姓名匹配，自动合并：名册由 students.class_id ∈ session_classes 派生，
                # 故检查该学生当前班级是否已在本课堂绑定班级中。
                student_pk = int(existing_student["id"])
                session_class_rows = connection.execute(
                    "SELECT class_id FROM session_classes WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
                session_class_ids = [int(r["class_id"]) for r in session_class_rows]

                if int(existing_student["class_id"]) in session_class_ids:
                    # 已在课堂名册中，无需操作
                    raise AppError("您已在课堂名单中，可以直接签到", code="STUDENT_ALREADY_IN_COURSE", status_code=409)

                # 自动加入本课堂名册：将学生班级设为课堂绑定班级之一（取第一个）
                target_class_id = session_class_ids[0] if session_class_ids else int(existing_student["class_id"])
                connection.execute(
                    """
                    UPDATE students
                    SET class_id = ?, is_active = 1, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (target_class_id, student_pk),
                )

                # 记录为自动合并
                cursor = connection.execute(
                    """
                    INSERT INTO enrollment_applications(
                        session_id, student_number, name, major, college, grade,
                        status, assigned_class_id, ip_address, user_agent, device_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'auto_merged', ?, ?, ?, ?)
                    """,
                    (
                        session_id, student_number, name, major, college, grade,
                        target_class_id, ip_address, user_agent, device_hash,
                    ),
                )

                application_id = cursor.lastrowid
                row = connection.execute(
                    """
                    SELECT ea.*, cl.name AS assigned_class_name
                    FROM enrollment_applications ea
                    LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
                    WHERE ea.id = ?
                    """,
                    (application_id,),
                ).fetchone()

                return _row_to_dict(row)
            else:
                # 姓名不匹配，创建待审批申请（教师需要决定是否覆盖）
                pass

        # 学号不存在或姓名不匹配，创建待审批申请

        # 检查是否已有待审批的申请
        pending_application = connection.execute(
            """
            SELECT id FROM enrollment_applications
            WHERE session_id = ? AND student_number = ? AND status = 'pending'
            """,
            (session_id, student_number),
        ).fetchone()

        if pending_application:
            raise AppError("您已提交过注册申请，请等待教师审批", code="APPLICATION_ALREADY_EXISTS", status_code=409)

        # 创建待审批申请
        cursor = connection.execute(
            """
            INSERT INTO enrollment_applications(
                session_id, student_number, name, major, college, grade,
                ip_address, user_agent, device_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, student_number, name, major, college, grade,
                ip_address, user_agent, device_hash,
            ),
        )

        application_id = cursor.lastrowid
        row = connection.execute(
            """
            SELECT ea.*, cl.name AS assigned_class_name
            FROM enrollment_applications ea
            LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
            WHERE ea.id = ?
            """,
            (application_id,),
        ).fetchone()

        result = _row_to_dict(row)

    # 如果是待审批状态，通过 WebSocket 通知教师端
    if result.get("status") == "pending":
        await manager.broadcast(
            session_id,
            {
                "type": "enrollment.application.created",
                "session_id": session_id,
                "application": result,
            },
        )

    return result


def list_pending() -> list[dict[str, Any]]:
    """教师查看全部课堂的待审批注册申请（跨课堂汇总），含所属课堂信息"""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT ea.*,
                   cl.name AS assigned_class_name,
                   cs.title AS session_title,
                   co.name AS course_name,
                   (SELECT GROUP_CONCAT(c.name, '、')
                    FROM session_classes sc
                    JOIN classes c ON c.id = sc.class_id
                    WHERE sc.session_id = ea.session_id) AS class_name
            FROM enrollment_applications ea
            LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
            LEFT JOIN classroom_sessions cs ON cs.id = ea.session_id
            LEFT JOIN courses co ON co.id = cs.course_id
            WHERE ea.status = 'pending'
            GROUP BY ea.id
            ORDER BY ea.created_at DESC
            LIMIT 200
            """
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def list_applications(
    session_id: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """教师查看注册申请列表"""
    get_session_public(session_id)

    where = ["ea.session_id = ?"]
    params: list[Any] = [session_id]

    if status:
        where.append("ea.status = ?")
        params.append(status)

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT ea.*, cl.name AS assigned_class_name
            FROM enrollment_applications ea
            LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
            WHERE {' AND '.join(where)}
            ORDER BY ea.created_at DESC
            LIMIT 200
            """,
            tuple(params),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def approve_application(
    application_id: int,
    class_id: int,
    auto_sign_in: bool,
    reviewed_by: str,
) -> dict[str, Any]:
    """教师批准注册申请"""
    with get_connection() as connection:
        application = connection.execute(
            """
            SELECT ea.*, cl.name AS assigned_class_name
            FROM enrollment_applications ea
            LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
            WHERE ea.id = ?
            """,
            (application_id,),
        ).fetchone()

        if not application:
            raise AppError("申请记录不存在", code="APPLICATION_NOT_FOUND", status_code=404)

        # sqlite3.Row 不支持 .get()，转成 dict 以复用后续字段读取
        application = _row_to_dict(application)

        if application["status"] != "pending":
            raise AppError("该申请已处理", code="APPLICATION_ALREADY_REVIEWED", status_code=409)

        session_id = int(application["session_id"])
        student_number = str(application["student_number"])
        name = str(application["name"])

        # 检查课堂状态
        session = get_session_public(session_id)
        course_id = int(session["course_id"])

        # 检查班级是否属于该课堂
        valid_class = connection.execute(
            """
            SELECT cl.id, cl.name
            FROM classes cl
            JOIN session_classes sc ON sc.class_id = cl.id
            WHERE sc.session_id = ? AND cl.id = ?
            """,
            (session_id, class_id),
        ).fetchone()

        if not valid_class:
            raise AppError("所选班级不在本课堂名单中", code="CLASS_NOT_IN_SESSION", status_code=400)

        # 插入或更新学生表
        existing_student = connection.execute(
            "SELECT id FROM students WHERE student_id = ?",
            (student_number,),
        ).fetchone()

        if existing_student:
            # 学号已存在，更新信息
            connection.execute(
                """
                UPDATE students
                SET name = ?,
                    class_id = ?,
                    major = COALESCE(?, major),
                    college = COALESCE(?, college),
                    grade = COALESCE(?, grade),
                    is_active = 1,
                    updated_at = datetime('now')
                WHERE student_id = ?
                """,
                (
                    name,
                    class_id,
                    application.get("major"),
                    application.get("college"),
                    application.get("grade"),
                    student_number,
                ),
            )
            student_pk = int(existing_student["id"])
        else:
            # 新学生，插入记录
            cursor = connection.execute(
                """
                INSERT INTO students(student_id, name, class_id, major, college, grade)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    student_number,
                    name,
                    class_id,
                    application.get("major"),
                    application.get("college"),
                    application.get("grade"),
                ),
            )
            student_pk = int(cursor.lastrowid)

        # 名册由 students.class_id ∈ session_classes 派生：上面已将学生 class_id 设为
        # 本课堂绑定班级之一（assigned_class_id，已校验属于 session_classes），无需再写 course_students。

        # 更新申请状态
        connection.execute(
            """
            UPDATE enrollment_applications
            SET status = 'approved',
                assigned_class_id = ?,
                reviewed_by = ?,
                reviewed_at = datetime('now'),
                auto_signed_in = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (class_id, reviewed_by, 1 if auto_sign_in else 0, application_id),
        )

        session_active = session["status"] == "active"
        result = {
            "application_id": application_id,
            "status": "approved",
            "student_pk": student_pk,
            "auto_signed_in": False,
        }

    # 自动签到必须在外层事务提交后进行：student_sign_in 会另开独立连接，
    # 若仍在未提交事务内，新写入的 class_id 对其不可见（WAL 隔离），会导致签到静默失败。
    if auto_sign_in and session_active:
        try:
            sign_in_result = student_sign_in(
                session_id,
                student_number,
                name,
                application.get("ip_address"),
                application.get("user_agent"),
                application.get("device_hash"),
            )
            result["auto_signed_in"] = True
            result["sign_in_result"] = sign_in_result
        except AppError:
            # 签到失败不影响批准流程（可能课堂已结束等）
            pass

    return result


def reject_application(
    application_id: int,
    rejection_reason: str | None,
    reviewed_by: str,
) -> dict[str, Any]:
    """教师拒绝注册申请"""
    with get_connection() as connection:
        application = connection.execute(
            "SELECT * FROM enrollment_applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if not application:
            raise AppError("申请记录不存在", code="APPLICATION_NOT_FOUND", status_code=404)
        application = _row_to_dict(application)

        if not application:
            raise AppError("申请记录不存在", code="APPLICATION_NOT_FOUND", status_code=404)

        if application["status"] != "pending":
            raise AppError("该申请已处理", code="APPLICATION_ALREADY_REVIEWED", status_code=409)

        connection.execute(
            """
            UPDATE enrollment_applications
            SET status = 'rejected',
                rejection_reason = ?,
                reviewed_by = ?,
                reviewed_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (rejection_reason, reviewed_by, application_id),
        )

        updated = connection.execute(
            """
            SELECT ea.*, cl.name AS assigned_class_name
            FROM enrollment_applications ea
            LEFT JOIN classes cl ON cl.id = ea.assigned_class_id
            WHERE ea.id = ?
            """,
            (application_id,),
        ).fetchone()

    return _row_to_dict(updated)
