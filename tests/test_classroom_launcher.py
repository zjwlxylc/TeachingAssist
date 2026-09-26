import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "win32", "Windows launcher")
class ClassroomLauncherTests(unittest.TestCase):
    def test_existing_rule_checks_do_not_modify_firewall_or_request_elevation(self):
        helper = Path(__file__).resolve().parents[1] / "scripts/ensure_classroom_access.ps1"
        program = str(Path(sys.executable).resolve()).replace("'", "''")
        for enabled, correct_program, expected in [(True, True, 0), (False, True, 2), (True, False, 2)]:
            with self.subTest(enabled=enabled, correct_program=correct_program), tempfile.TemporaryDirectory() as directory:
                harness = Path(directory) / "check.ps1"
                configured = program if correct_program else "C:\\OldVersion\\TeachingAssist.exe"
                harness.write_text(f"""
function Get-NetFirewallRule {{ [CmdletBinding()] param($Name) [pscustomobject]@{{ Enabled='{str(enabled)}'; Action='Allow'; Direction='Inbound'; Profile='Any' }} }}
function Get-NetFirewallApplicationFilter {{ [pscustomobject]@{{ Program='{configured}' }} }}
function Get-NetFirewallPortFilter {{ [pscustomobject]@{{ Protocol='TCP'; LocalPort=@('8081','8888','8080') }} }}
function Get-NetFirewallAddressFilter {{ [pscustomobject]@{{ RemoteAddress='LocalSubnet' }} }}
function New-NetFirewallRule {{ throw 'Unexpected firewall mutation' }}
function Set-NetFirewallRule {{ throw 'Unexpected firewall mutation' }}
function Start-Process {{ throw 'Unexpected elevation' }}
& '{str(helper).replace("'", "''")}' -ProgramPath '{program}' -CheckOnly
exit $LASTEXITCODE
""", encoding="utf-8-sig")
                result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)], capture_output=True, timeout=20)
                self.assertEqual(result.returncode, expected, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
