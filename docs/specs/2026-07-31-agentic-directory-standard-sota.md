# SOTA Agentic Repository Directory Standard & Estate Enhancement Plan

Status: design. Specification and architectural comparison, 2026-07-31.

- **Date**: 2026-07-31
- **Status**: SPECIFICATION & ARCHITECTURAL COMPARISON
- **Companion**: `docs/standards/agentic-repo-standard.md` ([ADR-0020](file:///c:/Users/shova/claude-setup/docs/adr/0020-agentic-repo-standard.md)), `docs/specs/2026-07-31-project-federation.md`

---

## 1. Architectural Comparative Analysis: SOTA Agent Systems

We evaluated top open-source agentic systems—**Goose** (Block/AAIF), **AutoGen v0.4** (Microsoft), **LangGraph** (LangChain), **MCP Servers** (Anthropic), and **CrewAI**—against our ShovalBenjer estate standard ([ADR-0020](file:///c:/Users/shova/claude-setup/docs/standards/agentic-repo-standard.md)).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC REPOSITORY ARCHITECTURE MATRIX                           │
├───────────────────┬──────────────────────┬─────────────────────────┬───────────────────┤
│ System / Repo     │ Architectural Model  │ Primary Directory Pattern│ Key Strength      │
├───────────────────┼──────────────────────┼─────────────────────────┼───────────────────┤
│ Goose (AAIF)      │ Multi-Crate Engine   │ crates/ + ui/ + evals/  │ Isolated MCP/ACP  │
│ AutoGen v0.4      │ Asynchronous Actors  │ packages/ (core vs ext) │ Layered Runtime   │
│ LangGraph         │ Cyclic State Graph   │ libs/ (graph+checkpoint)│ State Checkpointing│
│ MCP Servers       │ Monorepo Tools       │ src/ (tool_name/ common)│ Zero Tool Leakage │
│ CrewAI            │ Role & Task Framework│ agents/ + tasks/ + tools│ Domain Concept Map│
│ claude-setup (Ours)│ Verification Harness │ src/ + tools/ + state/  │ Verifiable Oracles│
└───────────────────┴──────────────────────┴─────────────────────────┴───────────────────┤
```

---

## 2. Grading Goose (`aaif-goose/goose`) & Comparative Takeaways

### Repository Grade: **9.2 / 10 (A)**

- **Strengths**:
  1. **Workspace Decoupling (`crates/`)**: Engine execution logic (`goose`) is isolated from protocol transport (`goose-mcp`, `goose-server`) and desktop UI (`ui/`).
  2. **First-Class Evaluation (`evals/harbor`)**: Benchmarking and evaluation harnesses live in top-level `evals/`, preventing test drift.
  3. **Strict Binary Entry Points (`bin/`)**: Clear separation between execution binaries and library code.

- **Implications for Our Estate**:
  - We should adopt a top-level **`evals/`** directory standard for benchmarking agent skills and prompt refutations, elevating `tools/skilleval/`.
  - We should maintain strict separation between runtime source ([src/](file:///c:/Users/shova/claude-setup/src)), state telemetry ([state/](file:///c:/Users/shova/claude-setup/state)), and verification instruments ([tools/](file:///c:/Users/shova/claude-setup/tools)).

---

## 3. The Perfect Estate Directory Specification (Target Grade: 10/10)

To achieve a 10/10 mature repository layout across all 31 estate repositories, every repository must conform to the following top-level directory taxonomy with a **maximum depth cap of 4 levels**:

```
<repo-root>/
├── AGENTS.md                  # Single authority for agent rules, boot, & gotchas
├── CLAUDE.md                  # 11-byte pointer -> @AGENTS.md
├── REVIEW.md                  # Code review policy & quality criteria
├── LICENSE                    # Root OSS license
├── quality-contract.json      # 12-domain quality contract specification
├── .alint.yml                 # Machine linter ruleset (enforces max depth 4)
├── .github/                   # Workflows, CODEOWNERS, & issue templates
├── src/                       # Production source packages (Max Depth 4)
│   └── <module_name>/         # Domain logic & core algorithms
├── tests/                     # Unit, integration, & regression test oracles
├── tools/                     # Verification instruments (gate, panel, refute, docmap)
├── state/                     # Append-only JSONL ledgers & sqlite materializations
├── docs/                      # PRDs, ADRs, Specs, Analysis, & Handoffs
│   ├── adr/                   # Architecture Decision Records
│   ├── prd/                   # Product Requirement Documents
│   ├── specs/                 # Technical Specifications
│   ├── analysis/              # Diagnostic & empirical research
│   └── handoffs/              # Dated session handoffs
└── evals/                     # Agent skill evaluation & benchmark harnesses
```

---

## 4. Machine Enforcement via `.alint.yml`

Our directory taxonomy is mechanically checked by `alint check` using three load-bearing rules:

1. **`r3-directory-depth-cap`** (`max_directory_depth`): Caps directory tree depth at **4 levels max**.
2. **`r1-claude-md-is-a-pointer`**: Ensures `CLAUDE.md` is strictly an 11-byte pointer (`@AGENTS.md\n`).
3. **`r4-no-dotless-github-dir`**: Fails if an un-dotted `github/` directory exists.

---

## 5. Implementation Roadmap for Estate Repositories

1. **Deploy `.alint.yml` & `AGENTS.md`**: Deploy to the remaining 30 estate repos (`daily-deep-learning`, `new-recruit`, `oren-roast-hq`).
2. **Elevate `evals/`**: Standardize `evals/` across repos carrying agent skills or LLM prompts.
3. **Keep `src/` Modular**: Ensure past implementations (like `intent-control-plane`) live cleanly under `src/<module_name>/`.
