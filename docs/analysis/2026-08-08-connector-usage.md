# Connector usage, measured over 1183 transcripts

Point-in-time scan, 2026-08-08, lane A. Produced by counting assistant `tool_use`
blocks in every transcript under `~/.claude/projects`, after the session-store
migration of the same day made the pre-2026-07-31 history reachable at all.

## The measurement that matters, and the one that lies

A grep for `mcp__` returns 140,614 hits. That number is close to meaningless: the
tool list is injected into every system prompt, so a connector counts once per
turn merely for being switched on. Ranked that way, Scite leads with 25,041 and
Semrush is third with 14,266.

Counting only assistant `tool_use` blocks, which is an invocation the model
actually made:

| server | real calls | sessions | `mcp__` mentions |
| --- | ---: | ---: | ---: |
| claude-in-chrome (local) | 147 | 10 | not applicable |
| alphaXiv | 96 | 31 | 11,374 |
| PubMed | 28 | 2 | 7,761 |
| Scholar Gateway | 11 | 8 | 1,032 |
| Scite | 8 | 4 | 25,041 |
| Consensus | 7 | 4 | 1,048 |
| Microsoft Learn | 6 | 5 | 3,076 |
| bioRxiv | 4 | 1 | 7,653 |
| sadna (local) | 4 | 2 | not applicable |
| Exa | 3 | 2 | 581 |
| Context7 | 2 | 1 | 348 |
| Anthropic Economic Index | 1 | 1 | 19,054 |

Scite: 25,041 mentions, 8 calls. Anthropic Economic Index: 19,054 mentions, 1
call. This is a size comparison read as a usage comparison, the same shape as
`L-2026-08-07-b`, and it is the reason this file leads with the method.

## Never called, across 1183 sessions

Semrush, SNOMED CT Terminology, ICD-10 Codes, Clinical Trials, Gmail, Medidata,
Mobbin, Indeed, Zapier.

Two different reasons, and they need different answers. Semrush, SNOMED, ICD-10,
Clinical Trials, Medidata and Mobbin are domain connectors for domains this
operator's work does not touch: clinical coding, pharmacovigilance, SEO, and UI
reference galleries. They are not underused, they are misfitted, and the answer
is to scope them off rather than to find a use. Gmail, Indeed and Zapier are a
different case: each needs an authorisation step and a reason, and neither has
been supplied, so a zero says nothing about whether they would be useful.

## How they load, which was the operator's first question

Efficiently, and the mechanism is already right. Connector tools are deferred:
only their names sit in context, and a schema is fetched on demand through
`ToolSearch`. Roughly 100 tool names across 12 servers cost their names in every
system prompt and nothing more until called.

Per-project relevance, however, was almost entirely unused. `~/.claude.json`
carries a `disabledMcpServers` list per project and only one project had a
non-empty one: claude-setup, with three entries.

## What was wired, and what deliberately was not

`disabledMcpServers` for `/home/shov/work/repos/claude-setup` moved from 3 to 10:
added Clinical Trials, PubMed, bioRxiv, Scite, Semrush, Mobbin and Anthropic
Economic Index, beside the SNOMED CT, ICD-10 and Consensus already there.

Left on for this repo, because a disable list is only honest beside its keep
list: Context7 for library documentation, Exa for search and fetch, Microsoft
Learn for Azure, and alphaXiv plus Scholar Gateway because this repository holds
`research-papers/` and prior-art records that cite literature. Exa earns its
place on the day's evidence rather than on principle: `WebSearch` and `WebFetch`
were unavailable to two subagents this session and the work was completed
through other fetch paths.

`new-recruit` and `daily-deep-learning` were NOT touched. A connector list is a
working-environment decision for whoever works in that repository, and the
charter makes a cross-lane need a proposal rather than an edit. The proposal, for
whoever owns those lanes: new-recruit is the one project where Indeed is
plausibly on-topic, and it currently has an empty disable list, so it inherits
every medical connector for no reason.

## Not established here

Whether any of the ~850 connectors in the directory would help. That question
needs the directory itself, which this scan did not read, and the honest state is
that nine already-connected connectors have never been called once. Adding before
pruning would make the list longer and the hit rate worse.
