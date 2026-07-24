# intent-control-plane

Local-first intent ledger, context pack, and evidence CLI for Claude, Codex, and Hive
workflows. It is the machine channel behind the session hooks: it captures what each turn
was trying to do, what proof it required, and whether that proof arrived, so a new session
can resume with real state instead of a cold start.

Read-only and additive by design. It records and reports; it never mutates project config
or production data.

## State

All runtime state lives under `~/.intent` (never in a repo):

- `config.toml` - storage, foundry, privacy, eval settings.
- `intent.db` - SQLite store (events, intent_cards, evidence, context_packs, evals, hive bindings, transitions, feedback).
- `ledger/events.jsonl` - append-only raw event ledger.
- `evals/` - golden, replay, mutants, reports.
- `indexes/` - lexical and vector recall.

## Install

```bash
uv sync                 # runtime (zero third-party deps) + dev group (ruff, mypy, pytest)
uv run intent doctor    # verify the store is reachable
```

The `intent` console script is defined in `[project.scripts]`.

## CLI

```
intent init                                  # create ~/.intent and the schema
intent capture   --event-type ... --text ... # append an event
intent extract   --event <id>                # derive an intent card (goal, constraints, proof)
intent context-pack --task ...               # build a retrieval context pack
intent evidence attach --intent <id> --type <t> --status pass|fail|blocked ...
intent eval smoke                            # deterministic eval gate
intent index rebuild | search --query ...    # lexical/vector recall
intent repo-map [root] [--format md|json]    # repo-estate map + import-graph hub
intent log-skill --skill <name> [--session]  # record a skill invocation (usage telemetry)
intent session brief                         # SessionStart digest (used by the hook)
intent jira assess ...                       # ticket relation scoring
intent foundry status | hive sync | retention sweep | state ... | feedback ...
intent list <kind> --limit N | show <id>     # read the store
```

## Layout

```
src/intent_control_plane/
  cli.py          command handlers, argparse wiring, main()
  schema.py       base paths, sqlite connection, schema DDL
  mappers.py      sqlite Row -> dict mappers
  text_index.py   lexical retrieval: sparse term vectors, cosine, session terms
  util.py         ids, timestamps, redaction
  project_map.py  repo-estate scan + stdlib-ast Python import graph (hub)
  standards.py    six-dimension repo scorecard (/17)
  repo_health.py  per-repo health checks
  delegation.py   delegation queue derived from scorecard gaps
  dashboard.py    read-only data providers (a2a usage, intent-plane health) for the tower
  tower.py        live eight-panel control-tower TUI (--once/--watch), incl. context meter
  session_guard.py  parallel-session detection (fail-safe)
  reliability.py  pass^k reliability (PRD T4.3, pure, unwired by design)
  calibration.py  judge kappa / inter-rater agreement (T4.7, pure, unwired by design)
  trace_diff.py   deterministic trace-replay diff (T4.4, pure, unwired by design)
  eval_tiers.py   tier-1 deterministic eval gate (T4.1, pure, unwired by design)
  harness/
    router.py       UserPromptSubmit routing + corpus previews + usage-ranked skills
    self_improve.py  G1 skill-reachability self-improve report
tests/            black-box + unit + property tests, real CLI + sqlite, no mocks
```

`cli.py` re-imports the public names from `schema.py` and `mappers.py`, so call sites and
external importers (for example `from intent_control_plane.cli import session_brief`, used
by the session-brief hook) keep working after the split.

The sim2real rungs (`reliability`, `calibration`, `trace_diff`, `eval_tiers`) are accepted
as pure, tested, unwired-by-design cores; see `docs/adr/0002-*`. Wiring them into the live
eval pipeline is deferred.

## Test, lint, type

```bash
uv run pytest -q                    # full suite (black-box CLI + unit + property)
uv run --group dev ruff check src   # lint
uv run --group dev mypy             # types
scripts/check.sh                    # the whole gate (ruff + mypy + pytest)
```

This repo has no remote, so `scripts/check.sh` is the CI-BIND equivalent. Wire it as a
git pre-commit hook so a red gate blocks the commit:

```bash
ln -sf ../../scripts/check.sh .git/hooks/pre-commit
```

No mocks: tests drive the real CLI against a real temp SQLite store. See
`TESTING-SOTA-2026-GAPS.md` and `CODE-HEALTH-2026-GAPS.md` for the maturity backlog.
