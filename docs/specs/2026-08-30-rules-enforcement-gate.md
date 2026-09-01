# Rules-as-Enforcement Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** rules_enforcement

## Problem

The 26 rules in `dot-claude/rules/` are prose: the LLM reads them and complies
(or not). The existing `rules` gate domain guards deployment integrity (drift and
shrinkage) but never checks whether the codebase actually complies with what the
rules say. A rule like "no decorative emoji" has no mechanical oracle.

## Solution

A rule file may now carry a YAML frontmatter block with an `enforce:` key that
declares a machine-checkable predicate. `tools/audit/rules_enforce.py` reads
each rule, extracts the frontmatter, and runs the predicate. Rules without
frontmatter are prose-only and skipped (not failed).

Two enforcement modes:

- `deny_pattern` + `glob` + `scope`: a regex that must not appear in matching
  files. Uses ripgrep with a Python fallback.
- `cmd`: a shell command whose exit code decides (0 = pass, nonzero = fail).

A new gate builtin `rules_enforcement` captures the checker's output as evidence.

## Schema

```yaml
---
enforce:
  deny_pattern: "breakpoint\\(\\)"
  glob: "*.py"
  scope: "tools"
---
```

```yaml
---
enforce:
  cmd: "python tools/slop_lint.py CLAUDE-OS.md"
---
```

## Initial annotations

Three rules annotated as proof of concept:

- `no-emojis.md`: denies emoji in `docs/specs/` and `docs/prd/` markdown
- `calibrated-claims.md`: runs slop_lint against CLAUDE-OS.md and AGENTS.md
- `docs-control-plane.md`: checks that INDEX.md, CODEBASE-MAP.md, DOCMAP.md,
  specs/ and prd/ exist

## Scope

- `tools/audit/rules_enforce.py`: checker with `check`, `selftest` CLI
- `tools/gate/gate.py`: `rules_enforcement` builtin, registered in `BUILTINS`
- `quality-contract.json`: `rules_enforcement` domain entry
- `dot-claude/rules/{no-emojis,calibrated-claims,docs-control-plane}.md`:
  enforcement frontmatter added

## Non-goals

- Annotating all 26 rules (incremental adoption; prose-only rules are skipped)
- Blocking on unannotated rules (absence of frontmatter is not a failure)
- Replacing the existing `rules` domain (that guards deployment integrity)
