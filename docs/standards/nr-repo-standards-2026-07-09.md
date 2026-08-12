# Repo Standards: five dimensions - 2026-07-09

Status: reference. Imported from new-recruit 2026-08-04. Five per-project dimensions; not yet wired to a gate domain here.

Five per-project standards, one per dimension, each a machine-checkable bar scored by
`intent_control_plane.standards` (the compliance scorecard). Derived from the `~/docs`
research cluster. The scorer emits `project-scorecard-2026-07-09.md`; this doc defines
what each check means and where the bar comes from. v1 checks are cheap and deterministic;
each dimension lists the deeper checks a v2 should add.

## 1. Repo organization

Bar: a clean, localizable tree with the layout its class demands.
- v1 checks: `readme`, `docs_dir`, `adr` (docs/adr present), `single_git` (no nested .git).
- Class-specific layout (the standard, not yet auto-scored): product app -> `src/` layout;
  harness/tooling -> tested package + thin `hooks/` (see harness-structure-standard);
  agentic -> the LangGraph layout (`agents/ tools/ prompts/ memory/ state/ workflows/`,
  see Next-Gen AI-Native Repo Structure section 2.2). If a project is agentic, that layout
  is expected. If none of the estate is agentic today, this check is dormant, not skipped.
- Deepen: clean-root check (no tracked artifacts/backups/caches), REPO-MAP present.
- Source: Next-Gen AI-Native Repo Structure, repo-topology, repo-maintenance-file-plan.

## 2. Code health

Bar: automated quality floor, size discipline, minimal duplication.
- v1 checks: `lint_config` (ruff/eslint), `type_config` (mypy/pyright/tsconfig).
- Deepen: `repo_health` LOC budgets (no hard violations), duplication report (jscpd),
  gates actually blocking (tie to CI/CD).
- Source: Code Maturity Ladder, Code Reuse/DRY, `intent_control_plane.repo_health`.

## 3. Documentation

Bar: a reader (human or agent) can orient, and every costly decision is recorded.
- v1 checks: `readme`, `contract_or_map` (docs/API_CONTRACT.md or RUNBOOK.md or REPO-MAP.md),
  `adr` (docs/adr present).
- Deepen: docstring coverage on public API (Google style, per the AI-native docstring
  framework: always on public functions/classes, tool handlers, state schemas, modules;
  skip trivial helpers), generated OpenAPI where there is an HTTP surface.
- Source: Next-Gen AI-Native Repo Structure section 4, Code Maturity Ladder docs axis.

## 4. Testing

Bar: no dark suites; tests exist, run, and gate.
- v1 checks: `has_tests` (files found), `runner` (pytest/bun detected), `gated_in_ci`
  (CI present, blocking, and tests exist).
- Deepen: pyramid-layer presence (unit / property / integration / contract), no-mocks,
  coverage threshold enforced.
- Source: SOTA-TESTING-CRITERIA-2026.

## 5. CI/CD

Bar: a registered pipeline that actually gates, secretlessly, with stage/prod separation.
- v1 checks: `has_ci` (azure-pipelines present), `blocking_gates` (no `|| true`).
- Deepen: secretless (Key Vault refs, no inline secrets), stage/prod branch separation,
  health gate, Codex review + Foundry eval gate where applicable.
- Source: Code Maturity Ladder CI/CD axis, prod-deploy-rules.

## Scoring

`python -m intent_control_plane.standards ~/projects` scores each repo across the five
dimensions (checks passed / total) and lists the failing checks as gaps. It reuses the
facts from `intent_control_plane.project_map`. Both are read-only and regenerable; do not
hand-edit the generated scorecard.

## Known limitations (v1, be honest)

- Root-level config checks miss monorepo subprojects and non-standard config locations
  (a repo with nested `ruff`/`mypy` config scores 0/2 falsely). Needs per-subproject scan.
- Monorepos (`ORM-AGENT`, `video-understanding`) come back `unclassified`; per-subproject
  classification is the v2.
- Test-file counts can be inflated by nested vendored/generated tests; treat counts as a
  signal, not a verified inventory.
