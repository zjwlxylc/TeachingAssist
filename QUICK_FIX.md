# 快速修复指南

> 本文记录的是旧版故障。当前版本已通过数据库迁移废弃 `course_students` 表，请勿按下方旧命令手动创建该表。当前源码统一双击仓库根目录的 `开始上课.bat` 启动。

## 当前问题：系统内部错误

**症状：** 浏览器红色警告 + 连接已断开

**原因：** 数据库缺少 `course_students` 表

## 快速修复（3 步）

### 第 1 步：停止服务
关闭所有标题为 "TA-Backend" 和 "TA-Frontend" 的命令行窗口

### 第 2 步：创建缺失的表
打开 PowerShell 或 CMD，运行：

```powershell
cd D:\Agent\TeachingAssist-main\backend
$env:PYTHONPATH = "D:\Agent\TeachingAssist-main\backend"
python -c "import sqlite3; conn = sqlite3.connect('C:/TeachingAssist/data/teaching_assist.db'); conn.execute('CREATE TABLE IF NOT EXISTS course_students (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, class_id INTEGER NOT NULL, student_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime(''now'')), UNIQUE(course_id, student_id), FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE, FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE, FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE)'); conn.commit(); print('✓ 表已创建'); conn.close()"
```

### 第 3 步：重新启动
双击 `开始上课.bat`

---

## 验证修复成功

打开浏览器访问 http://127.0.0.1:8080/teacher（若默认端口被其他程序占用，以启动窗口显示的地址为准）

如果：
- ✅ 页面正常显示
- ✅ 左下角显示"已连接"或没有连接警告
- ✅ 没有红色错误提示

说明问题已解决！

---

## 如果还有问题

查看详细排查文档：`docs/troubleshooting-course-students-table.md`

或者运行自检脚本：
```powershell
python scripts\selftest_smoke.py
```
