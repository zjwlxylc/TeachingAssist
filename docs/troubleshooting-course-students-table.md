# 问题排查：course_students 表缺失导致的系统错误

## 问题症状

- 浏览器显示红色警告："系统内部错误"
- 左下角显示："连接已断开"
- 后端日志报错：`sqlite3.OperationalError: no such table: course_students`

## 根本原因

数据库中缺少 `course_students` 表，该表应该在迁移 `003_course_class_import.sql` 中创建，但由于某种原因未成功创建或被删除。

## 解决方案

### 方案一：手动创建表（推荐）

1. 停止后端服务（关闭 TA-Backend 窗口）

2. 运行以下 Python 脚本创建表：

```bash
cd D:\Agent\TeachingAssist-main\backend
set PYTHONPATH=D:\Agent\TeachingAssist-main\backend
python -c "import sqlite3; conn = sqlite3.connect('C:/TeachingAssist/data/teaching_assist.db'); conn.execute('CREATE TABLE IF NOT EXISTS course_students (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, class_id INTEGER NOT NULL, student_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime(\"now\")), UNIQUE(course_id, student_id), FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE, FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE, FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE)'); conn.commit(); conn.close(); print('course_students 表已创建')"
```

3. 重新双击 `start_dev.bat` 启动服务

### 方案二：使用修复脚本

已为你创建了 `fix_and_start.bat` 脚本，它会：
- 检查 Python 环境
- 验证 course_students 表是否存在
- 启动后端服务

**使用方法：**
1. 关闭所有 TA-Backend 和 TA-Frontend 窗口
2. 双击 `fix_and_start.bat`
3. 等待后端启动完成（看到 "Application startup complete" 信息）
4. 在新的命令行窗口中启动前端：
   ```bash
   cd frontend
   npm run dev
   ```
5. 浏览器访问 http://127.0.0.1:5173

### 方案三：重建数据库（慎用）

如果以上方案都不行，可以重建整个数据库：

```bash
# 备份现有数据库
copy C:\TeachingAssist\data\teaching_assist.db C:\TeachingAssist\data\teaching_assist.db.backup

# 删除数据库
del C:\TeachingAssist\data\teaching_assist.db

# 重新初始化
cd D:\Agent\TeachingAssist-main
python scripts\init_db.py
```

**注意：这会丢失所有现有数据！**

## 验证修复

运行以下命令验证表是否存在：

```bash
cd D:\Agent\TeachingAssist-main\backend
set PYTHONPATH=D:\Agent\TeachingAssist-main\backend
python -c "import sqlite3; conn = sqlite3.connect('C:/TeachingAssist/data/teaching_assist.db'); cur = conn.cursor(); cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"course_students\"'); print('✓ 表存在' if cur.fetchone() else '✗ 表不存在'); conn.close()"
```

## 预防措施

1. **定期备份**：使用系统内置的备份功能定期备份数据库
2. **检查迁移**：每次启动时检查日志，确保所有迁移都成功应用
3. **数据库完整性检查**：定期运行 `scripts/selftest_smoke.py` 进行自检

## 相关文件

- 迁移文件：`backend/app/db/migrations/003_course_class_import.sql`
- 数据库位置：`C:\TeachingAssist\data\teaching_assist.db`
- 日志位置：`C:\TeachingAssist\logs\teaching_assist.log`

## 时间线

- **2026-07-12 23:25:00**: 首次发现错误
- **2026-07-12 23:26:47**: 持续报错
- **2026-07-12 23:30**: 手动创建表并提供修复方案

## 后续改进建议

1. 在启动时添加关键表的存在性检查
2. 如果发现表缺失，自动尝试重新创建
3. 在迁移系统中添加表完整性验证
