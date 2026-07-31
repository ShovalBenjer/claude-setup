# Estate Directory & Repository Catalog

This catalog outlines the structured directory taxonomy, repository roles, depth limits, and consolidation status across `C:\Users\shova\claude-setup` and `C:\Users\shova\Downloads`.

---

## 1. Directory Structure Rules & Depth Enforcements

- **Max Directory Depth Cap**: **4 Levels** (Enforced by `.alint.yml` rule `r3-directory-depth-cap`). Deeply nested subtrees past 4 levels (e.g. `root/dir1/dir2/dir3/dir4/file`) are prohibited.
- **Canonical Top-Level Root Directories**:
  - `src/` — All production source modules (including consolidated `intent_control_plane`).
  - `docs/` — Specifications, PRDs, ADRs, and handoffs.
  - `tests/` — Executable test oracles.
  - `.github/` — Workflows, CODEOWNERS, issue templates.
  - `state/` — Append-only JSONL ledgers.
  - `tools/` — Verification instruments.
  - `scripts/` — One-shot operator scripts.

---

## 2. Directory Triage Matrix (`C:\Users\shova\claude-setup`)

| Directory | Type | Max Depth | Status / Role | Action Taken |
|---|---|---|---|---|
| [src/intent_control_plane/](file:///c:/Users/shova/claude-setup/src/intent_control_plane) | Source | 3 | **CONSOLIDATED** — Primary intent control plane module. | Merged into canonical `src/intent_control_plane/`. |
| [docs/](file:///c:/Users/shova/claude-setup/docs) | Documentation | 3 | **ACTIVE** — ADRs, PRDs, Specs, Analysis, and Handoffs. | Documented in `docs/DOCMAP.md`. |
| [tests/](file:///c:/Users/shova/claude-setup/tests) | Tests | 2 | **ACTIVE** — Root verification test suite. | Verified with 100% green tests. |
| [tools/](file:///c:/Users/shova/claude-setup/tools) | Instruments | 3 | **ACTIVE** — Gate, panel, bus, refute, codemap, docmap verification instruments. | Active. |
| [state/](file:///c:/Users/shova/claude-setup/state) | Telemetry | 2 | **ACTIVE** — Append-only JSONL state ledgers & manifests. | Unchanged. |
| [dot-agents/](file:///c:/Users/shova/claude-setup/dot-agents) | Payload | 4 | **PAYLOAD** — Agent skills payload tree. | Kept as payload tree. |
| [dot-claude/](file:///c:/Users/shova/claude-setup/dot-claude) | Payload | 4 | **PAYLOAD** — Committed copy of `~/.claude`. | Kept as payload tree. |
| [dot-codex/](file:///c:/Users/shova/claude-setup/dot-codex) | Payload | 4 | **PAYLOAD** — Committed copy of `~/.codex`. | Kept as payload tree. |
| [work-docs/](file:///c:/Users/shova/claude-setup/work-docs) | Research | 3 | **HISTORICAL** — SOTA research documents and past work docs. | Documented in DOCMAP. |
| [master-plans/](file:///c:/Users/shova/claude-setup/master-plans) | Planning | 2 | **HISTORICAL** — Dated master plans (2026-05-*). | Retained for reference. |

---

## 3. Directory Triage Matrix (`C:\Users\shova\Downloads`)

| Directory / File | Type | Status | Recommended Disposition |
|---|---|---|---|
| `claude-mastery-research/` | Research Hub | **ACTIVE** | Keep as reference research for book catalogs & SQLite knowledge. |
| `daily-deep-learning/` | Learning Log | **ACTIVE** | Retain as active deep learning study log repo. |
| `new-recruit/` | Research / Video | **RESCUED** | Video-understanding and SOTA video gen research; needs private git remote. |
| `resumes_2026/` | Career | **ACTIVE** | Resume prompt grill & change plan files; sync with profile README. |
| `work-oren/` | Client / Project | **HISTORICAL** | Retain in Downloads; do not import into `claude-setup`. |
| `talk-2807-transcripts/` | Transcripts | **HISTORICAL** | Audio transcripts from 2026-07-28 session. |
| `AI PR Review Prompt Best Practices.md` | Research File | **STANDALONE** | Copy to `work-docs/` if needed for repo rules. |
| `thesis_review_2026-07-30.md` | Thesis | **STANDALONE** | MSc thesis review document. |
| `תדרוך_ אסטרטגיות אופטימיזציה Taboola.md` | Briefing | **STANDALONE** | Taboola performance optimization briefing. |
