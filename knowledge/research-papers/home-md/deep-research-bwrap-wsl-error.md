# Research: Claude Code Bash tool fails with `bwrap: Can't mkdir /mnt/c/Program Files/ClaudeCode: Permission denied` on WSL2

## Environment
- OS: Linux 6.6.87.2-microsoft-standard-WSL2 (Ubuntu in WSL2 on Windows)
- Claude Code CLI installed in WSL2 at `/home/shovalbe/.claude/`
- Windows filesystem mounted at `/mnt/c/`, including `/mnt/c/Program Files/ClaudeCode/` (Windows install of Claude Code — read-only from WSL by default, owned by Windows)
- Shell: bash
- User has no sudo-less write access to `/mnt/c/Program Files/`
- Sandbox implementation: `bwrap` (bubblewrap) — used by Claude Code to isolate Bash tool calls

## Error
Every Bash tool invocation — including simple `ls ~`, and including calls made with `dangerouslyDisableSandbox: true` — fails with:

```
bwrap: Can't mkdir /mnt/c/Program Files/ClaudeCode: Permission denied
```

Exit code 1, no command output, bwrap dies during sandbox setup before the command runs.

The sandbox's default policy references `/mnt/c/Program Files/ClaudeCode/managed-settings.json` and `/mnt/c/Program Files/ClaudeCode/managed-settings.d` as part of the `denyWithinAllow` write policy (enterprise/admin policy tier). bwrap appears to attempt to bind-mount or mkdir those paths during sandbox setup, and fails because the parent `/mnt/c/Program Files/` is owned by Windows and not writable from WSL.

## What has been tried (all failed)
1. `dangerouslyDisableSandbox: true` on the Bash tool call — same error. The harness appears to invoke bwrap *before* honoring this flag, or the flag doesn't disable bwrap setup on this platform.
2. `/sandbox` slash command in Claude Code with auto-allow enabled — no change.
3. Creating `~/.claude/settings.json` with `"sandbox": { "enabled": false }` — user settings tier, below managed-settings in precedence.
4. Creating `/etc/claude-code/managed-settings.json` with `"sandbox": { "enabled": false }` — Linux managed-settings path; unclear if Claude Code on WSL reads this or prefers the Windows mount path.
5. `sudo mkdir -p "/mnt/c/Program Files/ClaudeCode"` is suggested as a workaround but requires the user to run it in a plain WSL terminal (can't be run from inside Claude Code because Bash itself is broken). Also unclear whether WSL can chown/chmod under `/mnt/c/Program Files/` at all given DrvFs and Windows ACLs.

## What I need the research to answer
1. **Root cause:** why does bwrap try to mkdir inside `/mnt/c/Program Files/ClaudeCode` during sandbox initialization? Is this from Claude Code's default `denyWithinAllow` policy for Windows-path managed settings, and does it trigger regardless of sandbox enabled/disabled?
2. **Why `dangerouslyDisableSandbox: true` doesn't work.** Does that flag disable bwrap entirely, or just relax its policies? Is there a known issue on WSL where it still invokes bwrap for setup?
3. **The correct fix.** Rank solutions by reliability, WSL-safety, and whether they survive Claude Code upgrades:
   - Creating an empty `/mnt/c/Program Files/ClaudeCode/` directory from Windows (PowerShell as admin)
   - Configuring `/etc/claude-code/managed-settings.json` to disable sandbox globally — does this override the Windows-mount policy?
   - An env var or CLI flag to opt out of the Windows-mount policy paths on WSL
   - Modifying `~/.claude/settings.json` with specific sandbox config overrides (exact JSON)
   - Removing/relocating the Windows Claude Code install (`/mnt/c/Program Files/ClaudeCode/`) so the path doesn't exist and the policy has nothing to enforce
4. **Is this a known Claude Code bug on WSL2?** Check the Claude Code GitHub issues repo (`anthropics/claude-code`) and release notes for `bwrap`, `WSL`, `mnt/c`, `managed-settings`, and `sandbox` issues. Cite issue numbers.
5. **Precedence of managed-settings on WSL.** Which path wins: `/etc/claude-code/managed-settings.json` (Linux) or `/mnt/c/Program Files/ClaudeCode/managed-settings.json` (Windows)? Official docs preferred.

## Deliverable
A short report with:
- Root-cause explanation (2-4 paragraphs)
- Ranked fix list with exact commands/file contents
- Link to the canonical GitHub issue or docs page if one exists
- One-line mitigation the user can run in a plain WSL terminal right now

Keep the report under 800 words. Prefer Anthropic/Claude Code official docs and the anthropics/claude-code GitHub repo over third-party blogs. Cite every claim.
