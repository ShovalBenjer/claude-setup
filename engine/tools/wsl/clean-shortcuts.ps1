# Remove the superseded Claude Desktop shortcuts, keep exactly one generation.
#
# Three generations were live on 2026-07-31:
#
#   gen 1  2026-07-27  wt.exe + pwsh, Windows-side, PRE-ADR-0016 letters (B/C/D)
#   gen 2  2026-07-30  wsl + kitty + tools/workspace/start-claude.sh, letters A/B/C/D
#   gen 3  2026-07-31  wt.exe + bare wsl, written by an agent that did not look for gen 2
#
# gen 2 is the keeper and it is not close: it runs in WSL, it carries the correct lane
# letters, and it routes through start-claude.sh, which offers global / project / new,
# prefers ext4 with a visible fallback, and runs `gate.py init` on a new repo so a fresh
# project starts red rather than unmeasured. gen 3 reimplemented a worse subset of that
# by bypassing the launcher entirely, which is the excavate-before-building failure.
#
# Nothing here is recreated. Every removed shortcut's exact target and arguments are
# recorded in tools/wsl/audit-shortcuts.ps1 output and in the session that made them.
#
#   powershell -ExecutionPolicy Bypass -File tools\wsl\clean-shortcuts.ps1
#   powershell -ExecutionPolicy Bypass -File tools\wsl\clean-shortcuts.ps1 -Execute

param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')

$remove = @(
  @{ F='Claude B - harness.lnk';        Why='gen 1: pwsh on Windows, lane letter B retired by ADR-0016 (now A)' },
  @{ F='Claude C - resume engine.lnk';  Why='gen 1: pwsh on Windows, lane letter C retired by ADR-0016 (now B)' },
  @{ F='Claude D - learning.lnk';       Why='gen 1: pwsh on Windows, lane letter D retired by ADR-0016 (now C)' },
  @{ F='Claude A - harness (WSL).lnk';  Why='gen 3: mine, bypasses start-claude.sh; gen 2 does this better' },
  @{ F='Claude C - learning (WSL).lnk'; Why='gen 3: mine, bypasses start-claude.sh; gen 2 does this better' },
  @{ F='Claude D - content (WSL).lnk';  Why='gen 3: mine, bypasses start-claude.sh; gen 2 does this better' }
)

$keep = @(
  'Claude - choose workspace.lnk',
  'Claude A - harness.lnk',
  'Claude B - resume engine.lnk',
  'Claude C - learning.lnk',
  'Claude D - content.lnk'
)

Write-Host ("`n== {0} ==" -f $(if ($Execute) {'EXECUTE'} else {'DRY RUN'})) -ForegroundColor Green

foreach ($r in $remove) {
  $p = Join-Path $desktop $r.F
  if (-not (Test-Path $p)) { Write-Host ("  absent  " + $r.F) -ForegroundColor DarkGray; continue }
  if ($Execute) {
    Remove-Item $p -Force
    Write-Host ("  REMOVED " + $r.F) -ForegroundColor Yellow
  } else {
    Write-Host ("  remove  " + $r.F) -ForegroundColor DarkYellow
  }
  Write-Host ("            " + $r.Why) -ForegroundColor DarkGray
}

Write-Host "`n== keeping (gen 2) ==" -ForegroundColor Green
foreach ($k in $keep) {
  $p = Join-Path $desktop $k
  if (Test-Path $p) { Write-Host ("  keep    " + $k) }
  else              { Write-Host ("  MISSING " + $k) -ForegroundColor Red }
}

Write-Host "`n== Claude shortcuts on the Desktop now ==" -ForegroundColor Green
Get-ChildItem $desktop -Filter 'Claude *.lnk' | Sort-Object Name |
  ForEach-Object { Write-Host ("  " + $_.Name) }
