# Agent Shell & MCP Layer — Companion Decision Report

**Date:** 2026-06-09
**Author:** automated research sweep (CLI agent-vs-human triage + MCP landscape/security + install wiring)
**Reader:** Shoval (operator). Bottom-line-first. No secret values appear in this report.
**Companion to:** `2026-06-09-stack-modernization-and-hive-upgrade.md` (this is the agent-shell + MCP-layer half of the same sweep).
**Stack reality assumed:** Azure Functions (Python) + Azure Container Apps + Bicep + Azure DevOps Pipelines, WSL2/Ubuntu host, `rtk` proxy already present, `bun`/`uv` toolchain, Jira + Playwright + Foundry + VoiceSpin + AlphaVantage + HeyGen MCPs already connected.

---

## 1. The Central Insight

**The 2026 "modern CLI" map optimizes for HUMAN richness. Your agents' shell output flows into an LLM context window, where every byte of decoration costs tokens — and `rtk` already exists to strip exactly that. So the answer is a 3-way split, not "adopt the map."**

The operator-supplied CLI map bundles two orthogonal concerns:

1. **Speed / ergonomics** — legitimate for both humans AND agents. ripgrep's speed is real and agent-relevant. fd's parallelism is agent-relevant. sd's PCRE2 regex dialect reduces agent escaping errors.
2. **Visual richness** — human-ONLY. ANSI 24-bit color, Nerd Font icons, side-by-side diffs, Unicode bar-charts, image previews, full-screen TUIs.

The second category is not neutral in an agent context — it is actively harmful. ANSI escape sequences carry 20-60 bytes per visible diff line, each tokenized as 1-3 tokens by BPE encoders, with **zero semantic value**. Augment Code's SWE-bench analysis found 30,400 of 48,400 total tokens in a representative agent run came from tool outputs alone (~63%), and 39-59% of those were removable with no performance loss.

`rtk` on this host is the lever that already addresses this: it strips and compresses tool output before it reaches the context window. So the correct mental model is:

- **Install modern Rust CLIs for speed** (human ergonomics + the genuinely faster agent-facing ones).
- **Route ALL agent Bash through `rtk`** so decoration never enters context.
- **Set `NO_COLOR=1` + `PAGER=cat`** as defense-in-depth for anything that slips past `rtk proxy`.
- **Never invoke TUI / interactive tools from agent Bash** (btop, yazi, zellij, broot, fzf-interactive, atuin, zoxide) — they require a PTY, block on keyboard input, and cannot produce parseable output.

MCP suggestions are largely sound, with one material security caveat (Context7 / ContextCrush) and one hard "do not use" (the official `@modelcontextprotocol/server-postgres` — confirmed read-only bypass).

### Map corrections (claims that did not survive verification)

- **"ripgrep is 10-50x faster than grep"** — overstated. Primary sources (BurntSushi blog, ripgrep.dev) show 1.9x-36x. The 36x only applies to Unicode-aware regex on the Linux kernel tree; literal English searches are 1.9-3x. The 50x upper bound is unsubstantiated.
- **"sd is 2-11x faster than sed"** — accurate range, but applies specifically to `across` mode (`-A`) and regex-heavy workloads. sd's default line-by-line mode can be slower than sed on some patterns.
- **fd 13-23x vs find** — true but single-machine, warm-cache, .gitignore-dense; fd's own README cautions it is "one benchmark on one machine."
- **Context7 "65% token reduction"** — single secondary source (EF-Map blog), not verified against Context7 docs.
- **xh "30% faster than HTTPie"** — refers to startup vs Python HTTPie, NOT vs curl. No primary benchmark vs curl exists.

---

## 2. Tool Triage Table

Consolidated across all three research domains. Verdict reconciles where domains differed (the stricter agent-safety verdict wins for the "should the agent ever call this" column).

| Tool | Verdict | rtk-covered? | Why |
|---|---|---|---|
| **ripgrep (rg)** | agent-facing | yes (`rtk grep`) | 1.9-36x faster than grep (pattern/corpus-dependent). Already installed. Clean line-oriented output. Use `--color=never --no-heading`. |
| **fd** | agent-facing | yes (`rtk find`) | 13-23x faster than find on large trees. Respects .gitignore (less noise). Plain output. Not yet installed. Use `--color=never`. |
| **sd** | agent-facing | no | 2.35-11.93x faster than sed; PCRE2 dialect matches rg (fewer escaping errors). Plain text, no ANSI. Not installed. Safe to call directly. |
| **yq** | agent-facing | yes (`rtk json` adjacent) | Already installed. Clean structured YAML/JSON. Use `-r` / `--no-colors`. Essential for Bicep params + Azure pipeline YAML. |
| **mlr (miller)** | agent-facing | no | CSV/TSV/JSON tabular processing jq cannot do. Always `--ojson`/`--ocsv`. Not installed. For CRM exports, eval CSVs, Azure cost data. |
| **hyperfine** | agent-facing | no | Scripted benchmarking; always `--export-json`. The benchmark methodology behind fd/sd/rg's own numbers. CI regression loops. |
| **eza / lsd** | human-facing | yes (`rtk ls`) | Icons = Unicode PUA codepoints (2-4 tokens each). lsd has no plain mode. Install eza for operator; agent uses `rtk ls`. |
| **bat** | human-facing | yes (`rtk read`) | Suppresses ANSI when piped, but adds startup overhead. Agent uses `rtk read`. Operator: `BAT_STYLE=plain` if ever in agent env. |
| **delta** | human-facing | yes (`rtk diff`) | 24-bit RGB ANSI + side-by-side (doubles line count). Git pager — bypassed when piped (no tty), so agent is safe by default. |
| **dust** | human-facing | no | ASCII/Unicode bar-chart disk usage. Agent uses `du -sh` via `rtk proxy`. |
| **duf** | human-facing | no | Unicode box-drawing table — wastes tokens even with NO_COLOR. Agent uses `df -h` via `rtk proxy`. |
| **procs** | human-facing | no | Color + tree + icons on process listings. Agent uses `ps aux` via `rtk proxy` (or `procs --no-header --color=never` if needed). |
| **btop / btm** | human-facing | no | Full-screen TUI, alternate screen, no batch/pipe mode. Cannot be agent-called at all. |
| **broot** | human-facing | yes (`rtk tree`) | Interactive alternate-screen tree navigator. `--headless` output is non-standard. Agent uses `rtk tree` or fd. |
| **yazi** | human-facing | no | Async TUI file manager, Kitty image preview. Requires PTY. No agent use. |
| **zellij** | human-facing | no | Terminal multiplexer, WASM plugin UI, no pipe mode. tmux (installed) covers all agent session needs. |
| **zoxide** | human-facing | no | Shell function mutating PWD via eval hooks — hooks do not fire in subprocess Bash. Agent uses absolute paths. |
| **atuin** | human-facing | no | Ctrl-R history daemon + TUI. Agent does not use interactive history. Guard init with `[[ $- == *i* ]]`. |
| **fzf** | dual-use | no | Interactive picker = human-only. BUT `fzf --filter 'q' < input` (filter mode) is plain output, zero ANSI/TUI — usable in agent fuzzy-filter pipelines. |
| **xh / httpie** | dual-use | yes (`rtk wget`) | Human: colored JSON. Agent: prefer curl (LLM-known, deterministic) or `rtk wget`; if xh, force `--pretty=none`. No speed delta vs curl. |
| **tmux** | dual-use | no | Already installed. Fully scriptable (`send-keys`, `new-session -d`). Agent-facing for parallel-pane orchestration (Gastown). Do NOT replace with zellij. |
| **MCP: GitHub** | agent-facing | no | Structured JSON; removes gh CLI subprocess spawns. Scope read-only first. |
| **MCP: Azure (microsoft/mcp)** | agent-facing | no | 43+ service areas; removes az CLI spawns. Reader RBAC. |
| **MCP: Azure DevOps** | agent-facing | no | Structured ADO repo/PR/work-item access. Remote endpoint + Entra auth. |
| **MCP: Sentry** | agent-facing | no | Pulls error context without browser switch. `org:read` only initially. Treat results as untrusted. |
| **MCP: Postgres** | agent-facing (deferred) | no | No active Postgres source (PandaTS dropped, CRM is HTTP). Defer. If added: CrystalDBA `--access-mode=restricted` only. |
| **MCP: Context7** | dual-use | no | Kills stale-API hallucinations BUT ContextCrush prompt-injection via Custom Rules. Cap maxTokens=3000, treat injected content as untrusted. |
| **MCP: Playwright** | dual-use | no | Already connected. Structured JSON + screenshots, no ANSI. Headless on agent runs. |
| **MCP: Linear** | human-facing | no | Not in stack (Jira + ADO cover PM). Adds injection surface, zero net capability. Skip. |

---

## 3. Corrected "Agent Shell Defaults" Block for CLAUDE.md (rtk-first)

Paste-ready. This replaces / extends the terminal-contract section of CLAUDE.md.

````markdown
## Agent Shell Defaults (rtk-FIRST)

All agent Bash calls route through `rtk` by default. Use `rtk proxy <cmd>` only when
exact GNU/host behavior is required (e.g. `find -maxdepth`, Docker inspect, systemd).

### rtk-covered commands — always use the rtk form

| Need | Agent call | NEVER use |
|---|---|---|
| List files | `rtk ls [path]` | `eza`, `lsd`, `ls --color`, `ls -la --icons` |
| Read file | `rtk read <file>` | `bat`, `cat` with pager |
| Grep/search | `rtk grep <pattern> [path]` | `rg --color=auto`, `grep --color` |
| Find files | `rtk find -name '*.py'` | `fd --color=always`, raw `find` |
| Git status/log | `rtk git status`, `rtk git log` | `git` with delta pager active |
| Diff | `rtk diff <a> <b>` | `delta`, `diff --color`, side-by-side diffs |
| JSON query | `rtk json < file` or `jq -r` | colorized jq output |
| Docker | `rtk docker ps` | `docker ps` with color |
| Test runs | `rtk test <runner>` | raw pytest/bun test (full verbose output) |
| HTTP fetch | `rtk wget <url>` or `curl -sS` | `xh` without `--pretty=none` |
| GitHub CLI | `rtk gh pr list` | `gh` with color/icons |
| Logs | `rtk log <cmd>` | raw `func host start`, `az` log streams |
| YAML query | `rtk proxy yq -r '.key' file.yaml` | yq with color |

### Agent-safe non-rtk tools (install + call directly)

- `sd 'pattern' 'replacement' file` — in-place regex edits; PCRE2 dialect matches `rg`; no ANSI output. Use instead of `sed` for agent-driven file transforms.
- `mlr --ojson ...` — CSV/TSV/JSON tabular transforms; always pass `--ojson` or `--ocsv` for machine-readable output. Use for CRM exports, eval result CSVs, Azure cost data.
- `hyperfine --export-json results.json <cmd>` — benchmarks in CI/agent loops; always `--export-json`, never let it render the interactive progress bar to context.
- `yq -r '.key'` via `rtk proxy yq` — YAML config queries for Bicep params, Azure pipeline YAMLs.
- `jq -r` — already known-good; always `-r` (raw string) to suppress JSON quoting noise.

### Mandatory env contract for all agent subshells

```
NO_COLOR=1
BAT_STYLE=plain
GIT_PAGER=cat
PAGER=cat
```

Export these in the rtk execution environment and in `.env` for local Azure Functions dev.
They are defense-in-depth: rtk already strips ANSI, but tools invoked via `rtk proxy`
may bypass stripping.

### Explicitly FORBIDDEN in agent Bash calls

Never invoke: `eza` (icons/ANSI), `lsd`, `bat` (without plain flags), `delta`,
`btop`, `btm`, `broot`, `yazi`, `zellij`, `zoxide`/`z`, `fzf` (interactive mode),
`atuin`, `dust`, `duf`, `procs` (without `--color=never`), `xh` (without `--pretty=none`).
These emit ANSI, Unicode box-drawing, or TUI escape sequences that waste context tokens.
````

---

## 4. Human Install Set + Declarative Manifest

### 4a. Install manifest recommendation: **mise**

Use `mise` as the single declarative install manifest. It combines an **aqua-registry backend** (prebuilt binaries, no compile time, registry compiled into the mise binary) + a **cargo backend** (auto-uses `cargo-binstall` for speed) + language runtime management — covering all 20+ tools plus fd/sd/mlr in one TOML file.

- **aqua standalone** — viable if you want binary-only tooling with a simpler mental model, but mise is a strict superset (it embeds the aqua registry).
- **Nix / home-manager** — strongest reproducibility (flake.lock pins transitive store hashes), but significant WSL2 operational overhead for a single-dev setup. Overkill here.
- **Homebrew-on-Linux** — do NOT use. Separate prefix, own compiler toolchain (~500MB), no per-project pinning, documented WSL2 kernel-upgrade breakage.

Bootstrap:

```
curl https://mise.run | sh
echo 'eval "$(~/.local/bin/mise activate bash)"' >> ~/.bashrc
```

Declare all tools in `~/.config/mise/config.toml`. After any version edit: `mise install && mise lock` (generates `config.lock` with SHA256 checksums + download URLs). In CI / headless agent runs: `export MISE_LOCKED=1` for strict checksum-pinned reproducibility.

**Supply-chain rule:** pin every tool to an exact version (no `^`/`~`). `cargo-binstall` is a mise accelerator (`cargo.binstall=true`, already the default) — never use it as a standalone manifest (no lockfile/checksum format). Enable Renovate with a human review gate for bumps.

> Version numbers below are illustrative — verify with `mise registry` / crates.io before committing; aqua registry versions change frequently.

### 4b. Human-only install set

| Tool | Purpose (operator interactive shell only) | Install |
|---|---|---|
| **eza** | Rich ls — icons, git-status columns, tree | `mise install aqua:eza-community/eza@0.21.0` — then `alias ls='eza --icons --group-directories-first'` inside `[ -t 1 ]` guard |
| **bat** | Syntax-highlighted cat + line numbers | `mise install bat@0.25.0` — `alias cat='bat --paging=never'` in interactive shell; `BAT_STYLE=plain` in agent env |
| **delta** | Syntax-highlighted side-by-side git diffs | `mise install delta@0.18.3` — `~/.gitconfig`: `[core] pager = delta`, `[delta] side-by-side = true` |
| **zoxide** | Frecency cd (`z`) — interactive only (eval hooks) | `mise install aqua:ajeetdsouza/zoxide@0.9.7` — `eval "$(zoxide init bash --cmd cd)"` at END of `~/.bashrc`, interactive guard |
| **atuin** | Ctrl-R history + cross-machine sync (daemon) | `mise install aqua:atuinsh/atuin@18.4.0` — `eval "$(atuin init bash)"` AFTER fzf, inside `[[ $- == *i* ]]` guard |
| **fzf** | Interactive fuzzy picker (Ctrl-T/R, Alt-C) | `mise install aqua:junegunn/fzf@0.62.0` — `eval "$(fzf --bash)"` BEFORE atuin in interactive block |
| **btop** | Full-screen TUI resource monitor | `mise install aqua:aristocratos/btop@4.4.3` — launch as `btop`, no alias |
| **dust** | Visual du with bar charts | `mise install aqua:bootandy/dust@1.1.2` — `alias du='dust'` interactive |
| **duf** | Unicode-table df | `mise install duf@0.8.1` — `alias df='duf'` interactive |
| **procs** | Colored ps + process trees | `mise install cargo:procs@0.14.9` (or `cargo binstall procs`) |
| **yazi** | Async TUI file manager + image preview | `mise install aqua:sxyazi/yazi@25.4.8` — launch as `yazi` |
| **zellij** | Terminal multiplexer (WASM UI) — visual upgrade over tmux | `mise install aqua:zellij-org/zellij@0.42.2` — do NOT alias over tmux |
| **broot** | Interactive tree navigator | `mise install cargo:broot@1.44.0` — run once to gen config; keep out of agent PATH resolution |
| **xh** | Ergonomic HTTP client, colored JSON | `mise install aqua:ducaale/xh@0.23.0` — interactive only; `--pretty=none` if ever in agent context |
| **mlr** | CSV/TSV/JSON processor — ALSO dual-use (see §5) | `mise install aqua:johnkerl/miller@6.13.0` — agent: `mlr --ojson <verb> <file>` |

### 4c. Shell-init hook ordering (`~/.bashrc`, very end, interactive-guarded)

```bash
# --- interactive-only: load last ---
[[ $- == *i* ]] || return    # guard: skip in agent/cron sub-shells
eval "$(fzf --bash)"         # fzf keybindings FIRST
eval "$(atuin init bash)"    # atuin AFTER fzf — must win the Ctrl-R binding
eval "$(zoxide init bash --cmd cd)"  # zoxide aliases cd transparently
```

Ordering matters: atuin binds Ctrl-R and must load after fzf or fzf silently overrides it. The `[[ $- == *i* ]]` guard prevents agent/rtk/Azure-Functions-local sub-shells from sourcing TUI hooks that emit ANSI to stdout.

---

## 5. Dual-Use Tools with Project Tie-ins

| Tool | Agent invocation | Project tie-in |
|---|---|---|
| **hyperfine** | `hyperfine --export-json results.json <cmd>` — parse JSON with jq, never render the interactive bar | Verify library-choice decisions in seekapa training platform: polars vs pandas CSV ingest for eval processing, orjson vs stdlib json for CRM API response parsing, rg vs grep on the KB corpus in Azure Functions. |
| **sd** | `sd 'pattern' 'replacement' file` — PCRE2 (same as rg), no ANSI, safe direct call | Drive import migrations in seekapa codebase: `sd 'import pandas' 'import polars'` on data-pipeline files; `sd 'openai\.ChatCompletion' 'client.chat.completions'` for legacy OpenAI SDK calls in func-training / func-qc. |
| **mlr (miller)** | `mlr --ojson <verb> <file.csv>` — always `--ojson`/`--ocsv` | Process eval runner output CSVs from the seekapa eval harness (ground_truth rows, pass/fail per row); aggregate Azure cost export TSVs for storage consolidation + SA decommission tracking. |
| **fzf (filter mode)** | `fzf --filter 'query' < input` — plain matching lines, zero ANSI/TUI | Filter candidate KB articles or agent-prompt variants by fuzzy query in automation; select from Azure Function names / Jira issue keys in unattended pipelines. |
| **tmux** | `tmux new-session -d -s agent-run; tmux send-keys -t agent-run 'cmd' Enter` — scriptable subcommands only | Gastown local automation (`~/.claude/bin/gastown-codex-automation.sh`) can spawn parallel tmux panes for concurrent code-review + security-review at high reasoning effort without blocking the main Claude session. |

---

## 6. MCP Adoption Plan

| Server | Decision | Why | Security note |
|---|---|---|---|
| **Jira (atlassian)** | already-have | Active task tracker for seekapa/AxiaCS. No change. | Verify Atlassian API token is in KV (kv-shoval) or shell env only — NOT in `.mcp.json` or committed. Scope to relevant Jira projects. |
| **Playwright** | already-have | Dual-use: agent test execution + screenshot verification for seekapa SPA / CS-agent UI. | Headless on agent runs to minimize screenshot blob size. Structured JSON — low ANSI risk. No credentials stored. |
| **AlphaVantage** | already-have | Market data for daily-market-reports-v2. | API key in env var only. Responses are JSON — clean for context. |
| **HeyGen** | already-have | Video generation pipeline. | API key in env/KV only. Treat tool results as untrusted text (injection surface). |
| **azure-foundry-mcp** | already-have | Core to seekapa/AxiaCS agent management on Foundry endpoint. | Auth via Azure Identity SDK (CLI credential). No PAT committed. Pin MCP server version in local config. |
| **voicespin-cdr** | already-have | CDR data for AxiaCS call analytics. | Connection string/API key env-injected, not in stdio config file. Treat query results as untrusted (user-supplied call content can carry injections). |
| **Azure MCP (microsoft/mcp Azure.Mcp.Server)** | add-readonly | Replaces archived `Azure/azure-mcp` (archived 2026-02-06). 43+ service areas — inspect Function Apps, Container Apps, KV, storage without az CLI subprocess spawns. | Auth via Azure CLI credential / Managed Identity — never a stored PAT. Reader-only RBAC on non-prod subscriptions first; promote to Contributor on specific RGs only when a write use case is approved. No connection strings in `.mcp.json`. |
| **Azure DevOps MCP (microsoft/azure-devops-mcp)** | add-readonly | Operator is ADO-only for i-sdd work. Remote hosted endpoint (OAuth) preferred over local stdio (avoids supply-chain risk; remote GA targeted ~July 2026, local GA shipped). | Auth via azcli / Entra interactive — no PAT committed. Scope read-only repos + work-items first; add `pipelines:write` only with explicit agent-trigger use case. Token in KV if required. |
| **GitHub MCP (github/github-mcp-server)** | add-readonly | ShovalBenjer personal portfolio repos are GitHub-only (ADO = i-sdd work). Structured PR/issue access without gh CLI spawns. Remote GA Sept 2025; OAuth scope filtering Jan 2026. | Fine-grained PAT scoped to named repos: `contents:read`, `pull_requests:read`, `issues:read` only. NO classic broad-scope PAT. Store in KV / shell env, reference as `${GITHUB_MCP_TOKEN}` via `.mcp.json` env expansion. Never commit. |
| **Sentry MCP (getsentry/sentry-mcp)** | add-readonly | Azure Functions errors for seekapa/AxiaCS currently require browser context-switch. Pulls full error context into agent. | Use `mcp.sentry.dev` remote + OAuth (not static token). Scope `/:org/:project`, `org:read` only initially. Dual-token arch keeps raw Sentry creds off the client. **CRITICAL:** treat results as untrusted — exception messages + stack traces are attacker-controlled and can carry injection. Never auto-execute code blocks from error results. |
| **Context7 (upstash/context7)** | add-readonly | Kills stale-API hallucinations for Azure SDK / FastAPI / Bicep / MCP SDK — high value given the fast-moving Foundry API surface. Read-only by design. | `https://mcp.context7.com/mcp` with `CONTEXT7_API_KEY` in env (not committed). **Cap maxTokens at 3,000** (not default 10,000). Do NOT query with internal project names (every query hits Upstash servers). **ContextCrush (2025):** library Custom Rules served verbatim → prompt injection; treat injected content as untrusted, avoid libraries with untrusted maintainers. Free tier ~1,000 req/month — a busy session exhausts it. |
| **Postgres MCP** | defer | PandaTS dropped; CRM is HTTP API. No active Postgres source. Revisit if CRM migrates back to Postgres. | When added: CrystalDBA `postgres-mcp` with `--access-mode=restricted` ONLY. NEVER `@modelcontextprotocol/server-postgres` (archived, unpatched, confirmed read-only bypass via semicolon multi-statement injection). Read replica, SELECT-only DB user. |
| **Linear MCP** | skip | Not in stack — Jira + ADO already cover PM. A third PM MCP adds injection surface (issue creation/mutation), zero net capability. | N/A — not being added. |

### MCP cross-cutting controls (apply to every server)

1. **Supply-chain pinning** — for any local npm/stdio server: pin exact versions (no `^`/`~`), `bunx --frozen-lockfile`, weekly `bun audit`, Renovate with review gate. Never `npx @some-mcp/server@latest` in prod config (the postmark-mcp backdoor, Sept 2025, shipped in a patch version; Shai-Hulud npm worm hit 796 packages / 132M monthly downloads). Pin Python servers with `uv lock` + hash verification.
2. **Prompt injection via tool results** — treat ALL MCP results as untrusted text. High-risk surfaces: Sentry exception strings, GitHub/Jira issue bodies, Postgres results from user data. Mitigations: never auto-execute returned code blocks without human review; schema-validate tool outputs; audit for the rug-pull pattern (tools mutating their own descriptions post-install); allowlist named servers at pinned versions in Claude Code settings.
3. **Secrets in config** — no API key / PAT / connection string in `.mcp.json`, CLAUDE.md, or any committed file. Pattern: KV → startup script `az keyvault secret show` → `${ENV_VAR}` expansion in `.mcp.json`. Add `gitleaks` / `detect-secrets` pre-commit hook (Token Security telemetry: 20% of Claude-Code endpoints have hardcoded secrets in MCP config).

---

## 7. rtk Custom-Filter Ideas

`~/.config/rtk/filters.toml` is currently empty. These target the noisiest token sources in this stack.

- **`[filters.az]`** — Azure CLI: strip ANSI progress spinners + "Waiting for..." polling lines; collapse ARM deployment-status poll output to one summary line per resource; strip `\` continuation lines in `az deployment what-if`; `max_lines=60`. Trigger: `match_command='^az\b'`
- **`[filters.func]`** — Functions Core Tools: strip startup ASCII banner; suppress "Host initialized" / "Worker process started" INFO; collapse repeated "Executing HTTP request" lines to a count; keep WARN/ERROR verbatim; `max_lines=80`. Trigger: `match_command='^func\b'`
- **`[filters.bicep]`** — Bicep CLI: strip non-actionable experimental-feature WARNINGs; collapse "Compiling..." lines; keep ERROR verbatim. Trigger: `match_command='^(az bicep|bicep)\b'`
- **`[filters.azd]`** — Azure Developer CLI: strip spinner/progress animation frames; suppress duplicate "Initializing/Packaging services..." status; keep ERROR + "Deployment complete". Trigger: `match_command='^azd\b'`
- **`[filters.pytest]`** — strip the session-start header + platform block; suppress PASSED (keep FAILED/ERROR/WARNING); collapse parametrize IDs to count on passing suites; keep full failure tracebacks; `max_lines=100`. Trigger: `match_command='^(pytest|uv run pytest|python -m pytest)\b'`
- **`[filters.ruff]`** — strip "All checks passed!" / "Found 0 fixable"; on errors collapse by rule code (`E501: 12 in src/`) not per-line; strip `--watch` progress bars. Trigger: `match_command='^(ruff|uv run ruff)\b'`
- **`[filters.mypy]`** — suppress "Success: no issues found" when clean; group errors by file (`file:count` summary first); strip the redundant "Found N errors in M files" footer. Trigger: `match_command='^(mypy|uv run mypy|python -m mypy)\b'`
- **`[filters.bun-test]`** — strip passing test lines (keep FAIL/SKIP/ERROR); suppress "bun test v..." header; collapse passing files to a count; keep full failure output. Trigger: `match_command='^bun test\b'`

---

## 8. Phased Rollout + Ranked Top Actions

### Phased rollout

- **Phase 1 (day 1, ~2h) — Agent shell contract hardening.** Export `NO_COLOR=1` + `BAT_STYLE=plain` + `GIT_PAGER=cat` + `PAGER=cat` in the rtk execution environment and `.env` for local Functions dev. Add rtk filters for `az`, `func`, `ruff`, `pytest` to the (empty) `~/.config/rtk/filters.toml`. Verify with `rtk gain` after a typical `az deployment what-if` run.
- **Phase 2 (day 1-2, ~1h) — Agent-facing tools.** `mise install` sd (`cargo:sd`), mlr (`aqua:johnkerl/miller`), hyperfine (`aqua:sharkdp/hyperfine`). Zero ANSI risk, immediate project use.
- **Phase 3 (day 2-3, ~2h) — Human-facing operator tools.** `mise install` eza, bat, delta, fzf, zoxide, atuin, xh, dust, duf, procs, btop, yazi, zellij, broot. Wire interactive hooks with `[[ $- == *i* ]]` guards. Set delta as git pager. Alias ls→eza / cat→bat inside `[ -t 1 ]` guards only.
- **Phase 4 (day 3-4, ~1h each) — MCP read-only additions, validate each before next.** (a) Azure MCP + Reader RBAC via CLI credential; (b) GitHub MCP + fine-grained PAT in kv-shoval; (c) Azure DevOps MCP remote + Entra auth.
- **Phase 5 (day 4-5, ~1h each) — Remaining MCP.** (a) Context7, `CONTEXT7_API_KEY` in env, maxTokens=3000, injection awareness documented in CLAUDE.md; (b) Sentry MCP via `mcp.sentry.dev` OAuth, `org:read` on seekapa/AxiaCS. Add rtk filters for mypy + bun-test.
- **Phase 6 (ongoing).** Add rtk filters for azd + bicep after first use on the modernization branch. `rtk cc-economics` weekly to track token savings. Review `mise.lock` monthly; Renovate with human review gate.

### Ranked top actions

1. **Export `NO_COLOR=1` + `PAGER=cat` + `GIT_PAGER=cat` in agent env** — highest leverage, zero install, kills ANSI token waste across all conforming tools.
2. **Populate `~/.config/rtk/filters.toml` with az/func/pytest/ruff filters** — the tool exists and is empty; az deploys + pytest are the noisiest token sources today.
3. **Install sd** (`cargo:sd`) — immediate use for seekapa import migrations; PCRE2 parity with rg cuts agent prompt overhead.
4. **Install mlr** (`aqua:johnkerl/miller`) — unblocks eval-CSV aggregation + Azure cost export processing that jq can't do.
5. **Add Azure MCP + Reader RBAC** — replaces archived azure-mcp; kills az CLI spawns for Function App / Container App inspection.
6. **Add GitHub MCP + fine-grained read-only PAT** — structured PR/issue access for portfolio repos without gh CLI spawns.
7. **Install hyperfine** — agent-driven CI perf-regression loops; clean `--export-json` output.
8. **Add Sentry MCP via OAuth (`org:read`)** — removes browser context-switch for AxiaCS/seekapa error triage.
9. **Add Context7 MCP, maxTokens=3000** — kills Azure SDK / Bicep / FastAPI stale-API hallucinations; cap guards token budget.
10. **Install operator tools (eza/bat/delta/fzf/zoxide/atuin) with interactive guards** — human ergonomics; zero agent risk if guards are correct.

---

## 9. References (deduplicated)

**Agent context cost / NO_COLOR**
- AI Agent Loop Token Costs — Augment Code — https://www.augmentcode.com/guides/ai-agent-loop-token-cost-context-constraints
- NO_COLOR — https://no-color.org/

**CLI tools**
- fd — https://github.com/sharkdp/fd
- ripgrep is faster than {grep, ag, ...} — BurntSushi — https://burntsushi.net/ripgrep/
- ripgrep Benchmarks — https://ripgrep.dev/benchmarks/
- sd — https://github.com/chmln/sd
- Miller — https://github.com/johnkerl/miller
- yq — https://github.com/mikefarah/yq
- hyperfine — https://github.com/sharkdp/hyperfine
- eza — https://github.com/eza-community/eza
- bat — https://github.com/sharkdp/bat (+ flags: https://32blog.com/en/cli/cli-modern-rust-tools)
- delta — https://github.com/dandavison/delta
- btop — https://github.com/aristocratos/btop
- zoxide — https://github.com/ajeetdsouza/zoxide
- atuin — https://docs.atuin.sh/cli/guide/shell-integration/
- fzf shell integration — https://junegunn.github.io/fzf/shell-integration/
- yazi — https://github.com/sxyazi/yazi
- zellij — https://github.com/zellij-org/zellij
- xh — https://github.com/ducaale/xh
- curl vs httpie — Daniel Stenberg — https://daniel.haxx.se/docs/curl-vs-httpie.html
- eza man page (--color/--icons) — https://manpages.ubuntu.com/manpages/questing/man1/eza.1.html

**Install wiring**
- mise Getting Started — https://mise.jdx.dev/getting-started.html
- mise Lockfiles / Reproducibility — https://deepwiki.com/jdx/mise/6.7-lockfiles-and-reproducibility
- mise Aqua Backend — https://mise.jdx.dev/dev-tools/backends/aqua.html
- mise Cargo Backend — https://mise.jdx.dev/dev-tools/backends/cargo.html
- aqua — https://github.com/aquaproj/aqua (+ docs: https://aquaproj.github.io/docs/tutorial/)
- cargo-binstall — https://github.com/cargo-bins/cargo-binstall
- mise vs Homebrew (Lobsters) — https://lobste.rs/s/otlxxz/tools_i_love_mise_en_place
- mise tool version management (Jan 2026) — https://oneuptime.com/blog/post/2026-01-25-mise-tool-version-management/view
- Nix Download — https://nixos.org/download/
- Home Manager Manual — https://nix-community.github.io/home-manager/
- Reproducible dev-env with Nix on WSL — https://yashgarg.dev/posts/nix-devenv/

**Terminal multiplexing (agents)**
- tmux vs Termdock vs Zellij for AI Agents — https://www.termdock.com/en/blog/terminal-multiplexing-tmux-termdock-zellij

**MCP servers**
- Best MCP Servers for Developers in 2026 — builder.io — https://www.builder.io/blog/best-mcp-servers-2026
- microsoft/mcp Azure.Mcp.Server — https://github.com/microsoft/mcp/tree/main/servers/Azure.Mcp.Server
- Azure MCP Server in Visual Studio 2026 — https://devblogs.microsoft.com/visualstudio/azure-mcp-server-now-built-in-with-visual-studio-2026-a-new-era-for-agentic-workflows/
- Azure DevOps Remote MCP (preview) — https://devblogs.microsoft.com/devops/azure-devops-remote-mcp-server-public-preview/
- ADO MCP Preview → GA — InfoQ — https://www.infoq.com/news/2025/11/microsoft-ado-mcp-server/
- GitHub MCP OAuth scope filtering — https://github.blog/changelog/2026-01-28-github-mcp-server-new-projects-tools-oauth-scope-filtering-and-new-features/
- Remote GitHub MCP GA — https://github.blog/changelog/2025-09-04-remote-github-mcp-server-is-now-generally-available/
- crystaldba/postgres-mcp — https://github.com/crystaldba/postgres-mcp
- Postgres MCP read-only bypass review — https://chatforest.com/reviews/postgres-mcp-server/
- getsentry/sentry-mcp security.md — https://github.com/getsentry/sentry-mcp/blob/main/docs/security.md
- Sentry remote endpoint — https://mcp.sentry.dev/
- Context7 MCP (Upstash blog) — https://upstash.com/blog/context7-mcp
- upstash/context7 — https://github.com/upstash/context7
- ContextCrush (Context7 vulnerability) — Noma Security — https://noma.security/blog/contextcrush-context7-the-mcp-server-vulnerability/
- Context7 / Playwright ranking — PulseMCP — https://www.pulsemcp.com/servers/upstash-context7
- Linear MCP — https://linear.app/changelog/2025-05-01-mcp
- Atlassian MCP — https://www.atlassian.com/platform/marketplace/apps/1234987-atlassian-mcp

**MCP security / supply chain**
- MCP Security 2026: Tool Poisoning, Rug-Pulls, npm Meltdown — Glasp — https://glasp.co/articles/mcp-security-tool-poisoning-supply-chain
- Typosquatted npm packages steal CI/CD secrets — Microsoft Security Blog — https://www.microsoft.com/en-us/security/blog/2026/05/28/typosquatted-npm-packages-used-steal-cloud-ci-cd-secrets/
- MCP Connector Poisoning — https://earezki.com/ai-news/2026-04-04-mcp-connector-poisoning-how-compromised-npm-packages-hijack-your-ai-agent/
- Prompt Injection via MCP Sampling — Palo Alto Unit 42 — https://unit42.paloaltonetworks.com/model-context-protocol-attack-vectors/
- MCP has prompt injection problems — Simon Willison — https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/
- MCP-38 Threat Taxonomy — https://arxiv.org/pdf/2603.18063
- Stop exposing secrets in MCP configs — Token Security — https://www.token.security/blog/how-to-stop-exposing-secrets-on-your-mcp-configs
- Preventing MCP token mismanagement — Will Velida — https://www.willvelida.com/posts/preventing-mcp01-token-mismanagement-secret-exposure/

---

## Appendix: Caveats & Unverified Claims

- Tool version numbers in §4 are illustrative — verify with `mise registry` / crates.io before committing; aqua registry versions change frequently.
- aqua registry tool count (~399) is from a 2024 doc excerpt; likely higher mid-2026.
- `btop --no-tty` ANSI-disable came from a forum post, not the official man page — verify with `btop --help`.
- mise "ubi backend deprecated" came from a search snippet — verify at mise.jdx.dev before relying on it.
- Linear MCP exact OAuth 2.1 flow (DCR/PKCE) not fully confirmed from the changelog.
- Context7 free-tier reduction (6,000 → 1,000 req/month, Jan 2026) is a single secondary source (ChatForest), not an official Upstash announcement.
- Token Security "20% of endpoints have hardcoded secrets" — customer telemetry, methodology/sample size not disclosed.
- Remote Azure DevOps MCP GA date (~July 2026) is a blog comment, not a committed Microsoft date.
- Atlassian MCP URL is a marketplace-format placeholder, not directly fetched/verified.
- xh "30% faster than HTTPie" refers to startup vs Python HTTPie, not vs curl; no primary source vs curl.
