# 课前准备模块重构方案

> 背景：试点中教师反馈"课前准备流程不清晰、操作不顺"。根因经代码核对（academic.py / classroom.py / 前端 TeacherPage 课前准备 Tab）确认，是**领域模型错误**——把"导入学生名单"错误地耦合进每堂课的课前准备，并绑死在"课程/课堂"上。本方案按慧行 2026-07-07 的修正重做模型。

## 0. 结论先行

问题本质是模型错，不是界面顺序问题。正确模型里：

- **学生跟着班级走**，导入是"建班级"时的一次性动作，不该每堂课重复。
- **课前准备只负责"为某次课选定上课班级"**，即 选课程 → 多选上课班级 → 建课堂。

改动集中在三处：**数据模型（课堂支持多班级、导入改绑班级）** + **名册取数逻辑（由存储改为派生）** + **前端课前准备布局（拆出导入、改为多选班级）**，不破坏签到、统计、AI 降级等其它能力。

## 1. 目标领域模型（四层实体）

| 实体 | 生命周期 | 关键关系 |
|------|----------|----------|
| 课程 Course | 学期级，建一次 | 一门课面向若干班级（CourseClass） |
| 班级 Class | 行政班，长期 | 学生归属班级（students.class_id）；建班时一次性导入学生 |
| 课程-班级 CourseClass | 开课设置，学期初一次 | 课程有哪些可选班（course_classes 表已存在） |
| 课堂 Session | 某课程某次课 | 绑定"选中的若干班级" + 课次/时间 |

**名册（谁该来签到）= 课堂绑定班级的学生集合，由数据派生，不再单独存储"导入名单"。**

当前 `students` 表已有 `class_id`，导入改绑班级时数据结构基本就位；主要工作是改导入语义、课堂多班级、以及把 `course_students` 从"存储名册"降级/废弃。

## 2. 对比：旧流程 vs 新流程

**旧（错误）**：建课程 → 传 Excel 导入到"课程" → 选班级 → 建课堂（每堂课都要导入；导入还会自动建班级、自动关联、自动写 course_students）。

**新（正确）**：

- 学期初一次性准备：
  1. 建课程（整个学期）
  2. 建班级 + 导入该班学生（一次性，跟班级走）
  3. 配置课程-班级关系（可选，开课设置）
- 每堂课的课前准备：
  1. 选课程
  2. **多选本次上课班级**
  3. 填课次/时间 → 建课堂

## 3. 数据模型变更（追加迁移 0xx_*.sql）

- 保留 `students(class_id)`；导入只写 `students`（不再写 `course_students`）。
- 新增 `session_classes(session_id, class_id)`，主键 `(session_id, class_id)`，FK 级联删除。
- `classroom_sessions`：移除 `class_id` 单列与 `UNIQUE(course_id, class_id, session_no)`，改为 `UNIQUE(course_id, session_no)`（同课程同课次唯一；多班级改存 session_classes）。
- `course_students`：废弃作为名册存储语义。可保留表作历史或迁移后 DROP；名册改为派生查询。

## 4. 后端改动清单

**academic.py（导入语义重构）**

- 导入接口改为"按班级导入"：新增/改造 `POST /academic/classes/{class_id}/imports/excel` 与对应 preview/confirm，参数用 `class_id`。
- `confirm_import` 只写 `students` + `class_id`，**移除"自动建班级、自动关联 course_classes、写 course_students"的逻辑**。
- `list_students`：按班级或"课程关联班级"查询，不再依赖 `course_students`。
- 班级创建/列表接口保留，并补"导入学生"入口（一次性）。

**classroom.py（名册全面改为派生，影响最大）**

- `_roster_count`：`students JOIN session_classes WHERE session_id=? AND is_active=1`。
- `student_sign_in`：校验学生属于本 session 的某班级（`students JOIN session_classes`）。
- `_end_session_in_connection` 生成 absent：基于 session_classes 的学生集合。
- `get_sign_in_summary` / `update_sign_in_status` / `list_active_sessions` / `export_sign_ins`：名册来源全部切换为 session_classes 派生。

**路由**

- `POST /academic/sessions`：请求体 `class_ids: list[int]` 替代单 `class_id`；创建时写入 `session_classes`；保留"课程-班级须已关联"校验（或在建课堂时顺带关联，待决策）。
- 课程-班级关系：保留 `course-classes` 接口，作为课堂可选班级来源。

## 5. 前端改动清单（TeacherPage 等）

- **课前准备 Tab**：移除"Excel 学生导入"区块；重构为：
  - 选课程（当前课程）
  - 多选上课班级（MultiSelect，来源 = 该课程已关联班级；若为空提示先去配置）
  - 填标题/课次/时间 → 建课堂（传 class_ids）
- **新增"班级管理"模块**（或并入课程管理）：建班级 + 一次性导入该班学生（独立入口，与课前准备解耦）。
- 课堂列表/详情展示多班级。
- 删除"当前课程"下拉与导入区之间的隐式耦合报错。
- 选班级、建课堂的按钮在依赖未满足时**前置置灰禁用 + 提示**，替代"点了才报错"。

## 6. 影响面 / 需回归

以下模块当前依赖 `course_students` 或单班级，改造后必须回归：

- 签到校验、考勤统计、缺勤(absent)自动生成、CSV 导出、设备共享检测。
- 学生停用/启用（is_active）仍有效。
- 评估(evaluation)若取名册也须同步（需确认其数据源，见决策点）。

## 7. 历史数据迁移

- 将 `course_students` 中学生的 `class_id` 与 `students.class_id` 对齐；缺失按导入记录班级回填。
- 为每个历史 `classroom_sessions` 生成 `session_classes`（用其原 class_id）。
- `course_students` 表在迁移脚本 DROP 前先做备份。

## 8. 分步实施

- **A. 数据模型 + 迁移脚本 + 备份**
- **B. 后端**：导入改班级 + 名册派生（classroom.py 全量切换）
- **C. 前端**：课前准备重构 + 班级管理导入入口
- **D. 回归**：签到/统计/导出/设备检测 + 历史迁移校验

## 9. 待你拍板的关键决策

1. **课堂是否允许"多班级同时上课"？** 你原话"多选上课班级"我按"支持多班级"设计（需 session_classes）。若实际是单班、只是从不同班里挑一个，则无需 session_classes，改动更小——请确认。
2. **"课程-班级关系(course_classes)"配置入口放哪？** 课程管理（学期初一次）还是课前准备时直接勾选即建？
3. **历史数据**：试点是否已有真实 `course_students` 数据？决定是否要走迁移脚本。

---
*方案状态：已拍板 —— 支持多班级、课程管理里配置开课关系、已有真实数据需迁移。进入实施（阶段 A-D）。*
