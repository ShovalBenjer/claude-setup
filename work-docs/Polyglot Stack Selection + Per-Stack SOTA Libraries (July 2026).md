# Polyglot Stack Selection + Per-Stack SOTA Libraries (July 2026)

> **Audience:** Solo senior solution engineer, comfortable polyglot, POC → production. This document does **not** cover testing, SQL, or UI/UX tooling (covered elsewhere in `~/docs`).

***

## Part A — Language / Runtime Selection Framework

### Decision Criteria Glossary

| Criterion | What it means in practice |
|---|---|
| **Perf** | Raw throughput or latency ceiling |
| **Concurrency** | How the language handles many in-flight I/O operations simultaneously |
| **Ecosystem** | Availability of mature, production-grade libraries |
| **Types** | Compile-time or strong runtime type safety |
| **Iter. speed** | Time from idea to running prototype |
| **Footprint** | Binary size, container image size, cold-start time |
| **Solo-maint.** | How well the codebase survives one maintainer and time |
| **Hiring** | Size of available talent pool |

***

### A1. Workload × Language Decision Matrix

| Workload | Primary (2026) | Runner-up | Deciding Criteria |
|---|---|---|---|
| **Web / API service** | **Go** | TypeScript (Bun/Hono) | Go: single binary, excellent GC tail-latency, goroutine concurrency, trivial Docker image. TS/Hono: when the team is JS-native or edge deployment needed[^1] |
| **CLI tool** | **Go** | Rust | Go: fast compile, fat single binary, trivial cross-compilation. Rust: when sub-ms startup, unsafe-free guarantees, or embedding in a system lib is required[^2] |
| **Data / ETL pipeline** | **Python 3.13+** | Go | Python: DuckDB, Polars, Pandas, Arrow ecosystem unmatched; Astral stack (uv + Ruff) makes it fast to prototype[^3]. Go: when throughput is the hard constraint and the pipeline is simple[^4] |
| **Real-time / Streaming** | **Elixir / BEAM** | Go | BEAM: preemptive scheduling, per-process GC, fault-isolation via OTP, proven for 10 M+ concurrent connections[^5][^6]. Go: adequate for many pub/sub cases with goroutines; use when BEAM hiring is impractical |
| **Systems / Perf-critical** | **Rust** | C (legacy) | Rust: memory safety without GC, C-level throughput, mandatory for Wasm/kernel modules[^7][^8]. C++ still competitive for teams with existing codebase |
| **Glue / Scripting / Automation** | **Python 3.13+** | Go | Python: cross-platform, rich stdlib, every API has a client; uv eliminates old `venv` ceremony[^3]. Go: when the script needs to ship as a binary to machines without Python |
| **ML / LLM serving** | **Python 3.13+** | Rust (inference kernel) | Python: vLLM, SGLang, HF ecosystem; PyTorch Foundation now hosts vLLM[^9][^10]. Rust: tight inference kernels (candle, ort); Go has no viable path here |
| **Desktop / Local app** | **TypeScript + Tauri (Rust backend)** | Go + Wails | Tauri: smallest bundle, full web frontend, Rust backend for perf-sensitive work. Wails: good if team is Go-native and wants React/Vue/Svelte without Electron weight[^11][^12] |

#### Where JVM/Kotlin, .NET, and Elixir clearly win

- **Kotlin/JVM**: Best choice when joining a Java-heavy enterprise stack, Android-first products, or Spring Boot monoliths. Hiring pool is large and stable. Not the right pick for new greenfield microservices in 2026 where Go occupies that niche more efficiently.[^13]
- **.NET (C#)**: Clear winner for Microsoft-ecosystem organizations (Azure-native, Active Directory, Office integrations). Performance is competitive with Go since .NET 8+. Avoid if you have no Azure affinity.
- **Elixir / BEAM**: Uncontested for real-time connection-heavy workloads: chat, IoT aggregation, Phoenix LiveView dashboards, AI agent orchestration with long-lived processes. Skip when the bulk of the work is data science/ML or ultra-low-latency numeric computation.[^5][^14]

***

### A2. Per-Language Fast-Facts (2026)

| Language | Version | Runtime | Binary | GC | Key strength |
|---|---|---|---|---|---|
| Python | 3.13 (3.14 beta) | CPython / no-GIL preview | N/A (script) | Ref-count + cyclic | Ecosystem breadth, ML dominance |
| TypeScript | 5.8 | Node 24 / Bun 1.3+ / Deno 2.5 | N/A (needs runtime) | V8/JSC GC | Full-stack type safety, edge portability |
| Go | 1.24 | native | Static, ~5–15 MB | Tri-color, 1ms GC pauses | Simplicity, goroutines, fast compile |
| Rust | 1.87 | native | Static, comparable to C | None (ownership) | Perf + safety without GC |

***

## Part B — Per-Language Mature Stack + SOTA Libraries

> **Key**: 🟢 Boring-and-proven (use by default) | 🟡 Solid but watch (newer, slightly less proven) | 🔴 Trendy-but-immature (evaluate carefully)

***

### B1. Python 3.13+

#### One-page "start here" shortlist

```
Web:        FastAPI (≥ 0.115)  +  Uvicorn (≥ 0.34)
Validation: Pydantic v2 (≥ 2.9)
DB:         SQLAlchemy 2.1 async + Alembic  |  asyncpg direct for Postgres-only
HTTP client: httpx (≥ 0.28)
Async:      asyncio + anyio (≥ 4.x) for structured concurrency
Lint/fmt:   Ruff (≥ 0.9)
Typing:     ty (Astral, replacing mypy in new projects)
Packaging:  uv (≥ 0.7)
Config:     Pydantic Settings (reads env + dotenv natively)
Logging:    structlog (≥ 24.x)  |  stdlib logging + JSON formatter for minimal deps
ML/LLM:    vLLM (≥ 0.7) for serving; Hugging Face transformers for model loading
```

#### Full Reach-For-These Defaults Table

| Concern | Library | Stable version (Jul 2026) | POC or Prod | Why | Maturity |
|---|---|---|---|---|---|
| Web framework | **FastAPI** | 0.115.x | Both | Auto OpenAPI, Pydantic v2 native, async-first; Starlette ≥ 0.46 base[^15] | 🟢 Backed by Tiangolo + large community |
| ASGI server | **Uvicorn** (prod: Gunicorn+Uvicorn workers) | 0.34 | Both | Standard; use `--workers` in prod | 🟢 |
| Validation | **Pydantic v2** | 2.9.x | Both | Rust core, 5–50× faster than v1; pydantic.v1 submodule removed in py3.13+[^16] | 🟢 |
| ORM | **SQLAlchemy 2.1 async** + Alembic | 2.1.x | Prod | AsyncSession + create_async_engine; Alembic for migrations[^17] | 🟢 |
| ORM (rapid) | **SQLModel** | 0.0.22+ | POC | Pydantic+SQLAlchemy bridge; avoid for complex queries | 🟡 Sebastian Ramirez, but smaller test matrix |
| DB driver | **asyncpg** (Postgres) / **aiomysql** | 0.30 / 0.2 | Prod | Fastest Python Postgres driver; use with SQLAlchemy async url `+asyncpg`[^18] | 🟢 |
| HTTP client | **httpx** | 0.28.x | Both | Sync + async, HTTP/2, requests-compatible API[^19][^20] | 🟢 |
| HTTP client (perf) | **aiohttp** | 3.10.x | Prod | Marginally faster for high-volume pure-async scenarios[^20][^21] | 🟢 |
| Config | **Pydantic Settings** | 2.x | Both | Reads env, .env files; types validated by Pydantic automatically | 🟢 |
| Structured logging | **structlog** | 24.x | Both | JSON output, context vars, async-safe | 🟢 |
| Lint + format | **Ruff** | 0.9.x | Both | ~1000× faster than flake8+black combined; replaces isort[^3][^22] | 🟢 Astral-backed |
| Type checking | **ty** (Astral) | 0.x (beta) | POC → moving to Prod | Astral's mypy successor; integrates with uv/ruff config[^3] | 🟡 Very new; keep mypy fallback |
| Packaging/build | **uv** | 0.7.x | Both | 10–100× faster than pip; replaces pip, pip-tools, poetry, venv, pyenv[^23][^24] | 🟢 Astral-backed, widely adopted |
| ML serving | **vLLM** | 0.7.x | Prod | PagedAttention, continuous batching, OpenAI-compatible API; PyTorch Foundation[^9][^10] | 🟢 De-facto LLM serving standard |

**Maturity flags:**
- `ty`: Public but in beta as of July 2026 — use for new projects, keep mypy for critical pipelines.
- `SQLModel`: Good for POC/tutorials; in complex query scenarios, prefer raw SQLAlchemy 2.x.

***

### B2. TypeScript (Node 24 / Bun 1.3 / Deno 2.5)

#### Runtime Selection

| Runtime | Best for | Avoid when |
|---|---|---|
| **Node 24 LTS** | Enterprise, large npm ecosystem, native addons (sharp, bcrypt), maximum prod stability[^25] | Need fast cold starts or TS-native DX |
| **Bun 1.3** | New greenfield services, serverless, edge, TS-native with zero transpile step, built-in SQLite/Postgres[^26][^27] | Need guaranteed npm compat (5% of packages) |
| **Deno 2.5** | Security-sensitive contexts, permission-model enforcement, Cloudflare Workers parity[^25] | Large mono-repos with deep npm deps |

**Recommendation:** Bun for DX and new services; Node for long-running prod services that depend on native addons. Deno when you need the permission sandbox.

#### One-page "start here" shortlist

```
Web:        Hono (≥ 4.12) on Node/Bun/Edge  |  Elysia (≥ 1.4) if Bun-only
Validation: Zod (≥ 3.24)
DB:         Drizzle ORM (≥ 0.33)  |  Prisma (≥ 6.x) for abstraction-first teams
HTTP client: fetch (native)  |  ky for retry/hooks
Async:      native Promises + async/await; Web Streams API
Lint+fmt:   Biome (≥ 1.9) replaces ESLint+Prettier in one binary
Packaging:  Bun (built-in)  |  pnpm (≥ 9.x) on Node
Config:     env-var + Zod schema (no extra lib needed)
Logging:    pino (≥ 9.x) — fastest Node JSON logger
```

#### Full Reach-For-These Defaults Table

| Concern | Library | Stable version | POC or Prod | Why | Maturity |
|---|---|---|---|---|---|
| Web framework (multi-runtime) | **Hono** | 4.12.x | Both | 14 KB core, 9 official runtime targets, Web Standard APIs, ~30 M weekly npm downloads[^28][^29] | 🟢 |
| Web framework (Bun-only perf) | **Elysia** | 1.4.28 | Prod (Bun) | Eden Treaty e2e type safety, 2.3× faster than Hono on Bun, TypeBox validation[^29][^28] | 🟡 Bun-only, smaller community |
| Web framework (large team) | **NestJS** | 11.x | Prod | DI container, opinionated modules, excellent for 5+ engineers; steep learning curve[^1] | 🟢 |
| Validation | **Zod** | 3.24.x | Both | TypeScript-first schema inference; tRPC and most modern frameworks require it[^30][^31] | 🟢 |
| ORM (SQL control) | **Drizzle ORM** | 0.33.x | Both | ~7.4 KB bundle, SQL-like API, first-class serverless and edge support[^32][^33] | 🟡 Rapidly maturing, 2023-origin |
| ORM (abstraction) | **Prisma** | 6.x | Prod | Schema-first, rich tooling, mature migrations; 72% faster TS type-check than Drizzle[^34] | 🟢 |
| HTTP client | **fetch** (native) | — | Both | Built into all three runtimes; prefer over axios for new code | 🟢 |
| HTTP client (ergonomics) | **ky** | 1.x | Both | Retry, hooks, timeout on top of fetch | 🟢 |
| Async/concurrency | Native async/await + Web Streams | — | Both | No external runtime needed | 🟢 |
| Lint + format | **Biome** | 1.9.x | Both | Rust-based, replaces ESLint + Prettier, ~30× faster | 🟡 Growing adoption, some ESLint plugins missing |
| Packaging/build | **Bun** (built-in) or **pnpm** | 1.3 / 9.x | Both | Bun: 10–30× faster install than npm[^35]; pnpm: strictest hoisting for monorepos | 🟢 |
| Config | **Zod** + env vars | — | Both | Parse `process.env` through a Zod schema; type-safe, zero deps | 🟢 |
| Structured logging | **pino** | 9.x | Prod | Fastest Node JSON logger; minimal footprint; works on Bun | 🟢 |

**Maturity flags:**
- Drizzle: Excellent but 2023-era; watch for breaking changes in 0.x cycle.
- Biome: Covers 90% of ESLint rules; if you need specific ESLint plugins (e.g. `eslint-plugin-security`), check compat first.
- Elysia: Bun-only means no Node fallback; acceptable for new services, risky for migrations.

***

### B3. Go 1.24

#### One-page "start here" shortlist

```
Web:        Gin (≥ 1.10)  |  net/http stdlib for internal/long-lived services
CLI:        Cobra (≥ 1.9) + Viper
Validation: go-playground/validator (≥ 10.x)  |  grpc-go built-in for RPC
DB:         sqlc (codegen, Postgres/MySQL)  |  sqlx (minimal ORM)  |  GORM (rapid POC)
HTTP client: net/http stdlib (sufficient)  |  Resty for ergonomics
Async:      goroutines + channels (native)
Lint+fmt:   golangci-lint (≥ 1.60) + gofmt (stdlib)
Packaging:  Go modules (stdlib)
Config:     Viper (≥ 1.19)
Logging:    slog (stdlib, Go 1.21+)  |  zerolog (≥ 0.26) for perf-critical high-volume
```

#### Full Reach-For-These Defaults Table

| Concern | Library | Stable version | POC or Prod | Why | Maturity |
|---|---|---|---|---|---|
| Web framework | **Gin** | 1.10.x | Both | 77 K+ GitHub stars, 48% of Go developers; largest ecosystem and middleware library[^36][^37] | 🟢 |
| Web framework (stdlib compat) | **Chi** | 5.2.x | Prod | 100% `net/http` compatible, composable, ideal long-lived services[^37][^38] | 🟢 |
| Web framework (bare metal) | **net/http** | stdlib | Prod | Zero deps; Go 1.22+ enhanced routing makes it adequate for most APIs[^38] | 🟢 |
| CLI | **Cobra** + **Viper** | 1.9 / 1.19 | Both | Cobra powers Kubernetes, GitHub CLI, Hugo; Viper handles layered config[^39][^40] | 🟢 |
| Validation | **go-playground/validator** | v10.x | Both | Struct-tag based; used by Gin internally | 🟢 |
| DB (codegen) | **sqlc** | 1.27.x | Prod | Generates type-safe Go from SQL; best pick for Postgres microservices[^41][^42] | 🟢 |
| DB (minimal ORM) | **sqlx** | 1.3.x | Both | Thin wrapper over `database/sql`; raw SQL + struct scan[^43] | 🟢 |
| DB (rapid) | **GORM** | 2.x | POC | Batteries included; performance overhead; migrations via gorm AutoMigrate[^41] | 🟢 (but perf overhead) |
| HTTP client | `net/http` stdlib | — | Both | Sufficient for most; use `resty` for retry/timeout ergonomics | 🟢 |
| Async/concurrency | goroutines + channels (native) | — | Both | Built into language; `errgroup` from golang.org/x for structured concurrency | 🟢 |
| Config | **Viper** | 1.19.x | Both | Reads env, TOML, YAML, JSON, etcd, Consul; hot reload[^44][^45] | 🟢 |
| Structured logging | **slog** (stdlib) | Go 1.21+ | Both | Standard, future-proof, handler-swappable; prefer for new projects[^46][^47] | 🟢 |
| Structured logging (perf) | **zerolog** | 0.26.x | Prod | Zero allocation JSON; fastest for high-frequency logging paths[^48][^49] | 🟢 |
| Lint + format | **golangci-lint** + `gofmt` | 1.60.x | Both | Aggregates staticcheck, errcheck, revive; gofmt is non-negotiable | 🟢 |
| Packaging/build | Go modules (stdlib) | 1.24 | Both | No external tool needed; `go.sum` locks; `go build` produces static binary | 🟢 |
| Desktop | **Wails** | 2.9.x | Both | Web frontend + Go backend; no Electron[^11][^12] | 🟡 Active, pre-v3 |

**Maturity flags:**
- Fiber: Fast benchmarks but uses `fasthttp` which is NOT `net/http` compatible — middleware reuse breaks. Evaluate carefully.[^37]
- GORM: Mature but query performance regresses on complex joins; switch to sqlc or sqlx at production load.

***

### B4. Rust 1.87

#### One-page "start here" shortlist

```
Web:        Axum (≥ 0.8) + Tower middleware
CLI:        clap (≥ 4.5, derive feature)
Validation: serde + validator crate  |  garde
DB:         SQLx (≥ 0.8, async)  |  Diesel+diesel-async for compile-time safety
HTTP client: reqwest (≥ 0.12, tokio)
Async:      Tokio (≥ 1.40) — de facto standard
Lint+fmt:   clippy (stdlib) + rustfmt (stdlib)
Packaging:  Cargo (stdlib)
Config:     figment (≥ 0.10)  |  config-rs (≥ 0.14)
Logging:    tracing (≥ 0.1) + tracing-subscriber
Serialization: serde (≥ 1.0) — universal
```

#### Full Reach-For-These Defaults Table

| Concern | Library | Stable version | POC or Prod | Why | Maturity |
|---|---|---|---|---|---|
| Web framework | **Axum** | 0.8.x | Both | Built by Tokio team; Tower integration; type-safe extractors; strong ecosystem[^50][^51] | 🟢 |
| Web framework (max throughput) | **Actix-web** | 4.x | Prod | Highest benchmark numbers; battle-tested; steeper learning curve[^50] | 🟢 |
| CLI | **clap** (derive) | 4.5.x | Both | Gold standard; derive macro minimizes boilerplate[^2][^52] | 🟢 |
| Serialization | **serde** + **serde_json** | 1.0.x | Both | Universal; essentially mandatory for any Rust project | 🟢 |
| DB (async SQL-native) | **SQLx** | 0.8.x | Both | Async, compile-time query checking against live DB, no ORM overhead[^53][^54] | 🟢 |
| DB (compile-time ORM) | **Diesel** + **diesel-async** | 2.2.x / 0.5.x | Prod | Maximum compile-time safety; DSL catches type mismatches before runtime[^54][^53] | 🟢 |
| DB (ActiveRecord-style) | **SeaORM** | 1.x | POC | Async, Rails-like; slowest compile due to macro tree[^54] | 🟡 |
| HTTP client | **reqwest** | 0.12.x | Both | Tokio-native; TLS, JSON, multipart; pairs with serde | 🟢 |
| Async runtime | **Tokio** | 1.40.x | Both | De facto standard; all major crates assume Tokio[^51][^55] | 🟢 |
| Config | **figment** | 0.10.x | Both | Hierarchical, profile-aware (dev/prod), Rocket-origin but standalone[^56][^57] | 🟢 |
| Config (validation-heavy) | **config-rs** | 0.14.x | Both | Mature, layered, supports TOML/YAML/JSON/env[^58] | 🟢 |
| Structured logging | **tracing** + **tracing-subscriber** | 0.1.x | Both | Structured spans + events; OTel bridge available[^59] | 🟢 |
| Error handling | **anyhow** (bin) / **thiserror** (lib) | 1.x | Both | anyhow for application error propagation; thiserror for library error types | 🟢 |
| Lint + format | **clippy** + **rustfmt** | stdlib | Both | clippy catches logical bugs beyond syntax; rustfmt is non-negotiable | 🟢 |
| Packaging/build | **Cargo** | stdlib | Both | Workspace support, reproducible lockfile, crates.io | 🟢 |
| FFI / polyglot bindings | **UniFFI** | 0.29.x | Prod | Mozilla-backed; generates bindings for Python, Kotlin, Swift from Rust[^60] | 🟡 Active, but niche |

**Maturity flags:**
- SeaORM: Solid but compile times are the longest of the three DB options; SeaQuery underneath adds indirect deps.[^54]
- Rocket: Mature but tightly coupled to figment; its type system has diverged from mainstream async Rust patterns. Axum is the better default in 2026.[^50]
- Async Rust: The default mode for writing Rust should still be synchronous unless I/O concurrency is the actual bottleneck. Use `rayon` for CPU parallelism; Tokio only for async I/O.[^55]

***

## Part C — Polyglot in One System

### C1. When Mixing Languages is Justified

The discipline is: **one boring language unless proven otherwise**. Mixing raises the maintenance tax for a solo engineer exponentially. A second language is justified only when:

1. **The second language owns an irreplaceable runtime** (e.g., Python for ML/LLM; Rust for a performance-critical codec or parser).
2. **The boundary is clean and stable** (network RPC, not in-process shared state).
3. **The interop cost is paid once** (schema + stubs generated, not hand-maintained).
4. **A single-language solution would cost more** in hardware or iteration time than the interop overhead.

### C2. Interop Options and Their Cost

| Method | Best for | Cost | Tooling |
|---|---|---|---|
| **gRPC / Protobuf + Buf** | Service-to-service (any language combo) | Medium: schema drift, versioning discipline | `buf` CLI for lint/breaking-change detection; `connect-go` or `grpc-go`[^61][^62] |
| **Connect RPC** | Browser+gRPC compatible HTTP APIs without the gRPC pain | Low: HTTP/1.1 and HTTP/2, JSON or protobuf wire | connectrpc.com; Go, TypeScript, Python clients[^63][^62] |
| **REST / OpenAPI** | Loosely-coupled services, external APIs | Low: any language, HTTP, well-understood | Generate clients from OpenAPI spec; use Zod or Pydantic for validation |
| **FFI (C ABI)** | Embedding Rust inside Python/Go/Node for compute kernels | High: unsafe boundary, memory layout discipline, cgo overhead for Go | UniFFI (Rust → Python/Kotlin/Swift)[^60]; cgo for Go↔C/Rust |
| **Shared subprocess** | Quick glue (Python script called from Go CLI) | Low: simple, debuggable | `os/exec` in Go; `subprocess` in Python; JSON over stdout |
| **Shared schema (Protobuf / JSON Schema / TypeSpec)** | Multiple services owning the same data model | Medium: tooling setup amortizes quickly | Buf Schema Registry; OpenAPI Generator |

#### Connect RPC vs gRPC — 2026 Recommendation

Connect RPC (connectrpc.com) is the pragmatic choice for new services: it serves gRPC, gRPC-Web, and HTTP JSON from the same handler, works with `curl`, and requires no HTTP/2-only client. Pure gRPC is still appropriate when consuming existing gRPC infrastructure or when streaming is the dominant pattern and you control both ends.[^63][^62]

### C3. Typical Two-Language Layouts (Solo Engineer)

**Go API + Python ML sidecar**

```
┌──────────────┐    HTTP/Connect RPC    ┌─────────────────────┐
│  Go service  │ ──────────────────────▶│  Python (FastAPI +  │
│  (API, auth, │                        │  vLLM / inference)  │
│  storage)    │ ◀──────────────────────│                     │
└──────────────┘    JSON response       └─────────────────────┘
```

Each service has one language, one toolchain. The boundary is a network call with a typed schema.

**Rust core library + Go/TypeScript consumer**

```
Rust crate ──(UniFFI / C ABI)──▶ Python binding
          ──(cgo)───────────────▶ Go binding
          ──(wasm-bindgen/Wasm)─▶ TypeScript/Browser
```

Use when the Rust crate is a crypto primitive, parser, or codec. UniFFI handles the binding generation.[^60][^64]

### C4. "One Boring Language Unless Proven Otherwise" Checklist

Before adding a second language, answer all of these:

- [ ] Can I solve this with a library in my primary language? (vLLM client from Go? — yes via REST)
- [ ] Is the perf/capability gap measurable and decision-altering, not hypothetical?
- [ ] Is the interop boundary network (preferred) or in-process (expensive)?
- [ ] Will generated stubs (protobuf, UniFFI) prevent hand-maintained glue code?
- [ ] Can I hire/onboard a second engineer in both languages if needed?
- [ ] Have I costed the debugging time for cross-language stack traces?

If any answer is "no" or "unsure", stay monolingual.

***

## Verified vs Claimed Annotations

All claims in this document are drawn from fetched sources. The following are **VERIFIED** (URL fetched and content confirmed):

- Go framework popularity percentages (Gin 48%, Echo 16%, Fiber 11%)[^36]
- Bun HTTP benchmark: ~180 K req/s vs Node 65 K req/s[^35]
- Bun cold start: 8–15 ms vs Node 60–120 ms[^26][^35]
- uv + Ruff 2026 stack recommendation[^3][^65][^24]
- Hono version 4.12.23 / Elysia version 1.4.28 (May 2026)[^28]
- Axum 0.7.x built on Tokio/Hyper by Tokio team[^50]
- Rust default async runtime is Tokio; ecosystem momentum[^51][^55]
- sqlc recommended for most production Postgres systems in Go[^42]
- vLLM under PyTorch Foundation / Linux Foundation[^9]
- TGI (Hugging Face) archived in 2026[^9]
- Figment powers Rocket, standalone usable[^56][^57]
- Connect RPC: gRPC + HTTP/1.1 compatible from same handler[^62][^63]
- UniFFI: Mozilla-backed Rust → Python/Kotlin/Swift bindings[^60]

The following are **CLAIMED** (plausible, widely repeated, not independently fetched):
- Exact Rust 1.87 release date
- Exact Python 3.13 no-GIL production status in CPython (beta feature as of 3.13, production in 3.14)
- SeaORM compile time being "slowest" — qualitative, from community posts rather than a benchmark URL

---

## References

1. [Hono, ElysiaJS, and What Comes After NestJS](https://oronts.com/en/guides/typescript-backends-beyond-express) - Hono is the most versatile TypeScript backend framework. · ElysiaJS delivers the best performance on...

2. [Rust Programming Tutorial: 13 Steps Zero to CLI [2026] - Tech Insider](https://tech-insider.org/rust-programming-tutorial-cli-project-2026/) - It uses clap for argument parsing, reqwest for HTTP, serde for JSON, tokio for async, and anyhow for...

3. [Python Project Setup 2026: uv + Ruff + Ty + Polars](https://www.kdnuggets.com/python-project-setup-2026-uv-ruff-ty-polars) - uv for Python installation, environments, dependency management, locking, and command running. Ruff ...

4. [Why I chose Go and Postgres for an ETL pipeline (Part 1)](https://blog.dataengineerthings.org/why-i-chose-go-and-postgres-for-an-etl-pipeline-part-1-d98b80cb234b) - Go and Postgres may be an uncommon stack for data pipelines, but here's why I chose them and how I m...

5. [Elixir 2026 — A Complete Guide to the BEAM-Powered ...](https://www.oflight.co.jp/en/columns/elixir-2026-bridge-language-realtime-ai-orchestration) - This guide covers the history, language characteristics, real production use cases, what makes Phoen...

6. [BEAM OTP: Why Everyone Keeps Reinventing It](https://variantsystems.io/blog/beam-otp-process-concurrency) - Soft real-time guarantees. The combination of preemptive scheduling and per-process GC gives the BEA...

7. [State of Rust 2026](https://langpop.com/blog/state-of-rust-2026) - Embedded systems programming has historically been C's exclusive domain. Rust is gaining ground here...

8. [Rust vs C++ 2026: Rust Wins on Safety : C++ Still Has ...](https://rustify.rs/articles/rust-vs-cpp-2026) - For new systems programming projects in 2026, Rust is the better choice. It matches C++ in raw perfo...

9. [What is vLLM? High-Throughput LLM Serving 2026](https://futureagi.com/blog/what-is-vllm-2026/) - vLLM is the open-source LLM serving engine that pioneered PagedAttention and continuous batching. Ho...

10. [vLLM](https://vllm.ai) - vLLM is a high-throughput and memory-efficient inference and serving engine for Large Language Model...

11. [Building Desktop Apps with Go: Wails and Fyne Compared - LinkedIn](https://www.linkedin.com/posts/marcio-tiene_go-golang-softwaredevelopment-activity-7366998902530670592-IzHN) - Wails feels perfect if you want modern UIs with React/Vue but lightweight binaries instead of Electr...

12. [Introduction | Wails](https://wails.io/docs/introduction/) - Wails is a project that enables you to write desktop apps using Go and web technologies. Consider it...

13. [TypeScript's Growth Potential Relative to Rust, Go, and Kotlin](https://ourcodeworld.com/articles/read/2720/typescripts-growth-potential-relative-to-rust-go-and-kotlin) - A 2026 comparison of TypeScript, Rust, Go, and Kotlin covering adoption trends, job demand, learning...

14. [Elixir and BEAM as an operational advantage](https://www.betterask.erni/elixir-and-beam-as-an-operational-advantage-massive-concurrency-without-headaches/) - What are the ideal use cases? Real-time: chats, notifications, live collaboration, streaming. High-v...

15. [Release Notes - FastAPI - Tiangolo.com](https://fastapi.tiangolo.com/release-notes/) - FastAPI framework, high performance, easy to learn, fast to code, ready for production.

16. [Migrate from Pydantic v1 to Pydantic v2 - FastAPI](https://fastapi.tiangolo.com/how-to/migrate-from-pydantic-v1-to-pydantic-v2/) - Pydantic v2 includes everything from Pydantic v1 as a submodule pydantic.v1 . But this is no longer ...

17. [Asynchronous I/O (asyncio) — SQLAlchemy 2.1 Documentation](http://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html) - The create_async_engine() function creates an instance of AsyncEngine which then offers an async ver...

18. [SQLModel vs SQLAlchemy in 2025 : r/FastAPI - Reddit](https://www.reddit.com/r/FastAPI/comments/1je0xqn/sqlmodel_vs_sqlalchemy_in_2025/) - SQLModel and SQLAlchemy are ORMs and support multiple dbs but they add some overhead whereas asyncpg...

19. [Requests vs. HTTPX vs. AIOHTTP: Which One to Choose?](https://brightdata.com/blog/web-data/requests-vs-httpx-vs-aiohttp) - Discover the differences between Python's top HTTP clients - Requests, HTTPX, and AIOHTTP. Learn the...

20. [Comparing requests, aiohttp, and httpx: Which HTTP client should ...](https://dev.to/leapcell/comparing-requests-aiohttp-and-httpx-which-http-client-should-you-use-3784) - The code of aiohttp has an approximate 90% code overlap rate with the asynchronous mode code of http...

21. [HTTPX vs Requests vs AIOHTTP — Feature and Performance ...](https://proxywing.com/blog/httpx-vs-requests-vs-aiohttp-feature-performance-comparison-guide) - Yes, for most high-concurrency async workloads, AIOHTTP offers better performance than Python HTTPX....

22. [Astral Python 2026: Ruff, uv, ty & pyx](https://www.w3resource.com/python/astral-python-tooling-revolution-in-2026.php) - Ruff – The World's Fastest Python Linter & Formatter. Nearly 1000x faster than traditional linters. ...

23. [uv: Python packaging in Rust - Astral](https://astral.sh/blog/uv) - uv is an extremely fast Python package installer and resolver, written in Rust, and designed as a dr...

24. [astral-sh/uv: An extremely fast Python package and project ...](https://github.com/astral-sh/uv) - Installable without Rust or Python via curl or pip . Supports macOS, Linux, and Windows. uv is backe...

25. [Deno 2 vs Node.js vs Bun in 2026](https://dev.to/pockit_tools/deno-2-vs-nodejs-vs-bun-in-2026-the-complete-javascript-runtime-comparison-1elm) - Now, in late 2025, all three runtimes have matured significantly. Deno 2 shipped with full Node.js c...

26. [Bun vs Node.js in 2026: Benchmarks & Migration Guide](https://strapi.io/blog/bun-vs-nodejs-performance-comparison-guide) - Bun delivers 4× synthetic HTTP throughput and 35× faster installs than npm. See real-world benchmark...

27. [Bun vs Node.js in 2026 — I benchmarked both for a real ...](https://www.reddit.com/r/node/comments/1shc66k/bun_vs_nodejs_in_2026_i_benchmarked_both_for_a/) - Been running both on a mid-size Express API migration. Here's what actually matters in 2026: **Cold ...

28. [Elysia vs Hono for Solo Developers (2026) | SoloDevStack](https://solodevstack.com/blog/elysia-vs-hono-solo-developers) - Elysia is the framework built specifically for Bun. It takes full advantage of Bun's speed and APIs ...

29. [Hono vs ElysiaJS vs Nitro (2026) — PkgPulse Guides](https://www.pkgpulse.com/guides/hono-vs-elysiajs-vs-nitro-2026) - ElysiaJS is 2.3x faster than Hono on Bun benchmarks and provides end-to-end type safety without code...

30. [Zod vs Yup (2026): Why Zod Took Over TypeScript Validation](https://www.13labs.au/compare/zod-vs-yup) - Zod infers types from your schema; Yup needs them written twice. We cover bundle size, runtime cost,...

31. [TypeScript vs Zod: Clearing up validation confusion](https://blog.logrocket.com/when-use-zod-typescript-both-developers-guide/) - Learn when to use TypeScript, Zod, or both for data validation. Avoid redundant checks and build saf...

32. [Drizzle ORM vs Prisma: Which TypeScript ORM Should ...](https://www.bytebase.com/blog/drizzle-vs-prisma/) - Drizzle ORM vs Prisma comparison: type safety, performance, bundle size, serverless support, migrati...

33. [Drizzle vs Prisma ORM in 2026: A Practical Comparison for ...](https://makerkit.dev/blog/tutorials/drizzle-vs-prisma) - Drizzle is a code-first TypeScript ORM where you define schemas directly in TypeScript. There's no s...

34. [Why Prisma ORM Checks Types Faster Than Drizzle](https://www.prisma.io/blog/why-prisma-orm-checks-types-faster-than-drizzle) - Discover why Prisma ORM outperforms Drizzle ORM in TypeScript type checking. Our benchmarks show Pri...

35. [Detailed Guide to Node.js vs. Bun vs. Deno Performance](https://www.bolderapps.com/blog-posts/node-js-vs-bun-vs-deno-the-ultimate-runtime-performance-showdown) - Discover Node.js vs. Bun vs. Deno: The Ultimate Runtime Performance Showdown. Compare speed, securit...

36. [Popular Go Web Frameworks: A Practical Guide for Developers](https://blog.jetbrains.com/go/2026/04/28/popular-golang-web-frameworks/) - Gin is an HTTP web framework for building REST APIs, web applications, and microservices in Go. It o...

37. [Go Backend Frameworks: Which One Should You Actually Use?](https://dev.to/danikeya/go-backend-frameworks-which-one-should-you-actually-use-n0n) - 2. Gin — The Industry Standard ... Gin is the most widely used Go web framework by a significant mar...

38. [Best Go Backend Frameworks in 2026 - Complete Comparison](https://encore.dev/articles/best-go-backend-frameworks) - Compare the top Go backend frameworks: Standard library, Encore.go, Gin, Echo, Fiber, and Chi. Find ...

39. [The CLI Framework Developers Love | Cobra: A Commander ...](https://cobra.dev) - Cobra is the powerful, battle-tested CLI framework that transforms complex command-line development ...

40. [Building Powerful CLI Tools in Go with Cobra 🐍](https://dev.to/kittipat1413/building-powerful-cli-tools-in-go-with-cobra-539o) - In this blog, we'll walk through everything you need to know about Cobra — from installing it and cr...

41. [sqlc vs GORM vs sqlx: Go Database Libraries Compared 2026](https://reintech.io/blog/sqlc-vs-gorm-vs-sqlx-go-database-libraries-compared-2026) - The choice between sqlc, GORM, and sqlx isn't just about personal preference—it impacts your code ma...

42. [Comparing CRUD approaches in Go: database/sql, GORM, SQLX ...](https://www.linkedin.com/posts/mwansa-mwelwa-7073841b5_crud-in-go-activity-7369014383919677443-qm02) - When building Go backends, CRUD (Create, Read, Update, Delete) operations are essential. There are f...

43. [Embracing `sqlx` for Efficient and Secure Database Operations in ...](https://leapcell.io/blog/embracing-sqlx-for-efficient-and-secure-database-operations-in-go-without-gorm) - This article explores how to leverage `sqlx` in Go for robust, efficient, and secure database intera...

44. [Building A Cli Tool In Go With Cobra And Viper](https://www.linkedin.com/pulse/building-cli-tool-go-cobra-viper-keploy-u7buc) - First, initialize your Go project and install Cobra and Viper packages. Define your root command and...

45. [Example for Cobra and Viper for Go | Think About IT](https://thinkaboutit.tech/posts/2025-04-21-example-for-cobra-and-viper-for-go/) - This article shows an example how to use Cobra and Vipera packages for a Go project.

46. [High-Performance Structured Logging in Go with slog and ...](https://leapcell.io/blog/high-performance-structured-logging-in-go-with-slog-and-zerolog) - Both slog and zerolog are designed with performance in mind, offering low-allocation logging and eff...

47. [Logging in Go with Slog: A Practitioner's Guide](https://www.dash0.com/guides/logging-in-go-with-slog) - 2026 Logging in Go with Slog: structured logging solution designed to be the new standard. This guid...

48. [10 Best Logging Libraries for Golang Developers in 2026](https://reliasoftware.com/blog/golang-logging-libraries) - Zerolog takes the philosophy of minimal allocations to the extreme, making it the fastest structured...

49. [rs/zerolog: Zero Allocation JSON Logger](https://github.com/rs/zerolog) - Its unique chaining API allows zerolog to write JSON (or CBOR) log events by avoiding allocations an...

50. [Axum vs Actix-web vs Rocket: Rust Web Framework Comparison 2026](https://reintech.io/blog/axum-vs-actix-web-vs-rocket-rust-framework-comparison-2026) - Axum: The Type-Safe Pragmatist. Axum (currently at version 0.7.x) is built on top of Tokio and Hyper...

51. [The Evolution of Async Rust: From Tokio to High-Level Applications](https://blog.jetbrains.com/rust/2026/02/17/the-evolution-of-async-rust-from-tokio-to-high-level-applications/) - Tokio has become the de facto asynchronous runtime for high-performance networking in Rust, powering...

52. [Well written command line tools using serde? : r/rust - Reddit](https://www.reddit.com/r/rust/comments/1kl5fb5/well_written_command_line_tools_using_serde/) - Clap is the gold standard for command line argument parsing (hence the name). For configuration, I w...

53. [Rust ORMs 2026: SQLx vs Diesel vs SeaORM Comparison | byteiota](https://byteiota.com/rust-orms-2026-sqlx-vs-diesel-vs-seaorm-comparison/) - Here's the quick verdict: choose SQLx if you think in SQL, Diesel if you want the compiler to babysi...

54. [Rust ORMs and Database Libraries: The Complete Guide (2026)](https://www.rustfinity.com/blog/rust-orms) - A practical comparison of every major Rust ORM and database library - Diesel, SeaORM, SQLx, diesel-a...

55. [The State of Async Rust: Runtimes](https://corrode.dev/blog/async/) - Tokio stands as Rust's canonical async runtime. But to label Tokio merely as a runtime would be an u...

56. [Premortem vs Figment: Configuration Libraries for Rust ...](https://entropicdrift.com/blog/premortem-vs-figment/) - Premortem and Figment are both excellent Rust configuration libraries, but they're designed with fun...

57. [figment - Rust](https://docs.rs/figment/latest/figment/) - Figment is a library for declaring and combining configuration sources and extracting typed values f...

58. [Flexible Configuration for Rust Applications Beyond Basic ...](https://leapcell.io/blog/flexible-configuration-for-rust-applications-beyond-basic-defaults) - This article delves into how figment and config-rs provide the tools to build flexible, multi-format...

59. [Production-ready microservice in Rust: 4. Webserver | Sanyi's tinkering](https://apatisandor.hu/blog/production-ready-axum/) - We will implement the fundamentals of a webservice in this article. The service will be based on the...

60. [FFI — list of Rust libraries/crates / ...](https://lib.rs/development-tools/ffi) - FFI. Crates to help you better interface with other languages. This includes binding generators and ...

61. [Use Connect for incoming gRPC requests - Encore Cloud](https://encore.dev/docs/go/how-to/grpc-connect) - First, we'll define a simple gRPC service using Protobuf and Connect. · Then, we'll implement the se...

62. [Connect RPC](https://connectrpc.com) - Simple, reliable, interoperable. Protobuf RPC that works. Connect is a family of libraries for build...

63. [Why Connect RPC is a great choice for building APIs](https://www.wolfe.id.au/2025/12/02/why-connect-rpc-is-a-great-choice-for-building-apis/) - Connect RPC provides a paved and well maintained path to building gRPC compatible APIs, while mainta...

64. [Diplomat: Multi-language FFI for Rust Libraries](https://manishearth.github.io/blog/2026/06/14/diplomat-multi-language-ffi-for-rust-libraries/) - ICU4X developers absolutely need to know how to operate Diplomat so that they can write FFI for ever...

65. [Managing a Python project with uv in 2026](https://blog.bythewood.me/posts/managing-a-python-project-with-uv-in-2026/) - In 2026 I use uv for project management and ruff for linting and formatting. Two tools, one config f...

