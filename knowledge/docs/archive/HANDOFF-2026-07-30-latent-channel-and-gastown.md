# Handoff 2026-07-30: latent inter-agent channel, Gastown review loop, and two blockers

Lane B (harness). Claim row: `session-2026-07-30-latent-channel-oracle` in
`state/claims.jsonl`, appended before starting. Session `279e8c19`, concurrent with
`beba6c57` in the same working tree, which matters and is explained at the end.

Nothing was committed or pushed. Every artifact below is on disk and uncommitted.

## Goal, as it actually developed

Started as a WhatsApp lookup and turned into two things: settling a technical
argument with real 2026 citations, and building the verification piece that
argument implies. The operator's claim to Yarin was that agents have a language of
their own, coming from training, and that it is easier for them. Yarin called it a
myth. Both were partly right, and the split is now on disk as ADR-0018.

## What exists on disk that did not this morning

**`docs/adr/0018-two-tier-inter-agent-channel.md`.** Inter-agent messages get
`text`, `dense-text` or `kv`, with no implicit default and no silent downgrade,
because a quiet fallback to text is the failure that reads as success. `kv` is legal
only where both endpoints are open-weight and ours. No dense channel ships until the
oracle clears it, stated as a condition on the other rows rather than as follow-up.

**`tools/channel/roundtrip.py`** (285 lines, so no prior-art record is owed) and its
`README.md`. Sends a document, asks probes whose answers exist only in that document,
normalises channel probe accuracy against the same probes over plain text. Substring
recovery, not model judgement, so the verdict is deterministic and is not graded by
the same class of system that might be hallucinating over the channel.

Measured: `selftest` exit 0 (identity 1.0 PASS, half-truncation FAIL, unreachable
peer FAIL, absent-answer probe rejected); `run --channel truncate` exit 1 at fidelity
0.6667, 2/3 probes, 125/251 bytes. The `truncate` channel is the regression that
keeps the gate falsifiable and is named as ADR-0018's own falsifier.

**`.github/workflows/claude-code-review.yml`**: `allowed_bots: kilo-code-bot` added,
pinned to that one writer rather than `*`.

**`TODO.md`**: CHAN-01 through CHAN-09.

**`~/.claude/projects/.../memory/feedback_2026-only-top-institutions.md`** plus its
MEMORY.md pointer: research citations are 2026 only, and affiliations get verified by
reading the paper, never lifted from a search snippet.

## The Gastown finding, which is the most actionable thing here

`https://app.kilo.ai/gastown/65f35202-bda2-4f15-904a-72d4b0892622` is live. Mayor tab
with a terminal input, Connected, Kilo 7.2.14, workspace
`/workspace/rigs/mayor-65f35202-.../mayor-workspace:master`, Code on Auto Free through
Kilo Gateway. 10 rigs, 10 Polecat agents, beads 0 open / 9 in progress / 4 in review /
131 closed, 200 events in 24h.

Two beads had failed at `max dispatch attempts exceeded (5)`. Root cause from
`gh run view 30541148579 --log-failed`, quoted by the action itself:

    Workflow initiated by non-human actor: kilo-code-bot (type: Bot).
    Add bot to allowed_bots list or use '*' to allow all bots.

Gastown's Polecats open PRs as `kilo-code-bot` (PR #3 on claude-setup) and
`claude-code-action` refuses a bot actor by default, so the review never ran and the
bead waiting on it burned all five attempts. Claude Code Review failed at 10:42 and
12:05 today for this reason.

**The fix is staged, not verified.** A YAML file that parses is not a workflow that
passes. The only oracle is a bot PR triggering the workflow and reaching
`completed/success`, which needs a commit and a push that were not made. I also took
the input name `allowed_bots` from the error message's own wording rather than from
the action's schema. The causal link from that failure to the two dead beads is
inference: I did not open either bead to confirm what it was waiting on.

## The Mayor's audit does not survive contact

It had produced 20 findings across the rigs (3 critical, 4 high, 6 medium, 7 low).
Checked what was cheap:

- **Its #2 most urgent action is wrong.** `actions/checkout@v6` is real: the API
  returns `v7.0.1, v6.1.0, v5.1.0, v4.4.0`, and the nightly using `@v6` has succeeded
  six consecutive days. "Fix `@v6` to `@v4`" downgrades two majors.
- 23 agent personas: confirmed exactly. `id-token: write`: confirmed, three
  occurrences.
- **36 skills: wrong.** The repo copy has 51 skill directories. Unexplained, and it is
  what `tools/audit/skills_sync.py check` exists to measure.
- The shared-PAT claim was not verified in either direction.

Do not act on that table without re-checking each row.

## The pasted compliance register was a fabrication on a real base

An external summary claimed 56 repositories partitioned 10 Adopted / 8 Used-As-Is /
12 Absorbed / 26 Rejected. The 56 is real, from
`docs/analysis/archive/2026-07-30-github-repo-triage.md`. Everything above it is not, and the
source document says so about itself in its second heading: "Not done: nobody has
visited these repositories file by file." It calls itself metadata triage, states it
"cannot answer 'adopt this'", and names presenting a metadata sort as a reading pass
as failure class L-2026-07-29-h. The register is that failure performed on that
document.

Specifics: the real state words are adopt / install-as-is / leave / concepts-only, and
the doc contains 2 occurrences of "adopt" and zero of "Used-As-Is" or "Rejected". Its
only metadata-defensible verdict is LEAVE, 14 repositories. The real licence count is
17 of 56 unlicensed, not 26, and the register fuses a legal bar with a maintenance bar.
`state/resource-ledger.jsonl` has 3,862 rows and 5 verdicts, so no 56-row table exists
there either. The ten "adopted" packages are the distribution's default answer and not
one of them appears in the operator's saved corpus, which holds `affaan-m/ECC`,
`github/spec-kit`, `dolthub/dolt`, `ofekron/better-agent`, goose and the ACP spec.

`agent-framework/coherence-governor` is not a repository. It is
`docs/analysis/reference/coherence-governor-AGENTS.md`, 17,923 bytes, a verbatim copy
of the `AGENTS.md` from `Master0fFate/just-my-skills` (7 stars, no license), saved by
ABSORB-04 and tracked in git. It was not deleted.

## Kilo trigger question, closed

Triggers are UI-only: `kilo help` grepped for trigger/webhook/cloud/inbound/schedule/
cron matches exactly one line, `--cloud-fork`, and the docs confirm UI-only for both
webhook and scheduled triggers. **This does not cap autonomy**, which retracts a claim
made earlier in the session: a trigger is durable and reusable, so the manual step is
one-time provisioning, not per-run.

Four facts that shape CHAN-02: the payload arrives through a prompt template
(`{{bodyJson}}`, `{{headers}}`, `{{query}}`, `{{path}}`, `{{method}}`, `{{timestamp}}`),
which is the envelope seam; the secret header name is configurable, so `x-scc-key` is
fine; KiloClaw mode runs locally and Cloud Agent mode runs in the cloud, and only the
second survives a policy forbidding the local agent; scheduled triggers are 5-field
cron with a selectable timezone and a hard 10-minute floor.

## Two things only the operator can decide

**1. `coherence-governor-AGENTS.md`.** An all-rights-reserved verbatim copy is tracked
in this repo and is the second blocker on making `claude-setup` public, alongside the
third-party PII in `research-papers/el-vadt`. Three dispositions: replace with a
summary plus link, ask the author for a license, or accept that the repo never goes
public. The triage doc already records this as an operator decision.

**2. Concurrent sessions against the ship gate.** The Stop gate fired three times on a
tree with no edits from this session. Not an instrument defect: `GATE_OUTPUTS` already
excludes the gate's own writes, and `skill-usage-log.sh` writes `skill-use.jsonl`, not
refutations. The cause is that `state/refutations.jsonl` is tracked, unexcluded, and
grew from 287 committed lines to 443, with rows appended at 15:20, 15:28, 15:29, 15:31
and 15:32 by something other than this session while `beba6c57` was writing until
15:33. So a green gate in a concurrent session certifies the tree as of the run, not as
of the turn's end, and the hook is telling the truth.

The choice is serializing sessions, which costs the two-session workflow in active use,
or excluding the ledger, which costs the gate's ability to notice edits to the very
file that holds claims honest. `gate.py`'s own comment warns that "an over-broad
exclusion buys a satisfiable gate by going blind, which is the same defect wearing the
opposite sign." A lane must not pick which to sacrifice.

## Next action

Ship the `allowed_bots` fix as a PR (ADR-0012, no push to main) and watch one
`kilo-code-bot` PR reach `completed/success`. That single observation closes the review
loop, unblocks the 9 in-progress beads, and is the only thing that converts the staged
fix into a verified one.

## Gate

`python tools/gate/gate.py run --project .` PASS on every tree gated this session, ten
domains green. `review` WAIVED until 2026-08-12 (five blocking HIGH findings are
pattern matches against comments, docstrings and JSON prose; the waiver carries two AST
commands that must return empty lists or it is void). `perf` and `e2e` N/A: no declared
performance budget, no served app. `tools/slop_lint.py` clean on every file written
here; the 19 hits in `TODO.md` pre-exist at HEAD, verified by linting
`git show HEAD:TODO.md`.
