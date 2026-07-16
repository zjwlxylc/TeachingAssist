# 当前存储机制说明

## 📁 存储架构（当前实现）

### 核心设计原则
**数据存储在本地磁盘（C 盘），程序运行在 U 盘**

这正是你期望的机制！✅

---

## 🔍 详细机制

### 1. 数据存储位置（固定）

**所有数据始终存储在 C 盘**：
```
C:\TeachingAssist\
├── data\
│   └── teaching_assist.db      # 数据库（固定位置）
├── uploads\                     # 学生上传文件
├── backups\                     # 本地备份
├── logs\                        # 日志文件
└── runtime\                     # 运行时临时文件
```

**配置位置**：`config/default.yaml`
```yaml
storage:
  local_root: C:/TeachingAssist  # 固定，不会改变
```

### 2. U 盘自动检测

系统会自动检测 U 盘：

**检测逻辑**（`app/services/startup.py`）：
1. 如果程序从 U 盘运行（如 E:\TeachingAssist.exe）
   - 自动识别 U 盘为 `E:\`
2. 如果程序从本地运行
   - 自动扫描所有可移动磁盘，找到第一个 U 盘

### 3. 自动备份到 U 盘

**双重备份机制**：

当你执行备份时，系统会自动创建两份备份：

1. **本地备份**（C 盘）：
   ```
   C:\TeachingAssist\backups\
   └── teaching_assist_manual_20260712_235959_abc123.db
   ```

2. **U 盘备份**（自动检测）：
   ```
   E:\backup\  (或你的 U 盘盘符)
   └── teaching_assist_manual_20260712_235959_abc123.db
   ```

**代码实现**（`app/services/backup.py`）：
```python
def _backup_targets() -> list[tuple[str, Path]]:
    targets = []
    targets.append(("local", C:/TeachingAssist/backups/))  # 本地

    removable_root = detect_removable_root(settings)
    if removable_root:
        targets.append(("removable", removable_root / "backup"))  # U 盘

    return targets
```

---

## ✅ 使用场景验证

### 场景 1：第一次在机房 A 使用

1. U 盘插入教师机 A
2. 运行 `E:\TeachingAssist-0.4.1\start_teaching_assist.bat`
3. 系统检查 `C:\TeachingAssist\data\teaching_assist.db`
4. **不存在** → 自动创建新数据库
5. 你创建课程、导入学生、上课
6. 数据保存在 `C:\TeachingAssist\`

### 场景 2：下次在机房 A 使用

1. U 盘插入同一台教师机 A
2. 运行程序
3. 系统检查 `C:\TeachingAssist\data\teaching_assist.db`
4. **存在** → 使用现有数据库
5. 你的历史数据都在（课程、学生、历史课堂）

### 场景 3：第一次在机房 B 使用

1. U 盘插入教师机 B
2. 运行程序
3. 系统检查 `C:\TeachingAssist\data\teaching_assist.db`
4. **不存在** → 自动创建新数据库
5. 这是一个全新的环境，需要重新导入学生

### 场景 4：在机房 A 备份到 U 盘

1. 在机房 A 上课完成
2. 点击"创建备份"
3. 系统自动创建两份：
   - `C:\TeachingAssist\backups\...` （本地）
   - `E:\backup\...` （U 盘）
4. 拔出 U 盘，备份随身携带

### 场景 5：在机房 B 恢复机房 A 的数据

1. U 盘插入教师机 B
2. 打开系统，点击"恢复备份"
3. 选择 U 盘上的备份文件 `E:\backup\...`
4. 恢复到 `C:\TeachingAssist\data\teaching_assist.db`
5. 现在机房 B 有了机房 A 的所有数据

---

## 🎯 关键特性

### ✅ 符合你的需求

1. **数据在 C 盘**
   - 每台教师机有独立的数据
   - 不会因 U 盘拔出而丢失
   - SQLite WAL 模式要求（不能在 U 盘）

2. **程序在 U 盘**
   - 便携，带到任何机房
   - 更新方便，只需更新 U 盘内容
   - 不需要在每台机器安装

3. **自动备份到 U 盘**
   - 备份随身携带
   - 可在不同机房恢复数据
   - 双重保险（本地 + U 盘）

### 🔄 数据流转

```
机房 A 教师机:
  上课 → C:\TeachingAssist\data\
       → 备份 → C:\TeachingAssist\backups\ (本地)
                E:\backup\ (U 盘)

U 盘携带到机房 B:
  恢复 ← E:\backup\
       → C:\TeachingAssist\data\ (机房 B)
```

---

## 📋 配置文件说明

### default.yaml（默认配置）
```yaml
storage:
  local_root: C:/TeachingAssist  # 数据始终在 C 盘
  # removable_root: 不设置，自动检测 U 盘
```

### 为什么不配置 removable_root？
注释中说明：
> removable_root 省略：修复后的 detect_removable_root 会自动识别程序所在的可移动磁盘（U 盘盘符变化也能自适应）

这意味着：
- E 盘、F 盘、G 盘等，无论 U 盘盘符是什么
- 系统都能自动检测并使用
- 无需手动配置

---

## 💡 总结

**现在的机制完全符合你的使用场景！** ✅

1. ✅ C 盘有数据 → 用原来的数据
2. ✅ C 盘没数据 → 创建新数据库
3. ✅ 备份到 U 盘 → 自动双重备份
4. ✅ U 盘便携 → 程序在 U 盘，数据在 C 盘
5. ✅ 盘符自适应 → 自动检测 U 盘，无需配置

**没有变化，机制一直是这样的！** 😊

唯一需要注意：
- 不同机房的教师机有各自独立的数据
- 如需在机房间共享数据，使用备份/恢复功能
- 每次在新机房使用前，可以恢复 U 盘上的备份

---

**文档位置**：`docs/storage-mechanism-explained.md`
**最后更新**：2026-07-12
