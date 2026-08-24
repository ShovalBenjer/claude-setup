# Handoff from the learning lane: discovery must watch organizations, not trending

**From:** lane D, daily-deep-learning
**To:** lane B, claude-setup
**Date:** 2026-07-29
**Why this is a handoff:** the scanner runs from `daemon/discover.cmd`, but the
scanning contract, schedulers and org lists are harness concerns. Lane D owns
what the learner sees, not how the sweep runs.

## The operator's ask, in his words

He wants the learning system fed by "signals of all relevant open source blogs".
He named `github.com/google-research` and an OpenReview forum page as examples.
His instruction: investigate "not only trending repo's, but also check changelogs
and activity across organizations".

## What runs today

`daily-deep-learning/daemon/discover.cmd` holds the whole contract in one prompt.
It does three things:

1. GitHub orgs through `gh api orgs/{org}/repos?sort=pushed&per_page=5`, over
   NVIDIA, google, google-deepmind, microsoft, facebookresearch, apple,
   huggingface, mistralai, EleutherAI, colossalai, significant-gravitas.
2. Releases for `anthropics/claude-code`, commits for
   `merlihson/scientific-resources`.
3. Telegram, plus rotating podcast and news searches.

Output is `discoveries.json`. Read this session: `generated` 2026-07-28T04:15:09Z,
46 items.

## Six gaps, each checked against the file

**1. `google-research` is missing.** The list holds `google`, which is a
different GitHub organization. The operator named `google-research` directly, and
it is where a large share of paper-linked code lands.

**2. Five repos per org is a thin sample.** `per_page=5` caps every org at five,
including google and microsoft. Anything below the top five in the window is
invisible. Paginate, or widen the cap per org size.

**3. The `pushed_at` trap, already recorded.** Sorting by `pushed` surfaces branch
and tag noise. A hit needs qualifying by in-window commits on the default branch.
This was recorded earlier in the learning lane's project memory. Flagging it here
so the rebuild does not reintroduce it.

**4. Releases are watched for exactly one repo.** Only `anthropics/claude-code`.
A release is a different signal class from a commit: it is curated, versioned and
human-written. That is the class the operator says he wants.

**5. No changelog watch exists at all.** No `CHANGELOG.md`, no release-notes feed,
no blog feed. "Open source blogs" in his message points straight at this gap.

**6. Research venues are absent.** OpenReview is not scanned.

## What I could not resolve, so you do not repeat it

OpenReview blocks plain clients. Measured this session:

- `https://openreview.net/forum?id=oCHsDpyawq` returns a browser verification
  screen, not the paper.
- `https://api2.openreview.net/notes?forum=oCHsDpyawq` returns HTTP 403.
- `https://api.openreview.net/notes?forum=oCHsDpyawq` returns HTTP 403.

So an OpenReview watcher needs an authenticated client, or a different route such
as the venue's accepted-papers listing or the arXiv mirror.

**RESOLVED by the operator, 2026-07-29.** The paper is **ZAPBench**, the Zebrafish
Activity Prediction Benchmark: predicting cellular-resolution neural activity
across an entire vertebrate brain, published at ICLR. The repository is
`github.com/google-research/zapbench`, Apache-2.0, confirmed reachable this
session.

That closes the identification, and it sharpens gap 1 rather than softening it.
The repository sits in `google-research`, the organization missing from the scan.
The operator's point is that the paper was a SIGNAL, not the target: he wants the
repositories and the journal articles behind work like this feeding the
cross-domain map, across subjects and their subsections. ZAPBench is
neuroscience plus benchmark design plus time-series forecasting, which is
precisely the kind of item a vendor-org sweep never surfaces.

## His earlier prompts

He says his WhatsApp self-chat holds prompts for this work, and that they can be
improved rather than reused as-is. I searched three exports under
`C:\Users\shova\Downloads\docs\`, named `_chat 12.txt`, `_chat 14.txt` and
`_chat 15.txt`. None matches trending, changelog, org scan or discover. So the
prompts sit in the live store, not in those files. The `whatsapp-query` skill is
the retrieval path, and it is lane B's to run.

## The interface lane D needs held

Do not change the record shape. `discoveries.json` items carry `id`, `subject`,
`title`, `url`, `source`, `kind`, `time`, `time_label`, `line`, `quest`, `min`
and `tree`. The learning app reads that shape directly.

Two additions would help, and neither breaks the reader:

- Extend `kind` with `release` and `changelog`. It already carries `repo`,
  `release`, `article`, `video`, `podcast`, `paper` and `news`.
- Add an `org` field, so a discovery can attach to the organization that shipped
  it.

Requirement R19 in the learning lane wants discoveries indexed by subject and
presented as optional side quests. The `subject` field already supports that.
Keep it populated.

## Suggested scope

1. Move the contract out of the `.cmd` prompt into a versioned file the gate can
   read. A prompt string is not reviewable.
2. Build an org-activity watcher over a named list that includes
   `google-research`, qualified by in-window default-branch commits.
3. Build a release and changelog watcher, separate from the commit scan.
4. Add a research-venue watcher once the OpenReview access route is settled.
5. Pull his WhatsApp prompts first, so the rebuild starts from what he already
   wrote.


## Added later on 2026-07-29: test architecture is not gateable

The operator asked why the gate shows no integration, property or mutation
testing. It does not, and this is a real gap rather than a per-project omission.

`tools/gate/gate.py:86` fixes `DOMAINS` at build, unit, types, e2e, a11y_ux,
security, docs, pipeline, review, perf. There is no domain for property based,
mutation, fuzz, contract, concurrency or integration testing, so a project
passes the gate with example tests alone. daily-deep-learning did exactly that
today: its `unit` domain is ten example tests in one file, and the gate returned
PASS.

Two documents already say this is not enough, and both predate the question:

- `work-docs/testing_practices.txt` section 6 names the minimum as unit,
  property, regression, integration and performance baseline, plus fuzz for
  external input and contract tests if distributed. Section 5 gives the CI
  schedule: property on every commit, contract and integration on pull request,
  fuzz and mutation nightly.
- the global `CLAUDE.md` verification section already requires property,
  metamorphic, differential, mutation, fuzz, concurrency or benchmark checks
  when ordinary examples leave material uncertainty.

So the rule exists in two places and the enforcement point exists in a third,
and they are not connected. `TODO.md` RT-5 notes this repo already has mutation
testing and no metamorphic relations, which means the capability is here and
only the gate wiring is missing.

Filed as two rows in `tools/selfimprove/proposals.jsonl`. Note the second row:
line 14 of that file holds two concatenated JSON objects, so a line-by-line
parse raises before reaching the newest rows. Left unfixed deliberately, it is
lane B's data.

Not proposing a design from here. The judgement calls belong to this lane:
whether the taxonomy becomes new domains or subdomains of `unit`, whether it is
required or N/A per project type, and what a static site with no bundler should
be held to.


## Added later on 2026-07-29: the harness swallows commands that do not exist

Three findings, one root cause. Filed as proposal rows the same day.

**1. An unknown slash command produces nothing.** No error, no suggestion, no log
line. `/goal` becomes literal text inside the sentence. The operator believes he
issued a command; the assistant reads a word and answers around it. Neither side
can see the failure. He typed it twice on 2026-07-29 and both were no-ops.

Verified absent everywhere: `~/.claude/commands`, `~/.claude/skills`,
`~/.claude/plugins`, `claude-setup/dot-claude`, `dot-agents`.

The fix surface already exists. Three hooks run on UserPromptSubmit
(`bus-inbox.sh`, `kernel-anchor.sh`, `voice-explainer-trigger.sh`), so a
leading-token check against the installed command and skill names is a small
addition to an event that is already wired, not a new mechanism.

**2. Command drift.** `dot-claude/commands` holds 7 definitions and
`~/.claude/commands` has 4. Missing: `insights.md`, `pickup-reviews.md`,
`reground.md`. This is the same drift already recorded for `settings.json` (live
4 hook events, canonical 6), which suggests the install step reconciles some of
the `dot-claude` tree and not the rest.

**3. The two compound, and the boot path is the casualty.** The SESSION RECALL
block injected at every session start says "run /reground if it looks stale", and
`reground.md` is one of the three that never got installed. So the standard boot
text advertises a command that silently degrades into prose. On 2026-07-29 the
operator asked for a reground and it was done by hand, because nothing resolved
and nothing said so.

Worth checking whether `/insights` and `/pickup-reviews` are referenced anywhere
in the boot or runbook text as well. If they are, the same trap is armed twice
more.

### Why this is filed rather than fixed here

Lane D owns the learning PWA. Commands, hooks and the install step are lane B's,
and the decision of what an unknown command should DO is a judgement call that
belongs there: hard-fail, suggest the nearest match, or pass through with a
warning. Each has a different cost when the operator is mid-flow.

### One related note from the same session

`/loop` DOES exist and works. Run in dynamic mode it removes the turn-boundary
stall the completion-gate hook measures (66 operator turns spent only on
restarting stopped work, roughly 940 minutes of waiting in the last week). That
hook measures the cost; nothing documents the remedy. Worth naming `/loop`
dynamic mode in the runbook as the standard answer to it, next to the hook that
counts the loss.
