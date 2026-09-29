param(
  [string]$ReleaseName = 'TeachingAssist-Classroom-r10'
)

$ErrorActionPreference = 'Stop'
if ($ReleaseName -notmatch '^TeachingAssist-Classroom-r[0-9]+$') {
  throw 'ReleaseName must use TeachingAssist-Classroom-rN.'
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$packageRoot = Join-Path $projectRoot $ReleaseName
$zipPath = Join-Path $projectRoot "$ReleaseName.zip"
$workRoot = Join-Path $projectRoot ".runtime\package-build\$ReleaseName-$(Get-Date -Format 'yyyyMMddHHmmssfff')"
$frozenRoot = Join-Path $workRoot 'dist\TeachingAssist'
$backendData = (Join-Path $projectRoot 'backend\app') + ';app'
$configData = (Join-Path $projectRoot 'config\default.yaml') + ';config'
$frontendData = (Join-Path $projectRoot 'frontend\dist') + ';frontend\dist'

if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Root .venv Python is missing.' }
foreach ($target in @($packageRoot, $zipPath, $workRoot)) {
  if (Test-Path -LiteralPath $target) { throw "Existing build path must be reviewed before reuse: $target" }
}
New-Item -ItemType Directory -Path $workRoot -Force | Out-Null

Push-Location (Join-Path $projectRoot 'frontend')
try {
  & npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw "Frontend build failed ($LASTEXITCODE)." }
} finally { Pop-Location }

Push-Location $projectRoot
try {
  & $pythonExe -m PyInstaller --noconfirm --onedir --name TeachingAssist `
    --distpath (Join-Path $workRoot 'dist') `
    --workpath (Join-Path $workRoot 'work') `
    --specpath $workRoot `
    --paths backend `
    --hidden-import app.main `
    --add-data $backendData `
    --add-data $configData `
    --add-data $frontendData `
    backend\run.py
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)." }
} finally { Pop-Location }

if (-not (Test-Path -LiteralPath (Join-Path $frozenRoot 'TeachingAssist.exe'))) {
  throw 'Frozen executable is missing.'
}
New-Item -ItemType Directory -Path $packageRoot | Out-Null
Copy-Item -Path (Join-Path $frozenRoot '*') -Destination $packageRoot -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $packageRoot 'config') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'config\default.yaml') -Destination (Join-Path $packageRoot 'config\default.yaml')
New-Item -ItemType Directory -Path (Join-Path $packageRoot 'frontend') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'frontend\dist') -Destination (Join-Path $packageRoot 'frontend\dist') -Recurse
@'
environment: production
server:
  host: 0.0.0.0
  port: 8080
  fallback_ports: [8081, 8888]
storage:
  local_root: C:/TeachingAssist
'@ | Set-Content -LiteralPath (Join-Path $packageRoot 'config\local.yaml') -Encoding utf8

Copy-Item -LiteralPath (Join-Path $projectRoot 'scripts\start_teaching_assist.bat') -Destination (Join-Path $packageRoot '开始上课.bat')
Copy-Item -LiteralPath (Join-Path $projectRoot 'scripts\ensure_classroom_access.ps1') -Destination $packageRoot
@"
大学教学过程辅助软件 · 课堂版 r10

解压完整文件夹，在教师机双击“开始上课.bat”，浏览器会打开教师端。
首次使用若弹出 Windows 授权窗口，请允许局域网访问，然后把教师端显示的学生地址发给学生。
升级前先关闭旧版服务窗口；程序可以放本地硬盘或 U 盘运行。

教学数据库仍在教师机 C:\TeachingAssist\data\teaching_assist.db，不随程序包移动。
已有数据库沿用原教师密码；全新数据库的默认教师密码为 test123。
误建内容可在“班级管理”或“课堂签到”中搜索并点击“删除”，确认前会显示影响。
正在进行的课堂需先结束；班级仍关联课堂时先处理对应课堂。
删除不能撤销，真实教学记录请先在“系统与备份”中按需备份。

版本说明：docs\v0.4.5.md
"@ | Set-Content -LiteralPath (Join-Path $packageRoot '使用说明.txt') -Encoding utf8
New-Item -ItemType Directory -Path (Join-Path $packageRoot 'docs') | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\releases\v0.4.5.md') -Destination (Join-Path $packageRoot 'docs\v0.4.5.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\safe-academic-deletion.md') -Destination (Join-Path $packageRoot 'docs\safe-academic-deletion.md')

$exePath = Join-Path $packageRoot 'TeachingAssist.exe'
$commit = (& git -C $projectRoot rev-parse HEAD).Trim()
$info = [ordered]@{
  build = $ReleaseName
  tag = 'v0.4.5'
  source_commit = $commit
  executable_sha256 = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant()
  database_included = $false
}
$info | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $packageRoot 'BUILD-INFO.json') -Encoding utf8
Compress-Archive -Path $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Package: $packageRoot"
Write-Host "ZIP: $zipPath"
