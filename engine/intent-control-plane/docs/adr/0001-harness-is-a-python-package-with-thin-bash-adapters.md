# ADR 0001: The local agent harness is a Python package with thin bash adapters

- Status: Accepted
- Date: 2026-07-09
- Deciders: Shoval

## Context

The local Claude/Codex harness (session hooks, the UserPromptSubmit router, the G1
self-improve loop) grew as bash hooks with embedded python heredocs plus standalone
scripts under `~/.claude/bin` and `~/.claude/hooks`. A 2026-07-09 maturity review found
the decision logic that shapes every session (the router runs on every prompt; the
self-improve report drives the weekly G1 call) was untested python-in-bash: 11 of 19 live
hooks embedded a `python3 <<PYEOF` block, there were zero tests, and 14 dead-stub hooks
sat in the live directory. The operator's own SOTA references name Python (not bash) the
mature choice for glue/automation and prescribe an importable, tested package; bash is not
a candidate application language. A real package already exists, `intent-control-plane`,
described as the machine channel behind the session hooks.

## Decision

The harness is a Python package, not glue.

1. Decision logic lives as pure, typed, tested functions in
   `intent_control_plane.harness` (`router.py`, `self_improve.py`). Behavior is frozen by
   golden tests (verified byte-identical to the prior hook output before the swap).
2. Bash hooks are thin adapters only: read stdin, set `PYTHONPATH` to the package `src`,
   `exec python -m intent_control_plane.harness.<module>`, emit the JSON, fail safe to
   `{}`. No decision logic in bash.
3. Embedded python heredocs are migration debt, not the target. Remaining heredoc hooks
   migrate opportunistically to the same shim shape.
4. `print` in CLI scripts stays (sanctioned by CLAUDE.md); it is not a defect to fix.
5. The package carries its own tooling: `uv`, `ruff`, `mypy`, `pytest`, no third-party
   runtime dependencies.

## Consequences

Positive: the router and self-improve logic are unit- and golden-tested, typed, and
linted; one source of truth; a bug in session-shaping logic now fails a test instead of
silently degrading every session.

Negative: hooks depend on the package being present at `~/projects/intent-control-plane/src`
(a `PYTHONPATH` bootstrap, the same pattern `intent-session-brief.sh` already uses); one
more import boundary to keep acyclic.

Migration state (2026-07-09): `prompt-router.sh` (149 lines to a 13-line shim) and
`self-improve.py` are migrated and tested. `cli.py` was split (1736 to 1453 lines) into
`schema.py` + `mappers.py`. The other heredoc hooks are not yet migrated.
