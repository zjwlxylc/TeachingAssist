param(
  [Parameter(Mandatory = $true)][string]$ProgramPath,
  [switch]$Configure,
  [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$RuleName = 'TeachingAssist-Classroom-LocalSubnet'
$ProgramPath = (Resolve-Path -LiteralPath $ProgramPath).Path
$Ports = @('8080', '8081', '8888')

function Test-ClassroomRule {
  $rule = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
  if (-not $rule -or $rule.Enabled -ne 'True' -or $rule.Action -ne 'Allow' -or $rule.Direction -ne 'Inbound' -or $rule.Profile -ne 'Any') { return $false }
  $application = $rule | Get-NetFirewallApplicationFilter
  $port = $rule | Get-NetFirewallPortFilter
  $address = $rule | Get-NetFirewallAddressFilter
  return ($application.Program -eq $ProgramPath -and $port.Protocol -eq 'TCP' -and
    (@($port.LocalPort | Sort-Object) -join ',') -eq ($Ports -join ',') -and
    (@($address.RemoteAddress) -join ',') -eq 'LocalSubnet')
}

try {
  if (Test-ClassroomRule) { exit 0 }
  if ($CheckOnly) { exit 2 }
  if ($Configure) {
    $administrator = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $administrator) { throw 'Administrator approval is required.' }
    $rule = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
    if ($rule) {
      $rule | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Any
      $rule | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $ProgramPath
      $rule | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $Ports
      $rule | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet
    } else {
      New-NetFirewallRule -Name $RuleName -DisplayName 'TeachingAssist classroom access' -Direction Inbound -Action Allow -Enabled True -Profile Any -Program $ProgramPath -Protocol TCP -LocalPort $Ports -RemoteAddress LocalSubnet | Out-Null
    }
    if (-not (Test-ClassroomRule)) { throw 'Classroom network rule verification failed.' }
    exit 0
  }
  Write-Host 'First classroom startup: approve the Windows prompt to allow students on this local network.'
  $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -ProgramPath "{1}" -Configure' -f $PSCommandPath, $ProgramPath
  $setup = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
  exit $setup.ExitCode
} catch {
  Write-Host 'Classroom network setup was not completed. The teacher page can still open, but students may be unable to connect.'
  Write-Host $_.Exception.Message
  exit 1
}
