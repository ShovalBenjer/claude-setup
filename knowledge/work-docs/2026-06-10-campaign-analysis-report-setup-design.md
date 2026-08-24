# Campaign-Analysis Report Setup — Decision-Grade Design

Date: 2026-06-10
Owner: Shoval
Project: `/home/shovalbe/projects/campaign-analysis`
Anchor of record: `docs/CJA-REQUIREMENT-OF-RECORD.md` (12 questions, 4-row answer contract)

---

## Bottom line

The in-project Claude does not fabricate because the model is weak. It fabricates because the **architecture forces it to**: a 146-file parquet/xlsx corpus does not fit a context window, so the agent either overflows and guesses, or stops and labels a section PENDING. The current canonical builder (`seekapa_deliverable.py`) makes this worse — it is wired to the **deprecated, leakage-unsafe `scores_v2` corpus**, covers only 6 of 12 questions, never tags ACTIONABLE/DIRECTIONAL, never attaches provenance, and never raises an error when a section is missing — it just ships an incomplete workbook.

The fix is **query-not-load**: the agent never reads raw files into context. It issues SQL to DuckDB over a catalog, fills a fixed per-question template from real query results, and a no-mock gate + completeness/provenance critic blocks anything ungrounded. Every component reuses code already in the repo. **No new Azure resource, no new BI SaaS, no new MCP server.**

Build order (each is a prerequisite for the next):
1. Fix the corpus + PII (P0, blocks correctness) — `scores_v2` → `scores_v3`, mask `agents.csv`.
2. DuckDB catalog + metric dictionary (query-not-load engine).
3. Per-question fan-out into the 4-row CJA template.
4. No-mock gate + completeness/provenance critic.
5. Prove it on 2-3 of Liron's 12 questions end-to-end.

---

## 1. Root cause recap — why output is partial / mocked / unexplained today

Verified against source (line numbers from the live files, 2026-06-10):

**R1 — Corpus is wrong (P0, contaminates every number).**
`scripts/report/seekapa_deliverable.py:31` globs `outputs/2026-06-06/seekapa/scores_v2/part_*.parquet`. `scores_v2` is leakage-unsafe and the CJA anchor explicitly deprecates it. The canonical corpus is `scores_v3` (`outputs/2026-06-07/seekapa/scores_v3/`, **verified 4,287 rows × 119 cols, 22 parts**). `scores_v2` has 5,587 rows. The shipped `outputs/2026-06-09/deliverable/Seekapa_Call_QA.xlsx` 00_README tab still declares `Cohort: Seekapa scored sample (scores_v2)` (`seekapa_deliverable.py:166`). `build_brand_report.py:187` reads the same v2 glob. **Every headline in the shipped deliverable is computed from a contaminated set.**

**R2 — Mocked / frozen constants that silently go stale.**
- `build_brand_report.py:128` — AXIA prior-7 fallback is a frozen literal `MislabelStats(n_answered=12443, n_aligned=12443, n_mislabel=4634)`. If the DB is unreachable this sentinel propagates into CI deltas with no signal.
- `build_brand_report.py:230` — `"$3,072"` avg net deposit per FTD is a string literal. It is derivable at runtime (mean `net_deposit` over `is_ftd==True` in `master_frame` = 3,072 today) but is never computed, so it goes wrong silently if the cohort shifts.

**R3 — Deferred = absent.** `build_brand_report.py:248` PENDING block defers speed-to-lead, source-at-scale, and behaviors-at-scale "for integrity." These are honest labels, not fakes — but they are 3 of the 12 questions, and PENDING is a UI element, not a backlog. They never get built because nothing forces them.

**R4 — No completeness contract.** `seekapa_deliverable.py` covers 6 of 12 questions (call quality + status trust). Q1/Q2/Q3/Q4/Q5/Q6/Q8/Q11/Q12 have no sheet. The builder never raises — an incomplete workbook is indistinguishable from a complete one. The CJA anchor confirms Q3/Q4/Q5/Q7/Q9/Q10 are answerable **now** from telephony + `scores_v3`; Q1/Q2/Q6/Q8/Q11 need the CRM revenue join; Q12 is DIRECTIONAL (model not built).

**R5 — No provenance, no decision contract.** `scripts/lib/provenance.py` implements `Claim` + `cell_with_provenance()`, but **grep finds zero callers** in any report builder. Every headline is a plain `ws.cell()` with no "how did you get this" hover. The CJA 4-row contract (Headline+tag / How-derived / What-it-means / one owned dated Action — anchor §4 lines 88-91) is implemented in **no** worksheet; ACTIONABLE/DIRECTIONAL tagging exists in no column.

**R6 — PII at the read boundary (P0, compliance).** `agents.csv` (409 rows: `first_name`, `last_name`, `email`) is read raw into the `agent_name` column. No pseudonymization. The anchor requires masking before any output.

**R7 — Builder churn.** ~8 competing builders (`build_liron_final_xlsx`, `build_liron_complete`, `build_liron_dashboard_v2`, `build_unified_liron_dashboard`, `build_liron_unified`, `build_clean_liron`, `build_xlsx_workbook`, `seekapa_deliverable`, `build_brand_report`). The anchor names `seekapa_deliverable.py` the ONE canonical builder; nothing enforces it, so the next session forks a 9th.

Underlying mechanism (research-backed): a single agent asked to **retrieve and narrate in one pass** over a corpus larger than its window will fill retrieval gaps from parametric memory. The 2026 dbt benchmark: raw text-to-SQL 64-90% correct vs 98-100% when grounded through a semantic layer — and the semantic layer **errors** instead of returning a wrong number silently.

---

## 2. Proposed report-generation pipeline

One pipeline, six components. Each maps to a concrete artifact and names what it **reuses** (no new resource).

### (a) DuckDB / Polars catalog + metrics dictionary

**Artifact:** `scripts/lib/catalog.py` (new, ~120 lines) producing `outputs/<date>/_catalog.json` + a metric dict `scripts/lib/metrics.py` (new).

- **Catalog:** one-time scan of the canonical inputs (`scores_v3/`, `master_frame.parquet`, `scoring_sample_manifest.parquet`, `bronze_cdr/`, `bronze_windsor_v2/`, `status_audit_summary.parquet`). Per file: schema, dtypes, rowcount, null rate, top-5 distinct for categoricals. Writes a ~5K-token JSON that is the **only** thing the agent loads at session start. The agent never re-scans the corpus.
- **Metric dictionary:** a Python dict of named query functions — `cpl_by_source()`, `ftd_rate_by_source()`, `speed_to_lead_curve()`, `objection_taxonomy()`, `status_accuracy()`, etc. — one per CJA metric. Each returns a parametrized DuckDB SQL string. The LLM's job shrinks to picking `(metric, dimension, filter)`; it never writes a raw `GROUP BY/JOIN`. This is the "wrong-join elimination" surface.

**Query-not-load loop:** `duckdb.connect(':memory:')` → `CREATE VIEW v_scores AS SELECT * FROM read_parquet('<v3 glob>')` → run metric SQL → return aggregated rows (<50 lines) into context. Large intermediates stay as named DuckDB tables / parquet; the agent gets a memory pointer (rowcount + schema + 5-row preview), never the full set.

**Reuses:**
- DuckDB in-memory views over parquet — already proven in `scripts/gold/build_liron_final_xlsx.py` (`duckdb.connect(':memory:')` + `read_parquet` glob views for all 11 sheets).
- Polars reads already in `behavior_correlation.py` and `build_brand_report.py`.
- `scripts/lib/manifest.py` `RunManifest` (input sha256 + rowcount) is the catalog's reproducibility spine — the catalog opens a manifest stage.
- Statistical primitives: `scripts/live_report/trust.py` (`wilson_ci`, `two_proportion_test`, `aggregate`) for every rate's 95% CI.

### (b) Encoded Liron-grade report template

**Artifact:** `scripts/report/templates/cja_workbook.py` (new) — the 12-sheet skeleton, encoding the established format so structure is not a model choice.

Encodes the verified house style from `funnel-analysis-v3-FINAL.xlsx` / `build_liron_final_xlsx.py`: `HDR_FILL=#305496`, `TITLE_FILL=#1F4E78`, `DANGER_FILL=#F4CCCC`, `GOOD_FILL=#D9EAD3`; DANGER conditional formatting at ≥10%; human-readable headers; quote columns truncated to 280 chars; a `Cover` tab with computed headlines + method + cohort size + run date + rubric sha256; `ACC_Master` + `Call_Master` exhibit sheets. Each of the 12 answer sheets is pre-shaped to the **CJA 4-row contract**: row 1 Headline + ACTIONABLE/DIRECTIONAL tag; row 2 How-derived (source path + filter + SQL); row 3 What-it-means (one business sentence); row 4 Action (owned, named, dated). Empty contract rows are a render error, not a silent gap.

**Reuses:** `write_df_to_sheet()` helper + multi-parquet view pattern from `build_liron_final_xlsx.py`; openpyxl styling constants already in that file.

### (c) Section / question fan-out

**Artifact:** `scripts/report/orchestrator.py` (new) — supervisor → 12 sub-agent calls → assemble.

Supervisor reads the catalog + the 12 questions. For each question it spawns a **focused** sub-agent call (parallel where independent, e.g. Q3 funnel vs Q10 language; sequential only where one feeds another). Each sub-agent gets: the relevant catalog slice + question text + a strict output schema. It runs its DuckDB metric query and returns one compact JSON: `{question_id, headline, tag(ACTIONABLE|DIRECTIONAL), how_derived(sql+path), what_it_means, action(owner,date), supporting_numbers:[{value, unit, sql_provenance, wilson_ci}], confidence, gaps}`. Fan-out bounds each question's context to catalog + one result set — fabrication becomes structurally hard. **`sql_provenance` is required, not optional**: any `supporting_numbers` entry with null provenance is auto-rejected before assembly.

Each sub-agent result is written to `artifacts/run_<ts>/q<N>.json` immediately, with a `run_state.json` (DONE/PENDING/FAILED). Interruptions resume — DONE questions are skipped, only PENDING/FAILED re-run. Final assembly reads the q-files from disk, never in-memory state.

**Reuses:** Azure AI Foundry Python SDK (`azure-ai-projects`) already in project for sub-agent calls; `behavior_correlation.py` directly for Q9 (objection taxonomy) and Q7 (message-match) — already leakage-safe, confounder-adjusted, BH-FDR; `cuts.py::ftd_by_source()` + `outcome_ladder.py::classify_account()` for Q1/funnel; `status_audit_summary.parquet` read directly for Q8 (already computed — cite, don't recompute).

### (d) No-mock / no-placeholder gate

**Artifact:** `scripts/lib/nomock_gate.py` (new) — Pydantic schema + validators, run **before** assembly.

A Pydantic `ReportSection` model, one field per question. Validators: `min_length` on narrative (rejects one-liners); reject `PLACEHOLDER_PATTERNS = {TODO, TBD, N/A, placeholder, coming soon, [insert, …, see above, not available, PENDING}`; reject any section without ≥1 `[Q##]` provenance tag; reject any hardcoded sentinel by checking that each headline number appears in its sub-agent's executed query result (within ±0.1% for rounded percentages). On `ValidationError`, feed the message back to the sub-agent and retry up to 3×. After 3 failures the section is flagged P0-incomplete and **the report is not delivered**. This is what kills R2 (`$3,072` / `12443` constants) and R3 (PENDING-as-stub).

**Reuses:** Pydantic (standard dep); `provenance.py::Claim.confidence` (the `H/M/L` field that exists but is never used) becomes the section confidence; metric dict results are the ground truth the validator checks against.

### (e) Completeness + provenance critic

**Artifact:** `scripts/lib/critic.py` (new) — a separate Foundry call (one prompt, ~200 lines), MACE-style Planner→Executor→Verifier.

Receives the 12 JSON objects. For every claimed number: classify **grounded** (provenance matches query output) / **ungrounded** (no provenance) / **contradicted** (provenance exists, value mismatches) / **complementary** (narrative with no number, acceptable if flagged). Ungrounded or contradicted → bounded regeneration (max 2 retries) for that one sub-agent. Still unresolved → section renders `[DATA GAP — query returned no rows for filter X]`, never a fabricated number. A separate verifier (not the generator) acts as the fact-checker, because a single LLM is biased toward its own output. Provenance appendix is auto-rendered from the q-file `sql_provenance` fields — Liron can trace any number to its exact SQL + parquet path + timestamp. Optional CI bind: `deepeval` FaithfulnessMetric (≥0.75) or Azure `GroundednessEvaluator` (≥4/5) over the SQL-result blocks as a pytest gate — both run against the existing `brn-azai` Foundry endpoint, no new credential.

**Reuses:** Foundry endpoint already wired; `provenance.py::cell_with_provenance()` wired (finally) to every headline cell so the appendix is real; manifest as the audit spine.

### (f) LTMD framing

**Artifact:** the row-4 `Action` line of every sheet + a `Cover` LTMD summary block.

Every question ends in ONE owned (rep/desk/source named), dated, dollar-valued next step — the gate that separates a decision from a dashboard dump. The `/LTMD` skill is the pre-ship reviewer: run it on the assembled workbook; any answer that ends in a plot instead of an action is BOMB-THE-FORMAT and bounced back to its sub-agent.

**Reuses:** the `LTMD` skill (already installed); the CJA anchor §4 contract is the spec.

### Pipeline flow

```
catalog.py  ──►  metrics.py (12 metric fns over scores_v3 / master / cdr / windsor)
     │
     ▼
orchestrator.py  ──►  12× sub-agent (focused, parallel)  ──►  artifacts/run_<ts>/q<N>.json
     │                        │ each: real SQL → headline+tag+how+means+action+provenance+CI
     ▼                        ▼
nomock_gate.py (Pydantic, retry 3×)  ──►  critic.py (MACE, retry 2×, grounded/contradicted/gap)
     │
     ▼
cja_workbook.py (12 sheets, CJA 4-row contract, provenance hover, Wilson CI)
     │
     ▼
/LTMD review  ──►  ship  OR  block-with-structured-error (failing section + claim)
```

A section reaches Liron ONLY IF: all 12 Pydantic fields pass (0 placeholders, ≥1 provenance tag, headline number = query result), AND the critic produces 0 ungrounded/contradicted claims (or fixes are re-verified), AND the LTMD action line is present. Otherwise the pipeline emits a structured error naming the failing section and claim — never a partial report.

---

## 3. Reuses vs replaces the current builders

| Current asset | Verdict | What happens |
|---|---|---|
| `seekapa_deliverable.py` | **EXTEND (stays canonical)** | The anchor names it the ONE builder. Wrap it with the pipeline: (1) glob `scores_v2`→`scores_v3` (`:31`), MANIFEST→2026-06-07 region; (2) add `agents.csv` pseudonym map at the read boundary; (3) call metric dict + 4-row contract instead of 6 ad-hoc sheets; (4) wire `cell_with_provenance()`. Do not fork a 9th builder. |
| `build_brand_report.py` | **REPLACE the mocked internals** | Kill the frozen `MislabelStats` (`:128`) and `$3,072` literal (`:230`) — both derived at runtime from the parquet cache. Repoint v2 glob (`:187`) to v3. The HTML shell + PENDING-as-first-class-UI pattern is reused; PENDING sections become real query results or explicit `[DATA GAP]`. |
| `behavior_correlation.py` | **REUSE as-is** | Already leakage-safe, confounder-adjusted, BH-FDR. Becomes the metric fn for Q9 + Q7. Only change: it currently reads the v2 glob via its callers — pass it the v3 path. |
| `provenance.py` | **REUSE (finally wire it)** | `Claim` + `cell_with_provenance()` exist; the pipeline makes them mandatory on every headline cell. |
| `manifest.py` | **REUSE** | `RunManifest` becomes the catalog + run audit spine. |
| `build_liron_final_xlsx.py` | **HARVEST + deprecate** | Its DuckDB view pattern + `write_df_to_sheet()` + styling constants seed `cja_workbook.py`. After harvest, mark deprecated. |
| `cuts.py`, `outcome_ladder.py`, `trust.py` | **REUSE** | Direct metric fns for funnel / FTD-by-source / Wilson CI. |
| `run_daily.py` | **REUSE as scheduler** | Already defaults to `scores_v3`; becomes the autonomous daily backbone once the pipeline is the report step. |
| 6 other `build_liron_*` builders | **DEPRECATE** | Add a one-line guard / README note: the canonical path is `seekapa_deliverable.py` + pipeline. Prevents the 9th-builder fork. |

Net: **nothing rewritten from scratch.** New code = 6 thin glue modules (catalog, metrics, orchestrator, nomock_gate, critic, cja_workbook template); everything analytical is reused.

---

## 4. Skills to build and how they compose

These are project-local skills (`.claude/skills/` in campaign-analysis) the in-project Claude invokes; each maps to one pipeline component so the agent's behavior is enforced, not hoped-for.

1. **`requirement-anchor`** — loads `docs/CJA-REQUIREMENT-OF-RECORD.md` + `_catalog.json` at session start; refuses to answer a question not in the 12, and refuses any question whose required data is absent from the catalog (emits the honest-status mapping: Q3/4/5/7/9/10 now, Q1/2/6/8/11 partial-needs-CRM, Q12 DIRECTIONAL). **Composes into:** the orchestrator's planning step.

2. **`context-bounded-analyst`** — the query-not-load enforcer. Every numeric claim must come from a `duckdb.execute()` call returning ≤500 rows; SELECT-only; no `SELECT *` without WHERE/LIMIT; large results become memory pointers. **Composes into:** every sub-agent call (2c) over the metric dict (2a).

3. **`decision-grade-linter`** — encodes the CJA 4-row contract + LTMD gate. Lints each section: present Headline+tag, How-derived(sql+path), What-it-means, owned-dated-dollar Action. Missing any → fail. **Composes into:** the no-mock gate (2d) and final `/LTMD` review (2f).

4. **`pii-scrubber`** — reads `agents.csv`, builds a stable pseudonym map (`Agent-042`), applies it at every join boundary before any sheet/JSON write; refuses to emit raw `first_name/last_name/email`. **Composes into:** the read boundary inside the orchestrator, ahead of all sub-agents.

5. **`no-mock-gate`** — the runtime twin of `nomock_gate.py`: scans candidate output for placeholder patterns AND for any number not traceable to an executed query (catches frozen constants like `$3,072`). Blocks ship; returns the failing claim. **Composes into:** the gate (2d) + critic (2e).

Composition: `requirement-anchor` plans → `pii-scrubber` masks → `context-bounded-analyst` answers each question with real SQL → `decision-grade-linter` + `no-mock-gate` block anything incomplete or ungrounded → critic verifies → `/LTMD` final review. Each skill is the human-readable contract; the `.py` modules are the deterministic enforcement. Skills make the agent **do it autonomously**; modules make it **impossible to skip**.

---

## 5. Prove-it validation

Run the pipeline end-to-end on 3 of Liron's 12 questions before building all 12 — pick the cheapest fully-answerable-now questions so the proof is unambiguous (anchor confirms these need only telephony + `scores_v3`):

- **Q3 — answer rate** (`bronze_cdr/` 63 parts; ANSWER-only join to manifest). Pure CDR, no CRM dependency.
- **Q9 — objection taxonomy** (`scores_v3` L07 frequency + handling score, via `behavior_correlation.py`). Pure scores, reuses an existing leakage-safe engine.
- **Q10 — language-barrier false-flag** (`scores_v3` L09/lang + `inferred_status`; validate against dialect, per anchor §16.5 — 5/12 pilot LB labels were false).

For each, the proof must show the full chain, not just a number:
1. Sub-agent issued real DuckDB SQL (printed) → result rows (printed).
2. `q<N>.json` on disk with `sql_provenance` non-null + Wilson CI.
3. Workbook sheet renders all 4 contract rows: Headline+ACTIONABLE/DIRECTIONAL, How-derived (path+SQL), What-it-means, owned-dated Action.
4. No-mock gate: deliberately inject a frozen constant into one answer → gate **rejects** it (negative test). Then remove → passes.
5. Critic: deliberately corrupt one `sql_provenance` value → critic flags **contradicted** and bounces (negative test).
6. Provenance hover present on every headline cell.

Acceptance: 3/3 sheets complete + sourced + 4-row + CI; both negative tests fire. If that holds, fan out to the remaining 9 (Q7 now; Q1/Q2/Q6/Q8/Q11 once the CRM/Yasha + Windsor joins land; Q12 stays DIRECTIONAL, no placeholder sheet). TDD discipline: write the gate negative-tests RED before the gate code (RED→GREEN per behavior).

---

## 6. Ranked next actions (effort / impact)

| # | Action | Effort | Impact | Reuses |
|---|---|---|---|---|
| 1 | **P0 corpus fix:** `scores_v2`→`scores_v3` in `seekapa_deliverable.py:31` + `build_brand_report.py:187`; MANIFEST/MASTER to 2026-06-07 region | XS (1 line ×3) | **Critical** — every shipped number is currently leakage-contaminated | existing globs |
| 2 | **P0 PII:** `pii-scrubber` skill + pseudonym map at read boundary | S | **Critical** — compliance; raw names in shipped xlsx | `agents.csv` |
| 3 | **De-mock:** derive `$3,072` (`:230`) + `MislabelStats` (`:128`) at runtime from parquet cache | S | High — kills silent staleness | `master_frame`, trust.py |
| 4 | **Catalog + metric dict** (`catalog.py`, `metrics.py`) | M | High — the query-not-load engine; ends overflow fabrication | `build_liron_final_xlsx` DuckDB pattern, `trust.py`, `cuts.py`, `outcome_ladder.py` |
| 5 | **No-mock gate + decision-grade linter** (`nomock_gate.py` + skills) | M | High — blocks incomplete/ungrounded ship | Pydantic, `provenance.py` |
| 6 | **Prove-it on Q3/Q9/Q10** end-to-end | M | High — de-risks before full fan-out | `behavior_correlation.py`, `bronze_cdr` |
| 7 | **Fan-out orchestrator + 4-row template** (`orchestrator.py`, `cja_workbook.py`) | L | High — fills the 6 missing questions, enforces format | Foundry SDK, `build_liron_final_xlsx` helpers |
| 8 | **Critic + provenance appendix** (`critic.py`, wire `cell_with_provenance`) | M | Medium-High — semantic faithfulness + traceability | Foundry endpoint, `provenance.py` |
| 9 | **Wire Windsor spend** (`bronze_windsor_v2/` join on `client_source`/`campaign`) for Q1/Q2/Q11 partial | M | Medium — unlocks partial ROAS/cost ladder | on-disk parquets, `master_frame` |
| 10 | **Deprecate 6 redundant builders** (guard + README) | XS | Medium — stops the 9th-builder fork | — |
| 11 | **Autonomous daily** via `run_daily.py` once pipeline is the report step | S | Medium — hands-off runs | `run_daily.py` (already v3) |

Do 1-3 today (XS/S, P0). 4-6 next (the engine + proof). 7-11 after the proof holds.

---

## 7. References (deduplicated)

In-repo (verified 2026-06-10):
- `docs/CJA-REQUIREMENT-OF-RECORD.md` — 12 questions; 4-row answer contract (§4 lines 88-91); honest status (lines 54-55); ACTIONABLE/DIRECTIONAL (line 27); Q12 DIRECTIONAL (line 52); Windsor self-report caveat (line 76); LB false-flag (line 80).
- `scripts/report/seekapa_deliverable.py` — canonical builder; v2 glob `:31`; v2 README `:166`.
- `scripts/live_report/build_brand_report.py` — frozen `MislabelStats` `:128`; `$3,072` literal `:230`; v2 glob `:187`; PENDING block `:248`.
- `scripts/offline_base/behavior_correlation.py` — leakage-safe behavior→FTD engine.
- `scripts/lib/provenance.py` — `Claim` + `cell_with_provenance()` (zero callers today).
- `scripts/lib/manifest.py` — `RunManifest` ledger.
- `scripts/gold/build_liron_final_xlsx.py` — DuckDB view pattern + `write_df_to_sheet()` + style constants.
- `scripts/offline_base/cuts.py`, `outcome_ladder.py`; `scripts/live_report/trust.py`; `scripts/pipeline/run_daily.py`.
- Canonical data: `outputs/2026-06-07/seekapa/scores_v3/` (4,287 × 119, 22 parts — verified); `outputs/2026-06-06/seekapa/master_frame.parquet` (199,102 × 33); `outputs/2026-06-07/validity/scoring_sample_manifest.parquet`; `outputs/2026-05-23/bronze_cdr/` (63 parts); `outputs/2026-05-23/bronze_windsor_v2/` (5 connectors); `outputs/2026-06-07/validity_v3/status_audit_summary.parquet`.

External (SOTA 2026, deduped to load-bearing):
- DuckDB query-not-load + semantic layer: MotherDuck analytics-agent workshop; dbt "Semantic Layer vs Text-to-SQL 2026 benchmark" (64-90% raw vs 98-100% grounded; errors not silent wrong answers); MetricFlow open-source governed metrics.
- Report-as-code / structural completeness: Quarto parameterized reports (Jupyter engine, 2025).
- Faithfulness / completeness / provenance gates: Pydantic AI structured output + retry-with-error; DeepEval FaithfulnessMetric; Azure `GroundednessEvaluator`; MACE multi-agent tabular claim verification (Planner→Executor→Verifier); GSAR typed grounding (grounded/ungrounded/contradicted); tool-receipts provenance binding.
- Context bounding: catalog/manifest pattern (AgentAda offline semantic catalog; Discovery Agents); memory-pointer pattern for large intermediates; supervisor→fan-out hierarchical RAG (84.5% vs 62.8% flat); Anthropic "Building effective agents" (multi-agent when task exceeds one window).
