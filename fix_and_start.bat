@echo off
chcp 65001 >nul 2>&1
echo ============================================================
echo  TeachingAssist 修复并启动
echo ============================================================
echo.

echo [1/3] 检查 Python 环境...
if exist "%~dp0.venv\Scripts\python.exe" (
    set PY=%~dp0.venv\Scripts\python.exe
    echo      使用虚拟环境: .venv\Scripts\python.exe
) else (
    set PY=python
    echo      使用系统 Python
)

echo.
echo [2/3] 验证数据库 course_students 表...
cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend
"%PY%" -c "import sqlite3; conn = sqlite3.connect('C:/TeachingAssist/data/teaching_assist.db'); cur = conn.cursor(); cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"course_students\"'); result = cur.fetchone(); print('✓ course_students 表存在' if result else '✗ course_students 表缺失'); conn.close()"

echo.
echo [3/3] 启动后端服务 (端口 8080)...
echo      按 Ctrl+C 停止服务
echo.
"%PY%" run.py

pause
