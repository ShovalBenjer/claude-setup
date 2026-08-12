# External repositories, read at source, against our surfaces

Date: 2026-08-06. Lane A. Claim: `EXT-REPO-DEEP-READ-2026-08-06` in `state/claims.jsonl`.

Data: the `תזכורת לעצמי` WhatsApp group (`972528034567-1603902193@g.us`, 427 messages,
2025-07-29 to 2026-08-06), re-decrypted today; `state/saved-repos-2026-07-30.json`;
115 repositories resolved against the GitHub API; 12 cloned; 10 read at source.

Durable output is `state/external-repos.jsonl`, 115 rows, one per repository, each
carrying its licence, verdict, the depth it was examined at, and the evidence for that
verdict. This document is the reasoning. The ledger is the thing that survives it.

## What is broken, and it is ours

**`dot-claude/bin/a2a-codex-call.sh` corrupts any peer response containing a Python
escape sequence.** VERIFIED, reproducible. The script builds its JSON response by
interpolating shell variables into a `python -c` source template (lines 128 to 146), so
the peer's text is parsed as a Python string literal before it becomes data:

```
$ printf 'regex \t matches; path C:\new; hex \x41\n' > c4.txt   # literal backslashes
$ cat -A c4.txt
regex \t matches; path C:\new; hex \x41$
$ ./injtest.sh c4.txt | python3 -c "import json,sys; print(repr(json.load(sys.stdin)['response_text']))"
'regex \t matches; path C:\new; hex A'
```

Four input characters `\x41` arrive as one character `A`. A Windows path, a regex
containing `\t`, or any `\x` sequence in a Codex review is silently rewritten before the
caller sees it. This fails points 1, 2 and 3 of our own `boundary-contracts.md`: no typed
DTO, a response built by string concatenation rather than from a named view type, and a
serialization step whose failure mode is corruption rather than an error. The rule has
been in force since 2026-07-01 and nothing in the 12-domain contract looks at this file.

The counterpart is `agentclientprotocol/agent-client-protocol`, Apache-2.0: 16 methods,
172 JSON-schema definitions, a versioned schema with its own CHANGELOG, and explicit
handling for cancellation, permission requests and session resume. Our bridge has none of
that and was described in the July 30 triage as having zero recorded calls.

## What the sync actually added

Four repositories, which is a smaller number than the effort suggests and is the honest
result: `reposwarm/reposwarm` (saved 2026-08-05), `island-io/mila`, plus `Sdraugel/albert`
and `covibes/zeroshot`, the last two already known but mangled by the frozen CSV.

The extraction defect the July 30 document described is now fixed at the source. That
document worked from `~/wa-export-archive/self-chat-links-2026-07-29.csv`, whose URLs were
cut mid-path, producing names that are not repositories (`covibes/zerosho`, `github/spec-k`,
`dolthub/dol`). Reading the decrypted message store directly returns the full URLs, so
`covibes/zeroshot` resolves and needs no repository search to recover.

One number moved a long way. The CSV yielded 57 repositories. The message store holds
**190 distinct `owner/repo` names across all chats**, of which 52 are in the self-notes
group and 138 were posted by other people in community groups. That second set is a
discovery pool nobody has looked at, and it is where `juliusbrussee/caveman`,
`bgauryy/octocode-mcp`, `comet-ml/opik` and `block/buzz` live.

## The licence gate, restated because it still blocks the same thing

26 of the 115 resolved repositories carry `NONE` or `NOASSERTION`. No licence means all
rights reserved, so those are read-and-describe regardless of quality, and the ledger
enforces this mechanically: any row whose licence is `NONE` or `NOASSERTION` is downgraded
to `concepts-only` even when the fit is good.

`docs/analysis/reference/coherence-governor-AGENTS.md` is still tracked, still 17,923
bytes, and `Master0fFate/just-my-skills` still resolves with `license: NONE` as of today.
This is the same blocker the July 30 document raised and it has not been decided. It is an
operator decision, not a lane decision, and it is listed again at the end.

## Surface by surface

Ten of our subsystems, each against the best external implementation that was read at
source. The delta is what we would gain, and the licence says what we may take.

### 1. Prose gate: `tools/slop_lint.py` against `petergyang/no-ai-slop` (MIT)

Ours is 114 lines of Python and it is a gate: 20 lexical regexes, one punctuation rule
(em or en dash used as a connector), and a ritual-acknowledgement detector kept
byte-identical to `dot-claude/hooks/completion_gate.py` so the file channel and the
response channel cannot correct the operator differently. It exits 1. It calls
`tools/prose_metrics.py`, 207 lines, which strips code fences, tables, links, paths, flags
and identifiers to isolate prose and then measures sentence-length variance and hyphen
rate. Those measurements are warn-only and logged to `state/prose-scores.jsonl`, with no
fitted band, deliberately.

Theirs is a 97-line `SKILL.md` plus a 44-line `eval.md` and it is not executable. What it
has that we do not is **18 named structural patterns with rewrite examples**: binary
contrasts ("not X, it's Y"), colon reveals, faux-insight setups, superficial `-ing`
analysis, interpretive metadiscourse, weasel attribution, fake-profound kickers,
summary-recap endings, negative listing, dramatic fragmentation, synonym cycling,
rhetorical setups, formatting slop.

Our own output-style file already names several of these and our gate cannot see any of
them. That is the enforcement gap ADR-0005 exists for, sitting inside the tool ADR-0005
produced. About 8 of the 18 are regex-able against our current architecture:
summary-recap openers, rhetorical setups, weasel attribution, faux-insight setups, the
trailing `-ing` clause, negative listing, colon reveals, and binary contrast.

Their second idea is `eval.md`, a checklist the model runs against its own output after
editing. That is a second oracle layer over a generated artifact, and it is the shape of
the `dod.py` that TODO says is unbuilt.

**Verdict: adopt-patterns.** MIT means the patterns can be taken, not only read.

### 2. Spec and PRD lifecycle: `tools/docmap/` against `github/spec-kit` (MIT)

`strand.py` (391 lines) checks two rules: every doc under `docs/specs/`, `docs/prd/` and
`docs/standards/` declares a status from a fixed vocabulary, and every doc is referenced by
at least one file that is not `docs/INDEX.md`. `atlas.py` adds near-duplicate detection by
Jaccard over hashed 5-word shingles. Both are real and both are running.

`strand.py` names its own gap in its own docstring, and it is worth quoting because it
predicts exactly what spec-kit supplies: "Reachability is a proxy for absorption and it is a
weak one: it catches a document nobody links, and it cannot catch a document that is linked
and ignored." On 2026-08-03 a hand pass found 7 of 37 documents in `docs/analysis/` whose
findings never reached a mechanism while most were referenced.

spec-kit's `analyze` command is a read-only cross-artifact pass with a six-way detection
taxonomy (duplication, ambiguity, underspecification, constitution alignment, coverage
gaps, inconsistency), a four-level severity heuristic where a constitution `MUST` violation
is automatically CRITICAL, and a coverage table that reports the percentage of requirements
with at least one associated task. It builds a requirements inventory keyed on stable
`FR-###` / `SC-###` identifiers and maps tasks onto it.

Coverage percentage between requirements and tasks is the measurement we do not have. Our
`TODO.md` carries 166 rows and `docs/prd/2026-08-03-unified-architecture.md` plus
`docs/specs/2026-08-03-detail-passes-teleology-and-creativity.md` carry 48 definition-of-done
rows, and no tool relates the two sets. TODO already records this and already records the
right caution: classify the 48 first, because some are prose and the count of mechanically
checkable rows is below 48 and unknown.

**Verdict: concepts-only in practice.** The licence permits copying, but the CLI assumes
spec-kit's own directory layout and the transferable part is the taxonomy.

### 3. Inter-agent channel: `dot-claude/bin/a2a-*` against ACP (Apache-2.0)

Covered above. **Verdict: adopt-candidate**, and the first move is smaller than adopting
the protocol: make the bridge build its response with `json.dumps` from a dict instead of
interpolating into Python source. That is a 5-line change that removes a measured
corruption path, and it does not require deciding about ACP at all.

`aaif-goose/goose` (Apache-2.0) is a native ACP server, so it tests the protocol without
writing an adapter first. Cloned, not source-read.

### 4. Review fabric: `tools/review/panel.py` against `alibaba/open-code-review` (Apache-2.0)

The July 30 document ranked this repository for reading on the grounds that our `review`
domain is on its third waiver for the same false-positive class. Reading both, the overlap
is larger than that framing suggests, and two things it implied are wrong.

`panel.py` (1,386 lines) already does the structural fix. `validate_findings` keeps only
findings citing a line the change actually added, counts the drops, and `build_note` ships
the count in the artifact, with the stated reason that "a reviewer that quietly discards
half its own output while reporting the rest as clean is worse than one that reports
nothing". `emit_github_annotations` is not dead code: it is called at `panel.py:956`, again
from `tools/review/gemini_diff_review.py:199`, and pinned by `tests/test_panel_annotations.py`.
So the July 30 suggestion that `reviewdog` is the missing path from `state/reviews/<sha>.json`
to PR comments is stale. That path exists.

Three real deltas remain:

- **Whole-file scan.** `panel.py` reviews added diff lines and never holds the whole file,
  and its own comment says a construct spanning lines can be missed and that closing it
  "needs file-level parsing". `internal/scan/` is that mode, with batching by language or
  first-level directory and a token-budget estimator.
- **Typed finding DTO.** `LlmComment` carries `category` from an 8-value enum and
  `severity` from a 4-value enum, plus `existing_code` and `suggestion_code`, which makes a
  finding machine-appliable. Ours carries a 3-value severity and free-text `why`.
- **`ASSURANCE_CASE.md`.** A per-tool threat model: 4 trust boundaries, 7 numbered threats,
  each with its mitigation. T6 is "malicious LLM response", mitigated by schema validation
  plus line-number bounds checking. We have `boundary-contracts.md` as a global rule and no
  per-tool assurance artifact anywhere in the repo.

**Verdict: concepts-only.**

### 5. Install and skills drift: `tools/audit/skills_sync.py` against `affaan-m/ECC` (MIT)

Two open TODO rows describe the same wound: `skills_sync.py check` exits 0 while reporting
drift, and three skill trees hold 45 forks whose divergence has no recorded decision.
`state/deploy-manifest.tsv` exists and is 84 rows of `sha256 <tab> relative-path`. It
records what the bytes were. It does not record what was requested, how the request
resolved, which source it came from, what operations ran, or when the installation was last
validated, and it was last written 2026-07-31.

ECC carries 11 JSON schemas governing installation. Two matter here. `install-state.v1`
requires `schemaVersion`, `installedAt`, `target`, `request`, `resolution`, `source` and
`operations`, with an optional `lastValidatedAt`, where `request` itself records the
profile, the modules, and the explicit include and exclude lists. `provenance.schema.json`
requires `source`, `created_at`, `confidence` and `author` on every learned or imported
skill.

Provenance is the direct answer to the 45 forks. A fork with a recorded source and author is
a merge decision with evidence under it. Picking by timestamp, which TODO explicitly rejects,
is what happens when that field does not exist.

**Verdict: adopt-patterns.**

### 6. Cross-repo architecture: `tools/map/codemap.py` against `reposwarm/reposwarm` (Apache-2.0)

`codemap.py` is 520 lines and works at directory granularity for one repository: it resolves
each tracked directory's purpose from its own `SKILL.md`, `README.md` or the
`docs/dir-purpose.txt` registry, renders `docs/CODEBASE-MAP.md`, and audits prior-art records
for components over 300 lines. It is a purpose map, not a symbol graph, and it stops at the
repository boundary.

RepoSwarm generates one standardized `.arch.md` per repository into a central results hub,
re-analyzes only repositories whose HEAD moved, and selects the analysis prompt by detected
repository type using a declarative pattern file (`prompts/prompt_selector.json` matches on
file globs, directory names and keywords).

We run three repositories in three lanes with no shared architectural view of any kind, and
`docs/specs/2026-07-31-project-federation.md` is the spec that wants one. The incremental
rule (regenerate only when HEAD moved) is the part that makes it affordable.

**Verdict: adopt-patterns.**

### 7. Design and anti-convergence: `rules/out-of-distribution.md` against `pbakaus/impeccable` (Apache-2.0)

Our rule bans named modes in prose: "system-font and Inter/Roboto stacks, purple gradients
on dark, the cream-and-serif house style, cookie-cutter component layouts", and says the
frontend-design and dataviz skills carry the current avoid-lists. Those lists are prose. No
tool under `tools/` checks any of them.

Impeccable ships **59 deterministic detector rules that run with no LLM and no API key**.
Eleven of them are our ban list by name: `overused-font`, `ai-color-palette`, `cream-palette`,
`nested-cards`, `icon-tile-stack`, `dark-glow`, `gradient-text`, `radial-halo`,
`kicker-above-heading`, `hero-eyebrow-chip`, `monotonous-spacing`. Two are model-specific
tells we have never named: `gpt-thin-border-wide-shadow` and `codex-grid-background`. Three
are prose rules living inside a design linter: `em-dash-overuse`, `aphoristic-cadence`,
`theater-slop-phrase`.

The lane C evidence makes this concrete rather than theoretical. `daily-deep-learning` has
already built one rule of this class: `tools/contrast_pass.py` computes WCAG contrast over
declared token pairs from `style.css` with no browser, written precisely because the
`a11y_ux` domain needs a Chrome CDP endpoint and otherwise sits behind a waiver. Lane C
built one browser-free design check. Impeccable has 59.

**Verdict: adopt-patterns**, and the landing zone is lane C, not lane A.

### 8. Self-improvement: `tools/selfimprove/scan.py` against `facebookresearch/HyperAgents`

`scan.py` is 179 lines. `scan()` emits proposals with title, why, risk, auto, evidence and
kind. It ranks. There is no evaluation, no archive of scores, and no selection step, so
nothing closes the loop from a proposal to a measured outcome to the next proposal.

HyperAgents is the closed version: `meta_agent.py` modifies the codebase, `generate_loop.py`
runs generations, and `select_next_parent.py` picks the next parent by averaging per-domain
scores, gating on a `valid_parent` flag, tracking child counts, and then **selecting at
random among candidates to keep the search space open** rather than hill-climbing on the
best score. That last choice is an explicit anti-convergence policy and it rhymes with our
`/diverge` rule, which currently governs human design decisions and not the improvement loop.

**Verdict: concepts-only, and hard.** The licence is CC BY-NC-SA 4.0, which is
noncommercial and share-alike. Read and describe. Do not copy, and do not vendor. Same
treatment as `Sdraugel/albert` under PolyForm Noncommercial.

### 9. Memory: `docs/adr/0010-sessions-are-ephemeral-disk-is-memory.md` against `MemPalace/mempalace` (MIT)

MemPalace stores conversation history verbatim, refuses to summarize or paraphrase, and
retrieves by semantic search over a pluggable backend with a structured index. Read at README
and module-listing depth only this session, so this row is `read-further` and not a
recommendation. It bears on ADR-0010 and on the open OKF question.

**Verdict: read-further.** Named here so the ledger records that the reading was not done.

`colbymchenry/codegraph` (MIT, Rust kernel, semantic code graph synced on change) is in the
same position: it is the symbol-level counterpart to `codemap.py`'s directory-level view, and
it was not source-read.

### 10. Model routing: `rules/model-selection.md` against `musistudio/claude-code-router` (MIT)

CCR routes one control plane across many providers with failover, presets and a usage
dashboard, at 36,444 stars.

**Verdict: leave.** ADR-0002 chose subscription OAuth over metered API, and
`model-selection.md` states the standing constraint directly: keep first-party Claude.ai
OAuth routing, and do not introduce gateways or free proxies unless the operator explicitly
requests a controlled experiment. A recorded decision outranks a star count. This row exists
to show the comparison can reject as well as adopt.

## Corrections to the 2026-07-30 triage

- Item 5 of its reading list proposed `reviewdog` as the missing path from the review
  artifact to PR comments. That path exists: `emit_github_annotations`, called from two
  places and covered by a test.
- Its ranked item 4 implied our review domain lacks location verification. `validate_findings`
  has it, with drop counting.
- `covibes/zerosho` "did not resolve at all". It is `covibes/zeroshot` and the truncation was
  in the CSV, not in the save.
- Its corpus was 57 repositories from one exported file. The store holds 190 across all
  chats, 52 in the self-notes group.

## Coverage boundary

Stated plainly, because a document that does not say what it skipped reads as complete.

- **10 repositories read at source. 2 cloned and not read** (`goose`, and `mempalace` beyond
  its module listing). **103 of 115 rows in the ledger are metadata-only** and carry
  `verdict: untriaged`. That is not a backlog that got smaller; it is the same backlog with
  10 rows taken off it.
- **Lane A is the only lane analysed in depth.** Lane B (`new-recruit`) and lane C
  (`daily-deep-learning`) were checked for the specific surfaces named above and nothing
  more: both declare a 10-domain `quality-contract.json`, both have `state/reviews/`, lane B
  has no `gate-runs` ledger, lane C has `tools/contrast_pass.py` and `tools/check_inline_js.py`.
  No lane B or C document was read. The proposals below are scoped to that evidence.
- **The 138 community-shared repositories were resolved and not evaluated.** They are in the
  ledger with `source: community` so a later pass has a starting list.
- Repository names and licences are public facts. The ledger deliberately carries no chat
  identifiers, no timestamps tied to a named group, and no message text.

## Open operator decisions

1. **`coherence-governor-AGENTS.md`.** 17,923 bytes of an all-rights-reserved document,
   tracked in git, upstream still `license: NONE` today. Replace with a summary and a link,
   ask the author for a licence, or accept that this repository cannot go public. Raised
   2026-07-30, still open.
2. **The community pool.** 138 repositories from other people's group messages. Worth a
   triage pass, or deliberately out of scope. Currently neither.
