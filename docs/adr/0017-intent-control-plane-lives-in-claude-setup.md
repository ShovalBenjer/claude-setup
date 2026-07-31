# ADR-0017: intent-control-plane is authoritative in claude-setup; the new-recruit copy is redundant

- Status: accepted
- Date: 2026-07-30
- Decided by: operator, on being shown the measurement
- Unblocks: AUTO-06 (`state/ecosystem.db` bootstrap), AUTO-04 (work-claims), AUTO-19 (FleetView),
  and Phase F4 of `docs/prd/2026-07-30-consolidation-and-migration.md` (the repo migration)
- Extends ADR-0011 and ADR-0013. Supersedes nothing.

## Context

`intent-control-plane` existed at two paths, both touched since 2026-07-01:

- `C:\Users\shova\claude-setup\intent-control-plane`
- `C:\Users\shova\Downloads\new-recruit\projects\intent-control-plane`

`docs/HANDOFF-2026-07-30-session-close.md` ranked this the highest-value unknown on the estate and
said plainly that nothing should be merged until it was answered, because both were live and a
wrong merge loses work. `TODO.md` AUTO-06 bootstraps `state/ecosystem.db` from this package's
schema, so the ambiguity blocked the substrate, and the repo migration would have moved the
directory containing the second copy.

## The numbers that were quoted, and why they were wrong

The comparison in circulation was "1,037 files under claude-setup, 616 under new-recruit", which
reads as new-recruit being the smaller copy. Both halves were misleading:

- claude-setup's 1,037 counted its `.venv`. Its **source** count is 90.
- new-recruit's 616 counted 528 files inside `.claude/worktrees`, which are git worktree
  duplicates of itself. Its **source** count is also 44 in `src`, identical to claude-setup's.

So the figure that looked like a 1.7x advantage for claude-setup was, read naively, a 7x advantage
for new-recruit, and both readings were artefacts of counting virtualenvs and worktrees as source.

A second artefact nearly reversed the verdict again. A byte-level hash comparison of the 105 shared
files under `src`, `tests`, `scripts` and `docs` reported **105 of 105 differing**, which reads as
two divergent codebases. Every file was 1 to 2 percent larger on the claude-setup side, which is
the signature of CRLF against LF rather than of content. Normalised, the real figure is **101
identical, 4 differing**.

That line-ending trap appeared three separate times in the session that produced this ADR: here,
in a stash-reconstruction check that falsely reported 9 of 9 files mismatching, and in a claim that
eol normalisation would break the `bus.jsonl` hash chain (it does not; `bus.py verify` reports the
chain intact against the normalised copy, because it hashes parsed JSON rather than bytes). Any
future cross-platform file comparison in this estate should normalise first or it will manufacture
a difference that is not there.

## Decision

**`claude-setup/intent-control-plane` is the single authoritative copy.**
`new-recruit/projects/intent-control-plane` is redundant and may be deleted.

Nothing is merged. There is nothing to merge.

Three independent grounds, any one of which would be sufficient:

1. **Charter.** `docs/charters.md` assigns Lane A "rules, hooks, skills, schedulers, review fabric,
   a2a bridges, ecosystem.db, FleetView, autonomy rails, and intent intake/routing surfaces". A
   control plane for intent capture is an intake and routing surface by definition, so it is Lane A
   infrastructure. Lane B owns `~/Downloads/new-recruit` as the resume engine: hiring machine, arms,
   applications, job scans. Harness infrastructure living inside the resume engine is a charter
   violation regardless of which copy has more code.
2. **Deployment.** The live `~/.claude/settings.json` runs
   `claude-setup\intent-control-plane\.venv\Scripts\python.exe` against
   `claude-setup\tools\intent\capture_turn.py` on `UserPromptSubmit`. The claude-setup copy is
   already the one executing on every prompt, so it is authoritative in practice and the question
   was only ever about the paper record.
3. **Content.** After normalisation: 101 of 105 shared files identical, 2 files exist only in
   claude-setup (`tests/test_intent_capture_slice.py`, `tests/test_schema.py`), **0 files exist
   only in new-recruit**, and in all 4 differing files claude-setup is both newer and a
   near-superset:

   | file | claude-setup | new-recruit | lines only in claude-setup | lines only in new-recruit |
   |---|---|---|---|---|
   | `cli.py` | 1,442 lines, 2026-07-29 | 1,326 lines, 2026-07-13 | 125 | 9 |
   | `schema.py` | 277 lines, 2026-07-29 | 230 lines, 2026-07-13 | 48 | 1 |
   | `test_local_alpha.py` | 734 lines, 2026-07-25 | 725 lines, 2026-07-13 | 11 | 2 |
   | `codebase_map.py` | 118 lines, 2026-07-25 | 112 lines, 2026-07-13 | 7 | 1 |

   The 13 total lines "only in new-recruit" are the pre-edit forms of lines the claude-setup copy
   changed, not unique work.

`cli.py` and `schema.py` on the claude-setup side are currently **uncommitted** (` M` in
`git status`), so those newer edits are the thing at risk in this decision, not anything in
new-recruit. They should be committed before the migration moves the tree.

## Consequences

- **AUTO-06 is unblocked.** `state/ecosystem.db` seeds from
  `claude-setup/intent-control-plane/src/intent_control_plane/schema.py`, at 277 lines, the newer
  of the two. Note that `docs/specs/2026-07-30-data-architecture-and-orchestration.md` narrows
  ADR-0011's scope: five of twelve ledgers migrate, `bus.jsonl` is structurally barred by its hash
  chain, and `gate-runs.jsonl` is the first tenant because it is the only ledger with real growth
  and a real query shape.
- **Phase F4 is unblocked.** The migration may move `new-recruit`, since its copy is redundant.
- **`new-recruit/projects/intent-control-plane` becomes a reclamation row**, action
  `delete-artifact`, verified by this ADR. Its 528 `.claude/worktrees` files go with it. It is not
  an archive candidate, because archiving implies content worth keeping and there is none.
- **The venv does not travel.** claude-setup's copy carries a Windows `.venv` referenced by an
  absolute path in the live hook. Moving the repo to ext4 breaks it, and intent capture then fails
  silently. Rebuilding it is Phase F3 and its acceptance is a `state/hook-fires.log` line, not a
  settings diff.

## Falsifier

If a file is later found in `new-recruit/projects/intent-control-plane` that is absent from
`claude-setup/intent-control-plane` and is not a worktree or virtualenv artefact, this decision was
made on an incomplete comparison and the deletion was wrong. The check, run before any deletion:

```bash
python - <<'EOF'
import hashlib, pathlib
A = pathlib.Path(r"C:\Users\shova\claude-setup\intent-control-plane")
B = pathlib.Path(r"C:\Users\shova\Downloads\new-recruit\projects\intent-control-plane")
def coll(root):
    out = {}
    for sub in ("src", "tests", "scripts", "docs"):
        d = root / sub
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if f.is_file() and ".venv" not in f.parts and "__pycache__" not in f.parts:
                out[f.relative_to(root).as_posix()] = hashlib.sha256(
                    f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return out
a, b = coll(A), coll(B)
print("only in new-recruit:", sorted(set(b) - set(a)))
EOF
```

It must print an empty list. Note the `.replace(b"\r\n", b"\n")`: without it this check reports
every file as differing and proves nothing.
