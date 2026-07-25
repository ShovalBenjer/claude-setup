# Other resources that can close the named weak points — 2026-07-25

Point-in-time inventory scan (docs-control-plane taxonomy: `docs/analysis/`, not root).
Answers: "same for other resources you think can upgrade our weak points."

## Risk and unknowns first (calibrated-claims order)

- **`claude-nightly.yml` (the AUTO-18 always-on cron) has ZERO runs.** Created
  2026-07-24T19:58:15Z, cron is `17 1 * * *` UTC — its first fire has not happened
  yet as of this scan. STAGED, not VERIFIED. Do not report AUTO-18 as solved until
  a run completes and a PR/no-op is confirmed.
- **`claude-code-review.yml` is currently BROKEN.** Both of its last 2 runs
  (2026-07-23T02:28, 2026-07-23T11:44) failed with `error_max_turns` — the review
  hit the 10-turn cap before finishing and the job exited 1. This is already-deployed
  infra silently not working, the exact failure class calibrated-claims flags as
  worst (false-negative "the review ran"). Fix this BEFORE adding a second reviewer
  (AUTO-10, below), or the second reviewer inherits the same failure mode.
- **AUTO-05 (phone concierge) is not a tooling gap, it's a decision gap.** The
  transport (Cloudflare Tunnel) is already sitting on disk. What's missing is a
  telephony/SMS *provider* (Twilio or equivalent) that Shoval has not chosen or
  signed up for. Building a receiver before that decision repeats the exact
  unused-infrastructure pattern (23 persona files, 35 dead skill stubs) — flagged
  as NOT worth building yet.
- **Azure/Foundry is not usable from this machine and may not be the right owner.**
  `az` is not installed at all (verified, both bash and PowerShell say "command not
  found"). Foundry (`brn-azai`/`seekapa_ai`) is employer (i-sdd) infrastructure per
  CLAUDE.md's own project context — routing personal job-search/autonomy automation
  through an employer Azure tenant is a boundary question, not a free resource.
  Recommend: skip, unless Shoval explicitly authorizes using employer Azure for
  personal automation.
- **GitHub Actions minutes could not be verified via billing API** (`gh api
  users/.../settings/billing/actions` returned 404 / needs `user` scope not
  currently granted, request not made since scope changes need explicit sign-off).
  The 2,000 min/month private-repo free tier is ASSUMED from GitHub's published
  pricing, not confirmed against this account.

## Inventory — what he actually owns (verified this session)

| Resource | State | Evidence |
|---|---|---|
| GitHub (`gh`) | VERIFIED logged in, `ShovalBenjer`, scopes `gist,read:org,repo,workflow` | `gh auth status` |
| GitHub API quota | VERIFIED 4998/5000 core remaining | `gh api rate_limit` |
| `claude-setup` repo secrets | VERIFIED: `CLAUDE_CODE_OAUTH_TOKEN` (2026-07-23), `GEMINI_API_KEY` (2026-07-24T20:17:02Z) | `gh secret list` |
| `claude-setup` repo visibility | VERIFIED private | `gh repo view --json isPrivate` |
| Existing GH Actions workflows | VERIFIED 3: `claude-code-review.yml` (active, 2/2 recent runs FAILED), `claude-nightly.yml` (active, AUTO-07/AUTO-18, 0 runs yet), Dependency Graph | `gh api repos/.../actions/workflows` + `gh run list` |
| Azure CLI | VERIFIED absent (`az: command not found` in bash and PowerShell) | direct invocation, both shells |
| Ollama | VERIFIED installed, v0.13.0, models `qwen2.5:1.5b` (986MB) and `qwen2.5:7b` (4.7GB) already pulled | `ollama list` |
| Local model capability ceiling | VERIFIED (prior scan, `2026-07-23-local-model-stress-test.md`): no discrete GPU, Intel Iris Plus integrated; 1.5B does 13.8 tok/s usable, 7B does 3.5 tok/s and thrashes RAM. Confirmed again this session: GPU is Intel Iris Plus only, no `nvidia-smi`. | `wmic path win32_VideoController get name`, cited prior stress test |
| Local classifier tool | VERIFIED built (`tools/local/route_classify.py`, has a compiled `.pyc` so it has run), used by `tools/local/reflex_router.py` — but VERIFIED **not wired** into any hook or `settings.json` | `grep -rl route_classify .claude/hooks .claude/settings.json` returned nothing |
| Docker | VERIFIED installed (28.1.1) but daemon not running (Docker Desktop not started) | `docker ps` → pipe connection error |
| `cloudflared.exe` | VERIFIED present at `~/bin/cloudflared.exe` (already used for `daily-deep-learning.pages.dev` per memory) | `ls ~/bin` |
| `gws` CLI (Google Workspace) | VERIFIED installed and already authenticated: `token_cache.json`, `credentials.enc`, `client_secret.json` present at `~/.config/gws` | `ls -la ~/.config/gws` |
| Python / sqlite3 | VERIFIED Python 3.11.9, sqlite3 module v3.45.1 built in, zero new dependency | `python -c "import sqlite3; print(sqlite3.sqlite_version)"` |
| `uv` | VERIFIED 0.9.4 | `uv --version` |
| Node / Bun | VERIFIED v22.20.0 / 1.3.14 | version checks |
| Raw session transcripts ("raw gold") | VERIFIED 150MB of `.jsonl` already on disk across 4+ project dirs under `~/.claude/projects/` | `du -sh ~/.claude/projects` |
| PreCompact hook | VERIFIED live and firing (`precompact-handoff.sh`, wired in `settings.json`) but VERIFIED it only logs `git status`/`git log` to `state/compact-log.md` — it does **not** copy or archive the transcript itself | Read of the hook script |
| Windows Task Scheduler | VERIFIED: zero personal/Claude/Gastown tasks exist (only OEM/vendor updater tasks) | `Get-ScheduledTask` (all, filtered) |
| Claude Code session cron (`CronCreate`/`CronList`) | VERIFIED empty ("No scheduled jobs") — this is the in-session tool, distinct from the cloud `schedule` skill that already runs `daily-deep-learning` at 06:02 per memory | `CronList` |
| CDP browser automation (`/cdp` command) | VERIFIED present at `.claude/commands/cdp.md` but VERIFIED entirely WSL-shaped: references `~/.codex/bin/obscura-cdp`, `ip route show default`, `/home/shovalbe/...` — none of which exist on this native-Windows box | Read of `cdp.md` |
| Native browsers for CDP | VERIFIED present: `msedge.exe` and `chrome.exe` both installed locally, either can open with `--remote-debugging-port` directly, no WSL bridge needed | `ls` on both binaries |

## Ranked recommendations (weak-point-closed per hour of effort, descending)

| # | Weak point | Resource that closes it | First command | Verification command | Honest effort |
|---|---|---|---|---|---|
| 1 | AUTO-18 always-on scheduling | Already-deployed GH Actions nightly cron + the `schedule` skill's cloud routines (proven elsewhere: `daily-deep-learning` posts daily at 06:02) | Nothing to build. Tomorrow: `gh run list --repo ShovalBenjer/claude-setup --workflow=claude-nightly.yml --limit 3` | Confirm a run with `conclusion=success` or a no-op (no changes) after 01:17 UTC; if it never fires, check Actions is enabled for scheduled workflows on a repo with recent pushes (GitHub auto-disables schedules after 60 days of repo inactivity — not yet a problem here, note for later) | 10-20 min, pure verification, zero build |
| 2 | Verification loop driving a browser (CDP) | Native `msedge.exe`/`chrome.exe` already installed — replace the WSL bridge in `cdp.md`, don't repair it | `Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList "--remote-debugging-port=9222","--user-data-dir=$env:LOCALAPPDATA\Edge-CDP-Profile"` | `curl -fsS http://127.0.0.1:9222/json/version` returns JSON with `webSocketDebuggerUrl` | 20-30 min: rewrite `cdp.md` for native Windows, drop the WSL-only steps, confirm the playwright MCP (if wired) can attach |
| 3 | Transcript archiving ("raw gold", unscoped) | 150MB of `.jsonl` already produced + the PreCompact hook that already fires but doesn't copy them | Edit `precompact-handoff.sh`: append the hook's `transcript_path` (from stdin JSON) to `state/transcript-archive/` before compaction runs, e.g. `cp "$TRANSCRIPT_PATH" "$OS_DIR/state/transcript-archive/$(date +%s)-$(basename "$TRANSCRIPT_PATH")"` | Trigger a manual `/compact`, then `ls state/transcript-archive/` shows a new file, and `state/hook-fires.log` shows the PreCompact fire timestamp matching it | 45 min-1 hr for the copy-only version (defer parsing/mining to a follow-up spec — don't build the miner before the archive exists) |
| 4 | AUTO-10 second-model review | `GEMINI_API_KEY` already set as a repo secret (2026-07-24), `claude-code-review.yml` as a structural template — but fix its broken max-turns FIRST | Step A (5 min): bump `--max-turns 10` in `claude-code-review.yml` to e.g. 20, or narrow the prompt scope, then re-run: `gh run rerun <last-failed-run-id> --repo ShovalBenjer/claude-setup`. Step B: write `.github/workflows/gemini-review.yml` triggered on the same `pull_request: [opened, synchronize]`, curl the Gemini API with the PR diff, post via `gh pr comment` | Step A: `gh run view <id> --repo ShovalBenjer/claude-setup --json conclusion` shows `success`. Step B: open a real test PR, confirm a Gemini-authored comment appears via `gh pr view <n> --json comments` | Step A: 15 min. Step B: 1-1.5 hr (no first-party Gemini GH Action exists, this is a hand-written curl step, not a drop-in like `anthropics/claude-code-action`) |
| 5 | AUTO-06 ecosystem.db | Python's built-in `sqlite3` — zero new dependency, already verified working | `python -c "import sqlite3; conn=sqlite3.connect('ecosystem.db'); conn.execute('CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY, ts TEXT, source TEXT, claim TEXT)'); conn.commit()"` | `sqlite3 ecosystem.db ".tables"` shows the table, and a second command inserts + selects one real row (not an empty schema sitting unused — this is exactly the failure pattern to avoid) | 1-2 hrs, but almost all of it is schema/scope design, not tooling — the resource is already 100% available, this is a "start the file" gap, not a resource gap |
| 6 | AUTO-05 phone concierge inbound | `cloudflared.exe` already on disk (closes ingress only) — telephony provider is NOT yet chosen, do not build past the tunnel until it is | `~/bin/cloudflared.exe tunnel --url http://localhost:8080` (stand up ingress only, point at a placeholder) | `curl -I https://<generated>.trycloudflare.com` returns a response through the tunnel | 30-45 min for the tunnel skeleton. Full close requires an explicit decision + signup (Twilio free trial or similar) that is out of scope for a "resource" recommendation — flag to Shoval as a decision, not a task |

## What is NOT worth doing right now (ruthless cuts)

- **Do not install `az` CLI for Foundry access.** No local Azure login exists, and
  `brn-azai`/`seekapa_ai` is employer infrastructure (i-sdd), not a personal-project
  resource. Using it here without explicit signoff blurs the personal/employer
  boundary for no clear payoff against the six named weak points.
- **Do not start Docker Desktop for this scope.** It is installed but the daemon is
  down, and Ollama already covers the "local model" need directly with less
  overhead. Spinning up Docker adds a running service with no weak point it uniquely
  closes here.
- **Do not repair the WSL CDP bridge.** `cdp.md` documents a path (`obscura-cdp`,
  WSL host-gateway routing, firewall rules) built for a machine that is not this
  one. Repairing it means re-deriving a WSL environment on a native Windows box.
  Replacing it with a 10-line native Edge/Chrome launch is strictly less work and
  removes a whole class of "wrong machine" failure.
- **Do not build the AUTO-05 receiver before the provider decision.** A Cloudflare
  Tunnel pointed at nothing is exactly the shape of the 23-unused-persona-files /
  35-dead-skill-stubs pattern this operator has already hit twice. The tunnel
  command above is a 30-minute proof it *can* work, not a thing to leave running.
- **Do not report AUTO-18 solved off the nightly workflow existing.** It has zero
  runs. "Deployed" is not "verified"; wait for the first real fire before closing
  the PRD line.

## Anti-pattern check (deploy-and-verify step named for each recommendation)

Every row above carries both a first command and a verification command precisely
because the standing failure mode here is infrastructure that gets created and
never exercised (23 persona files, 35 WSL-path skill stubs, no deploy script). The
one item without a hard verification loop by design is #6 (phone concierge): it is
deliberately capped at "prove the tunnel works" and explicitly told not to go
further until Shoval names a telephony provider, so it cannot silently join the
unused-infrastructure pile.
