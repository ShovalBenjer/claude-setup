# Which persona metrics we are missing, from outside sources

2026-08-06. The operator asked for this twice. The first time I declined it and
said the local measurement dominated, which was mine to justify and I did not
justify it. This is the sweep, run by four subagents over 19 personas.

Read the caveat first, because it bounds everything below. All four agents hit
sustained HTTP 429 from `export.arxiv.org` and `api.semanticscholar.org`. Two
worked around it via OpenAlex, Crossref and direct `arxiv.org/abs/<id>` fetches;
the others fell back to papers they could name in advance. **So this is biased
toward well-known work and away from anything recent that only a working search
endpoint would surface.** None of the agents papered over it, and their ABSENCE
sections list the exact queries that never completed. Treat "nothing found" here
as "the search that would have found it was rate-limited", not as a claim about
the literature.

## The finding that matters most: our metric shape is externally supported, and the obvious alternative is contaminated

`The SWE-Bench Illusion` (arXiv:2506.12286) measured state-of-the-art models
identifying buggy file paths **from the issue text alone, with zero repository
access, at up to 76% accuracy**, falling to 53% on repositories outside the
benchmark. Verbatim 5-gram overlap on ground-truth functions was 35% on
SWE-bench Verified against 18% on comparable non-benchmark tasks.

That is direct evidence for a decision this repo already made and recorded in
`docs/specs/2026-07-31-github-native-project-surface.md` section 4.1, which
rejected importing benchmark-shaped scores and argued for measuring this harness
on its own ledgers. The external literature now supports that from the other
direction. Four further papers argue the same fragility (arXiv:2509.16941,
arXiv:2602.09540, arXiv:2512.10218, arXiv:2505.23419).

## Metrics we are missing that are computable from artifacts already on disk

Ranked by how little new instrumentation they need.

| # | Metric | Source | What it needs here |
|---|---|---|---|
| M1 | **Review-finding precision**, true findings over total flagged, paired with resolution rate and never reported alone | CR-Bench, arXiv:2603.11078, which measured that resolution rate alone obscures agent quality because agents inflate it by over-flagging | `state/reviews/*.json` already holds every panel finding. Nothing has ever labelled one true or spurious. One label field closes it |
| M2 | **Regression flip rate**, tests flipping pass to fail between two versions, treated as first-class promotion evidence rather than an aggregate score | AgentDevel, arXiv:2601.04620 | `state/gate-runs.jsonl` plus git history. We record verdicts per run and never diff two runs' pass/fail matrices |
| M3 | **Request-to-outcome transition rate** | our own `tools/intent/tickets.py` lifecycle, unused | 467 tickets, all CAPTURED, zero transitions ever. The state machine and its legal-edge allow-list already exist |
| M4 | **Citation accuracy scored separately from factual accuracy** | Anthropic multi-agent research system, 2026-06-13, which found a single LLM judge on five separate axes most consistent with human judgment | `state/claims.jsonl` carries provenance per claim. No scorer reads it. The point of separating them is that a claim can be true but mis-cited, or correctly cited and false |
| M5 | **Per-task token and tool-call logging** | same source, which measured token usage alone explaining ~80% of performance variance on BrowseComp, and token plus tool-calls plus model reaching ~95% | Not logged anywhere. This is the largest single explanatory variable in the external work and we capture none of it |
| M6 | **Spawn rate per persona** | Anthropic names over-spawning as an observed failure mode; the inverse is ours | `state/agent-spawns.jsonl` exists and has 0 rows. Now that all 19 personas are operational the ratio is finally meaningful |

## Metrics named as vanity or misleading, with sources

These matter as much as the additions, because three of them are things a
reasonable person would otherwise build.

- **Step-conformance scoring.** Anthropic states multi-agent systems do not
  follow one correct path, so turn-by-turn evaluation produces false negatives.
  Evaluate the end state, not the route.
- **Resolution rate alone.** CR-Bench, above. Without a precision denominator it
  rewards over-flagging.
- **Any static benchmark pass rate.** arXiv:2506.12286 and four companions.
- **"Passes an AI-content detector."** Five commercial detectors (OpenAI's own,
  Writer, Copyleaks, GPTZero, CrossPlag) were measured unreliable at separating
  human from machine text (https://doi.org/10.1007/s40979-023-00140-5). This one
  is worth naming precisely because `tools/slop_lint.py` looks adjacent and is
  not: it checks named rules the operator chose, it does not classify authorship.
  A move toward detector-passing as a score would be the vanity version.
- **Readability formulas as a comprehension proxy.** Directly critiqued
  (https://doi.org/10.1177/0049124113513436). Relevant to `explain-simply`,
  which currently measures against rules rather than a formula, which is the
  defensible side.
- **Checkpoint or state-file count.** LangGraph names unbounded checkpoint
  growth as a production defect, not as richer memory. Our `state/*.jsonl` are
  append-only and growing, so this reads directly on us.

## The load-bearing finding, from the security sweep

`Safety, or Just Capability? A Validity Audit of Agent-Safety Benchmarks`
(arXiv:2607.28685) re-ran four named agent-safety benchmarks (R-Judge,
InjecAgent, AgentHarm, AgentDojo) under their own official scorers across up to
22 models. Two results:

- A trivial **"always positive" policy scores F1 = 0.690 on R-Judge's binary
  trace-judgment metric, beating 5 of the 21 models that actually discriminate.**
- The three broad-coverage benchmarks **rank the same 18 models in three
  different orders.**

That is a measured demonstration that a single agent-eval score, quoted without
a trivial-baseline comparison and without cross-benchmark agreement, is a vanity
metric. It generalises past security: any score this harness ever reports about
itself should be checked against what a dumb policy would score. Our own
`tools/audit/mutate.py` is the same instinct one level down, since it exists to
prove a passing selftest can fail at all.

The rest of the security picture is real and named: AgentDojo (arXiv:2406.13352),
InjecAgent (arXiv:2403.02691), AgentHarm (arXiv:2410.09024, 110 malicious tasks
across 11 harm categories), and MSB (arXiv:2510.15994) for MCP specifically. All
need their harness stood up; none is computable from our ledgers today.

For the MCP and Tooling Office there is one defensive check worth building
locally. Tool-poisoning attacks (Invariant Labs, 2025-04-01) hide instructions in
an MCP tool's description, invisible in the client UI and fully visible to the
model; the published example reads `~/.cursor/mcp.json` and exfiltrates it
through an innocuous argument. Scanning installed connector descriptions for
that shape is computable here now. The mechanism is sourced; the check is a
proposal.

Two accuracy notes the agent flagged against itself and I am keeping: MSB's
"12 attack types" count is confirmed but the individual names are not, and
OWASP's agentic threat-category names were never read, only the landing page. A
later pass must not backfill invented names under either citation.

## The memory and corpus half of the question

The operator's framing was that personas should have skills, tools, and memory
or corpus. The sweep supports that framing and names the substrate:

- CoALA (arXiv:2309.02427) splits agent memory into semantic, episodic and
  procedural, and is the taxonomy LangGraph's own memory documentation cites.
- MemGPT (arXiv:2310.08560) is the tiered fast-and-slow paging model.
- LangGraph's two-tier split, thread-scoped checkpointer plus cross-thread store,
  is the closest thing to an off-the-shelf shape.
- Generative Agents (arXiv:2304.03442) ablated observation, reflection and
  retrieval and found each contributes independently.

Against that, our position: the registry instructs every persona to use a
best-practices corpus at three paths under `~/.claude/corpus/`, and two
independent agents confirmed this session that **the entire directory does not
exist**. The one persona with a real corpus is the Communications Desk, whose
fitted idiolect (n=35,472) lives in `~/.claude/skills/voice-metrics`, and the
external work on personalization from a user's own history (LaMP,
arXiv:2304.11406) and content-independent style embeddings
(https://doi.org/10.18653/v1/2023.findings-emnlp.1020) says that is the right
shape. It also names the trap: style scores contaminated by topic rather than
voice (https://doi.org/10.18653/v1/2022.repl4nlp-1.26).

## Where the sweep found nothing, stated rather than padded

- **Conversation Layer**: no published work treats persona toggling or chat-mode
  switching as a role with a success metric. Counting `/persona` invocations
  would be an invented metric.
- **Architecture Office**: ADR generation has an empirical literature
  (arXiv:2403.01709, arXiv:2604.03826, arXiv:2602.07609) but no operational
  architecture-health metric was found, only benchmark accuracy on a detection
  task.
- **Voice and Media Studio**: MOS and predicted-MOS are real and sourced (SOMOS,
  Interspeech 2022), but nothing was retrieved for video or visual-explainer
  quality. Frechet Video Distance was a query term, not a retrieved result, and
  must not be cited as though it were.
- **Product Studio**: no published metric measures whether generated UI is
  distinctive versus mode-collapsed. The mode-collapse result the operator
  already relies on (arXiv:2510.01171) has only two citing works in OpenAlex and
  neither concerns UI, so the transfer is an assumption rather than a finding.

## What I would do next, in cost order

M1 and M3 are both a single field away and both measure something we currently
assert without evidence. M5 is the one the external work says explains the most
variance and the one we have none of. Everything else can wait for those three.
