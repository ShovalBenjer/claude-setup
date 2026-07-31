# Inventory reconciliation, and the two layers that were dark

Date: 2026-07-31. Lane A. Point-in-time analysis per docs-control-plane, an input to
TODO.md, not a spec and not a decision.

Written because the operator asked for an architecture pass across skills, plans,
contracts and phases, with every file under `docs/` visited. What that produced was
mostly not a plan. It was a measurement showing that two verification layers were
inert and that the document spine indexes a fifth of the documents it is the spine for.

TODO.md already carries the warning this document had to answer, filed 2026-07-29 as
L-2026-07-29-h:

> Inventory reconciliation BEFORE the next build plan ... the competing frame this
> evidence supports, and which the architecture plan suppressed, is that inventory
> bloat is the core problem and adding tickets is the wrong shape.

So the deliverable is reconciliation first. Rows closed by measurement are named in
section 6; the new rows are four, and each one is a defect found by running something.

## 1. Coverage of this pass, stated before any finding

162 tracked files under `docs/`, 2,047,263 bytes. Read as follows, because claiming to
have read two megabytes evenly would be the absence-claim class in reverse:

| class | n | how it was read |
|---|---|---|
| prior-art records | 39 | structurally, every record, every field: component, verdict, recheck_after, alternatives count, absorption fields |
| generated maps | 2 | not read; they are output, and `codemap.py check` plus `docmap.py check` are their oracles |
| registries | 4 | `dir-purpose.txt`, `doc-status.txt`, `claims-verify.jsonl` targets, `icepanel-intent-to-done.json` |
| spine | 9 | in full: INDEX, SESSION-BOOT, charters, SYSTEM-MAP, QUALITY-CONTRACT, EXECUTION-PLAN, OPERATOR-RUNBOOK, taste, ESTATE-DIRECTORY-CATALOG |
| ADRs | 20 | title, status, supersession line, each one |
| specs | 18 | title, status, ticket, length; the Zion board spec in full |
| everything else | 70 | headline pass: title, declared status, and the first numeric claim in the first 60 lines |

`TODO.md` and `CLAUDE.md` were read in full although they sit outside `docs/`, because
every finding below lands in one of them.

What this does not cover: the body of the 33 analysis documents and 16 handoffs. Their
titles and lead claims were read, not their arguments. Anything below that cites one of
them cites a line I read.

## 2. The refutation layer was returning zero information, and had been since the move

```
python tools/refute/refute.py run
26 claims: 0 held, 0 REFUTED, 26 broken verifier
```

Every claim in this repository that carries a falsifier had a falsifier that could not
start. One cause: each row declared `shell: "pwsh"`, the runner defaulted to `pwsh` when
the field was absent, and neither `pwsh` nor `powershell` exists under WSL.

The tool did not lie about it. Its own output says a broken verifier is not a pass, the
claim stays unknown, and unknown counts toward the exit code. Nothing was falsely
certified. What was lost is the layer: on the host the operator now works from, no claim
here had a working check, which is precisely the failure `refute` was built to catch,
turned on the checker.

Two of the seven PowerShell-native verifiers were worse than unportable. They resolved
`$env:USERPROFILE\claude-setup`, the Windows clone, a different working tree from the WSL
one. With pwsh present they would have reported on a checkout the session was not
editing, and reported it as a pass.

Repaired in `aeaecd3`. Now:

```
26 claims: 21 held, 5 REFUTED, 0 broken verifier
```

The five refutations are the product and are listed in section 5. They are not fixed
here; a refutation is a finding, and closing it in the same commit that made it visible
would destroy the evidence that it was ever hidden.

## 3. The document spine indexes 22 of 112 documents

`docs/INDEX.md` opens with "Generated-from-docs wiki spine (docs-control-plane rule). One
TODO, one INDEX." `SESSION-BOOT.md` sends a fresh session to it. Measured against what is
on disk:

| group | on disk | in INDEX | missing |
|---|---|---|---|
| specs | 18 | 7 | **11** |
| analysis | 33 | 2 | **31** |
| reflections | 6 | 0 | **6** |
| handoffs and top-level | 31 | 4 | **27** |
| ADRs | 20 | 20 | 0 |
| PRDs | 3 | 2 | 1 |
| standards | 1 | 1 | 0 |

The ADR row is the control. Someone has kept ADRs indexed by hand for twenty entries, so
the mechanism is not impossible, it is unenforced everywhere else.

Two of the missing are structural rather than merely absent: `QUALITY-CONTRACT.md` and
`SYSTEM-MAP.md` are not linked from the spine that claims to index the spine.

`docs/DOCMAP.md` already computes this. Its header line reads
`reachable from docs/INDEX.md: 38 (3%)` across the whole repository. So the number has
been generated, printed and committed on every regeneration, and nothing fails on it.
That is the shape of every defect in this document: measured, visible, and not wired to
anything that stops.

## 4. Eight of eighteen specs declare no status

`docs/doc-status.txt` and `docmap.py` derive a status by class when a document does not
declare one, so `docmap check` passes. A class-derived status answers "what kind of
document is this", never "is this still true". These eight say nothing about themselves:

`2026-07-29-architecture-build-plan.md`, `-v2.md`, `2026-07-29-intent-traceability.md`,
`2026-07-29-trace-model-sacred-timeline.md`,
`2026-07-30-data-architecture-and-orchestration.md`,
`2026-07-31-agentic-directory-standard-sota.md`, `2026-07-31-project-federation.md`,
`2026-07-31-research-corpus-and-cache.md`.

Two of them supersede each other by title (`architecture-build-plan` and its `-v2`,
merged the same day) and neither carries the fact.

## 5. Five refutations, now visible

Reported verbatim from the first run that could run. Each is a claim this repository was
making that its own checker rejects.

| id | claim | what the checker found |
|---|---|---|
| C-003 | every hook in live settings.json resolves to a file that exists | 1 of 12 registrations unresolved: `PreToolUse` points at `/home/shov/claude-setup/tools/hookgate/target/release/hookgate`, and no script path was found there |
| C-008 | the hiring funnel has a real ledger with rows in every funnel table | `ledger.sqlite` missing at `~/Downloads/new-recruit/hiring_engine/ledger.sqlite` |
| C-012 | live `~/.claude/CLAUDE.md` and settings.json match the recorded baseline | `CLAUDE.md` DELETED since baseline; `settings.json` rewritten, 7440 to 6807 bytes |
| C-015 | bus.py's selftest is proven able to fail across its mutation spec | mutation run reports failures against the current tree |
| C-025 | the pre-write snapshot is intact, so the pending settings write stays revertable | many `agents/*.md` MISSING from the snapshot |

C-012 is the one worth pausing on. The baseline was taken 2026-07-29 and the live
`~/.claude/CLAUDE.md` has since been deleted, which means the global instruction file the
harness reasons about is gone and nothing noticed for two days. C-025 says the rollback
source for a settings write is incomplete, which is the same class: a safety net recorded
as present and measured as partial.

## 6. Rows that measurement closes

Numbers in TODO.md and SYSTEM-MAP.md that are no longer true. Each was re-measured today.

| where | recorded | measured 2026-07-31 |
|---|---|---|
| TODO, "bus inbox never read" | 19 unread to lane A | **0**; `bus.py inbox` returns empty, chain intact |
| TODO, "scan.py false positives" | top 3 proposals are phantom hooks | **0**; fixed by the `_under_wsl` probe in 24e01de |
| SYSTEM-MAP, VERIFIED | `docs/taste.md` does not exist, zero /diverge picks | exists, 51 lines, **1** recorded pick |
| SYSTEM-MAP, VERIFIED | live model is `claude-fable-5[1m]` | `opus[1m]`, effort `low` |
| SYSTEM-MAP, VERIFIED | only 4 hooks are live-wired | **7** events, 7 registrations |
| CLAUDE.md commands | "the full 12-domain contract" | **13** domains |
| ABSORB-01 | all 27 prior-art records lack an absorption field | **39** records, still 0 with one |
| TODO, skills_sync | 52 drift | **49** |
| TODO, pointers | 261 absent paths | **271**, moving the wrong way |

The pointers row is the only one that got worse, and it got worse while nobody was
looking at it, which is the argument for putting a ratchet on the number rather than
re-measuring it in another audit five days from now.

## 7. The prior-art schema has two defects, not one

ABSORB-01 names the first: no field records what was taken from an alternative, so
absorption is unrepresentable, therefore unchecked, therefore never happens. Confirmed
across all 39 records, including the one written this morning, which has the same gap.

The second is not in any ticket. `verdict` is free text. 39 records carry 13 distinct
values, and four of them are sentences:

- `keep-provisionally, and it is the weakest of the three records written today`
- `keep-the-ledger-design, replace-the-capture-claim`
- `keep-ours-with-a-named-defect`
- `thin-wrapper-justified-by-reuse`

The prose is good. It is also ungroupable, so the question "how many components did we
decide to replace" cannot be answered without reading 39 files. This is the identical
defect the Zion spec diagnosed on the board, where hierarchy lived in an `EPIC:` title
prefix that GitHub could not group on. Same fix shape: keep the sentence, add the
enumerated field beside it.

One verdict is `delete-ours`, for `tools/whatsapp`. The directory still exists with 4
tracked files. A decision recorded and not executed looks exactly like a decision not
taken.

## 8. What this says about the phases

The repository has thirteen contract domains, eight oracles with selftests, a mutation
runner that proves those selftests can go red, and a refutation layer. That machinery is
real and it works. Every finding above is of one kind: **a measurement that is produced
and then not bound to anything that stops.**

- `docmap` computes INDEX reachability and prints 3%. Nothing fails.
- `pointers.py` counts 271 absent paths and exits FAIL, and is not a gate domain.
- `skills_sync` reports 49 drifted items. Nothing fails.
- `refute` ran green-adjacent for days by returning "unknown" 26 times, and the exit code
  did fail, and nobody read it.

So the next phase is not more instruments. `docs/reflections/2026-07-29-what-is-going-wrong.md`
section 4.2 warns against adding a thirteenth gate domain and the count is now thirteen
already. The phase is **binding the instruments that exist to a ratchet**: a number that
may not get worse, checked by something that already runs.

That is a design position, not a decision. It needs `/diverge` before anything is built,
per charters rule 2, and it is filed to TODO rather than implemented here.
