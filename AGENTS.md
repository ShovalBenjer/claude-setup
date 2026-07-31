# AGENTS.md

This file provides single-authority guidance to AI agents (Claude, Codex, etc.) working in this repository.

## What this repo is

The harness itself: rules, hooks, skills, schedulers, review fabric, and the tools that check whether any of it actually works. There is no application here, nothing is served, and there is no build output. Most "code" is a verification instrument whose job is to disagree with an agent's own report.

The `dot-*` trees are payload, not live config. `dot-claude/` is the committed copy of `~/.claude`, `dot-codex/` of `~/.codex`, `dot-agents/` the agent skills tree. Editing a file under `dot-claude/` changes nothing about a running session until it is deployed, and the live tree can also drift ahead of the repo. `python tools/audit/skills_sync.py check` measures that drift in both directions.

## Starting a session

`docs/SESSION-BOOT.md` is the boot path. Two steps in it are easy to skip and are the ones that keep failing:

- Name your lane from `docs/charters.md` (harness work is lane A; the letters were renumbered from B/C/D/E on 2026-07-30 by ADR-0016, so an older row saying B means this lane) and append a claim row to `state/claims.jsonl` before starting. Doing another lane's work is the most frequently logged entry in `state/lessons.jsonl`.
- Ground truth is git plus the files under `state/`, never a doc. `docs/analysis/` and `work-docs/` are dated snapshots and several are knowingly stale.

Design decisions run `/diverge` first (charters rule 2). Work ships through a PR, not a push to main (ADR-0012).

## Commands

```bash
python tools/gate/gate.py run --project . -v   # the full 12-domain contract
python tools/gate/gate.py status               # last verdict from the run ledger

python -m pytest tests/ -q                     # root suite, ~47s, 70 tests
python -m pytest tests/test_codemap.py -q      # one file
python -m pytest tests/test_codemap.py::test_name -q
cd intent-control-plane && uv run pytest -q    # the only packaged subproject
cd intent-control-plane && uv run ruff check . && uv run mypy   # lint/types exist only here
```

Every oracle carries its own selftest, and CI runs them as named steps so a regression is attributable:

```bash
python tools/gate/gate.py selftest
python tools/review/panel.py selftest
python tools/bus/bus.py selftest
python tools/refute/refute.py selftest
python tools/skilleval/run.py selftest
python tools/snapshot/snap.py selftest
python tools/audit/skills_sync.py selftest
python tools/audit/mutate.py --spec all        # proves those selftests can go red; slowest check
```

Repo upkeep that the gate reads:

```bash
python tools/map/codemap.py check              # directory purposes + map freshness
python tools/map/codemap.py write              # regenerate after adding a directory
python tools/map/codemap.py prior-art          # 300+ line components owe a record
python tools/review/panel.py run --project .   # writes state/reviews/<sha>.json
python tools/audit/pointers.py scan            # hooks and skills that are dead paths
python tools/refute/refute.py run              # run each claim's own falsifier
python tools/slop_lint.py <file.md>            # prose gate, exit 1 on hits
```

## How verification is arranged

`quality-contract.json` declares the domains; `docs/QUALITY-CONTRACT.md` holds the reasoning for each scope. The contract carries no measured status on purpose, since a file that states its own result goes stale the first time somebody fixes something. A domain counts as covered only when a command exits zero or a named artifact exists for the current commit. Unconfigured is UNCOVERED, and UNCOVERED fails.

The layering is contract, then oracle, then that oracle's selftest, then a mutation that must turn the selftest red. `.github/workflows/ship-gate.yml` splits these across three jobs and its header comment states exactly what each job does and does not cover. Read that comment before renaming or wrapping anything in it: the `pipeline` domain greps the workflow files for a literal `gate.py run` invocation.

## Gotchas

- `docs/CODEBASE-MAP.md` is generated. A hand edit reads as drift and fails `codemap.py check`. To change a directory's purpose, edit that directory's own `SKILL.md` or `README.md`, or its row in `docs/dir-purpose.txt`. A row beside a self-documenting directory is an error, not an override.
- A new tracked directory with no stated purpose fails the gate. A new Python component over 300 lines owes `docs/prior-art/<name>.json` with real named alternatives and an expiry date; an empty alternatives list fails.
- The `review` domain matches its artifact by commit sha rather than by tree, so a verdict written against a dirty tree keeps reading as current for that commit.
- Roughly half of `dot-claude/hooks` and about a dozen `dot-claude/skills` entries are one-line stubs naming `~/.codex` paths that do not exist on this machine. A hook that cannot run fails open and reports nothing. `tools/audit/pointers.py scan` is the check for it.
- Windows specifics, both documented in `docs/QUALITY-CONTRACT.md` and deliberately unwaived: three `intent-control-plane` tests fail on a sqlite handle still open at `TemporaryDirectory` teardown, and `tools/whatsapp/cdp_driver.py` plus `tools/setup_token_pty.py` import packages declared in no manifest, so the `build` domain does not claim those two run.
- Prose is gated. No emoji, and `tools/slop_lint.py` fails on a spaced em or en dash used as a connector, plus a banned-phrase list.
- `state/*.jsonl` are append-only ledgers. `state/bus.jsonl` is hash-chained and `python tools/bus/bus.py verify` checks it, so rewriting history there is visible.

## Where the rest lives

`CLAUDE-OS.md` is the spine (layers L0 to L8, the deep-work protocol, the supersession table). `docs/INDEX.md` indexes the PRDs, specs, and 15 ADRs; the ones that bind day-to-day work are 0005 enforcement over prose, 0010 disk is memory, 0012 autonomy ships only via the PR gate, and 0013 the lane topology. `TODO.md` is the single ticket list and `tools/selfimprove/scan.py` ranks what to pick up next.
