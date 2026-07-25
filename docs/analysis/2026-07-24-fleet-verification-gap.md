## PRD: n/a (point-in-time scan per docs-control-plane.md)
## Ticket: n/a
## Status: active

# Why the reference Opus 5 run shipped a game and this setup ships documents

Comparison point: one user, one Claude Code Opus 5 session, 13 named parallel
teammates (`@rounddata @powerups @weapondata …`), a finished single-file HTML
game, verified by driving headless Chrome over CDP with 60+ scripted checks,
honest residual-bug report. Question: is this setup's gap the model, the
fleet, the verification loop, or something else. Evidence below, ranked by
what's broken first per the calibrated-claims register.

Investigating box: this Windows 11 machine, Claude Code 2.1.219, binary at
`C:\Users\shova\.local\bin\claude.exe`. All findings below are from that exact
install and this exact `~/.claude` config, not from documentation alone.

---

## Top-line: three things are broken, not one

1. **The in-session named-teammate feature ("Agent Teams") is real, present in
   this exact binary, and OFF.** It needs an env var or CLI flag that is set
   nowhere in this config. — VERIFIED
2. **23 well-formed named persona subagent files exist but were never deployed
   to where Claude Code actually reads them.** The routing docs (registry,
   `mayor-opus.md`) reference a skill (`agent-team`) that does not exist on
   disk anywhere. — VERIFIED
3. **The CDP verification loop is not stale, it's dead in two different ways
   in two different files**, both pointing at infrastructure (WSL paths, a
   different machine's username, ports nothing is listening on) that has
   nothing to do with this box, while a real, live, driveable Chrome instance
   sits on a port neither file mentions. — VERIFIED

None of these three is "the model." Opus 5 is available here
(`~/.claude/settings.json` doesn't even pin a model away from the account
default, and `model-selection.md` already recommends Opus 5 for leads). The
gap is entirely in wiring, not capability.

---

## A. The named parallel teammate fleet

### A1. A real feature exists, and it is exactly what the screenshot shows — VERIFIED

Extracting readable ASCII strings from the installed binary
(`C:\Users\shova\.local\bin\claude.exe`, v2.1.219) turns up **592 distinct
occurrences** of `teammate`/`Teammate`, including:

```
CLAUDE_CODE_TEAMMATE_COMMAND
- To stop an agent-team teammate, pass its agent ID ("name@team") or bare teammate name as task_id
# Agent Teammate Communication
IMPORTANT: You are running as an agent in a team. To communicate with anyone on your team,
  use the SendMessage tool with `to: "<name>"` to send messages to specific teammates.
How spawned teammates execute (tmux, iterm2, in-process, auto)
waitForTeammatesToBecomeIdle
idle-teammate-summary
TeammateIdle
[TeammateTool] Removed worktree via git: ...
[TeammateTool] git worktree remove failed, falling back to rm: ...
```

This is a one-to-one match for the reference screenshot: named agents
(`name@team` addressing), a `SendMessage` tool for cross-agent chat, per-agent
git worktrees, and idle/finished reporting. This is not speculative — it's
literal strings pulled from the shipped binary this session is running.

### A2. It's gated behind a flag that is set nowhere in this config — VERIFIED

The gate function, decompiled from the minified bundle:

```js
function BRy(){return process.argv.includes("--agent-teams")}
function mc(){ // isAgentSwarmsEnabled
  if(!Z.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS && !BRy())return!1;
  if(!Ke("tengu_amber_flint",!0))return!1;
  return!0
}
```

So the feature requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (env var) OR
`--agent-teams` on the launch command line, AND a remote/local feature gate
named `tengu_amber_flint`.

Checked every place this env var could be set:

```
$ env | grep -i AGENT_TEAM        # (session env dump, no match, exit 1)
$ grep -rl CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS ~/.claude   # only cache/changelog.md and this
                                                              # session's own transcript files —
                                                              # never a SET value
$ grep -rl CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS ~/claude-setup
  → master-plans/claude-code-experimental-features.md   (a note ABOUT the flag)
  → research-papers/home-md/claude-code-experimental-features.md   (same note, copied)
  → work-docs/root-cleanup-2026-05-28/claude-code-experimental-features.md   (same note, copied)
```

All three "hits" outside this session's own transcript are the SAME research
memo (copy-pasted three times into three different archive locations),
describing the flag as **"experimental... may behave differently than
documented"** and explicitly recommending to defer it:

> Worth deferring: Agent teams / forked subagents — experimental, behavior may
> change.

`~/.claude/settings.json`'s `env` block sets `API_TIMEOUT_MS`,
`CLAUDE_CODE_DISABLE_1M_CONTEXT`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`,
`CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING`, and `CLAUDE_CODE_SUBAGENT_MODEL` —
not `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Nobody ever turned this on. The
reference user almost certainly launched with `--agent-teams` or the env var
set; this account has never tried.

### A3. Windows is not the blocker — the default mode is process-local, not terminal-multiplexer-based — VERIFIED

```js
var prn="in-process", Ydt=null, drn=null;
DEFAULT_TEAMMATE_MODE: () => prn   // = "in-process"
```

`teammateMode` supports `tmux`, `iterm2`, `in-process`, `auto`, and the
**default is `in-process`**, not `tmux` or `iterm2` (those are opt-in,
platform-specific visual backends for people who want each teammate in its
own terminal pane — tmux needs Unix, iterm2 needs macOS, neither exists
natively here). `in-process` has no such requirement. So the earlier
hypothesis that Windows structurally can't run this is not supported by what
the binary actually does by default — the blocker is purely the unset flag in
A2, not the OS.

### A4. "hasUsedAgentsFleet" is a different feature — a correction, not a confirmation

`~/.claude.json` does contain `"hasUsedAgentsFleet": true` and
`"showSpinnerTree": false` (verified — these are the only 2 of 62 top-level
keys matching `/fleet|spinner|agent|subagent|team/i`, checked
programmatically). But tracing the actual code path for `isAgentsFleetEnabled`
shows this is a **separate feature from Agent Teams**:

```js
function jM(){return!Xer()}   // isAgentsFleetEnabled
```

wired into CLI subcommands for **background/routine processes**
(`--bg`, `--routine`, `logs|attach|stop|kill|respawn|rm`) and a
"FleetView"/`showSpinnerTree` monitor UI for those detached processes — this
is the machinery behind `/schedule` and the cron-style "Gastown Local
Orchestrator" jobs already in use (per memory: 8 durable cron jobs). It is
**not** the in-session named-teammate swarm from the screenshot. Treating
`hasUsedAgentsFleet: true` as evidence the screenshot's mechanism has been
used before would be wrong — it's evidence a *different*, already-adopted
capability (background job monitoring) has been used, while the actual
in-session teammate swarm (A1–A3) has never been turned on.

### A5. The routing layer names a fleet-invocation skill that does not exist anywhere on disk — VERIFIED

`gastown-company-registry.md` and `~/claude-setup/dot-claude/agents/mayor-opus.md`
both list `agent-team` as a skill owned by Mayor Opus:

```
Owned skills: `agent-team`, `brainstorming`, `codex-call`, `context-i-forgot`, ...
```

Checked every skill location reachable by this session:
- `~/.claude/skills/` — 30 entries, no `agent-team`.
- `new-recruit/.claude/skills/` — 20 entries, no `agent-team`.
- This session's own available-skills list (system reminder) — no `agent-team`.
- `~/.claude/commands/` and `new-recruit/.claude/commands/` — no `agent-team.md`.

Per `hive-mind-workflows.md`'s own rule ("If an installed skill has no clear
trigger, route, or use case, mark it as unwired skill"), `agent-team` is
exactly that: a name in three routing documents pointing at nothing. Even if
someone flipped the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag on, there is
no skill file that would teach Claude *how* to invoke it in this account's
workflow.

### A6. 23 well-formed named persona files exist, but were never deployed to where the binary reads them — VERIFIED

```
$ ls ~/.claude/agents
ls: cannot access '/c/Users/shova/.claude/agents': No such file or directory

$ ls ~/claude-setup/dot-claude/agents | wc -l
23
```

Every file has a proper Claude Code subagent frontmatter (spot-checked 3 of
23):

```yaml
---
name: mayor-opus
description: Lead orchestrator for Gastown. ...
tools: Read, Grep, Glob, Task
model: opus
---
```

```yaml
---
name: engineering-firm
description: General coding and implementation company. ...
tools: Read, Grep, Glob, Bash, Edit, Write
model: sonnet
---
```

These are exactly the shape Claude Code needs for GA (non-experimental) named
subagents invoked by the Task tool. They exist only in the git-tracked mirror
(`claude-setup/dot-claude/agents/`), never copied to the live
`~/.claude/agents/` the binary actually reads. `sync-setup.sh` (the only sync
script found, in `new-recruit/.claude/bin/`) explicitly syncs **`~/.claude`
↔ `~/.codex` on the same machine** (skills/hooks/rules union) — it does not
push the git repo `claude-setup` to live `~/.claude` at all. Nothing deploys
these 23 files.

The proof this actually bites: this very session's own spawned subagent record
(`~/.claude/projects/.../subagents/agent-aa3e661662585adab.meta.json`) shows:

```json
{"agentType":"Explore","description":"Excavate claude-setup bundles", ...}
```

`"Explore"` is a generic built-in subagent type — not `mayor-opus`, not
`engineering-firm`, not any Gastown persona. Even ordinary (non-experimental)
named-subagent invocation isn't happening in practice, because the persona
files never reached the directory Claude Code reads.

### A7. CLAUDE_CODE_SUBAGENT_MODEL is real but is not the blocker it looks like — correction

`CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` is set globally (confirmed in
both the session env dump and `~/.claude/settings.json`'s `env` block). This
is a deliberate, documented cost-control policy (`model-selection.md`), not an
accident. It affects which model backs a subagent when no more specific model
is chosen — it does not gate whether Agent Teams / Fleet activates at all
(A2/A4 are the actual gates). Whether it would override an explicit
`model: opus` in a deployed persona file's frontmatter was not verified here
(ASSUMED unclear) — that's a real but secondary question, moot until A2 and
A6 are fixed and there's anything running to observe.

---

## B. Closed-loop artifact verification (CDP)

### B1. Chrome IS live and reachable, right now, on a port neither cdp doc mentions — VERIFIED

```
$ curl -s http://127.0.0.1:9224/json/version
{
   "Browser": "Chrome/150.0.7871.129",
   "Protocol-Version": "1.3",
   ...
   "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/browser/6a4a2875-6fc8-49e4-b92f-65e1c027421e"
}

$ curl -s http://127.0.0.1:9222/json/version   → connection refused (exit 7)
$ curl -s http://127.0.0.1:9223/json/version   → connection refused (exit 7)
```

### B1a. Addendum, same-day re-check: B1's "live" port is not stable — it is actively racing across concurrent sessions right now — VERIFIED

Re-run minutes after B1, in a separate subagent pass over the same box:

```
$ curl -s --max-time 3 http://127.0.0.1:9224/json/version   → connection refused (exit 7), x5 consecutive attempts
$ netstat -an | grep 9224
  TCP    [::1]:9224             [::]:0                 LISTENING
```

Only the IPv6 loopback (`[::1]:9224`) is bound; IPv4 `127.0.0.1:9224` — what
both `cdp.md` files, `cdp_driver.py` (below), and the earlier B1 curl all
target — is refused. Immediately before this, `wmic`/`Get-CimInstance` showed
**12 separate `chrome.exe` processes with `--remote-debugging-port=9224` in
their command line**, spread across at least 5 distinct `--user-data-dir`
values (`cdp-prof-v2tree`, `cdp-prof-eng1`, `cdp-prof-ach1`, `cdp-prof-r1`,
and `.claude/automation-chrome-profile`) — each one a different parallel
Claude Code session's own automation Chrome, all hardcoded to the identical
port. Only one process can actually own the OS-level bind at a time; the rest
either fail silently or the bind flips between IPv4/IPv6 as sessions start and
exit. `CLAUDE.md` itself documents "6+ parallel Claude sessions are normal"
for this operator — that habit is what's colliding on this port, live, right
now, independent of any file being stale.

This changes B5's confidence, not its diagnosis: even after every `cdp.md`
fix below, a hardcoded shared port (9224, or any other single
fixed number) will keep intermittently breaking under this operator's own
normal multi-session load unless the launcher allocates a **per-session**
port (e.g. derive it from `$CLAUDE_CODE_SESSION_ID`, or scan for a free port)
instead of reusing one fixed number across every concurrent session.

### B1b. A working native driver already exists in this exact project, unwired and currently broken by B1a — VERIFIED

`new-recruit/cdp_driver.py` (80 lines, read in full) is a real, already-written
CDP client for port 9224: `uv run --with websocket-client python cdp_driver.py
{url|nav|shot|text|eval|tabs|rect|click}`, pure Python + `websocket-client`,
no Node, no MCP server, no WSL. This is not a proposal — it exists on disk
today and is exactly the shape B5(b) below asks for. It is not referenced by
either `cdp.md`, not in any skill or command, and not mentioned elsewhere in
this analysis before this addendum. Running it live:

```
$ uv run --with websocket-client python cdp_driver.py tabs
urllib.error.URLError: <urlopen error [WinError 10061] ... actively refused it>
```

It fails right now, for the exact reason in B1a (IPv4 127.0.0.1:9224 refused),
not because the script is broken. So the honest state of "build it, drive it,
prove it" on this box is: the driver script already exists and is the right
shape, and the one thing stopping it from working this second is the shared-port
collision in B1a, not missing code.

### B1c. A "cdp" Skill has real usage history but its source file could not be located in the time available — ASSUMED, flagging not resolving

This session's own available-skills list includes an invocable `cdp` skill
(distinct from the `.claude/commands/cdp.md` documented in B2), and
`~/.claude.json`'s `skillUsage.cdp` shows `usageCount: 1`,
`lastUsedAt: 1784575579040` (2026-07-20, four days before this scan) — real,
recent use. Searched and came up empty: `~/.claude/skills/` (29 entries, no
`cdp` dir), `new-recruit/.claude/skills/` (24 entries, no `cdp` dir), and the
one installed plugin marketplace (`claude-plugins-official`, no `cdp` plugin).
Not concluding it doesn't exist — a session-scoped skill resolver clearly
finds it somewhere the filesystem searches above didn't reach in the time
budget. Recorded as an open item rather than asserted either way.

### B2. Two different `/cdp` command files exist, both stale, in different ways — VERIFIED

There are TWO copies, textually different from each other (diffed):

- `~/.claude/commands/cdp.md`
- `new-recruit/.claude/commands/cdp.md`

Both:
- Default to `~/.codex/bin/obscura-cdp start` on port **9222**.
- Offer an "edge" path on port **9223** via
  `WIN_HOST="$(ip route show default | awk '{print $3}')"` — `ip route` is a
  Linux command; this is a native Windows Claude Code session, there is no
  WSL host gateway to look up.
- Launch Edge with `--user-data-dir=C:\Users\shoval.be\...` — **`shoval.be` is
  a different machine's username** (the work box per CLAUDE.md's own
  reference paths); this machine's user is `shova`.

The project-local copy additionally claims a `playwright` MCP server is
"already in `~/.mcp.json`" and references
`/home/shovalbe/.codex/bin/playwright-mcp-visual` — a Linux home-directory
path that cannot exist on this Windows box under any circumstance.

### B3. The infrastructure both files assume doesn't exist here — VERIFIED

```
$ find ~/.codex/bin
find: 'C:/Users/shova/.codex/bin': No such file or directory
```

`obscura-cdp` exists ONLY inside the git mirror,
`claude-setup/dot-codex/bin/obscura-cdp` — never deployed live. Reading it
confirms it's written for a POSIX/WSL runner (`/tmp/obscura-cdp-${PORT}.log`,
a binary literally named `obscura`), not portable to native Windows Git-Bash
without rewriting.

```
$ cat ~/.mcp.json
cat: 'C:/Users/shova/.mcp.json': No such file or directory
```

`~/.claude.json` top-level `mcpServers` is `{}` (parsed directly). The 3
tracked projects in `~/.claude.json` are `C:/Users/shova`, `oren-roast-hq`,
`daily-deep-learning` — **new-recruit is not among them**, so there is no
project-scoped MCP config either. Zero MCP servers are configured anywhere
reachable by this session. The doc's claim that a playwright MCP server is
"already" wired is false on this machine.

### B4. What IS present — STAGED, not wired

- `node v22.20.0` and `bun v1.3.14` are installed and on PATH (verified).
- Playwright's downloaded browser binaries exist at
  `C:/Users/shova/AppData/Local/ms-playwright` (found, not exercised).
- Multiple OTHER project folders under `new-recruit/projects/`
  (`qc-telephony-api`, `ORM-AGENT/social-media-agent`, `ORM-AGENT/widgora`,
  `campaign-analysis`, `seekapa-training-platform`, `video-understanding`,
  `agent-call-tracker`, `lp-creation/ebook-task`) each contain a
  `.playwright-mcp` output directory — evidence CDP-driven browser automation
  via a Playwright MCP has worked before, scoped to those individual
  project-local configs. Not verified here whether each has its own working
  `.mcp.json` (that would need opening each project) — flagging as STAGED,
  a real capability that exists somewhere in this account's history but isn't
  wired for `new-recruit` root or pointed at the live port 9224.
- **Update (B1b): `new-recruit/cdp_driver.py` already exists and is exactly
  the driver B5(b) below asks for** — no new script needed, only wiring +
  the port fix in B1a.

### B5. What a one-command "build it, drive it, prove it" loop actually needs

1. Fix the port collision first (B1a): allocate a per-session port (derive
   from `$CLAUDE_CODE_SESSION_ID` or scan-for-free) instead of every parallel
   session hardcoding 9224 — otherwise steps 2-3 are built on a resource that
   silently breaks under this operator's own normal 6+-parallel-session load.
2. Rewrite (not patch) both `cdp.md` files: default target is the live local
   Chrome (per-session port from step 1), no WSL/`ip route` logic, no
   `shoval.be`/`shovalbe` paths, no claim of an MCP server that isn't
   configured.
3. Either (a) add one real `mcpServers` entry (project- or account-scoped)
   pointing a `playwright` MCP server at the driver, matching the pattern
   already proven to work in the sibling project folders in B4; or (b) reuse
   `new-recruit/cdp_driver.py` (B1b) as-is — it already implements
   nav/shot/text/eval/click/tabs over raw CDP, no MCP, no Node dependency,
   and just needs its hardcoded `PORT = 9224` default replaced with the
   per-session value from step 1.
4. Wire whichever path is chosen as an actual skill or command that gets
   invoked automatically after a build step — today nothing in
   `new-recruit/.claude/` or the global config calls either cdp.md file or
   `cdp_driver.py` as part of a build-then-verify flow; it's a manually-typed
   `/cdp` that, per B2/B3, currently does nothing useful if typed, or a
   manually-run script that, per B1a/B1b, is currently broken by port
   contention even when someone remembers it exists.

None of this needs new capability from Anthropic — Chrome CDP is already
proven live on this box (B1), the driver code already exists (B1b). The one
piece that isn't just "unwired local config" is B1a: a shared hardcoded port
that genuinely races across this operator's own normal parallel-session
pattern needs a real fix (per-session port), not just a copy-paste.

---

## The real question, answered

The gap is not the model — Opus 5 is already the recommended lead in this
account's own `model-selection.md`, and nothing here required a smarter model
to fix. It is not really "the fleet" or "the verification loop" as isolated
technical absences either, both exist as real, working, documented features
in this exact binary and on this exact machine (Agent Teams is compiled in
and default-mode-compatible with Windows; Chrome speaks CDP live on this box,
though — per the same-day re-check in B1a — not stably on the one hardcoded
port every file assumes, because 12+ concurrent sessions are racing it).
The actual gap is that **the config never turns either one on and never
points them at what's real**: the experimental-teams flag was researched,
written up three times into three archive copies, and explicitly marked
"worth deferring" instead of being flipped; the 23 named persona files that
would make a named fleet mean something were written and committed to a git
mirror that nothing deploys; the routing docs assign a fleet-invocation skill
that was never created; and the CDP command was copied from a different
machine's WSL-era setup twice, pointing at a dead port and a nonexistent
Linux path, while the actually-running Chrome instance on 9224 sits
unreferenced by either copy. That is the pattern this session was asked to
check for directly: budget spent writing governance documents and research
memos *about* autonomy and fleets, and none of it spent on the five-minute
edits — flip one env var, `cp` one directory, fix two port numbers — that
would have made either feature actually fire.
