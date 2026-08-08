# 教师端与学生端交互整改 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变业务和后端的前提下，让教师端和学生端的移动导航、状态反馈与技术信息层级可用于真实机房试点。

**Architecture:** 保留现有单页状态与桌面侧栏，在两个页面内部增加 `md` 以下的 MUI Select 导航；用条件渲染修复学生连接误报和空状态；用原生 `details/summary` 收纳教师技术明细。所有改动均复用现有组件和状态，不引入依赖或新数据流。

**Tech Stack:** React 18、TypeScript 5.4、MUI 5、Vite 4、Playwright CLI。

## Global Constraints

- 保留现有未提交的 `TeacherPage.tsx`、`StudentPage.tsx` 和 `docs/interaction-layout-optimization.md` 改动。
- 只修改前端及本轮设计、计划文档；不改变后端 API、SQLite、业务规则、认证、Provider 或部署方式。
- 不升级 Node、Vite、MUI 或其他依赖。
- 不提交、不 push，不使用 `git add .`。
- 行为修改必须先看到对应浏览器断言失败，再做最小修改并验证通过。

---

### Task 1: 教师端响应式导航与无障碍名称

**Files:**
- Modify: `frontend/src/pages/TeacherPage.tsx`
- Test: Playwright CLI session `ta-ux`

**Interfaces:**
- Consumes: `activeTeacherSection`、`setActiveTeacherSection`、`TEACHER_SECTIONS` 和既有未读计数状态。
- Produces: `md` 以下“教师功能”选择器；`md` 以上原侧栏；名称与可见标签一致的导航按钮。

- [ ] **Step 1: 运行失败断言**

```javascript
await page.setViewportSize({ width: 390, height: 844 });
if (await page.getByRole('combobox', { name: '教师功能' }).count() !== 1) throw new Error('missing mobile teacher navigation');
```

在修改前预期失败，因为移动端仍渲染完整侧栏。

- [ ] **Step 2: 实现最小响应式导航**

在页面内复用既有 `FormControl`、`InputLabel`、`Select` 和 `MenuItem`：移动端显示选择器，桌面端显示原侧栏；提取一个局部切换函数以复用未读清零规则。给 Tooltip 增加 `describeChild`。

- [ ] **Step 3: 运行 GREEN 断言**

```javascript
await page.setViewportSize({ width: 390, height: 844 });
if (await page.getByRole('combobox', { name: '教师功能' }).count() !== 1) throw new Error('missing mobile teacher navigation');
await page.setViewportSize({ width: 1440, height: 900 });
if (await page.getByRole('button', { name: '系统与备份' }).count() !== 1) throw new Error('teacher navigation accessible name mismatch');
```

### Task 2: 学生端响应式导航与连接空状态

**Files:**
- Modify: `frontend/src/pages/StudentPage.tsx`
- Test: Playwright CLI session `ta-ux`

**Interfaces:**
- Consumes: `activeStudentSection`、`setActiveStudentSection`、`STUDENT_SECTIONS`、`currentSession` 和既有未读状态。
- Produces: `md` 以下“学生功能”选择器、无活动课堂提示、只在已选择课堂时出现的连接提示，以及防止重复提交的签到加载状态。

- [ ] **Step 1: 运行三个失败断言**

```javascript
await page.goto('http://127.0.0.1:5173/student');
await page.setViewportSize({ width: 390, height: 844 });
if (await page.getByRole('combobox', { name: '学生功能' }).count() !== 1) throw new Error('missing mobile student navigation');
if (await page.getByText('当前没有进行中的课堂').count() !== 1) throw new Error('missing active-session empty state');
if (await page.getByText('连接已断开').count() !== 0) throw new Error('false disconnected state without classroom');
```

修改前预期分别因选择器缺失、空状态缺失和误报断线而失败。

- [ ] **Step 2: 实现最小修复**

增加移动选择器并隐藏移动侧栏；在活动课堂列表为空时显示说明；仅在 `currentSession` 存在时渲染 `ConnectionIndicator`。不改变签到 API 调用或 WebSocket 实现。

- [ ] **Step 3: 运行 GREEN 断言**

重复 Step 1，三个断言均不得抛错；再切换到“课堂公告”并确认对应标题可见。

- [ ] **Step 4: 验证签到提交加载状态的 RED/GREEN**

用 Playwright 在 HTTP 边界延迟 `/classroom/sessions/123/sign-in`，点击“提交签到”后断言按钮具有
`disabled` 和 `aria-busy="true"`。修改前预期失败；增加局部 `signingIn` 状态和 MUI
`CircularProgress` 后预期通过，不改变请求参数或响应处理。

### Task 3: 教师状态本地化与技术详情折叠

**Files:**
- Modify: `frontend/src/pages/TeacherPage.tsx`
- Test: Playwright CLI session `ta-ux`

**Interfaces:**
- Consumes: `health` 和 `startup` 现有响应字段。
- Produces: 面向教师的中文状态值；默认折叠且可展开的技术详情。

- [ ] **Step 1: 运行失败断言**

```javascript
if (await page.getByText('查看技术详情').count() !== 1) throw new Error('technical details are not grouped');
if (await page.getByText('开发环境', { exact: true }).count() !== 1) throw new Error('environment value is not localized');
```

- [ ] **Step 2: 实现最小信息层级修复**

把 `ok` 和 `development` 映射为中文；保留数据库路径和 U 盘状态，将迁移、初始化目录放入原生 `details/summary`。

- [ ] **Step 3: 运行 GREEN 断言**

重复 Step 1，并确认关闭状态下“本次迁移”不可见、展开后可见。

### Task 4: 移动端非核心悬浮入口避让

**Files:**
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Test: Playwright CLI session `ta-ux`

**Interfaces:**
- Consumes: 既有“开源仓库” aside。
- Produces: `xs` 隐藏、`sm` 及以上保留的固定入口。

- [ ] **Step 1: 运行失败断言**

```javascript
await page.setViewportSize({ width: 390, height: 844 });
if (await page.getByLabel('开源仓库入口').isVisible()) throw new Error('repository badge overlaps mobile tasks');
```

- [ ] **Step 2: 实现断点显示规则**

只给 aside 增加 `display: { xs: 'none', sm: 'block' }`，不调整桌面样式和链接行为。

- [ ] **Step 3: 运行 GREEN 断言**

390px 时入口不可见；1440px 时入口可见且链接仍指向既有仓库地址。

### Task 5: 全量回归与交付证据

**Files:**
- Update: `docs/interaction-layout-optimization.md`
- Verify: all modified frontend files

**Interfaces:**
- Consumes: Tasks 1-4 的页面行为。
- Produces: 构建结果、桌面/窄屏截图、导航覆盖表和最终差异报告。

- [ ] **Step 1: 浏览器覆盖全部功能入口**

在教师端登录后逐一切换 12 个功能，在学生端逐一切换 8 个功能；记录标题、页面级横向溢出和控制台错误。分别保存 1440×900 与 390×844 的教师、学生截图到 `output/playwright/`。

- [ ] **Step 2: 运行前端构建**

```powershell
Set-Location frontend
npm.cmd run build
```

预期：TypeScript 和 Vite 构建退出码为 0，只保留既有 chunk size 警告。

- [ ] **Step 3: 运行 ALE 前端聚焦验证**

```powershell
Set-Location <仓库根目录>
.\.venv\Scripts\python.exe scripts\ale.py focused --target frontend
```

预期：前端目标通过。

- [ ] **Step 4: 检查差异质量并清理临时配置**

删除本轮临时 `config/local.yaml`，停止本轮启动的服务，运行：

```powershell
git diff --check
git status --short
```

最终差异不得包含临时数据库、日志、构建产物或配置。
