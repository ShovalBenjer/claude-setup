<#
.SYNOPSIS
  Pick a workspace, then start Claude in it with the lane declared.

.DESCRIPTION
  Replaces the single hardcoded desktop shortcut, which ran

      wt.exe -d "C:\Users\shova\Downloads\new-recruit" pwsh -NoExit -Command claude

  and therefore pinned every session's working directory to one repo. Because
  docs/charters.md assigns a lane by working directory, that shortcut made every
  session report Lane C no matter what it was doing.

  Two levels, in this order:

    GLOBAL   one of the four charter lanes (B harness, C resume engine,
             D learning, E content; A retired 2026-07-29). Lane is declared,
             cwd follows.
    PROJECT  an existing repo, or a new one scaffolded on the spot.

  Whatever is chosen, CLAUDE_LANE is exported before claude starts, so
  session-recall.sh reads the lane instead of inferring it from a path a
  launcher chose.
#>

[CmdletBinding()]
param(
    # '' is in the set because -File binds every declared parameter, so an unpassed
    # [string] arrives as empty and would otherwise fail ValidateSet before the
    # script body runs. An empty lane means undeclared, which is a real state here.
    [ValidateSet('B', 'C', 'D', 'E', '')] [string] $Lane,
    [string] $Path,
    [switch] $NoLaunch          # print the resolved choice and exit; for testing
)

$ErrorActionPreference = 'Stop'
$Home_ = [Environment]::GetFolderPath('UserProfile')

$Lanes = [ordered]@{
    B = @{ Dir = Join-Path $Home_ 'claude-setup'
           Desc = 'harness: rules, hooks, skills, schedulers, review fabric' }
    C = @{ Dir = Join-Path $Home_ 'Downloads\new-recruit'
           Desc = 'resume engine: hiring machine, arms, applications' }
    D = @{ Dir = Join-Path $Home_ 'Downloads\daily-deep-learning'
           Desc = 'learning: the PWA, learning cards, study loops' }
    E = @{ Dir = Join-Path $Home_ 'Downloads\daily-deep-learning'
           Desc = 'content & publishing: case ledgers, syndication; operator posts' }
}

# Where a project may live. Bounded on purpose: an unbounded scan of the home
# directory takes seconds and surfaces node_modules clones nobody wants.
$ProjectRoots = @(
    (Join-Path $Home_ 'Downloads'),
    (Join-Path $Home_ 'projects'),
    # Added 2026-07-31. Sub-projects live INSIDE new-recruit, in its gitignored
    # projects/ tree, so the depth-0 scan above could never see them. Measured
    # before adding: exactly one git repo is down there today
    # (projects/nexus-engine-rs), so this widens the menu by one entry, not by a
    # flood. Note that the 'projects' root on the line above does not exist on
    # this machine, so the launcher was already scanning one dead path.
    (Join-Path $Home_ 'Downloads\new-recruit\projects'),
    $Home_
)

function Get-Projects {
    $seen = @{}
    foreach ($root in $ProjectRoots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem -Path $root -Directory -Depth 0 -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName '.git') } |
            ForEach-Object {
                if (-not $seen.ContainsKey($_.FullName)) {
                    $seen[$_.FullName] = $true
                    [pscustomobject]@{ Name = $_.Name; Dir = $_.FullName }
                }
            }
    }
}

function Read-Choice {
    param([string] $Prompt, [int] $Max)
    while ($true) {
        Write-Host ''
        $raw = Read-Host $Prompt
        if ($raw -eq 'q') { return $null }
        $n = 0
        if ([int]::TryParse($raw, [ref] $n) -and $n -ge 1 -and $n -le $Max) { return $n }
        Write-Host "  pick 1 to $Max, or q to quit" -ForegroundColor DarkYellow
    }
}

function New-Project {
    Write-Host ''
    $name = Read-Host 'new project name (letters, digits, dash)'
    if ([string]::IsNullOrWhiteSpace($name)) { return $null }
    if ($name -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
        Write-Host '  rejected: use letters, digits, dot, dash, underscore' -ForegroundColor Red
        return $null
    }
    $dir = Join-Path (Join-Path $Home_ 'Downloads') $name
    if (Test-Path $dir) {
        Write-Host "  already exists: $dir" -ForegroundColor Red
        return $null
    }
    New-Item -ItemType Directory -Path $dir | Out-Null
    Push-Location $dir
    try {
        git init -q 2>$null
        # gate.py init writes a starter quality-contract.json that deliberately
        # fails a project with no tests, so a new repo starts red rather than
        # starting unmeasured.
        $gate = Join-Path $Home_ 'claude-setup\tools\gate\gate.py'
        if (Test-Path $gate) { python $gate init --project . 2>$null | Out-Null }
    } finally { Pop-Location }
    Write-Host "  created $dir" -ForegroundColor Green
    return $dir
}

# ---------------------------------------------------------------- resolve
if ($Path) {
    $dir = (Resolve-Path $Path).Path
    $lane = if ($Lane) { $Lane } else { '' }
} elseif ($Lane) {
    $dir = $Lanes[$Lane].Dir
    $lane = $Lane
} else {
    Write-Host ''
    Write-Host '  CLAUDE WORKSPACE' -ForegroundColor Cyan
    Write-Host '  ----------------'
    Write-Host '  1  global   a charter lane'
    Write-Host '  2  project  an existing repo'
    Write-Host '  3  new      scaffold a repo, then open it'
    $top = Read-Choice 'choose' 3
    if ($null -eq $top) { return }

    switch ($top) {
        1 {
            Write-Host ''
            $keys = @($Lanes.Keys)
            for ($i = 0; $i -lt $keys.Count; $i++) {
                $k = $keys[$i]
                '  {0}  lane {1}  {2}' -f ($i + 1), $k, $Lanes[$k].Desc | Write-Host
            }
            $pick = Read-Choice 'lane' $keys.Count
            if ($null -eq $pick) { return }
            $lane = $keys[$pick - 1]
            $dir = $Lanes[$lane].Dir
        }
        2 {
            $projects = @(Get-Projects)
            if (-not $projects) { Write-Host '  no git repos found'; return }
            Write-Host ''
            for ($i = 0; $i -lt $projects.Count; $i++) {
                '  {0,2}  {1,-28} {2}' -f ($i + 1), $projects[$i].Name, $projects[$i].Dir |
                    Write-Host
            }
            $pick = Read-Choice 'project' $projects.Count
            if ($null -eq $pick) { return }
            $dir = $projects[$pick - 1].Dir
            # A known lane directory keeps its lane; anything else is undeclared,
            # and session-recall.sh will say so rather than guess.
            $lane = ''
            foreach ($k in $Lanes.Keys) {
                if ($Lanes[$k].Dir -eq $dir) { $lane = $k; break }
            }
        }
        3 {
            $dir = New-Project
            if (-not $dir) { return }
            $lane = ''
        }
    }
}

if (-not (Test-Path $dir)) {
    Write-Host "  missing directory: $dir" -ForegroundColor Red
    return
}

Write-Host ''
Write-Host ("  cwd  {0}" -f $dir) -ForegroundColor DarkGray
if ($lane) {
    Write-Host ("  lane {0}  {1}" -f $lane, $Lanes[$lane].Desc) -ForegroundColor DarkGray
} else {
    Write-Host '  lane UNDECLARED (session-recall will say so)' -ForegroundColor DarkYellow
}

if ($NoLaunch) { return [pscustomobject]@{ Dir = $dir; Lane = $lane } }

Set-Location $dir
if ($lane) { $env:CLAUDE_LANE = $lane } else { Remove-Item Env:\CLAUDE_LANE -ErrorAction SilentlyContinue }
claude
