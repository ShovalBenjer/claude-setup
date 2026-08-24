# Shoval Benjer — Claude Setup (Claude OS)

**Start here: [CLAUDE-OS.md](CLAUDE-OS.md) — the single source of truth.** It merges and
supersedes every prior plan in this repo.

Updated 2026-08-24: directory structure consolidated. `dot-claude/`, `dot-codex/`,
`dot-agents/` are the deployable dotfiles payload. `tools/` holds the harness (gate,
oracles, review fabric, bus). `research-papers/` holds long-form research. `work-docs/`
holds work artifacts. `docs/` holds project governance docs (PRDs, specs, ADRs, analysis).

---

## Contents

```
claude-setup/
├── CLAUDE-OS.md              single source of truth (layers L0–L8, deep-work protocol)
├── AGENTS.md                 agent instructions and lane topology
├── TODO.md                   active ticket list (< 300 lines)
├── CONTRIBUTING.md           PR process, code style, testing
│
├── tools/                    harness verification instruments
│   ├── gate/                 12-domain contract + waiver system
│   ├── bus/                  hash-chained cross-session bus
│   ├── review/               panel.py oracle + diff model
│   ├── audit/                skills_sync, pointers, codemap, refute
│   ├── map/                  codemap + docmap
│   ├── intent/               prompt capture + ticket lifecycle
│   ├── slop_lint.py          prose gate (banned lexicon + density)
│   └── ...
│
├── dot-claude/               committed copy of ~/.claude/ (skills, hooks, bin, commands)
├── dot-codex/                committed copy of ~/.codex/ (skills, hooks)
├── dot-agents/               committed copy of ~/.agents/ (skills)
│
├── intent-control-plane/     packaged subproject (lint + mypy here)
├── nexus-engine-rs/          Rust ledger crate (hot-path rewrite candidate)
│
├── research-papers/          long-form research and SOTA references
│   ├── home-md/              25 long-form research markdowns
│   ├── Documents/            11 dated research subfolders
│   ├── Prompts/              curated prompt library
│   └── el-vadt/              sales-agent research project
│
├── work-docs/                work artifacts, specs, and planning docs
├── docs/                     project governance
│   ├── INDEX.md              every tracked prose document
│   ├── SESSION-BOOT.md       fresh-session context from disk
│   ├── PLAN-SPINE.md         PRD → spec → slice → ticket → % built
│   ├── prd/                  product requirements
│   ├── specs/                implementation specs
│   ├── adr/                  architecture decision records
│   ├── analysis/             point-in-time scans and measurements
│   ├── standards/            imported and home-grown standards
│   ├── prior-art/            third-party tool comparisons (300+ line components)
│   └── ...
│
├── dashboard/                Tauri + React session dashboard
├── state/                    append-only JSONL ledgers (bus, gate-runs, claims)
├── tests/                    root test suite
└── .github/workflows/        CI: gate, review, supply-chain, gemini-review
```

## Companion documentation

- [docs/SESSION-BOOT.md](docs/SESSION-BOOT.md) — full context from disk in 60 seconds
- [docs/PLAN-SPINE.md](docs/PLAN-SPINE.md) — one page connecting PRD to spec to slice to ticket
- [docs/INDEX.md](docs/INDEX.md) — every tracked prose document under docs/
- [CLAUDE-OS.md](CLAUDE-OS.md) — mission, layers L0–L8, deep-work protocol, native-feature map

## How to restore dotfiles

1. `cp -r dot-claude/skills dot-claude/hooks dot-claude/bin dot-claude/commands ~/.claude/`
2. Review `dot-claude/settings.json` and merge with current `~/.claude/settings.json`
3. Repeat for `dot-codex/` and `dot-agents/` if those runtimes are installed
