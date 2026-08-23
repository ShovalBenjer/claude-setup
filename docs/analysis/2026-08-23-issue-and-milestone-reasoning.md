# 2026-08-23: issue and milestone reasoning

Status: MEASURED
Measured against: commit 7c9484d (main, post PR #88 + rules/skills waiver merge),
GitHub state as of 2026-08-23T21:00Z.

## Why this file exists

The operator flagged the milestone/epic/task/subtask hierarchy as stale "from my
perspective" and asked for each open issue to be reasoned: is it a real current
problem, what tier does it actually belong at, and which milestone owns it, with
milestones re-derived against `docs/*.md` rather than trusted as given.

56 open issues exist (not 37 — the first count this session ran was truncated by
`--limit 50` interacting with issue creation order; `gh issue list --limit 300` is
the authoritative count, re-run below to keep it checkable):

```
gh issue list --repo ShovalBenjer/claude-setup --state open --limit 300 --json number \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
# -> 56
```

## The three generations, and why the operator is right that it's stale

Three planning documents tried to answer "what's left" at three points, each one
superseding the last, none re-derived on the schedule its own header demanded:

1. **2026-08-11 milestone-task-plan.md** — created the 34 EPIC issues (#4-#35) and
   the M0-M4 grouping (M0 unmerged work, absorbed into GitHub's M1-M5 without a
   direct number match — GitHub has no M0). Its own header: "Re-derive before
   acting if the date above is more than a week old." Today is 12 days past that.
2. **2026-08-15-unfinished-work-inventory.md** — superseded #1 explicitly, listing
   8 named corrections (skills waiver state, 6 PRs it claimed still open were
   already merged, domain counts, etc.). Itself now 8 days past a reasonable
   freshness window, though it carries no explicit re-derive-after date.
3. **2026-08-23 T01-T18 prompt-triage (#91-#108)** — created TODAY, 2 hours before
   this file, machine-extracted from `~/.intent/intent.db` (480 events, 426
   unique operator prompts, 2026-07-23 to 2026-08-23), clustered by hand. This is
   the freshest and most directly grounded in the operator's own words, not an
   agent's summary of them.

None of the three ever fully reconciled into the other. That gap — not any single
wrong fact — is what "stale" names correctly. The EPICs are not fabricated; most
map to a real, still-open gap the 2026-08-15 inventory itemizes with a concrete
artifact. What's stale is the packaging: 34 same-shaped "EPIC:" issues with no
tier distinction, sitting apart from the newer T-series that already re-surfaced
much of the same ground in the operator's own words.

## Milestone re-derivation

GitHub's 5 milestones, checked against `docs/prd/` and `docs/PLAN-SPINE.md`:

| Milestone | Description | Still a real phase? | Evidence |
|---|---|---|---|
| M1 Instruments trustworthy | no self-invalidating gate, no unproven selftest, no dead pointer reporting success | Yes, live | `PLAN-SPINE.md` harness-gate row: ~90% built, verified `gate.py selftest` exits 0. Real gap remains: 23 hooks unwired (AGENTS.md gotchas), stub count re-measured 2026-08-15 at 13/32 dot-claude + 17/30 dot-codex. |
| M2 Consolidation and shrinkage | one canonical tree, GitHub-backed clones removed, 1682 files under 600, licensing resolved | Yes, live, and this is the SAME topic as T02 (17 operator prompts, 2026-07-29 to 08-18, on dirs/docs sprawl) | File count not re-measured this pass; `T02`'s 17 prompts are the sharper, dated evidence for this milestone than the EPIC bodies are. |
| M3 Delegation that has actually run | native hook wiring, ACP over the bespoke bridge, personas with reputation, one measured workflow run | Yes, live | 2026-08-15 inventory 5.3: 18 persona-review artifacts all say "external backend not requested" — zero delegation runs measured. Matches operator's own memory row `Gastown is a map, not a runtime`: 0 of 19 personas ever spawned. |
| M4 Design with an anchor | DESIGN.md + tokens with parity guard, taste ledger, Construct v4 | Partially stale | `docs/taste.md` exists and has rows (dashboard picks logged). DESIGN.md does not exist. Construct v4 (#18) has no code per 6.5. This milestone is real but under-evidenced relative to the other four. |
| M5 Autonomy and CI | gate runs in CI, releases structured, repo standards agent-maintained | Yes, live, but CI itself is currently degraded | `ship-gate.yml` has 6 failing checks as of this session's PR #88 (confirmed pre-existing, not caused by that PR). Billing-vs-runner-env question is UNRESOLVED — `gh api /users/{u}/settings/billing/actions` returned 404 (wrong scope), not confirmed either way. Treat the "runner env gap not billing" claim from earlier this session as ASSUMED, not VERIFIED. |

**Verdict: keep all 5 milestones.** Each names a real, still-open phase with
evidence less than 2 weeks old. The defect is not the milestones, it's that
roughly 20 open issues (all of #38, #56-58, #90-108) carry no milestone at all.

## Per-EPIC reasoning (#4-#35, 24 of the 34 milestone-linked issues)

Reasoned from `PLAN-SPINE.md` (2026-08-17, hand-verified % built) and the
2026-08-15 inventory (itemized artifacts), not re-read from each issue body
individually — both sources are more current and more concrete than the EPIC
text, which mostly restates a title with no acceptance criteria.

| # | Title | Verdict | Evidence | Real tier |
|---|---|---|---|---|
| 4 | Gate and fingerprint integrity | **Mostly done, keep open narrow** | PLAN-SPINE: harness-gate ~90%. 2026-08-15 3.4-3.9 name 6 specific residual bugs (codemap/review sha collision, claims.jsonl dual shape, selftest ledger isolation, no skills_sync mutation spec, 3 refute residues, 4 CI gaps). | Task-cluster, not an epic — the remaining work is 6 named bugs, closeable one at a time. |
| 49 | Falsifier layer, 5 claims refuted | **Done** per 2026-08-11 plan (checked `[x]`) | `python tools/audit/mutate.py --spec all` selftest referenced live in AGENTS.md commands. | Close, or fold residual into #4's bug list. |
| 50 | Bind instruments to a ratchet | **Live, blocked on /diverge** | 2026-08-15 3.2: needs `/diverge` first per charters rule 2, never run. | Task — one concrete next action named. |
| 28 | Waiver reason names its mechanism | **Live** | 2026-08-15 3.3, no contradicting evidence found. | Task. |
| 10 | Commit at-risk work, settle absorption verdicts | **Live, worse than title suggests** | 2026-08-15 3.1: 1 of 41 absorption records actually name what was taken. `whatsapp` delete-ours verdict still has 4 tracked files present, contradicting its own recorded verdict. | Epic-scale, genuinely 40 sub-decisions. |
| 5 | Reconcile the repo's self-contradictions | **Live** | 2026-08-15 4.3 names the current worklist directly (the supersession table above IS this issue's worklist). | Task, self-updating — point it at whichever inventory is newest. |
| 6 | Dead pointers, stubs, drift | **Live, numbers updated 2026-08-15** | 13/32 dot-claude hooks + 17/30 dot-codex hooks are stubs into dead `/home/shovalbe/`; 319 files still cite it. **This is the same underlying problem the operator raised mid-turn about dot-claude/dot-codex/dot-agents structure.** | Epic — real scope, connects directly to the directory-reshape ask. |
| 34 | Adopt ast-grep | **Live** | 2026-08-15 4.4: retires 3rd waiver of the same prose-vs-code false-positive class. | Task. |
| 33 | Review recomputes its own numbers | Not directly evidenced this pass | No 2026-08-15 row found under this exact wording; may be folded into 4.10 (docs control plane) or superseded. | **Needs operator or a fresh read before closing — flagged, not resolved.** |
| 32 | Fix data structures/interfaces first | **Live** | 2026-08-15 4.6 groups with #31/#25. | Task-cluster. |
| 31 | Record where plan was refuted | **Live, 5 rows exist, binding doesn't** | 2026-08-15 4.6: plan-deviation ledger exists, nothing enforces writing to it. | Task. |
| 29 | Review recomputes numbers, renders what it judges | Same ambiguity as #33 — titles are near-duplicates | Not distinctly evidenced. | **Flagged: #29 and #33 may be the same ask filed twice. Recommend reading both bodies before any close.** |
| 27 | Prose gate measures ruled form not property | **Live** | 2026-08-15 4.5: `slop_lint.py` still prints "no band fitted"; concrete next steps named (port from voice_score.py, add fenced-code awareness, add 8 structural-pattern regexes). | Task. |
| 26 | Point-in-time reconstruction | **Live** | 2026-08-15 6.2 ABSORB-02: DoltHub-style, hiring ledger is the concrete need. | Task, low priority (P3 in original plan). |
| 25 | Supply-chain verification | **Live** | 2026-08-15 4.6: osv-scanner steps still `continue-on-error`. | Task. |
| 24 | RTK adoption | Not evidenced this pass | Neither source names a current blocker. | **Flagged for a fresh check — may be genuinely stale.** |
| 23 | Research transfer, 5 findings | **Live, itemized** | 2026-08-15 6.4: RT-1 to RT-5 named individually, 753 gate runs with zero approve/reject recorded. | Task-cluster, 5 real subtasks. |
| 22 | Autonomy ecosystem backlog | **Live, large** | 2026-08-15 5.1: AUTO-06/10/18/11/09/12-15/17/20 each named with a concrete blocker. PLAN-SPINE: AUTO is "unverified, no rollup" — 285 TODO.md rows, no aggregator. | Epic — genuinely the largest real cluster; needs the AUTO rollup PLAN-SPINE itself flags as missing before this can be scored. |
| 21 | GitHub repo standards, agent-maintained | **Overlaps directly with T06** | T06 (#96) has 5 real prompts on this exact topic, including the unresolved 2026-08-12 billing question. | Task — recommend merging into T06's tracking rather than keeping separate. |
| 20 | Get the gate running in CI | **Live, and this session found new evidence** | 2026-08-15 4.1: review job silently erroring, OAuth rotation suspected. This session (2026-08-23): 6 checks red on PR #88, confirmed pre-existing on main's last 5 pushes, unrelated to that PR's diff. Billing check attempted, returned 404 (wrong `gh` scope) — **not resolved, do not treat as answered**. | Epic — real, ongoing, and got worse (more red checks) since 2026-08-15, not better. |
| 19 | Absorb open-design and OpenGame | **Live, P3** | 2026-08-15 6.2 groups under ABSORB backlog. | Task, low priority. |
| 18 | The Construct v4 | **Live, zero code** | 2026-08-15 6.5 confirms zero code exists. | Design question, not a build task yet — recommend re-tiering to "design" not "epic" until a spec exists. |
| 17 | Design foundations that do not exist yet | **Live** | Same 6.5 cluster as #18; DESIGN.md still absent (checked this pass). | Design question, same as #18. |
| 16 | Run one workflow under prescribed routing | **Live** | 2026-08-15 5.4, no contradicting evidence. | Task — should be quick to close once run once. |
| 15 | Kilo Code integration, deadline | **blocked-operator label already correct** | 2026-08-15 5.5. | Keep as-is, correctly labeled. |
| 14 | Persona review economy | **Live, worse than title suggests** | 2026-08-15 5.3: 18 of 18 review artifacts to date report "external backend not requested." PLAN-SPINE: persona-economy 0%, `find . -iname "*reputation*"` returns only the ADR. | Epic — real, and confirms operator's own memory row (0 of 19 personas ever spawned). |
| 13 | Replace bespoke bridge with ACP | **Live** | 2026-08-15 5.5. | Task. |
| 12 | Wire Claude Code native surface | **Live** | 2026-08-15 5.4. | Task. |
| 11 | Licensing/privacy blockers, going public | **blocked-operator, correct** | Matches memory row `claude-setup cannot be made public` — 295 files carry former-employer identifiers. | Keep, correctly blocked. |
| 9 | WSL2 migration and terminal launcher | **Partially done, overlaps T04 and T16** | This session did real launcher work (PR #88). T04 (#94) and T16 (#106) both re-raise WSL/launcher topics from fresher prompts. | **Recommend closing #9 as superseded by T04+T16, which have the actual current operator asks.** |
| 8 | Shrink 1682 files under 600 | **Live** | 2026-08-15 6.1 names concrete feed-in work (work-docs archaeology, archive calls). File count not re-measured this pass. | Epic, real. |
| 7 | Phase D reclamation | Not evidenced this pass, title is vague | Neither source elaborates beyond a title-level mention in 6.5. | **Flagged — needs a fresh read of the issue body, likely stale or foldable into #8.** |

Issues #4-#35 not in the table above (there are gaps in the numbering: no #36,
#37 in this milestone series) — none found; the milestone-linked EPICs are
exactly #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #18,
#19, #20, #21, #22, #23, #24, #25, #26, #27, #28, #29, #31, #32, #33, #34, #35,
#49, #50 (33 issues, not 34 — recount from the milestone listing, corrected here).

**#35 (Repo Clear enforced standard)** not individually reasoned above — 2026-08-15
6.5 groups it with 9 others in one line with no per-item evidence. Recommend a
follow-up pass reads #35, #29, #33, #21 (partly covered), #17 (covered), #7
(flagged), #9 (recommend-close above), #24 (flagged), #19 (covered), #18
(covered) individually before any milestone action, since 6.5's grouping is
itself a compression this file inherited rather than verified.

## The standalone issues (#38, #56, #57, #58)

Not evidenced fresh this pass (would need each body re-read); per the 2026-08-11
plan these were already correctly filed as standalone, not epics. No verdict
change recommended without a dedicated read.

## The T-series (#90-#108) — relationship to the above

T01-T18 are not new work; they are the same underlying prompt history the EPICs
were built from, re-clustered today with sharper sourcing (literal operator
words, dated, `PT-` ids resolving to full text via `tools/intent/resolve.py`).
Where a T-issue's topic overlaps an EPIC (T02↔#6/#8, T04↔#9, T06↔#20/#21,
T09↔interpretability row in PLAN-SPINE, T07↔#14), **the T-issue is the more
current and more trustworthy source** — it's 2 hours old versus 8-12 days, and
it's the operator's own words versus an agent's paraphrase.

**Recommendation, not yet executed:** link each overlapping EPIC to its T-issue
via `related:`, and let the T-issue's checkbox state (which `PT-` boxes are
still unchecked) become the actual progress signal, rather than maintaining two
parallel unlinked trackers.

## The ledger gap this triage did NOT fix

`state/prompt-tickets.jsonl`: 2313 rows, **100% still in state `CAPTURED`**, 0
ever transitioned to `TRIAGED`. Today's T-series triage clustered 426 unique
prompts into 18 issues but did not write back to this ledger — `tools/intent/tickets.py`
defines the CAPTURED → TRIAGED → NOT_WORK / SUPERSEDED lifecycle and nothing has
ever called it. This means the T-series issues, however good, will themselves go
stale the same way the EPICs did unless something closes this loop. Flagging
this as the actual root cause rather than a detail: three generations of
planning docs have now hit the same wall (a capture mechanism with no write-back).

## What was NOT resolved by this pass, named explicitly

- GitHub Actions billing state (T06's 2026-08-12 question): `gh api` call
  returned 404, needs `gh auth refresh -s user` to check properly. Still ASSUMED,
  not VERIFIED, that CI failures are a runner-env gap rather than a billing wall.
- #33 vs #29 possible duplicate — not resolved, flagged for a body-level read.
- #24, #7 — insufficient fresh evidence to verdict, flagged.
- #35 and 9 others in 2026-08-15's compressed 6.5 line — inherited a group
  verdict, not individually checked.
- The directory-reshape question (dot-claude/dot-codex/dot-agents vs a
  professional-standard layout like `src/`) the operator raised mid-turn: this
  connects directly to #6 (dead pointers/drift, live) and T02 (17 prompts on
  exactly this), but is held as its own follow-up rather than decided inside
  this file, per the operator's implicit signal that it deserves its own pass.

## Proposed next action (not yet executed, awaiting operator sign-off)

1. Assign a milestone to every currently-unmilestoned open issue that maps
   cleanly (T-series → whichever M1-M5 its topic matches; #38/#56/#57/#58 stay
   standalone per the 2026-08-11 precedent).
2. Add `related:` cross-links between overlapping EPIC/T pairs named above.
3. Do NOT close anything yet — every closeable-looking item above (#49 done,
   #9 superseded) still needs the operator's explicit go, per his redirect away
   from "close all 34" toward "reason each one."
