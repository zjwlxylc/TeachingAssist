# TeachingAssist v0.3.0（U 盘部署包）

面向高校机房课堂教学的 B/S 架构教学过程辅助系统，打包为自包含、免安装目录。
拷贝到任意 Windows 教师机的 U 盘或本地磁盘，双击 `start_teaching_assist.bat` 即可运行。

## 目录结构

```
TeachingAssistPack-v0.3.0/
├─ TeachingAssist.exe      # 后端服务（内嵌 Python 运行时与全部依赖）
├─ _internal/              # PyInstaller 运行时（勿删、勿改）
├─ frontend/dist/          # 前端生产构建静态资源
├─ config/
│  ├─ default.yaml         # 默认配置（勿改）
│  ├─ local.yaml           # 生产覆盖配置（运行时权威）
│  └─ local.example.yaml   # 本地覆盖示例
├─ docs/                   # 教师手册 / 部署清单 / 排障 / 试点反馈
├─ backup/                 # 备份输出目录（含 U 盘备份）
└─ start_teaching_assist.bat
```

## 启动方式

1. 双击 `start_teaching_assist.bat`。
2. 脚本自动探测可用端口（8080 / 8081 / 8888），启动后打开浏览器
   `http://127.0.0.1:8080`（或实际端口）。
3. 学生用同一局域网的教师机 IP 访问，例如 `http://192.168.x.x:8080`。

## 数据落盘

- 运行数据库：`C:\TeachingAssist\data\teaching_assist.db`（教师机本地磁盘，非 U 盘）。
- 备份：本地 `C:\TeachingAssist\backups` 与 U 盘 `backup/` 双重备份。

## v0.3.0 变更

- 修复「U 盘路径识别」显示成 `.` 的问题：
  - 旧版 `config/local.yaml` 误写 `removable_root: .` 导致启动检查显示 `.`；
  - 新版已省略该配置，`detect_removable_root` 会自动识别程序所在的可移动磁盘
    （U 盘盘符在别的机器上变成 F:/G: 也能自适应），并在备份目标中加入 U 盘。
- 如需固定 U 盘根目录，可在 `config/local.yaml` 的 `storage` 下写绝对路径，例如 `removable_root: E:/`。

## 与旧版区别

- `TeachingAssistPack/`（隐式 v0.1.0）与本包可并存，注意端口冲突。
- 本包启动器会校验 `project_root`，避免误连其它已运行实例。
