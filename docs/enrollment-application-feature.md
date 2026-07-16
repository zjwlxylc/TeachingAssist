# 学生注册申请功能实现文档

## 功能概述

本次更新实现了学生注册申请功能，解决学生不在课堂名单时无法签到的问题。学生可以提交注册申请，教师审批后加入课堂名单。

## 核心流程

### 学生端流程

1. 学生尝试签到
2. 如果不在课堂名单中，系统提示"您不在课堂名单中，可以提交注册申请"
3. 学生填写注册申请表单（学号、姓名、专业、院系、年级）
4. 提交申请后，系统返回两种情况：
   - **自动合并**：如果学号已存在于系统且符合条件，自动加入课堂名单
   - **待审批**：需要教师手动审批

### 教师端流程

1. 教师打开课堂签到统计
2. 查看待审批的注册申请列表
3. 对每个申请可以：
   - **批准**：选择目标班级，学生加入名单并自动完成签到
   - **拒绝**：可选填写拒绝原因

## 技术实现

### 数据库设计

**新增表：enrollment_applications**

```sql
CREATE TABLE IF NOT EXISTS enrollment_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_number TEXT NOT NULL,
    name TEXT NOT NULL,
    major TEXT,
    college TEXT,
    grade TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'auto_merged')),
    rejection_reason TEXT,
    assigned_class_id INTEGER,
    auto_signed_in INTEGER NOT NULL DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at TEXT,
    ip_address TEXT,
    user_agent TEXT,
    device_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_class_id) REFERENCES classes(id) ON DELETE SET NULL
);
```

**索引**：
- `idx_enrollment_applications_session_status`：按课堂和状态查询
- `idx_enrollment_applications_student_session`：防重复申请
- `idx_enrollment_applications_created`：按时间排序

### 后端实现

**新增服务层：backend/app/services/enrollment.py**

核心函数：
- `create_application()` - 学生提交申请，包含自动合并逻辑
- `list_applications()` - 教师查看申请列表
- `get_session_classes()` - 获取课堂关联的班级列表
- `approve_application()` - 教师批准申请，可选自动签到
- `reject_application()` - 教师拒绝申请

**新增 API 路由：backend/app/api/routes/classroom.py**

- `POST /classroom/sessions/{session_id}/enrollment/apply` - 学生提交申请（公开接口）
- `GET /classroom/sessions/{session_id}/enrollment/applications` - 教师查看申请列表
- `GET /classroom/sessions/{session_id}/enrollment/classes` - 获取课堂班级列表
- `POST /classroom/sessions/{session_id}/enrollment/applications/{application_id}/approve` - 批准申请
- `POST /classroom/sessions/{session_id}/enrollment/applications/{application_id}/reject` - 拒绝申请

### 前端实现

**学生端：frontend/src/pages/StudentPage.tsx**

- 签到失败时自动显示注册申请表单
- 提交申请后显示状态提示
- 自动合并后提示重新签到

**教师端：frontend/src/pages/TeacherPage.tsx**

- 签到统计页面新增"学生注册申请"板块
- 显示待审批申请数量
- 提供批准/拒绝操作界面
- 批准时需要选择目标班级

**前端 API：frontend/src/api/classroom.ts**

- `createEnrollmentApplication()` - 提交申请
- `fetchEnrollmentApplications()` - 获取申请列表
- `fetchSessionClasses()` - 获取班级列表
- `approveEnrollmentApplication()` - 批准申请
- `rejectEnrollmentApplication()` - 拒绝申请

## 自动合并逻辑

为提高效率，系统在以下情况下自动合并申请：

1. 学号已存在于系统的 `students` 表
2. 该学生未在当前课堂的任何班级中
3. 学生提交的信息与现有记录不冲突

自动合并时：
- 将学生添加到课堂的第一个班级
- 状态标记为 `auto_merged`
- 提示学生重新点击签到按钮

## 安全措施

1. **防重复申请**：同一学生对同一课堂只能有一个待审批申请
2. **设备指纹记录**：记录申请时的设备标识，用于防刷检测
3. **IP 和 User-Agent 记录**：用于审计和异常检测
4. **班级归属验证**：批准时检查班级是否属于该课堂

## 审计日志

系统记录以下信息：
- 申请时间（created_at）
- 审批时间（reviewed_at）
- 审批人（reviewed_by）
- 拒绝原因（rejection_reason）
- 是否自动签到（auto_signed_in）

## 使用场景

### 场景 1：新生首次上课
学生尚未导入系统，通过注册申请加入课堂名单。

### 场景 2：学号已存在但不在本课堂
学生之前上过其他课程，信息已录入，想加入新课堂。系统自动合并。

### 场景 3：旁听生或转专业学生
学生信息需要审核确认，教师手动批准后加入。

## 测试建议

### 单元测试
- 测试自动合并逻辑的各种边界情况
- 测试防重复申请机制
- 测试批准后的签到自动完成

### 集成测试
- 完整流程：申请 → 批准 → 签到
- 完整流程：申请 → 拒绝
- 自动合并流程

### UI 测试
- 学生端申请表单显示和提交
- 教师端申请列表和审批操作
- 错误提示和成功消息显示

## 后续优化建议

1. **批量审批**：支持一次批准多个申请
2. **申请通知**：有新申请时实时提醒教师
3. **申请历史**：查看已处理的申请记录
4. **申请撤回**：学生可以撤回待审批的申请
5. **班级建议**：根据学号或专业自动推荐班级

## 文件清单

### 后端
- `backend/app/db/migrations/020_enrollment_applications.sql` - 数据库迁移
- `backend/app/services/enrollment.py` - 业务逻辑（新增）
- `backend/app/api/routes/classroom.py` - API 路由（修改）

### 前端
- `frontend/src/api/classroom.ts` - API 封装（修改）
- `frontend/src/pages/StudentPage.tsx` - 学生端界面（修改）
- `frontend/src/pages/TeacherPage.tsx` - 教师端界面（修改）

## 版本信息

- 实现日期：2026-07-11
- 数据库迁移版本：020
- 相关 Issue：学生不在名单时无法签到
