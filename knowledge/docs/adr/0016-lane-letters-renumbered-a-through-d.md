# ADR-0016: Lane letters renumbered B/C/D/E to A/B/C/D

- Status: accepted
- Date: 2026-07-30
- Supersedes the letter assignments in ADR-0013 only. ADR-0013's topology decision
  (a session names one lane and implements only inside it) is unchanged and still binding.

## Context

ADR-0013 established five lanes, A through E. Lane A was the concierge lane: intent
intake from phone, routing, notifications. It was retired on 2026-07-29 by operator
decision, having never been opened once between ADR-0013 and retirement, because
sessions always started directly in an implementation lane. Its scope folded into the
harness lane as plumbing.

That left the live set running B, C, D, E, with a hole at the front. Every launcher
label, statusline field, and charter heading advertised a set that started at B for a
reason no future reader would know without reading a retirement note. The operator
directed the letters be shifted down to close the hole.

## Decision

The live lanes are A, B, C, D:

| scope | before | after |
|---|---|---|
| concierge / phone intake | A | retired; scope belongs to A |
| claude-setup harness | B | A |
| resume / hiring engine | C | B |
| learning (הסדנה) | D | C |
| content and publishing | E | D |

No charter's scope changed. This is a relabel.

`tools/lib/lanes.py` is the single source of truth for the scheme, the cutover instant
(`2026-07-30T00:00:00Z`), and the old-to-new mapping. `tools/bus/bus.py` keeps a copy of
the current name table so it stays importable from any cwd without path surgery, and
`tests/test_lane_renumber.py` asserts the copy matches, so the duplication cannot drift
silently.

## The part that is not cosmetic

The letters collide across the cutover. `{"lane": "B"}` written on 2026-07-29 means the
harness; the identical row written on 2026-07-31 means the resume engine. At the time of
this decision the ledgers held roughly 400 refutation rows, 33 claim rows, 15 lesson
rows, and 44 bus rows carrying pre-cutover letters.

The historical rows were NOT rewritten. Two reasons, in order of weight:

1. `state/bus.jsonl` is hash-chained and `tools/bus/bus.py verify` checks it. Rewriting a
   `lane` field there breaks the chain, and the correct repair would be to re-chain,
   which is indistinguishable from tampering. The chain exists precisely so that this is
   not quietly possible.
2. Even where the chain does not apply, editing 400 historical rows so a cosmetic rename
   reads as clean is falsifying the record. A row asserts what a lane claimed at a time.
   The letter it used is part of that fact.

So the ambiguity is carried explicitly rather than erased. `lanes.py::resolve` takes the
row's timestamp as a required positional argument, not an optional one defaulting to
now, because a resolver that can be called without a timestamp will be, and the failure
is silent: 396 refutation rows attributed to the wrong lane with no error raised.

## Consequences

- Desktop `.lnk` launchers are regenerated from `make_lane_launchers.py`. Until
  `python tools/workspace/make_lane_launchers.py` is run on this machine, the shortcuts
  on disk still say the old letters and will export a stale `CLAUDE_LANE`. That is
  deployment drift of exactly the kind `docs/CODEBASE-MAP.md`'s payload-versus-live
  distinction warns about, and it is not closed by this ADR.
- Any new reader of a `state/*.jsonl` lane field that does not go through `lanes.py` is a
  defect, not a style preference.
- Dated historical sections in `TODO.md` and `docs/analysis/` keep their original
  letters. They are records of what happened under scheme 1 and are correct as written.
  Forward-looking ownership claims were updated to the new letters.

## Falsifier

If a tool reads a lane letter from a pre-cutover ledger row and reports it as a
scheme-2 lane, this decision has failed in practice regardless of the documentation.
The check: `python tools/lib/lanes.py` must pass, and a grep for `["\']lane["\']` across
`tools/` must show every ledger-reading call site either routing through `lanes.py` or
carrying a comment stating it only ever sees post-cutover rows.
