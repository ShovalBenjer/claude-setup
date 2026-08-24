---
name: skillmap
description: Router over every skill you invoke by hand. Ask which one fits the situation.
disable-model-invocation: true
---

You do not remember 38 skills. Ask.

Named `skillmap` to sit beside `codemap` and `docmap`, the two maps this repo already
generates. Same job, different territory.

This map is only useful if it is true. Whenever a user-reachable skill is added, renamed,
removed, or changes where it sits, update this file in the same commit. A router that
names a skill which no longer exists is the same failure class `tools/audit/pointers.py`
catches for hooks, and nothing catches it here yet.

## The spine: idea to merged

1. **`/brainstorming`** before any creative or feature work. Explores intent and
   requirements before implementation.
2. **`/diverge`** for any design, UI, naming, copy, or architecture decision. Five
   candidates with stated `p_conventional`, at least two below 0.3. Required by
   `~/.claude/rules/out-of-distribution.md`, not optional.
3. **`/premortem`** gates the plan. Five failure modes in writing before code.
4. Build. **`/prove-implementation`** for anything non-trivial: it compares alternatives
   under explicit constraints and demands executable evidence before "best", "optimized",
   or "production-ready".
5. **`/code-simplifier`** on the changed files, then **`/refactor-pre-push`**.
6. **`/commit-push-pr`** runs the gates and opens the PR. **`/coverage-enforcer`** blocks
   the push if source changed without tests.

Work ships through a PR, never a push to main (ADR-0012).

## Before you claim anything

- **`/prior-art-gate`** before writing "novel", "nobody has built", "there is no
  benchmark", or any claim of absence. Blocks unsourced novelty.
- **`/codex-call`** for an independent external judge after executable checks, on
  high-risk work and before strong quality claims.
- **`/red-team-review`** for a full multi-persona sweep: security, architecture,
  performance, UX, eval, in parallel worktrees. Expensive. Use before a ship, not per
  commit.
- **`/heidegger-reflect`** at end of task: test evidence plus completion honesty.

## Grounding a session

- **`/wayfinder`** draws the map before work is picked: one destination, what is
  fog, what is frontier. Reconciles the four surfaces that disagree about what to
  do next (`TODO.md`, `state/claims.jsonl`, `selfimprove/scan.py`, the Zion board)
  and claims the destination before starting. Reach for it at session start;
  `/reground` is the narrower move when only this session's picture is stale.
- **`/reground`** reconciles this session against measured repo state. Run it when
  resuming, after a compact, or whenever a plan is about to be built on remembered
  state rather than disk.
- **`/learn-on-demand`** retrieves the smallest relevant knowledge pack. Reach for it
  instead of reasoning from memory about a library, standard, or API.
- **`/deep-research`** delegates multi-source research with citation tracking. Slow and
  expensive; the session rules say it does not fire unless you ask for it.
- **`/grill-me`** interviews you relentlessly until each branch of the decision tree is
  resolved. Reach for it when a plan feels agreed but nobody has stated the trade.

## Outbound text

Everything a human reads outside this repo goes through here.

- **`/voice-metrics`** measures a draft against the fitted corpus before it is sent. The
  source of truth for thresholds is the tool, never a number copied into a doc.
- **`/shoval-voice-draft`** drafts in the operator's voice, review-only, never auto-sends.
- **`/explain-simply`** before any status update, blocker list, handoff, or report a
  human has to read and act on.
- **`/humanize`** rewrites flagged AI-tell patterns.
- **`/slop`** lints changed prose. Note it is not a `quality-contract.json` domain and
  does not run in CI, so a clean `/slop` is a manual result, not gate evidence.
- **`/syndication-engine`** projects one canonical post across platforms. Never
  auto-publishes.
- **`/persona`** mirrors the operator's meme or Hebrew register in 1:1 chat. Hard-blocked
  in any audit, PR, eval, or spec output.

## Visual and data work

Load these before the first line of UI or chart code, per out-of-distribution rule 3.

- **`/frontend-design`** for aesthetic direction and typography.
- **`/dataviz`** before any chart, plot, dashboard, or stat tile, in any medium.
- **`/artifact-design`** before publishing an Artifact; **`/artifact-capabilities`** when
  the page needs live data, shared state, or self-update.

## Azure and agents

- **`/azure-runtime`** to call deployed models and Foundry agents. **`/agent-builder`** to
  author them. **`/openai-agents`** for platform.openai.com. **`/eval-runner`** for the
  four-phase eval pipeline.
- **`/azure-audit`** weekly dormancy and cost. **`/azure-activity-watch`** when a service
  goes cold and you suspect someone else touched it.
- **`/dispatch`** for a sync call to a registered peer. **`/claude-api`** before answering
  anything about Claude models, pricing, or limits; never from memory.

## Local corpora

- **`/whatsapp-query`** reads the local WhatsApp store. Local-only, read-only, sends
  nothing.
- **`/youtube-distill`** drives Chrome to Gemini to read a video. Slow; it needs a
  browser.
- **`/cdp`** kickstarts a browser for inspection or scraping.

## Setup and harness

- **`/update-config`** for anything in `settings.json`: permissions, env vars, and every
  "from now on when X" automation, which requires a hook and cannot be satisfied by
  memory.
- **`/fewer-permission-prompts`** scans transcripts and proposes an allowlist.
- **`/keybindings-help`**, **`/loop`**, **`/schedule`** for their obvious jobs.
- **`/writing-great-skills`** is the reference for writing and editing skills. Read it
  before adding a skill to this map, because the cost of a new skill is exactly what that
  reference is about.

## Not here

Agent types (`Explore`, `Plan`, `review-board`, `qa-lab`, and roughly thirty more) are
invoked through the Agent tool, not by name, and are not routed by this map. Lanes are in
`docs/charters.md`, and naming your lane happens before any of the above.
