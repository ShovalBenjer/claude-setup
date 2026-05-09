# Skills Triage — Used / Unused / Missing / Redundant

> **APPENDIX NOTE (2026-05-04):** This is a per-skill triage feeding into the canonical plan. **For current status and decisions see `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`.** Master plan §14.1 has the merge checklist for the 6 redundant pairs. Use this file when executing the actual moves.

**Date:** 2026-05-03
**Backup:** `~/dotfiles-backup-2026-05-03.tar.gz` (981MB, 1583 files — includes Codex sqlite log)
**Scope:** All 94 SKILL.md files across `.agents/`, `.codex/`, `cs-agent/.agents/`, `figma-4-all/.codex/`. Decision: what merges to `~/.dotfiles/skills/`, what archives, what gets built new.

---

## Triage table

Legend: **KEEP-G** = move to `~/.dotfiles/skills/` (global), **KEEP-P** = stay at project level, **ARCHIVE** = move to `~/archive/skills-deprecated-2026-05-03/`, **MERGE** = redundant duplicate, pick canonical, **NEW** = doesn't exist, build from scratch.

### Tier 1 — Active and high-value (KEEP-G)

These are referenced in `AGENTS.md` trigger policy, called by hooks, or map to the 2030 vision Layer 3/4. **No-brainer keeps.**

| Skill | Source | Decision | Notes |
|---|---|---|---|
| voice-explainer | .codex | KEEP-G | Called by `~/.claude/hooks/voice-explainer-trigger.sh` — must move with the hook |
| visual-explainer | .codex | KEEP-G | Same — paired with the visual hook |
| commit-push-pr | .codex + .agents + ~/.claude/commands | **MERGE** (3 copies!) | Diff all three; expect `.agents` is most current; canonical → `~/.dotfiles/skills/`; symlink `~/.claude/commands/commit-push-pr.md` to it |
| mcp-activation | .codex | KEEP-G | Per-session MCP gate — listed in AGENTS.md |
| azure-keyvault-secrets | .codex + .agents | **MERGE** | Both exist; diff, pick canonical |
| azure-devops | .codex + .agents | **MERGE** | Same |
| cleanup-crew | .codex (also figma) | KEEP-G | Drop the figma copy (project-level dup of global skill) |
| code-simplifier | .codex (also figma) | KEEP-G | Drop figma copy |
| eval-runner | .codex (also figma) | KEEP-G | Drop figma copy. **High value for Seekapa.** |
| kill-stale | .codex (also figma) | KEEP-G | Drop figma copy |
| mutation-runner | .codex + .agents (also figma) | **MERGE** | 3 copies; diff `.agents` vs `.codex`, drop figma |
| ops-status | .codex (also figma) | KEEP-G | Drop figma copy |
| property-test-gen | .codex + .agents (also figma) | **MERGE** | 3 copies |
| red-team | .codex + .agents | **MERGE** | Both exist |
| red-team-review | .codex (also figma) | KEEP-G | Drop figma copy |
| triage-tests | .codex (also figma) | KEEP-G | Drop figma copy |
| watchdog | .codex (also figma) | KEEP-G | Drop figma copy |
| web-inspect | .codex (also figma) | KEEP-G | Drop figma copy |
| workspace-brain | .codex (also figma) | KEEP-G | Drop figma copy |
| apify-mcp | .codex | KEEP-G | |
| heygen-mcp | .codex | KEEP-G | |
| elevenlabs-mcp | .codex | KEEP-G | Used by voice-explainer pipeline |
| feature-investor | .codex | KEEP-G | 2026 SOTA feature gating — useful for Seekapa work |
| memory-curator | .agents | KEEP-G | **Layer 3 priority** — runs ACE pipeline post-session. Single most-important subagent in the 2030 vision. |
| agent-team | .agents | KEEP-G | Multi-agent coordination protocol — Layer 3 backbone |
| deep-research | .agents | KEEP-G | Already in your active vocabulary ("/deep-research it") |
| obsidian-vault | .agents | KEEP-G | Pairs with planned `claude-obsidian` install |
| azure-foundry | .agents | KEEP-G | **Critical** — you said you want Azure Foundry CLI. This is the existing skill; needs upgrade (see Tier 4 below). |
| azd | .agents | KEEP-G | Azure Developer CLI workflow — aligns with Foundry/Microsoft Agent 365 push |
| azure-wiki-onepager | .agents | KEEP-G | i-sdd specific (you have an Azure Wiki) — keep |
| shoval-voice-draft | .codex | KEEP-G | Drafts in your work style — useful for i-sdd messages |
| humanize | .agents | KEEP-G | De-AI text — useful for any external comms |
| caveman | .agents | KEEP-G | 75% token compression mode. Tiny file, no cost to keep. |
| review | .agents | KEEP-G | Multi-layer code review (combines red-team + heidegger + ci) — high-leverage |
| end-session | .agents | KEEP-G | Security wipe + post-mortem — important for credential hygiene |
| context-hygiene | .agents | KEEP-G | Detects bloat across `~/.codex/`, `~/projects/*` — exactly what we just did manually here |
| context-i-forgot | .agents | KEEP-G | Mid-session injection helper |
| reground | .agents | KEEP-G | Full context reload — useful after long sessions |

**Subtotal Tier 1: ~37 skills KEEP-G, with 6 MERGE pairs to resolve.**

### Tier 2 — Domain & workflow utilities (KEEP-G, lower priority)

Useful, occasional triggers. Keep but not on the critical path.

| Skill | Source | Decision | Notes |
|---|---|---|---|
| zoom-out | .agents | KEEP-G | Step-back perspective tool |
| brainstorming | .agents | KEEP-G | Pre-creative-work alignment |
| grill-me | .agents | KEEP-G | Interview-to-alignment |
| domain-model | .agents | KEEP-G | DDD grilling |
| ubiquitous-language | .agents | KEEP-G | DDD glossary extraction |
| to-prd | .agents | KEEP-G | Conversation → PRD |
| to-issues | .agents | KEEP-G | Plan → tracked work items |
| triage-issue | .agents | KEEP-G | Bug → root cause + work item |
| github-triage | .agents | KEEP-G | Label-based state machine — usable now that we're activating GitHub |
| improve-codebase-architecture | .agents | KEEP-G | Architecture deepening (overlaps with planned `architecture-review` subagent — could merge) |
| request-refactor-plan | .agents | KEEP-G | Tiny-commit refactor planning |
| pre-ship-clean | .agents | KEEP-G | Dead-code audit + .gitignore hardening |
| deploy-prod | .agents | KEEP-G | Pre-flight checklist |
| project-intake | .agents | KEEP-G | New-project onboarding gate |
| project-state | .agents | KEEP-G | Status.json + handover protocol — overlaps with memory-curator slightly |
| plant-task | .agents | KEEP-G | Future-session TODO injection |
| tdd | .agents | KEEP-G | Red-green-refactor enforcer |
| setup-pre-commit | .agents | KEEP-G | Husky + lint-staged setup |
| frontend-design | .agents | KEEP-G | Anti-slop UI constraints |
| design-an-interface | .agents | KEEP-G | Parallel UI variant generation |
| codex-ci | .agents | KEEP-G | CI fix/review loop (rename to `ai-ci` once we're cross-CLI) |
| answer-question | .agents | KEEP-G | Read-only research mode |
| quick-respond | .agents | KEEP-G | One-shot answer, no verify |
| qa | .agents | KEEP-G | Conversational bug intake → work item |
| edit-article | .agents | KEEP-G | Article editing (matches your research markdown habit) |
| notebook | .agents | KEEP-G | Polars/Numba/Plotly notebook scaffold — useful for the planned Windsor analytics work |
| scaffold-exercises | .agents | KEEP-G | Exercise dir generator (low-priority for current work) |
| write-a-skill | .agents | KEEP-G | Meta-skill — needed before building anything new |
| git-guardrails-claude-code | .agents | KEEP-G | But: review against the proposed Claude `PreToolUse` hook plan — likely overlap |

**Subtotal Tier 2: ~28 skills KEEP-G.**

### Tier 3 — Archive (low value or stale)

| Skill | Source | Decision | Why |
|---|---|---|---|
| meme-control | .agents | ARCHIVE | Toggles Codex meme playback. Not part of professional setup. |
| migrate-to-shoehorn | .agents | ARCHIVE | TS-specific (`@total-typescript/shoehorn`). Seekapa is Python — not relevant. |
| heidegger-reflection.md | .codex (stray file) | ARCHIVE | Stray `.md` at `.codex/skills/` root, NOT in a subdir. Duplicate of `.agents/heidegger-reflect/SKILL.md`. |
| heidegger-reflect | .agents | KEEP-G *or* ARCHIVE | Keep one canonical; if you don't actively use it, archive. Your call. |
| friday-meeting/skills/skills/ (20 skills) | extracted from .zip | ARCHIVE entire dir | All are subsets of `.codex/skills/` already. `mv ~/friday-meeting ~/archive/`. |
| ~/.codex/migrated-from-claude/ | frozen Claude config | ARCHIVE | Pre-Codex migration snapshot, no longer relevant |

### Tier 4 — Project-scope (KEEP-P, stay at project level)

| Skill | Location | Notes |
|---|---|---|
| claude-eval-cs | `~/projects/cs-agent/.agents/skills/` | Seekapa/Axia eval runner — project-specific, stays put |
| banner-analyzer | `~/projects/figma-4-all/.codex/skills/` | Figma-specific — stays put |

The other 14 skills in `figma-4-all/.codex/skills/` are duplicates of globals — drop after global consolidation.

### Tier 5 — MISSING (referenced but not present, BROKEN refs) — UPDATED 2026-05-03

These are bugs in your current setup — `AGENTS.md` mentions them but the SKILL.md doesn't exist anywhere I can find.

| Skill | Referenced at | Status | Fix |
|---|---|---|---|
| **playwright-cli** | `~/AGENTS.md` line 24 | **NOT FOUND** in any skills dir | Write SKILL.md targeting **Obscura** (see Tier 5b below) |
| **playwright-mcp** | `~/AGENTS.md` line 25 | **NOT FOUND** in any skills dir | Write SKILL.md, but split: Obscura for general scraping + **MS Edge (Windows-side) for domain apps** (see Tier 5b) |
| **perplexity-mcp** | `~/AGENTS.md` line 22 — listed as `~/.codex/skills/perplexity-mcp/SKILL.md` | Only exists at `~/projects/figma-4-all/.codex/skills/perplexity-mcp/` | Promote to global: move to `~/.dotfiles/skills/perplexity-mcp/`. |

### Tier 5b — Playwright wiring plan (Obscura + Edge dual setup)

User clarified the intent:
- **`playwright-cli` skill → Obscura** (the optimized stealth Chromium fork, already installed)
- **`playwright-mcp` → routed to MS Edge on Windows side** for domain/corporate apps (Entra ID SSO, Windows Hello, domain-joined SaaS)

#### What's already in place

| Component | Path | What it does |
|---|---|---|
| Obscura binary | `~/.local/bin/obscura` (77MB ELF) | Stealth Chromium fork, native Linux |
| Obscura CDP launcher | `~/.codex/bin/obscura-cdp` | start/status/stop/restart on `127.0.0.1:9222` |
| Playwright MCP wrapper | `~/.codex/bin/playwright-mcp-obscura` | Boots Obscura then launches `@playwright/mcp@latest --cdp-endpoint=...` |
| Existing `.mcp.json` entry | `~/.mcp.json` | `playwright` MCP currently points at the Obscura wrapper, lazy-loaded, autoEnable=false |

#### What's missing

1. **`playwright-cli` SKILL.md** — needs to instruct Claude/Codex to call Obscura via CLI (not MCP) for ad-hoc scrapes, screenshots, etc. Should reference `~/.local/bin/obscura` directly + the `obscura-cdp` start/stop helpers.

2. **Second MCP entry: `playwright-edge`** — for domain apps that require Windows-side authentication. Today the MCP only knows Obscura. Add a parallel MCP that connects to MS Edge running on Windows via CDP.

3. **MS Edge CDP launcher** — does not exist yet. Needs a small WSL script that:
   - Detects whether Edge is already running with `--remote-debugging-port=9223` on Windows
   - If not, launches Edge with that flag (`/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1`)
   - Returns the WSL-reachable endpoint (typically Windows host IP from `/etc/resolv.conf` or `cat /proc/sys/net/ipv4/conf/eth0/address`'s default gateway)
   - Health-checks `http://${WIN_HOST}:9223/json/version`

#### Proposed `.mcp.json` after the change

```json
{
  "mcpServers": {
    "playwright": {
      "command": "/home/shovalbe/.codex/bin/playwright-mcp-obscura",
      "description": "Obscura (stealth Chromium) on Linux side. General scraping, public web, anti-bot.",
      "lazyLoad": true,
      "toolSearch": { "enabled": true, "keywords": ["playwright","obscura","stealth","scrape","public-web"] },
      "autoEnable": false
    },
    "playwright-edge": {
      "command": "/home/shovalbe/.codex/bin/playwright-mcp-edge",
      "description": "MS Edge on Windows host. Domain apps, Entra ID SSO, Windows Hello, internal SaaS.",
      "lazyLoad": true,
      "toolSearch": { "enabled": true, "keywords": ["playwright","edge","domain","entra","sso","corp","internal"] },
      "autoEnable": false
    }
  }
}
```

#### Proposed `~/.codex/bin/playwright-mcp-edge` (sketch)

```bash
#!/usr/bin/env bash
set -euo pipefail
WIN_HOST="$(ip route show default | awk '{print $3}')"   # WSL2 host gateway
PORT="${EDGE_CDP_PORT:-9223}"
ENDPOINT="http://${WIN_HOST}:${PORT}"

# Health-check; if dead, prompt user to launch Edge manually with the right flag
if ! curl -fsS --max-time 1 "${ENDPOINT}/json/version" >/dev/null 2>&1; then
  echo "Edge CDP not reachable at ${ENDPOINT}." >&2
  echo "On Windows host, run:" >&2
  echo '  "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9223 --remote-debugging-address=0.0.0.0' >&2
  exit 1
fi

exec bunx -y @playwright/mcp@latest "--cdp-endpoint=${ENDPOINT}" "$@"
```

> **Note:** binding Edge to `0.0.0.0` opens CDP to anyone on your machine — fine on a single-user dev box, NOT fine on a shared host. If you're nervous, use SSH tunneling or `socat` from `127.0.0.1:9223` on Windows to WSL instead. Document this in the SKILL.md.

#### Proposed `playwright-cli` skill body (sketch)

```yaml
---
name: playwright-cli
description: Headed/headless browser automation via Obscura (stealth Chromium) for general scraping. Use for public web, screenshot capture, login flows that don't need domain auth.
allowed-tools: ["Bash(/home/shovalbe/.local/bin/obscura *)", "Bash(/home/shovalbe/.codex/bin/obscura-cdp *)"]
---

Always start with `obscura-cdp start` (idempotent — health-checks first). For domain/corporate
apps requiring Entra/SSO, use `playwright-mcp` server `playwright-edge` instead, NOT this skill.
```

### Tier 5c — Hidden agents I missed in the first scan

The first scan only looked for `*.md` agents. I missed JSON agents and project-source agents. Here's the full picture:

| Location | Count | Format | What |
|---|---|---|---|
| **`~/projects/social-intelligence-unit/.kilocode/agents/`** | **24** | Kilocode JSON | The most complete subagent fleet you have anywhere — and you're not loading it from Claude. See list below. |
| `~/friday-meeting/agents/` | 2 | Markdown | `code-reviewer.md`, `doc-compactor.md` (plus duplicate at `agents/agents/`) |
| `~/projects/campaign-analysis/agents/` | 2 | system_prompt.txt | `call_quality_agent`, `market_intel_agent` (domain-specific, project-scope) |
| `~/projects/social-intelligence-unit/src/siu/agents/` | — | Python source | `definitions.py`, `workflow.py`, `tools.py` — runtime SIU agents, not Claude config |
| `~/.openclaw/workspace/` | 1 | Markdown | Has its own `AGENTS.md`, `IDENTITY.md`, `BOOTSTRAP.md`, `SOUL.md`, `TOOLS.md` — separate runtime (Telegram bot on Foundry GPT-5.2 per `~/projects/openclaw-poc/README.md`) |

#### The SIU 24-agent fleet (this is the gold mine)

```
chaos-tester        concurrency-tester    contract-tester     e2e-tester
fuzz-tester         integration-tester    mutation-tester     performance-tester
property-tester     regression-tester     scalability-tester  unit-tester
test-generator      red-team              code-reviewer       style-enforcer
sota-documenter     context-compactor     history-cleaner     file-organizer
frontend-specialist implementer           orchestrator        planner
```

This **is** the subagent fleet the 2030 vision doc recommends. You already built it — for Kilocode, in JSON format. **The 2030-vision Tier 6 list ("MISSING for the 2030 vision") needs revision: most of those subagents already exist as Kilocode agents. They just need format-conversion to Claude `.md` frontmatter.**

#### Format conversion pattern (Kilocode JSON → Claude markdown)

Kilocode JSON looks like:
```json
{ "name": "code-reviewer", "role": "Tech Lead / Code Reviewer", ... }
```

Claude expects:
```yaml
---
name: code-reviewer
description: <one-line task>
tools: [Read, Grep, Bash]
permissions: read-only
memory: project
---

<role + instructions>
```

A small `kilocode-to-claude.py` converter script could batch-port all 24 in one pass. **Recommend doing this AS PART OF the consolidation** — these 24 agents are the highest-value content discovered so far.

### Tier 5d — Parallel-project context (you're running 6+ Claude sessions concurrently)

Recent history (`~/.claude/history.jsonl` last 50 entries) shows active sessions in:

- `/home/shovalbe` — this session, orchestration / setup planning
- `/home/shovalbe/projects/seekapa-training-platform` — Postgres migrations + Key Vault firewall work
- `/home/shovalbe/projects/cs-agent` — PR work (`/review`, `/commit-push-pr`, "Full broader scope in pr")
- `/home/shovalbe/projects/azure-devops-agent` — separate agent project
- `/home/shovalbe/projects/campaign-analysis` — Meta Ads CLI/MCP exploration ("is there MCP writes actions that is not handled by windsor?", "Not claude, but my foundry agents. we can wrap it with OPENclaude + gpt 5.5")
- `/home/shovalbe/projects/campaign-analysis/runs/whatsapp-analysis` — child run
- `/home/shovalbe/projects/qc` — qc/qc-telephony-api

Implications for the consolidation plan:
1. **Symlink resolution must be safe under concurrent reads** — 6 Claude processes all tail-following `~/.dotfiles/skills/` simultaneously is fine for reads but introduces a race during the symlink swap. Migration should happen during a quiet window, or use atomic rename: `mv -T newlink oldlink`.
2. **Per-project `CLAUDE.md` matters more than I sized** — each of the 6 active projects has its own context Claude is loading. Reconciling the 4 diverged `CLAUDE.md`/`AGENTS.md` pairs becomes high-priority, not low-priority.
3. **The cs-agent project has TWO worktrees** (`axia-seekapa-cs-agents/` and `axia-seekapa-cs-agents-devops/`), each with its own `.claude/`. Worth one careful pass to sync them or document the divergence.

### Tier 5e — OpenClaw / OpenClaude (separate runtime, NOT Claude Code config)

Per recent history: *"Not claude, but my foundry agents. we can wrap it with OPENclaude + gpt 5.5 https://github.com/Gitlawb/openclaude for the server."*

- `~/.openclaw/workspace/` — runtime workspace with `AGENTS.md`, `IDENTITY.md`, `BOOTSTRAP.md`, `SOUL.md`, `TOOLS.md`, `USER.md`, `HEARTBEAT.md`
- `~/projects/openclaw-poc/` — Telegram bot on Foundry GPT-5.2, deployed to Azure Container Apps. Composio wiring deferred to iteration 2.
- Plan (per user): wrap Foundry agents with OpenClaude (Gitlawb/openclaude) + GPT-5.5 — separate from Claude Code setup; do not include in `~/.dotfiles/`.

This belongs in the master plan as a **parallel agent runtime**, not part of Claude Code's skill/hook layer. Mentioned here so we don't accidentally try to consolidate it.

### Tier 6 — MISSING for the 2030 vision (REVISED 2026-05-03)

Original list assumed nothing existed. After Tier 5c discovery, most subagents **already exist as Kilocode JSON in SIU** — they just need conversion to Claude format.

| Item | Type | Status (revised) |
|---|---|---|
| security-reviewer | subagent | Partial — SIU has `red-team.json` (offensive) but no defensive `security-reviewer`. Build new. |
| test-writer | subagent | **Exists as `test-generator.json` in SIU** — convert to Claude format |
| performance-auditor | subagent | **Exists as `performance-tester.json` + `scalability-tester.json` in SIU** — convert |
| dep-watcher | subagent | Build new — not in SIU set |
| coverage-gap-detector | skill | Build new — Layer 7 keystone, no equivalent in SIU |
| semantic-commit | skill | Merge into `commit-push-pr` (don't build separately) |
| architecture-review | subagent | Partial — `style-enforcer.json` and `sota-documenter.json` cover parts; `improve-codebase-architecture` skill covers other parts. Reconcile. |
| `/spawn-team` | slash command | Build new — wraps `agent-team` skill + new `orchestrator.json` |
| `/consolidate-memory` | slash command | Build new — triggers `memory-curator` skill |
| `/coverage-map` | slash command | Build new — triggers coverage-gap-detector |
| **NEW: convert SIU agents** | 24 subagents | Port `~/projects/social-intelligence-unit/.kilocode/agents/*.json` → `~/.dotfiles/agents/*.md`. Highest-leverage single move on the entire plan. |

### Tier 7 — MISSING for stated user goals (NEW)

| Item | Why | Source |
|---|---|---|
| **microsoft-agent-365** skill + MCP | User explicitly asked. Needs research: official Microsoft 365 Agents SDK / Copilot Studio CLI / `.NET Aspire` agents. Probably wraps the MS Graph API + agent registration. | User request 2026-05-03 |
| **azure-foundry-cli** skill (replaces existing `azure-foundry` skill body) | The current `azure-foundry` skill is MCP-based. User wants CLI-first. The Foundry CLI exists (`az ai`/`az cognitiveservices`), but a wrapper skill that knows your specific seekapa_ai project + endpoint pattern doesn't exist. | User request 2026-05-03 |
| **gh CLI** (system-level, not a skill) | Required for GitHub flow + commit-push-pr GitHub branch | Master plan Part 4 |

---

## Redundancy resolution checklist

The 6 skills with `.agents` + `.codex` duplicates need a `diff` decision before merging. Proposed approach for each: read both, pick the more recent / more complete / better-described one as canonical.

```bash
# Pre-merge diff template (do not run yet, awaiting OK)
for s in azure-devops azure-keyvault-secrets commit-push-pr mutation-runner property-test-gen red-team; do
  echo "=== $s ==="
  diff -q ~/.agents/skills/$s/SKILL.md ~/.codex/skills/$s/SKILL.md 2>&1
done
```

For `commit-push-pr` specifically there are **3 copies** (`.agents/`, `.codex/`, `.claude/commands/`) — possibly with different command vs. skill semantics. Worth a careful look before picking one.

---

## What goes where (final layout)

```
~/.dotfiles/                                        # private repo, github.com/ShovalBenjer/dotfiles
├── skills/                                         # ~67 skills total
│   ├── # Tier 1: 37 high-value
│   ├── # Tier 2: 28 utilities  
│   ├── # Tier 5 fix: perplexity-mcp (promoted from figma)
│   └── # Tier 7 NEW: microsoft-agent-365, azure-foundry-cli (replacing azure-foundry)
├── hooks/                                          # 8 hooks (2 Claude + 6 Codex)
├── bin/                                            # generate-voice.py, generate-visual.py, pop-* wrappers
├── rules/                                          # behavioral contracts (extracted from AGENTS.md)
├── CLAUDE.md  →  AGENTS.md                         # one rules file, two names
└── README.md                                       # symlink topology + per-skill quickstart

~/archive/skills-deprecated-2026-05-03/             # 4 skills + 1 stray + 20-skill friday-meeting backup
├── meme-control/
├── migrate-to-shoehorn/
├── heidegger-reflection.md                         # the stray
├── heidegger-reflect/                              # if you decide to drop this too
└── friday-meeting/                                 # whole dir

# Symlink targets:
~/.claude/skills      → ~/.dotfiles/skills
~/.claude/hooks       → ~/.dotfiles/hooks
~/.claude/bin         → ~/.dotfiles/bin
~/.claude/CLAUDE.md   → ~/.dotfiles/CLAUDE.md
~/.codex/skills       → ~/.dotfiles/skills
~/.codex/hooks        → ~/.dotfiles/hooks
~/.codex/AGENTS.md    → ~/.dotfiles/AGENTS.md
~/AGENTS.md           → ~/.dotfiles/AGENTS.md
# ~/.agents/  →  REMOVED (you're not actively using the .agents CLI)
```

### Project-level after consolidation

| Project | Keep | Drop |
|---|---|---|
| `~/projects/cs-agent/` | `.agents/skills/claude-eval-cs/`, `.claude/CLAUDE.md`, `.azure/commands/` | `.claude/{agents,commands}/` (empty), divergent `AGENTS.md` (sync to CLAUDE.md) |
| `~/projects/figma-4-all/` | `.codex/skills/banner-analyzer/`, `.codex/skills/perplexity-mcp/` (promote to global, then drop) | All 13 other duplicate skills in `.codex/skills/` |
| `~/projects/qc/` | `CLAUDE.md` | `AGENTS.md` (sync to CLAUDE.md) — both diverged |
| `~/projects/seekapa-training-platform/` | `CLAUDE.md` | `AGENTS.md` (diverged) |
| `~/projects/social-intelligence-unit/` | `CLAUDE.md`, `.kilocode/` *(if used)* | `AGENTS.md` (diverged) |
| `~/projects/.claude/` (orphan parent) | nothing | empty `agents/`, empty `commands/`, investigate `settings.local.json` then likely drop |

---

## Backup verification

```
~/dotfiles-backup-2026-05-03.tar.gz  →  981MB, 1583 files
```

Note: 981MB is bloated by `~/.codex/logs_2.sqlite` (100MB+). You can drop this from the archive after consolidation completes — keep a leaner snapshot:

```bash
# Lean re-snapshot (after consolidation succeeds):
tar -czf ~/dotfiles-snapshot-2026-05-03-lean.tar.gz \
  ~/.dotfiles \
  --exclude='*.sqlite' --exclude='*.log' --exclude='cache/'
```

---

## Recommended sequence (REVISED 2026-05-03)

1. **Diff the 6 redundant skill pairs** → 30 min, decision per pair, no moves yet.
2. **Pick canonical for `commit-push-pr` × 3 copies** → most consequential merge.
3. **Create `~/.dotfiles/` repo, copy Tier 1 + Tier 2 skills in** → ~70 files, ~1 hour.
4. **Archive Tier 3** (4 skills + friday-meeting) → 5 min.
5. **Add hooks + bin to `~/.dotfiles/`** → 10 min.
6. **Convert 24 SIU Kilocode JSON agents → `~/.dotfiles/agents/*.md`** → write `kilocode-to-claude.py` converter, run once, validate. Highest-leverage single step. *(NEW — discovered in Tier 5c)*
7. **Symlink Claude paths first, test for a day, then Codex** → low-risk staged rollout.
8. **Reconcile project CLAUDE.md/AGENTS.md pairs** → one project per session. **Higher priority than originally sized given 6 parallel active sessions.**
9. **Wire playwright-cli + playwright-edge MCP** *(NEW — Tier 5b)*:
   - Write `playwright-cli` SKILL.md targeting Obscura
   - Write `~/.codex/bin/playwright-mcp-edge` launcher with WSL→Windows host detection
   - Add `playwright-edge` server to `~/.mcp.json`
   - Document the Edge launch flag pattern (`--remote-debugging-port=9223`)
10. **Fix the 3 broken refs** in AGENTS.md after step 9 lands.
11. **Build NEW skills** (microsoft-agent-365, azure-foundry-cli refresh) — separate task once consolidation lands.

Awaiting OK on Step 1 (the diff). No file moves yet.
