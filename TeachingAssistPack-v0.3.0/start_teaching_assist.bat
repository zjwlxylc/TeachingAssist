@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = @(8080, 8081, 8888); foreach ($port in $ports) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $port + '/api/v1/auth/status') -TimeoutSec 1; if ($r.StatusCode -eq 200) { $url = 'http://127.0.0.1:' + $port; Write-Host ('TeachingAssist is already running: ' + $url); Start-Process $url; exit 0 } } catch {} }; exit 1"
if not errorlevel 1 (
  pause
  exit /b 0
)

if exist "TeachingAssist.exe" (
  start "TeachingAssist Server" /min "TeachingAssist.exe"
) else if exist "backend\run.py" (
  set PYTHONPATH=%CD%\backend
  set PYTHON_EXE=python
  if exist "%CD%\.venv\Scripts\python.exe" set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
  if exist "%CD%\..\..\..\.venv\Scripts\python.exe" set PYTHON_EXE=%CD%\..\..\..\.venv\Scripts\python.exe
  echo Using Python: !PYTHON_EXE!
  "!PYTHON_EXE!" -c "import fastapi, uvicorn" >nul 2>nul
  if errorlevel 1 (
    echo Python dependencies are not installed for source fallback mode.
    echo Use TeachingAssist.exe, or run pip install -r backend\requirements.txt first.
    pause
    exit /b 1
  )
  start "TeachingAssist Server" /min "!PYTHON_EXE!" backend\run.py
) else (
  echo TeachingAssist.exe or backend\run.py not found.
  pause
  exit /b 1
)

echo TeachingAssist is starting. Detecting the active service port...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = @(8080, 8081, 8888); $ready = $null; for ($i = 0; $i -lt 40 -and -not $ready; $i++) { foreach ($port in $ports) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $port + '/api/v1/auth/status') -TimeoutSec 1; if ($r.StatusCode -eq 200) { $ready = $port; break } } catch {} }; if (-not $ready) { Start-Sleep -Milliseconds 500 } }; if ($ready) { $url = 'http://127.0.0.1:' + $ready; Write-Host ('TeachingAssist is ready: ' + $url); Start-Process $url } else { Write-Host 'TeachingAssist is still starting or the port is blocked. Try http://127.0.0.1:8080, http://127.0.0.1:8081, or http://127.0.0.1:8888.' }"
pause
