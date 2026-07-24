# ~/docs Index and Standard

The index of `~/docs`. Referenced from `~/.claude/CLAUDE.md` so the setup actually consumes
this knowledge instead of leaving it inert. One-liners are derived from filenames and prior
use, not a fresh read of each file. Last curated: 2026-07-07.

## Standard (how this directory works)

- Naming: dated work is `YYYY-MM-DD-topic.md`; evergreen references are `TOPIC.md` (uppercase).
- Root holds active, cross-cutting docs and the SOTA research corpus. Keep root lean: when a
  piece of work is finished, move it into the matching subdirectory.
- Subdirectory taxonomy: `audits/` (dated audits), `research/` (deep-research reports),
  `specs/` (requirement-of-record and PRDs, the control plane), `reflections/`
  (heidegger-reflect output), `meetings/`, `jira-tasks/` (local drafts), `pipelines/`,
  `qa/`, `eval-results/`, `wiki/` + `wiki-drafts/`, `diagrams/`, `azure-snapshots/`,
  `core/`, `cs-agent/`, `root-cleanup-*/` (archived clear-outs).
- Cruft: Windows `*:Zone.Identifier` files are download-provenance junk, safe to delete.

## SOTA research corpus (reference these; do not re-derive from memory)

Wired-vs-unused status of the tools these name is tracked in
`research/2026-07-07-claude-setup-gap-analysis.md`.

- `Production AI & Software Engineering  The June 2026 State of the Art.md` : agentic-coding,
  eval, observability, retrieval, supply-chain SOTA.
- `The Complete Principal Engineer Curriculum  June 2026 — Systems, Architecture, Product, and AI.md`
  : architecture, ADRs, fitness functions, SRE, distributed patterns.
- `SOTA-TESTING-CRITERIA-2026.md` : the 8-layer test pyramid plus trajectory and adversarial planes.
- `SOTA Video Testing Pyramid 2026.md`, `SOTA Voice Testing Pipeline 2026.md` : media QA metrics.
- `Text2SQL Token Optimization  The June 2026 Market Gap & How to Build the Missing Layer.md`
  and `Excellent SQL Engineering — June 2026 State of the Art.md` : text2SQL and SQL engineering.
- `Next-Gen UI UX  2026 Skills, Libraries & Open-Source Arsenal.md` and
  `SOTA Subtle UI UX Enhancements for Live Dashboards — Psychology & Behavioral Science Proof.md`
  : frontend libraries, motion, dashboard UX.
- `GD Coverage Metric 2030  Neuro-Symbolic, Psychological, Mathematical, and Bibliometric Research Roadmap.md`
  : coverage-metric research.
- `Lightweight Open-Source Video Editing & QA Libraries for Frame-Accurate Logo Tracking.md`.
- `deep-research-report (2).md` (agent eval and testing), `deep-research-report (3).md`
  (high-risk MCP platform testing).

## Plans and design

- `2026-06-09-autonomous-azure-agent-fleet-design.md`, `2026-06-09-explicit-program-of-work.md`,
  `2026-06-09-CONSOLIDATED-adopt-backlog.md`, `2026-06-10-IMPLEMENTATION-PLAN.md`,
  `2026-06-10-campaign-analysis-report-setup-design.md`, `2026-06-10-REVIEW-QUEUE.md`,
  `2026-06-10-OVERNIGHT-STATUS.md`, `agent-call-tracker-NIGHT-PLAN-2026-07-07.md`,
  `AI_NATIVE_ENGINEERING_TODO.md`, `ai-native-code-level-scout-2026-07-05.md`,
  `auto-mode-tasks-2026-05-12.md`, `weekly-plan-2026-05-10.md`,
  `2026-06-28-work-general-setup_4614.md`.

## Audits and state

- `project-maturity-audit-2026-07-01.md`, `REPO-AUDIT.md`, `COMPLIANCE-AUDIT.md`,
  `2026-07-07-agent-call-tracker-session-postmortem.md`, `eval-findings-2026-05-11.md`,
  `2026-06-08-storage-mitigation-runbook.md`.

## Setup and reference

- `ARCHITECTURE.md`, `KNOWLEDGE-BASE.md`, `MODEL-MIGRATION-PLAN.md`, `FOUNDRY-EVAL-CI-PLAN.md`,
  `auth-setup.md`, `Auth_vlad.txt`, `cloudflare_pipeline.txt`, `company_context.txt`,
  `example-pipeline-cs-agent.txt`, `testing_practices.txt`,
  `foundry-chatwoot-alignment-2026-04-16.md`, `prompt_v96_optimization_suggestions.md`,
  `DEBUG_HANDOVER_20260112.md`, `cs-agent-explainer.html`, `database-schema-reference.xlsx`.

## Career and profile

- `SHOVAL-BENJER-5MO-CONTEXT-2026-05-08.md`, `SHOVAL-CV-PROJECT-INVENTORY-2026-05-28.md`,
  `SHOVAL-FIT-ANALYSIS-2026-05-08.md`.

## Study and learning

- `ai-103-study-tracker.md`, `fundamentals-mastery-plan.md`.

## Subdirectories (open the dir for its dated contents)

`audits/` `research/` `specs/` `reflections/` `meetings/` `jira-tasks/` `pipelines/` `qa/`
`eval-results/` `wiki/` `wiki-drafts/` `diagrams/` `azure-snapshots/` `core/` `cs-agent/`
`root-cleanup-2026-05-28/`.
