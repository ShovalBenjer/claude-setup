# Spec: persona allocation, reviewer identity, and who is allowed to approve

Status: active, 2026-08-05. `active` is the vocabulary's word for this; the accurate
description is PARTIAL. §3 is built and its selftest passes; §4 and §5 are designed and
unbuilt. Nothing here is a completion claim, and §6 carries the per-criterion status
so the header word cannot flatten four DONE rows and six OPEN ones into one.

PRD: `docs/prd/autonomy-ecosystem.md` (AUTO-04, AUTO-19) and
`docs/prd/2026-08-03-unified-architecture.md` §4 quality plane.
Ticket: SETUP-PERSONA.
ADRs bound: 0004 (two-model agreement gate), 0007 (second reviewer is a free
different-family model), 0008 (reputation from external truth), 0012 (autonomy
ships only via PR gate), 0014 (publish behind a hard approval gate), 0018 (two-tier
inter-agent channel), 0019 (third-party tools adopted on recorded evidence).

---

## 1. There are three persona systems and no code joins any two of them

Measured 2026-08-05.

| system | where | count | who reads it |
|---|---|---|---|
| panel personas | `tools/review/panel.py` `PERSONAS` | 5, carrying 32 regex checks | `panel.py` itself |
| review aspects | `tools/review/actors.json` `_aspect_enum` + per-actor `may_enact` | 8 aspects across 6 actors | **nobody, until this spec** |
| company personas | `dot-claude/agents/*.md` + `gastown-company-registry.md` | 23 | **nobody; the registry is markdown no code parses** |

The panel's five are `security`, `correctness`, `ux_frontend`, `ops_release`,
`data`. The registry's eight are `correctness`, `security`, `boundary`,
`simplicity`, `perf`, `slop`, `tests`, `a11y`.

**They share two words out of eleven.** `data`, `ops_release` and `ux_frontend`
exist only in the panel. `a11y`, `boundary`, `perf`, `simplicity`, `slop` and
`tests` exist only in the registry.

So the answer to "how are specific personas picked per review type" is that they
are not picked. `panel.py` runs all five personas on every change regardless of
what changed, and the external half of the registry has never been consulted:
all 11 artifacts in `state/reviews/` record `reviewer: persona-panel/local` and
`external_note: "external backend not requested"`.

## 2. What a persona is here, and what it is not

`panel.py:21` states it directly and the definition is worth keeping: a persona is
**a named set of pattern checks**, not a prompt saying "act as a security expert".
That is why the panel is deterministic and why its findings carry `file:line`.

The registry's aspects are a different kind of thing: they are a **capability
declaration**, a statement that a given external actor is willing to be held to a
dimension. `may_enact` is a permission, not a behaviour.

The 23 company personas are a third kind again: session-time subagent definitions
with their own tools and system prompts.

Conflating the three is the reason this spec exists. They are a rule set, a
permission, and an agent. Only the first has ever run.

## 3. The allocator (BUILT)

`tools/review/allocate.py`. Given a change, decide which aspects it needs and
which actors may enact them.

```
python tools/review/allocate.py plan --files src/App.tsx migrations/003.sql
python tools/review/allocate.py selftest
```

Three rules, each of which exists because of something measured:

1. **Decorrelation is on `model_family`, never on `host`.** `actors.json` carries
   this in its own `_decorrelation_contract`: nvidia-nim and openrouter are both
   multi-vendor resellers and both serve deepseek, qwen and llama, so picking two
   hosts can silently produce the same weights twice and the agreement gate would
   report agreement carrying no information.
2. **A `VARIES-BY-MODEL` family can never be half of a pair.** The first real run
   paired `nvidia-nim [VARIES-BY-MODEL]` with `qwen-dashscope [alibaba-qwen]` for
   the `slop` aspect, which is exactly the forbidden pair, because nvidia-nim
   serves qwen. A reseller family cannot be shown to DIFFER from a partner it may
   itself be serving, so it is admissible only as a solitary reviewer, and the
   exclusion is always stated rather than silent.
3. **Holes are reported, never filled.** `ops_release` and `data` map to no
   registry aspect and stay `None`. An aspect nobody declares returns
   "unreviewable by the current registry". An unreachable actor is ranked last and
   named, never dropped.

### What the first real plan exposed

```
a11y     claude-code-action [anthropic-claude]
         ! wanted 2 decorrelated actors, found 1
slop     qwen-dashscope [alibaba-qwen], gemini [google-gemini]
         ! nvidia-nim excluded: a VARIES-BY-MODEL family cannot be shown to differ
```

**Accessibility can never get a second opinion.** Exactly one actor declares
`a11y`. That is a registry gap, not an allocator gap, and it was invisible before
anything read `may_enact`.


## 3a. Prior art, searched 2026-08-05, and the claim it retracts

The Stop hook was right to stop this. §3 called the allocator "the missing joint"
and presented the family-decorrelation rule as something this session discovered by
failing. The failure was real; the rule is published, older, and better developed.

**Exact queries run**, across academic, practitioner and product vocabulary:

1. `LLM ensemble correlated errors diversity model family selection judge decorrelation survey`
2. `automatic code reviewer recommendation assign reviewers by expertise pull request tool`
3. `multi-agent LLM code review router assign specialist agent per review dimension framework awesome list`

**Not-a-gap signals checked.** A survey FIRES: `Large language models for automated
scholarly paper review: A survey` (arXiv 2501.10326) and `Deploying Foundation
Model Powered Agent Services: A Survey` (arXiv 2412.13437). No curated awesome-list
for reviewer routing surfaced, no recurring workshop and no three benchmarks
sharing a name for the problem. One signal firing is enough. **This is not a gap
and nothing here is novel.**

What the searches found that is directly upstream of §3:

- `Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation
  Panels` (arXiv 2605.29800). Family-correlated errors reduce a nine-judge panel to
  **2.5 to 3.6 effective independent voters**. This is the decorrelation rule, with
  a number on it.
- `Hidden Clones: Exposing and Fixing Family Bias in Vision-Language Model
  Ensembles` (arXiv 2603.17111). Hierarchical Family Voting aggregates WITHIN
  families before voting ACROSS them, recovering 18 to 26 points; QualRCCV weights
  by calibration, family quality and **inverse family size**. Strictly stronger
  than this allocator's binary "never pair two of one family".
- `Don't Always Pick the Highest-Performing Model: An Information Theoretic View of
  LLM Ensemble Selection`. Budget-constrained selection by mutual information,
  where **correlation matters and accuracy does not**, which is the opposite of how
  a reader would naturally rank `actors.json`.
- Practitioner and product: GitHub CODEOWNERS routes reviewers by file path, and
  Aviator FlexReview and LinearB gitStream route dynamically by domain expertise,
  complexity and availability. §3's `PATH_ASPECTS` is CODEOWNERS with fewer
  features.

**The correction that matters, and it changes the design.** The literature treats
error correlation as the quantity and model family as a PROXY for it. This spec
had the proxy hard-coded in a JSON file and declared by hand. Two consequences:

1. The `VARIES-BY-MODEL` wrinkle that §3 treats as a special case is not special.
   It is the general case of unknown correlation, and the information-theoretic
   answer is to MEASURE pairwise disagreement between actors rather than to declare
   a family string.
2. This repo can measure it. `state/reviews/*.json` is exactly the substrate:
   run two actors on the same diff, record whether they flag the same lines, and
   the correlation is observed rather than asserted. Until that runs, every
   decorrelation claim here is ASSUMED.

So the allocator survives as a cheap first cut with its justification demoted: it
implements a published proxy, badly, and the honest next step is PERSONA-10.

Sources:
[Nine Judges, Two Effective Votes](https://arxiv.org/html/2605.29800) |
[Hidden Clones](https://arxiv.org/html/2603.17111) |
[Are Diversity Metrics Measuring Diversity?](https://arxiv.org/html/2607.20768v1) |
[Wisdom of LLM Crowds](https://arxiv.org/html/2607.18269v2) |
[LLMs as a Jury](https://arxiv.org/html/2607.10139) |
[Scholarly paper review survey](https://arxiv.org/pdf/2501.10326) |
[Auto-assign reviewers in GitHub](https://blog.pullnotifier.com/blog/how-to-automatically-assign-reviewers-in-github) |
[LinearB find code experts](https://linearb.io/blog/find-code-experts) |
[AgentRouter](https://aclanthology.org/2026.acl-long.33/)

## 4. Who approves, who reviews, and the gap between the ADRs and the code

| question | ADR says | code does |
|---|---|---|
| who approves | class-based: `auto:low` auto-merges on CI green **plus both-model approval**; everything else is an operator phone tap (0012, 0014) | only the operator, by hand. Nothing has ever auto-merged |
| who reviews first | two independent reviews, different families, **neither seeing the other's output** (0004, 0007) | `persona-panel/local` on all 11 artifacts. No external model has ever reviewed |
| is there agreement | the gate suppresses single-model false positives (0004) | **no `agreement` domain in the 14-domain contract, and no implementation anywhere in `tools/`** |

**ADR-0012's auto-merge is gated on a mechanism that does not exist.** That is the
most load-bearing gap on this page: the governance documents describe a system
that was never built, which is worse than having no documents, because a reader
reasonably assumes the gate is there.

Two honest resolutions, and this spec does not choose between them:

- **Build it.** The allocator in §3 is the missing input. What remains is running
  two allocated actors blind to each other and comparing findings.
- **Amend 0004 and 0012** to record that the agreement gate is designed and
  unbuilt, and that `auto:low` therefore cannot auto-merge.

Doing neither is the status quo and it is the option with the worst properties.

## 5. Reviewer identity (DESIGNED, UNBUILT)

Measured: **every agent is `ShovalBenjer (User)`.** Issue #38's derived feed, every
PR, every comment. `bus.py` has `from_lane` derived from cwd (four possible values)
and a `from_session` field that is the empty string in all 25 rows, which
`bus.py:39` already documents: `CLAUDE_SESSION_ID` is not exported into the hook
environment.

And a distinction that matters for ADR-0008, which computes reputation from
external truth: **hash-chaining gives tamper-evidence, not authorship.**
`bus.py verify` proves no row was altered after the fact and proves nothing about
who wrote one. Anything that can append to `state/bus.jsonl` can claim any lane.
Reputation attributed to a lane is therefore attributed to a claim, not to an
actor.

External practice, searched 2026-08-05 rather than assumed: per-agent identity is
the consensus and shared identity is named as the specific failure, because shared
roles collapse the attribution needed for incident response. The shipped mechanism
is a GitHub App per agent giving each a `[bot]` signature with short-lived
installation tokens, attributing the action to the agent and recording the owner as
the accountable principal. A2A v1.0 (Linux Foundation, 2026) formalises this as an
**AgentCard**: machine-readable identity, capabilities and security requirements,
JWS-signed.

`actors.json` is already most of an AgentCard. It carries host, model_family,
model, credential_env, cost_tier, a measured/declared/unreachable legend, and now
`may_enact` has a consumer.

### The clamp

**One human, one machine, no adversary.** The value here is ATTRIBUTION (which
agent did this) and not AUTHENTICATION (proving an agent was not impersonated). So
take the GitHub App and the session id; do **not** build JWS signing over bus rows.
That is A2A solving a cross-organisation trust problem this estate does not have,
and ADR-0019 says third-party tools are adopted on recorded evidence rather than on
principle.

## 6. Acceptance

| # | criterion | check | status |
|---|---|---|---|
| 1 | an aspect maps to actors that declare it | `allocate.py plan --aspect security` | DONE |
| 2 | no two picked actors share a `model_family` | `allocate.py selftest` | DONE |
| 3 | a reseller family is never half of a pair | `allocate.py selftest` | DONE |
| 4 | unreviewable aspects and unreachable actors are named, not hidden | `allocate.py selftest` | DONE |
| 5 | `panel.py` consumes the allocation instead of running all five personas always | a review artifact naming its allocated actors | OPEN |
| 6 | two allocated actors review one PR blind to each other | a `state/reviews/*.json` with `reviewer` other than `persona-panel/local` | OPEN |
| 7 | their findings are compared and disagreements go to the digest, not the PR | an `agreement` domain in `quality-contract.json` | OPEN |
| 8 | at least two actors declare every aspect in the enum | `allocate.py plan` over all 8 with no "found 1" note | OPEN, `a11y` has one |
| 11 | decorrelation is MEASURED, not declared | pairwise disagreement rate between two actors on one diff | OPEN, and until it runs every decorrelation claim here is ASSUMED |
| 9 | a feed comment carries a `[bot]` identity that is not the operator | `gh issue view 38 --comments` | OPEN |
| 10 | `from_session` is populated on new bus rows | `bus.py log` | OPEN |

## 7. What this spec does not do

It does not touch the 23 company personas. They are session-time subagents with a
different lifecycle from review actors, and folding them into the aspect vocabulary
would be a third conflation on top of the two this spec is untangling. Whether the
Gastown registry should become machine-readable is a separate question and it needs
its own evidence, starting with whether anything would read it.
