# Albert: prior art for the whole repository, and not adoptable

Date: 2026-07-29. Lane B. Closes the branch left open in
`docs/analysis/archive/2026-07-29-where-our-system-stands.md:99`, which named
`github.com/Sdraugel/albert` as "prior art for the entire repository, not for any
component in it, and our gate never asked about it because the audit is scoped per
directory."

Scope of this read: README, GitHub API metadata, top-level and `harness/` listings,
and the full license. Not read: any source file. Every claim below is from those
five fetches and is labelled accordingly.

## The verdict, first

**Prior art: YES. Adoption: NO, blocked on license.**

`LICENSE.md` is **PolyForm Noncommercial 1.0.0**. Not OSI-approved. Commercial use is
not permitted. Modification and redistribution are allowed for noncommercial purposes
only, and redistribution must carry the same terms forward.

`CLAUDE-OS.md` section 1 states the mission as gated, evidenced action "across his
ventures". Ventures are commercial. So the code cannot be lifted, vendored, or
adapted into anything with a commercial path, and a noncommercial-only dependency at
the root of a harness that serves commercial work is a worse position than writing it
ourselves. This is a legal constraint, not a quality judgment.

## What it is (VERIFIED, README plus API)

| | |
|---|---|
| Description | "Autonomous multi-agent harness for Claude Code (A.L.B.E.R.T. orchestrator) plus a zero-dependency live HUD console" |
| Created | 2026-07-23 |
| Last push | 2026-07-26 |
| Stars / forks | 85 / 19 |
| Primary language | JavaScript |
| Size | 4,533 KB |
| Platform | Windows 10/11, PowerShell 5.1+, Node 20+ |
| Structure | `harness/{agents,runtime,skills,workflows}`, `console/`, `chat/`, `tools/`, `install.ps1`, `uninstall.ps1` |

Mechanism, quoting the README: a planner writes dependency-ordered task lists,
producers execute in isolated git worktrees, critics independently verify.
"Independent tasks in the same chunk then run concurrently, each in its own git
worktree." "Producers never grade themselves." Deploys need an explicit
`allow_deploy: true`. A `stop_after` checkpoint allows review before proceeding.

## Correction to the framing that sent me here

It was called an ancestor. It is not one. Albert was created 2026-07-23, which is
**one day before** `docs/analysis/archive/2026-07-24-reference-repos-excavation.md` was
written and after most of this repository existed. It is a contemporary solving the
same problem at the same time, not prior work we failed to find.

That distinction matters for exactly one thing, and it is the thing that counts:
`prior-art-gate` blocks unsourced novelty claims. Albert is a live, starred,
maintained instance of "autonomous multi-agent harness for Claude Code with a
console." **No document in this repo may describe that shape as novel, missing, or
unbuilt.** That includes the FleetView spec (`docs/specs/2026-07-24-command-center-superior.md`)
and PRD row AUTO-19.

## Where it is genuinely ahead of us

Two mechanisms, both structural, both absent here:

1. **Git worktree isolation per producer.** Concurrent agents each get their own
   working tree. Our open risk 1 in the 07-29 handoff is precisely that concurrent
   sessions write one tree, and it fired again during this session's own verification
   run: `tests/test_selfimprove_scan.py` appeared at 19:54 mid-suite, moving the
   count from 173 to 179. Albert's design makes that class of race structurally
   impossible. We have the tooling for this already (`EnterWorktree`, `isolation:
   "worktree"`) and do not use it.
2. **Producers never grade themselves, enforced by role.** Ours is a norm in prose.
   `docs/analysis/archive/2026-07-29-where-our-system-stands.md:170` records that today's ten
   prior-art records were each written and self-annotated by their own author, with no
   independent check. Same rule, unenforced.

Neither of these requires Albert's code. Both are shapes we can build.

## Where we are ahead

From the README only, so read as ABSENT-FROM-README rather than proven absent:
evidence bound to a working-tree fingerprint, mutation testing that proves each
oracle can fail, prior-art records carrying expiry dates, hash-chained append-only
ledgers, and a refutation ledger. None appear in Albert's description of its own
gating, which is critic sign-off plus two manual checkpoints.

Our gate refuses. That remains the strongest thing here and it is not on their list.

## Decision

1. Do not vendor, copy, or adapt Albert code. License blocks it.
2. Strike novelty language for the multi-agent-harness-plus-console shape wherever it
   appears. FleetView and AUTO-19 must cite Albert as existing prior art or be
   retired.
3. Build worktree isolation for concurrent sessions. Independently motivated by open
   risk 1, which is live, and reachable with tooling already available.
4. Make "producers never grade themselves" mechanical, starting with prior-art
   records, which are currently self-graded.

## Residual risk

I read five fetched artifacts and zero source files. The claims about what Albert
does are its own README's claims, unverified by running it, and I did not install it.
The two "ahead of us" items are design descriptions, not observed behavior. The
license reading is the only claim here I would defend without further work, and even
that is a summary of the license text rather than legal advice.
