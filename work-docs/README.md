# Shoval Docs Index

This folder is the global knowledge surface for setup, operating rules, research, audits, and reusable project context. `reground` should read this file first, then open only the task-relevant docs.

## Primary Lanes

| Lane | Path | Use |
|---|---|---|
| Core setup | `core/`, root core files | Durable workstation, architecture, testing, deployment, and AI-native engineering rules. |
| Specs | `specs/` | Source-of-truth plans and implementation deltas. |
| Research | `research/`, root SOTA research files | Long-form technical research and SOTA references. |
| Pipelines | `pipelines/` | CI/CD, notification templates, deploy gates, pipeline snippets. |
| Audits | `audits/` | Evidence-backed inspections and maturity reports. |
| Reflections | `reflections/` | Session learnings, post-mortems, and handoffs. |
| Eval results | `eval-results/`, `qa/` | Test/eval artifacts and QA scripts. |
| Wiki drafts | `wiki/`, `wiki-drafts/` | Azure DevOps Wiki content and drafts. |

## Core Files To Read First

- `2026-06-28-work-general-setup_4614.md`
- `specs/2026-06-25-local-intent-control-plane.md`
- `specs/2026-06-28-work-general-mojuco-artifixer-foundry-plan.md`
- `SOTA-TESTING-CRITERIA-2026.md`
- `testing_practices.txt`
- `project-maturity-audit-2026-07-01.md`
- `AI_NATIVE_ENGINEERING_TODO.md`
- `Production AI & Software Engineering  The June 2026 State of the Art.md`

## Placement Rules

- New durable setup or operating-system docs go in `core/` or `specs/`.
- New CI/CD scripts, notification scripts, and reusable pipeline snippets go in `pipelines/`.
- Long-form research goes in `research/` unless it is a canonical root reference already used by other docs.
- One-off reports and audits go in `audits/`, `eval-results/`, or `reflections/`.
- Avoid adding loose scripts at the docs root. Keep compatibility symlinks only when an old path may be referenced.
