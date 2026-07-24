# Excellent SQL Engineering in June 2026: The Definitive Production Guide

> **Audience:** Principal engineers and database architects. Fundamentals of PostgreSQL, OLTP/OLAP, transactions, and distributed systems are assumed. Every recommendation is backed by production evidence or official vendor documentation.

***

## Executive Summary

The SQL engineering landscape in June 2026 is defined by four structural shifts: PostgreSQL 18's asynchronous I/O subsystem delivering 2–3× read throughput gains on cold caches; the maturation of UUIDv7 as the production-safe distributed primary key; the consolidation of the expand-contract migration pattern as a hard industry requirement for zero-downtime deployments; and the emergence of PostgreSQL as a credible hub in lakehouse architectures via pg_lake, pg_mooncake, and native Iceberg integration.[^1][^2][^3][^4][^5][^6][^7][^8]

MySQL 8.4 LTS is the current stable anchor for MySQL shops, supported through 2032, while MySQL 8.0 reached EOL in April 2026. SQL Server 2025 GA shipped in November 2025 with native vector types, DiskANN indexing, and optimized locking ported from Azure SQL Database. ClickHouse remains the dominant choice for real-time analytics at scale, and DuckDB's single-writer constraint defines its production envelope: embedded analytics, per-tenant isolation, and local-first query on data lakes.[^9][^10][^11][^12][^13]

The agent-call-tracker project represents state-of-the-art read-path engineering given its architectural constraints (no schema ownership). The Widgora target architecture described in Section 13 exceeds it in every dimension where schema ownership is available.

***

## 1. Physical Schema Design

### Normalization vs. Selective Denormalization

**Industry standard:** 3NF for OLTP with targeted denormalization for high-frequency read paths. The test is always measured, not assumed — reach for `EXPLAIN ANALYZE` before denormalizing. Denormalization is a performance intervention, not a design philosophy.[^14]

**Best practice:** Normalize first. Denormalize one column at a time when a specific query plan shows a join cost you can measure. Denormalized columns become consistency liabilities the moment they exist — enforce derived denormalized columns with `GENERATED` columns to eliminate application-layer synchronization bugs.[^15]

**Failure mode:** Premature denormalization creates write amplification and silent drift between normalized source and denormalized copies.

### Identity vs. UUID vs. UUIDv7

The June 2026 production consensus:[^16][^5]

| Key Type | When to Use | Index Locality | Distributed Safe | Size |
|---|---|---|---|---|
| `BIGSERIAL` / `IDENTITY` | Single-node, high-write OLTP | Excellent (sequential) | No (requires coordination) | 8 bytes |
| UUIDv4 (`gen_random_uuid()`) | Pre-PG18 distributed ID gen | Poor (random insertion) | Yes | 16 bytes |
| UUIDv7 (`uuidv7()` PG18+) | Distributed + sortable | Good (timestamp-ordered) | Yes | 16 bytes |
| Composite natural key | Known, immutable business key | Domain-dependent | Yes | Variable |

**State of the art:** PostgreSQL 18 ships `uuidv7()` natively, delivering timestamp-ordered UUIDs with monotonicity guaranteed per session. Benchmarks show UUIDv7 within 4% of UUIDv4 throughput (~21,700 ops/sec) on PG18 with zero collisions detected. UUIDv7 is the correct choice for any new distributed system starting in 2026.[^3][^5][^17]

**Failure mode:** UUIDv4 primary keys on B-tree indexes cause page splits on every insert (random write amplification), bloat secondary indexes by 2× versus BIGINT, and disable primary-key range scans.[^16]

```sql
-- PG18 recommended pattern
CREATE TABLE runs (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    status      TEXT NOT NULL CHECK (status IN ('pending','running','done','failed'))
);
```

### Generated Columns

**PG18 change:** Virtual generated columns (compute at query time, no storage) are now the default. Stored generated columns existed since PG12. In PG18, `GENERATED ALWAYS AS (...) VIRTUAL` requires no disk space and no write overhead.[^18][^19]

**When to use stored:** When the expression is expensive (full-text tsvector, JSON extraction used in index) and you want to index it. When to use virtual: read-heavy derivations that don't need indexing.

```sql
-- Virtual generated column (PG18) - zero storage cost
ALTER TABLE orders ADD COLUMN total_with_tax NUMERIC
    GENERATED ALWAYS AS (subtotal * 1.17) VIRTUAL;

-- Stored (indexable) - for full-text search
ALTER TABLE articles ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED;
CREATE INDEX ON articles USING GIN (search_vector);
```

### CHECK Constraints, Foreign Keys, and Deferred Constraints

**Best practice:** Declare ALL constraints the database can enforce. Foreign keys are not optional — they prevent orphaned rows, document relationships, and enable the query planner to use join elimination. The operational argument against them (performance) applies only to poorly-tuned systems.[^14][^15]

Deferred constraints (`DEFERRABLE INITIALLY DEFERRED`) are essential for bulk-loading operations that temporarily violate referential integrity (e.g., loading a parent-child hierarchy where order cannot be guaranteed).

```sql
-- Deferred FK for bulk loads
ALTER TABLE run_steps
    ADD CONSTRAINT fk_run
    FOREIGN KEY (run_id) REFERENCES runs(id)
    DEFERRABLE INITIALLY DEFERRED;
```

**ENUM vs. lookup tables:** ENUM is a catalog entry — cheap for small, truly static value sets. Lookup table wins when: values need descriptions, need to be queried, need foreign-key relationships, or might change. In 2026, the production consensus favors `TEXT` with a `CHECK` constraint or a lookup table over ENUM for anything that touches application code.[^20]

### Partitioning

**Declarative partitioning** (PG10+) is the only supported production pattern. Table inheritance for partitioning is deprecated.[^20]

| Strategy | When | Prune Condition | Pitfall |
|---|---|---|---|
| `RANGE` by time | Time-series, event logs, audit | `WHERE created_at BETWEEN ...` | Must include partition key in PK/UNIQUE |
| `LIST` by tenant | Multi-tenant, region | `WHERE tenant_id = $1` | Partition count explosion |
| `HASH` by id | Even distribution, no natural key | Equality on hash column | Disables range scans across all partitions |

**Failure mode:** Hash partitioning disables range queries — any `WHERE id > $1` must scan all partitions. Use only when you have measured a write hotspot that cannot be resolved by sequence ordering.[^16]

```sql
CREATE TABLE events (
    id          UUID NOT NULL DEFAULT uuidv7(),
    tenant_id   BIGINT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload     JSONB
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2026_q2 PARTITION OF events
    FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
```

### JSONB Usage

**Best practice:** JSONB for variable-structure attributes (third-party payloads, extensible metadata). Never as a substitute for properly normalized columns queried on every request.[^15][^20]

Indexing decision tree:
1. **Containment or key existence queries** → `GIN` on the full column
2. **Single known path, equality/range** → Expression B-tree on extracted value
3. **Containment-only at scale** → `GIN` with `jsonb_path_ops` opclass (smaller index, but loses key-existence support)
4. **Frequently accessed scalar field** → Promote to generated column with B-tree index

```sql
-- GIN for containment/key-existence
CREATE INDEX idx_events_payload ON events USING GIN (payload);

-- Expression index for known scalar path
CREATE INDEX idx_events_status ON events ((payload->>'status'))
    WHERE payload->>'status' IS NOT NULL;
```

### Column Ordering and Fillfactor

**Column ordering** affects TOAST (The Oversized Attribute Storage Technique) and alignment padding. Order fixed-width columns before variable-width ones to minimize padding waste in row storage.

**Fillfactor** controls free space left on data pages. Default is 100 (100% full). For OLTP update-heavy tables, `fillfactor=70-90` enables **HOT (Heap-Only Tuple) updates** — updates that avoid creating new index entries when only non-indexed columns change. This is the single highest-ROI physical storage tuning for write-heavy tables.[^20]

```sql
CREATE TABLE orders (...) WITH (fillfactor=80);
-- Or retroactively:
ALTER TABLE orders SET (fillfactor=80);
VACUUM orders; -- Reclaims existing pages at new fillfactor
```

***

## 2. SQL Query Engineering

### Sargable Queries and Predicate Pushdown

A sargable predicate is one an index can satisfy. The most common non-sargable patterns in production code:

```sql
-- NON-SARGABLE: function on indexed column
WHERE EXTRACT(year FROM created_at) = 2026
-- SARGABLE:
WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'

-- NON-SARGABLE: implicit cast
WHERE user_id = '12345'  -- user_id is BIGINT
-- SARGABLE:
WHERE user_id = 12345

-- NON-SARGABLE: leading wildcard
WHERE name LIKE '%smith'
-- SARGABLE (for prefix matches only):
WHERE name LIKE 'smith%'
```

**Anti-pattern:** Using `NOT IN` with a subquery that can return NULL — the entire query returns no rows if any NULL exists in the sublist. Replace with `NOT EXISTS` or a left join.

### Index-Only Scans and Covering Indexes

An index-only scan avoids heap access entirely when all required columns are present in the index (or in the visibility map). This is the most impactful single query optimization available for read-heavy workloads.

```sql
-- Covering index — includes all SELECT and WHERE columns
CREATE INDEX idx_runs_tenant_covering
    ON runs (tenant_id, created_at DESC)
    INCLUDE (id, status);

-- Verify index-only scan
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, status FROM runs
WHERE tenant_id = 42 AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
-- Look for "Index Only Scan" — "Heap Fetches: 0" indicates all data from index
```

### Partial Indexes

**Industry standard, massively underused.** A partial index indexes only rows matching a WHERE clause. Size reduction for a `status = 'pending'` index can be 100×+ versus a full index on status.[^15][^20]

```sql
-- Only index active, unprocessed runs
CREATE INDEX idx_runs_pending ON runs (tenant_id, created_at)
    WHERE status = 'pending' AND deleted_at IS NULL;
```

**Failure mode:** The query's WHERE clause must exactly match or imply the partial index predicate. `WHERE status = 'pending'` uses the index; `WHERE status IN ('pending', 'running')` does not.

### CTE Optimization (post-PG12)

Before PG12, CTEs were optimization fences (always materialized). From PG12, the planner can inline non-recursive, non-volatile CTEs — treat them as subquery aliases. Explicit `WITH ... AS MATERIALIZED` forces the pre-PG12 behavior when you want isolation (e.g., side-effecting CTEs, or when you know materialization reduces cost).[^16]

```sql
-- Force materialization for a CTE used multiple times
WITH expensive_agg AS MATERIALIZED (
    SELECT tenant_id, COUNT(*) as run_count, MAX(created_at) as last_run
    FROM runs
    WHERE status = 'done'
    GROUP BY tenant_id
)
SELECT t.name, e.run_count, e.last_run
FROM tenants t
JOIN expensive_agg e USING (tenant_id);
```

### Window Functions

Window functions execute after GROUP BY and WHERE but before ORDER BY and LIMIT. Key production uses:
- Running totals and rolling averages without self-joins
- `ROW_NUMBER()` for deduplication (latest record per group)
- `LAG()/LEAD()` for change detection in time-series
- `NTILE()` for percentile bucketing

```sql
-- Latest record per run_id without subquery
SELECT DISTINCT ON (run_id)
    run_id, step_name, status, completed_at
FROM run_steps
ORDER BY run_id, completed_at DESC;
-- DISTINCT ON is PostgreSQL-specific and often faster than window function for this pattern
```

### MERGE and UPSERT

**`INSERT ... ON CONFLICT`** (PostgreSQL) is the production standard for upsert. It is atomic, uses a single round-trip, and avoids the check-then-insert race condition of application-side merge logic.[^16]

```sql
INSERT INTO daily_rollups (tenant_id, date, total_runs, total_steps)
VALUES ($1, $2, $3, $4)
ON CONFLICT (tenant_id, date) DO UPDATE
    SET total_runs  = EXCLUDED.total_runs,
        total_steps = EXCLUDED.total_steps,
        updated_at  = now();
```

**`MERGE`** (SQL:2003, available in PG15+) handles insert/update/delete in one statement — useful for SCD Type 2 updates and data vault loading. Performance is comparable to `ON CONFLICT` for simple cases but more expressive for multi-branch logic.

### Pagination

**Offset pagination** (`LIMIT n OFFSET m`) is O(n+m) — the database must count and discard m rows on every page. At page 1000 with page size 50, PostgreSQL reads and discards 49,950 rows.[^21]

**Keyset pagination** uses a compound cursor based on sort column values. It is O(log n) per page regardless of depth:[^22][^23]

```sql
-- First page
SELECT id, created_at, status FROM runs
WHERE tenant_id = 42
ORDER BY created_at DESC, id DESC
LIMIT 50;

-- Next page (cursor = last row's (created_at, id))
SELECT id, created_at, status FROM runs
WHERE tenant_id = 42
  AND (created_at, id) < ($last_created_at, $last_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

**When offset pagination is acceptable:** Small datasets (<10K rows), admin UIs that need page numbers, reports where absolute position matters more than performance.

### Recursive CTEs and LATERAL

Recursive CTEs (`WITH RECURSIVE`) are the correct tool for adjacency-list hierarchies, graph traversal, and sequence generation. The termination condition must be carefully bounded to prevent infinite recursion.

`LATERAL` enables row-by-row subquery evaluation — essentially a correlated subquery in FROM position. Use for "top N per group" without window functions, and for calling set-returning functions per row.

```sql
-- Top 3 recent steps per run (LATERAL)
SELECT r.id, s.*
FROM runs r,
LATERAL (
    SELECT step_name, status, completed_at
    FROM run_steps
    WHERE run_id = r.id
    ORDER BY completed_at DESC
    LIMIT 3
) s
WHERE r.tenant_id = 42;
```

### Anti-Patterns Checklist

- `SELECT *` in application queries (prevents index-only scans, breaks on schema changes)
- `OFFSET` pagination beyond page 100 on large tables
- Non-sargable predicates (function on indexed column, implicit cast)
- `NOT IN` with nullable subqueries (use `NOT EXISTS`)
- ORM-generated N+1 queries (use `IN` clause batch or join)
- String concatenation for dynamic SQL (use parameterized queries; eliminates SQL injection)
- `COUNT(*)` on large tables without a covering partial index for existence checks (use `EXISTS` instead)
- Unnecessary `DISTINCT` hiding cardinality bugs from the join
- Joining on `LIKE '%pattern%'` (not sargable; use full-text search)

***

## 3. Index Engineering

### Decision Tree

```
Is the query selective (< 10–15% of rows)?
├── Yes → Does it filter on a known prefix of columns?
│   ├── Yes → B-tree composite index (most-selective col first)
│   └── No → Expression index or partial index
└── No → Seq scan is likely cheaper; revisit query predicate

Does it filter on JSONB / array / full-text?
└── Yes → GIN index

Is the table huge (>1B rows) and is the indexed column correlated with physical insertion order (e.g., a timestamp)?
└── Yes → BRIN index (very small, excellent for time-series append-only tables)

Does the query need multiple columns, and would a heap fetch be expensive?
└── Yes → Covering index with INCLUDE
```

### Composite Index Column Order

Rule: **equality predicates first, range predicates last, ORDER BY direction matched**.[^20][^16]

```sql
-- Query: WHERE tenant_id = $1 AND status = $2 AND created_at > $3 ORDER BY created_at DESC
-- Correct order:
CREATE INDEX idx_runs_tenant_status_time
    ON runs (tenant_id, status, created_at DESC);
-- Wrong: (created_at, tenant_id, status) — range on first column blocks equality use
```

### PG18 Skip Scan

PostgreSQL 18 introduces **B-tree skip scan**: the planner can use a composite index even when the query omits an equality predicate on leading prefix columns. This reduces the need to create multiple partial indexes to cover omitted-leading-column patterns. Still verify with `EXPLAIN ANALYZE` — the optimizer will choose seq scan if selectivity is low.[^19][^24]

### Concurrent Index Creation

**Always** use `CREATE INDEX CONCURRENTLY` in production. It takes longer but does not hold an `ACCESS EXCLUSIVE` lock. A regular `CREATE INDEX` blocks all reads and writes for the duration on large tables.[^15]

```sql
-- Production-safe index creation
CREATE INDEX CONCURRENTLY idx_runs_tenant
    ON runs (tenant_id, created_at DESC);
```

**Failure mode:** `CREATE INDEX CONCURRENTLY` can leave an INVALID index if the process is interrupted. Check `pg_indexes.indisvalid` and drop/recreate if invalid.

### Index Maintenance

- **`VACUUM`**: Reclaims dead tuple space, updates visibility map (enables index-only scans), advances transaction ID horizon. Run aggressively on high-churn tables.
- **`ANALYZE`**: Updates planner statistics. Default `default_statistics_target = 100` is insufficient for highly skewed columns — raise to 500–1000 for join keys and filter columns.
- **Extended statistics** (`CREATE STATISTICS`): Captures column correlations. Critical when two columns are correlated but the planner estimates them as independent, causing severe cardinality underestimates.

```sql
-- Extended statistics for correlated columns
CREATE STATISTICS stat_tenant_status ON tenant_id, status FROM runs;
ANALYZE runs;

-- Check index usage — drop indexes with 0 scans over 30+ days
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Hypothetical Indexes

The `hypopg` extension allows testing index effectiveness without building the index. Run `EXPLAIN` with a hypothetical index to validate it would be used before paying the build cost on a large table.

***

## 4. Database Migrations

### Tool Comparison

| Tool | Model | Language | Drift Detection | Auto-generation | Rollback | Verdict |
|---|---|---|---|---|---|---|
| **Flyway** | Versioned SQL files | Java/CLI | No (Community) | No | Manual | Best for teams wanting simple, SQL-first, linear migrations[^25][^26] |
| **Liquibase** | Versioned + declarative XML/SQL/YAML | Java/CLI | Yes | No | Yes (Rollback block) | Best for complex governance, preconditions, labeling[^25][^26] |
| **Alembic** | Versioned Python | Python | Limited | Yes (autogenerate) | Yes | Best for SQLAlchemy shops; autogenerate is approximate, always review[^27] |
| **Atlas** | Declarative HCL/SQL | Go/CLI | Yes | Yes (from ORM/diff) | Planned rollback | State-of-the-art: Terraform for databases, lint-before-apply safety[^28][^29] |
| **Sqitch** | Change-based SQL | Perl/CLI | No | No | `revert` scripts | Solid for pure-SQL teams wanting dependency tracking |
| **dbmate** | Versioned SQL files | Go/CLI | No | No | `down` SQL | Minimal, language-agnostic, good for polyglot teams |
| **Goose** | Versioned SQL/Go | Go | No | No | `down` SQL | Best for Go services, supports Go migrations for complex transforms |

**Industry consensus 2026:** For new projects, Atlas's declarative model (describe desired state, auto-plan changes) with built-in lint checks is the highest-ROI choice. Flyway remains the most widely deployed in enterprise Java shops. Alembic is standard for Python/SQLAlchemy. All teams should enforce **versioned migrations only** — no DDL at application startup.[^28]

### Expand-Contract Pattern (Non-Negotiable for Zero Downtime)

The pattern decomposes every breaking schema change into three independently deployable phases:[^4][^6][^30]

**Phase 1 — Expand:** Add new structures alongside the old. Nothing is renamed or dropped. The existing application version is completely unaffected.

```sql
-- Migration V012: Expand — add new column alongside old
ALTER TABLE runs ADD COLUMN completed_date DATE; -- nullable
```

**Phase 2 — Migrate:** Backfill historical data in bounded batches. Deploy application code that writes to both old and new columns.

```sql
-- Backfill in batches of 10,000 to avoid I/O saturation
DO $$
DECLARE
    last_id UUID := NULL;
    batch_count INT;
BEGIN
    LOOP
        WITH batch AS (
            SELECT id, completed_at FROM runs
            WHERE (last_id IS NULL OR id > last_id)
              AND completed_at IS NOT NULL
              AND completed_date IS NULL
            ORDER BY id
            LIMIT 10000
            FOR UPDATE SKIP LOCKED
        )
        UPDATE runs r
        SET completed_date = b.completed_at::DATE
        FROM batch b
        WHERE r.id = b.id
        RETURNING r.id INTO last_id;
        GET DIAGNOSTICS batch_count = ROW_COUNT;
        EXIT WHEN batch_count = 0;
        PERFORM pg_sleep(0.05); -- 50ms pause between batches
    END LOOP;
END $$;
```

**Phase 3 — Contract:** After all application code is exclusively using the new column, drop the old in a separate deployment.

```sql
-- Migration V014: Contract — safe to drop only after all app versions use new column
ALTER TABLE runs DROP COLUMN completed_at; -- now just metadata update
```

**Failure mode:** Combining Phase 1 and 3 in one migration. A running replica of the old application code will immediately fail when the column it reads disappears.

### Lock Timeouts for Migrations

Every migration that acquires an `ACCESS EXCLUSIVE` lock must set a lock timeout to prevent a stuck migration from blocking all reads and writes indefinitely:[^6][^31]

```sql
-- Every migration that acquires heavy locks
SET lock_timeout = '3s';
SET idle_in_transaction_session_timeout = '10s';

ALTER TABLE runs ADD COLUMN completed_date DATE;
-- If the lock cannot be acquired in 3s, the migration fails-fast
-- rather than queueing all production traffic behind it
```

### Large Table Migration

Adding a NOT NULL column with a default to a large table is safe in PG11+ (default stored in catalog, no table rewrite). For PG10 and earlier: expand with nullable, backfill, then add NOT NULL constraint using `NOT VALID` + `VALIDATE CONSTRAINT` (two steps that avoid a full table scan lock):[^32]

```sql
-- PG10 safe pattern for NOT NULL constraint addition
ALTER TABLE runs ADD CONSTRAINT runs_status_not_null
    CHECK (status IS NOT NULL) NOT VALID; -- Fast, no scan

-- Later, in off-peak window:
ALTER TABLE runs VALIDATE CONSTRAINT runs_status_not_null; -- Shares lock only
```

***

## 5. Application Database Layer

### Driver Selection (June 2026)

| Driver/ORM | Language | Async | Server-Side Prepare | Production Status |
|---|---|---|---|---|
| **psycopg3** | Python | Yes | Yes | Current standard; replaces psycopg2[^33] |
| **psycopg_pool** | Python | Yes | N/A | Ships with psycopg3; production-grade pool management[^34] |
| **asyncpg** | Python | Yes | Yes | Highest throughput Python driver; no ORM layer[^35] |
| **SQLAlchemy Core** | Python | Yes (2.0+) | Via driver | SQL expression layer; well-suited for complex queries[^36] |
| **SQLAlchemy ORM** | Python | Yes (2.0+) | Via driver | Correct for CRUD-heavy apps; watch for N+1 |
| **pgx/v5** | Go | Yes | Yes | De facto standard Go driver |
| **jOOQ** | Java | Yes | Yes | Best type-safe SQL DSL for Java/Kotlin; compile-time query validation |
| **JDBC + HikariCP** | Java | No | Yes | HikariCP is the standard connection pool for blocking Java |

### Connection Pool Configuration

**PgBouncer** (transaction-mode pooling) remains the external connection pooler of choice for high-connection-count deployments. It dramatically reduces the number of actual PostgreSQL backends, which each consume ~5–10 MB of shared memory and a postmaster process.[^37][^38]

**Pool sizing formula:** `pool_size = (cpu_cores × 2) + effective_spindle_count`. For NVMe storage, treat spindle count as 1. For cloud databases, start at `cpu_cores × 2` and tune with load testing.[^33]

```python
# psycopg_pool production configuration
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo="postgresql://user:pass@host:5432/db",
    min_size=4,
    max_size=16,
    max_waiting=20,          # Queue depth before returning error
    timeout=10.0,            # Time to wait for connection
    max_lifetime=1800,       # 30-minute max connection age (recycles auth)
    max_idle=300,            # Close connections idle > 5 min
    reconnect_timeout=300,   # Give up reconnect after 5 min
    check=ConnectionPool.check_connection,
)
```

**Failure mode:** Setting `max_size` equal to `max_connections` — no headroom for admin connections, monitoring, and replication. Reserve 10-15 connections for non-application use.

### Prepared Statements and Server-Side Prepare

Server-side prepared statements cache the query plan in the backend process. For queries executed hundreds of times per second with identical structure (different params), this eliminates repeated parse-analyze-plan cycles. In psycopg3, use `cursor.execute()` with a `Prepared` cursor or `connection.prepare()`.

**Failure mode:** Generic plans vs. custom plans. PostgreSQL will switch between generic (parameter-independent) and custom (parameter-specific) plans based on cost. The `plan_cache_mode` parameter controls this explicitly. For highly-skewed distributions, `plan_cache_mode = force_custom_plan` prevents the planner from using a generic plan that ignores parameter values.

### Isolation Levels

| Level | Prevents | PostgreSQL Implementation | Use Case |
|---|---|---|---|
| Read Committed (default) | Dirty reads | MVCC snapshot per statement | General OLTP |
| Repeatable Read | Non-repeatable reads | MVCC snapshot per transaction | Analytics scans, multi-step read-modify-write |
| Serializable (SSI) | Phantom reads, serialization anomalies | Predicate locking + SSI | Financial transactions, inventory allocation |

**Advisory locks** are the highest-ROI PostgreSQL concurrency primitive for application-level coordination — mutex for distributed cron jobs, token-bucket rate limiting, leader election. Use transaction-scoped locks (`pg_try_advisory_xact_lock`) for "do once per transaction" patterns:[^39][^40]

```sql
-- Advisory lock for idempotent job execution
-- Returns FALSE immediately if lock is held (vs. blocking)
SELECT pg_try_advisory_xact_lock(hashtext('daily_rollup_job_' || tenant_id::text))
```

### Circuit Breakers and Retry Strategy

Every database call from an application should have:
1. **Statement timeout** (`SET statement_timeout = '5s'`) — per query, not per connection
2. **Connection timeout** — pool-level, 5-10 seconds
3. **Retry with exponential backoff** for transient errors (connection refused, serialization failure, deadlock detected)
4. **Circuit breaker** — after N consecutive failures, stop sending traffic to the database for a cooldown period (prevents thundering herd against a struggling primary)

***

## 6. Performance Engineering

### Measure Before Optimizing

The only valid optimization workflow: measure → identify bottleneck → form hypothesis → implement change → measure again. Never optimize from intuition on production SQL.

### EXPLAIN ANALYZE

```sql
-- Full production diagnostic
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
SELECT ...;
```

Key elements to read:
- **Actual Rows vs. Estimated Rows:** 10× or greater divergence indicates stale statistics or missing extended statistics
- **Buffers: shared hit vs. read:** "read" means disk I/O; "hit" means served from `shared_buffers`
- **Execution Time vs. Planning Time:** If planning time approaches execution time, consider `plan_cache_mode` or query complexity reduction

### pg_stat_statements + auto_explain

These two extensions are **mandatory on every production PostgreSQL instance**:[^41][^42]

```sql
-- postgresql.conf
shared_preload_libraries = 'pg_stat_statements,auto_explain'
pg_stat_statements.max = 10000
pg_stat_statements.track = all
pg_stat_statements.track_planning = on
auto_explain.log_min_duration = 1000  -- Log plans for queries > 1s
auto_explain.log_analyze = on
auto_explain.log_buffers = on
auto_explain.log_format = json
compute_query_id = on
```

`pg_stat_statements` answers "what is expensive across the workload." `auto_explain` answers "why was a specific execution expensive." Join them via `queryid` for plan regression detection.[^41]

### pg_stat_io (PG16+)

Introduced in PostgreSQL 16, `pg_stat_io` provides per-backend, per-context I/O accounting. Use it to identify which query or maintenance operation is saturating I/O:

```sql
SELECT backend_type, object, context, reads, writes, hits, evictions
FROM pg_stat_io
ORDER BY reads DESC
LIMIT 20;
```

### Wait Events

`pg_stat_activity.wait_event_type` + `wait_event` is the first diagnostic when queries are slow but `EXPLAIN ANALYZE` shows low execution time. Common production wait events:

| Wait Event | Meaning | Resolution |
|---|---|---|
| `Lock:relation` | Table-level lock contention | Identify blocking query via `pg_blocking_pids()` |
| `Lock:tuple` | Row-level lock | Check for long-running transactions holding row locks |
| `IO:DataFileRead` | Cold cache misses | Increase `shared_buffers`, prefetch with `pg_prewarm` |
| `Client:ClientRead` | Application not reading results fast enough | Check application network/processing lag |
| `LWLock:buffer_content` | Buffer pool contention | Increase `shared_buffers` or partition hot tables |

### WAL and Checkpoint Tuning

```ini
# Production WAL configuration for write-heavy OLTP
wal_buffers = 64MB
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9   # Spread checkpoint writes over 90% of interval
checkpoint_timeout = 10min           # Longer interval = less frequent I/O spike
synchronous_commit = on              # Keep for durability (turn off only for idempotent bulk loads)
wal_compression = lz4                # PG14+ LZ4 compression, ~30% WAL size reduction
```

### PostgreSQL 18 Async I/O Configuration

```ini
# PostgreSQL 18: io_uring on Linux (fastest), worker otherwise
io_method = io_uring            # Linux only, requires liburing
io_workers = 4                  # Start at CPU_count / 4
effective_io_concurrency = 32   # Increase for multiple drives
maintenance_io_concurrency = 32
```

Benchmarks show 2–3× improvement for sequential scans on cold caches with io_uring; 15-25% for sequential scans in general, 10-18% for bitmap heap scans.[^2][^43][^1]

***

## 7. Data Pipeline Patterns

### Incremental Loading and CDC

**Watermark-based incremental loading** requires a reliable high-watermark column (`updated_at TIMESTAMPTZ`). Add a buffer window (3 hours) to handle late-arriving data:[^44]

```sql
-- dbt incremental model pattern
{% if is_incremental() %}
WHERE updated_at >= (
    SELECT DATEADD(hour, -3, MAX(updated_at)) FROM {{ this }}
)
{% endif %}
```

**Debezium** is the production-standard log-based CDC tool. It reads PostgreSQL WAL directly via logical replication slots, captures inserts/updates/deletes with zero query-based overhead on the source. Key production requirements:[^45][^46]
- Monitor replication slot lag — an unconsumed slot accumulates WAL and can fill disk
- Set `max_slot_wal_keep_size` to prevent unbounded WAL accumulation
- Use `wal_level = logical` on the source

### Idempotency and Exactly-Once Semantics

Every pipeline step must be safely re-runnable without producing duplicates. For PostgreSQL targets, `INSERT ... ON CONFLICT DO NOTHING/UPDATE` is the idempotency primitive. For ClickHouse, `ReplacingMergeTree` achieves eventual deduplication.

**Exactly-once semantics** at the database layer: write the Debezium offset and the target rows in the same transaction. If the transaction fails, Debezium will replay the event; `ON CONFLICT` ensures no duplicate row is created.

### dbt Materialization Strategy

| Materialization | When | Risk |
|---|---|---|
| `view` | Logic layer, rarely queried directly | Full recompute every query |
| `table` | Small/medium, full refresh acceptable | Full rebuild on every run |
| `incremental` | Large tables, reliable watermark exists | Merge key collisions produce duplicates; always verify uniqueness |
| `materialized view` | PostgreSQL materialized views; refresh via dbt or cron | Refresh blocking query window |

**State-of-the-art:** For medium tables (<10M rows) with complex transforms, a daily full refresh is often faster and more reliable than incremental state management. Always validate merge key uniqueness before using `unique_key` in incremental models.[^44]

### Slowly Changing Dimensions and Data Vault

**SCD Type 2** (effective/expiry timestamp) is the standard historical tracking approach. Use `MERGE` (PG15+) or the insert-check-update pattern with `ON CONFLICT`:

```sql
-- SCD Type 2 via INSERT ON CONFLICT for tenant attribute history
INSERT INTO tenant_attributes_history (tenant_id, attribute, value, valid_from, valid_to)
SELECT tenant_id, attribute, value, now(), NULL
FROM staging_tenant_attributes
ON CONFLICT (tenant_id, attribute, valid_to)
DO UPDATE SET value = EXCLUDED.value
WHERE tenant_attributes_history.value <> EXCLUDED.value;
```

**Data Vault** (Hub + Link + Satellite) is the state-of-the-art schema for enterprise data warehouses requiring full auditability and load-order independence. It pairs naturally with dbt's ref/source graph.[^47]

### Lakehouse Integration (Emerging, Production-Adopted)

The PostgreSQL-Iceberg integration story matured significantly in late 2025:[^7][^8]
- **pg_lake** (Snowflake, Nov 2025): Hosts DuckDB as a sidecar process. Queries Iceberg tables from PostgreSQL via SQL translation. Supports joins between Iceberg and local PG tables[^8]
- **pg_mooncake** (acquired by Databricks Oct 2025): Continuous logical replication slot → Iceberg ingestion
- **EDB Analytics Accelerator**: Vectorized query engine for PostgreSQL that reads Delta Lake and Iceberg directly, targeting analytical workloads without a separate warehouse[^48]

***

## 8. Observability

### Core Metrics: RED + USE

**RED (Rate, Errors, Duration)** for query-level observability:
- Rate: queries/second by type (read/write) and by normalized query fingerprint
- Errors: transaction rollbacks/second, deadlocks/second, connection errors
- Duration: p50/p95/p99 query latency by fingerprint from `pg_stat_statements`

**USE (Utilization, Saturation, Errors)** for resource-level observability:
- CPU utilization, I/O wait %
- Connection pool saturation: `active_connections / max_connections`
- Lock saturation: `pg_locks` queue depth

### Prometheus + OpenTelemetry Stack

**postgres_exporter** exposes `pg_stat_*` views as Prometheus metrics. The OpenTelemetry Collector's PostgreSQL receiver collects metrics natively via SQL queries against the database. Both are production-standard in 2026.[^49][^50]

```yaml
# OTel Collector PostgreSQL receiver
receivers:
  postgresql:
    endpoint: "postgres-primary:5432"
    databases: ["production"]
    collection_interval: 10s
    tls:
      insecure: false
      ca_file: /etc/ssl/certs/pg-ca.crt
```

### Essential Dashboard Panels

| Panel | Query/Source | Alert Threshold |
|---|---|---|
| Query rate (QPS) | `pg_stat_statements.calls` rate | — |
| Active connections | `pg_stat_activity` | > 80% of `max_connections` |
| Long-running queries | `pg_stat_activity.query_start` age | > 30s → warn; > 5min → alert |
| Lock waits | `pg_locks l JOIN pg_stat_activity a` | Any wait > 10s |
| Cache hit ratio | `blks_hit / (blks_hit + blks_read)` from `pg_stat_database` | < 95% → investigate |
| Replication lag | `pg_stat_replication.write_lag` | > 100MB or > 5s |
| Dead tuple ratio | `n_dead_tup / n_live_tup` from `pg_stat_user_tables` | > 20% → force VACUUM |
| Temp file usage | `pg_stat_database.temp_bytes` | > 0 in steady state → tune `work_mem` |
| Checkpoint frequency | `pg_stat_bgwriter.checkpoints_timed` vs `checkpoints_req` | If `checkpoints_req` >> `checkpoints_timed` → increase `max_wal_size` |

### Slow Query and Plan Regression Detection

```sql
-- Top 10 slowest query fingerprints by total time
SELECT
    LEFT(query, 80) as query_snippet,
    calls,
    mean_exec_time,
    total_exec_time,
    stddev_exec_time,
    rows
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY total_exec_time DESC
LIMIT 10;
```

Plan regression: compare `mean_exec_time` snapshots across deployments. A sudden increase for a stable fingerprint indicates a plan change — investigate with `auto_explain` log and `pg_stat_statements.plans` (PG13+).

***

## 9. Testing Strategy

### Testcontainers: Industry Standard for Integration Testing

Testcontainers is the production consensus for database integration testing in 2026. It replaces H2/in-memory databases with real Docker containers, ensuring tests run against the same engine, dialect, lock behavior, and constraint enforcement as production.[^51][^52][^53][^54]

**Non-negotiable tests:**
1. Migration idempotency — run the full migration suite twice, assert schema matches expected
2. `ON CONFLICT` behavior — verify upsert logic produces correct results under concurrent inserts
3. Isolation level behavior — `SERIALIZABLE` anomalies cannot be tested against H2
4. Index usage — run `EXPLAIN ANALYZE` in tests and assert no unexpected `Seq Scan` appears

```python
# Python pytest + Testcontainers pattern
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:18") as pg:
        yield pg.get_connection_url()

def test_upsert_idempotency(pg_container):
    # Apply migrations
    # Insert same row twice
    # Assert row count = 1, not 2
    ...

def test_query_uses_index(pg_container, pg_conn):
    plan = pg_conn.execute(
        "EXPLAIN (ANALYZE, FORMAT JSON) SELECT ..."
    ).fetchone()
    node_type = plan['Plan']['Node Type']
    assert node_type == 'Index Scan', f"Expected Index Scan, got {node_type}"
```

### Query Plan Regression Tests

Include `EXPLAIN (FORMAT JSON)` assertions in your CI pipeline. Assert that critical queries do not regress to `Seq Scan` after schema or index changes. This catches migrations that inadvertently break an existing index.

### Snapshot Testing for Schema

Check `pg_dump --schema-only` output into version control. Any migration that changes the schema must produce a predictable, reviewed diff. Atlas's drift detection does this automatically as part of its CI integration.[^28]

***

## 10. Production Architecture

### High Availability: Patroni + pgBouncer (Industry Standard)

**Patroni** is the production consensus for PostgreSQL automated failover. It manages primary election via etcd/Consul/ZooKeeper, performs automated promotion on primary failure, and exposes a REST API that HAProxy uses to route reads and writes to correct nodes.[^55][^38][^56][^37]

```
Application Layer
     │
     ▼
HAProxy (VIP)
  ├── Port 5000 → Primary (Patroni /primary check)
  └── Port 5001 → Replicas (Patroni /replica?lag=1MB check)
     │
     ▼
PgBouncer (Transaction Mode)
     │
     ├── Primary (writes + reads)
     └── Replica(s) (read-only queries)
```

**Logical vs. Physical Replication:**
- Physical (streaming) replication: byte-for-byte copy of WAL. Simplest, most reliable. Replicas are read-only. Standard for HA.
- Logical replication: table-level, can replicate to different PostgreSQL major versions, partial replication, bidirectional (PG16+). Required for blue-green major version upgrades and cross-version reads.

**PG18 failover slot synchronization:** PostgreSQL 18 adds native support for synchronizing logical replication slots to standbys, solving a long-standing HA gap. Previously, a failover would lose the logical slot, breaking downstream consumers (Debezium, etc.).[^57]

### Cloud Managed: Decision Matrix

| Platform | Best For | Caveat |
|---|---|---|
| **AWS Aurora PostgreSQL** | Standard HA SaaS, AWS-native | ~3× RDS throughput; extension support limited to approved list |
| **Google AlloyDB** | Mixed OLTP + analytics (columnar engine), ML workloads | 4× faster than standard PostgreSQL for OLTP; higher cost[^58][^59] |
| **Azure Database for PostgreSQL Flexible Server** | Azure-native; cheapest entry point | Fewer extensions than Aurora |
| **Neon** | Serverless, branching workflows, per-tenant DBs | Scale-to-zero with 300-500ms cold start[^60]; acquired by Databricks May 2025[^61] |
| **Crunchy Data** | Full Postgres compatibility, extension freedom | Less automation than hyperscalers |
| **Timescale (Tiger Cloud)** | Time-series + PostgreSQL, 1-5TB range | Columnar compression on time-series chunks; TimescaleDB-specific features required |

***

## 11. SQL Data Engineering Patterns

### dbt Architecture

The mature dbt architecture layers are:[^47][^44]
1. **Staging** (`stg_*`): 1:1 source table mapping, minimal transformation, type casting
2. **Intermediate** (`int_*`): Business logic joins, complex transformations
3. **Marts** (`dim_*`, `fct_*`): Consumption-ready dimensional models

All staging models: `materialized = 'view'`. Intermediate that is expensive: `materialized = 'table'`. Large fct_ tables: `materialized = 'incremental'`.

### DuckDB Production Envelope

DuckDB is production-ready within its constraint: **single-writer, multi-reader on one machine**:[^12][^62]
- ✅ Embedded analytics in a single-process application
- ✅ Local-first querying of Parquet/Iceberg/S3 files
- ✅ Per-tenant isolated databases (one DuckDB file per tenant)
- ✅ dbt development and testing locally
- ❌ High-frequency concurrent writes from multiple processes
- ❌ Row-level security across users
- ❌ Replication / PITR

### ClickHouse Production Rules

From ClickHouse's own engineering blog and production evidence:[^63][^13]
1. **Primary key = sort key** — determines physical sort order of MergeTree. Choose columns used in the most frequent WHERE/GROUP BY queries, low cardinality first
2. **Never insert one row at a time** — batch inserts; use async_insert for client-side streaming
3. **ReplacingMergeTree for deduplication** — eventual deduplication on primary key at merge time, not guaranteed on read without `FINAL`
4. **Avoid mutations** (`ALTER TABLE UPDATE/DELETE`) — rewrites entire parts; use tombstone columns
5. **Part count monitoring** — "Too many parts" error is the most common production incident; root cause is insert frequency outpacing merge[^63]

### Materialized Views for Daily Rollups

```sql
-- Materialized daily rollup for dashboard performance
CREATE MATERIALIZED VIEW daily_run_stats AS
SELECT
    tenant_id,
    created_at::DATE AS run_date,
    COUNT(*)         AS total_runs,
    COUNT(*) FILTER (WHERE status = 'done') AS successful_runs,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) AS avg_duration_sec
FROM runs
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY tenant_id, created_at::DATE;

CREATE UNIQUE INDEX ON daily_run_stats (tenant_id, run_date);

-- Refresh concurrently (no read lock)
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_run_stats;
```

***

## 12. Security

### Row-Level Security

PostgreSQL RLS (since PG9.5) is the correct tool for tenant isolation at the database layer. Enable it explicitly (opt-in) and create policies per operation:[^64]

```sql
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON runs
    USING (tenant_id = current_setting('app.current_tenant_id')::BIGINT);

-- BYPASSRLS role for service accounts that legitimately span tenants
CREATE ROLE service_account;
ALTER ROLE service_account BYPASSRLS;
```

**Failure mode:** Superusers and table owners bypass RLS unless `FORCE ROW LEVEL SECURITY` is set on the table. Always test RLS with a non-superuser connection.

### Dynamic Data Masking

Aurora PostgreSQL 16.10+ and 17.6+ ship `pg_columnmask` for SQL-based masking policies at query time. Data is masked based on the querying user's role without modifying stored data or requiring application changes. Compliant with GDPR, HIPAA, PCI DSS.[^65][^66]

### Secrets Management

- Never store database credentials in environment variables in plain text in production
- Use AWS Secrets Manager / GCP Secret Manager / HashiCorp Vault with automatic rotation
- Application retrieves credentials at startup and on rotation signal
- Database users should use `SCRAM-SHA-256` authentication (MD5 is deprecated in PG18 and will be removed)[^19]

### Least Privilege

```sql
-- Application user — minimal privileges
CREATE USER app_user WITH PASSWORD 'scram-sha-256-hashed';
GRANT CONNECT ON DATABASE production TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- NEVER GRANT: SUPERUSER, CREATEROLE, CREATEDB, DROP, TRUNCATE, ALTER, DDL
```

### SQL Injection Prevention

Parameterized queries are mandatory at the driver level. ORMs and query builders that support parameterized queries eliminate injection by default. The only injection risk comes from dynamic table/column name construction — these must use a whitelist validation, never string interpolation.

### Immutable Audit Tables

```sql
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    table_name  TEXT NOT NULL,
    operation   TEXT NOT NULL CHECK (operation IN ('INSERT','UPDATE','DELETE')),
    record_id   UUID NOT NULL,
    actor_id    UUID NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    old_data    JSONB,
    new_data    JSONB
);

-- Prevent deletion or update of audit records
CREATE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;
CREATE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
-- Or enforce via RLS policy that no role can UPDATE/DELETE audit_log
```

***

## 13. Comparative Case Study

### Dimension 1: Read Path Engineering — agent-call-tracker

The agent-call-tracker demonstrates **June 2026 state-of-the-art read-path engineering** within its constraint envelope:

| Component | Pattern | June 2026 Assessment |
|---|---|---|
| Connection pooling | Application-layer pool | ✅ Standard |
| Overload shedding (HTTP 503) | Synchronous check on pool exhaustion | ✅ State-of-the-art — fast failure over queuing under load |
| Single-flight deduplication | Go's `singleflight` or Python equivalent | ✅ State-of-the-art — prevents thundering herd on cache miss[^67][^68] |
| L1 memory cache | In-process LRU or TTL map | ✅ Standard |
| L2 disk cache | Persistent cache (Redis, disk KV) | ✅ Best practice for expensive query results |
| L3 database | MySQL CRM read replica | ✅ Correct tiering |
| Sargable SQL | Strictly avoiding function-on-column, implicit casts | ✅ State-of-the-art |
| Primary key ID range pruning | `WHERE id BETWEEN $start AND $end` | ✅ State-of-the-art for sequential ID systems |
| 68× performance improvement | Measured via Prometheus, not assumed | ✅ Exemplary — measure first |
| Prometheus metrics | Histograms per endpoint, per tier | ✅ State-of-the-art |
| Real database integration tests | No mocks | ✅ June 2026 best practice[^51] |

**Remaining improvements possible (read path only):**
1. **OpenTelemetry traces** — distributed trace correlation from HTTP request through cache tiers to database query. Prometheus covers metrics; OTel adds the causal chain
2. **Adaptive TTL based on data freshness signals** — if the CRM publishes change events (even webhooks), invalidate L1/L2 proactively rather than on TTL expiry
3. **Query fingerprint tracking** — capture normalized query text + parameter ranges in Prometheus labels for per-query breakdown

### Dimension 2: Database Ownership — agent-call-tracker

**Assessment: architected correctly given no schema ownership.** It is architecturally sound to build a reliable, high-performance read service over a shared view with no DDL rights. Operational state via Prometheus metrics + disk cache is appropriate and sufficient.

The following assessments are invalid penalties:
- ❌ "Should add indexes" — no DDL rights
- ❌ "Should add constraints" — no schema ownership
- ❌ "Should add migration tooling" — nothing to migrate

**What is genuinely not available and genuinely missing:**
- No query plan insight into the CRM's schema (index strategy unknown)
- No ability to add `pg_stat_statements`-compatible monitoring on the CRM side
- No typed DATE/TIMESTAMPTZ columns (string → date parsing in application layer)

***

### Target Architecture: Widgora

Widgora owns its PostgreSQL schema. The following architecture exceeds agent-call-tracker on every axis where schema ownership provides leverage.

#### Schema Design

```sql
-- Core tables with June 2026 best practices
CREATE TABLE tenants (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE runs (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    run_date     DATE GENERATED ALWAYS AS (started_at::DATE) STORED,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','running','done','failed')),
    metadata     JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT runs_completed_after_started
        CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE run_steps (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step_name   TEXT NOT NULL,
    step_order  INT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed','skipped')),
    duration_ms NUMERIC(12,2) GENERATED ALWAYS AS (
        CASE WHEN completed_at IS NOT NULL
             THEN EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
        END
    ) VIRTUAL,
    error_detail JSONB
);

-- Composite indexes: equality columns first, range column last
CREATE INDEX idx_runs_tenant_date ON runs (tenant_id, run_date DESC)
    INCLUDE (id, status);

-- Partial index: only pending/running (active) runs — small, fast
CREATE INDEX idx_runs_active ON runs (tenant_id, started_at DESC)
    WHERE status IN ('pending', 'running') AND deleted_at IS NULL;

-- Expression index: for status-specific analytics
CREATE INDEX idx_run_steps_run_status ON run_steps (run_id, status)
    WHERE status != 'skipped';

-- Audit history: immutable via RLS policy
CREATE TABLE audit_events (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    table_name  TEXT NOT NULL,
    operation   TEXT NOT NULL,
    record_id   UUID NOT NULL,
    actor_id    UUID,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL
);
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_insert_only ON audit_events FOR INSERT WITH CHECK (true);
-- No SELECT/UPDATE/DELETE policies → only INSERT is possible
```

#### Connection Layer

```python
# Widgora production connection layer
from psycopg_pool import AsyncConnectionPool
from opentelemetry import trace

pool = AsyncConnectionPool(
    conninfo="postgresql://app_user@pgbouncer:6432/widgora",
    min_size=4,
    max_size=16,
    timeout=5.0,
    max_lifetime=1800,
    check=AsyncConnectionPool.check_connection,
)

tracer = trace.get_tracer("widgora.db")

async def execute_with_trace(query: str, params: tuple, span_name: str):
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("db.statement", query[:200])
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()
```

#### Migrations

Use **Atlas** for declarative schema management with CI lint integration:

```hcl
# schema.hcl — desired state, Atlas diffs against live schema
table "runs" {
  schema = schema.public
  column "id" {
    type = uuid
    default = sql("uuidv7()")
  }
  column "tenant_id" {
    type = bigint
    null = false
  }
  # ...
}
```

Atlas generates the versioned SQL migration, lints for unsafe operations (missing CONCURRENTLY, lock risks), and applies via CI/CD with `atlas migrate apply --auto-approve=false`.

#### Materialized Rollup for Dashboard Performance

```sql
-- Replaces ad-hoc dashboard queries with pre-aggregated data
CREATE MATERIALIZED VIEW mv_daily_run_stats AS
SELECT
    r.tenant_id,
    r.run_date,
    COUNT(*)                                        AS total_runs,
    COUNT(*) FILTER (WHERE r.status = 'done')       AS successful_runs,
    COUNT(*) FILTER (WHERE r.status = 'failed')     AS failed_runs,
    PERCENTILE_CONT(0.50) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (r.completed_at - r.started_at))
    )                                               AS median_duration_sec,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (r.completed_at - r.started_at))
    )                                               AS p95_duration_sec
FROM runs r
WHERE r.completed_at IS NOT NULL
GROUP BY r.tenant_id, r.run_date;

CREATE UNIQUE INDEX ON mv_daily_run_stats (tenant_id, run_date);

-- Refresh strategy: scheduled via pg_cron every 5 minutes
SELECT cron.schedule('refresh_daily_stats', '*/5 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_run_stats');
```

***

## 14. Gap Analysis

| Capability | agent-call-tracker | Widgora Target | June 2026 State-of-the-Art |
|---|---|---|---|
| Schema ownership | ❌ None | ✅ Full | Full ownership + migrations |
| Migration tooling | ❌ N/A | ✅ Atlas versioned | Declarative + CI lint |
| Typed columns (DATE, TIMESTAMPTZ, NUMERIC) | ❌ String parsing | ✅ Native types | Native types mandatory |
| Foreign keys | ❌ Not possible | ✅ Enforced | Always declared |
| Composite indexes | ❌ Not possible | ✅ Designed | Designed from query patterns |
| Partial indexes | ❌ Not possible | ✅ Active-only index | Partial indexes on selective subsets |
| ON CONFLICT upserts | ❌ Not possible | ✅ Idempotent loads | Always atomic upsert |
| Advisory locks | ❌ Not possible | ✅ Job coordination | Transaction-scoped, 2-int namespace |
| Materialized rollups | ❌ Not possible | ✅ mv_daily_run_stats | Refreshed concurrently via cron |
| Audit history | ❌ Not possible | ✅ Immutable audit_events | Trigger-based or app-level insert |
| Connection pooling | ✅ Application pool | ✅ psycopg_pool + PgBouncer | PgBouncer transaction mode + app pool |
| Overload shedding | ✅ HTTP 503 | ✅ Pool exhaustion → 503 | Immediate failure over queuing |
| Single-flight | ✅ Implemented | ✅ Cache tier pattern | asyncio.Lock / singleflight |
| Prometheus metrics | ✅ Full | ✅ Extended (per-query) | Per-query histograms |
| OpenTelemetry traces | ⚠️ Partial | ✅ Full distributed traces | Full correlation from HTTP → SQL |
| Integration tests | ✅ Real DB | ✅ Testcontainers + PG18 | Testcontainers, plan assertions |
| pg_stat_statements | ❌ Not accessible | ✅ Enabled + monitored | Mandatory on all production instances |
| Row-level security | ❌ Not possible | ✅ Tenant isolation | Enforced at database layer |
| UUIDv7 primary keys | ❌ MySQL INT / UUID | ✅ uuidv7() default | UUIDv7 for all distributed PKs |

***

## 15. Prioritized Implementation Roadmap

### Tier 1: Highest ROI, Lowest Risk

1. **Enable `pg_stat_statements` + `auto_explain`** — zero schema change, immediate query visibility. Eliminates "we don't know which query is slow" class of incidents.
2. **Implement keyset pagination** — replace offset-based paging on any table >100K rows. 10–100× improvement on deep pages, zero schema change needed.
3. **Add partial indexes** for active-record subsets (`WHERE status = 'pending'`, `WHERE deleted_at IS NULL`) — concurrently created, dramatically reduces index size and read I/O.
4. **Convert application queries to parameterized** — eliminates SQL injection, enables server-side plan caching. Code change only.
5. **Add `lock_timeout = '3s'` to all migrations** — prevents any migration from causing an outage via lock accumulation.

### Tier 2: Largest Performance Gain

6. **Migrate to UUIDv7** (PostgreSQL 18) — eliminates B-tree fragmentation from random UUID inserts. Upgrade to PG18 triggers the 2–3× async I/O gains simultaneously.[^1][^19]
7. **Add covering indexes** with `INCLUDE` for highest-traffic queries — converts heap-access index scans to index-only scans.
8. **Deploy PgBouncer in transaction mode** — reduces PostgreSQL backend count from max_connections to pool_size, frees ~5–10 MB RAM per connection.
9. **Implement fillfactor=80** on high-churn tables + run VACUUM — enables HOT updates, reduces index maintenance on writes.
10. **Tune PostgreSQL memory** (`shared_buffers` = 25-40% RAM, `work_mem` per workload type, `max_wal_size` = 4GB) — typically 20-50% query throughput improvement.[^69][^70]

### Tier 3: Largest Operational Benefit

11. **Adopt expand-contract migration pattern** — eliminates all deployment downtime caused by schema changes. Requires migration discipline, not new tools.
12. **Implement Testcontainers integration tests** — catches schema bugs, constraint violations, and query plan regressions before production.
13. **Deploy Patroni + HAProxy for HA** (self-hosted) or migrate to Aurora/AlloyDB — eliminates single-node failure risk, enables rolling major version upgrades.
14. **Implement Debezium CDC** for real-time downstream propagation — replaces polling-based sync, reduces source database load.
15. **Add Row-Level Security** for multi-tenant isolation — database-enforced tenant boundary, removes application-level WHERE tenant_id filter as a defense perimeter.

### Tier 4: State-of-the-Art Differentiation

16. **Integrate OpenTelemetry distributed tracing** — HTTP request → cache miss → SQL query → execution plan as a single correlated trace.
17. **Migrate to Atlas declarative migrations** with CI lint — prevents unsafe DDL from reaching production.
18. **Implement dbt + materialized rollups** for analytics — converts expensive dashboard aggregations to sub-millisecond reads.
19. **Evaluate Iceberg integration** (pg_lake / pg_mooncake) for lakehouse use cases — emerging but production-adopted by 2026 early adopters.[^8]
20. **Enable PostgreSQL 18 io_uring** (`io_method = io_uring` on Linux) for sequential scan intensive workloads — up to 3× throughput on cold caches.[^2][^1]

***

## Ranked Checklist: June 2026 SQL Engineering Best Practices

### Physical Design
- [ ] `BIGSERIAL`/`IDENTITY` for single-node PKs; `uuidv7()` for distributed systems
- [ ] Foreign keys declared and enforced on all relationships
- [ ] `CHECK` constraints for domain validation at the database layer
- [ ] `TIMESTAMPTZ` (not `TIMESTAMP`) for all temporal columns
- [ ] `NUMERIC` (not `FLOAT`) for monetary and precise decimal values
- [ ] `JSONB` (not `JSON`) for semi-structured data; GIN indexed
- [ ] Declarative range partitioning by time for tables >100M rows
- [ ] `fillfactor=80` for high-UPDATE OLTP tables

### Indexing
- [ ] Composite indexes ordered: equality cols first, range col last
- [ ] Covering indexes with `INCLUDE` for high-traffic read paths
- [ ] Partial indexes for selective subsets (active, pending, not-deleted)
- [ ] `CREATE INDEX CONCURRENTLY` exclusively in production
- [ ] Monthly audit of `pg_stat_user_indexes` — drop zero-scan indexes
- [ ] `ANALYZE` with raised `default_statistics_target` (500) for join keys

### Query Engineering
- [ ] All queries sargable (no function on indexed column, no implicit cast)
- [ ] Keyset pagination on all large-table paging
- [ ] `EXISTS` instead of `COUNT(*)` for existence checks
- [ ] Parameterized queries exclusively
- [ ] `ON CONFLICT` for all upsert patterns
- [ ] `NOT EXISTS` instead of `NOT IN` with nullable subqueries

### Migrations
- [ ] Expand-contract pattern for all breaking schema changes
- [ ] `lock_timeout = '3s'` in every migration
- [ ] `CREATE INDEX CONCURRENTLY` only (never blocking index creation)
- [ ] NOT NULL added via `NOT VALID` constraint + separate `VALIDATE`
- [ ] Versioned migration files only — no runtime DDL at application start
- [ ] Staging environment at 10%+ of production data size for migration testing

### Application Layer
- [ ] psycopg3 / asyncpg / pgx (not psycopg2 / pg8000)
- [ ] PgBouncer transaction-mode pooling for high connection counts
- [ ] Pool min/max sized to `(cpu_cores × 2)` formula
- [ ] Statement timeout per query (not per connection)
- [ ] Retry with exponential backoff for serialization failures and deadlocks
- [ ] Circuit breaker after N consecutive database failures
- [ ] Advisory locks for distributed job coordination (transaction-scoped)

### Performance
- [ ] `pg_stat_statements` + `auto_explain` enabled on all instances
- [ ] `pg_stat_io` monitored (PG16+)
- [ ] `shared_buffers` = 25-40% RAM
- [ ] `work_mem` tuned per workload (4-16MB OLTP; 64-256MB OLAP)
- [ ] `max_wal_size` = 4GB; `checkpoint_completion_target` = 0.9
- [ ] `io_method = io_uring` on PG18 Linux deployments (2-3x sequential scan gain)
- [ ] Slow query threshold reviewed weekly via `pg_stat_statements` total_exec_time

### Observability
- [ ] Prometheus metrics: QPS, connection utilization, cache hit ratio, replication lag
- [ ] OpenTelemetry distributed traces correlated to database queries
- [ ] Alert: active connections > 80% of max_connections
- [ ] Alert: replication lag > 100MB or 5 seconds
- [ ] Alert: any query waiting on lock > 10 seconds
- [ ] Alert: cache hit ratio < 95%

### Testing
- [ ] Testcontainers (real PostgreSQL) for all integration tests
- [ ] `EXPLAIN ANALYZE` assertions in CI for critical query paths
- [ ] Migration idempotency tested (run suite twice, schema must match)
- [ ] `ON CONFLICT` concurrency tested under parallel insert load

### Security
- [ ] Row-Level Security enabled for multi-tenant tables
- [ ] `SCRAM-SHA-256` authentication (MD5 deprecated PG18)
- [ ] Least-privilege application user (no DDL, no SUPERUSER)
- [ ] Secrets via vault (not env vars in plaintext)
- [ ] Immutable audit table with INSERT-only RLS policy
- [ ] `pg_columnmask` for column masking on Aurora PG16.10+/17.6+
- [ ] Parameterized queries only — zero string interpolation in SQL

***

## Technology Decision Matrix

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Primary key | BIGSERIAL | UUIDv7 | UUIDv7 if distributed; BIGSERIAL otherwise |
| Migration tool | Flyway | Atlas | Atlas for new projects; Flyway for Java shops |
| Python driver | psycopg2 | psycopg3 | psycopg3 (psycopg2 is legacy) |
| Connection pooler | PgBouncer | Pgpool-II | PgBouncer transaction mode |
| HA | Patroni | Cloud-managed | Patroni self-hosted OR Aurora/AlloyDB |
| Analytics | PostgreSQL + dbt | ClickHouse | ClickHouse >10B rows/day; PG otherwise |
| Local analytics | DuckDB | PostgreSQL | DuckDB for single-process analytics |
| CDC | Debezium | JDBC Source | Debezium (log-based, complete change capture) |
| Data quality | Great Expectations | Soda | GX for pipeline validation; Soda for continuous monitoring |
| Pagination | Offset | Keyset | Keyset for tables >10K rows |
| UUID format | UUIDv4 | UUIDv7 | UUIDv7 — native PG18, no performance penalty |

---

## References

1. [Highlights of PostgreSQL 18 - pgEdge](https://www.pgedge.com/blog/highlights-of-postgresql-18) - The Asynchronous I/O (AIO) feature is introduced to boost I/O throughput, especially for sequential ...

2. [Benchmarking Asynchronous I/O in Postgres 18 beta1 - LinkedIn](https://www.linkedin.com/posts/lfittl_postgres-activity-7325918540828413952-l8Od) - With the Postgres 18 beta1 release around the corner (Thursday this week), we decided its time to do...

3. [PostgreSQL UUIDv7 Performance Benchmark: Native vs Custom ...](https://www.saybackend.com/blog/uuidv7-postgres-comparison/) - Key Finding: PostgreSQL 18's native uuidv7() now delivers UUIDv4-parity performance (74.3 vs 71.6 μs...

4. [Database Schema Migrations with Zero Downtime: The Expand ...](https://systemdr.systemdrd.com/p/database-schema-migrations-with-zero) - The pattern decomposes a breaking schema change into three discrete deployment phases, each independ...

5. [UUIDv7 Comes to PostgreSQL 18 - Nile Postgres](https://www.thenile.dev/blog/uuidv7) - PostgreSQL 18 adds native support for UUIDv7. A timestamp-based UUID variant that plays nicely with ...

6. [How we make database schema migrations safe and robust at Defacto](https://www.getdefacto.com/article/database-schema-migrations) - 1. Adopting the Expand -> Migrate -> Contract pattern · Deploy code that writes to both the old and ...

7. [Introducing pg_lake: Integrate Your Data Lakehouse with Postgres](https://www.snowflake.com/en/blog/engineering/pg-lake-postgres-lakehouse-integration/) - Introducing pg_lake, a set of open-source PostgreSQL extensions from Snowflake that allow you to que...

8. [A quiet revolution is happening in Postgres and Iceberg ... - LinkedIn](https://www.linkedin.com/posts/stanislavkozlovski_a-quiet-revolution-is-happening-in-postgres-activity-7414652463770750976-Eb_W) - ... 2025 All these integrate Postgres with Iceberg in different ways. ... - Delta Lake, Apache Icebe...

9. [MySQL 8.0 Is EOL: Upgrade Checklist for 8.4 LTS (5 ... - JusDB](https://www.jusdb.com/blog/mysql-80-eol-in-2026-why-upgrading-to-mysql-84-lts-is-mission-critical) - MySQL 8.0 end-of-life is April 2026. Plan your upgrade to MySQL 8.4 LTS now. Learn migration strateg...

10. [SQL Server 2025: 10 new features that can create value - Cegal](https://www.cegal.com/en/resources/sql-server-2025-10-new-features-that-can-create-value) - SQL Server 2025: 10 new features that can create value · Support for JSON columns · Query optimizati...

11. [SQL Server 2025 has arrived! - SQLServerCentral](https://www.sqlservercentral.com/articles/sql-server-2025-has-arrived) - There are over 40+ new engine features in SQL Server 2025 across security, performance, and availabi...

12. [Running DuckDB in Production: What You Need to Know - Dench](https://www.dench.com/blog/duckdb-in-production) - DuckDB is excellent for analytics. But running it in production requires understanding its specific ...

13. [Top 10 best practices tips for ClickHouse](https://clickhouse.com/blog/10-best-practice-tips) - Ten best practices for getting the most out of ClickHouse, from primary key design and data types to...

14. [Best Practices for Database Schema Design in PostgreSQL - Reintech](https://reintech.io/blog/best-practices-database-schema-design-postgresql) - Best Practices for Database Schema Design in PostgreSQL · Start with Normalization (But Know When to...

15. [PostgreSQL Schema Design Guide: Best Practices and Tools](https://erflow.io/en/blog/postgresql-schema-design-guide) - This guide covers PostgreSQL-specific schema design decisions — data types, indexes, constraints, pa...

16. [Scalable Database Schema Design (2026): 12 Production Patterns](https://www.jusdb.com/blog/database-schema-design-for-scalability-summary-and-best-practices) - Composite Index Design: Order columns based on query patterns and selectivity; Specialized Indexes: ...

17. [PostgreSQL 18 UUIDv7 Support - Generate Timestamp-Ordered ...](https://neon.com/postgresql/18/uuidv7-support) - PostgreSQL 18's UUIDv7 support addresses long-standing performance concerns with using UUIDs as prim...

18. [PostgreSQL 18 New Features: What's New and Why It Matters - Neon](https://neon.com/postgresql/18-new-features) - PostgreSQL 18 was officially released on September 25, 2025, marking one of the most significant rel...

19. [PostgreSQL 18 Released!](https://www.postgresql.org/about/news/postgresql-18-released-3142/) - Introducing asynchronous I/O · Faster upgrades, better post-upgrade performance · Query and general ...

20. [postgresql-table-design - Skill - Smithery](https://smithery.ai/skills/zmre/postgresql-table-design) - Design a PostgreSQL-specific schema. Covers best-practices, data types, indexing, constraints, perfo...

21. [Keyset Cursors, Not Offsets, for Postgres Pagination - Sequin Blog](https://blog.sequinstream.com/keyset-cursors-not-offsets-for-postgres-pagination/) - Learn why keyset-based pagination outperforms traditional offset pagination in Postgres for large da...

22. [API Pagination Guide: Cursor vs Offset vs Keyset for High-Scale ...](https://designgurus.substack.com/p/api-pagination-guide-cursor-vs-offset) - Keyset pagination extends cursors to compound sort keys. Use it when sorting by non-unique columns l...

23. [PostgreSQL Keyset Pagination vs Offset: Cursor-Based Guide for ...](https://www.stacksync.com/blog/keyset-cursors-postgres-pagination-fast-accurate-scalable) - Keyset cursor pagination uses compound cursors to create stable, efficient data traversal by positio...

24. [Postgres 18 Features: Async I/O, UUIDv7, OAuth and More | xata](https://xata.io/blog/going-down-the-rabbit-hole-of-postgres-18-features) - PostgreSQL 18 brings async I/O (2-3x faster sequential scans), native UUIDv7, OAuth 2.0, virtual gen...

25. [Flyway vs. Liquibase: The Definitive Comparison in 2026 | Bytebase](https://www.bytebase.com/blog/flyway-vs-liquibase/) - Both Flyway and Liquibase are Java-based, offering with SDKs and CLI support, and follow a migration...

26. [Database schema migration tools: Flyway vs Liquibase](https://community.databricks.com/t5/data-engineering/database-schema-migration-tools-flyway-vs-liquibase/td-p/146578) - Pick Flyway if you prefer a simple, lightweight solution with sequential migrations and minimal over...

27. [Choosing the Right Schema Migration Tool: A Comparative Guide](https://www.pingcap.com/article/choosing-the-right-schema-migration-tool-a-comparative-guide/) - We will explore three widely-used tools: Flyway, Liquibase, and Alembic. Each tool offers unique fea...

28. [Atlas | Manage your database schema as code](https://atlasgo.io) - Atlas is a language-agnostic tool for managing and migrating database schemas using modern DevOps pr...

29. [Bytebase vs. Atlas: a side-by-side comparison for database schema ...](https://www.bytebase.com/blog/bytebase-vs-atlas/) - Atlas is a migration engine: you declare the schema you want and it generates the SQL to get there. ...

30. [Expand and Contract: Key to Zero Downtime Database Migration](https://www.linkedin.com/pulse/copy-expand-contract-key-zero-downtime-database-mahmud-chowdhury-8gric) - During my studies with database migrations the question of maintaining zero downtime crossed my mind...

31. [The PostgreSQL Locking Trap That Killed Our Production API (and ...](https://www.reddit.com/r/programming/comments/1lfg2bx/the_postgresql_locking_trap_that_killed_our/) - API-encapsulated advisory locks plus human-reviewed SQL keeps your DB safe and flexible.

32. [Zero-Downtime Database Migrations: How-To Guide - SchemaSmith](https://schemasmith.com/guides/zero-downtime-database-migrations.html) - The core techniques are the expand-contract pattern (add new structure before removing old), online ...

33. [Cut Django Database Latency by 50-70ms With Native Connection ...](https://saurabh-kumar.com/articles/2025/06/cut-django-database-latency-by-50-70ms-with-native-connection-pooling/) - Deploy Django 5.1's native connection pooling in 10 minutes to cut database latency by 50-70ms, redu...

34. [Connection pools - psycopg 3.3.5.dev1 documentation](https://www.psycopg.org/psycopg3/docs/advanced/pool.html) - A connection pool is an object managing a set of connections and allowing their use in functions nee...

35. [Boost Your Application Performance With Asyncpg and PostgreSQL](https://www.tigerdata.com/blog/how-to-build-applications-with-asyncpg-and-postgresql) - Connection pooling is a crucial feature of asyncpg. It means that instead of opening and closing the...

36. [(Postgres) Using the Psycopg 3 connection pool in SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy/discussions/12522) - Psycopg 3 has a nice psycopg_pool.ConnectionPool implementation ・ that can automatically disconnect ...

37. [PostgreSQL High Availability: A Practical Guide with Patroni ...](https://instadevops.com/blog/postgresql-high-availability-patroni-pgbouncer-guide/) - This guide walks through a production-ready PostgreSQL HA setup using the tools that have become the...

38. [The Best PostgreSQL Hosting for Developers in 2026 - Railway Blog](https://blog.railway.com/p/best-postgresql-hosting-2026) - Railway shipped one-click HA Postgres on Patroni in March 2026, which means a developer can provisio...

39. [PostgreSQL Advisory Locks, explained (with real-world patterns)](https://flaviodelgrosso.com/blog/postgresql-advisory-locks) - A practical guide to PostgreSQL advisory locks. What they are, when to use them, how to use them saf...

40. [What are Postgres advisory locks and their use cases](https://dev.to/oleg_potapov/what-are-postgres-advisory-locks-and-their-use-cases-49nd) - Another feature of Postgres advisory locks is a behavior control on conflict. It allows a different ...

41. [What auto_explain sees that pg_stat_statements does not - Datapace](https://datapace.ai/blog/pgstat-vs-autoexplain) - pg_stat_statements and auto_explain are the two diagnostic extensions every production Postgres inst...

42. [Best Open Source Tools for PostgreSQL Monitoring & Observability](https://vela.simplyblock.io/articles/best-open-source-postgresql-monitoring-observability-tools/) - pg_stat_statements is often the first tool to enable because it exposes the queries that consume the...

43. [[PDF] Boosting Typical Query Patterns - PostgreSQL 18's Performance ...](https://www.postgresql.eu/events/pgconfeu2025/sessions/session/7008/slides/754/pg18-performance-talk-present.pdf) - Configuration and Performance. Async I/O: Benchmark Results. Key Findings: Sequential scans: 15-25% ...

44. [6 Hard-Won Lessons from Building dbt Models at Enterprise Scale](https://www.linkedin.com/pulse/6-hard-won-lessons-from-building-dbt-models-enterprise-jack-fang-nmj2c) - When starting with dbt, the conventional wisdom is simple: use incremental models for large tables. ...

45. [7 Best Change Data Capture (CDC) Tools in 2025 - LinkedIn](https://www.linkedin.com/pulse/7-best-change-data-capture-cdc-tools-in2025-bladepipe-9govc) - Debezium is an open-source distributed platform for change data capture. Built on top of Apache Kafk...

46. [Kafka Change Data Capture (CDC): The Complete Guide [2026]](https://factorhouse.io/articles/kafka-cdc-change-data-capture) - Learn how to implement change data capture with Kafka using Debezium. Includes working PostgreSQL CD...

47. [How to Write Effective dbt Models - OneUptime](https://oneuptime.com/blog/post/2026-01-27-dbt-models-effective/view) - A practical guide to writing effective dbt models - covering organization, materialization strategie...

48. [Take Your First Steps with EDB Postgres AI Analytics Accelerator](https://www.enterprisedb.com/blog/take-your-first-steps-edb-postgres-ai-analytics-accelerator) - Analytics Accelerator supports querying popular open table formats like Apache Iceberg and Delta Lak...

49. [Monitoring PostgreSQL Metrics with OpenTelemetry - Randoli](https://www.randoli.io/blogs/monitoring-postgresql-metrics-with-opentelemetry) - In this guide, we'll walk through the two main approaches to monitoring Postgresql, comparing their ...

50. [How to Use OpenTelemetry with Postgres - Last9](https://last9.io/blog/how-to-use-opentelemetry-with-postgres/) - Learn how to set up OpenTelemetry with Postgres to trace queries, monitor performance, and get bette...

51. [Spring Boot Testcontainers integration testing: what to test with real ...](https://bitdive.io/blog/spring-boot-testcontainers-integration-testing/) - Use Testcontainers when you need to verify migrations, complex SQL dialects, and locking behavior. U...

52. [Testcontainers Best Practices for .NET Integration Testing](https://www.milanjovanovic.tech/blog/testcontainers-best-practices-dotnet-integration-testing) - Testcontainers transforms integration testing by giving you the confidence that comes from testing a...

53. [Integration Testing with Real Databases Using Testcontainers](https://dev.to/imdj/integration-testing-with-real-databases-using-testcontainers-2k62) - TL;DR: Testcontainers lets you run real SQL Server in Docker inside your tests. This guide shows how...

54. [Shift-Left Testing with Testcontainers - Docker](https://www.docker.com/blog/shift-left-testing-with-testcontainers/) - Using Testcontainers Cloud locally and in CI ensures consistent testing outcomes, giving you greater...

55. [How to Deploy a Highly Available PostgreSQL 16 Cluster ... - Onidel](https://onidel.com/blog/deploy-high-availability-postgresql) - This comprehensive tutorial will guide you through deploying a three-node PostgreSQL 16 cluster usin...

56. [PostgreSQL High Availability: Patroni, Replication and Failover ...](https://dev.to/philip_mcclarence_2ef9475/postgresql-high-availability-patroni-replication-and-failover-patterns-4f6k) - PostgreSQL high availability is a solved problem in 2026. But ... Patroni is the tool most teams rea...

57. [Postgres 17 and 18 in Production: The Features Worth Migrating For](https://www.birjob.com/blog/postgres-17-18-production-2026) - Postgres 18 shipped on September 25, 2025, and the headline feature is the asynchronous I/O subsyste...

58. [Best Managed Postgres for Analytics 2026 - Definite.app](https://www.definite.app/blog/best-managed-postgres-for-analytics) - We compare 7 options — Aurora PostgreSQL, AlloyDB, Citus on Cosmos DB for PostgreSQL, Crunchy Data, ...

59. [Best Managed PostgreSQL Cloud Providers in 2026 - QueryPlane](https://queryplane.com/blog/top-managed-postgresql-cloud-providers/) - Aurora claims up to 3x the throughput of standard PostgreSQL. AlloyDB is 4x faster than standard Pos...

60. [Neon Serverless Postgres: Complete Guide for TypeScript Developers](https://encore.dev/articles/neon-serverless-postgres) - Neon makes PostgreSQL work the way developers expect databases to work in 2026: instant provisioning...

61. [Neon Serverless Postgres Pricing 2026: Complete Breakdown &…](https://vela.simplyblock.io/articles/neon-serverless-postgres-pricing-2026/) - After the Databricks acquisition in May 2025, Neon introduced new usage-based pricing in August, cut...

62. [Why Use DuckDB? - by Madison Mae - Learn Analytics Engineering](https://learnanalyticsengineering.substack.com/p/why-use-duckdb) - It allows for multi-user data access, cloud scalability without the headache of managing the infrast...

63. [ClickHouse: Production Monitoring & Optimization Tips](https://bigdataboutique.com/blog/clickhouse-production-monitoring-and-optimization-tips-9b26bc) - Key insights from our webinar on monitoring and optimizing ClickHouse in production - covering part ...

64. [Row-level and Column-level Security - Oracle vs PostgreSQL](https://hexacluster.ai/blog/row-level-and-column-level-security-oracle-vs-postgresql) - For column-level protection, Oracle users typically choose between Data Redaction for on-the-fly mas...

65. [Protect sensitive data with dynamic data masking for Amazon Aurora ...](https://aws-news.com/article/2025-11-24-protect-sensitive-data-with-dynamic-data-masking-for-amazon-aurora-postgresql) - This article announces dynamic data masking (DDM) for Amazon Aurora PostgreSQL, a new security featu...

66. [Amazon Aurora PostgreSQL introduces dynamic data masking - AWS](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-aurora-postgresql-dynamic-data-masking/) - Using pg_columnmask, you can control access to sensitive data through SQL-based masking policies and...

67. [SingleFlight: Smart Request Deduplication - DEV Community](https://dev.to/serifcolakel/singleflight-smart-request-deduplication-33og) - This article explains the pattern, shows code, and contains a benchmarking methodology you can run l...

68. [How to Reduce DB Load with Request Coalescing in Python](https://oneuptime.com/blog/post/2026-01-23-request-coalescing-python/view) - Request coalescing, also known as request deduplication or single-flighting, is a technique where co...

69. [How to Tune PostgreSQL Performance for Production - OneUptime](https://oneuptime.com/blog/post/2026-02-20-postgresql-performance-tuning/view) - A practical guide to tuning PostgreSQL performance including shared_buffers, work_mem, and query opt...

70. [PostgreSQL Performance Tuning Best Practices 2025 - Mydbops](https://www.mydbops.com/blog/postgresql-parameter-tuning-best-practices) - Optimize PostgreSQL for OLTP, OLAP, and high-write workloads with expert tuning tips on memory, WAL,...

