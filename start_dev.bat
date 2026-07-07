@echo off
setlocal
chcp 65001 >nul 2>&1
REM ============================================================
REM  TeachingAssist Dev Launcher
REM  Double-click to start backend(8080) + frontend(5173)
REM  Close the two popup windows to stop.
REM ============================================================
set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

if exist "%ROOT%.venv\Scripts\python.exe" (
    set PY=%ROOT%.venv\Scripts\python.exe
) else (
    set PY=python
)

echo [Dev] Starting backend  -> http://127.0.0.1:8080
start "TA-Backend" /d "%BACKEND%" cmd /k "set PYTHONPATH=%BACKEND% & "%PY%" run.py"

echo [Dev] Starting frontend -> http://127.0.0.1:5173
if not exist "%FRONTEND%\node_modules" (
    echo [Dev] node_modules not found, running npm install first...
    start "TA-Frontend" /d "%FRONTEND%" cmd /k "npm install & npm run dev"
) else (
    start "TA-Frontend" /d "%FRONTEND%" cmd /k "npm run dev"
)

echo [Dev] Opening browser in a few seconds...
timeout /t 6 /nobreak >nul
start http://127.0.0.1:5173

echo [Dev] Ready. Close TA-Backend and TA-Frontend windows to stop.
pause
