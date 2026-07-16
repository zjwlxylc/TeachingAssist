# 学生注册申请功能修复说明

## 问题描述

学生端提交注册申请后，没有明确的反馈信息，教师端也没有实时收到通知，需要手动刷新才能看到新的申请。

## 修复内容

### 1. 后端修改

#### `backend/app/services/enrollment.py`

- **添加 WebSocket 支持**：导入 `app.services.realtime.manager`
- **异步化 `create_application` 函数**：将函数改为 `async def`，以支持 WebSocket 广播
- **添加实时通知**：当学生提交待审批申请时，通过 WebSocket 向该课堂的所有连接（主要是教师端）广播 `enrollment.application.created` 事件

```python
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
```

#### `backend/app/api/routes/classroom.py`

- **异步化路由处理器**：将 `create_enrollment_application` 改为 `async def`，并在调用服务层时使用 `await`

### 2. 前端修改

#### `frontend/src/pages/TeacherPage.tsx`

- **添加刷新按钮**：在注册申请区域添加"刷新"按钮，允许教师手动刷新申请列表
- **添加自动刷新定时器**：每30秒自动刷新注册申请列表（仅在课堂进行中时）

```typescript
// 自动刷新注册申请列表（每30秒）
useEffect(() => {
  if (!signInSummary || signInSummary.session.status !== "active") {
    return;
  }
  const intervalId = setInterval(() => {
    loadEnrollmentApplications(signInSummary.session.id).catch(() => {
      // 静默失败，不打断用户操作
    });
  }, 30000); // 30秒
  return () => clearInterval(intervalId);
}, [signInSummary]);
```

## 测试步骤

### 前置条件

1. 确保后端已启动：`cd backend && python run.py`
2. 确保前端已构建：`cd frontend && npm run build`
3. 教师端已登录并开始了一个课堂

### 测试场景1：学生提交注册申请

1. **学生端操作**：
   - 打开学生端页面
   - 选择活动课堂或输入课堂ID
   - 输入一个不在名单中的学号和姓名（如：`20240999` / `测试学生`）
   - 点击"提交签到"
   - 系统提示"您不在课堂名单中"，显示注册申请表单
   - 填写可选信息（专业、院系、年级）
   - 点击"提交注册申请"

2. **预期结果**：
   - 学生端显示成功提示："注册申请已提交（申请时间：xxxx-xx-xx xx:xx:xx），请等待教师审批"
   - 显示蓝色 Alert 提示框，包含申请时间

3. **教师端验证**：
   - 进入"签到管理"模块，加载签到汇总
   - 在签到汇总下方看到"学生注册申请（1 条待审批）"区域
   - 显示学生信息：学号、姓名、专业、院系、年级、申请时间
   - 如果30秒内没有刷新，定时器会自动刷新申请列表

### 测试场景2：教师审批申请

1. **教师端操作**：
   - 点击某个待审批申请
   - 点击"批准"按钮
   - 选择目标班级（从下拉菜单中选择）
   - 点击"确认批准"

2. **预期结果**：
   - 显示成功提示："申请已批准，学生已加入名单并完成签到"
   - 申请从待审批列表中消失
   - 签到汇总中新增该学生的签到记录（状态为"正常"或"迟到"）

### 测试场景3：自动刷新机制

1. **教师端操作**：
   - 打开签到汇总页面

2. **学生端操作**：
   - 另一个学生提交注册申请

3. **预期结果**：
   - 30秒内，教师端的申请列表自动刷新
   - 新申请出现在列表中，无需手动刷新

### 测试场景4：手动刷新

1. **教师端操作**：
   - 点击注册申请区域的"刷新"按钮

2. **预期结果**：
   - 立即重新加载申请列表
   - 显示最新的待审批申请

## WebSocket 事件说明

### 新增事件类型

**`enrollment.application.created`**

- **触发时机**：学生提交注册申请且状态为 `pending` 时
- **事件数据**：
  ```json
  {
    "type": "enrollment.application.created",
    "session_id": 123,
    "application": {
      "id": 456,
      "session_id": 123,
      "student_number": "20240999",
      "name": "测试学生",
      "major": "计算机科学",
      "college": "计算机学院",
      "grade": "2024",
      "status": "pending",
      "created_at": "2026-07-11 10:30:00",
      ...
    }
  }
  ```

### 未来改进方向

如果要进一步优化，可以在教师端添加 WebSocket 监听器，实时接收 `enrollment.application.created` 事件：

```typescript
// 在 TeacherPage.tsx 中添加
useEffect(() => {
  if (!signInSummary) return;

  const ws = new WebSocket(`ws://localhost:8080/ws/classroom/${signInSummary.session.id}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "enrollment.application.created") {
      // 实时添加新申请到列表
      setEnrollmentApplications(prev => [data.application, ...prev]);
      setMessage(`收到新的注册申请：${data.application.name}`);
    }
  };

  return () => ws.close();
}, [signInSummary]);
```

## 已知限制

1. **定时刷新间隔**：当前设置为30秒，在高并发场景下可能存在延迟
2. **WebSocket 未完全集成**：虽然后端已发送 WebSocket 事件，但前端教师端尚未实现 WebSocket 监听器，目前依赖定时刷新
3. **网络失败处理**：自动刷新失败时静默处理，不会提示用户

## 代码验证

### 前端构建验证
```bash
cd frontend
npm run build
```

### 后端语法验证
```bash
cd backend
python -m compileall app/services/enrollment.py app/api/routes/classroom.py
```

## 相关文件

- `backend/app/services/enrollment.py` - 注册申请服务层
- `backend/app/api/routes/classroom.py` - 课堂相关路由
- `frontend/src/pages/TeacherPage.tsx` - 教师端页面
- `frontend/src/pages/StudentPage.tsx` - 学生端页面（反馈UI已完善）
- `backend/app/services/realtime.py` - WebSocket 管理器

## 更新日期

2026-07-11
