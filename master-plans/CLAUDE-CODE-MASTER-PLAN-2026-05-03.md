# Claude Code Master Plan — 2026-05-03

**Author / operator:** Shoval Benjer (`shoval.be@i-sdd.com` / `Shovalb9@gmail.com` / `ShovalBenjer`)
**Status:** Refined plan. Supersedes prior planning docs; references them as source material.
**Goal:** One canonical document. Read this first; everything else is appendix.

**Source docs reconciled:**
- `~/From 2028  Looking Back on 2026 Agentic Coding — What to Build Today.md` (7-layer 2030 vision)
- `~/Futuristic Learning Stack...April 2026 Edition.md` (measurement + math frontier)
- `~/Autonomous Agentic Coding Systems...2025–2030 Deep Dive.md` (research grounding)
- `~/AI Engineering 2030–2035 Scientific Frontiers...md` (career frame)
- `~/claude-code-experimental-features.md` (feature inventory + first-wave picks)
- `~/cleanup-proposal.md` (`$HOME` hygiene status)
- `~/claude-setup-tasks-2026-05-02.md` (weekend research roundup)
- `~/claude-setup-master-plan-2026-05-02.md` (yesterday's reconciliation v1)
- `~/claude-skills-scatter-2026-05-03.md` (skills/hooks scatter inventory)
- `~/claude-skills-triage-2026-05-03.md` (used/unused/missing/redundancy decisions)
- `~/docs/KNOWLEDGE-BASE.md` (Seekapa/Axia CS architecture)
- `~/docs/FOUNDRY-EVAL-CI-PLAN.md` (4-phase eval gate)
- `~/.codex/automations/prompts/a09-forge-loop-compliance-score.md` (the forge loop)
- `~/.agents/skills/tdd/SKILL.md` (+ companions: deep-modules, interface-design, mocking, refactoring, tests)
- `~/.codex/AGENTS.md` (+ `~/AGENTS.md` Codex root)
- `~/.claude/projects/-home-shovalbe/memory/MEMORY.md` (auto-memory)
- Live Windsor.ai connector inventory (this session)
- GitHub `ShovalBenjer` profile (this session)

---

## Part 1 — How I Operate (Identity + Constraints)

This is the durable context every Claude session should inherit. Most of it lives in `~/.claude/projects/-home-shovalbe/memory/MEMORY.md` already; a few things should also land in `~/.dotfiles/CLAUDE.md` for global load.

### 1.1 Operator profile

- Senior engineer, Israel-based (Tel Aviv). Solution Engineer at i-sdd.
- Polyglot setup: en / he / ar — terminal Hebrew/Arabic needs explicit BiDi handling.
- AI-heavy workflow: Claude Code as orchestrator, Codex as executor. **Never collapse the two.**
- $HOME doubles as a git worktree of `dev.azure.com/.../axia-seekapa-cs-agents` (HOME-as-repo anomaly — act with care; A1 move to `~/projects/axia-seekapa-cs-agents/` is in the queue).
- 6+ parallel Claude sessions are normal: orchestration here at `$HOME`, plus seekapa-training-platform, cs-agent, azure-devops-agent, campaign-analysis (+ child runs), qc.

### 1.2 Tone + behavior

- **Terse, no trailing summaries, no emojis** (unless explicitly requested).
- **Destructive ops require explicit per-action OK**: branch delete, force-push, $HOME rm, git reset --hard, etc. Don't proceed on prior approvals — ask each time.
- **Trigger words for auxiliary modes:**
  - "i don't understand" / out-of-focus signals → spawn voice + visual narration
  - "caveman mode" / "less tokens" → 75% compression mode
  - "/deep-research" → multi-source synthesis with citations
  - "/grill-me" → relentless interview until shared understanding

### 1.3 Skill activation policy

- If user names a skill, use it.
- If task intent clearly matches, use it without explicit naming.
- If multiple skills fit, use minimal set; state order briefly.
- MCP servers are default-off; activate per session via `mcp-activation` skill.

### 1.4 Engineering rules (cross-runtime)

- `bun`/`bunx` for JS/TS. Never `npm`/`npx`/`yarn`/`pnpm` unless project requires.
- `uv` for Python. Never bare `pip`.
- TDD: RED → GREEN → REFACTOR (vertical slices via tracer bullets, **never horizontal slicing** — see Part 4).
- No mocks for business logic, external services, DB, or filesystem. Use recorded fixtures + real components.
- Never claim completion without verification evidence (command + real output + pass/fail).
- Treat `.env`, credentials, tokens, keys, secrets as sensitive — never read, never echo, never commit.

---

## Part 2 — The Forge Loop (the implementation discipline)

Every implementation request gets scored on 8 binary axes. Audited weekly (Saturday 9am) by `~/.codex/automations/prompts/a09-forge-loop-compliance-score.md`.

| # | Axis | What |
|---|---|---|
| 1 | **SPEC** | Doc written under `docs/superpowers/specs/` for this work |
| 2 | **PREMORTEM** | 5 failure modes listed in the spec |
| 3 | **RED** | Failing test pasted before code |
| 4 | **GREEN** | Passing test pasted after code |
| 5 | **REFACTOR** | `/simplify` run on changed files |
| 6 | **COVERAGE** | Acceptance criteria explicitly mapped to tests |
| 7 | **REFLECT** | `/heidegger-reflect` run |
| 8 | **CI BIND** | User pushed and confirmed CI green |

**Trend tracking:** 4-week rolling average. **If average drops below 5/8 → next week's `SessionStart` hook injects a banner nudge** identifying the top 3 most-missed steps.

**Outputs:** `~/.claude/docs/FORGE_COMPLIANCE_<DATE>.md` per week.

This is *the* operating discipline. Skills, hooks, subagents — all of them serve this loop.

---

## Part 3 — TDD Philosophy (the testing discipline)

Source: `~/.agents/skills/tdd/SKILL.md` + 5 companion files (deep-modules, interface-design, mocking, refactoring, tests).

### 3.1 Core principle

**Tests verify behavior through public interfaces, not implementation details.** Code can change entirely; tests shouldn't. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or query the DB directly instead of using the interface. The warning sign: your test breaks when you refactor, but behavior hasn't changed.

### 3.2 Anti-pattern: horizontal slicing (NEVER do this)

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical, tracer bullet):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

Horizontal slicing produces tests of *imagined* behavior, not actual behavior. They test the *shape* of things, not user-facing capability. They pass when behavior breaks and fail when behavior is fine.

### 3.3 Workflow

1. **Plan** — confirm interface changes + behaviors to test with user. Get approval.
2. **Tracer bullet** — ONE test → ONE implementation. Proves the path works end-to-end.
3. **Incremental loop** — for each remaining behavior: RED → GREEN. One test at a time. Only enough code to pass the current test. Don't anticipate.
4. **Refactor** — only after all tests pass. Never refactor while RED.

### 3.4 Per-cycle checklist

- [ ] Test describes behavior, not implementation
- [ ] Test uses public interface only
- [ ] Test would survive internal refactor
- [ ] Code is minimal for this test
- [ ] No speculative features added

---

## Part 4 — Testing Variety (the 12 test types you already built)

Discovered in `~/projects/social-intelligence-unit/.kilocode/agents/` — 24 Kilocode JSON agents, 12 of which are dedicated test types. **This is the testing fleet you already have. It needs format conversion to Claude `.md`, not invention.**

| Type | Agent file | Purpose |
|---|---|---|
| **unit** | `unit-tester.json` | Single-function isolation, fast feedback |
| **integration** | `integration-tester.json` | Multi-module behavior through real interfaces |
| **e2e** | `e2e-tester.json` | Full user journey, headed browser if needed |
| **contract** | `contract-tester.json` | API/schema contracts between services |
| **property** | `property-tester.json` | Hypothesis-style invariants over generated inputs |
| **fuzz** | `fuzz-tester.json` | Random/malformed input resilience |
| **mutation** | `mutation-tester.json` | Test-suite effectiveness via code mutation |
| **regression** | `regression-tester.json` | Known-bug guard tests |
| **chaos** | `chaos-tester.json` | Fault injection (kill processes, drop connections) |
| **concurrency** | `concurrency-tester.json` | Race conditions, deadlocks |
| **performance** | `performance-tester.json` | Latency, throughput baselines |
| **scalability** | `scalability-tester.json` | Load shape and degradation curve |
| (meta) | `test-generator.json` | Generates new tests from coverage gaps |
| (adversary) | `red-team.json` | Adversarial test design |

**The plan:** convert all 24 from Kilocode JSON to Claude `.md` frontmatter via a small `kilocode-to-claude.py` script. They become the subagent fleet the 2030 vision doc says to build.

---

## Part 5 — Eval Pipeline (the Seekapa/Axia evaluation gate)

Source: `~/docs/FOUNDRY-EVAL-CI-PLAN.md` (2026-03-30).

**Constraint:** Foundry-only judges (`grok-4-1-fast-reasoning-2-eval` primary, `DeepSeek-V3.2` audit). No Braintrust as primary. No full transcripts to judges unless multi-turn behavior is the thing being evaluated.

### 5.1 Four phases

| Phase | Where | Dataset | Cost profile |
|---|---|---|---|
| **0 — Deterministic gate** | Build, first | ruff + mypy + unit + webhook/router checks | Free |
| **1 — Foundry smoke** | Build, after Phase 0 | `tests/test_data/foundry_smoke_eval.jsonl` — 10 rows, EN only, no auth flows | grok-4 scores all; DeepSeek audits subset |
| **2 — Expanded pre-merge** | `stage` PRs / scheduled | 40-80 rows, multilingual, KB/escalation/redirect/refusal | grok-4 primary; DeepSeek sampled audit |
| **3 — Nightly benchmark** | `stage` nightly | 80-150 rows max | Same judges; tracks cost, pass rate, disagreement, failure clusters |
| **4 — Portal-native continuous** | Production | Low sample rate, hourly cap, rollback if token spike | Sampled |

### 5.2 Token budget (per row)

- Input: target ≤1500 tokens, hard cap is "compact question + compact answer only"
- Output: ≤120 tokens
- **JSON-only output, binary pass/fail, one-sentence evidence, no chain-of-thought**

### 5.3 Success criteria

Eval gate is successful if it: fails obvious routing regressions, fails financial-advice regressions, fails missed-human-handoff regressions, keeps cost small, produces auditable artifacts, doesn't break on CRM-dependent rows.

### 5.4 Current eval state

- 64% eval pass rate confirmed at v107.3 deploy (per recent commit)
- Latest agent versions: Seekapa v109 yasha-multilingual (current branch), Axia v30
- Multi-LLM prompt debate: GPT-5 Pro + Gemini + Perplexity + Codex iterate; versions in `~/agent-prompts/` (Seekapa v100→v108, Axia v20→v30)

---

## Part 6 — Architecture Reference (Seekapa/Axia CS)

Source: `~/docs/KNOWLEDGE-BASE.md`.

### 6.1 What it is

AI customer service for two FSA-regulated forex platforms (Seekapa, Axia). 4 channels (web widget, Telegram, WhatsApp, email). Email-OTP auth. CRM data from PandaTS MySQL (per-brand) + legacy SQL Server. Compliance escalation via LiveAgent. Multilingual: EN/AR/ES/PT.

### 6.2 Key architectural decisions (don't relitigate without cause)

1. **Channel-agnostic routing** via `message_normalizer.py`
2. **Dual auth paths**: HMAC-signed deep links (pre-auth) + email OTP (5-min expiry, 3-attempt lockout)
3. **Brand-aware CRM routing** — `brand.lower()` lookup; lowercase mandatory
4. **Hard escalation gate (Step 0)** — KYC rejected, >$50K withdrawals, legal identity, regulatory inquiries → human, before any other processing
5. **Hybrid test connector** — Applications endpoint for KB, FunctionToolConnector for CRM (Applications endpoint returns 500 for OpenAPI tool calls)

### 6.3 Production endpoints

- Function App: `https://axia-seekapa-crm.azurewebsites.net`
- Foundry (Seekapa): `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai/applications/seekapa/`
- Foundry (Axia): `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai/applications/AxiaCS/`
- Azure DevOps: `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`

### 6.4 Known platform issues (cause-of-symptom shortcuts)

| Symptom | Cause | Fix |
|---|---|---|
| ~20% Content Safety refusal | Azure platform false positive | Retry; not a prompt issue |
| OTP lost on restart | In-memory dict (Consumption plan single instance) | Migrate to Redis/Table Storage (planned) |
| Brand lookup fails | Caller passed "Seekapa" not "seekapa" | `.lower()` it |
| Telegram silent | Bot token rotated, webhook not re-registered | Re-call `setWebhook` |
| Escalation tickets missing | LiveAgent department IDs are `""` placeholders | Fill from LiveAgent admin |

---

## Part 7 — Open question: .pst → DB → RL mechanism

**Status: NOT FOUND.** You said the .pst file is moved weekly to update a DB that has a reinforcement learning mechanism, documented in `~/docs/`. I searched but did not find an explicit doc describing it.

What I did find under `~/docs/`:
- `KNOWLEDGE-BASE.md` (Seekapa/Axia architecture — no .pst reference)
- `FOUNDRY-EVAL-CI-PLAN.md` (eval pipeline — no .pst, no RL)
- `MODEL-MIGRATION-PLAN.md` (15KB — not yet read; possibly relevant)
- `prompt_v96_optimization_suggestions.md` (possibly the optimization loop)
- `reflections/`, `eval-results/`, `wiki/`, `specs/` — content not yet enumerated for this question

The `~/shoval.be@i-sdd.com.pst` (138MB) at $HOME root is what I think you mean, but its weekly-move-to-DB workflow isn't documented in any file I read.

**Action needed from you:** name the doc (filename or topic) so I can read it directly. I'll wire the cleanup-orchestrator to *not* move the .pst until I understand the workflow that consumes it.

---

## Part 8 — The Setup Plan (refined sequence)

### Pre-requisites (must happen first)

| # | Task | Why | Reversible? |
|---|---|---|---|
| 0 | **Snapshot taken** ✓ | `~/dotfiles-backup-2026-05-03.tar.gz` (981MB, 1583 files) | n/a — already done |
| 1 | **Move `$HOME` worktree** to `~/projects/axia-seekapa-cs-agents/` (cleanup A1) | Currently `$HOME` IS a git repo of the seekapa codebase. New `CLAUDE.md` files at `$HOME` will tangle with the worktree. | Yes — `mv` only |
| 2 | **Install `gh` CLI** | Required for GitHub flow + `commit-push-pr` skill on GitHub repos (Azure DevOps unaffected) | Yes |
| 3 | **Create `~/.dotfiles/` private repo** on `github.com/ShovalBenjer/dotfiles` | One source of truth for skills/hooks/bin/rules | Yes |

### Consolidation (do in order, each step takes ≤1h)

| # | Task | Reference |
|---|---|---|
| 4 | **Diff 6 redundant skill pairs**, pick canonical (`commit-push-pr` is 3 copies) | triage §"Redundancy resolution checklist" |
| 5 | **Copy Tier 1 + Tier 2 skills** from `.agents` and `.codex` into `~/.dotfiles/skills/` (~70 unique after dedup) | triage Tiers 1+2 |
| 6 | **Convert 24 SIU Kilocode agents** → `~/.dotfiles/agents/*.md` via `kilocode-to-claude.py` | triage Tier 5c — single highest-leverage step |
| 7 | **Move 8 hooks** (2 Claude + 6 Codex) → `~/.dotfiles/hooks/` | triage §2 |
| 8 | **Move `~/.claude/bin/`** → `~/.dotfiles/bin/` (generate-voice.py, generate-visual.py, pop-* wrappers) | triage layout target |
| 9 | **Write `~/.dotfiles/CLAUDE.md`** — 30-line global rules (Part 1 of this doc, condensed). Symlink `~/AGENTS.md` to it for Codex. | Part 1 §1.1-§1.4 |
| 10 | **Atomic symlink swap** (`mv -T newlink oldlink`) — Claude paths first, test 24h, then Codex. **Critical: 6 parallel sessions are running.** | scatter §"symlink swap safety" |
| 11 | **Archive Tier 3** (meme-control, migrate-to-shoehorn, heidegger-reflection.md stray, friday-meeting/, .codex/migrated-from-claude/) → `~/archive/skills-deprecated-2026-05-03/` | triage Tier 3 |
| 12 | **Reconcile 4 diverged project CLAUDE.md/AGENTS.md pairs** (qc, cs-agent, social-intelligence-unit, seekapa-training-platform). One per session. | scatter §4 |
| 13 | **Drop `~/.agents/` entirely** (you confirmed not actively used) | user decision 2026-05-03 |
| 14 | **Wire 3 priority Claude hooks** from the experimental-features picks: `PreToolUse` deny-list, `PreCompact` snapshot, `SubagentStop` voice recap | experimental-features.md §1 + §3 |

### Browser layer (parallel track)

| # | Task | Notes |
|---|---|---|
| 15 | **Write `playwright-cli` SKILL.md** targeting Obscura at `~/.local/bin/obscura` + `~/.codex/bin/obscura-cdp` start/stop | triage Tier 5b |
| 16 | **Write `~/.codex/bin/playwright-mcp-edge`** launcher: detects WSL2 host gateway, health-checks `http://${WIN_HOST}:9223/json/version`, bunx-execs `@playwright/mcp` against it; if dead, prints the **exact PowerShell command** to run | triage Tier 5b + this session |
| 17 | **Write `edge-cdp-reminder` skill** — invoked when `playwright-edge` MCP fails health-check. SKILL.md body **prints the exact PowerShell command** below for the user to paste. Memory-backed: don't ask twice in same session. | New, this session |
| 18 | **Add `playwright-edge` server to `~/.mcp.json`** alongside existing Obscura entry | triage §"Proposed `.mcp.json`" |

#### Edge launcher command (the one the reminder skill prints)

```powershell
Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  -ArgumentList @(
    "--remote-debugging-port=9223",
    "--remote-debugging-address=0.0.0.0",
    "--user-data-dir=C:\Users\shoval.be\AppData\Local\Microsoft\Edge\CDP-Profile"
  )
```

The `edge-cdp-reminder` skill body should also note: separate `--user-data-dir` so CDP profile doesn't conflict with normal Edge.

### Cleanup orchestrator (parallel track)

| # | Task | Notes |
|---|---|---|
| 19 | **Build `home-cleanup-orchestrator` skill** at `~/.dotfiles/skills/home-cleanup-orchestrator/`. Phase A (parallel subagent fan-out per project), Phase B ($HOME-root file relocation rules), Phase C (approval-gated execution). | this session |
| 20 | **Encode the relocation rules** in `rules.yaml` (research → `~/research/`, WhatsApp images → `~/Pictures/whatsapp-2026-03/`, etc.) | this session |
| 21 | **Hold off on .pst move** until Part 7 question is answered | this session |
| 22 | **Update `.claudeignore`** to add `~/research/`, `~/archive/`, `~/Documents/email-archive/` exceptions if needed | After step 20 runs |

### Build new (Tier 6 + Tier 7)

| # | Task | Source |
|---|---|---|
| 23 | **microsoft-agent-365** skill + MCP — needs research on Microsoft 365 Agents SDK / Copilot Studio CLI | user request |
| 24 | **azure-foundry-cli** skill — replace existing `azure-foundry` (MCP-based) with CLI-first wrapper (`az ai`, `az cognitiveservices`) tied to `seekapa_ai` project endpoint | user request |
| 25 | **dep-watcher** subagent — CVE monitoring + auto-update proposals (important for Seekapa Azure Functions Python deps) | 2030 vision Layer 3 |
| 26 | **coverage-gap-detector** skill — UMAP projection of session embeddings against golden dataset | 2030 vision Layer 7 keystone |
| 27 | **Slash commands**: `/spawn-team`, `/consolidate-memory`, `/coverage-map`, `/audit-deps` | 2030 vision Layer 5 |

### Observability (Layer 7 — the moat)

| # | Task | Notes |
|---|---|---|
| 28 | **Stop hook → JSONL session log** at `~/.claude/observability/sessions.jsonl` | minimal viable Layer 7 |
| 29 | **DeepEval `@observe` tracing** wrapped around significant sessions | non-intrusive |
| 30 | **Golden dataset (50 examples)** built from real Seekapa session failures | tied to Foundry CI Phase 1-2 |
| 31 | **LanceDB embedding store** — only after ≥100 sessions logged | premature optimization otherwise |
| 32 | **Weekly UMAP coverage topology** + gap-driven golden expansion | quarter 2 |
| 33 | **Confidence-tier routing** (0.90+/0.70-0.89/<0.70) at PreToolUse hook | quarter 2 |

### Career path (parallel, owned by you)

| # | Task | Why |
|---|---|---|
| 34 | **GitHub `ShovalBenjer` audit** — 21 repos triage (keep-private/public/archive); profile README rewrite | activate professional profile (Navan calibration target) |
| 35 | **One showcase public repo** — Time Twist Visualizer is the candidate (Rust TUI, no IP entanglement) | flagship pinned repo |
| 36 | **One merged PR to vLLM / HF TRL / DeepEval** | higher signal than 5 personal repos |
| 37 | **Stand up vLLM container** with quantized 7B — closes Navan gap, hosts internal eval-judge cheaply, becomes a public blog | self-hosted inference + cost saver |

---

## Part 9 — Windsor / Meta Ad Ops surface (for context)

Not Claude Code config, but informs which skills matter. Live as of 2026-05-02 via `shovalbeisddcom`:

| Connector | Accounts | Notable brands |
|---|---|---|
| facebook | **40** | Seekapa, Axia, Traders Academy, DailyVesting, WhatsAppSignals×2, MIC, Q8 Trade, Wonder Care, CalendarTrader, Top 10 Apps Ever, Al Manara, ST-Agency, BeZ Online HR, +regional MS/GCCMM/TS/WS/TA |
| google_ads | 37 | Per-region: UAE/KSA/BHR/KWT/OMN/QTR/Brazil for Axia, SeeKapa, Daily Vesting, WhatsApp Signals, MIC |
| linkedin | 4 | Trader's Ad Account ×2, Ali's, Trader Academy |
| tiktok | 4 | GCCMM, AccountSeekapa, BP-General, Academy-TA |
| snapchat | 2 | MITSO MARKETING, Traders_Academy |
| taboola, sendinblue | 1, 1 | smarttool-network, tech@corp-domain.com |

**Implication:** Meta Ads CLI worth installing read-only behind Key Vault token (you do run ads at scale). Cross-brand 30-day FB spend report is a 2-hour task with immediate i-sdd value. Suspended-account audit (e.g. `MIC - UAE (SUSPENDED)`) before any spend reports get noisy.

---

## Part 10 — Parallel agent runtimes (NOT Claude Code config — keep separate)

| Runtime | Path | Purpose |
|---|---|---|
| **OpenClaw** (Telegram bot on Foundry GPT-5.2) | `~/projects/openclaw-poc/`, `~/.openclaw/workspace/` | Telegram-only PoC; Composio deferred. Plan (per recent session): wrap Foundry agents with OpenClaude (Gitlawb/openclaude) + GPT-5.5 |
| **SIU Python agents** | `~/projects/social-intelligence-unit/src/siu/agents/` | Runtime SIU agents (definitions.py, workflow.py, tools.py) — separate from the 24 Kilocode test agents |
| **Campaign-analysis domain agents** | `~/projects/campaign-analysis/agents/` | `call_quality_agent`, `market_intel_agent` (system_prompt.txt) |

These do **not** belong in `~/.dotfiles/`. They're project artifacts with their own deploy paths.

---

## Part 11 — Decisions still open

1. **Part 7 .pst → RL doc** — point me at the file
2. **Edge CDP exposure** — `0.0.0.0` (any process on dev box) vs `127.0.0.1` + `socat` tunnel from Windows side
3. **SIU Kilocode agent ownership** — port (copy to `~/.dotfiles/agents/`, leave originals) or move out of SIU
4. **`heidegger-reflect` keep or archive** (Tier 3) — your call
5. **Microsoft Agent 365 priority** — research-and-build now, or after consolidation lands
6. **`/schedule` weekly Windsor cross-brand FB spend report** — wire it once Meta Ads CLI install is decided

---

## Part 12 — Quick reference

### File locations after consolidation

```
~/.dotfiles/                                  # NEW: single source of truth
├── CLAUDE.md → AGENTS.md                     # one file, two names
├── skills/                                   # ~70 unique
├── agents/                                   # 24 (from SIU) + new
├── hooks/                                    # 8 unified
├── bin/                                      # voice/visual generators + pop-* wrappers
└── rules/                                    # extracted behavioral contracts

~/.claude/{skills,hooks,bin,CLAUDE.md}        # → ~/.dotfiles/{...}
~/.codex/{skills,hooks,AGENTS.md}             # → ~/.dotfiles/{...}
~/AGENTS.md                                   # → ~/.dotfiles/AGENTS.md

~/projects/axia-seekapa-cs-agents/            # NEW: $HOME no longer a worktree
~/research/                                   # NEW: research markdowns moved here
~/Documents/email-archive/                    # NEW: .pst moved here (PENDING Part 7)
~/Pictures/whatsapp-2026-03/                  # NEW: WhatsApp images moved here
~/archive/                                    # NEW: friday-meeting + deprecated skills
```

### Skill counts (post-consolidation)

| Tier | Count | Status |
|---|---|---|
| Tier 1 (high-value) | ~37 | KEEP-G |
| Tier 2 (utilities) | ~28 | KEEP-G |
| Tier 3 (archive) | 4 + friday-meeting (20) | ARCHIVE |
| Tier 4 (project-scope) | 2 | KEEP-P (claude-eval-cs, banner-analyzer) |
| Tier 5 (broken refs) | 3 | FIX (playwright-cli, playwright-mcp, perplexity-mcp) |
| Tier 6 (NEW for 2030) | 4 (revised down — most exist in SIU) | BUILD or PORT |
| Tier 7 (NEW for stated wants) | 2 | BUILD (microsoft-agent-365, azure-foundry-cli) |

### Active session count

6+ Claude sessions in flight per `~/.claude/history.jsonl`. Symlink swaps must use `mv -T` for atomicity.

### Backup

`~/dotfiles-backup-2026-05-03.tar.gz` — 981MB, 1583 files. Lean re-snapshot can drop `~/.codex/logs_2.sqlite` (100MB).

---

## Part 13 — Status (2026-05-04 update)

Resolved this session:
- **.pst pipeline (Part 7):** found at `~/.codex/automations/prompts/a05-pst-email-action-mining.md`. RL theory in `~/Prompts/Q-Learning, Deep RL & March 2026 Research...md` is the FRAMEWORK — the actual ranker is not yet built; current a05 is deterministic mining.
- **Edge bridge (Part 8 §17):** dropped. Edge security strips `--remote-debugging-address=0.0.0.0`; Windows admin denied for `netsh portproxy`. Pivot: use Entra/MFA via API (service principal / device-code flow) to skip browser entirely. Obscura covers ≥95% of UI work. WSL mirrored networking is the only no-admin path forward if Edge becomes critical.
- **$HOME worktree move:** ATTEMPTED + REVERTED. Sidelined `~/.git` would have orphaned 5 stashes (`v109-session-home-mods`, callanalyzer WIP, align-test-connector WIP) and broken `~/projects/cs-agent/axia-seekapa-cs-agents/` which relies on tree-walk-up to `$HOME/.git`. Real fix is a clone-and-migrate (multi-step), not a sideline. Deferred.
- **bypassPermissions across all projects:** propagated to all 10 project-level `settings.local.json` (preserves existing allow lists). Backups at `*.local.json.bak-2026-05-03`. New sessions get bounded-by-rules immediately.
- **Per-skill model routing:** 6 skills now have `model:` frontmatter (haiku × 2 narration, sonnet × 1 routine, opus × 3 review/eval/research).
- **`codex-call` skill:** wired (Patterns A-D for Claude→Codex bridging).
- **Night cron + 5 Codex automations:** live; a09 smoke verified end-to-end (forge-loop measured 2.06/8 last 4 weeks — discipline gap is real).
- **22 dormant systemd timers:** archived + removed. Layer7 cron commented (recoverable).
- **6 Codex hooks wired into Claude lifecycle** (SessionStart × 2, PreToolUse × 3, Stop × 1).

Open / dropped:
- ~~Edge CDP exposure~~ → DROPPED (use API auth instead)
- ~~SIU Kilocode 24-agent conversion~~ → DROPPED (legacy, not aligned with current vision; write fresh agents instead)
- ~~`heidegger-reflect` archive decision~~ → keep, low cost
- **Microsoft Agent 365 priority** — still your call. Pre-research suggested install during consolidation phase, not before.
- **`/schedule` weekly Windsor cross-brand FB spend** — wire if/when Meta Ads CLI install lands.

---

## Part 14 — Appendix: ready-to-paste templates (merged from past plans)

### 14.1 Skill redundancy resolution checklist (6 pairs)

```bash
# Pre-merge diff each pair, decide canonical, record decision
for s in azure-devops azure-keyvault-secrets commit-push-pr mutation-runner property-test-gen red-team; do
  echo "=== $s ==="
  diff -q ~/.agents/skills/$s/SKILL.md ~/.codex/skills/$s/SKILL.md 2>&1
  ls -lh ~/.agents/skills/$s/SKILL.md ~/.codex/skills/$s/SKILL.md 2>/dev/null
  echo ""
done
# `commit-push-pr` is the worst — 3 copies including ~/.claude/commands/commit-push-pr.md
```

For each pair: pick the more recent / fuller version as canonical, copy into `~/.dotfiles/skills/<name>/SKILL.md`, then symlink the other location to it. Source: `claude-skills-triage-2026-05-03.md` Tier 1.

### 14.2 Hook JSON templates (paste into `~/.claude/settings.json` if extending)

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [
        { "type": "command", "command": "$HOME/.codex/hooks/session-context.sh" },
        { "type": "command", "command": "$HOME/.codex/hooks/post-compact-reinject.sh" }
      ]}
    ],
    "PreToolUse": [
      { "matcher": "Edit|Write|MultiEdit", "hooks": [
        { "type": "command", "command": "$HOME/.codex/hooks/protect-infra.sh" },
        { "type": "command", "command": "$HOME/.codex/hooks/watchdog-verify.sh" }
      ]},
      { "matcher": "TaskUpdate", "hooks": [
        { "type": "command", "command": "$HOME/.codex/hooks/verification-before-completion.sh" }
      ]},
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "$HOME/.dotfiles/hooks/credit-guard.sh" }
      ]}
    ],
    "PreCompact": [
      { "hooks": [
        { "type": "command", "command": "$HOME/.dotfiles/hooks/snapshot-state.sh" }
      ]}
    ],
    "SubagentStop": [
      { "matcher": "code-reviewer|red-team-review", "hooks": [
        { "type": "command", "command": "$HOME/.dotfiles/hooks/completion-voiceover.sh" }
      ]}
    ],
    "Stop": [
      { "matcher": "*", "hooks": [
        { "type": "command", "command": "$HOME/.codex/hooks/stop-checklist.sh" }
      ]}
    ]
  }
}
```

Currently wired: SessionStart, UserPromptSubmit (voice/visual), PreToolUse (Edit/Write/Multi + TaskUpdate), Stop. Not yet wired (future): PreCompact, SubagentStop, Bash credit-guard. Source: `claude-code-experimental-features.md` §1+§3.

### 14.3 Skill frontmatter schema (for future skills)

```yaml
---
name: <kebab-case-name>
description: |
  One-paragraph trigger description ending with phrases that should auto-invoke
  (the "Triggers on" pattern). Be specific — Claude matches description against intent.
model: claude-haiku-4-5-20251001 | claude-sonnet-4-6 | claude-opus-4-7
effort: low | medium | high | xhigh   # optional, default medium
paths: "**/*.py"                       # optional, glob to scope when skill is relevant
allowed-tools:                         # optional, pre-approves specific tool calls
  - "Bash($HOME/.dotfiles/bin/foo *)"
  - "Read(/specific/path/**)"
disable-model-invocation: false        # default false; set true to require explicit /skill-name
---

# Title
Body markdown — instructions for Claude when this skill activates.
```

Source: `claude-code-experimental-features.md` §3.

### 14.4 Dotfiles repo init checklist

```bash
# 1. Create empty private repo on GitHub ShovalBenjer (UI), name: dotfiles
# 2. Local init
mkdir -p ~/.dotfiles && cd ~/.dotfiles
git init
git remote add origin git@github.com:ShovalBenjer/dotfiles.git  # or https with PAT

# 3. Skeleton
mkdir -p skills hooks bin agents rules
cp ~/.claude/CLAUDE.md ./CLAUDE.md       # global rules (already exists)
ln -sf CLAUDE.md AGENTS.md                # one file, two names

# 4. Move canonical skills/hooks one batch at a time (each reversible)
#    (do this after diff-ing the 6 redundant pairs in 14.1)
mv ~/.codex/skills/voice-explainer skills/
mv ~/.codex/skills/visual-explainer skills/
# ... etc per triage Tier 1+2

# 5. Symlink back so existing tools find them
ln -sfn ~/.dotfiles/skills ~/.claude/skills
ln -sfn ~/.dotfiles/skills ~/.codex/skills

# 6. First commit + push
git add .
git commit -m "feat: initial canonical dotfiles layout"
git push -u origin main
```

Source: master plan Part 8 §3 + scatter consolidation target.

### 14.5 `kilocode-to-claude.py` scaffold (50-line target — DEFERRED)

Note: SIU Kilocode conversion was DROPPED (legacy, not current). Keeping scaffold here for future agent-format-port tasks. Skip unless re-prioritized.

```python
#!/usr/bin/env python3
"""kilocode-to-claude.py: convert Kilocode JSON agent definitions to Claude .md frontmatter.

Usage: python3 kilocode-to-claude.py <input-dir> <output-dir>
Reads ~/projects/.../kilocode/agents/*.json → writes ~/.claude/agents/*.md
"""
import json, sys
from pathlib import Path

MODEL_HINTS = {
    "tester": "claude-sonnet-4-6", "test": "claude-sonnet-4-6",
    "review": "claude-opus-4-7",   "red-team": "claude-opus-4-7",
    "orchestrator": "claude-opus-4-7", "planner": "claude-opus-4-7",
    "compactor": "claude-haiku-4-5-20251001", "cleaner": "claude-haiku-4-5-20251001",
    "organizer": "claude-haiku-4-5-20251001",
}

def pick_model(name: str) -> str:
    for hint, model in MODEL_HINTS.items():
        if hint in name.lower():
            return model
    return "claude-sonnet-4-6"

def convert(json_path: Path, out_dir: Path) -> Path:
    data = json.loads(json_path.read_text())
    name = data.get("name", json_path.stem)
    role = data.get("role", "")
    description = data.get("description", role)
    system_prompt = data.get("systemPrompt", data.get("system_prompt", ""))
    tools = data.get("tools", [])
    out = out_dir / f"{name}.md"
    out.write_text(
        f"---\nname: {name}\n"
        f"description: {description.strip().replace(chr(10), ' ')[:600]}\n"
        f"model: {pick_model(name)}\n"
        f"tools: {tools}\n"
        f"---\n\n# {role or name.title()}\n\n{system_prompt}\n"
    )
    return out

if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.json"):
        out = convert(f, dst)
        print(f"  {f.name} → {out}")
```

### 14.6 A1-A4 weekend setup carryover (from `claude-setup-tasks-2026-05-02.md`)

| Task | Status | Notes |
|---|---|---|
| **A1: claude-obsidian** install | ⏳ deferred | `claude plugin marketplace add AgriciDaniel/claude-obsidian && claude plugin install claude-obsidian@claude-obsidian-marketplace`. Heavy plugin (11 skills). Try in side worktree first. |
| **A2: Understand-Anything** for Seekapa | ⏳ deferred | `claude plugin marketplace add Lum1104/Understand-Anything`. 5-agent parallel scanner with React Flow viz. Best fit for Seekapa given v109 layered architecture. |
| **A3: Meta Ads CLI** | ⏳ deferred | Install only if you decide; needs Python 3.12+ + Key Vault token. Default `--paused` for create commands. |
| **A4: setup hygiene fixes** | ✅ done | gh CLI demoted (work=ADO); global `CLAUDE.md` written; AGENTS.md broken refs cleaned; one-shot, settings consolidated. |

### 14.7 forge-loop axis-fix skills (the actual P1 from current pain)

Three small skills to raise compliance from 2.06/8:

- **`premortem`** — fires on `/spec` or "let's design X"; forces a 5-failure-mode section. ~30-line SKILL.md.
- **`coverage-enforcer`** — wired into `commit-push-pr` pre-push step; fails if diff has source changes but no test changes. Hook-level enforcement.
- **`refactor-pre-push`** — bakes `/simplify` into `commit-push-pr` between green tests and push. Uses existing `code-simplifier` skill.

These three address the 3 most-missed axes (PREMORTEM, COVERAGE, REFACTOR) per the latest a09 audit. Estimated ~1 hour total. **Recommended as the new P1.**

---

## Part 15 — Source files (for re-reading)

These were merged into this master plan:

| File | Now considered | Why kept |
|---|---|---|
| `claude-skills-scatter-2026-05-03.md` | Reference appendix | Detailed dir-by-dir audit; useful when actually consolidating |
| `claude-skills-triage-2026-05-03.md` | Reference appendix | Per-skill triage decisions; bigger than what fits in master |
| `claude-setup-tasks-2026-05-02.md` | Superseded by 14.6 | Original A1-A4 tasks merged in |
| `claude-setup-master-plan-2026-05-02.md` | Superseded | First-pass reconciliation; this file is the v2 |
| `cleanup-proposal.md` | Active reference | $HOME hygiene status; Tier H scrub-mode files still pending |
| `claude-code-experimental-features.md` | Source extract | Hook + frontmatter templates pulled into 14.2 + 14.3 |
| `~/.claude/CLAUDE.md` | Live, loaded every session | Global rules (matches Part 1 of this doc) |
| `~/AGENTS.md` | Live, Codex-side root | Mirror of CLAUDE.md for Codex; broken refs cleaned 2026-05-03 |
