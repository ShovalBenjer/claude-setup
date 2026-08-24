# claude-setup

A mature Claude Code harness: gates, hooks, skills, review fabric, and the tools that verify whether any of it actually works. This repository is the operating system for AI-assisted development - rules, verification instruments, and living documentation.

## What this repository is

This is not an application. Nothing is served and there is no build output. Most "code" is a verification instrument whose job is to disagree with an agent's own report. The `dot-*` trees are deployable payload (committed copies of `~/.claude`, `~/.codex`, and agent skills), not live configuration.

## Directory map

```
claude-setup/
├── tools/                    Harness tools: gate, review, bus, audit, map, refute
│   ├── gate/                12-domain contract runner and verdict engine
│   ├── review/              PR review fabric (panel, allocation, verdict)
│   ├── bus/                 Hash-chained task bus and inbox
│   ├── audit/               Skills sync, pointers, mutations, append-only oracles
│   ├── map/                 Codemap and directory purpose registry
│   ├── refute/              Claim falsifier layer
│   ├── slop_lint.py         Prose gate (banned lexicon, hyphen density, symmetry)
│   └── ...
├── dot-claude/              Deployable payload for Claude Code (no caches/sessions/secrets)
│   ├── skills/              User-authored skills
│   ├── hooks/               Session hooks (pretooluse, posttooluse, stop, compact)
│   ├── bin/                 Helper scripts
│   ├── commands/            Slash commands
│   ├── agents/              Persona definitions
│   ├── rules/               Enforcement rules
│   ├── CLAUDE.md            Global per-session instructions
│   └── settings.json        Permissions, hooks, env (no secrets)
├── dot-codex/               Deployable payload for Codex CLI
│   ├── skills/              Codex-specific skills
│   └── hooks/               Codex hook stubs and implementations
├── dot-agents/              Agent skills tree (Gastown personas)
│   └── skills/              Persona skill bodies
├── intent-control-plane/    Packaged subproject: intent ledger, resources, tickets
├── docs/                    Living documentation
│   ├── prd/                 Product requirements documents
│   ├── specs/               Technical specifications
│   ├── adr/                 Architecture decision records
│   ├── analysis/            Point-in-time scans and audits
│   ├── prior-art/           External tool comparisons and adoption records
│   ├── standards/           Imported and native coding standards
│   └── DOCMAP.md            Generated living document inventory
├── state/                   Ledgers and generated artifacts (append-only)
│   ├── gate-runs.jsonl      12-domain contract execution history
│   ├── bus.jsonl            Hash-chained task bus
│   ├── reviews/             PR review artifacts
│   └── ...
├── tests/                   Root test suite (~70 tests)
├── dashboard/               Session dashboard (Tauri + React, under active development)
├── research-papers/         Deep-dive research and curated prompt library
├── work-docs/               Work project artifacts and handover docs
└── nexus-engine-rs/         Rust crate for hot-path ledger operations
```

## Quickstarts

### Harness tools

```bash
python -m pytest tests/ -q                     # Root suite, ~47s
python tools/gate/gate.py run --project . -v   # Full 12-domain contract
python tools/gate/gate.py status               # Last verdict
python tools/map/codemap.py check              # Directory purposes + map freshness
python tools/slop_lint.py <file.md>            # Prose gate
python tools/bus/bus.py selftest               # Bus oracle self-test
```

### Dotfiles payload

The `dot-*` trees are committed copies of runtime configuration. Editing them changes nothing about a running session until deployed. Deploy with the skills sync tool:

```bash
python tools/audit/skills_sync.py check         # Measure drift between repo and live trees
python tools/audit/skills_sync.py deploy --apply # Apply repo payload to live runtime
```

### Documentation

```bash
python tools/map/codemap.py write                # Regenerate CODEBASE-MAP.md after adding files
python tools/docmap/docmap.py check               # Verify document status declarations
python tools/docmap/docmap.py write               # Regenerate docs/DOCMAP.md
```

### Intent control plane

```bash
cd intent-control-plane && uv run pytest -q     # Subproject tests
cd intent-control-plane && uv run ruff check . && uv run mypy  # Lint and type check
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Claude Code Session                          │
│  (reads dot-claude/ rules, hooks, skills, CLAUDE.md at startup)    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
     ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
     │  Hooks      │        │  Skills     │        │  Rules      │
     │  (events)   │        │  (invoke)   │        │  (enforce)  │
     └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                    ┌─────────────────────────────┐
                    │      tools/ (harness)        │
                    │  gate → review → bus → audit │
                    └─────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │         state/               │
                    │  gate-runs.jsonl            │
                    │  bus.jsonl (hash-chained)    │
                    │  reviews/<sha>.json          │
                    └─────────────────────────────┘
```

## Verification philosophy

Every oracle carries its own selftest, and CI runs them as named steps so a regression is attributable. The layering is contract, then oracle, then that oracle's selftest, then a mutation that must turn the selftest red.

Key checks:
- `tools/gate/gate.py run` - 12-domain contract with verdict
- `tools/review/panel.py` - PR review fabric with aspect-split verification
- `tools/audit/mutate.py --spec all` - Mutation testing for all oracles
- `tools/slop_lint.py` - Prose quality gate

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, branch naming, commit conventions, PR process, code review expectations, testing requirements, and release process.

## FAQ

**Why is nothing served?**
This repository is a harness and verification instrument, not an application. Its outputs are verdicts, artifacts, and living documentation.

**What are the dot-* trees?**
They are deployable payload: committed copies of runtime configuration for Claude Code (`dot-claude/`), Codex CLI (`dot-codex/`), and agent skills (`dot-agents/`). Editing them changes nothing until deployed via `tools/audit/skills_sync.py`.

**What is the single source of truth for conventions?**
[CLAUDE-OS.md](CLAUDE-OS.md) is the single source of truth for conventions, governance, and process. It merges and supersedes every prior plan in this repo.

**How is work tracked?**
[TODO.md](TODO.md) is the roadmap: strategic objectives, key results, initiative tracker, and risk log. The `docs/DOCMAP.md` maps every major document to its purpose, audience, and maintenance owner.

**How do I start a session?**
Read [docs/SESSION-BOOT.md](docs/SESSION-BOOT.md) for the boot path. Name your lane from `docs/charters.md`, append a claim row to `state/claims.jsonl` before starting, and ground truth in git plus `state/` files.

**What is the quality contract?**
[quality-contract.json](quality-contract.json) declares 12+ domains. A domain counts as covered only when a command exits zero or a named artifact exists for the current commit. Unconfigured is UNCOVERED, and UNCOVERED fails.
