@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if /I "%~1"=="--no-browser" set "TEACHING_ASSIST_NO_BROWSER=1"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe in the project root.
  echo Create the virtual environment and install backend\requirements.txt first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Missing frontend\node_modules. Run npm install in the frontend folder first.
  pause
  exit /b 1
)
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo npm.cmd was not found. Install Node.js or add it to PATH.
  pause
  exit /b 1
)

rem Do not open a portable or older service while claiming to start this source tree.
powershell -NoProfile -Command ^
  "$ports = @(8080, 8081, 8888); foreach ($port in $ports) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $port + '/api/v1/auth/status') -TimeoutSec 1; if ($r.StatusCode -eq 200) { Write-Host ('TeachingAssist is already running on port ' + $port + '. Close that server before starting this source version.'); exit 2 } } catch {} }; exit 0"
if errorlevel 1 (
  pause
  exit /b 2
)

echo Building the frontend from this source tree...
pushd frontend
call npm.cmd run build
if errorlevel 1 (
  popd
  echo Frontend build failed. See the error above.
  pause
  exit /b 1
)
popd

set "PYTHONPATH=%CD%\backend"
"%CD%\.venv\Scripts\python.exe" -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Backend dependencies are missing. Install backend\requirements.txt into .venv.
  pause
  exit /b 1
)

start "TeachingAssist Source Server" /min "%CD%\.venv\Scripts\python.exe" "%CD%\backend\run.py"
if errorlevel 1 (
  echo Could not start the source server.
  pause
  exit /b 1
)

echo Waiting for the source server...
powershell -NoProfile -Command ^
  "$ports = @(8080, 8081, 8888); for ($i = 0; $i -lt 40; $i++) { foreach ($port in $ports) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $port + '/api/v1/auth/status') -TimeoutSec 1; if ($r.StatusCode -eq 200) { $url = 'http://127.0.0.1:' + $port + '/teacher'; Write-Host ('Teacher page: ' + $url); if ($env:TEACHING_ASSIST_NO_BROWSER -ne '1') { Start-Process $url }; exit 0 } } catch {} }; Start-Sleep -Milliseconds 500 }; Write-Host 'Server did not become ready. Check the minimized TeachingAssist Source Server window.'; exit 1"
if errorlevel 1 (
  pause
  exit /b 1
)

echo Close the minimized TeachingAssist Source Server window to stop the service.
if "%TEACHING_ASSIST_NO_BROWSER%"=="1" exit /b 0
pause
