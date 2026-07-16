# U 盘备份机制详解

## 📋 当前机制分析

### 备份文件命名规则

**格式**：`teaching_assist_{backup_type}_{timestamp}_{uuid}.db`

**示例**：
```
teaching_assist_manual_20260713_001530_a3f9d2.db
teaching_assist_manual_20260713_015820_b7e4c1.db
teaching_assist_automatic_20260713_023000_c8f2d5.db
```

**命名组成**：
1. `teaching_assist_` - 固定前缀
2. `manual` 或 `automatic` - 备份类型
3. `20260713_001530` - 时间戳（年月日_时分秒）
4. `a3f9d2` - 6 位随机 UUID（避免同一秒内重复）
5. `.db` - 文件扩展名

---

## 🔄 多教室使用场景

### 场景分析

**A 教室操作**：
1. 上完课，点击"创建备份"
2. 系统创建两份备份：
   - C 盘：`C:\TeachingAssist\backups\teaching_assist_manual_20260713_100000_abc123.db`
   - U 盘：`E:\backup\teaching_assist_manual_20260713_100000_abc123.db`

**B 教室操作**：
1. 插入 U 盘，启动程序
2. B 教室的 C 盘是空的，系统创建新数据库
3. 上完课，点击"创建备份"
4. 系统创建两份备份：
   - C 盘（B 教室）：`C:\TeachingAssist\backups\teaching_assist_manual_20260713_150000_def456.db`
   - U 盘：`E:\backup\teaching_assist_manual_20260713_150000_def456.db`

**结果**：
```
E:\backup\
├── teaching_assist_manual_20260713_100000_abc123.db  ← A 教室的备份
└── teaching_assist_manual_20260713_150000_def456.db  ← B 教室的备份
```

**U 盘确实同时包含两个教室的备份！** ✅

---

## 📊 自动清理机制

### 清理规则

**代码逻辑**：
```python
BACKUP_KEEP_COUNT = 5  # 每个位置保留最新的 5 个备份

def _cleanup_old_backups(target_dir: Path):
    # 按修改时间排序，保留最新的 5 个
    backups = sorted(target_dir.glob("teaching_assist_*.db"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True)
    # 删除第 6 个及之后的旧备份
    for stale in backups[BACKUP_KEEP_COUNT:]:
        stale.unlink(missing_ok=True)
```

### 清理行为

**每次备份后自动清理**：
- 保留最新的 5 个备份文件
- 删除更老的备份

**示例**：
```
U 盘初始状态（空）
  └── backup/ (空)

A 教室备份 1 次：
  └── backup/
      └── A1.db

A 教室备份 2 次：
  └── backup/
      ├── A1.db
      └── A2.db

B 教室备份 1 次：
  └── backup/
      ├── A1.db
      ├── A2.db
      └── B1.db

B 教室备份 2 次：
  └── backup/
      ├── A1.db
      ├── A2.db
      ├── B1.db
      └── B2.db

继续备份（A3, B3, A4...）直到有 6 个文件时：
  └── backup/
      ├── A2.db  (最老的 A1.db 被删除)
      ├── B1.db
      ├── B2.db
      ├── A3.db
      ├── B3.db
      └── A4.db  (最新的)
```

**关键点**：
- 清理是按**时间**排序，不区分教室
- A 教室和 B 教室的备份**混在一起计数**
- 如果 A 教室备份 5 次，B 教室备份 1 次，第 6 次 B 教室备份会导致最老的 A 教室备份被删除

---

## ⚠️ 潜在问题

### 问题 1：备份混淆

**现象**：
- U 盘上的备份来自不同教室
- 无法从文件名区分哪个是 A 教室、哪个是 B 教室
- 恢复时可能选错教室的数据

**影响**：
- 可能把 B 教室的数据恢复到 A 教室（反之亦然）
- 导致数据混乱

### 问题 2：备份互相覆盖

**现象**：
- A 教室备份 3 次，B 教室备份 3 次
- U 盘上只能保留最新的 5 个
- 可能 A 教室的所有备份都被清理掉

**影响**：
- 某个教室的历史备份丢失
- 无法回溯到早期状态

---

## 💡 解决方案建议

### 方案 1：备份文件名包含机器标识（推荐）

**修改命名规则**：
```python
# 获取机器名或 MAC 地址
import socket
machine_name = socket.gethostname()

# 文件名格式
teaching_assist_{machine_name}_{backup_type}_{timestamp}_{uuid}.db
```

**示例**：
```
E:\backup\
├── teaching_assist_RoomA-PC01_manual_20260713_100000_abc123.db
├── teaching_assist_RoomA-PC01_manual_20260713_110000_def456.db
├── teaching_assist_RoomB-PC02_manual_20260713_150000_ghi789.db
└── teaching_assist_RoomB-PC02_manual_20260713_160000_jkl012.db
```

**优点**：
- 文件名清晰标识来源教室
- 恢复时不会选错
- 仍然可以自动清理

**缺点**：
- 文件名更长
- 仍然会混合清理（但至少能区分来源）

### 方案 2：按教室分目录存储

**目录结构**：
```
E:\backup\
├── RoomA-PC01\
│   ├── teaching_assist_manual_20260713_100000_abc123.db
│   └── teaching_assist_manual_20260713_110000_def456.db
└── RoomB-PC02\
    ├── teaching_assist_manual_20260713_150000_ghi789.db
    └── teaching_assist_manual_20260713_160000_jkl012.db
```

**修改代码**：
```python
def _backup_targets() -> list[tuple[str, Path]]:
    settings = get_settings()
    targets: list[tuple[str, Path]] = []

    if settings.storage.backups_dir:
        targets.append(("local", settings.storage.backups_dir))

    removable_root = detect_removable_root(settings)
    if removable_root:
        # 按机器名创建子目录
        machine_name = socket.gethostname()
        targets.append(("removable", removable_root / "backup" / machine_name))

    return targets
```

**优点**：
- 每个教室独立清理，互不影响
- A 教室的 5 个备份和 B 教室的 5 个备份互不冲突
- 恢复时直接选择对应教室的目录

**缺点**：
- 目录结构稍复杂
- 需要知道机器名才能找到备份

### 方案 3：手动选择备份策略

**在备份时提示用户**：
```
[ ] 仅备份到本地 C 盘
[ ] 仅备份到 U 盘
[x] 同时备份到本地和 U 盘（默认）

提示：U 盘备份可在其他教室恢复，但会与其他教室的备份混合。
如需隔离，请在每个教室使用不同的 U 盘。
```

---

## 📝 当前机制总结

### 现状

✅ **优点**：
- 自动双重备份（本地 + U 盘）
- 自动清理旧备份（保留 5 个）
- 文件名有时间戳，避免覆盖

⚠️ **缺点**：
- U 盘备份来自不同教室，无法区分
- 恢复时可能选错教室的数据
- 多教室备份会互相挤占清理配额

### 当前行为

1. **U 盘会同时包含多个教室的备份** ✅
2. **自动清理保留最新 5 个**（不区分教室）
3. **无法从文件名识别来源教室**

---

## 🎯 你的具体问题回答

> U 盘是不是就变成了既有 A 教室又有 B 教室的数据？

**答：是的！** U 盘会同时包含两个教室的备份文件。

> 换新教室的时候，到底是拷贝了哪个教室的数据呢？

**答：取决于你恢复时选择哪个备份文件。**

恢复备份时的流程：
1. 系统列出所有可用的备份文件
2. 显示文件名和时间戳
3. 你手动选择要恢复哪一个

**问题**：文件名没有教室标识，你只能根据时间戳猜测。

**示例**：
```
可恢复的备份：
1. teaching_assist_manual_20260713_100000_abc123.db (上午 10:00)
2. teaching_assist_manual_20260713_150000_def456.db (下午 3:00)
```

你需要记住：
- 上午 10:00 是在 A 教室备份的
- 下午 3:00 是在 B 教室备份的

**容易出错！**

---

## 💭 建议行动

我建议实施**方案 2（按教室分目录）**，这样：
- 每个教室有独立的备份目录
- 清理配额独立（A 教室 5 个，B 教室 5 个）
- 恢复时直接选择对应教室的目录，不会搞混

需要我帮你实现这个改进吗？

---

**文档位置**：`docs/backup-mechanism-multi-classroom.md`
**最后更新**：2026-07-13
