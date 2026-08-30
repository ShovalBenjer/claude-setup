# Research corpus and cache (row-reuse, cache2action)

Status: proposed. Corpus and cache design, 2026-07-31. Not built.

> Renamed 2026-07-31. This document originally called the read path `cache2cache`.
> That name is taken: `cache2cache` is Cache-to-Cache, arXiv 2510.03215 (ICLR 2026,
> Tsinghua / CUHK / SJTU / Shanghai AI Laboratory / Infinigence AI), which fuses one
> model's KV-cache into another's per layer. ADR-0018 already owns that term and
> rules that it applies only on open-weight legs. Nothing in this document is that
> mechanism: this is document-row reuse over a sqlite corpus, so it is `row-reuse`.
> `cache2action` has no collision and keeps its name.

Date: 2026-07-31. Status: PROPOSAL. Nothing in this document has been executed.
Every item below is UNEXECUTED. The operator decides which, if any, get built.

Author lane: A (harness). Written under ADR-0005 (enforcement over prose) and
ADR-0010 (disk is memory). No file outside this one was created or edited.

---

## 1. What was verified, and what in the brief is stale

All commands run 2026-07-31 from `C:\Users\shova\claude-setup`. Python 3.11.9,
sqlite 3.45.1, FTS5 confirmed available.

### 1.1 Corrections to the brief

| Brief said | Measured | Correction |
|---|---|---|
| `work-docs/research/prompts/` has 7 prompts | `ls` returns 11 entries | 11, not 7. |
| voice-metrics "stores embeddings locally" | `voice_engine.py:90` reads `class IdiolectEmbedding:` with docstring `Hashed char-ngram TF-IDF -> PCA. Fit once on a corpus, then transform.` | It does NOT store embeddings. It fits them in numpy at runtime; `profiles.json` (5,143 bytes) holds fitted scalar stats only. The sqlite it touches is the read-only WhatsApp export `wa_work/genericStorage.dec.db`, a data source, not an embedding store. |
| intent-control-plane has "14 tables" | `schema.py` is 277 lines; DDL is one `conn.executescript` inside `apply_schema` | Verified tables include `schema_meta`, `events`, `intent_cards`, `context_packs`, `evidence`, `graph_edges`. The exact count of 14 was not re-verified; treat it as unconfirmed. |
| `shadcn/ui` and `shadcn-ui/taxonomy` are two seeds | `gh api repos/shadcn/ui` resolves to `shadcn-ui/ui` | `shadcn/ui` is a redirect, not a distinct source. 13 named seeds are 12 distinct repos. |
| `kamranahmedse/developer-roadmap` | resolves to `nilbuild/developer-roadmap` | Owner changed. The seed name is stale. |
| `30-seconds/30-seconds-of-code` | resolves to `Chalarangelo/30-seconds-of-code` | Org name is stale, repo is live. |
| `modelcontextprotocol` | is a GitHub org, not a repo | Ambiguous seed, resolved into three candidate repos below. |
| `docs/memory-layer--nexus-...md` is 27 lines, a Rust GPU engine spec | `wc -l` = 27, text ends mid-`Cargo.toml` at `chrono = ...` with no closing fence | Confirmed exactly as stated. |

### 1.2 Commands run

```bash
find work-docs research-papers docs/analysis -name "*.md" | wc -l      # 355
gh api repos/<name> -q '[.full_name,(.license.spdx_id//"NONE")]|join(" ")'
gh api repos/<name>/contents/LICENSE -q '.content' | base64 -d          # actual text
curl -s https://huggingface.co/api/datasets/<id>                        # HF metadata
python -c "import sqlite3; ...CREATE VIRTUAL TABLE t USING fts5(x)"     # FTS5 OK
```

Library probe on this machine: `numpy 2.2.6`, `duckdb 1.1.1`, `polars 1.9.0`
present. `sklearn`, `sentence_transformers`, `onnxruntime`, `tiktoken`,
`pandera`, `hypothesis` all MISSING. This constrains section 4 hard: any design
needing a neural embedding model needs an install, and installs are outside
tonight's permission boundary.

### 1.3 The nexus memory-layer file: what is reusable

`docs/memory-layer--nexus-gemini-code-1785456331041.md`, 27 lines. It is a
truncated mission spec for `nexus-engine-rs`, a Rust GPU binary combining an
"Agentic Divergence Sandbox" with a physics and visual architecture auditor. It
names `eframe/egui/wgpu`, `rapier2d`, `petgraph`, `similar`, `tree-sitter`, and
WGSL compute shaders. The filename says memory-layer and the content is a GPU
renderer. The two do not match.

Reusable for this corpus design: two items, both small.

1. `petgraph` plus the stated git-worktree revert idea is a graph-over-artifacts
   model, which maps onto the `graph_edges` table intent-control-plane already
   has. That confirms an existing choice; it is not a new input.
2. `similar` (a Rust diff crate) names the right primitive for near-duplicate
   detection. The concept transfers, the crate does not, since nothing here is
   Rust.

Everything else is not reusable. There is no memory design in the file, no
schema, no retrieval model, and it terminates mid-dependency-list.
Recommendation: do not cite this file as prior art for the corpus. Renaming or
archiving it is a separate decision, out of scope tonight.

---

## 2. Corpus inventory, measured

In-process Python pass over 355 markdown files in `work-docs/`,
`research-papers/`, `docs/analysis/`, read with `errors="replace"`.

```
files:                355
bytes:                5,697,764  (5.43 MiB)
words:                782,617
exact dup groups:     53   (54 redundant files, 15.2% of corpus)
near-dup pairs >0.7:  55   (8-word shingles, stride 4, Jaccard)
files with no URL and no [S#]:  205 / 355  (57.7%)
files using the [S#] protocol:  4 / 355    (1.1%)
est. chunks @ ~350 words:       7,336
mojibake filenames:             6
```

Per-tree counts: `work-docs` 191, `research-papers` 133, `docs/analysis` 31.
`research-papers` breaks down as `el-vadt` 44, `docs-shoval` 36, `Documents` 24,
`home-md` 24, `Prompts` 4, `knowledge` 1. Those sum to 133 and match the brief.

### 2.1 What the duplication actually is

An earlier naive `find ... -exec md5sum` reported only 9 duplicate groups. That
undercount came from filenames containing spaces breaking the shell loop. The
corrected in-process pass finds 53. The lesson generalises: this corpus has
filenames with spaces, dashes, parentheses, and 6 carrying mojibake from a
cp1255 round-trip. Any ingestion tool that shells out per file will silently
miss rows. Ingestion must run in-process.

Three duplication classes, needing different treatment:

- **Class A, byte-identical copies across trees.** `research-papers/home-md/` and
  `work-docs/root-cleanup-2026-05-28/` are largely the same documents. Pairs at
  Jaccard 1.0 include `claude-setup-master-plan-2026-05-02.md`,
  `claude-skills-scatter-2026-05-03.md`, `deep-research-bwrap-wsl-error.md`, and
  `compass_artifact_wf-662a99e3-...md`. This is a directory-level copy event, not
  scattered accidents. Hash dedup removes all 54 with zero loss.
- **Class B, versioned drafts of one artifact.** `maryam-v6.7-DEPLOYED.md` and
  `maryam-v6-system-prompt.md` sit at Jaccard 1.0 on shingles but carry different
  names and different intent. These are NOT redundant; one is the deployed
  revision. A hash dedup keeping an arbitrary winner destroys the
  deployed-versus-draft fact. They need a `supersedes` edge, not deletion.
- **Class C, mojibake twins.** The 2026 Mathematics and Statistics Frontier
  document exists under `work-docs/root-cleanup-2026-05-28/` with a proper dash
  and under `research-papers/home-md/` with a `GAMMA-aleph-pe` byte sequence.
  Same content, different encoding damage. A byte hash sees these as distinct, so
  normalisation must precede hashing.

The headline number: **of 355 files, at most 301 are plausibly unique**, and the
true unique-concept count is lower because Class B and the 55 near-duplicate
pairs overlap. Do not claim a unique count below 301 without running the section
6 pipeline. 301 is measured; anything smaller is estimated.

### 2.2 The citation defect, quantified

The operator's standing constraint is that uncited claims are a defect.
**205 of 355 files (57.7%) contain neither a URL nor an `[S#]` tag, and only 4
files use the `[S#]` protocol from his own synthesis standard.** This is the
largest quality problem in the corpus and it is measurable, which is what makes
it fixable under ADR-0005. It also means a naive ingestion of everything on disk
would populate the store majority-uncited. Section 6 gates on this.

---

## 3. External seed sources

All rows from `gh api repos/<name>` on 2026-07-31, plus the actual LICENSE text
fetched and read for every `NOASSERTION`. Size is the GitHub `size` field in KB.
Recency is `pushed_at`.

| # | Source (resolved) | License (verified) | Size KB | Last push | Structured or prose | Verdict |
|---|---|---|---|---|---|---|
| 1 | `shadcn-ui/taxonomy` | MIT | 14,600 | 2026-04-20 | TypeScript source, structured | vendor |
| 2 | `shadcn-ui/ui` | MIT | 68,214 | 2026-07-30 | TS source plus MDX docs | vendor |
| 3 | `Chalarangelo/30-seconds-of-code` | CC-BY-4.0 | 743,165 | 2026-07-29 | Astro `content/`, structured frontmatter | index-only |
| 4 | `nilbuild/developer-roadmap` | all rights reserved | 362,054 | 2026-07-30 | JSON roadmap graphs | link-only, hard block |
| 5 | `goldbergyoni/nodebestpractices` | CC-BY-SA-4.0 | 69,590 | 2026-06-15 | prose, needs extraction | index-only |
| 6 | `donnemartin/system-design-primer` | CC-BY-4.0 | 11,277 | 2026-03-20 | prose plus Python | vendor |
| 7 | `ashishps1/awesome-system-design-resources` | GPL-3.0 | 2,340 | 2026-02-16 | prose links plus Java | link-only |
| 8 | `binhnguyennus/awesome-scalability` | MIT | 1,607 | 2026-01-04 | link list | vendor (links only) |
| 9 | `GoogleCloudPlatform/ml-design-patterns` | Apache-2.0 | 35,041 | 2021-04-28, ARCHIVED | Jupyter notebooks | drop |
| 10 | `eugeneyan/applied-ml` | MIT | 397 | 2024-07-18 | single README link list | vendor |
| 11 | `paperswithcode/paperswithcode-data` | none in repo | 6 | 2025-09-08 | README pointer, no data | dead, replace |
| 12 | `e2b-dev/awesome-ai-agents` | CC-BY-NC-SA-4.0 | 117,630 | 2026-07-09 | README prose | link-only, NC risk |
| 13a | `modelcontextprotocol/modelcontextprotocol` | Apache-2.0 and MIT, in transition | 55,581 | 2026-07-30 | spec TS plus docs | vendor |
| 13b | `modelcontextprotocol/servers` | same transition | 29,656 | 2026-07-29 | TS and Python source | vendor |
| 13c | `modelcontextprotocol/python-sdk` | MIT | 12,692 | 2026-07-30 | Python source | vendor |

### 3.1 Licensing conclusions, stated per source

Definitions. **vendor** means we may copy extracted content into this repo with
attribution. **index-only** means we may fetch, chunk, and store locally for
retrieval but must not redistribute the text in repo output or commits.
**link-only** means store the URL and our own notes, never the source text.

1. **shadcn-ui/taxonomy, MIT.** Vendor. MIT permits copying with the notice, so
   an attribution line is required in any vendored file. It is 3 months stale and
   is a demo app, so its value is narrow: one worked Next.js production shape,
   not a contract library.
2. **shadcn-ui/ui, MIT.** Vendor, and the highest-value production-code seed on
   the list. Pushed yesterday, and it publishes a machine-readable component
   registry, so the "which code was actually implemented" extraction is a JSON
   read rather than a prose parse.
3. **Chalarangelo/30-seconds-of-code, CC-BY-4.0.** Index-only, and the reason is
   size rather than law. CC-BY would permit vendoring with attribution, but 743
   MB is 130x the entire local corpus and would dominate any index. Fetch the
   `content/` collection only, which carries structured frontmatter.
4. **nilbuild/developer-roadmap, all rights reserved.** LINK-ONLY, a hard block
   rather than a preference. The license text is explicit: "You are allowed to
   use this material for personal use but are not allowed to use it for any other
   purpose including publishing the images, the project files or the content in
   the images in any form either digital, non-digital, textual, graphical or
   written formats." GitHub's `NOASSERTION` label hides this, and only reading
   the file surfaces it. Storing its content in an index any agent can retrieve
   and paste is the prohibited use. **The pipeline must refuse this by hostname,
   not by policy prose.**
5. **goldbergyoni/nodebestpractices, CC-BY-SA-4.0.** Index-only. ShareAlike is
   the blocker: vendoring extracted text arguably obliges licensing the derived
   corpus under CC-BY-SA, which conflicts with keeping the harness under the
   operator's own terms. Index locally, cite by URL, never commit the text.
6. **donnemartin/system-design-primer, CC-BY-4.0.** Vendor. LICENSE.txt is plain
   CC BY 4.0 with a personal-repo disclaimer. At 11 MB it is the best
   size-to-value ratio on the list. It is prose needing extraction; the Python
   solution directories are the structured part worth taking first. 4 months
   stale, which for system design fundamentals is not a defect.
7. **ashishps1/awesome-system-design-resources, GPL-3.0.** Link-only. GPL on a
   documentation repo is a copyleft trap: incorporating its text into a corpus we
   might later publish raises a licensing question nobody here wants to answer.
   The content is mostly links to other people's work, so link-only loses little.
8. **binhnguyennus/awesome-scalability, MIT.** Vendor, link list only. 1.6 MB,
   MIT, no code. Its value is as a bibliography of engineering blog posts, which
   makes it a seed for crawling rather than a corpus. 6 months stale.
9. **GoogleCloudPlatform/ml-design-patterns, Apache-2.0.** Drop. The license is
   the most permissive on the list and it does not matter, because the repo is
   **archived and last pushed 2021-04-28**, five years and three months stale.
   Its ML content predates the entire transformer-agent era the operator works
   in. Including it would inject confidently-wrong 2021 assumptions into a corpus
   whose stated first defect is opposing information.
10. **eugeneyan/applied-ml, MIT.** Vendor. 397 KB, one README, MIT, a curated
    bibliography of company engineering posts. Two years stale but bibliographies
    age gracefully. Cheapest ingest on the list.
11. **paperswithcode/paperswithcode-data.** DEAD. The repo is 6 KB and its
    contents listing returns exactly one file, `README.md`. That README states
    the data now lives at `huggingface.co/datasets/pwc-archive/*` under CC-BY-SA.
    Its own claim that "data is regenerated daily" is itself stale: the HF
    mirrors last changed 2025-09-10 and the org is literally named
    `pwc-archive`. Papers with Code is frozen. Replace with the HF datasets in
    3.2, and note the snapshot is 2025, which **disqualifies it under the
    operator's 2026-only paper rule** except as a historical baseline.
12. **e2b-dev/awesome-ai-agents, CC-BY-NC-SA-4.0.** Link-only in practice. The
    NonCommercial term is the problem: if this harness ever touches paid or
    employer work, an NC-licensed corpus becomes a liability, and ShareAlike
    compounds it. 117 MB, mostly images and README prose, low structured density.
    Cost-to-value is poor before the license is even considered.
13. **modelcontextprotocol.** The seed named an org. Three repos matter, and the
    license state is unusual enough to state exactly. The LICENSE says the
    project "is undergoing a licensing transition from the MIT License to the
    Apache License, Version 2.0", that new contributions are Apache-2.0,
    documentation excluding specifications is CC-BY-4.0, and contributions whose
    authors have not consented to relicensing **remain MIT**. Every path is
    therefore MIT or Apache-2.0, both vendor-safe, so vendor is fine. But a
    blanket "this repo is Apache-2.0" attribution would be wrong; attribute
    per-file or as "MIT/Apache-2.0, see upstream LICENSE". `python-sdk` is
    cleanly MIT and is the safest of the three.

### 3.2 Dataset candidates that beat a GitHub repo

Verified via `curl https://huggingface.co/api/datasets/<id>`.

| Dataset | License tag | Last modified | Why it beats the repo |
|---|---|---|---|
| `pwc-archive/evaluation-tables` | cc-by-sa-4.0 | 2025-09-13 | The only live carrier of the seed-11 data. 60,842 downloads in the reported window, two orders above its siblings, which says it is the piece people actually use. It is **structured JSON of benchmark results**, the one thing a markdown repo cannot give: a table you can query for "did source A and source B report different numbers for the same benchmark". That is the operator's contradiction requirement, natively. |
| `pwc-archive/links-between-paper-and-code` | cc-by-sa-4.0 | 2025-09-10 | Structured paper-to-repo edges. Turns "which code was actually implemented" from an extraction problem into a join. |
| `pwc-archive/methods` | cc-by-sa-4.0 | 2025-09-10 | A controlled vocabulary of ML method names. Useful as a normalisation dictionary at ingestion so "MHA" and "multi-head attention" collapse to one concept. Highest leverage per byte on the list. |
| `pwc-archive/papers-with-abstracts` | **no license tag** | 2025-09-10 | Listed and flagged: unlike its four siblings it carries no license tag on HF even though the source README claims CC-BY-SA for all data. Index-only until resolved. |

All five are CC-BY-SA in intent, so ShareAlike applies and they are index-only
under the same reasoning as seed 5. All five are a 2025 snapshot.

**Kaggle: no candidate recommended.** Checked the shape of the need rather than
the catalogue. Kaggle's strengths are tabular competition data and notebooks,
neither of which is production code contracts, system design, or 2026 agent
research. Kaggle also requires an authenticated API token for bulk download,
which adds a credential to a harness that currently needs none. Adding a secret
to reach data HuggingFace serves anonymously is a bad trade. If a Kaggle source
is ever wanted, the burden is to name the specific dataset and beat
`pwc-archive` on recency, not to browse.

**Explicitly rejected: `bigcode/the-stack-v2` and `codeparrot/github-code`.**
Both verified live (`license:other`; the-stack-v2 is gated `auto`, last modified
2024-04-23; github-code last modified 2022-10-20). Rejected on purpose: they are
training corpora measured in terabytes, they are 2 to 4 years stale, and the
operator wants which libraries and one-liners were actually implemented, which is
a curation question rather than a volume question. A bigger pile of
undifferentiated code makes the noise defect worse.

### 3.3 Summary of source verdicts

- Vendor (8 repos): shadcn-ui/taxonomy, shadcn-ui/ui, system-design-primer,
  awesome-scalability (links only), applied-ml, mcp spec, mcp servers, mcp
  python-sdk.
- Index-only (3): 30-seconds-of-code (`content/` subset), nodebestpractices, the
  four pwc-archive HF datasets.
- Link-only or drop (4): developer-roadmap (hard block), awesome-system-design-
  resources (GPL), ml-design-patterns (archived 2021, drop), awesome-ai-agents
  (NonCommercial).
- Dead (1): paperswithcode-data, replaced by pwc-archive on HuggingFace.

**Of 13 named seeds, 1 is dead, 1 is legally blocked, 1 is five years archived,
1 duplicates another, 1 was an org rather than a repo, and 2 have moved owner.**
6 of 13 seed identifiers were wrong or unusable as given. That is the main
finding of this section, and it is why a corpus needs a license and liveness
check at ingestion time rather than a curated list in a document.

---

## 4. The store

### 4.1 Sizing first, choice second

The local corpus is 782,617 words, 5.43 MiB of text, producing an estimated
**7,336 chunks** at ~350 words each, measured by splitting on h2/h3 boundaries
and subdividing long sections. External vendor sources, if all eight land, add an
estimated 8,000 to 15,000 chunks, dominated by system-design-primer and the mcp
repos. Design target: **25,000 chunks**, one order of headroom.

That number decides everything.

### 4.1a Chunking: the one thing this spec asserted instead of deciding

**GAP FOUND 2026-08-03 by comparison against DigitalOcean's published knowledge-base and
chunking-strategy docs.** The sentence above is the entire chunking strategy: ~350 words,
split on h2/h3, subdivide long sections. That is DigitalOcean's **section-based** strategy,
picked without naming an alternative, and applied uniformly to a corpus the atlas measures
at **420 documents across 16 clusters**: linguistics wiki dumps, four commercial sales
books, API-shaped specs, generated maps, and code.

By DO's own content-type guidance that span calls for three different strategies:

| DO strategy | Parameters | They recommend it for |
|---|---|---|
| fixed-length | token count | logs, OCR, machine-generated text, **code** |
| section-based | `max_chunk_size` | structured documents with headings |
| semantic | `semantic_threshold`, `max_chunk_size` | **long-form prose, academic writing** |
| hierarchical | `parent_chunk_size`, `child_chunk_size` | **API references, legal contracts, manuals** |

Four further constraints this spec does not carry, all from the same source:

1. **Cost multiplier.** Semantic chunking costs **1.5 to 3 times** more to index.
   Hierarchical raises *retrieval* cost, because parent and child are returned together.
   This spec has no cost model for chunking at all.
2. **A floor.** Chunks must be at least ~**100 tokens** and must fit the embedding model's
   window. This spec states ~350 words with no floor and no window check.
3. **The embedding model is immutable after the store is created**, and changing chunking
   forces a **full re-index**. That is unpriced here, and it matters right now: the choice
   between Qwen3-Embedding-8B and KaLM-Embedding-Gemma3-12B (`docs/analysis/2026-08-03-math-trends-and-model-stack.md` §5)
   is being weighed as if it were reversible. It is not.
4. **Incremental re-index.** DO skips unchanged files. §9's "migration path in ingestion
   units" has no skip logic, so today's design re-embeds everything on every run.

**What changes in this spec.** Chunking becomes **per-cluster, keyed off the atlas
cluster** rather than one rule for the corpus: fixed-length for `generated-map` and code,
section-based for `spec`, `adr`, `prd`, `analysis`, semantic for `sales-and-books` and
`linguistics`, hierarchical for `research-prompt` and `sota-report`. The chunk count above
is therefore an estimate under one strategy and will move once the strategies differ; it is
kept because the **order of magnitude** is what the ANN rejection rests on, and three
strategies do not change 25,000 into 250,000.

**Cost of fixing this now: zero.** The status of this spec is `proposed` and nothing has
been indexed. The same gap discovered after the first index costs a full re-embed.

**Prior art owed.** `docs/prior-art/` carries no record for a corpus or retrieval
component. If this is built, DigitalOcean's four-strategy table is a named alternative that
record has to answer.

- FTS5 over 25k rows: single-digit MB, sub-millisecond queries. Trivial.
- A dense index at 25,000 x 256 float32 is **25.6 MB**, and brute-force cosine
  over it in numpy is one `(25000,256) @ (256,)` matvec, about 6.4M FLOPs, under
  10 ms. **An approximate-nearest-neighbour index is not warranted at this
  size.** No FAISS, no Chroma, no LanceDB, no pgvector.
- DuckDB and Polars are installed and are right for the batch analysis passes
  (dedup, contradiction sweeps) but are the wrong home for the store: no
  append-only audit trail, and DuckDB takes an exclusive file lock that would
  collide with the parallel sessions this repo actually runs.

### 4.2 Chosen substrate: one sqlite file plus a jsonl ingestion ledger

**Store: sqlite with FTS5 at `state/corpus.db`.** Justified against the
alternatives on this repo's own facts:

- vs. **jsonl**: the corpus needs queries answering "which rows are uncited" and
  "which rows contradict each other". Those are joins and aggregates. A jsonl
  ledger answers them only by full scan in application code, and the repo already
  carries a 2.1 MB `state/gate-runs.jsonl` and a 1.8 MB
  `state/resource-ledger.jsonl` showing where that ends. jsonl stays, for the
  ingestion log rather than the corpus.
- vs. **intent-control-plane's existing database**: tempting, rejected. ICP's
  schema is about intents, events, and evidence for work being done. A research
  corpus is a different aggregate with a different lifecycle and retention
  policy. Sharing the file couples corpus growth to a packaged subproject's
  migrations and to its three known-failing Windows tests. What we DO reuse is
  ICP's patterns: the `connect()` context manager at `schema.py:34`, whose
  docstring says the `with` block "releases the file, not just the transaction",
  is exactly the Windows handle discipline this repo learned the hard way, and
  `graph_edges` is the right shape for typed relations.
- vs. **a vector database**: rejected on the numbers above. 25.6 MB of float32 in
  a numpy `.npy` sidecar beside the sqlite file is simpler, faster to build, has
  no server, and needs no install.

**Ingestion ledger: `state/corpus-ingest.jsonl`**, append-only, matching the
existing convention. Every accept, reject, dedup merge, and contradiction flag
lands there with its reason. This is what makes section 6 auditable. It is
deliberately NOT hash-chained: `state/bus.jsonl` is chained because rewriting it
would be an integrity attack, whereas an ingestion log is allowed to be
re-derived by re-running the pipeline.

### 4.3 Schema (UNEXECUTED)

```sql
-- state/corpus.db
create table if not exists corpus_meta (
  key text primary key,
  value text not null
);

-- one row per source artifact, local file or external
create table if not exists sources (
  source_id        text primary key,        -- 's' || sha256(canonical_uri)[:16]
  canonical_uri    text not null unique,    -- abs path, or https URL
  kind             text not null,           -- local_md|repo|hf_dataset|paper|derived
  title            text not null,
  license_spdx     text not null,           -- verified, never the GitHub label alone
  license_verdict  text not null,           -- vendor|index_only|link_only|blocked
  license_evidence text not null,           -- api path plus check date
  publisher        text,                    -- org, venue, or institution
  published_utc    text,                    -- for the 2026-only paper rule
  fetched_utc      text not null,
  upstream_rev     text,                    -- git sha or HF revision
  upstream_mtime   text,                    -- pushed_at / lastModified
  liveness         text not null,           -- live|stale|archived|dead
  content_sha256   text not null,
  bytes            integer not null,
  supersedes       text references sources(source_id)
);

-- one row per retrievable unit
create table if not exists chunks (
  chunk_id       text primary key,          -- 'c' || sha256(norm_text)[:16]
  source_id      text not null references sources(source_id),
  ordinal        integer not null,
  heading_path   text not null,             -- 'H1 > H2 > H3'
  kind           text not null,             -- claim|code|table|config|link|prose
  lang           text,                      -- for kind=code
  norm_text      text not null,             -- NFC, dash-normalised, mojibake repaired
  raw_text       text not null,
  word_count     integer not null,
  norm_sha256    text not null,             -- dedup key over norm_text
  simhash        integer not null,          -- 64-bit, near-dup blocking
  citation_count integer not null default 0,
  status         text not null,             -- accepted|quarantined|superseded|rejected
  status_reason  text,
  ingested_utc   text not null,
  unique(source_id, ordinal)
);

-- the enforcement table: a claim with no row here is uncited by construction
create table if not exists citations (
  citation_id      text primary key,
  chunk_id         text not null references chunks(chunk_id),
  target_uri       text not null,           -- URL, DOI, or corpus source_id
  target_source_id text references sources(source_id),
  tag              text,                    -- the literal [S#] as written
  locator          text,                    -- line, section, page
  verified         integer not null default 0,
  verified_utc     text
);

-- typed relations, shape borrowed from intent-control-plane graph_edges
create table if not exists claim_edges (
  edge_id      text primary key,
  source_chunk text not null references chunks(chunk_id),
  target_chunk text not null references chunks(chunk_id),
  edge_type    text not null,               -- contradicts|supports|supersedes|duplicates|refines
  basis        text not null,               -- numeric|negation|manual|shingle
  confidence   real not null,
  detected_utc text not null,
  resolution   text,                        -- null means open
  resolved_utc text
);

-- "which code was actually implemented", per the operator's rule
create table if not exists artifacts (
  artifact_id   text primary key,
  chunk_id      text not null references chunks(chunk_id),
  artifact_type text not null,              -- library|api|oneliner|config|command|pattern
  name          text not null,              -- 'polars', 'sqlite fts5'
  version       text,
  snippet       text,                       -- the actual line, not prose about it
  implemented   integer not null,           -- 1 = seen in source code, 0 = only discussed
  evidence_path text                        -- upstream file+line proving implemented=1
);

create virtual table if not exists chunks_fts using fts5(
  norm_text, heading_path, content='chunks', content_rowid='rowid',
  tokenize='porter unicode61'
);

create index if not exists ix_chunks_status  on chunks(status);
create index if not exists ix_chunks_simhash on chunks(simhash);
create index if not exists ix_chunks_normsha on chunks(norm_sha256);
create index if not exists ix_cit_chunk      on citations(chunk_id);
create index if not exists ix_edges_open     on claim_edges(edge_type, resolution);
create index if not exists ix_art_name       on artifacts(name, implemented);
```

Dense sidecar: `state/corpus-vec.npy`, shape `(n_chunks, 256)` float32, row order
equal to `chunks.rowid`, plus `state/corpus-vec.json` recording the fit
parameters and the `corpus_meta` generation counter it was built against. A
generation mismatch means the vectors are stale and retrieval must say so.

### 4.4 The two defect queries the operator asked for

> **Implemented as a health oracle:** `tools/corpus/health.py` (2026-08-30). Spec: `docs/specs/2026-08-30-corpus-health-oracle.md`.

The point of the schema is that these are one-liners, so a defect is found by
query rather than by a reader.

```sql
-- uncited: an accepted claim chunk with no verified citation
select c.chunk_id, s.canonical_uri, substr(c.norm_text,1,80)
from chunks c join sources s using(source_id)
left join citations ci on ci.chunk_id = c.chunk_id and ci.verified = 1
where c.kind = 'claim' and c.status = 'accepted' and ci.citation_id is null;

-- contradicted: accepted chunks on an unresolved conflict
select e.edge_id, e.confidence, a.chunk_id, b.chunk_id
from claim_edges e
join chunks a on a.chunk_id = e.source_chunk
join chunks b on b.chunk_id = e.target_chunk
where e.edge_type = 'contradicts' and e.resolution is null
  and a.status = 'accepted' and b.status = 'accepted';
```

### 4.5 Embedding approach that works offline on this machine

Constraint: `sentence_transformers`, `onnxruntime`, and `sklearn` are all absent,
and installing is out of scope tonight. `numpy 2.2.6` is present.

Proposal: **reuse `IdiolectEmbedding` from
`~/.claude/skills/voice-metrics/voice_engine.py:90`**, unchanged in method. It is
a hashed char-ngram TF-IDF projected by PCA, implemented in numpy with a signed
hashing trick at `voice_engine.py:107-109` whose comment states it "keeps
collisions from systematically inflating" counts. It is already fitted on a
35,472-message corpus in this ecosystem, so its behaviour here is known rather
than assumed.

Cost, estimated and not measured: fitting over 25,000 chunks is one pass to build
a `(25000, dim)` count matrix plus a PCA. At the skill's default dimensions this
is seconds to low minutes on CPU, and the artifact is the 25.6 MB `.npy`. Zero
network, zero install, zero dollars.

Honest limit, stated because this is the weakest part of the design: a hashed
lexical embedding gives **no semantic generalisation**. It will not match
"retrieval augmented generation" to "RAG" unless both strings co-occur somewhere.
That is a real gap against a neural embedder. Two cheap mitigations: the
`pwc-archive/methods` vocabulary as a synonym normaliser at ingestion, and FTS5
as the primary retrieval path with vectors used only for reranking and
clustering. **If semantic recall turns out to be the binding constraint, the
correct fix is a small ONNX embedder, decided after the lexical version runs and
fails, not before.** Proposing the install now would be the unsourced novelty
that prior-art-gate exists to block.

> **Implemented:** `tools/corpus/embed.py` (2026-08-30). Spec: `docs/specs/2026-08-30-corpus-embedding-rerank.md`.

---

## 5. row-reuse and cache2action

The operator named these. They are not established terms, so the definitions
below are an interpretation offered for approval, not a report of prior art.

### 5.1 row-reuse

> Implemented in `tools/corpus/rowreuse.py`; spec at `docs/specs/2026-08-30-corpus-row-reuse.md`.

**Definition.** A retrieval that answers a question entirely from stored corpus
rows, and whose output is itself written back as a corpus row with edges to every
row it consumed. The cache both serves and grows. The unit of reuse is a
synthesised answer, so the second time a question is asked it costs one lookup
rather than a re-synthesis over N chunks.

**What it buys over reading a file.** Reading a file gives one document. A
row-reuse answer is a synthesis across sources with `[S#]` provenance already
attached, deduplicated against previous answers by `norm_sha256`, and carrying
`claim_edges` so a later contradiction invalidates it automatically. A file
cannot be invalidated by a query; a row can.

**Worked example from tonight.** The question of which named external sources may
be vendored was answered in section 3 by 13 `gh api` calls, 13 license
resolutions, and 5 raw LICENSE reads. That work is now a table. Under
row-reuse, section 3.3 verdicts become `chunks` rows with `kind='claim'`, each
carrying a `citations` row pointing at the exact API path and the fetch date in
`sources.license_evidence`. The next session asking whether developer-roadmap can
be vendored gets `blocked` plus the evidence in one query, instead of re-deriving
it and quite possibly stopping at the misleading GitHub `NOASSERTION` label,
which is the failure this session nearly made.

**Failure mode.** Staleness laundering. A cached answer is a claim about the
world at fetch time and it looks identical to a fresh one. `shadcn-ui/ui` was
pushed 2026-07-30; in six months the cached `live` verdict will be wrong and
nothing about the row will say so. Mitigation belongs in the schema rather than
in a habit: every result carries `sources.fetched_utc` and `sources.liveness`,
and section 7 makes the caller receive a staleness verdict rather than compute
one. The second-order failure is worse and needs naming: a row-reuse answer
written back as a row becomes a source for the next answer, so an error compounds
across generations with each hop looking better cited than the last. Guard:
`sources.kind='derived'` rows are capped at one hop of provenance depth, and a
derived row may never be the sole citation for another derived row.

### 5.2 cache2action

> Implemented in `tools/corpus/cache2action.py`; spec at `docs/specs/2026-08-30-corpus-cache2action.md`.

**Definition.** A retrieval whose result is not prose but an **executable step**:
a command, a patch, a config fragment, or a check, drawn from the `artifacts`
table where `implemented = 1`, together with the `evidence_path` proving it was
actually implemented somewhere rather than merely recommended. The caller runs
it, and the outcome is written back as evidence.

**What it buys over reading a file.** A file tells you what someone wrote. The
`artifacts` table with `implemented` and `evidence_path` tells you what someone
ran, and that distinction is the operator stated priority for repository sources:
which code, libraries, techniques and one-liners were actually implemented, not
the prose around them. A `for` loop described in a blog post and a `for` loop in
a merged file are different evidence classes, and only a schema can hold that
difference. cache2action also closes the loop ADR-0005 demands: a retrieved step
that fails leaves a record, so the corpus learns which of its own advice does not
work on this machine.

**Worked example from tonight.** Section 4.5 needed to know what could embed text
offline on this Windows machine. The measured answer was a probe: `sklearn`,
`sentence_transformers`, `onnxruntime`, `tiktoken` MISSING; `numpy 2.2.6`,
`duckdb 1.1.1`, `polars 1.9.0` present; and `IdiolectEmbedding` already
implemented at `voice_engine.py:90`. Under cache2action that is not a paragraph,
it is an `artifacts` row: `artifact_type='pattern'`,
`name='IdiolectEmbedding'`, `implemented=1`,
`evidence_path='~/.claude/skills/voice-metrics/voice_engine.py:90'`, snippet
being the class docstring. A later session asking how to embed text here gets a
runnable pointer plus the proof it runs, rather than a recommendation to
`pip install sentence-transformers` that would fail.

**Failure mode.** Executing retrieved content is a code-execution path driven by
a datastore, a materially larger blast radius than answering a question wrongly.
Three specific risks. (a) **Context mismatch**: a command correct in its source
repo may be destructive here, and `rm -rf` in a CI script somewhere is a valid
`artifacts` row by every rule proposed above. (b) **Injection**: any index-only
external source is untrusted text, and a crafted snippet in a README is a
prompt-injection and a command-injection vector at once. (c) **Silent drift**:
`implemented=1` was true at `fetched_utc` and upstream may have deleted it.

Mitigations, load-bearing rather than advisory. cache2action never auto-executes;
it returns a proposal that passes through the same permission boundary as any
other command, which under the global contract means the operator approves
anything destructive. `artifacts` rows sourced from
`license_verdict='index_only'` material are marked untrusted and are
display-only. And `evidence_path` must be re-resolvable, so a step whose proof no
longer exists degrades to a suggestion rather than an instruction.

### 5.3 The relationship between the two

row-reuse is read-mostly and its worst outcome is a confidently stale answer.
cache2action is write-capable and its worst outcome is a destructive command with
good provenance. They deserve different gates, and collapsing them into one RAG
feature is the design mistake to avoid. The schema separates them already:
row-reuse reads `chunks` plus `citations`, cache2action reads `artifacts` plus
`evidence_path`.

---

## 6. Ingestion pipeline enforcing the synthesis standard

The standard lives in
`docs/archive/prompt-research-effiefecnt-.md-files-gemini-code-1785450497712.md` (59
lines) and asks for synthesis over summarisation, strict `[S#]` citation,
explicit conflict resolution, density, and no redundancy. Today those are
requests in a prompt, which ADR-0005 identifies as the exact failure class: a
polite request not to push to main is not a control, a pre-push hook is. Section
2.2 shows the request is not being honoured. 4 of 355 files use `[S#]`.

The pipeline turns each directive into a gate. All stages UNEXECUTED.

**Stage 0, normalise.** NFC unicode, repair the 6 known mojibake patterns, map
dash variants, strip trailing whitespace. In-process, never shelling out per file
(section 2.1). Output feeds `norm_text`.

**Stage 1, license and liveness gate.** Before content is read, resolve the
license from the actual LICENSE text and record `license_evidence`. A
`license_verdict='blocked'` source is refused by canonical hostname. A GitHub
`NOASSERTION` label is never accepted as an answer. A source whose
`upstream_mtime` is older than 18 months is admitted with `liveness='stale'` and
may never win a contradiction against a live source.

> **Implemented:** `tools/corpus/license_gate.py` (2026-08-30). Spec: `docs/specs/2026-08-30-corpus-license-gate.md`.

**Stage 2, chunk.** Split on h2/h3 headings, subdivide above ~350 words, classify
`kind`. Code fences become `kind='code'` and feed stage 6.

**Stage 3, dedup, three passes matching the three classes measured in 2.1.**
Pass A: exact `norm_sha256` collision; the second occurrence gets
`status='superseded'` plus a `duplicates` edge, never a delete. Pass B: simhash
Hamming distance under 4, blocked by simhash prefix so this stays linear rather
than the quadratic pair scan used to measure it tonight. Pass C: version
families, detected when two chunks are near-identical but their source filenames
differ by a version or status token such as `DEPLOYED` or `v6.7`. Pass C creates
a `supersedes` edge and keeps BOTH, because the `maryam-v6.7-DEPLOYED` case
proves that discarding one destroys the deployed-versus-draft fact.

**Stage 4, citation gate.** The enforcement of directive 2. A chunk with
`kind='claim'` must produce at least one `citations` row. `[S#]` tags resolve
against the source own reference section; bare URLs count; a claim with neither
is **quarantined**, neither accepted nor discarded, with
`status_reason='uncited'`. Quarantined rows are invisible to retrieval by default
and visible to the backlog query. On the local corpus this would quarantine a
large share of the 205 uncited files on first run, which is the correct outcome:
it converts an invisible 57.7% defect into a visible queue.

**Stage 5, contradiction detection.** Directive 3 asks for conflict resolution.
Three detectors, cheapest first. (a) Numeric: same metric name, different value
outside a tolerance band, which is why `pwc-archive/evaluation-tables` is worth
having as structured data. (b) Negation: high lexical similarity plus a polarity
flip on a small negation lexicon. (c) Recommendation conflict: two `artifacts`
rows with the same `name` and opposite `implemented`, or two chunks recommending
different libraries for one stated purpose. Each writes a `claim_edges` row with
`edge_type='contradicts'` and `resolution=null`. **Nothing is auto-resolved.** An
open contradiction downgrades both sides in ranking and surfaces in the 4.4
query. Implemented in
[specs/2026-08-30-corpus-contradiction-detection.md](../specs/2026-08-30-corpus-contradiction-detection.md).

**Stage 6, artifact extraction.** For repository sources, walk the actual source
tree rather than the README, and set `implemented=1` only with a real
`evidence_path`. A library named in prose and absent from every manifest gets
`implemented=0`. This is the mechanised form of the operator repository rule.
Implemented in
[specs/2026-08-30-corpus-artifact-extraction.md](../specs/2026-08-30-corpus-artifact-extraction.md).

**Stage 7, paper rule.** For `kind='paper'`, admit only `published_utc` in 2026
and record `publisher` from the paper record, never from a search snippet. A
paper whose institution cannot be verified from the paper is quarantined rather
than admitted with a guess. Consequence already visible in 3.2: the entire
`pwc-archive` set is a 2025 snapshot and therefore **fails this rule** except as
a historical baseline. The rule and the dataset are in genuine tension, and the
operator should decide which yields.

**What happens to a failing row.** Nothing is deleted. Every failure is a status
plus a reason plus a line in `state/corpus-ingest.jsonl`. Deletion would make the
defect rate unmeasurable, and an unmeasurable defect rate is how a corpus quietly
rots. Quarantine is reversible; deletion is not.

---

## 7. Retrieval

> **Implemented:** `tools/corpus/retrieve.py` (2026-08-30). Spec: `docs/specs/2026-08-30-corpus-unified-retrieval.md`.

### 7.1 What a query looks like

```
corpus query "offline text embedding on windows" \
  --kind code,pattern --implemented --max-age 180d --k 8
```

Path: FTS5 BM25 over `chunks_fts` restricted to `status='accepted'`, then rerank
the top ~200 by cosine against the `.npy` sidecar, then apply the requested
facets. FTS5 first and vectors second is deliberate, given the lexical embedder
limits named in 4.5.

### 7.2 What it returns

Each result is a record, not a paragraph:

```json
{
  "chunk_id": "c9f2...",
  "text": "...",
  "kind": "pattern",
  "source": {"uri": "~/.claude/skills/voice-metrics/voice_engine.py",
             "license_verdict": "vendor", "liveness": "live",
             "fetched_utc": "2026-07-31T...", "upstream_mtime": "2026-07-27T..."},
  "citations": [{"target_uri": "...", "verified": true}],
  "contradicted_by": [],
  "artifacts": [{"name": "IdiolectEmbedding", "implemented": 1,
                 "evidence_path": "voice_engine.py:90"}],
  "staleness": {"verdict": "fresh", "age_days": 4, "reasons": []},
  "trust": "trusted"
}
```

`trust` is `trusted` for vendor-verdict and local sources and `untrusted` for
index-only external material, which is what closes the 5.2 injection path.

### 7.3 How a caller knows a result is stale

Staleness is computed and returned, never left for the caller to infer. Four
signals, and the verdict is the worst of them:

1. **Source age**: `now - sources.upstream_mtime`. Over 18 months gives `stale`;
   an archived upstream gives `archived`.
2. **Fetch age**: `now - sources.fetched_utc`. This catches the case where
   upstream moved and we have not looked. Over 90 days gives `unverified`.
3. **Local file drift**: for local sources, re-hash the file. A `content_sha256`
   mismatch gives `drifted`, the strongest signal, and it is cheap because the
   whole local corpus is 5.43 MiB.
4. **Vector generation mismatch**: if `corpus-vec.json` generation does not match
   `corpus_meta`, the rerank stage is skipped and every result is tagged
   `rerank_unavailable` rather than silently returning worse rankings.

The rule behind all four: a result that cannot prove its freshness says so in the
payload. That is the retrieval-side form of the calibrated-claims rule and the
direct answer to the 5.1 staleness-laundering failure mode.

---

## 8. What was deliberately not proposed

- **No new vector database.** 25,000 chunks does not justify FAISS, Chroma,
  LanceDB, or pgvector. A 25.6 MB numpy matvec is under 10 ms. Adding a service
  or a native dependency for that is novelty with no measured advantage.
- **No neural embedding model, yet.** Not because it would not be better, but
  because installing one is outside tonight scope and because the honest sequence
  is to run the lexical version and measure recall failures before spending the
  dependency. The gap is named in 4.5 rather than hidden.
- **No extension of intent-control-plane schema.** Different aggregate, different
  lifecycle, and coupling corpus growth to a packaged subproject with three
  known-failing Windows tests is a cost with no benefit. Patterns are reused, the
  database is not shared.
- **No DuckDB or Polars as the store.** Both are installed and both are right for
  batch dedup and contradiction passes. Neither gives an append-only audit trail,
  and the DuckDB exclusive file lock would collide with parallel sessions.
- **No model-based summarisation at ingestion.** The synthesis standard is
  tempting to satisfy by calling a model per document. That would cost money per
  ingest, make ingestion non-deterministic and non-reproducible, and generate
  exactly the uncited prose the corpus exists to exclude. Synthesis belongs at
  query time in a row-reuse answer whose citations are checkable, not at ingest
  time where nobody sees it happen.
- **No auto-resolution of contradictions.** Detection is mechanical, adjudication
  is judgement, and an open edge is the honest state.
- **No deletion of any local file.** The 54 exact duplicates are a real cleanup
  opportunity and a separate decision. This design supersedes rows inside the
  store and touches nothing on disk.
- **No Kaggle integration**, for the credential reason in 3.2.
- **No crawler.** `awesome-scalability` and `applied-ml` are bibliographies of
  external blog posts, and following those links is a fetch-the-internet project
  with its own licensing and volume problems. Store the links, stop there.
- **No changes to any existing file**, per the collision constraint tonight. The
  stale seed names, the misnamed nexus file, and the 6 mojibake filenames are
  reported here and left in place.

---

## 9. Migration path, in ingestion units

S1 = 25 min, S2 = 45, S3 = 60, S4 = 90, S5 = half day, S6 = full day. Every step
is UNEXECUTED. Steps 1 to 4 deliver a working local corpus. External sources do
not start until step 6, because the local corpus is the thing with 782,617
measured words and no index.

| Step | Unit | Deliverable | Done when |
|---|---|---|---|
| 1 | S2 | `state/corpus.db` from the 4.3 DDL plus its selftest; stage 0 normaliser and stage 2 chunker over the 355 local files | `chunks` holds roughly 7,336 rows and the selftest exits 0 |
| 2 | S3 | Stage 3 dedup, all three passes, with simhash blocking | The 54 exact duplicates are `superseded` with `duplicates` edges, and the `maryam` family keeps both rows with a `supersedes` edge |
| 3 | S3 | Stage 4 citation gate plus the two 4.4 defect queries wired as a check | The uncited query returns a number, and that number is a tracked backlog rather than a surprise |
| 4 | S2 | FTS5 index and a `corpus query` CLI returning the 7.2 record shape including staleness | A query for a known local string returns it with a staleness verdict |
| 5 | S3 | `IdiolectEmbedding` fitted over the corpus, `.npy` sidecar plus generation counter, rerank stage | A generation mismatch produces `rerank_unavailable` rather than silent degradation |
| 6 | S4 | Stage 1 license gate plus ingestion of the 8 vendor-verdict sources; hostname block for developer-roadmap | The blocked source is refused by a test, not by a policy sentence |
| 7 | S4 | Stage 5 contradiction detection, all three detectors, over local plus vendored | Open contradictions are rows, and retrieval downranks both sides |
| 8 | S3 | Stage 6 artifact extraction with `implemented` and `evidence_path` | The 5.2 worked example exists as a real row |
| 9 | S5 | row-reuse write-back with the one-hop provenance cap | A derived row cannot be the sole citation for another derived row, enforced by a test |
| 10 | S5 | cache2action proposal path, trust flags, no auto-execution | An index-only-sourced artifact is display-only, enforced by a test |

Running every step is roughly two full days of ingestion units. Steps 1 to 4
alone are S2+S3+S3+S2, under four hours, and they are the ones that convert
782,617 unindexed words into something queryable.

**Recommended decision point: approve steps 1 to 4, then re-measure before
committing to 5 through 10.** The later steps assume the earlier ones find what
this document predicts they will find, and that assumption should be tested
rather than trusted.
