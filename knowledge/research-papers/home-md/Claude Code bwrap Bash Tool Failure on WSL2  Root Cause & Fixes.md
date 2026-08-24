# Claude Code `bwrap: Can't mkdir /mnt/c/Program Files/ClaudeCode: Permission denied` on WSL2

## Executive Summary

Every Bash tool invocation in Claude Code fails on this WSL2 setup because bubblewrap (`bwrap`) — the Linux sandboxing layer Claude Code uses — attempts to create a bind-mount staging directory inside `/mnt/c/Program Files/ClaudeCode/` during sandbox construction. That path lives on the Windows NTFS filesystem, which WSL2 exposes as read-only (from Linux's perspective) when the calling user has no Windows administrator rights. The error fires before any user command runs, which is why even `ls ~` and `dangerouslyDisableSandbox: true` have no effect — the sandbox *setup* itself crashes, not the command inside it.[^1][^2]

***

## Root Cause Analysis

### How bwrap Constructs Its Sandbox

Claude Code's sandbox runtime uses bubblewrap to create a new Linux mount namespace for every Bash tool call. Inside that namespace it builds a fresh root filesystem by bind-mounting a curated set of host directories. To create bind-mount target nodes on the host, bwrap must call `mkdir` for each path it intends to expose — even paths that will ultimately be read-only inside the sandbox.[^3][^4][^5][^2]

The sandbox launcher does not use the "soft" `--bind-try`/`--ro-bind-try` variants for all paths; for certain paths it uses hard `--bind`, meaning bwrap aborts immediately if the `mkdir` for that mount target fails. The error message `bwrap: Can't mkdir /mnt/c/Program Files/ClaudeCode: Permission denied` is exactly this abort — bwrap gave up at namespace setup, so the user command never runs.[^2][^1]

### Why `/mnt/c/Program Files/ClaudeCode` Is Attempted

Claude Code scans certain well-known paths when assembling the bwrap argument list, including the path where a Windows-native install of Claude Code stores its `managed-settings.json` and related files (`C:\Program Files\ClaudeCode\` → `/mnt/c/Program Files/ClaudeCode/` in WSL2). This is a **hard-coded path** in the bwrap launcher script, not something derived from the user's working directory or `additionalDirectories`. Even when no managed settings are present there, the launcher still attempts to bind-mount it.[^6][^2]

The identical failure pattern has been reported for other hard-coded optional paths — for example `/opt/cuda` on systems without CUDA installed — confirming this is a systematic issue with the launcher using unconditional `--bind` for paths that may not be writable.[^2]

### Why `dangerouslyDisableSandbox: true` Does Not Help

This flag instructs Claude Code to skip sandbox *enforcement* for a given tool call, but the bwrap wrapper is invoked at a lower level, before the per-call sandbox flags are evaluated. There is an open bug report (issue #46560) documenting exactly this: `sandbox.enabled: false` and `dangerouslyDisableSandbox: true` both fail to prevent bwrap from running when bwrap is triggered by path-detection logic that runs unconditionally.[^7][^8]

### Why WSL2 `/mnt/c` Is Read-Only for This Operation

Windows filesystem paths mounted under `/mnt/c/` are exposed to WSL2 with POSIX permissions emulated from the underlying Windows ACLs. For `C:\Program Files\`, standard Windows users do not have write permission, so WSL2 presents the directory to Linux processes as `dr-xr-xr-x` (no write bit). An unprivileged `bwrap` process calling `mkdir` on a child of this path receives `EPERM`/`EACCES`, which bwrap surfaces as `Permission denied`.[^9][^10]

This is not a WSL2 bug — it is the expected behavior: Linux permission semantics mirror Windows ACL read-only access.[^9]

***

## Fix Options (Ordered by Invasiveness)

### Fix 1 — Create the Missing Directory on the Windows Side (Recommended First Try)

The least disruptive fix is to create the directory that bwrap is trying to `mkdir` into, giving the WSL2 user write access:

```powershell
# Run in Windows PowerShell as Administrator
New-Item -ItemType Directory -Force -Path "C:\Program Files\ClaudeCode"
# Grant the current user write access
$acl = Get-Acl "C:\Program Files\ClaudeCode"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $env:USERNAME, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl "C:\Program Files\ClaudeCode" $acl
```

After granting Windows-side write permission, WSL2 will expose the path as writable and bwrap's `mkdir` will succeed. Restart Claude Code after making this change.[^10][^9]

**Limitation:** This adds a Windows filesystem path to the bwrap namespace. If the launcher also attempts to bind additional sub-paths under `C:\Program Files\ClaudeCode\`, each one must exist or bwrap will fail again at that sub-path (the same pattern seen with `/opt/cuda/bin`, `/opt/cuda/lib`, etc.).[^2]

### Fix 2 — Disable the Windows PATH Injection into WSL2

Claude Code's bwrap launcher discovers some paths to bind-mount by scanning the `PATH` environment variable and/or known installation prefixes. When WSL2 appends the Windows `%PATH%` to the Linux `$PATH` (the default WSL2 interop behavior), paths like `/mnt/c/Program Files/ClaudeCode` become visible and get included in the bwrap argument list.[^11][^12]

Disable Windows path injection in `/etc/wsl.conf`:

```ini
# /etc/wsl.conf  (create if absent, requires WSL restart to take effect)
[interop]
appendWindowsPath = false
```

Then restart WSL2 from PowerShell:

```powershell
wsl --shutdown
# Wait a few seconds, then reopen your terminal
```

After this, manually re-add any Windows tools you actually need in WSL2 (e.g., VS Code `code`):

```bash
# In ~/.bashrc or ~/.zshrc
export PATH="$PATH:/mnt/c/Users/<YourUser>/AppData/Local/Programs/Microsoft VS Code/bin"
```

This removes `/mnt/c/Program Files/ClaudeCode` from the paths that bwrap attempts to mount, because the path will no longer appear in `PATH` at all. This is the **cleanest systemic fix** and aligns with the general recommendation to keep WSL2 paths Linux-native when possible.[^13][^11]

### Fix 3 — Disable the bwrap Sandbox Entirely

This trades security for immediate functionality and is a recognized official workaround for bwrap failures where the path cannot be remedied.[^14][^15]

Edit `~/.claude/settings.json`:

```json
{
  "sandbox": {
    "enabled": false
  }
}
```

Fully quit Claude Code (kill all `claude` processes) and restart. Because of a known config-caching bug, a simple restart may not be enough — verify the sandbox is disabled via `/sandbox` inside Claude Code.[^16][^15]

**Caveat:** Disabling the sandbox removes filesystem and network isolation for Bash tool calls. This is acceptable for solo developer use on a trusted machine but is not suitable for agentic or multi-user environments.[^17][^15]

### Fix 4 — Use `denyRead` / `permissions.deny` to Exclude `/mnt`

If the path is being included because Claude Code's permission layer auto-includes directories from the filesystem (e.g., as part of scanning working-directory neighbors), adding an explicit deny can prevent the bind-mount from being attempted:

```json
{
  "permissions": {
    "deny": [
      "Read(/mnt/**)",
      "Edit(/mnt/**)"
    ]
  }
}
```

This approach works for some sub-categories of the problem (particularly when a symlink under `~` points to `/mnt/c/...`) but may not stop hard-coded path binding in the bwrap launcher itself. Use it in conjunction with Fix 1 or Fix 2, not as a standalone solution.[^18][^16]

### Fix 5 — Symlink `/mnt/c/Program Files/ClaudeCode` to a Native WSL2 Path

If you cannot modify Windows ACLs and do not want to disable `appendWindowsPath`, you can shadow the inaccessible Windows path with a native Linux directory:

```bash
# Create a writable native Linux directory to stand in for the Windows path
sudo mkdir -p "/mnt/c/Program Files/ClaudeCode"
# If that itself fails (because /mnt/c is fully read-only at the mount level):
# Create the directory tree in native WSL2 space and bind-mount over the Windows path
mkdir -p ~/wsl-overrides/ClaudeCode
sudo mount --bind ~/wsl-overrides/ClaudeCode "/mnt/c/Program Files/ClaudeCode"
```

This is fragile across WSL2 restarts (bind mounts do not persist) but can be scripted into `~/.bashrc` or a `wsl.conf` `[boot] command` entry. Use it as a temporary measure while implementing Fix 1 or Fix 2.[^19]

***

## Why `dangerouslyDisableSandbox` Does Not Work (Detailed)

This deserves explicit treatment because its failure is counterintuitive. The flag is documented as disabling sandbox isolation for a specific tool call, but the bwrap wrapper is invoked by Claude Code at a layer beneath per-call flags. Open bug report #46560 on the Claude Code repo (April 2026) documents the exact same symptom — `dangerouslyDisableSandbox: true`, `/sandbox` toggle showing "disabled," and `sandbox.enabled: false` in settings all still result in bwrap being invoked and failing — whenever bwrap is triggered by path-detection logic that runs unconditionally before the per-call flag is checked. Until Anthropic patches the launcher to use `--bind-try` for optional paths or to check writability before calling `--bind`, the only reliable escape from this class of failure is either to fix the underlying path permission or to prevent the path from appearing in the bwrap argument list entirely.[^8][^20][^7][^2]

***

## Config Caching Caveat

Multiple filed bugs confirm that Claude Code caches sandbox configuration and does not fully reload it on a simple restart. After making any change to `~/.claude/settings.json`, ensure all Claude Code processes are terminated:[^15][^16]

```bash
pkill -f claude
# Wait 3–5 seconds
# Restart Claude Code
```

If Claude Code was opened via the VS Code extension, also reload the VS Code window (`Ctrl+Shift+P` → "Developer: Reload Window").

***

## Recommended Action Plan

| Priority | Action | Expected Outcome |
|---|---|---|
| 1 | Disable `appendWindowsPath` in `/etc/wsl.conf` | Removes Windows paths from bwrap scan; cleanest fix[^11] |
| 2 | `wsl --shutdown` and reopen terminal | Applies wsl.conf change[^11] |
| 3 | Test `ls ~` in a new Claude Code session | Bash tool should succeed |
| 4 | If still failing, create the Windows directory with proper ACLs (Fix 1) | bwrap mkdir succeeds[^9] |
| 5 | As a last resort, set `sandbox.enabled: false` | Sandbox disabled; fully functional but no isolation[^15] |

***

## Related Known Issues

- **bwrap fails on `/opt/cuda` on non-CUDA systems** — identical root cause: hard-coded `--bind` on optional paths that don't exist or aren't writable.[^2]
- **bwrap fails when `~/.aws` is a symlink to `/mnt/c/...`** — sandbox tries to mount a tmpfs over a Windows-backed symlink target.[^16][^15]
- **`sandbox.enabled: false` ignored when CWD is `~/.claude/`** — bwrap is invoked for `denyWithinAllow` path setup regardless of the enabled flag.[^8]
- **`denyRead` and `denyWrite` silently ignore relative paths** — only absolute paths take effect in sandbox filesystem configuration.[^21]

---

## References

1. [Bash tool leaks 'mkdir: Permission denied' to stdout on ... - GitHub](https://github.com/anthropics/claude-code/issues/24774) - The error originates from the Claude Code parent process (the Bun binary), likely during sandbox (bw...

2. [bwrap launcher uses --bind for optional hardware paths (/opt/cuda ...](https://github.com/anthropics/claude-code/issues/50632) - Any user on AMD, Intel-iGPU, ARM, CPU-only hardware, or inside a container without CUDA installed wi...

3. [Sandboxing - Claude Code Docs](https://code.claude.com/docs/en/sandboxing) - Configurable: Define custom allowed and denied paths through settings. You can grant write access to...

4. [Trying out bubblewrap used in Claude Code's Sandbox Runtime ...](https://www.sambaiz.net/en/article/547/) - Claude Code has a Sandboxing feature that isolates filesystem and network to run agents safely while...

5. [bwrap(1) — Arch manual pages](https://man.archlinux.org/man/bwrap.1.en) - By default, bwrap creates a new mount namespace for the sandbox. ... Bind mount the host path SRC on...

6. [Anthropic Claude Hardening Guide](https://howtoharden.com/guides/anthropic-claude/) - Linux / WSL, /etc/claude-code/managed-mcp.json. Windows, C:\Program Files\ClaudeCode\managed-mcp.jso...

7. [sandbox.enabled: false setting ignored — bwrap still wraps all Bash ...](https://github.com/anthropics/claude-code/issues/35986) - Claude Code v2.1.79 on Linux still wraps every Bash tool invocation in bwrap (bubblewrap) with --die...

8. [[BUG] sandbox.enabled: false does not disable bwrap when working ...](https://github.com/anthropics/claude-code/issues/46560) - bwrap's denyWithinAllow list auto-includes paths like .claude/skills , .claude/hooks , .claude/setti...

9. [Fix Windows Subsystem for Linux (WSL) File Permissions](https://www.turek.dev/posts/fix-wsl-file-permissions/) - The fix has two pieces: fixing how WSL mounts Windows drives and then fixing the permissions for new...

10. [[WSL2] Permissions problem with mounted windows volume #4824](https://github.com/docker/for-win/issues/4824) - Starting official mysql container with empty data directory ( /var/lib/mysql ) mounted from windows ...

11. [How to remove the Win10's PATH from WSL - Stack Overflow](https://stackoverflow.com/questions/51336147/how-to-remove-the-win10s-path-from-wsl) - Changing that to 0x0D (= 13) prevents appending the Windows %PATH% to the Ubuntu $PATH. You can stil...

12. [Why does my $PATH include my windows path as well? - Reddit](https://www.reddit.com/r/bashonubuntuonwindows/comments/17zmalb/why_does_my_path_include_my_windows_path_as_well/) - It's intentional, you can change it in /etc/wsl.conf to disable this functionality.

13. [WSL2, Windows, Python and Node: resolving some conflicts](https://dev.to/yorek/wsl2-windows-python-and-node-resolving-some-conflicts-2gg2) - First, tell WSL not to automatically add windows path to WSL. This can be done via wsl.conf file, as...

14. [bwrap: Can't create file at .claude/skills: Is a directory when sandbox ...](https://github.com/anthropics/claude-code/issues/40133) - When setting up the bind-mount filesystem, bwrap tries to create a file node at this path, but it's ...

15. [(Guide) Fix BUG WSL2 Sandbox bwrap fails to mount - StepCodeX](https://www.stepcodex.com/en/issue/bug-wsl2-sandbox-bwrap-fails-to) - # [BUG] WSL2 Sandbox bwrap fails to mount ~/.aws when symlinked to inaccessible path

claude-code

O...

16. [[BUG] WSL2 Sandbox bwrap fails to mount ~/.aws when symlinked ...](https://github.com/anthropics/claude-code/issues/45122) - It looks like Claude Code caches the old configuration and retains it, ignoring more recent changes ...

17. [How /sandbox Works - Claude Code Camp](https://www.claudecodecamp.com/p/claude-code-sandboxing-how-sandbox-works-and-what-it-doesn-t-protect) - If you only configure the sandbox, bash can't read your SSH keys but Claude's Read tool can. The fix...

18. [[BUG] sandbox denyRead seems ineffective #32226 - GitHub](https://github.com/anthropics/claude-code/issues/32226) - What's Wrong? Claude can list by GPG private keys even though I denied access to ~/.gnupg/** in sand...

19. [How to add or remove /mnt/c/ in WSL 2 with Pengwin and zsh](https://stackoverflow.com/questions/61583405/how-to-add-or-remove-mnt-c-in-wsl-2-with-pengwin-and-zsh) - I have two Windows machines with WSL 2/Pengwin/zsh here and the first one shows prompt and refers to...

20. [[BUG] Linux sandbox broken - bad bwrap calls and no allow ...](https://github.com/anthropics/claude-code/issues/17727) - Steps to Reproduce. Use Linux. Edit permission settings. Enable sandbox. Get Bash tool to write to a...

21. [sandbox.filesystem.denyWrite/denyRead silently ignore relative ...](https://github.com/anthropics/claude-code/issues/50454) - When configuring sandbox.filesystem.denyWrite and denyRead in settings.json , relative path patterns...

