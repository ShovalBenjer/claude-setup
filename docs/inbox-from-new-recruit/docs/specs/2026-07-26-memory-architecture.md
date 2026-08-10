# Memory Architecture for a Single-Operator Self-Evolving Agent System

## 0. Evidence boundary

Verified by me, this session:

- **arXiv 2603.13017** fetched in full (1,457 lines, Sydney Lewis, March 2026, "Structured Distillation for Personalized Agent Memory: 11× Token Reduction with Retrieval Preservation"). Every claim in the brief checks out, with two corrections noted in section 1.
- **Local environment**: `sentence_transformers`, `faiss`, `sqlite_vec`, `sklearn`, `tiktoken`, `rank_bm25` are **all absent**. `numpy` and `duckdb` present. SQLite 3.45.1 with `ENABLE_FTS5` compiled in. No `bd` and no `dolt` binary on PATH.
- **Existing substrate** at `C:\Users\shova\claude-setup\state\`: `bus.jsonl` (13 rows, hash-chained), `bus-cursors/` (exactly one cursor, `B.txt`), `claims-verify.jsonl` (26), `refutations.jsonl` (287), `lessons.jsonl` (18), `gate-runs.jsonl` (355), `compact-log.md` (127 KB), `reviews/` (4), plus `C:\Users\shova\Downloads\new-recruit\state\reviews\` (2).
- **Hooks actually wired** in `~/.claude/settings.json`: SessionStart to `session-recall.sh`, PreCompact to `precompact-handoff.sh`, Stop to `completion_gate.py` + `ship_gate_stop.py`, PreToolUse Bash x2, Notification.
- **Corpus scale**: 47 top-level transcripts across 4 project dirs, 39,910 rows, 7,378 user turns, 12,901 assistant turns, 7.34 M chars (~1.84 M tokens). `~/.claude/history.jsonl` 563 lines.
- **`hiring_engine/ledger.sqlite`**: jobs 234, variants 4, approvals 11, applications 4, outcomes 8, runs 55, costs 3, contacts 1, mail_events 1.
- **`tools/dolt/client.py`** already exists (38 KB) and documents the DoltHub free-tier public-only constraint in its own header.
- **`gh api`** (read-only): `gastownhall/beads` Go, MIT, 25,671 stars, pushed 2026-07-26, not archived. `dolthub/dolt` Apache-2.0, 23,988 stars.

Flagged as **INFERENCE** throughout with that tag. I did not install, run, or trial beads or Dolt.

---

## 1. The finding that reorders the whole design

The prior-art brief says "VECTOR search survives distillation but BM25 does NOT." That is correct and it is verified (paper lines 21-23: all 20 vector configs non-significant after Bonferroni, all 20 BM25 configs significantly degraded, |d| = 0.031 to 0.756).

**The consequence has been missed.** This machine has no vector stack and cannot get one without a `pip install`, which is a per-action-approval operation. So the obvious build (distill everything, then FTS5 over the distilled text) lands precisely in the one cell the paper measured as significantly degraded. Distillation would make search *worse* than doing nothing.

The paper also reports the numbers that resolve this (lines 401, 417-418):

| Configuration | MRR |
|---|---|
| Full Text / BM25-FTS (best pure verbatim) | **0.745** |
| Full Text / BM25-Okapi | 0.719 |
| Distill Core+Rooms / Exact / Weighted (best pure distilled) | 0.717 |
| Full Text / HNSW | 0.645 |
| Full Text / Exact | 0.638 |
| Cross: BM25(V) + HNSW(D) / CombMNZ (best overall) | **0.759** |

Read the first and fourth rows together. **BM25-FTS over verbatim text beats vector search over verbatim text by 0.100 MRR.** The paper states it directly (line 419): "Mechanism choice matters more than distillation mode."

So the correct increment ordering is the inverse of what "distillation preserves retrieval" suggests on first read:

1. **Day 1**: FTS5 (BM25) over **verbatim** text. Zero new dependencies. Lands on 0.745, the best pure verbatim number in the paper.
2. **Later, when an embedding path is approved**: add HNSW over **distilled** text as a second signal and fuse. Lands on 0.759, the best overall number.

Nothing built in step 1 is discarded in step 2, because the paper's own best configuration *requires both layers* and maintains them as separate indices anyway (lines 187-189: separate indices are kept because of a density mismatch, ~1,500 chars verbatim versus ~200 chars distilled).

Two corrections to the brief, both minor and both worth carrying:

- **11× is a corpus-total ratio, not a per-item one.** Paper line 253: "per-item average ratio is 9.9×." The 11× arises because 12,427 distilled objects come from 14,340 exchanges (the 100-character trivia filter removes more than ply-splitting adds). Cite 9.9× per item.
- **"Two-tier index-vs-display" is stronger than a storage split.** Paper lines 139-142: "The distilled text is **never shown to the user**. It serves as a retrieval routing artifact: all search modes return the original verbatim conversation text." Distillation decides *rank order only*. The operator always reads unmodified original text. This is directly downstream of the never-delete rule and should be treated as non-negotiable.

---

## 2. Adopt Beads, or build?

**Split the answer by layer. The two things are not the same problem, and collapsing them is the error to avoid.**

### Work graph: adopt beads, but not on day 1

The case is real and the brief has it right. Commit `73cda2e` ("resolve a blocked phase by insertion order, not a tied timestamp") is a hand-rolled `bd ready` with a dependency-ordering tiebreak. That is duplicated upstream work.

But three verified facts push adoption to week 2, not day 1:

1. **`bd` is not installed.** Installing it is a third-party install requiring explicit per-action approval. It cannot be the one-day increment by construction.
2. **`bd dolt push` is blocked for anything touching this corpus.** The operator's own `tools/dolt/client.py` header documents the constraint from DoltHub's pages: free accounts host public databases only. The standing rule is explicit that no transcripts, employer material, resume content, or customer data may go there until a Pro account is confirmed. Beads' git-remote sync (`refs/dolt/data`) is therefore usable only for a work graph scrubbed of candidate data, never for the memory layer. Embedded local mode is fine.
3. **The multi-writer problem does not exist yet.** `state/bus-cursors/` contains exactly one file, `B.txt`. Cell-level merge solves contention between concurrent writers. There is currently one. Paying schema-migration cost for a property with no present demand is the premature move.

### Conversational memory: build

`bd remember` / `bd prime` is a project-note store. It is not a distilled retrieval layer over 39,910 transcript rows, and no amount of `bd remember` produces MRR 0.745 over that corpus. Beads is the right answer to "where does the work graph live" and the wrong answer to "how do I find the thing I said in May."

**Retire `MEMORY.md` into beads only after beads is trialed.** Right now `~/.claude/projects/<slug>/memory/MEMORY.md` plus its 5 satellite files are working and readable, and replacing a working thing with an uninstalled thing is the small-patch-reported-as-done pattern.

### Dolt directly: no

The engine is right and the level is wrong. In embedded mode `bd` already contains Dolt in-process. Taking a direct Dolt dependency means owning schema, IDs, merge policy, sync, and migrations, which is the from-scratch build the beads assessment correctly rejects. Keep `tools/dolt/client.py` as the remote-interchange escape hatch it already is.

---

## 3. Storage engine: SQLite, with the index treated as rebuildable

**Choice: a single SQLite file at `~/claude-setup/state/memory.db`, with FTS5.**

Justification against the alternatives, on this machine's measured constraints:

| Option | Verdict | Reason |
|---|---|---|
| **Append-only JSONL** (status quo) | insufficient alone | Works for 18-row `lessons.jsonl` and 26-row `claims-verify.jsonl`, where append-and-scan is the whole access pattern. Fails at ~5,000 exchange objects: no index, and grep does not produce ranked retrieval. |
| **Dolt direct** | premature | Cell-level merge solves multi-writer contention. One cursor file exists. Adds a binary, a schema, and a migration surface for a property with no current demand. |
| **Vector DB (Chroma/LanceDB/FAISS)** | blocked | Requires `pip install`, which needs per-action approval. `faiss`, `sentence_transformers`, `sqlite_vec` all verified absent. |
| **SQLite + FTS5** | **adopt** | Python stdlib, zero install, FTS5 verified compiled in at 3.45.1. Already the in-repo pattern (`hiring_engine/ledger.sqlite`, 9 tables, populated). BM25 ranking is built into FTS5, which is the exact mechanism that scores 0.745. |

**The architectural move that removes the need for a versioned database:** the DB is a *derived index*, not a source of truth. Raw transcripts already exist on disk under `~/.claude/projects/`, are never deleted per standing rule, and the distiller is git-tracked code. Therefore `memory.db` is reproducible from git-tracked material plus an immutable corpus. Add `state/memory.db` to `.gitignore` and add `tools/memory/rebuild.py`. "What did this table say on the 25th" becomes "check out the distiller at that SHA and re-derive," which is a weaker guarantee than Dolt but costs nothing and is sufficient for a derived artifact.

**INFERENCE**: I did not benchmark FTS5 on this corpus. The 0.745 figure is the paper's, on the paper's corpus, and my claim is that the mechanism transfers, not that the number does.

---

## 4. Schema

```sql
-- ~/claude-setup/state/memory.db
PRAGMA journal_mode = WAL;   -- Stop hook and drainer write concurrently

-- Tier 1: raw pointer. Never mutated, never deleted. The never-delete rule
-- lives here structurally: this table has no DELETE path in any tool.
CREATE TABLE exchange (
  id            TEXT PRIMARY KEY,   -- sha256(project||conv_id||ply_start)[:16]
  project_id    TEXT NOT NULL,      -- 'new-recruit' | 'claude-setup' | ...
  lane          TEXT,               -- A|B|C|D, operator's session lanes
  conv_id       TEXT NOT NULL,      -- transcript uuid (the .jsonl basename)
  ply_start     INTEGER NOT NULL,
  ply_end       INTEGER NOT NULL,
  ts            TEXT NOT NULL,      -- ISO8601 of first ply
  verbatim      TEXT NOT NULL,      -- full exchange text, PII-scrubbed, never truncated
  n_chars       INTEGER NOT NULL,
  source_path   TEXT NOT NULL       -- absolute path to the .jsonl, for drill-down
);

-- Tier 2: distilled object. Paper section 3.2, four fields.
-- Regenerable: dropping and rebuilding this table loses nothing.
CREATE TABLE distilled (
  exchange_id      TEXT PRIMARY KEY REFERENCES exchange(id),
  exchange_core    TEXT NOT NULL,   -- LLM: 1-2 sentences, what was accomplished
  specific_context TEXT NOT NULL,   -- LLM: one concrete detail copied exactly
  files_touched    TEXT NOT NULL,   -- JSON array, REGEX-extracted, not LLM
  distiller        TEXT NOT NULL,   -- 'haiku-4.5' etc, so a model swap is auditable
  distilled_at     TEXT NOT NULL,
  register         TEXT NOT NULL    -- 'ASSUMED' for LLM fields (see section 8)
);

-- room_assignments normalized out: it is 1-to-many and is the decay handle.
CREATE TABLE room (
  exchange_id TEXT NOT NULL REFERENCES exchange(id),
  room_type   TEXT NOT NULL CHECK (room_type IN ('file','concept','workflow')),
  room_key    TEXT NOT NULL,        -- 'retry_timeout', not 'errors'
  room_label  TEXT NOT NULL,
  relevance   REAL NOT NULL,        -- 0.0-1.0, LLM-assigned
  PRIMARY KEY (exchange_id, room_key)
);

-- Tier 3: standing rules and lessons. Distinct from exchanges: these are
-- ASSERTIONS, not history, and they carry an enforcement pointer.
CREATE TABLE rule (
  id           TEXT PRIMARY KEY,      -- 'R-041'
  rule         TEXT NOT NULL,
  strength     TEXT NOT NULL CHECK (strength IN
                 ('stated-once','repeated','emphatic-correction')),
  first_seen   TEXT NOT NULL,
  last_seen    TEXT NOT NULL,         -- refreshed on every restatement
  n_restated   INTEGER NOT NULL DEFAULT 1,
  evidence_ids TEXT NOT NULL,         -- JSON array of exchange.id
  enforcement  TEXT,                  -- path to hook/check, NULL = prose only
  tier         TEXT NOT NULL DEFAULT 'warm'
                 CHECK (tier IN ('hot','warm','cold')),
  superseded_by TEXT REFERENCES rule(id),   -- decay by supersession, never DELETE
  scope        TEXT NOT NULL DEFAULT 'global'  -- 'global' | lane | project
);

-- Search index: VERBATIM, per section 1. This is the day-1 retrieval surface.
CREATE VIRTUAL TABLE exchange_fts USING fts5(
  verbatim,
  content='exchange', content_rowid='rowid',
  tokenize='porter unicode61'
);

-- Built but NOT queried on day 1. Present so the distiller has a target and
-- so cross-layer fusion is a config change later, not a migration.
CREATE VIRTUAL TABLE distilled_fts USING fts5(
  distill_text,                      -- exchange_core || char(10) || specific_context
  content='', tokenize='porter unicode61'
);
```

Two schema decisions that depart from the paper, deliberately:

- **`verbatim` is stored in-row, not just pointed at.** The paper keeps back-references (`conversation_id`, `ply_start`, `ply_end`) and re-reads the source. Storing it costs ~7.3 MB for this corpus, which is nothing, and it makes the DB survive a transcript path change. FTS5 `content='exchange'` external-content mode means the text is not duplicated in the index.
- **`register` column on `distilled`.** The paper has no equivalent. It exists because this operator's standing discipline is VERIFIED / STAGED / ASSUMED. LLM-generated fields are ASSUMED by construction. `files_touched` is regex-extracted and is the only VERIFIED field in the object. That distinction should be queryable, not remembered.

---

## 5. Retrieval

**Day 1, single mode:** FTS5 BM25 over `exchange_fts`, returning verbatim text.

```sql
SELECT e.id, e.ts, e.project_id, e.verbatim,
       bm25(exchange_fts) AS raw_score
FROM exchange_fts
JOIN exchange e ON e.rowid = exchange_fts.rowid
WHERE exchange_fts MATCH ?
ORDER BY raw_score * decay_weight(e.ts) LIMIT 10;
```

`decay_weight` is a registered Python UDF (section 6), not SQL, because SQLite has no exponential function by default.

**The two-tier discipline is enforced in the return path, not by convention.** The retrieval function returns `e.verbatim` and never returns `exchange_core`. Distilled text is a routing artifact. This matters more here than in the paper: the corpus contains resume claims and funnel numbers, and a paraphrase of a claim presented as the claim is exactly the failure mode the operator's claim controls exist to prevent (the retracted 24%-to-64% figure). A distilled summary shown as evidence would manufacture that class of error at scale.

**Room-scoped retrieval** as a second entry point, cheap and available day 1 because rooms come from the same distillation pass:

```sql
SELECT e.* FROM room r JOIN exchange e ON e.id = r.exchange_id
WHERE r.room_key = ? AND r.relevance > 0.5 ORDER BY e.ts DESC;
```

**Later (approval-gated):** `pip install sentence-transformers` gives `all-MiniLM-L6-v2` (22 M params, CPU-only, 384-dim, the paper's exact choice at lines 182-186). Embed `distill_text`, store vectors as a numpy `.npy` sidecar (numpy is present, so brute-force cosine over ~5,000 vectors is a sub-millisecond matmul and needs no FAISS at all). Fuse with CombMNZ against the FTS5 verbatim ranking. That is the 0.759 configuration.

**Cost note:** at 5,000 objects × 384 dims × 4 bytes, the entire vector index is 7.7 MB. FAISS is unnecessary at this scale. The paper used `IndexFlatL2`, which is brute force. **INFERENCE**: exact brute force in numpy is equivalent to the paper's Exact mechanism (MRR 0.717 on distilled), not to its HNSW; on a corpus this small they should not differ meaningfully, but I have not measured it.

---

## 6. Decay

**Constraint that overrides the prior art:** the operator's never-delete rule is `emphatic-correction` strength and restated across every compaction. Beads' "semantic compaction of old closed items" and any TTL-eviction scheme collide with it head-on. Decay here must mean *rank suppression and tier demotion*, never row removal.

Three mechanisms, all non-destructive:

**1. Recency weighting on retrieval (soft).** A half-life on the BM25 score, applied at query time so it is a tuning knob, not a mutation:

```python
def decay_weight(ts_iso: str, half_life_days: float = 45.0) -> float:
    age = (now - parse(ts_iso)).days
    return 0.5 ** (age / half_life_days)
```

**INFERENCE**: 45 days is a starting guess, not a measured optimum. It should be tuned against a held-out query set once one exists, and until then it is a knob that has not been validated.

**2. Tier demotion (structural).** `rule.tier` moves hot to warm to cold on a schedule:

- **hot**: injected into every session at SessionStart. Hard cap 100 rules, enforced by the injector, not by hope.
- **warm**: retrievable on query, not injected.
- **cold**: present, reachable only by explicit query with an id or an exact room key.

Promotion rule, cheap and evidence-driven: a rule restated by the operator (`n_restated` incremented) or an `emphatic-correction` promotes to hot and resets `last_seen`. A rule not matched in 90 days demotes one tier. Nothing ever leaves the table.

**3. Supersession, not deletion (semantic).** When a rule is contradicted or replaced, set `superseded_by` on the old row and insert the new one. The rules corpus in the task brief has roughly a dozen near-duplicate restatements of the em-dash rule and the destructive-ops rule. Those are not noise: their repetition *is* the strength signal, which is why `n_restated` exists as a column. Deduplication should collapse them into one row with a high `n_restated` and an `evidence_ids` array, not discard the copies.

**The one thing this decay design deliberately refuses:** semantic compaction that rewrites old content into a summary. That is lossy, irreversible, and manufactures exactly the "reconstruct a file whose content was never seen" failure the operator already logged as a lesson.

---

## 7. Compaction survival

**Verified constraint, and it is the load-bearing one:** `precompact-handoff.sh` states in its own source, "PreCompact supports no additionalContext (verified vs hooks docs 2026-07-24); summarizer steering lives in session-recall.sh (SessionStart source=compact) instead."

So compaction survival cannot be pushed at compaction time. It must be pulled at the next session start. The wiring already exists and needs extending, not creating:

**PreCompact (`precompact-handoff.sh`, already wired):** add one line that flushes the pending write-queue and writes a compaction marker row. It already snapshots `git status` and `git log` to `compact-log.md`. No new hook.

**SessionStart (`session-recall.sh`, already wired, already branches on `source`):** it already gates on `source in {startup, resume, compact, clear}`. Add a hot-tier injection:

```
source == 'compact'  -> inject hot rules + last 5 exchanges of THIS conv_id
source == 'startup'  -> inject hot rules + last handoff + open bus messages
source == 'resume'   -> same as startup
```

**The budget that makes this work, computed not guessed:** 100 hot rules at ~38 tokens each is 3,800 tokens. That is an affordable SessionStart injection. Injecting 100 verbatim exchanges at 371 tokens each would be 37,100 tokens, which is not. This is the concrete, arithmetic reason the distillation layer is worth building even though day-1 retrieval does not use it: **distillation is what makes the hot tier injectable at all.** Retrieval and injection are two different consumers, and the paper's compression result serves the second one immediately even while the BM25 finding blocks it from the first.

That reframing is the strongest single argument for building the distilled layer on day 1 despite it not yet being the search index.

---

## 8. Write path: who writes, when, with what gate

**Standing rule that dictates the shape:** "i dont want any stop guards, i want redirects to keep it flowing and running." A memory write must never block or slow a turn. The paper ran per-turn distillation inline in a Stop hook with a 60-second timeout, which is exactly the stall this rule forbids.

**Solution: write-behind queue. The Stop hook never calls an LLM.**

```
Stop hook (existing, add a 3rd entry, target < 50 ms)
  -> memory_enqueue.py
     - reads $CLAUDE_TRANSCRIPT_PATH from hook stdin
     - appends {conv_id, ply_start, ply_end, project, lane, ts}
       to state/memory-queue.jsonl
     - exits 0 ALWAYS (wrapped, never fails the turn)

Drainer (separate, out of band: scheduled, or on SessionStart of the next session)
  -> memory_drain.py
     1. slice verbatim from the transcript
     2. filter: skip if < 100 chars (paper line 131); split if > 20 plies
     3. PII scrub via existing ~/.claude/bin/pii-scrub.py  <-- MANDATORY GATE
     4. regex-extract files_touched (deterministic, register=VERIFIED)
     5. distill via haiku, batch prompt from paper Appendix B
     6. INSERT exchange, distilled, room; rebuild FTS rows
     7. on any failure: leave the queue row, log, move on. Never lose input.
```

**Four gates, in order of how hard they bind:**

1. **PII scrub before write, non-bypassable.** `pii-scrub.py` already exists at `~/.claude/bin/pii-scrub.py`. The standing rule is that PII is masked at the model boundary and never placed in embedding indexes. This corpus is resumes and candidate records. The scrub runs before both the distiller call and the DB insert. If the scrubber errors, the row stays queued and is **not** written. This is the one place the pipeline is allowed to stop rather than redirect, because the rule it protects is stricter than the flow rule.
2. **Local-only, no remote.** `memory.db` is gitignored and never pushed. Any DoltHub or beads-remote sync of this table is blocked until a Pro account is confirmed, per the constraint documented in the operator's own `tools/dolt/client.py`.
3. **Register discipline.** `distilled.register = 'ASSUMED'` for the two LLM fields; `files_touched` is VERIFIED. A downgrade or a distillation the operator corrects appends to the existing `state/lessons.jsonl` as a calibration loss, which is the mechanism already in place (18 rows).
4. **Rule promotion needs evidence, not inference.** A row enters `rule` only with at least one `exchange_id` in `evidence_ids`. `strength = 'emphatic-correction'` requires the operator's own words in the cited exchange. No rule is synthesized from a summary.

**Who else writes:**

- **`/remember` (explicit)**: operator-initiated, writes a `rule` row directly at `tier='hot'`, `strength='stated-once'`, register VERIFIED because the operator is the source.
- **Batch backfill (once)**: the same drainer over all 47 existing transcripts.
- **Nothing else.** No agent writes rules autonomously. The system proposes rules into `state/selfimprove/proposals.jsonl` (which already exists) and the operator promotes them.

---

## 9. The cheapest first increment: one day

**Ship: `tools/memory/` with three files and one hook line.**

```
tools/memory/schema.sql       # section 4 verbatim
tools/memory/ingest.py        # transcript -> exchange rows + FTS, PII-scrubbed
tools/memory/recall.py        # FTS5 BM25 query, returns VERBATIM, decay-weighted
```

Plus one line added to the existing Stop hook array pointing at `memory_enqueue.py`.

**What day 1 delivers, concretely and measurably:**

- All 47 transcripts (39,910 rows, ~7.3 MB of text) ingested into `exchange` + `exchange_fts`.
- `python tools/memory/recall.py "thompson sampling arms"` returns ranked verbatim exchanges across every session ever run, in milliseconds.
- Zero new dependencies. Python stdlib `sqlite3`, FTS5 already compiled in, verified.
- Zero external cost. No LLM call in the day-1 path at all.
- The mechanism that the paper scores highest among pure-verbatim configurations (BM25-FTS, MRR 0.745).

**Acceptance check, executable, must be run before claiming it works:**

```bash
python tools/memory/ingest.py --all && \
python tools/memory/recall.py "bus.jsonl hash chain" --expect-contains "tamper EVIDENT"
```

That query has a known-correct answer: the string is in a real bus row I read this session, so it is a **positive control**, which the operator's standing rule requires before a zero-hit result can close anything.

### What day 1 deliberately does NOT do

| Deferred | Why |
|---|---|
| **Any LLM distillation** | Needs a haiku call per exchange. Day 1 has no LLM in the path, so it cannot fail on quota, latency, or a bad JSON parse. |
| **Vector search** | Needs `pip install sentence-transformers`, which is a per-action-approval install. Also unnecessary: verbatim BM25 already beats verbatim vector by 0.100 MRR. |
| **The `rule` table and hot-tier injection** | Requires distillation first (rules come from distilled exchanges). This is day 2 to 3, and it is the increment that actually reduces the operator's prompting burden. |
| **Installing beads** | Third-party install, needs approval, and needs a real trial rather than a documentation read. Week 2. |
| **Retiring `MEMORY.md`** | It works today. Replacing a working thing with an untrialed thing is the failure pattern already named. |
| **Any remote sync** | Blocked by the DoltHub public-only constraint until Pro is confirmed. |
| **Touching `bus.jsonl`, `lessons.jsonl`, `claims-verify.jsonl`** | Those are hash-chained and load-bearing. The memory layer is additive. Nothing existing is migrated on day 1. |

**Honest limit of the day-1 artifact:** it is keyword retrieval. Ask it "what did I decide about cost control" and it will miss an exchange that said "keep external spend at zero" and never used the word "cost." That gap is exactly what the distilled-plus-vector layer closes, and it is the reason to do days 2 and 3, not a reason to skip day 1.

---

## 10. Risks I have not retired

1. **The 0.745 number is the paper's, on the paper's corpus.** I have not measured MRR on this corpus, and I have no query set to measure against. Building one (20 to 30 recall queries with known-correct answers) is the actual prerequisite for any claim that retrieval is good, and it does not exist yet.
2. **Exchange segmentation is unvalidated here.** The paper's rules (100-char floor, 20-ply split) were tuned on 4,182 conversations of a different shape. This operator's p90 prompt is reportedly ~38,000 characters of pasted document, which is a very different ply-length distribution. **INFERENCE**: the 20-ply split will likely fire rarely and the 100-char filter will remove more than the paper's 13%. Measure before tuning.
3. **PII scrubbing is the single point of failure.** I did not read `pii-scrub.py` and cannot attest to its recall. Given the corpus is resumes and candidate records, that file needs its own planted-positive test before the first batch ingest, not after.
4. **`.gitignore` was modified in the working tree** (visible in git status). If `memory.db` is added there, that change collides with an in-flight edit and needs a look first.
5. **I did not install or run beads or Dolt.** The adopt-for-work-graph recommendation is documentation-grounded and gh-metadata-grounded, and it is not a trial result.