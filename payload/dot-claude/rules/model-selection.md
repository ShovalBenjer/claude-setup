# Claude model selection

Use model choice as a risk and verification decision, not a quality claim.
Model internals are not public; behavior on this repository is the relevant
evidence.

## Defaults (the fable experiment ENDED EARLY on 2026-07-29)

- Saved default for new sessions is `claude-opus-5[1m]`, set by the operator on
  2026-07-29 in the evening.
- The fable experiment ran for part of one day and was ended by operator
  decision BEFORE its 2026-08-05 falsifier date, so it produced no verdict.
  Recording this rather than quietly deleting it, because an experiment
  abandoned early and an experiment that failed are different facts, and only
  the second one is evidence about the model. What is known: the session that
  ran on fable at xhigh effort was stopped twice by the operator for scope and
  writing-rule failures, which is a data point about that session and not a
  measurement of the model.
- If the comparison is ever re-run, the falsifier stands as written: against
  the opus baseline on disk, compare handback blocks and restart turns per
  session (state/handback-log.jsonl), gate verdicts, refusal events on
  security-adjacent work, and subscription throttling; 2x token price needs a
  measured reduction in stalls to justify it. Until then fable is not a
  default, only the long-horizon and hardest-design rows below.
- `claude-opus-5` is the interactive workhorse: harness and oracle edits,
  review verification, gate-driven implementation, anything bounded.
- `claude-sonnet-5` for bounded implementation and parallel workers.
- Haiku only for low-risk inventory or transformation with a cheap oracle.

## Routing by task shape (per-MTok in/out pricing cached 2026-06-24)

| Model | $ | Route here | Keep away from |
|---|---|---|---|
| fable-5 | 10/50 | longest-horizon autonomous runs, hardest design and architecture calls, multi-agent coordination, tail sampling in /diverge | quick interactive edits; routine work at max effort, which overthinks |
| opus-5 | 5/25 | day-to-day harness work, oracle changes, adversarial verification | mass mechanical fan-out |
| sonnet-5 | 3/15 (intro 2/10 through 2026-08-31) | Workflow fan-out measurement agents, backfills, migrations, bounded features | oracle edits |
| haiku-4.5 | 1/5 | inventory, extraction, classification with a cheap oracle | anything whose output cannot be checked cheaply |

## Fable-specific handling

- Thinking is always on and cannot be disabled; the raw chain of thought is
  never returned. `budget_tokens` and sampling parameters are rejected.
- API code must branch on `stop_reason == "refusal"` before reading content.
- Separate rate-limit bucket from the Opus pool; requires 30-day data
  retention (not available under zero data retention).
- De-prescribe: state goal and constraints, not steps. Over-prescriptive
  prompts measurably reduce Fable output quality; A/B old scaffolding off.
- Effort: `low` on Fable already matches prior models at `xhigh` on many
  tasks. Default `high`; reserve `xhigh`/`max` for the hardest problems.

## Effort level: the live setting contradicts this file, on purpose for now

`~/.claude/settings.json` has run `effortLevel: xhigh` globally since before the
fable experiment, while the row above prescribes `high` as the default. That
gap was found on 2026-07-29 and is deliberately NOT closed by editing one to
match the other, because nobody has measured what `xhigh` buys on routine work
in this repo. Closing a contradiction by rewriting the losing side is how a
rule stops describing anything.

What would settle it: run a week on `high`, compare against the xhigh sessions
already in `state/handback-log.jsonl` and `state/gate-runs.jsonl` on the same
axes the fable falsifier named. Until that runs, treat the live value as the
status quo and this row as the untested hypothesis, not the other way round.

## Workflow tool overrides

`agent()` accepts per-call `model` (sonnet, opus, haiku, fable) and `effort`
(low through max), independent of what the session was set up with. Pattern:
measurement and mechanical stages on sonnet or haiku at low effort;
adversarial verify and judge stages on opus or fable at xhigh. Ultracode is
opt-in per session; without it, fan-out requires an explicit ask.

## Standing constraints (unchanged)

- Keep first-party Claude.ai OAuth routing. Do not introduce gateways or free
  proxies unless the operator explicitly requests a controlled experiment.
- Adaptive thinking stays enabled. 1M context is available.
- Do not copy the whole transcript to a worker. Send goal, constraints,
  relevant files, required evidence, write scope, and stop condition.
- Escalate by task risk: a stronger model does not replace tests, independent
  review, benchmarks, or external-state verification. For a non-trivial
  implementation, use `/prove-implementation`. For domain knowledge, retrieve
  a narrow pack with `/learn-on-demand`.

## Correction 2026-07-30: the live effort value is `low`, not `xhigh`

The section above says the live `effortLevel` has been `xhigh` since before the
fable experiment and treats the gap against its own prescribed `high` default as a
deliberate, unmeasured contradiction. That is no longer the fact on disk.

`~/.claude/settings.json` now carries `effortLevel: low`, set by the operator at the
start of the 2026-07-30 session as an explicit trial: his words were that if he is
happy with the output at `low`, it becomes the new consensus. So the live value has
moved past the prescribed default in the other direction, and the comparison the
older row asked for was never run at `xhigh` either.

Recorded as a correcting row rather than an edit to the section above, because that
section's own argument is that closing a contradiction by rewriting the losing side
is how a rule stops describing anything. What is now true: three effort levels have
been proposed (`xhigh` live, `high` prescribed, `low` live), and none has been
measured against the axes the fable falsifier named. The trial in progress is the
first one with a stated acceptance condition, and that condition is operator
judgement rather than a ledger, so it will not produce a comparable number unless
`state/handback-log.jsonl` and `state/gate-runs.jsonl` are read at the end of it.

## Correction 2026-08-12: available roster (operator-stated)

Opus 5 is no longer available. The roster is: `claude-fable-5` (session default,
saved 2026-08-12), `claude-sonnet-5`, Opus 4.6, and `claude-haiku-4-5` (which the
operator flags as highly underused; route inventory, extraction, classification,
and cheap-oracle work there deliberately). Every `opus-5` route above reads as
Opus 4.6 until the table is refit. The pricing row for opus-5 is stale with it.
