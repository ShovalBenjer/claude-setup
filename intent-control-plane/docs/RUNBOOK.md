# Runbook: intent-control-plane

Operational guide for the platform brain. Local-first, zero runtime deps.

## Run the control tower (TUI)

```bash
# rich 8-panel TUI (system python3 has rich); live refresh, Ctrl-C to exit
PYTHONPATH="$HOME/projects/intent-control-plane/src" python3 -m intent_control_plane.tower --watch 5
# one-shot
PYTHONPATH="$HOME/projects/intent-control-plane/src" python3 -m intent_control_plane.tower --once
```

Panels: Sessions & Worktrees (+ guard), Codex/a2a usage, Intent-plane health, Estate
standards scorecard (live /17), Orchestration telemetry, Delegation queue, Deployed
endpoints, Context-degradation meter (turns + est tokens vs the ~100k rot threshold).

The `uv` test/lint env has no rich, so it falls back to plain text there by design.

## The self-improving loop

```bash
intent telemetry record --strategy subagent --status green --task "..." --tokens 66000 --ms 106000
intent policy recommend            # cost-aware Thompson pick over strategies
intent policy stats                # per-strategy pass_rate / avg tokens / latency
intent eval passk  --file trials.json     # T4.3 reliability (recorded)
intent eval kappa  --file labels.json     # T4.7 judge calibration
intent eval tier1  --file checks.json     # T4.1 deterministic gate
intent eval trace-diff --file traces.json # T4.4 replay divergence
intent evolve                      # score golden set vs baseline, record the weekly delta
intent retrieve --query "..." --k 3       # ~/docs corpus (name + path + content)
intent repo-map --format json             # estate map + ast import hub
```

## The gate (CI-BIND for a no-remote repo)

```bash
scripts/check.sh                   # ruff + mypy --strict + pytest; installed as .git/hooks/pre-commit
```

## State

All runtime state under `~/.intent` (never in a repo): `intent.db` (events, intent_cards,
evidence, context_packs, eval_results), `ledger/events.jsonl`, `evals/golden`.

## Rollback

Local-only repo, no remote. Revert a change with `git revert <sha>`. The $HOME hook activation
(settings.json Skill hook, intent-capture recall) has backups: `*.bak-2026-07-10`.
