---
PRD: prd/claude-os.md
Ticket: SETUP-OS
Status: active, first run of the repo-compare skill
---

# Repo compare, run 1: the twice-dropped comparison finally executed

Run 2026-08-11 by the repo-compare skill on its first invocation. The request behind it
was scoped on 2026-08-07 (claims row 25, "comparing against the WhatsApp GitHub repos
which may never have been compared") and again on 2026-08-10 (row 28, prime-agent
analysis), and both times the session ended with no output file and no note. Evidence
class for everything below: README and repo metadata reads via `gh repo view` and
`gh api repos/<r>/readme`, no clone, no execution. That is one level of evidence below
"tried it", and each ADOPT names what a trial would have to show before implementation.

Corpus: 199 distinct saved repos in `state/resource-ledger.jsonl` (extraction command in
the skill). Examined this run: 5 saved plus 3 fresh search hits, 8 of a much larger
backlog, cap stated per the skill. `resources.py coverage` before this run: most saved
rows have no note; this run closes 8.

## Verdict table

| repo | stars | pushed | verdict | anchored reason |
| --- | --- | --- | --- | --- |
| PrimeIntellect-ai/prime-agent | 13848 | 2026-08-11 | ADOPT (2 mechanisms) | README: Continual Harness stores memories/skills/subagent specs as durable state with evidence-backed `/refine` updates and rollback snapshots; heartbeats + `/goal` + bounded `/autonomous` with user-defined gates |
| sapph1re/glm-harness | 0 | 2026-07-05 | ADOPT (1 mechanism) | README: retargets the stock Claude Code CLI at any Anthropic-wire endpoint via `ANTHROPIC_BASE_URL`; ships DeepSeek and Kimi profile templates (marked documented, untested) and a zero-spend mock endpoint battery |
| adewale/skill-eval-harness | 65 | 2026-08-01 | ADOPT (1 mechanism) | README: causal lift of a skill measured as paired with/without runs plus `skill-trigger-matrix` for autonomous-activation rates; grade path is deterministic, no model call |
| amirfish1/claude-command-center | 116 | 2026-08-10 | ADOPT (as replacement) | README: local board over Claude Code, Codex, Cursor, Kilo, OpenCode sessions with spawn/monitor/steer; overlaps most of `docs/specs/2026-07-24-command-center-superior.md`, which has no implementation here |
| bmad-code-org/bmad-method | 51762 | 2026-08-10 | WATCH | README: plan-to-build method with right-sized process; the estate already runs a PRD control plane; the `bmad-loop` module ("builds, verifies, and retros a whole epic unattended") is the piece to re-examine when S6 lands |
| Synaptic-Labs-AI/PACT-Plugin | 71 | 2026-08-11 | WATCH | README: 12-specialist orchestration as a Claude Code plugin over experimental Agent Teams; same shape as the Gastown registry, delivered as a plugin; revisit if Agent Teams goes stable |
| deepseek-ai/DeepSeek-V3.2 | 1631 | 2025-11-18 | REFERENCE | weights repo for the open-weights V3.2 line the eval pipeline already names as audit model; license field reads null via API (custom model license), so trainability terms need a direct read before any training claim |
| ThePrimeagen/prime-agent | 48 | 2026-08-10 | IGNORE | name collision only; the operator's prime-agent reference resolves to PrimeIntellect-ai/prime-agent |

## The ADOPT paragraphs

**prime-agent, mechanism 1: the refine loop.** Their Continual Harness is this estate's
open problem S6 shipped as product: durable supplemental state (memories, skills,
subagent specs) that the agent itself refines in small evidence-backed steps, never
touching the immutable base prompt, with snapshots for rollback. The landing spot here
is the autonomous-loop design in `docs/specs/2026-08-10-open-scope-delegation-plan.md`
item 1: their refine-with-rollback is the missing shape for how the loop edits its own
rules without the silent-live-edit failure the-loop-may-act forbids. A trial must show:
one refine cycle on a copy of `dot-claude/rules`, diffed and reversible.

**prime-agent, mechanism 2: heartbeats and goals.** `/heartbeat`, `/goal`, and bounded
`/autonomous` with user-defined quality gates map one-to-one onto the dead cron layer
here (CronList measured empty on 2026-08-11 against 8 promised jobs). Their framing,
re-enter the session on a pulse rather than re-bootstrap weekly, is the fix for the
7-day-expiry death spiral. Also relevant upstream: PrimeIntellect's `verifiers` and
`prime-rl` repos are the training half of the operator's "a model I can train on"
thread; that analysis was claims row 28 and stays open, now with a named starting point.

**glm-harness: the backend pivot mechanism.** The whole "free or better tier model"
question turns out to need no new harness: the stock Claude Code CLI retargets at any
endpoint speaking the Anthropic wire format. This repo wires GLM-5.2 and ships DeepSeek
profile templates plus a mock server for plumbing tests with zero spend. The landing
spot: a `deepseek` profile under a new `tools/backends/`, validated first against their
mock, then against a funded DeepSeek endpoint only after the operator approves spend.
A trial must show: their 6-test smoke battery green on the mock profile from this
machine. Their own caveat carries over verbatim: Anthropic does not support non-Claude
models behind Claude Code, and a CLI update may break retargeting.

**skill-eval-harness: measure the 79.** The live tree holds 79 skills and nothing here
measures whether any of them helps. Their paired with/without design plus the
trigger-matrix (does the skill fire when it should, stay quiet when it should not)
is exactly the missing oracle for the skills economy, and their grade path is
deterministic so it costs no model spend. Landing spot: run it AS-IS on the 5 most-used
skills from `state/skill-use.jsonl` before extending `tools/skilleval`. A trial must
show: one skill's lift report generated end to end locally.

**claude-command-center: buy, do not build.** The command-center-superior spec
(2026-07-24) describes a session board this repo already ships, including ingest of
Codex and OpenCode sessions. Source-available, free for non-commercial use, curl or
brew install, read-only demo. Recommendation: retire the spec to
`docs/specs/archive/` as superseded-by-external and trial CCC against live sessions.
A trial must show: it attaches to a running WSL Claude Code session on this machine.

## What this run did not do

No repo was cloned or executed; verdicts are README-grounded. 191 of 199 saved repos
remain unexamined. The DeepSeek license text was not read. None of the four ADOPTs is
implemented; each is a proposal with a named trial gate, and implementation is a
separate claimed session per the skill's hard limits.
