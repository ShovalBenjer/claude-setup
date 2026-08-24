# Session retro, 2026-07-29 (lane B): modes, models, workflows, interruption, observability

Operator questions answered here, each against what is on disk rather than from
memory: auto mode + /loop + goal versus bypass mode; fable/opus and effort
levels; whether workflows earn their cost and against which KPIs; the effect of
interruption and steering mid-execution; enforcement maturity ("hard to trust a
.md/.py"); free-tier CLI judges worth adding; and the Amir/CCC competitive read.

## 1. Auto mode + /loop + goal, versus bypass mode: closed

The 2026-07-29 handoff closed this with numbers: after the 07-26 flip to
bypassPermissions, permission blocks fell from 77 to 5, and the remaining 5 are
deny-list credential reads that SHOULD block. The thing that actually stops
sessions is not permissions, it is convergence: the model hands back with an
offer instead of continuing. That is why the fix landed as a Stop-hook
(completion_gate.py handback check, 2 real blocks, 2 releases, 0 trapped
sessions, 17 tests), not as a mode change.

Practical composition that follows from the measurements:

- Mode: bypassPermissions with the deny list, as live today. Note the standing
  drift: committed canonical settings say acceptEdits, live says bypass.
- Goal-shaped prompts plus the work-cadence rule (front-load questions, then a
  long run) attack the ~31% handback rate at its cause.
- /loop is for polling external state, not for keeping the model working; the
  Stop gate already does the latter. Adding /loop to mask handbacks would pay
  tokens to hide a defect the gate now measures (state/handback-log.jsonl).

## 2. Fable / opus / effort levels: the experiment ended early, with no verdict

SUPERSEDED the same evening this was written. When this section was drafted the
saved default was claude-fable-5, held as a one-week experiment with a
falsifier due 2026-08-05. The operator set `opus[1m]` as the saved default that
evening, ending the experiment after part of one day. It therefore produced NO
verdict, and model-selection.md now says so in both copies rather than quietly
deleting the row: an experiment abandoned early and an experiment that failed
are different facts, and only the second is evidence about a model.

The routing table is unaffected: opus for day-to-day harness and oracle work,
sonnet for bounded fan-out, haiku only with a cheap oracle, fable reserved for
longest-horizon and hardest-design work rather than as a default.

Effort: the rule prescribes `high` as the default and live settings run `xhigh`
globally. That contradiction is now recorded IN the rule instead of being
resolved by editing whichever side is easier, because nobody has measured what
xhigh buys on routine work here. Closing a contradiction by rewriting the
losing side is how a rule stops describing anything. What would settle it is a
week on high compared against the xhigh sessions already in
state/handback-log.jsonl and state/gate-runs.jsonl.

## 3. Workflows: what objective, against what cost

The operator's question, restated: what is the objective a Workflow fan-out is
driven against, and is it worth the tokens.

CORRECTION, made 2026-07-29 in the evening. This section originally said "this
repo has never measured a workflow's yield." That was false, and false against
evidence sitting in this repo's own message bus, unread since 2026-07-25:

    2026-07-25T03:05:29 B->B [warn] workflow wf_4d739b98-873 burned 2.66h and
    3.64M subagent tokens and produced nothing usable

    2026-07-27T05:32:42 D->B [warn] one fan-out exhausted the session WebSearch
    budget and everything after it degraded silently

So the yield HAS been measured twice, and both measurements are negative: one
workflow spent 2.66 hours and 3.64 million subagent tokens for no usable
output, and one fan-out exhausted a shared session budget in a way that
silently degraded everything downstream. The reason the section claimed
otherwise is the same defect this retro documents elsewhere: the bus inbox hook
had been dropped from live settings, so nineteen messages addressed to this
lane were never delivered. This is the second occurrence in one week of an
absence claim made against evidence already in hand (L-2026-07-29-a).

The negative infrastructure evidence stands alongside it: workflow selftests
appended scratch rows to the real gate ledger and produced a FAIL-then-PASS on
tree 842125e6 (risk row 1 in the 07-29 handoff; isolation is an open TODO).

What follows from three negative data points and zero positive ones is not
"workflows are bad", it is that no workflow in this repo has yet been run with
its yield instrumented, and two that ran uninstrumented were expensive
failures. The KPI list below is therefore the precondition for the next
workflow, not a nice-to-have after it.

KPIs that make the question answerable, most already fed by instruments that
exist as of today:

- Cost per session: the statusline tap now writes cost_usd per session to
  state/sessions/*.json. Sum over a week is the denominator.
- Tokens per confirmed finding: for review-shaped workflows, confirmed
  findings that survive verification, divided by output tokens. A workflow
  that finds nothing a single agent would not have found loses.
- Handback and restart rate: state/handback-log.jsonl, already live.
- Verified-claim rate: refute.py HELD versus REFUTED on claims the session
  wrote (state/claims-verify.jsonl).
- Free-channel draw: state/api-usage.jsonl quota rows for openrouter and
  nvidia, cost-zero but rate-bounded, so the KPI is ceiling headroom.

Policy until numbers exist: workflows stay opt-in (ultracode off), fan-out
stages on sonnet at low effort, judge stages on opus or fable at high, per the
model-selection overrides. The first measured workflow should be a review one,
because its yield metric (confirmed findings) is the cheapest to count.

## 4. Interruption and steering mid-execution

What the ledgers can say: interruptions divide into two classes with opposite
costs.

- Steering (mid-turn messages that redirect scope) is cheap when state is
  externalized. This session is the data point: five mid-turn messages
  (project split context, observability complaint, CLI question, Amir/CCC,
  enforcement maturity) landed during execution; the task list absorbed them
  as new tasks or scope edits, and none of the five caused a restart or lost
  work. The claims rows and task list are what made that absorption visible.
- Restarts (operator re-issuing work that stopped) are the expensive class:
  66 of 420 turns were pure restart turns, ~940 minutes per week idle, in the
  week measured for the work-cadence rule. Those were caused by convergence
  handbacks, not by operator interruptions.

So the measured answer: interruption does not damage execution here, stopping
does. Steering mid-execution is the operator's highest-bandwidth control and
costs little as long as the session keeps claims, tasks, and ledgers current.
This is an internal observation over one week of one operator's transcripts,
not literature; treat it as calibration data, not a law.

## 5. Enforcement maturity ("I find it hard to trust a .md and a .py")

The distrust is directionally correct and the repo's own records agree: prose
does not enforce (ADR-0005), and several accountability fields exist that
cannot fail (lessons L-2026-07-27-d, L-2026-07-29-c). The honest maturity map:

Mechanically enforced today (a command goes red):
- The 12-domain gate (gate.py), each oracle's selftest, and mutation specs
  proving the selftests can fail (tools/audit/mutate.py).
- Live Stop hooks: completion_gate handback check (2 real blocks),
  prior_art_gate (caught the L-2026-07-29-a absence claim), ship_gate_stop.
- pointers.py (dead hooks/skills), slop_lint.py (prose), codemap.py (map
  drift and undocumented directories), bus.py verify (chain integrity).

Prose only, zero mechanical teeth:
- Rule files themselves, including numerical-stack.md and any orjson/polars
  preference: nothing lints an implementation for `import json` versus orjson
  or pandas versus polars. The operator's example is exact.
- Lane boundaries: 0 enforcing lines; claims.jsonl is convention.
- Waiver reasons (checked for presence, never truth) and the confidence
  thresholds in CLAUDE-OS.md (no outcome ledger yet, RT-1).

Architecture, planned rather than vague: the layering stays
contract -> oracle -> selftest -> mutation, and the next level is closing the
prose gaps with three specific oracles, now ticketed in TODO.md: a stack-lint
oracle (rules/*.md preferences become grep/AST checks and a gate domain), a
lane-enforcement check in the Stop gate (session cwd and claims row must
agree), and waiver-falsifier execution (a waiver reason must name a command,
and the gate runs it). Each lands with its own selftest and mutation spec or
it repeats L017's class.

## 6. Free-tier judges: wired today, and the next highest-yield candidates

Wired and verified this session (updated same evening after the operator
ruled out interactive logins; every live channel proved by a real completion):
- NVIDIA NIM (tools/nvidia/nim.py): live selftest 9/9 including a real
  completion; separate vendor pool, local 100/day policy ceiling. Inference
  only; logprobs are the sole interior signal. Weights live on Hugging Face,
  a different project.
- Gemini: LIVE non-interactively. The .env GEMINI_API_KEY (39 chars, AI
  Studio shape) was simply never exported to the CLI; with it set in-process,
  `gemini -p` returned PONG, exit 0. Standing rule holds: only explicitly
  public, non-confidential input on this channel.
- Codex: LIVE. The failure was a stale `gpt-5.6-sol` model pin plus CLI
  0.145; after update to 0.146 and unpinning (config .bak kept), default
  `codex exec` returned PONG. Paid ChatGPT subscription, stays /codex-call.
- GitHub Models: LIVE via gh-models extension on existing gh auth; 36-model
  free catalog; PONG from openai/gpt-4o-mini and meta/llama-3.3-70b-instruct.
- qwen-code 0.21.1: PARKED. Its OAuth requires a browser login the operator
  declined to do, and the on-disk QWEN_API_KEY is a 116-char non-key. The
  qwen family is already served by the OpenRouter and NVIDIA preference
  lists, so the CLI adds no capability worth the login.

Highest-yield candidates worth one probe each, not yet wired (quotas are
advertised numbers, to be verified at wiring time): GitHub Models via the gh
CLI (already authenticated, rate-limited free catalog including several
frontier-adjacent models); Groq and Cerebras free API tiers (very high token
throughput for fan-out judging). Lower yield for this repo right now: AWS Q
Developer and Copilot CLI (IDE-completion shaped, weak judge fit), Azure
(no free LLM tier beyond trial credits; the operator already has paid Azure
runtime wired elsewhere).

## 7. Amir / CCC competitive read (from the 2026-07-29 investigation agent)

CCC is Claude Command Center (ccc.amirfish.ai, github amirfish1), Amir Fish's
Mac-first local dashboard orchestrating fleets of Claude Code / Codex / Cursor
/ Kilo sessions, backed by a queue system (WatchTower): Kanban and Flow views,
attention detection, GitHub-Issues-to-worker lifecycle with auto-close on
commit SHA, mobile UI, one-line installers, Homebrew tap, auto-update.
Velocity is the headline: 15 releases between 07-15 and 07-28, 109 stars.

Where he is ahead: distribution (installable product, webinar, onboarding
funnel), multi-engine session UI, productized queue-to-worker loop with users
other than its author. Where this repo is ahead: verification depth (gate,
selftests, mutation, hash-chained ledgers, prior-art discipline), Windows
breadth, provenance rigor; CCC's trust model is "watch the dashboard", ours is
"the oracle disagrees with the agent's report". The piece worth studying is
his GitHub-Issues-to-worker queue, which maps directly onto TODO.md plus the
gate. His site/README say MIT while GitHub classifies "Other"; unresolved.
Full detail with dates and sources is in the agent report inside this
session's transcript; user counts and revenue are not published anywhere.

## 8. Observability: what shipped, what it unblocks

Shipped today: the statusline (operator pick: Rich) renders
`lane · repo · model · $cost · ctx%` per terminal with honest lane markers
(declared plain, inferred as ?>X, unknown as ?), and tees a per-session
snapshot to state/sessions/<session_id>.json on every refresh. That registry
is deliberately the substrate for the operator's own UI, which replaces
Claude's: the operator wants out of the vendor surface, and the new
repo-stack-reasoning rule (authored today from the operator's own workflow
text, both copies) governs how that UI's stack gets chosen. FleetView v0 is
ticketed to consume the registry; ecosystem.db (AUTO-06) remains the fuller
substrate for tickets and work claims.

## 9. Also done this session, with the check that proves it

- Lane A retired, intake folded into B: charters.md, session-recall.sh (both
  copies emit the new lane text on a real payload), launchers and chooser
  drop A and gain E, tests/test_workspace_launcher.py 8/8 including a new
  negative test that lane A is refused.
- Cloudflare split live: case-ledgers.pages.dev serves the Writing index and
  both essays (HTTP 200, title "The Bench", 673KB body), media 200; old
  /writing/* URLs 301 there; the learning PWA no longer ships writing/.
  Two commits on daily-deep-learning main (930f2d0, e6c7c82), Actions run
  30464857878 green end to end.
- The the-bench namespace collision is lesson L-2026-07-29-f (external
  presence read as ownership); the naming pick is recorded in docs/taste.md.
- NVIDIA key moved from the shared .env into Windows User env without ever
  entering model context (length and prefix check only).
