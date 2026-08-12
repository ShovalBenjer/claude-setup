# Fix: `bwrap: Can't mkdir /mnt/c/Program Files/ClaudeCode: Permission denied`

## Root cause

Claude Code's sandbox policy (visible in the system prompt) includes these paths in its `write.denyWithinAllow` list:

```
/mnt/c/Program Files/ClaudeCode/managed-settings.json
/mnt/c/Program Files/ClaudeCode/managed-settings.d
```

To enforce a deny, bwrap must create those paths in its mount namespace. If `/mnt/c/Program Files/ClaudeCode/` does not exist on the Windows side, bwrap attempts to `mkdir` it — which fails because `/mnt/c/Program Files/` is a Windows-owned DrvFs mount that WSL cannot write to without Windows admin rights.

`dangerouslyDisableSandbox: true` does not help: the Bash tool sets up the bwrap namespace before honoring that flag on Linux/WSL.

## Fix (do ONE of these)

### Option 1 — RECOMMENDED: create the directory from Windows (persistent, survives Claude Code upgrades)

Open PowerShell **as Administrator** in Windows and run:

```powershell
New-Item -ItemType Directory -Path "C:\Program Files\ClaudeCode" -Force
```

That's it. The directory now exists, bwrap can bind-mount it, and the sandbox's deny policy becomes a no-op (nothing is inside it to deny). Restart Claude Code.

### Option 2 — WSL sudo workaround (may fail depending on DrvFs metadata)

In a plain WSL terminal (NOT inside Claude Code):

```bash
sudo mkdir -p "/mnt/c/Program Files/ClaudeCode"
```

If this fails with "Operation not permitted", use Option 1 — WSL can't override Windows ACLs on `Program Files`.

### Option 3 — if the Windows Claude Code install is what created the reference

If you have the Windows desktop Claude Code installed and don't use it, uninstall it. The sandbox policy reference may be gone after a full reinstall of Claude Code in WSL. Unverified — Option 1 is safer.

## Why `~/.claude/settings.json` and `/etc/claude-code/managed-settings.json` didn't work

The `denyWithinAllow` list is a hardcoded platform default baked into the Claude Code binary, not user-configurable. Disabling the sandbox in user or managed settings does NOT remove the bwrap setup step that creates the deny targets — bwrap still runs and still tries to mkdir the path.

## One-liner to verify fix worked

After running Option 1 and restarting Claude Code, the next Bash tool invocation should succeed. Test with: `ls ~`.

## If you want to prevent this recurring in future WSL setups

Add to your WSL setup notes:
> Before using Claude Code CLI on WSL, create `C:\Program Files\ClaudeCode\` from Windows admin PowerShell.

Optionally save the PowerShell command as a `.ps1` in your dotfiles:

```powershell
# fix-claude-code-wsl-sandbox.ps1
# Run as Administrator once per Windows host
New-Item -ItemType Directory -Path "C:\Program Files\ClaudeCode" -Force | Out-Null
Write-Host "Created C:\Program Files\ClaudeCode — Claude Code on WSL can now start bwrap."
```
