# Memory and retrieval substrate: what exists, what contradicts, what the field did

Date: 2026-08-06. Status: point-in-time findings. Lane A. Nothing here is built.

Written because ADR-0010 says nothing load-bearing lives only in a conversation. Every
number below was measured on this machine on this date, or carries its source.

## 0. The question that started it

The operator asked whether SAELens could run against Claude over the session corpus,
self-hosted on NVIDIA or AWS. It cannot: SAELens hooks a PyTorch forward pass to read
residual-stream activations, and no Anthropic endpoint emits an activation tensor.

That answer was already on disk. `tools/nvidia/nim.py` recorded it on 2026-07-29:
"these endpoints are HOSTED INFERENCE ONLY. No weights, no activations, no internals."
It was re-derived from the web before the repo was read, which is the wrong order and is
the most reusable lesson in this document.

ADR-0018 reached the same wall independently on 2026-07-30 for inter-agent messages: the
white-box KV-cache channel (Cache-to-Cache 2510.03215 and its 2026 successors) "requires
both sides' caches, hence open weights and a projector." The black-box dense-text channel
(arXiv 2606.19857) needs none, and buys 38.96% to 44.21% token reduction at 96.6% to
99.7% of task score. Anything latent needs open weights. That is one constraint, found
twice, and it should stop being rediscovered.

## 1. The corpus, measured

| Measure | Value |
|---|---|
| md files, claude-setup + new-recruit | 10,644 |
| unique by content sha256 | 3,609 |
| duplicate files | 7,035, **66.1%** |
| bytes total | 105.4 MB, ~26,361,369 tokens |
| bytes unique | 37.7 MB, ~9,417,817 tokens |
| full-corpus ripgrep | **35 to 94 ms** |

Worst duplication: one 262-byte file in 24 identical copies, a 26 KB research paper in
20. Most of the excess is `archive/bundles/` in new-recruit holding whole snapshots of
claude-setup. Any indexing design that skips deduplication pays 3x for nothing.

The 2026-07-30 data-architecture spec states "this is not big data" and it is right about
the ledgers it measured (twelve `state/*.jsonl` under 4 MB). It classified `docs/**/*.md`
as prose-in-git and never counted it. The two statements are not in conflict, but quoting
the first against the md corpus is an error, and it was made in this session.

Session transcripts are a separate and much smaller corpus: 175 operator turns, 84,838
chars, ~21k tokens, median turn 125 characters. `tools/corpus/extract.py` produces it.

## 2. Two specs that contradict each other

**`docs/gemini-code-1785457549011.md`**, 230 lines, listed in `docs/INDEX.md:171` as
"status not declared". A Gemini-generated implementation prompt titled "BUILD A NEXT-GEN
HYBRID RAG ENGINE (PAGEINDEX + LIGHTRAG + SPECULATIVE ROUTING)". Three layers: PageIndex
intra-document tree, LightRAG/LazyGraphRAG dual-level graph on NetworkX or Neo4j, agentic
router with a speculative verifier. Storage: LanceDB or Qdrant, ColBERTv2/PLAID.

**`intent-control-plane/docs/specs/2026-07-11-self-evolving-depth-harness.md`**, AC-K3:
"Stays agentic-JIT + sqlite-first; no vector-DB-first rewrite, no LangGraph-for-knowledge,
no GraphRAG. Dense embeddings remain a deferred, conditional Stage-2 secondary index."
Its non-goals name "Vector-DB-first retrieval; LangGraph adoption for knowledge;
MS-GraphRAG."

One says build LightRAG. One makes it a non-goal. The contradiction has been in the repo
since 2026-07-11 and neither document references the other.

## 3. The field moved toward the rejection, not away from it

| Finding | Source |
|---|---|
| Claude Code dropped vector RAG for glob+grep+read; reported to beat vector RAG "by a lot" | vendor statement, not independently verified |
| "Is Grep All You Need? How Agent Harnesses Reshape Agentic Search" | arXiv 2605.15184 |
| Direct Corpus Interaction: a fixed similarity interface is the bottleneck for exact lexical constraints, sparse clue combination, local context checks, multi-step refinement | arXiv 2605.05242, Dr-DCI 2606.14885 |
| 72% to 80% of enterprise RAG never reaches production; extraction pipelines hallucinate entities into brittle graphs needing manual correction | GraphRAG 2026 buyer's guide (vendor blog) |
| LightRAG graph construction cost **83,909,073 tokens** in one benchmark; GraphRAG 79.9M | GraphRAG-Bench, arXiv 2506.02404 |

The last row decides it at this corpus size. Deduplicated, the corpus is ~9.4M tokens.
LightRAG-style construction is roughly 9x that in LLM calls, because entity extraction is
a call per chunk, and it re-runs as documents change. The 2026-07-11 spec rejected
GraphRAG a month before the literature converged on the same answer.

## 4. Not reindexing: delta is the answer and the ratio is large

| Finding | Source |
|---|---|
| For a corpus where 1% of documents change daily, delta beats nightly full reindex by ~100x on embedding cost | kapa.ai, Real-Time Data Evolution (vendor blogs) |
| "Most RAG systems re-index nightly. In 2026 that is a design failure." | same |
| Single document update 2 to 5 min; batches of 50 to 100 under 10 min | particula.tech (vendor blog) |
| Semantic Pyramid Indexing: embeddings at semantically aligned resolution levels, retrieval depth chosen per query by an uncertainty-aware controller | arXiv 2511.16681 |

Evidence class is weaker here than in section 3: mostly vendor blogs plus two preprints.
No SIGIR or TOIS paper was found. Delta indexing keys on a content hash, which section 1
already computes, and 66% of the corpus is a hash collision with something already seen.

## 5. Postgres reopens an ADR-0011 rejection on capability grounds

`pg_textsearch` (Tiger Data) brings production BM25 into Postgres, open-sourced early
2026, reported v1.3.0 by mid-2026. Combined with pgvector and RRF this puts lexical,
semantic and (per a search snippet about Postgres 19, UNVERIFIED) graph queries in one
engine, which is the three-layer shape the LightRAG document assembles from three
components.

ADR-0011 rejected Postgres on operational grounds, not capability: "Rejected: per-tool
DBs (sprawl), Postgres (ops burden for one operator), everything-as-jsonl." The
2026-07-30 spec reinforces it with "no server processes without an owner." None of the
2026 capability news touches the ops argument. SQLite still has no daemon. Recorded as a
reopening argument, not a decision.

## 6. The db is empty and there are two capture paths, not zero

`state/ecosystem.db` does not exist and zero `.py` reference it. ADR-0011 was accepted
2026-07-24; spec §P1 names seven tables (`sessions`, `proposals`, `runs`, `lessons`,
`reputation`, `post_queue`, `repo_registry`) and **no embedding or vector table**.

`intent_control_plane/memory.py` has `MemoryStore` (four typed kinds, jsonl, tf-idf cosine
recall) and an `EmbeddingBackend` Protocol that is a deliberate empty seam: "Not
implemented here on purpose: no real model ships in this zero-dependency repo." It has
zero callers outside its own tests, and `~/.intent/memory/records.jsonl` has never been
written.

`docs/specs/2026-07-29-prompt-to-ticket-lifecycle.md`, 824 lines, status active, is the
prompt-to-request design: `PT-` ids from `sha256({session, text_sha, occ})[:12]` (587
minted, 587 unique, 0 collisions on the real corpus), a twelve-state lifecycle, and
evidence-guarded transitions where `CLOSED_VERIFIED` needs an evidence row newer than the
last `IN_PROGRESS` plus a matching PASS in `state/gate-runs.jsonl`.

Its four diagnosed breaks, re-measured on WSL 2026-08-06:

| Break | Windows, 2026-07-29 | WSL, today |
|---|---|---|
| `~/.intent` missing | broken | still missing |
| `intent-capture.sh` is a text file holding a path | broken | still broken, 45 bytes reading `/home/shovalbe/.codex/hooks/intent-capture.sh` |
| no `UserPromptSubmit` event | broken | FIXED, three hooks registered |
| `python3` does not resolve | broken | FIXED, `/usr/bin/python3` |

The registered hooks are **not** the spec's: `tools/intent/capture_turn.py`,
`tools/bus/bus.py inbox`, `tools/intent/route.py`. `state/prompt-tickets.jsonl` is live
(last row `2026-08-06T14:47:19Z PT-b140c7354f86 CAPTURED`) and stores `text_sha` with no
text, by design.

So there are two implementations of prompt capture, one specced and unbuilt, one built and
unspecced, and neither writes `ecosystem.db`. That reconciliation is the open question,
and it is prior to any retrieval decision.

## 7. What would falsify the recommendation

The recommendation implied by sections 1, 3 and 4 is: deduplicate first, keep direct
corpus interaction as the primary path, add structure (the PageIndex half) before any
embedding, and treat dense embeddings as the Stage-2 secondary index the 2026-07-11 spec
already scheduled.

It fails if any of these hold:

- Grep latency stops being milliseconds as the corpus grows. Re-measure; the numbers in
  section 1 are for 105 MB unindexed.
- A real query arrives that is semantic with no shared vocabulary, and grep provably
  cannot serve it. No such query has been recorded. This is the strongest missing
  evidence in this document.
- The 3,609 unique files turn out to be mostly third-party skill payloads rather than the
  operator's own material, in which case the corpus worth indexing is smaller again and
  was never measured separately.

## 8. Unverified

- The YouTube video that prompted section 5 was never read. `youtube-distill` needs a
  browser; none was reachable (no CDP on 9222/9223/9224 locally or on the Windows host).
  Only oEmbed metadata was retrieved: "This New Postgres Feature Is Crazy Powerful",
  Better Stack. The "Postgres 19 native graph queries" claim is a search snippet.
- Postgres 19 release notes were not opened.
- `tools/intent/capture_turn.py` and `tools/intent/route.py` were not read, so whether the
  live path duplicates or contradicts the spec is unknown.
- No external RAG tool was installed or run.
