# Operator Runbook — manual steps only you can do

These are the steps blocked on your hands (credentials, decisions, installs). Each is
self-contained with the exact command. Do them when you're at the computer; nothing
here is time-critical. Order is by unblock value.

---

## 1. Authorize the subscription OAuth token (unblocks the whole review fabric)

Why: the 22-repo PR-review workflow authenticates with `CLAUDE_CODE_OAUTH_TOKEN`
(subscription-billed, not metered API — ADR-0002). The token generation hit a
"sign in again" security gate that needs your password.

Do this:
```
claude setup-token
```
- A browser opens. Sign in (password), then click **Authorize**.
- It prints a token starting `sk-ant-oat...`. Copy it.

Then push it to all repos as a secret (paste when prompted; it never lands in a file):
```
read -s TOK && gh repo list ShovalBenjer --source --no-archived --json name -q '.[].name' \
  | while read r; do echo "$TOK" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R "ShovalBenjer/$r"; done
```
Verify one:
```
gh secret list -R ShovalBenjer/claude-setup
```
Then tell Claude "token is set" — it will run the live two-Claudes review test on a
fresh PR (seed data for the persona economy).

---

## 2. Install the `codex` CLI (unblocks the two-model agreement gate)

Why: `a2a-codex-call.sh` bridges to Codex as the SECOND, decorrelated reviewer
(ADR-0004). The script exists; the `codex` binary is missing on this Windows box.
Without it, PR review degrades to Claude-only (no independent second model, so no
real agreement gate, so persona reputation has only one source).

Do this (npm global, ChatGPT subscription auth):
```
npm install -g @openai/codex
codex login        # ChatGPT subscription, same as before
codex --version    # confirm it runs
```
Then: `command -v codex` should resolve. Tell Claude "codex installed" and it wires
the agreement gate for real.

Decision if you DON'T want Codex: the gate can use two DIFFERENT Claude configs
(e.g. sonnet vs opus, different prompts/evidence) — weaker decorrelation but real,
and $0. Say which you prefer.

---

## 3. Install `rtk` (token-efficiency guard) — optional, low urgency

Why: the RTK bash guard rewrites noisy shell output to save context tokens. It was a
WSL binary at `~/.local/bin/rtk`; not present on Windows. Until installed, commands
run raw (more tokens, no correctness impact).

Do this: locate/rebuild the rtk binary on Windows (it's your tool — the source or
build script should be in the work bundle or your dotfiles). Drop it on PATH, then
tell Claude "rtk on PATH" and it wires the `PreToolUse(Bash)` guard.

---

## 4. Operator decisions (no install, just your call)

- **Global default model**: currently `claude-fable-5[1m]` in `~/.claude/settings.json`.
  Your own model-selection rule says Sonnet default, Fable by exception. To change:
  tell Claude "set default sonnet" (it edits settings) — or keep Fable deliberately.
- **Rotate the API key** that's sitting in plaintext in the WhatsApp "תזכורת לעצמי"
  group. Rotate it at the provider, delete the message. (Security; do it soon.)
- **PR-fabric repo list**: default is all 22 source repos. If you want a subset
  (cost/noise), name it; else it stays all.
- **WhatsApp copilot cadence**: proposed 2x/day triage + weekly coaching retro.
  Confirm or change.

---

## 5. Always-on daily digest (Windows Task Scheduler) — when you want it headless

Why: the digest cron is currently session-scoped (dies when Claude exits). For a
push that fires at 07:03 even with no session open, register a Task Scheduler job.

Do this (PowerShell, once):
```powershell
$act = New-ScheduledTaskAction -Execute "claude" -Argument '-p "Run the Claude OS daily digest: python C:/Users/shova/claude-setup/tools/digest/build_digest.py then PushNotification the contents of tools/digest/out/push.txt"'
$trg = New-ScheduledTaskTrigger -Daily -At 7:03am
Register-ScheduledTask -TaskName "ClaudeOS-Digest" -Action $act -Trigger $trg
```
Requires the PC awake at 07:03 (check Power settings; or add `-WakeToRun`).

---

## Status snapshot (2026-07-23)

Done + on GitHub: OS repo canonical, single source of truth, notification fabric
(phone+toast verified), 22-repo review workflow, PRD+8 ADRs+persona spec, repo graph,
branch health sweep, kernel-anchor hook (live), slop gate, digest generator+cron.

Blocked on the steps above: live review test (needs #1), agreement gate + persona
economy (need #1 + #2), RTK guard (#3), headless digest (#5).
