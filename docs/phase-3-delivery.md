# 阶段 3 交付说明

## 已完成

1. 教师端课程创建与课程列表。
2. 教师端班级创建与班级列表。
3. 课程与班级关联。
4. 课堂创建，支持课次、开始时间、结束时间和补课标记。
5. 学生基础表、课程学生关联表、课程班级关联表。
6. Excel 学生名单上传，限制 `.xls` / `.xlsx` 入口和 10MB 文件大小。
7. `.xlsx` 表头读取与前 5 行样例保存。
8. 手动字段映射，必填字段为学号、姓名、班级。
9. 导入预览，包含空值、重复学号、已存在学号提示。
10. 确认导入学生、班级和课程关联，返回导入统计。
11. 教师端课前准备面板，覆盖“选课程 → 选班级 → 导入学生 → 创建课堂”。

## 新增接口

```text
GET  /api/v1/academic/courses
POST /api/v1/academic/courses
GET  /api/v1/academic/classes
POST /api/v1/academic/classes
POST /api/v1/academic/course-classes
GET  /api/v1/academic/sessions
POST /api/v1/academic/sessions
GET  /api/v1/academic/students
POST /api/v1/academic/imports/excel
POST /api/v1/academic/imports/{job_id}/preview
POST /api/v1/academic/imports/{job_id}/confirm
```

以上接口均需要教师 Bearer Token。

## 数据库变更

新增迁移：`backend/app/db/migrations/003_course_class_import.sql`

- `course_classes`：课程与班级关联。
- `students`：学生基础信息。
- `course_students`：课程学生名单。
- `classroom_sessions`：课堂/课次。
- `student_import_jobs`：Excel 导入任务、表头、样例与原始行数据。
- `courses.teacher_name`：任课教师显示名。

## 验证记录

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成 API 烟测：

- 创建课程。
- 创建班级。
- 关联课程和班级。
- 创建课堂。
- 生成 `.xlsx` 学生名单并上传。
- 读取表头和总行数。
- 手动字段映射并生成预览。
- 确认导入学生。
- 按课程查询学生名单，导入数量正确。

## 留待后续阶段

- 老式二进制 `.xls` 目前会给出明确提示，建议教师另存为 `.xlsx` 后上传；如现场确需原生 `.xls`，可追加 `xlrd` 支持。
- 课堂状态机的开始、结束、签到截止与课后备份将在阶段 4 接入。
- 学生停用/启用、增量导入覆盖/跳过/合并选择属于 P1 增强，按实施方案后续阶段继续。
