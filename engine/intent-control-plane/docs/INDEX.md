# Docs index: intent-control-plane

The docs spine for the platform brain (docs-control-plane taxonomy). PRD is the control
plane; ADRs record costly-to-reverse decisions; this INDEX is the entry point.

## PRD (the spine)

- [prd/intent-control-plane.md](prd/intent-control-plane.md) - the package's living acceptance table.

## ADRs (decisions)

- [adr/0001-harness-is-a-python-package-with-thin-bash-adapters.md](adr/0001-harness-is-a-python-package-with-thin-bash-adapters.md)
- [adr/0002-knowledge-and-capability-delivery.md](adr/0002-knowledge-and-capability-delivery.md) - CLI-core + MCP-adapter, content-first retrieval, measured skills.
- [adr/0003-measured-self-improving-loop.md](adr/0003-measured-self-improving-loop.md) - the Level-4 closed loop (bandit + wired eval + evolve).

## Code map

See the README "Layout" section for the module map. Entry points:

- `intent` CLI (`cli.py`) - init/capture/extract/context-pack/evidence/eval/index/session/
  repo-map/log-skill/policy/telemetry/retrieve/evolve/list/show.
- `python -m intent_control_plane.tower --once|--watch` - the 8-panel control tower.

## Gate

`scripts/check.sh` (ruff + mypy --strict + pytest) is the CI-BIND equivalent for this
no-remote repo, installed as the git pre-commit hook.
