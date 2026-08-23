# Handoff: external research, and what it changes here

Written 2026-07-27, lane B. Read this if you are picking up any lane that gates a
decision on a score, or that has a human in an approval seat.

## What exists now

| Artifact | Where | What it is |
|---|---|---|
| Source report | `~/Documents/TextToWorkflow_CompileOnce_Research_20260727/report.md` and `.html` | 43 sources, 38 URL verified, 0 suspicious, 7 findings. Commissioned to ground six challenge questions against an external architecture talk |
| Transfer analysis | `docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md` | T1 to T5: what the research says about THIS harness, each verified by running a command rather than reading a doc |
| Tickets | `TODO.md`, section `RT` | Five rows, ranked by value over effort |
| Lessons | `state/lessons.jsonl`, `L-2026-07-27-d` and `-e` | The two findings that are defects in the system rather than ideas for it |
| Broadcast | `state/bus.jsonl`, two messages to ALL | One warn (calibration), one fact (oracle techniques) |

The report itself lives outside the repo on purpose. It is about somebody else's
architecture and only its transfer belongs here.

## The two findings that are about us, not about them

**Our confidence gate has never been calibrated.** `CLAUDE-OS.md:45` gates
autonomy at 0.90 and a proof requirement at 0.70. Nothing on disk has ever
recorded a claimed confidence beside a verified outcome, so the reliability curve
behind those two numbers is not computable from anything we have. The external
evidence says self-reported model confidence sits in the 80 to 100 band almost
regardless of accuracy, which would make ">=0.90 autonomous" a description of the
default path rather than a gate on it. This is the same failure class as
`pointers.py`: a check that cannot fail looks exactly like a check that passes.

**Our human gates are unmeasured.** ADR-0005, ADR-0012 and ADR-0014 all rest on
somebody approving something. `state/` holds 753 gate runs and a machine
refutation ledger and no record at all of a human approve-or-reject. The
automation-bias literature says approval under volume decays into rubber-stamping
while the paperwork still shows a decision, which is precisely the state that
would be invisible to us today.

Neither is fixed. Both are logged and ticketed.

## Per lane

**Lane C, resume engine.** The fit-score is the closest thing in the estate to a
shipped scorer, and `CLAUDE-OS.md` L5 already commits that a shipped scorer needs
ground-truth calibration or it gets labelled a heuristic. RT-1 is the mechanism
for honouring that commitment. Do not tune arm weights or thresholds before the
`{claimed, outcome}` pairs exist, because tuning an uncalibrated signal moves a
number without moving the outcome.

**Lane D, learning.** Two items are directly teachable and both have measured
numbers behind them: metamorphic testing as the technique for checking work that
has no answer key, and calibration as the reason a confident answer and a correct
answer are different objects. The second is a genuine judgment-map entry rather
than a tool.

**Lane A, concierge.** If an intake ever routes on a confidence score, it is
routing on T1. Prefer routing on which lane owns the charter.

**Lane B, here.** RT-3 is an afternoon: print what a green gate does not assert,
using strings that already exist in `quality-contract.json`. RT-5 is the first
metamorphic relation, and `codemap` is the right first target because its
transformation is trivially constructible and its expected invariance is exact.

## What I did not do

None of RT-1 through RT-5 is implemented. This handoff carries analysis and
tickets, not working code.

The ship gate is FAIL on `review` and `prior_art` on the tree that produced this,
neither caused by this work. `prior_art` wants records for ten directories, and
`review` blocks on five high findings, of which two are `shell=True` in
`codemap.py` and two are a SQL pattern matching prose inside `docs/prior-art`
JSON files. No waiver was recorded, because the debt is not this session's to
waive.
