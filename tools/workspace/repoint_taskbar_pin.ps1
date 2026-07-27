<#
.SYNOPSIS
  Point the pinned taskbar shortcut at the workspace chooser.

.DESCRIPTION
  make_lane_launchers.py wrote Desktop shortcuts and Start-Claude.ps1 gave them a
  chooser, but neither touched the shortcut that is actually clicked. On
  2026-07-27 the taskbar pin still read

      wt.exe -d "C:\Users\shova\Downloads\new-recruit" pwsh -NoExit -Command claude

  so every session opened in one repo with CLAUDE_LANE unset, which is the exact
  defect the lane work was supposed to close. A fix installed next to the habit
  instead of inside it is not installed.

  Windows blocks programmatic pin and unpin, so the pin position is kept by
  rewriting the existing .lnk in place rather than replacing it. Two properties
  survive that rewrite only if they are carried across by hand:

    - the custom icon, which WScript.Shell keeps only because it is re-set here
    - the run-as-administrator bit, byte 21 flag 0x20, which Save() clears

  The filename is deliberately NOT changed. The taskbar label comes from the file
  name, and renaming a pinned .lnk orphans the pin. The label stays stale until
  the operator unpins and repins by hand.

    pwsh -File repoint_taskbar_pin.ps1            # show the plan
    pwsh -File repoint_taskbar_pin.ps1 -Apply     # rewrite the pin
    pwsh -File repoint_taskbar_pin.ps1 -Revert    # restore from the .bak
#>

[CmdletBinding()]
param(
    [switch] $Apply,
    [switch] $Revert
)

$ErrorActionPreference = 'Stop'
$Home_ = [Environment]::GetFolderPath('UserProfile')

$Pin = Join-Path $env:APPDATA `
    'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Claude new-recruit (Admin).lnk'
$Backup = "$Pin.bak"
$Wt = Join-Path $Home_ 'AppData\Local\Microsoft\WindowsApps\wt.exe'
$Chooser = Join-Path $Home_ 'claude-setup\tools\workspace\Start-Claude.ps1'
$Cwd = Join-Path $Home_ 'claude-setup'
$Args_ = '-NoExit -File "{0}"' -f $Chooser
$Desc = 'Claude: choose workspace (global lane / existing project / new project)'

# The elevation bit lives in the ShellLinkHeader LinkFlags field. WScript.Shell
# cannot read or write it, so it is read before Save() and stamped back after.
function Get-RunAsAdmin { param([string] $Path)
    return [bool]([IO.File]::ReadAllBytes($Path)[21] -band 0x20)
}
function Set-RunAsAdmin { param([string] $Path)
    $b = [IO.File]::ReadAllBytes($Path)
    $b[21] = $b[21] -bor 0x20
    [IO.File]::WriteAllBytes($Path, $b)
}

if (-not (Test-Path $Pin)) { Write-Host "  pin not found: $Pin" -ForegroundColor Red; exit 1 }

if ($Revert) {
    if (-not (Test-Path $Backup)) { Write-Host "  no backup at $Backup" -ForegroundColor Red; exit 1 }
    Copy-Item $Backup $Pin -Force
    Write-Host "  restored $Pin from backup" -ForegroundColor Green
    exit 0
}

$sh = New-Object -ComObject WScript.Shell
$cur = $sh.CreateShortcut($Pin)
$wasAdmin = Get-RunAsAdmin $Pin

Write-Host ''
Write-Host '  PIN' -ForegroundColor Cyan
Write-Host ("    file   {0}" -f $Pin)
Write-Host ("    now    {0} {1}" -f $cur.TargetPath, $cur.Arguments) -ForegroundColor DarkYellow
Write-Host ("    after  {0} pwsh {1}" -f $Wt, $Args_) -ForegroundColor Green
Write-Host ("    icon   {0}" -f $cur.IconLocation)
Write-Host ("    admin  {0} (preserved)" -f $wasAdmin)

if (-not (Test-Path $Wt)) { Write-Host '  wt.exe not found; nothing written.' -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Chooser)) { Write-Host "  chooser not found: $Chooser" -ForegroundColor Red; exit 1 }

if (-not $Apply) {
    Write-Host ''
    Write-Host '  PLAN ONLY. Re-run with -Apply to rewrite the pin.'
    exit 0
}

Copy-Item $Pin $Backup -Force
$icon = $cur.IconLocation

$l = $sh.CreateShortcut($Pin)
$l.TargetPath = $Wt
# wt.exe passes everything after its own switches to the child, so pwsh gets
# -NoExit -File. No -d: the chooser sets the working directory once it knows it.
$l.Arguments = 'pwsh ' + $Args_
$l.WorkingDirectory = $Cwd
$l.Description = $Desc
if ($icon) { $l.IconLocation = $icon }
$l.Save()

if ($wasAdmin) { Set-RunAsAdmin $Pin }

$after = $sh.CreateShortcut($Pin)
$ok = ($after.Arguments -eq ('pwsh ' + $Args_)) -and ((Get-RunAsAdmin $Pin) -eq $wasAdmin)
Write-Host ''
if ($ok) {
    Write-Host "  rewritten. backup at $Backup" -ForegroundColor Green
    Write-Host '  the taskbar LABEL still says "new-recruit"; unpin and repin to fix the text.' -ForegroundColor DarkYellow
    exit 0
}
Write-Host '  verification failed; restore with -Revert' -ForegroundColor Red
exit 1
