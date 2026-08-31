---
name: context-bounded-analyst
description: >
  Data analysis over large files/datasets using DuckDB/Polars lazy queries.
  Builds a catalog + metrics dictionary; returns compact sourced answers
  (number + provenance) — never loads full tables into context.
  The fix for partial/mocked reports over large data.
  Triggers: /analyst, "answer over the data", "query dont load",
  "analyze this dataset", "run a query", large-dataset analysis requests.
  SKIP: if the dataset fits in-memory < 5 MB and user explicitly asks to load it;
  if the question is about code, not data.
---

# context-bounded-analyst

Answer questions over large data without blowing context. Every number returned
must be accompanied by its source (file path + query). No full-table dumps, ever.

## When to activate

- User points at a CSV/Parquet/JSONL/SQLite file and asks a data question.
- Dataset is unknown size or visibly large (> a few MB, many rows, wide schema).
- Previous attempt produced a "loaded 120k rows into context" or mocked/partial answer.
- Trigger phrases: `/analyst`, "answer over the data", "query dont load",
  "analyze this dataset", "don't load the whole thing".

## When to skip

- Dataset < ~5 MB AND user explicitly wants the raw rows for inspection.
- Question is about code or config, not data values.

## Protocol

### Phase 0 — locate and fingerprint (never read rows)

```bash
# file size + row count without loading
mise exec -- fd -e csv -e parquet -e jsonl . <search_root> | head -20

# For CSV — row count + schema only
duckdb -c "DESCRIBE SELECT * FROM read_csv_auto('<file>', sample_size=1000);"
duckdb -c "SELECT COUNT(*) AS n_rows FROM read_csv_auto('<file>');"

# For Parquet
duckdb -c "DESCRIBE SELECT * FROM read_parquet('<file>');"
duckdb -c "SELECT COUNT(*) FROM read_parquet('<file>');"

# For SQLite
duckdb -c "INSTALL sqlite; LOAD sqlite; SELECT name FROM sqlite_master WHERE type='table';" <db>
```

Emit: file path, format, row count, column names + inferred types.
Do NOT emit sample rows unless explicitly asked.

### Phase 1 — build metrics dictionary

For each relevant table/file, run aggregates only:

```python
# Polars lazy (preferred for multi-file or very large)
import polars as pl
lf = pl.scan_csv("<file>")          # or scan_parquet / scan_ndjson
print(lf.schema)
print(lf.describe())                 # aggregate stats, not rows

# Or DuckDB for ad-hoc SQL
import duckdb
con = duckdb.connect()
con.execute("SUMMARIZE SELECT * FROM read_csv_auto('<file>')").df()
```

Capture to a local dict `catalog[table] = {col: {dtype, n_nulls, min, max, n_distinct}}`.
Report this dictionary to the user — it fits in context; a 120k-row CSV does not.

### Phase 2 — answer questions via targeted queries

Each answer must follow this template:

> **[metric]**: `<value>` — source: `<file_path>`, query: `<one-liner SQL or expression>`

Example:
> **avg_deal_value**: `$4,230` — source: `data/crm_export.csv`, query:
> `SELECT AVG(deal_value) FROM read_csv_auto('data/crm_export.csv') WHERE status='closed'`

Rules:
- Push filters/aggregations into DuckDB/Polars — never `collect()` before filtering.
- For Polars lazy chains always end with `.collect()` only after all predicates.
- Return at most 20 representative rows when the user explicitly asks for "examples".
  Use `LIMIT 20` or `.head(20)`. State the limit in the output.
- For groupby results, show top-10 by count or value unless user says otherwise.

### Phase 3 — PII/secret guard

Before running any query over unknown data:

```bash
# Check column names for obvious PII signals — schema only, no values
duckdb -c "DESCRIBE SELECT * FROM read_csv_auto('<file>', sample_size=0);"
```

If columns like `email`, `phone`, `id_number`, `password`, `token`, `key` appear:
- Report presence: "Column `email` detected — treating as PII. Will not echo values."
- Filter those columns out of any `SELECT *` queries.
- Never emit raw PII values into context or output.

### Phase 4 — optional: persist catalog

If the session involves repeated queries over the same data, persist the catalog:

```bash
duckdb data/catalog.duckdb -c "
  CREATE TABLE IF NOT EXISTS _meta AS
  SELECT '<table>' AS tbl, column_name, data_type, null_percentage
  FROM (SUMMARIZE SELECT * FROM read_csv_auto('<file>'));
"
```

Then all subsequent queries hit the DuckDB file instead of re-scanning the source.

## Output format

```
CATALOG
-------
file: <path>
rows: <n>  cols: <n>
columns: col1 (type), col2 (type), ...
PII flags: [none | col_name, ...]

ANSWER
------
<question rephrased one line>
→ <value>  |  source: <file>  |  query: <sql>
```

Keep total output under ~40 lines per question. If the answer requires a table,
show max 10 rows + "... N more rows omitted".

## Tool preference

| Task | Tool |
|---|---|
| Schema + aggregates | DuckDB `SUMMARIZE` or `DESCRIBE` |
| Multi-file scan | Polars `scan_parquet` / `scan_csv` (LazyFrame) |
| In-place CSV transforms | `mlr --ojson` via `mise exec` |
| File discovery | `mise exec -- fd -e csv -e parquet` |
| Quick ad-hoc SQL | `duckdb -c "..."` (no Python overhead) |

Never use `pandas.read_csv` on a file whose size is unknown — it loads everything.
Use `pd.read_csv(..., nrows=5)` only for schema sniffing when DuckDB isn't available.

## Failure modes

- **Schema inference fails on messy CSV** — pass `sample_size=10000` and `ignore_errors=true` to `read_csv_auto`.
- **DuckDB not installed** — `uv tool install duckdb` or `mise exec -- python -m duckdb`; fall back to Polars LazyFrame.
- **Parquet encrypted or columnar mismatch** — check with `duckdb -c "SELECT * FROM parquet_metadata('<file>');"`.
- **SQLite WAL lock** — copy the `.db` file to `/tmp/` before querying.
- **Query produces 0 rows unexpectedly** — verify column names match schema (case-sensitive in DuckDB by default); use `ILIKE` or `lower()` for string filters.

## Related

- Python library defaults: `CLAUDE.md` — polars for > 100 MB, pandas for < 100 MB.
- Tool install path: `mise exec -- fd|sd|mlr|hyperfine`
- PII rule: never read/echo .env, credentials, tokens, keys, PII values — report presence only.
