# Claude Code: faster and better than stock — middle ground vs restore

Research report, 2026-06-14. Decision: should the shelved Ink/React TUI daemon (commit `36f9a582`) be restored, or is a lighter "middle ground" the better path to a faster and higher-quality Claude Code than stock? Environment: WSL2 Ubuntu on Windows, bash, `$HOME` on ext4 (correct), heavy 1M-context Opus usage.

---

## Verdict

**Do NOT restore the Ink daemon. Take the middle ground — it is faster AND better than both stock and the daemon.**

The daemon is a net negative on the exact axis you care about. Reading its source (`ink-daemon.mjs`, 153 lines) confirms it is a persistent Node process running a Unix-socket server plus an 80ms `setInterval` spinner loop, fed by `pretooluse-ink.sh` / `posttooluse-ink.sh` hooks, rendering two ANSI rows on demand. Claude Code's native `statusLine` feature now delivers everything that daemon was built for, with the live session payload handed to you directly and no second process competing for the terminal's bottom rows. A separate render loop alongside Claude Code adds memory, CPU, and an IPC failure mode for zero capability gain. The same 2026 commit also shipped a `statusline.sh` (371 lines) — that is the piece worth reviving, as a native command, not the daemon.

The real "faster + better than stock" gains come from three layers, in priority order: (1) Claude Code's own native perf/quality settings, (2) a GPU-accelerated terminal emulator, (3) a native cached statusLine. None of them require the daemon.

---

## Layer 1 — Claude Code native settings (biggest, cheapest wins)

Verified against the official docs [1][2][3].

- **`"tui": "fullscreen"`** in `settings.json` — the documented persistent path to the alternate-screen renderer: eliminates flicker and keeps memory flat in long sessions [2]. Your launcher already sets `CLAUDE_CODE_NO_FLICKER=1`, which is the research-preview env path into the same thing; the settings key is the supported form.
- **Keep virtual scroll ON** — do NOT set `CLAUDE_CODE_DISABLE_VIRTUAL_SCROLL`. It renders only the viewport, which is the long-session perf win [2].
- **`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`** — blocks autoupdater/telemetry/error-reporting in one shot [1]. Optionally `CLAUDE_CODE_DISABLE_MOUSE=1` (you already set it in the launcher).
- **`"wheelScrollAccelerationEnabled": false`** (v2.1.174+) and the documented TUI keys: `theme`, `spinnerTipsEnabled` [3][2].
- **Stay current.** v2.1.152 stopped the idle `/goal` chip re-rendering at 5 Hz, removed redundant message normalization in long conversations, and improved large-file diff rendering [4]. These are free perf if you update.
- **Disable idle MCP servers** via `/mcp`. Your Jira/Playwright/HeyGen servers cost context and overhead when unused; tool defs are deferred but the servers still add weight [5].
- **`/fast` (conditional).** Up to ~2.5x output tokens/sec on Opus 4.8, same model and intelligence, persist with `"fastMode": true` [6]. Two hard caveats: it is **Anthropic-API/subscription only — NOT Azure Foundry/Bedrock/Vertex** [6], and the first enable in a conversation re-bills the whole context at full uncached input price, so enable from session start, never mid-session [7]. Only adopt if Claude Code here points at direct Anthropic, and you accept the higher per-token cost.

**Myths to skip:** no `autoCompactThreshold` settings key (use `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`) [1]; no "lite" TUI mode (fullscreen IS the light path) [2]; no `CLAUDE_CODE_DEBUG_PERF` flag.

---

## Layer 2 — GPU terminal emulator (largest real-world smoothness lever)

You currently have **no identifiable GPU terminal** (`TERM=xterm-256color`, no `WT_SESSION`). Moving to a GPU-accelerated emulator is the single biggest perceptual smoothness gain, and it also fixes the Nerd Font icon gap from the earlier glow-up.

Ranked for WSL2 on Windows in 2026 [8][9][10][11]:

1. **WezTerm** — best balance: GPU (WebGpu front-end), native WSL2 wiring (`default_domain = 'WSL:Ubuntu'`), ligatures, splits, built-in Catppuccin Mocha. Pick unless you measure keystroke lag (a known Win11 quirk, mitigated via `front_end`/`max_fps`) [12][13].
2. **Windows Terminal (AtlasEngine, D3D11)** — zero-install, native WSL2, solid GPU rendering. The safe no-config default [14][15].
3. **Alacritty + tmux** — only if you chase the lowest latency and accept tmux for multiplexing [9].

Skip **Kitty** (no native Windows, needs an X server) [16] and treat **Ghostty-on-Windows** as experimental (unofficial ports only as of 1.3.0) [17].

WezTerm `~/.wezterm.lua` (Windows side):
```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.default_domain = 'WSL:Ubuntu'
config.color_scheme = 'Catppuccin Mocha'
config.font = wezterm.font('JetBrainsMono Nerd Font')
config.font_size = 11.0
config.window_background_opacity = 0.90
config.win32_system_backdrop = 'Acrylic'
config.front_end = 'WebGpu'
config.max_fps = 120
return config
```

**Nerd Font:** install **JetBrainsMono Nerd Font on the Windows side** (`choco install nerd-fonts-jetbrainsmono` or the nerd-fonts release .ttf), then set it as the terminal font. The glyphs are rendered by the Windows terminal, not WSL, so no Linux-side font install is needed [18][19][20]. This makes your eza icons and starship glyphs render.

**WSL2 rules:** keep repos on the Linux ext4 filesystem (you do — `$HOME` is ext4); never run Claude Code against a repo under `/mnt/c` (9P file-server overhead per op is brutal for Claude Code's many small file ops) [21][22]. Prefer fixed opacity over acrylic blur for the snappiest input [15].

---

## Layer 3 — native statusLine (the quality upgrade that replaces the daemon)

Claude Code's `settings.json` `statusLine` (`type: "command"`) pipes a rich JSON session payload to your script on stdin; whatever it prints to stdout is rendered, no API tokens [23]. The payload already carries everything your daemon scraped: `model.display_name`, `context_window.used_percentage` / `exceeds_200k_tokens`, `cost.total_cost_usd`, `workspace.git_worktree` / `repo.*`, `pr.{number,review_state}`, `rate_limits.*`, `effort.level`, `output_style.name` [23].

- **Multi-line is native** (each `echo` is a row) — your two-row design maps directly.
- **Braille spinner** is just rotating braille chars in the printed string; animate it with `refreshInterval: 1` re-running a cheap script [23].
- **Performance is the load-bearing rule:** slow scripts block the bar. Cache git state to `/tmp/statusline-git-cache-$session_id`, refresh every ~5s, key on `session_id` (not `$$`/pid, which changes per invocation) [23].

Two ways to land it:
- **Revive your `statusline.sh`** from commit `36f9a582` as the native command, applying the 5s git cache. You keep your exact ISDD design.
- **Adopt `ccstatusline`** (~10.7k stars): powerline rendering, context % / token rates / cost / git / PR widgets, already caches git + block timers, runs as a per-invocation script (not a daemon) [24]. `ccusage` statusline (~4.8k stars) is the cost-focused alternative [25].

Either way: retire `ink-daemon.mjs` and the `pretooluse-ink.sh` / `posttooluse-ink.sh` hooks. Native statusLine gets the data without them.

---

## Recommended end state

1. **settings.json:** `"tui": "fullscreen"`, `"wheelScrollAccelerationEnabled": false`, `statusLine` pointed at a cached `statusline.sh` (revived) or ccstatusline. Add `"fastMode": true` only if Claude Code here is on direct Anthropic and you accept the cost.
2. **env (in the interactive guard):** `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`.
3. **terminal:** WezTerm (or Windows Terminal) + JetBrainsMono Nerd Font installed on Windows + Catppuccin Mocha + 0.90 opacity.
4. **hygiene:** keep Claude Code updated; disable idle MCP servers; keep repos off `/mnt/c`.
5. **drop:** the Ink daemon. It is the one thing that makes it slower, not faster.

This is faster than stock (fullscreen renderer + GPU terminal + trimmed traffic/MCP), better than stock (cached two-row statusLine + theme + font), and strictly better than restoring the daemon (no second process, no IPC, full native payload).

## Limitations

- Whether `/fast` applies depends on Claude Code's backend here (Anthropic vs Foundry), which this report did not pin — verify before enabling.
- Latency numbers between GPU terminals are hardware-dependent; the WezTerm-vs-WindowsTerminal gap is small, so pick on features/integration.
- The exact spelling of newer settings keys (`wheelScrollAccelerationEnabled`, auto-compact env vars) churned across the 2.1.x line — confirm against your installed version's `/config` and `claude --help` before baking in.

## Bibliography

1. https://code.claude.com/docs/en/env-vars.md
2. https://code.claude.com/docs/en/fullscreen.md
3. https://code.claude.com/docs/en/settings.md
4. https://code.claude.com/docs/en/changelog.md
5. https://code.claude.com/docs/en/how-claude-code-works.md
6. https://code.claude.com/docs/en/fast-mode.md
7. https://platform.claude.com/docs/en/build-with-claude/fast-mode
8. https://scopir.com/posts/best-terminal-emulators-developers-2026/
9. https://app.daily.dev/posts/terminal-latency-on-windows-stlfp3zdr
10. https://deepwiki.com/microsoft/terminal/3.2-atlas-engine
11. https://wezterm.org/config/lua/config/wsl_domains.html
12. https://github.com/wezterm/wezterm/discussions/5400
13. https://wezterm.org/config/appearance.html
14. https://github.com/catppuccin/wezterm
15. https://www.tskamath.com/configure-windows-terminal-for-peak-productivity/
16. https://petronellatech.com/blog/kitty-terminal-setup-guide-2026
17. https://ghostty.org/docs/install/release-notes/1-3-0
18. https://petronellatech.com/blog/nerd-fonts-guide/
19. https://www.ariadne-wsl.com/nerd-font.html
20. https://starship.rs/presets/nerd-font
21. https://learn.microsoft.com/en-us/windows/wsl/compare-versions
22. https://github.com/microsoft/WSL/issues/4197
23. https://code.claude.com/docs/en/statusline
24. https://github.com/sirmalloc/ccstatusline
25. https://ccusage.com/guide/statusline
