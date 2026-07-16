param(
  [string]$Version = "0.1.0",
  [switch]$SkipFrontend,
  [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$ReleaseRoot = Join-Path $Root ".runtime\release"
$PackageRoot = Join-Path $ReleaseRoot "TeachingAssist-$Version"

Remove-Item -LiteralPath $PackageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null

if (-not $SkipFrontend) {
  Push-Location $Frontend
  npm.cmd install
  npm.cmd run build
  Pop-Location
}

if (-not $SkipPyInstaller) {
  $Python = Join-Path $Root ".venv\Scripts\python.exe"
  if (-not (Test-Path $Python)) {
    $Python = "python"
  }
  & $Python -m pip install pyinstaller
  Push-Location $Root
  & $Python -m PyInstaller `
    --clean `
    --noconfirm `
    --name TeachingAssist `
    --paths backend `
    --add-data "config;config" `
    --add-data "frontend\dist;frontend\dist" `
    --add-data "backend\app;app" `
    "backend\run.py"
  Pop-Location

  Copy-Item -Path (Join-Path $Root "dist\TeachingAssist\*") -Destination $PackageRoot -Recurse -Force
} else {
  New-Item -ItemType Directory -Force -Path (Join-Path $PackageRoot "backend") | Out-Null
  robocopy (Join-Path $Backend "app") (Join-Path $PackageRoot "backend\app") /E /XD __pycache__ /XF *.pyc | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "Failed to copy backend source files"
  }
  Copy-Item -Path (Join-Path $Backend "run.py") -Destination (Join-Path $PackageRoot "backend") -Force
  Copy-Item -Path (Join-Path $Backend "requirements.txt") -Destination (Join-Path $PackageRoot "backend") -Force
  Copy-Item -Path (Join-Path $Backend "requirements-build.txt") -Destination (Join-Path $PackageRoot "backend") -Force
}

Copy-Item -Path (Join-Path $Root "config") -Destination (Join-Path $PackageRoot "config") -Recurse -Force
@"
environment: production
api_prefix: /api/v1

server:
  host: 127.0.0.1
  port: 8080
  fallback_ports:
    - 8081
    - 8888
  cors_origins:
    - http://localhost:5173
    - http://127.0.0.1:5173

storage:
  local_root: C:/TeachingAssist

logging:
  level: INFO
  file_name: teaching_assist.log
"@ | Set-Content -Encoding UTF8 -Path (Join-Path $PackageRoot "config\local.yaml")
Copy-Item -Path (Join-Path $Root "frontend\dist") -Destination (Join-Path $PackageRoot "frontend\dist") -Recurse -Force
Copy-Item -Path (Join-Path $Root "scripts\start_teaching_assist.bat") -Destination $PackageRoot -Force
Copy-Item -Path (Join-Path $Root "scripts\make_usb_package.ps1") -Destination $PackageRoot -Force
New-Item -ItemType Directory -Force -Path (Join-Path $PackageRoot "docs") | Out-Null
Copy-Item -Path (Join-Path $Root "docs\teacher-user-manual.md") -Destination (Join-Path $PackageRoot "docs") -Force
Copy-Item -Path (Join-Path $Root "docs\deployment-checklist.md") -Destination (Join-Path $PackageRoot "docs") -Force
Copy-Item -Path (Join-Path $Root "docs\troubleshooting.md") -Destination (Join-Path $PackageRoot "docs") -Force
Copy-Item -Path (Join-Path $Root "docs\pilot-feedback-report.md") -Destination (Join-Path $PackageRoot "docs") -Force

$ZipPath = Join-Path $ReleaseRoot "TeachingAssist-$Version.zip"
Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $PackageRoot -DestinationPath $ZipPath -Force

Write-Host "Release package created:"
Write-Host $PackageRoot
Write-Host $ZipPath
