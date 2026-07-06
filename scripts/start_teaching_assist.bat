@echo off
setlocal
cd /d "%~dp0"

if exist "TeachingAssist.exe" (
  start "" "TeachingAssist.exe"
) else if exist "backend\run.py" (
  set PYTHONPATH=%CD%\backend
  python backend\run.py
) else (
  echo TeachingAssist.exe or backend\run.py not found.
  pause
  exit /b 1
)

echo TeachingAssist is starting. Open http://127.0.0.1:8080 in the teacher browser.
echo If port 8080 is occupied, try http://127.0.0.1:8081 or http://127.0.0.1:8888.
pause
