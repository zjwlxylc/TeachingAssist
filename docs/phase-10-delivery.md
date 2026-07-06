# 阶段 10 交付说明

## 已完成

1. 前端生产构建流程已接入阶段验证，后端可托管 `frontend/dist` 静态资源。
2. 新增 PyInstaller 打包脚本 `scripts/build_release.ps1`，可生成 Windows 部署目录和 ZIP 包。
3. 新增启动器 `scripts/start_teaching_assist.bat`，支持优先启动可执行程序，缺少可执行程序时回退到源码运行。
4. 新增 U 盘目录生成脚本 `scripts/make_usb_package.ps1`，可生成 `TeachingAssist`、`backup`、`docs`、`config` 目录并写入 U 盘本地配置。
5. 新增构建依赖清单 `backend/requirements-build.txt`，固定 PyInstaller 版本。
6. 新增教师使用手册、部署检查清单、故障排查手册和试点反馈报告模板。
7. 后端配置根目录识别已兼容 PyInstaller 打包环境，生产模式下启动不再默认开启 reload。

## 打包命令

```powershell
.\scripts\build_release.ps1 -Version 0.1.0
```

输出目录：

```text
.runtime\release\TeachingAssist-0.1.0
.runtime\release\TeachingAssist-0.1.0.zip
```

如只需验证目录结构、不执行 PyInstaller：

```powershell
.\scripts\build_release.ps1 -Version 0.1.0 -SkipPyInstaller
```

## U 盘目录

在部署包目录中执行：

```powershell
.\make_usb_package.ps1 -TargetRoot E:\
```

生成结构：

```text
TeachingAssist/
  TeachingAssist.exe
  start_teaching_assist.bat
  config/
    default.yaml
    local.yaml
  frontend/
    dist/
  backup/
  docs/
```

运行数据库仍位于教师机本地：

```text
C:\TeachingAssist\data\teaching_assist.db
```

## 文档交付

- `docs/teacher-user-manual.md`
- `docs/deployment-checklist.md`
- `docs/troubleshooting.md`
- `docs/pilot-feedback-report.md`

## 验证记录

已执行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

打包脚本可在安装构建依赖后执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-build.txt
.\scripts\build_release.ps1 -Version 0.1.0
```

## 试点说明

真实机房试运行需在目标环境完成，建议按 `docs/deployment-checklist.md` 逐项检查，并使用 `docs/pilot-feedback-report.md` 记录教师和学生反馈。
