param(
  [Parameter(Mandatory = $true)]
  [string]$TargetRoot
)

$ErrorActionPreference = "Stop"
$Target = Resolve-Path -LiteralPath $TargetRoot -ErrorAction SilentlyContinue
if (-not $Target) {
  New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null
  $Target = Resolve-Path -LiteralPath $TargetRoot
}

$PackageRoot = Join-Path $Target "TeachingAssist"
$BackupRoot = Join-Path $PackageRoot "backup"
$DocsRoot = Join-Path $PackageRoot "docs"
$ConfigRoot = Join-Path $PackageRoot "config"

New-Item -ItemType Directory -Force -Path $PackageRoot, $BackupRoot, $DocsRoot, $ConfigRoot | Out-Null

Copy-Item -Path "$PSScriptRoot\*" -Destination $PackageRoot -Recurse -Force -Exclude "make_usb_package.ps1"

@"
environment: production
api_prefix: /api/v1

server:
  host: 0.0.0.0
  port: 8080
  fallback_ports:
    - 8081
    - 8888

storage:
  local_root: C:/TeachingAssist
  removable_root: $($Target.Path.Replace("\", "/"))

logging:
  level: INFO
  file_name: teaching_assist.log
"@ | Set-Content -Encoding UTF8 -Path (Join-Path $ConfigRoot "local.yaml")

Write-Host "USB package directory is ready:"
Write-Host $PackageRoot
Write-Host "Runtime database remains on C:\TeachingAssist\data\teaching_assist.db"
