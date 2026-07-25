---
name: ship-gate
description: >-
  The mandatory procedure before calling any implementation done. Runs the
  real-browser flow audit, the ten-domain SDLC gate (build, unit, types, e2e,
  a11y/UX, security, docs, pipeline, review, perf) and the persona review panel,
  then reads the verdict from the artifacts rather than from the agent. Use
  before any done-claim, before commit-push-pr, and whenever a web app, UI
  change, or user-facing flow is involved.
---

# Ship gate

## Why this exists

An agent built a web app, reported it working, and it was not working. Not a
wrong algorithm: nobody opened it at phone size and pressed the buttons. Nothing
in this setup could have disagreed, because every quality artifact here was
prose. `testing-pyramid` plans layers. `ui-ux-pro-max` recommends palettes.
`completion_gate.py` greps the assistant's own sentence for the word "tested".
`coverage-enforcer` names a companion hook at `~/.codex/hooks/coverage-enforcer.sh`,
which is not on this machine, and says it gates `commit-push-pr`, which is a
37-byte file containing a Linux path. `red-team`, `red-team-review`,
`mutation-runner`, `property-test-gen`, `triage-tests` and `code-simplifier` are
the same: the directory listing shows them, and there is nothing behind the name.
Run `tools/audit/pointers.py scan` to see the current list.

A model asked "does the app work" answers from the source it wrote, which is the
one witness that cannot be trusted. So the four tools below exist to produce a
verdict the agent does not author.

## The one rule

A domain counts as covered only when a command exits zero, or when a named
artifact exists for the current commit. Everything else is UNCOVERED, and
UNCOVERED **fails**. There is no state where the gate passes because nobody got
round to configuring a check, because that is exactly the state this setup was
already in.

## The procedure

Run this before any done-claim. Not after being asked for evidence.

```bash
S=~/claude-setup            # or $CLAUDE_SETUP_ROOT

# 0. once per project: write the contract, then edit it to name real commands
python $S/tools/gate/gate.py init --project .

# 1. if the change touches anything a person looks at, drive it in a real browser
python $S/tools/e2e/flow.py audit http://localhost:3000 --viewport mobile -v

# 2. the full gate. Exits 1 on any red domain, 2 if it cannot run at all
python $S/tools/gate/gate.py run --project . -v
```

`gate.py run` invokes the review panel itself, so step 3 is only for reading the
findings directly or for pointing the panel at a specific base:

```bash
python $S/tools/review/panel.py run --project . --base origin/main -v
```

A green gate writes a row to `state/gate-runs.jsonl` fingerprinted to the exact
working tree. One further edit invalidates it. That is deliberate: a pass earned
three edits ago is not a pass on what is about to ship.

## The instruments

| Tool | What it actually does | Verdict comes from |
| --- | --- | --- |
| `tools/e2e/flow.py` | Opens the real Chrome via CDP, emulates a phone, walks routes, presses every control, watches console and network per interaction | Rendered DOM, CDP events, computed styles |
| `tools/gate/gate.py` | Ten domains, each satisfied by an exit-zero command or a named artifact for this commit | Exit codes and artifacts, never prose |
| `tools/review/panel.py` | 32 named defect patterns in 5 personas over the lines the change ADDED | Pattern hits in the diff |
| `dot-claude/hooks/ship_gate_stop.py` | At the Stop boundary, refuses a done-claim with no green run for this tree | `state/gate-runs.jsonl` fingerprint |
| `tools/audit/pointers.py` | Finds the checks that only look wired: hooks settings.json runs that are missing or are themselves a path, skills that are a path, docs naming paths that do not exist | The filesystem |

Every one has a `selftest` subcommand that plants known defects and fails if any
check misses them. Run them if you change a check:

```bash
python $S/tools/e2e/flow.py selftest      # 11 planted defects, 0 false positives
python $S/tools/gate/gate.py selftest     # 8 gate behaviours
python $S/tools/review/panel.py selftest  # all 32 checks fire, clean code stays clean
python $S/tools/audit/pointers.py selftest
```

Setup maintenance, separate from any one project's gate. Run it after touching
hooks or skills, because a hook that settings.json invokes and that is really a
path to nowhere will fail open and say nothing:

```bash
python $S/tools/audit/pointers.py scan --project $S --include-live \
    --out $S/state/dangling-pointers.tsv
```

## The domains, and what each one wants

`build unit types e2e a11y_ux security docs pipeline review perf`

All except `perf` are always required. The contract may not shorten the list:
deleting a domain from `quality-contract.json` does not remove it, it fails it.

- **build / unit / types** name the project's own commands. If the project has no
  type checker, that is a waiver with a reason, not a silent omission.
- **e2e / a11y_ux** read `flow.py`'s json report. A report from a different
  commit does not count.
- **security** runs a builtin secret scan that reports `file:line pattern-name
  (value withheld)` and never echoes the match.
- **docs** requires the change to have touched documentation. A behaviour change
  with no doc change is a doc change nobody wrote.
- **pipeline** requires CI to run this gate. A gate that only ever runs on the
  machine that wrote the code is a local habit, not a standard.
- **review** requires an artifact naming this commit and a reviewer who is not
  the author. `reviewer` of `self` or `author` fails. `gate.py` runs
  `panel.py` to produce it.
- **perf** is opt-in, because most changes do not have a perf budget and a
  mandatory empty budget teaches people to waive domains.

## Waivers expire

A waiver is a `waived` key inside the domain it waives, not a separate list:

```json
"domains": {
  "perf": {
    "required": true,
    "waived": { "reason": "no latency budget defined for this tool yet",
                "until": "2026-08-31" }
  }
}
```

A waiver with no `until`, or a past one, is a FAIL, not a skip. A permanent
waiver is a disabled check with better manners.

## When the review needs to read for meaning

The panel reads syntax. A wrong algorithm that reads cleanly passes it, and its
own artifact says so in `coverage_boundary`. For a change where being wrong
matters more than being untidy, add a pass that reads for intent:

```bash
python $S/tools/review/panel.py run --project . --allow-external
python $S/dot-claude/bin/external-review-judge.py review --repo . --provider codex
```

`--allow-external` refuses to transmit anything if the diff contains
credential-shaped content, and drops any finding whose file and line are not in
the diff. Per the project contract, never send resumes, recruiting material,
employer code, credentials or PII to Gemini Free Tier.

## What these tools do not check

State this, do not let a green gate imply more than it earned.

- The panel sees added lines, not pre-existing code, and syntax, not intent.
- `flow.py` presses controls it can find in the DOM. A flow behind a login it
  has no credentials for is unvisited, and the report says which routes it
  reached.
- The gate checks that the review artifact exists and reaches a verdict. It does
  not check that the review was good.
- A green run covers one working tree. It says nothing about the deployed
  revision. Production still needs the deploy result and a real service-level
  smoke.

## If the gate is red

Make the domain green, or record a waiver with a reason and an expiry date and
say in the response which domains are waived and why. Do not restate the
done-claim without doing one of those two things, and do not weaken a check to
make it pass.
