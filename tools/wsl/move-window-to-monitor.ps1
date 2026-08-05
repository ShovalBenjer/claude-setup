<#
.SYNOPSIS
  Move a WSLg window to a named monitor, because Windows' own keyboard and mouse
  paths cannot.

.DESCRIPTION
  Measured 2026-08-04 on this machine. A WSLg window reaches Windows as class
  RAIL_WINDOW, and every one of them has WS_CAPTION and WS_SYSMENU CLEAR:

      BBB-X11-TEST     CAPTION=False SYSMENU=False THICKFRAME=True style=0x96070000
      AAA-WAYLAND-TEST CAPTION=False SYSMENU=False THICKFRAME=True style=0x96070000

  That single fact explains all three failures the operator reported. No caption
  means no titlebar to mouse-drag. Aero Snap (Win+Arrow, Win+Shift+Arrow) acts on
  the caption, so it does nothing. No sysmenu means Alt+Space has no Move item
  either. THICKFRAME is set, so the window can still be resized by its border,
  which is why the window feels half-alive rather than frozen.

  The two styles above are a controlled A/B: same kitty, same config, one launched
  with linux_display_server=wayland and one with x11, launched one second apart.
  The style words are identical, so the display server is NOT the lever and the
  kitty.conf deviation that chose wayland stands. An earlier reading that showed
  0x97070000 differed only by WS_MAXIMIZE, which is window state, not capability.

  SetWindowPos does not care about the caption, so it works where the shell does
  not. Verified:

      MOVE hwnd=1246294 call=True before=167,68 1120x720 -> after=-1520,284 1120x720

  On this machine monitor 2 is the LEFT one. System.Windows.Forms reports
  DISPLAY1 primary at {0,0 1536x864} (1920x1080 at 125% scaling, reported in
  logical units) and DISPLAY2 at {-1920,128 1920x1080}. Negative X is left of
  primary, which is also why Win+Shift+Right could never have worked: there is no
  monitor to the right of the primary.

  A maximized window is restored first, because SetWindowPos on a maximized window
  moves the restore rectangle and leaves the window where it was.

    powershell -ExecutionPolicy Bypass -File move-window-to-monitor.ps1 -List
    powershell -ExecutionPolicy Bypass -File move-window-to-monitor.ps1 -Title "Claude - choose workspace" -Monitor 2
#>

[CmdletBinding()]
param(
    [string] $Title = 'Claude - choose workspace',
    [int]    $Monitor = 2,
    [switch] $List,
    [switch] $Maximize
)

$ErrorActionPreference = 'Stop'

$sig = @"
using System; using System.Text; using System.Runtime.InteropServices;
public class MoveWin {
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
 public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern IntPtr GetWindowLongPtr(IntPtr h, int i);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@
Add-Type -TypeDefinition $sig -Language CSharp
Add-Type -AssemblyName System.Windows.Forms

$screens = [System.Windows.Forms.Screen]::AllScreens

Write-Host 'MONITORS' -ForegroundColor Cyan
for ($i = 0; $i -lt $screens.Count; $i++) {
    $s = $screens[$i]
    Write-Host ('  [{0}] {1} primary={2} bounds={3} work={4}' -f ($i + 1), $s.DeviceName, $s.Primary, $s.Bounds, $s.WorkingArea)
}

# Window enumeration runs even for -List, so the operator can see what titles exist
# before choosing one. Matching is a substring so the WSLg " (Ubuntu)" suffix, which
# the RDP client appends and no launcher controls, does not have to be typed.
$hits = @()
$cb = [MoveWin+EnumWindowsProc]{
    param($h, $l)
    if ([MoveWin]::IsWindowVisible($h)) {
        $n = [MoveWin]::GetWindowTextLength($h)
        if ($n -gt 0) {
            $sb = New-Object Text.StringBuilder ($n + 1)
            [void][MoveWin]::GetWindowText($h, $sb, $n + 1)
            $cn = New-Object Text.StringBuilder 256
            [void][MoveWin]::GetClassName($h, $cn, 256)
            # kitty draws client-side decorations, and weston exports every one of
            # them as its own RAIL_WINDOW titled "sub-surface". One kitty window
            # produced nine of them here: four 10x10 corners, four edges, and the
            # tab bar. They follow the parent when it is moved, so they are noise
            # in the listing and must never be matched as a move target.
            if ($cn.ToString() -eq 'RAIL_WINDOW' -and $sb.ToString() -notlike 'sub-surface*') {
                $script:hits += [pscustomobject]@{ H = $h; T = $sb.ToString() }
            }
        }
    }
    return $true
}
[void][MoveWin]::EnumWindows($cb, [IntPtr]::Zero)

if ($List) {
    Write-Host 'WSLg WINDOWS (class RAIL_WINDOW)' -ForegroundColor Cyan
    if ($hits.Count -eq 0) { Write-Host '  none' -ForegroundColor DarkYellow }
    foreach ($w in $hits) {
        $r = New-Object MoveWin+RECT; [void][MoveWin]::GetWindowRect($w.H, [ref]$r)
        Write-Host ('  hwnd={0} "{1}" at {2},{3} {4}x{5}' -f $w.H, $w.T, $r.L, $r.T, ($r.R - $r.L), ($r.B - $r.T))
    }
    return
}

if ($Monitor -lt 1 -or $Monitor -gt $screens.Count) {
    Write-Host ('No monitor {0}. This machine has {1}.' -f $Monitor, $screens.Count) -ForegroundColor Red
    exit 1
}
$wa = $screens[$Monitor - 1].WorkingArea

$targets = $hits | Where-Object { $_.T -like "*$Title*" }
if ($targets.Count -eq 0) {
    Write-Host ('No WSLg window whose title contains "{0}". Re-run with -List.' -f $Title) -ForegroundColor Red
    exit 2
}

foreach ($t in $targets) {
    $h = $t.H
    $before = New-Object MoveWin+RECT; [void][MoveWin]::GetWindowRect($h, [ref]$before)

    $style = [int64][MoveWin]::GetWindowLongPtr($h, -16)
    if (($style -band 0x1000000) -ne 0) { [void][MoveWin]::ShowWindow($h, 9) }   # SW_RESTORE

    if ($Maximize) {
        $x = $wa.X; $y = $wa.Y; $w = $wa.Width; $ht = $wa.Height
    }
    else {
        $w  = [Math]::Min($before.R - $before.L, $wa.Width)
        $ht = [Math]::Min($before.B - $before.T, $wa.Height)
        $x  = $wa.X + [int](($wa.Width  - $w)  / 2)
        $y  = $wa.Y + [int](($wa.Height - $ht) / 2)
    }

    # SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW. Not activating keeps focus
    # where the operator left it, which matters when this is called from a hook.
    $ok = [MoveWin]::SetWindowPos($h, [IntPtr]::Zero, $x, $y, $w, $ht, 0x4014)

    $after = New-Object MoveWin+RECT; [void][MoveWin]::GetWindowRect($h, [ref]$after)
    $landed = ($after.L -ge $wa.X) -and ($after.L -lt ($wa.X + $wa.Width))
    $colour = if ($ok -and $landed) { 'Green' } else { 'Red' }
    Write-Host ('  hwnd={0} "{1}"' -f $h, $t.T)
    Write-Host ('    {0},{1} {2}x{3}  ->  {4},{5} {6}x{7}   call={8} onMonitor{9}={10}' -f `
            $before.L, $before.T, ($before.R - $before.L), ($before.B - $before.T), `
            $after.L, $after.T, ($after.R - $after.L), ($after.B - $after.T), `
            $ok, $Monitor, $landed) -ForegroundColor $colour
}
