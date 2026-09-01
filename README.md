# Shoval Benjer - Claude Setup (the Claude OS)

**Start here: [CLAUDE-OS.md](CLAUDE-OS.md) - the single source of truth.** It merges and
supersedes every prior plan in this repo.

This repository is the canonical home of a personal Claude Operating System: a verification
harness plus the deployable configuration (`dot-claude/`, `dot-codex/`, `dot-agents/`) that
turns captured context - WhatsApp, docs, specs, prompts - into gated, evidenced action across
Shoval's ventures, with Shoval reduced to an approval surface. The defining principle, drawn
from `work-docs/research/2026-07-07-claude-setup-gap-analysis.md`, is that **prose is not
enforcement**: every claim this repo makes about itself is checked by something that runs.

> Note on this tree. This snapshot mirrors `github.com/ShovalBenjer/claude-setup`. The
> harness tooling (`tools/`, `docs/`, the gates) and the deployable payload (`dot-*` trees)
> live side by side. See `CLAUDE-OS.md` for the mission and the layer model (L0–L8) that
> organizes everything below.

## Project overview

| Concern | What lives here | Owner doc |
|---|---|---|
| Harness | `tools/` - the oracles, gates, schedulers, and review fabric that verify the OS | `AGENTS.md`, `docs/QUALITY-CONTRACT.md` |
| Dotfiles | `dot-claude/`, `dot-codex/`, `dot-agents/` - the deployable config payload | `CLAUDE-OS.md` L1/L2/L5 |
| Research | `research-papers/`, `work-docs/research/` - the corpus that shapes the rules | `work-docs/research/README.md` |
| Work / control plane | `docs/` (prd/spec/adr/analysis/INDEX/TODO), `state/` (ledgers), `intent-control-plane/` | `docs/INDEX.md`, `docs/SESSION-BOOT.md` |

The system is a **closed-loop control plane**, not a script (see `CLAUDE-OS.md` §2d). Three
feedback loops run at three speeds: per-task reputation + routing, a weekly self-improvement
loop, and an as-needed hiring/PIP/firing loop for the reviewer labor market. Depth is
enforced by structure (hooks, gates, files, crons) - never by asking the model to "think
deeply."

## Directory map (annotated)

```
claude-setup/
├── tools/                      # HARNESS - verification instruments, not application code
│   ├── gate/                   # the 12-domain quality contract (gate.py run)
│   ├── docmap/                 # DOCMAP.md + doc-status.txt derivation
│   ├── map/                    # CODEBASE-MAP.md generation + prior-art checks
│   ├── review/                 # dual-reviewer panel (agreement gate + provenance)
│   ├── bus/                    # hash-chained intent/task ledger
│   ├── refute/                 # per-claim falsifiers
│   ├── audit/                  # mutation + pointer/dead-path scanners
│   ├── intent/                 # intent ledger render/verify (the /loop spine)
│   ├── harness/                # consumer-side resolver (self/harness-ref/vendor)
│   ├── hookgate/              # Rust gate that supersedes pretooluse_gate.py
│   └── ...                     # slop_lint, corpus, snapshot, skills_eval, etc.
│
├── dot-claude/                 # DOTFILES - committed copy of ~/.claude (payload, not live)
│   ├── skills/                 # 73+ user-authored skills (owned per persona)
│   ├── hooks/                  # hook entry points; many unwired on this host
│   ├── agents/                 # standing persona definitions
│   ├── commands/               # slash commands (diverge, commit-push-pr, slop, ...)
│   ├── rules/                  # per-repo enforcement rules
│   ├── settings.json           # permissions + hooks + env (no secrets)
│   └── CLAUDE.md               # global per-session instructions
│
├── dot-codex/                  # DOTFILES - committed copy of ~/.codex (payload)
│   ├── skills/                 # skills tree (incl. heidegger-reflection)
│   ├── rules/                  # global binding rules (no-mocks, tdd-enforcement, ...)
│   ├── automations/            # cron automation prompts + last-message logs
│   └── AGENTS.md               # @AGENTS.md (delegates to root AGENTS.md)
│
├── dot-agents/                 # DOTFILES - agent skills tree (payload)
│
├── research-papers/            # RESEARCH - curated corpus (books, prompts, SOTA reports)
│   ├── home-md/                # long-form research markdowns
│   ├── Documents/              # dated research subfolders
│   ├── Prompts/                # prompt library + style guides
│   └── el-vadt/                # sales-agent research exemplar
│
├── work-docs/                  # WORK - working drafts, dated snapshots, the research lane
│   └── research/               # long-form research that should inform implementation
│
├── docs/                       # WORK / CONTROL PLANE - the docs control plane
│   ├── prd/ spec/ adr/         # product requirements, specs, architecture decisions
│   ├── analysis/               # dated-snapshot analyses (ephemeral by design)
│   ├── archive/                # retired content + migration notes
│   ├── INDEX.md                # curated reading order (not an inventory)
│   ├── DOCMAP.md               # GENERATED inventory (do not hand-edit)
│   ├── CODEBASE-MAP.md         # GENERATED directory-purpose map
│   └── QUALITY-CONTRACT.md     # reasoning behind the gate domains
│
├── state/                      # WORK - append-only ledgers (claims, lessons, bus, reviews)
├── intent-control-plane/       # WORK - subproject: intent ledger (own docs/ + uv toolchain)
├── nexus-engine-rs/            # Rust hot-path component
├── dashboard/                  # Tauri 2 dashboard (Rust core + web front end)
├── tests/                      # root pytest suite (~70 tests)
└── AGENTS.md                   # root agent guidance (the harness spine)
```

## Architecture

The OS is a control plane: work enters from anywhere, gets verified at every boundary, and
outcomes feed back into routing, memory, and the rules themselves.

```
                 ┌─────────────────────────────────────────────┐
   inbounds  ───▶ │  L0 SDLC kernel: intent contract → done-     │
 (WhatsApp,      │  verifier → coverage-format → state machine  │
  GitHub,        └───────────────┬─────────────────────────────┘
  phone, cron,                   │  verified evidence
  health sweeps)                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  L1–L8 fabric: governance, memory,           │
                 │  orchestration, I/O, quality, portfolio,     │
                 │  platform, frontier                         │
                 └───────────────┬─────────────────────────────┘
                                 │  artifacts + git + state/
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  HARNESS (tools/): gate.py · review panel ·   │
                 │  docmap · bus · refute · audit/mutate         │
                 └───────────────┬─────────────────────────────┘
                                 │  dichotomies: PASS / FAIL,
                                 │  caught / survived (mutation)
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  FEEDBACK: reputation+routing (fast) ·       │
                 │  self-improvement (weekly) · hiring/PIP (slow)│
                 └───────────────┬─────────────────────────────┘
                                 │
                                 └──────────▶ back into routing, memory, rules
```

The maturity ladder (L0 prose-collection → L5 self-improving control plane) and the current
honest self-assessment are tracked in `CLAUDE-OS.md` and `docs/adr`.

## Quickstart

### Harness (run the gate)

```bash
python3 tools/gate/gate.py run --project . -v     # the full 12-domain contract
python3 tools/gate/gate.py selftest               # every oracle's own selftest
python3 -m pytest tests/ -q                       # root suite (~47s, 70 tests)
```

### Dotfiles (deploy the payload)

The `dot-*` trees are payload, not live config. Editing `dot-claude/` changes nothing about a
running session until it is deployed to `~/.claude`. Measure drift both directions with:

```bash
python3 tools/audit/skills_sync.py check
```

### Research (read before reasoning)

The research lane is the corpus that shapes the rules. Start with:

- `work-docs/research/2026-07-07-claude-setup-gap-analysis.md` - the root finding (prose ≠
  enforcement) and the prioritized backlog.
- `work-docs/research/2026-07-08-global-and-per-project-suggestions.md` - the G1–G5 global
  build backlog.
- `work-docs/research/2026-07-08-trending-agent-repos.md` - verified 2026 SOTA to learn from.
- `work-docs/research/2026-07-29-llm-agents-game-theory-...md` - epistemic governance framing.

### Work / control plane (write a change)

1. Boot: `docs/SESSION-BOOT.md` (name your lane in `docs/charters.md`, append a claim row to
   `state/claims.jsonl`).
2. Plan: `docs/PLAN-SPINE.md` connects PRD → spec → slice → ticket → % built.
3. Implement behind tests (TDD is enforced - `CONTRIBUTING.md` §4).
4. Ship via PR gate only (`AGENTS.md`, ADR-0012). Docs are the control plane: update the
   matching PRD/spec/ADR, not just the code.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development setup, kebab-case branch naming,
Conventional Commits, the TDD-enforced test tiers, the PR process, review expectations, and
the release (merged + smoke-tested) process. The one-line version: small branches, tests
first, green gate, PR into `main`, no direct commits, no stubs, no emojis.

## FAQ

**Is this a project I install and run?** No. There is no application, nothing is served, and
there is no build output. The "code" is a verification instrument whose job is to disagree
with an agent's own report. The `dot-*` trees are deployable payload for one operator's
machines.

**Why are so many hooks/skills "unwired"?** Presence in the tree is not deployment. Per
`AGENTS.md`, 23 of 29 `dot-claude/hooks` entries are wired nowhere in the live
`settings.json`, and 12 are one-line pointers into a Windows home that does not exist on this
host. `tools/audit/pointers.py scan` reports them. Dead paths are logged, not silently
fixed.

**What is the difference between `docs/DOCMAP.md` and `docs/INDEX.md`?** DOCMAP is a
machine-generated inventory (counts, statuses, supersession). INDEX is a curated reading
order. DOCMAP is regenerated by `tools/docmap/docmap.py write`; never hand-edit it.

**What is "production" here?** Merged to `main` and smoke-tested - not a tagged artifact
(`dot-codex/rules/production-means-merged-and-smoked.md`). A local PASS is not evidence about
the CI runner; the gate must be green on the merged tree.

**Where is the research the rules cite?** `work-docs/research/` (the active research lane)
and `research-papers/` (the curated corpus). The gap analysis and the global/per-project
suggestions are the load-bearing reads.

**How do I know what not to work on?** `docs/charters.md` assigns lanes. Doing another lane's
work is the most frequently logged entry in `state/lessons.jsonl`.
