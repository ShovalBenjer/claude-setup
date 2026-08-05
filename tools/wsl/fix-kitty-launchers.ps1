<#
.SYNOPSIS
  Point every Claude launcher at kitty 0.48.2, launched without a console window.

.DESCRIPTION
  Measured 2026-08-01 on this machine. The desktop shortcut and the taskbar pin had
  drifted apart, and the pin is the one that gets clicked:

    pin      (2026-07-30 04:47)  wsl.exe  -d Ubuntu -- kitty --title "..." bash -lc "..."
    desktop  (2026-08-01 05:42)  wsl.exe  -d Ubuntu -- /home/shov/.local/kitty.app/bin/kitty
                                          --start-as=fullscreen --title "..." bash -lc "..."

  The running process confirmed which one launched: /proc/<pid>/exe resolved to
  /usr/bin/kitty and argv[0] was the bare word "kitty" with no --start-as flag. So the
  pin ran, bare `kitty` resolved through PATH to the apt build, and the session got
  kitty 0.32.2 while ~/.config/kitty/kitty.conf had been written and commented against
  0.48.2 (0.32.2 exposes 174 options, 0.48.2 exposes 225).

  Three reported symptoms are that one fact:

    [PARSE ERROR] Unsupported screen mode: 2031 (private)
        DECSET 2031 is the contour color-scheme-change notification. kitty added it in
        0.38.1 (2024-12-26, changelog line 1161 of the shipped 0.48.2 docs). Claude Code
        sends it: `THEME_NOTIFY:2031` appears in the claude binary. 0.32.2 does not know
        the mode, so it complains. 0.48.2 does.
    not fullscreen
        the pin never carried --start-as=fullscreen. SUPERSEDED 2026-08-04, see below.
    config partially ignored
        directives added after 0.32.2 are silently dropped by the older parser.

  FULLSCREEN REMOVED 2026-08-04. The 2026-08-01 pass read "not fullscreen" as a defect
  and propagated --start-as=fullscreen from the desktop shortcut onto the pin. That flag
  is why the startup window cannot be moved to a second monitor: kitty asks Wayland for
  fullscreen, weston-RDP hands the window to whichever output it picked, and from the
  Windows side there is no titlebar to drag and Win+Shift+arrow will not touch an
  app-owned fullscreen state. Measured on this machine: /mnt/wslg/weston.log reports
  MonitorCount 2 (primary 1920x1080 at 125%, second at x:-1920 100%), and all three
  shortcuts carried the flag. Default is now a plain window, which lands at the
  initial_window_width/height already set in ~/.config/kitty/kitty.conf (1400x900);
  ctrl+shift+f11 fullscreens it once it is on the wanted screen. Pass -Fullscreen to
  restore the old argument form.

  Wayland clients cannot position their own windows, so there is no argument that starts
  kitty on monitor 2. Placing it there needs a Windows-side SetWindowPos on the RAIL
  window after launch, which this script does not do. tools/wsl/move-window-to-monitor.ps1
  does it, and its header carries the RAIL_WINDOW style measurements.

  GPU, added and then REVERSED on 2026-08-04, both within the hour, after the WSL update
  to 2.7.11.0 / WSLg 1.0.73.2. Recording both halves because the reversal is the finding.

  What is true: WSLg renders on the CPU by default, and the GPU is reachable. Measured by
  tools/wsl/gpu-probe.sh, which reads GL_RENDERER from a surfaceless EGL context with a
  forced-software control beside it:

      default                    llvmpipe (LLVM 20.1.2, 256 bits)
      GALLIUM_DRIVER=d3d12       D3D12 (Intel(R) Iris(R) Plus Graphics)
      LIBGL_ALWAYS_SOFTWARE=1    llvmpipe (LLVM 20.1.2, 256 bits)      <- control

  The default being byte-identical to the forced-software control is what makes "on the
  CPU" a measurement. Cause: mesa picks its driver from a DRM render node, WSL has none,
  and the fallback is llvmpipe rather than the d3d12 driver sitting right there.

  What was WRONG was concluding the CPU path is the defect. The launcher briefly carried
  /usr/bin/env GALLIUM_DRIVER=d3d12. Then glxgears was run on both:

      llvmpipe              206 and 269 FPS
      GALLIUM_DRIVER=d3d12   10 and  29 FPS   (vblank_mode=0, so not a 60 cap)

  Ten times slower on the hardware path, because WSLg carries every finished frame over
  an RDP transport and a GPU-resident buffer costs a readback a system-memory one does
  not. So the default is now left alone and -Fullscreen's neighbour switch is inverted:
  the flag is OFF and -Gpu turns it on for anyone who measures otherwise.

  Still open, and named rather than guessed: glxgears is GLX over XWayland, whose glamor
  is on its own software fallback here, so it is the worst path and settles nothing about
  a native-Wayland client like kitty. glmark2-wayland would settle it.

  GL_VERSION is useless as evidence throughout and points the wrong way: llvmpipe
  advertises 4.5 and d3d12 caps at 4.1, so the software path reports the higher number.

  TWO WINDOWS. wsl.exe is a console application, so launching it from a shortcut makes
  Windows allocate a console host before kitty's WSLg window ever appears. Confirmed with
  tasklist: wsl.exe and conhost.exe both present on Console session 1 alongside the kitty
  window. C:\Program Files\WSL\wslg.exe is the same launcher without the console, and it
  takes the identical argument form; verified by running

      wslg.exe -d Ubuntu -- /bin/bash -c 'echo ok > /tmp/wslgtest'

  which wrote the file and opened no window. Side effect worth knowing: kitty's stderr
  had been landing in that console, so the PARSE ERROR lines the operator has been
  pasting stop being visible. That is disappearance, not repair, for anything 0.48.2
  still complains about.

  SCRIPT PATH. Both shortcuts ran the launcher out of /mnt/c/Users/shova/claude-setup,
  a third clone sitting at commit 24e01de while both ext4 clones are at 749ec19, and its
  start-claude.sh differs by content hash. So the click path was running an older chooser
  across the 9P boundary. Repointed at the ext4 clone.

  Two properties survive a WScript.Shell rewrite only if carried by hand, same as in
  repoint_taskbar_pin.ps1: the custom icon, and the run-as-administrator bit in
  ShellLinkHeader byte 21 flag 0x20, which Save() clears.

  The pin FILENAME is never changed. The taskbar label comes from the file name and
  renaming a pinned .lnk orphans the pin.

    powershell -ExecutionPolicy Bypass -File fix-kitty-launchers.ps1           # plan
    powershell -ExecutionPolicy Bypass -File fix-kitty-launchers.ps1 -Apply
    powershell -ExecutionPolicy Bypass -File fix-kitty-launchers.ps1 -Apply -Fullscreen
    powershell -ExecutionPolicy Bypass -File fix-kitty-launchers.ps1 -Apply -Gpu
    powershell -ExecutionPolicy Bypass -File fix-kitty-launchers.ps1 -Revert
#>

[CmdletBinding()]
param(
    [switch] $Apply,
    [switch] $Revert,
    [switch] $Fullscreen,
    [switch] $Gpu
)

$ErrorActionPreference = 'Stop'

$Wslg   = 'C:\Program Files\WSL\wslg.exe'
$Kitty  = '/home/shov/.local/kitty.app/bin/kitty'
$Script = '/home/shov/work/repos/claude-setup/tools/workspace/start-claude.sh'
$Title  = 'Claude - choose workspace'

# A fullscreen WSLg window cannot be dragged or Win+Shift+arrow'd to another monitor,
# so the default is a plain window and ctrl+shift+f11 does the fullscreening by hand.
$StartAs = if ($Fullscreen) { ' --start-as=fullscreen' } else { '' }

# OFF by default: the GPU is reachable and measured SLOWER through WSLg's frame
# transport than llvmpipe. See the GPU block above for the numbers. -Gpu forces it on.
# /usr/bin/env rather than a wrapper script, because wslg.exe execs this argv directly
# and kitty's own environment is what decides the GL driver.
$Env_ = ''
if ($Gpu) { $Env_ = '/usr/bin/env GALLIUM_DRIVER=d3d12 ' }

$Args_ = '-d Ubuntu -- {0}{1}{2} --title "{3}" bash -lc "bash {4}"' -f `
    $Env_, $Kitty, $StartAs, $Title, $Script

$Cwd  = [Environment]::GetFolderPath('UserProfile')
$Desc = 'Pick a lane, an existing repo, or scaffold a new one. Lane is declared, not inferred. kitty 0.48.2 under WSLg, no console window.'

# Parenthesised individually on purpose: without them the comma binds to Join-Path's
# own -ChildPath and the array never forms.
#
# The pin is DISCOVERED rather than named, corrected 2026-08-04. The earlier version
# hardcoded "Claude - choose workspace.lnk" in the TaskBar folder. On 2026-08-04 that
# exact file was deleted by Explorer moments after a WScript.Shell rewrite, and the live
# pin turned out to be "Claude - choose workspace (2).lnk", created the same morning. A
# hardcoded name silently patched nothing while reporting success on the desktop copy,
# which is the same class of failure the 2026-08-01 pass hit from the other direction.
$TaskBar = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
$Pins = @()
if (Test-Path $TaskBar) {
    $Pins = @(Get-ChildItem -Path $TaskBar -Filter 'Claude - choose workspace*.lnk' -File |
        Where-Object { $_.Name -notlike '*.bak*' } |
        ForEach-Object { $_.FullName })
}
$Targets = @((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Claude - choose workspace.lnk')) + $Pins

# WScript.Shell cannot read or write the elevation bit, so it is read before Save()
# and stamped back after.
function Get-RunAsAdmin { param([string] $Path)
    return [bool]([IO.File]::ReadAllBytes($Path)[21] -band 0x20)
}
function Set-RunAsAdmin { param([string] $Path)
    $b = [IO.File]::ReadAllBytes($Path)
    $b[21] = $b[21] -bor 0x20
    [IO.File]::WriteAllBytes($Path, $b)
}

$sh = New-Object -ComObject WScript.Shell

if ($Revert) {
    foreach ($t in $Targets) {
        $bak = "$t.bak-kitty"
        if (Test-Path $bak) {
            Copy-Item $bak $t -Force
            Write-Host ("  restored {0}" -f $t) -ForegroundColor Green
        } else {
            Write-Host ("  no backup for {0}" -f $t) -ForegroundColor DarkYellow
        }
    }
    exit 0
}

if (-not (Test-Path $Wslg)) {
    Write-Host "  wslg.exe not found at $Wslg; nothing written." -ForegroundColor Red
    exit 1
}

Write-Host ("`n== {0} ==" -f $(if ($Apply) { 'APPLY' } else { 'DRY RUN' })) -ForegroundColor Cyan
Write-Host ("  target  {0}" -f $Wslg)
Write-Host ("  args    {0}" -f $Args_)

$failed = 0
foreach ($t in $Targets) {
    Write-Host ''
    if (-not (Test-Path $t)) {
        Write-Host ("  MISSING {0}" -f $t) -ForegroundColor Red
        $failed++
        continue
    }
    $cur = $sh.CreateShortcut($t)
    Write-Host ("  file   {0}" -f $t)
    Write-Host ("  now    {0} {1}" -f $cur.TargetPath, $cur.Arguments) -ForegroundColor DarkYellow

    if (-not $Apply) { continue }

    $wasAdmin = Get-RunAsAdmin $t
    $icon     = $cur.IconLocation
    Copy-Item $t "$t.bak-kitty" -Force

    $l = $sh.CreateShortcut($t)
    $l.TargetPath       = $Wslg
    $l.Arguments        = $Args_
    $l.WorkingDirectory = $Cwd
    $l.Description      = $Desc
    if ($icon) { $l.IconLocation = $icon }
    $l.Save()
    if ($wasAdmin) { Set-RunAsAdmin $t }

    $after = $sh.CreateShortcut($t)
    $ok = ($after.TargetPath -eq $Wslg) -and
          ($after.Arguments -eq $Args_) -and
          ((Get-RunAsAdmin $t) -eq $wasAdmin)
    if ($ok) {
        Write-Host ("  after  {0} {1}" -f $after.TargetPath, $after.Arguments) -ForegroundColor Green
        Write-Host ("  backup {0}.bak-kitty" -f $t) -ForegroundColor DarkGray
    } else {
        Write-Host '  VERIFICATION FAILED; re-run with -Revert' -ForegroundColor Red
        $failed++
    }
}

if (-not $Apply) {
    Write-Host "`n  PLAN ONLY. Re-run with -Apply." -ForegroundColor DarkGray
    exit 0
}
exit $(if ($failed) { 1 } else { 0 })
