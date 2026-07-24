# System Architecture & Design Patterns SOTA — July 2026

> **Audience:** Solo senior engineer / small team (≤ 15 engineers), polyglot, scaling from POC to production without accidental complexity.
> **Stance:** Simplest architecture that meets the requirement. Patterns flagged ⚠️ **PREMATURE** for solo/small team contexts.

***

## Part A — Macro-Architecture Decision Framework

### The Monolith-First Position

The consensus across 2025–2026 engineering literature is clear: **start as a modular monolith, extract only under concrete pressure**. Martin Fowler's *MonolithFirst* principle (2015) has aged into orthodoxy — "design a monolith carefully, paying attention to modularity … and it's a relatively simple matter to make the shift to microservices". The inverse advice — starting with microservices — is now widely described as premature optimisation that locks in boundaries that almost always turn out to be wrong, and merging microservices back is harder than splitting them apart.[^1][^2][^3][^4]

The practical case: a modular monolith delivers roughly 80% of the architectural benefits microservices promise (clean boundaries, replaceability, testability) at 20% of the operational cost — one deploy pipeline, one observability story, one database to back up.[^1]

### Decision Tree

```
┌─────────────────────────────────────────────────────────────────────┐
│  START: New service or system                                       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  ▼
             ┌────────────────────────────────────┐
             │  Domain boundaries well understood? │
             └────────┬───────────────────────────┘
                      │ NO                │ YES (stable, proven)
                      ▼                   ▼
         ┌──────────────────┐   ┌───────────────────────────────┐
         │ MODULAR MONOLITH │   │  Team ≥ 50 engineers AND      │
         │ (default choice) │   │  12+ bounded contexts AND     │
         └──────────────────┘   │  10K+ rps hot paths?          │
                                └───────┬──────────────┬────────┘
                                        │ NO            │ YES
                                        ▼               ▼
                              ┌──────────────┐  ┌─────────────────┐
                              │ MODULAR      │  │  MICROSERVICES  │
                              │ MONOLITH     │  │  (justified)    │
                              │ + selective  │  └─────────────────┘
                              │ extraction   │
                              └──────────────┘

  Additional overlays (orthogonal choices):
  ┌──────────────────────────────────────────────────────────────┐
  │ Bursty, stateless, pay-per-use workloads → SERVERLESS/FaaS  │
  │ Async fan-out, decoupling producers/consumers → EVENT-DRIVEN │
  │ Per-entity stateful sessions, real-time tracking → ACTOR     │
  └──────────────────────────────────────────────────────────────┘
```

### Architecture Options Compared

| Architecture | Solo/Small team fit | Cost | Latency | Op burden | When justified |
|---|---|---|---|---|---|
| **Modular monolith** | ✅ Default | Low | Low (in-process) | Low — one deploy pipeline | ≤ 50 eng, ≤ 12 BC, ≤ 10K rps[^1] |
| **Traditional monolith** | ✅ Early-stage only | Very low | Very low | Very low | Unvalidated idea, <5 eng, MVP[^5][^6] |
| **Microservices** | ⚠️ PREMATURE below 50 eng | High (platform team, mesh, tracing) | Adds network hops | Very high | 50+ eng, Conway-matched teams, regulated isolation[^1][^2] |
| **Serverless / FaaS** | ✅ Event-driven workloads | Pay-per-use (zero at idle) | Cold-start 200 ms–seconds[^7][^8] | Low infra; vendor lock-in risk | Bursty, stateless, infrequent tasks; avoid for latency-sensitive sync APIs[^9][^7] |
| **Event-driven** | ✅ Overlay on any of above | Medium (broker) | Async; not real-time | Medium — broker ops | Fan-out, audit, decoupled consumers[^10][^11] |
| **Actor / stateful** | ⚠️ Narrow domain | Medium–High | Low for stateful sessions | High (Akka/Orleans ops) | Per-entity state, real-time tracking, game servers[^12] |

### Concrete Signals That Justify Splitting a Modular Monolith

- A **specific module** has a drastically different scaling profile (e.g., image-processing needing GPU clusters).[^2]
- A module requires **compliance isolation** (PCI, HIPAA) from the rest of the system.[^1]
- A specific team **owns** a module and is blocked by the release cycle of the rest of the codebase.[^6]
- A module needs a **different technology runtime** that cannot be embedded in-process.[^6]
- You have proven the domain boundaries are **stable** through months of iteration — splitting too early locks in wrong seams.[^4][^1]

### Failure Modes to Avoid

1. **Distributed monolith** — services that share a database or are co-deployed together. Gives all the pain of microservices with none of the independence.[^1]
2. **Synchronous service chains 4+ deep** — turns every release into a coordination meeting and every outage into a cross-service investigation.[^1]
3. **Premature splits** — splitting before scaling/deployment/ownership needs are proven. "Don't choose microservices because Netflix does it. Choose them because your monolith forces you to."[^6]

### Serverless Cold-Start Reality

Serverless is not free of tradeoffs. AWS Lambda cold starts range from ~200 ms for optimised small packages to 800 ms+ for large runtimes. GPU serverless adds 30–60 seconds from scale-to-zero. Mitigation options — provisioned concurrency, SnapStart, keep-warm — reintroduce cost. For solo teams: serverless is ideal for async jobs, webhooks, scheduled tasks; avoid for sync user-facing endpoints where latency consistency matters.[^13][^7][^8]

***

## Part B — Internal Structure Patterns

### Pattern Overview

| Pattern | Organises by | Coupling locus | Testability | When to use | Avoid when | Solo team verdict |
|---|---|---|---|---|---|---|
| **Classic layered** (Presentation → Application → Domain → Infra) | Technical tier | Layer | Moderate; infra leaks up | Simple CRUD, tutorials, small teams new to DDD | Domain logic is complex; layers become anemic pass-throughs | OK for small services with simple domains |
| **Hexagonal / Ports & Adapters** | Use-case (driving/driven ports) | Application boundary | Excellent; swap adapters for fakes | Any service with >1 infra adapter (DB + queue + external API) | Domain is trivial CRUD — overhead not justified | ✅ Recommended default for anything non-trivial[^14] |
| **Clean / Onion** | Dependency rings (innermost = domain) | Domain ring | Excellent | DDD-rich domain, large codebase | Simple domains; ceremony is disproportionate | ✅ Equivalent to hexagonal with more explicit rings |
| **Vertical Slice** (VSA) | Feature / use case | Slice | Very high; each slice tested in isolation | Feature-heavy apps, CQRS command handlers | Complex domain logic shared across slices (model duplication risk) | ✅ Best for feature-rich APIs; compose with hexagonal for complex slices[^15][^16] |

### Hexagonal in Practice — DTO and Boundary Contracts

The defining discipline of hexagonal architecture is the **application boundary rule**: adapters live outside; the domain never imports infrastructure. At every seam:[^14]

- **Inbound ports** (driving): accept typed Value Objects or Command DTOs — never raw primitives or Aggregates exposed outside transactional boundaries.[^17]
- **Outbound ports** (driven): return domain objects; mappers at adapters translate to/from persistence models.[^18][^17]
- **Validate at the boundary, fail-closed**: all DTO-to-domain conversions should throw (or return a typed error) on invalid data. A Value Object in the domain is always in a valid state.[^17]

This prevents the classic failure mode where invalid data enters the core and causes non-deterministic failures deep in the call stack.

### Vertical Slice + Hexagonal Hybrid

The emerging best practice for 2025–2026 is **Vertical Clean Slices**: feature folders at the top level (VSA), with hexagonal or clean architecture applied *inside* complex slices. Simple CRUD slices use EF Core / SQLAlchemy directly in the handler. Complex domain slices get ports-and-adapters internal structure. This avoids the ceremony tax on simple cases while preserving testability where complexity lives.[^15][^16]

### Testability Matrix

| Pattern | Unit tests | Integration tests | Contract tests |
|---|---|---|---|
| Classic layered | Moderate — infra leaks make units expensive | Required often | Optional |
| Hexagonal / Clean | Excellent — swap real adapters for fakes | Adapter-only | ✅ At every port |
| Vertical Slice | Excellent — per-slice isolation | Per-slice handler test | ✅ Between slices |

The hexagonal rule: **tests are the first adapter**. Write the domain test by invoking the inbound port directly — no HTTP, no DB. This is faster than integration tests by 10–100x and exercises the core invariants directly.[^14]

### CQRS and Event Sourcing — When Justified

CQRS and Event Sourcing are frequently misapplied. Apply them selectively:[^19]

- **CQRS alone**: when read/write patterns diverge significantly, or when multiple read models with different shapes are required.[^20]
- **Event Sourcing**: only when the domain genuinely requires audit trails (financial, healthcare, logistics), temporal queries, or history-dependent business logic.[^21][^20]
- **For a solo team**: start with a simple read model from the same DB. Introduce CQRS projections only if query performance becomes a real bottleneck.[^19]

⚠️ **PREMATURE** for solo teams: applying CQRS + Event Sourcing as a top-level architecture from day one. Adopt per aggregate, per bounded context, only where justified.[^22]

***

## Part C — Distributed Concerns (When You DO Split)

### Data Per Service

The foundation of true service independence: each microservice owns its private database — other services **never access it directly**, only through APIs. This prevents shared-schema coupling that makes independent deployments impossible. For a small team this also means: *before you split a service, ensure you are ready to own a separate schema migration workflow for it*.[^12][^23][^24]

Cross-service data needs are satisfied by:
1. **Synchronous API call** — simple, but creates runtime coupling.
2. **Async event** — loose coupling, eventual consistency.
3. **Read-side denormalisation** — each service projects what it needs into its own query model.

### Saga vs Outbox vs CDC

These patterns are **complementary, not competing**:[^25]

| Pattern | Solves | Implementation | Small team cost |
|---|---|---|---|
| **Outbox** | Dual-write: atomically update DB and publish event | Write to `outbox` table in same transaction; background worker (or Debezium/CDC) relays to broker[^25] | Low — just a DB table + a relay process |
| **CDC (Change Data Capture)** | Tail the DB transaction log as event stream | Debezium → Kafka; no application code change | Medium — infra dependency |
| **Saga (Choreography)** | Distributed transaction across services with no global lock; linear flows | Services emit events triggering next step; compensating transactions on failure[^26][^27] | Low–Medium |
| **Saga (Orchestration)** | Complex/branching distributed workflows; strict SLAs | Central coordinator (Temporal, AWS Step Functions)[^28] | Medium — orchestrator overhead |

**For a small team**: start with **Outbox + Choreography Saga**. The outbox table is just SQL. Choreography works for linear flows. Add an orchestrator (Temporal) only when compensating logic becomes branching and hard to reason about.[^27]

### Idempotency

Every event consumer and API endpoint that changes state **must** be idempotent:[^29][^30]

1. **Idempotency key**: client generates a UUID per logical operation; server stores key + response; retries return cached result.[^30]
2. **Deduplication store**: processed key → response in DB or Redis with TTL.[^29]
3. **Natural idempotency**: use upserts (`INSERT … ON CONFLICT DO UPDATE`), state machine transitions that only fire from valid prior state.[^29]
4. **Outbox + idempotency keys**: combine for critical-path consistency — the outbox log position (CDC offset) makes an excellent monotonically increasing idempotency key.[^31]

### API Gateway vs BFF

| Pattern | Use when | Avoid when |
|---|---|---|
| **API Gateway** | Single client type or unified auth/rate-limit/routing needed | Multiple clients with radically different payload shapes |
| **BFF (Backend-for-Frontend)** | Multiple client types (web, mobile, IoT) each requiring tailored contracts; frontend team owns their backend layer[^32][^33] | Single client app; small team where maintenance overhead outweighs benefit[^34] |

For a **solo team with one client type**: a simple API gateway (or just the modular monolith's API layer) is sufficient. BFF becomes useful when a second client type arrives with meaningfully different data needs.[^34]

### Service Discovery

For a solo team running on Kubernetes: use **Kubernetes-native service discovery** (DNS-based Services) — it is zero-configuration and handles health checks and load balancing automatically. A service mesh (Istio, Linkerd) is ⚠️ **PREMATURE** at small team scale — the operational burden exceeds the benefit until 20+ services exist.[^35]

### Eventual Consistency Checklist

When you accept eventual consistency across service boundaries:
- Every consumer enforces idempotency.[^29]
- Every API and event schema is versioned.[^24]
- All async operations are observable (correlation IDs propagated, distributed tracing in place).[^23][^24]
- Compensating transactions exist for every step of a saga.[^27]
- SLA for consistency lag is documented and tested.[^28]

***

## Part D — Architecture Enforcement (So It Doesn't Rot)

### ADR — Architecture Decision Records

ADRs are short (one-page) markdown documents that answer four questions: what was the context, what was decided, what alternatives were considered, and what are the consequences. The standard Nygard template (Context / Decision / Consequences) is sufficient for most needs.[^36][^37]

**Practice rules**:
- One ADR, one decision — never combine multiple architectural choices.[^36]
- Write an ADR when a decision is costly to reverse (DB choice, messaging platform, deployment pattern).[^36]
- Store in `docs/adr/` inside the repo, versioned with the code.[^38][^39]
- Maintain lifecycle status: `Proposed → Accepted → Active → Deprecated / Superseded`.[^36]
- Review quarterly: has the context changed?[^36]

**Tooling**:
- [`adr-tools`](https://github.com/npryce/adr-tools) — CLI to scaffold and manage markdown ADRs.
- [`log4brains`](https://github.com/thomvaill/log4brains) — IDE integration + static site generator for ADR browsing.[^40]
- For solo dev: plain markdown in `docs/adr/` with the Nygard template is sufficient.

### Fitness Functions in CI — Polyglot Tooling

Architecture fitness functions are automated tests that verify architectural rules on every CI run, preventing slow drift into a "Big Ball of Mud".

| Language | Tool | What it enforces | Config |
|---|---|---|---|
| **Python** | [`import-linter`](https://github.com/seddonym/import-linter) | Import contracts: layers, independence, forbidden modules[^41][^42] | `.importlinter` in repo root |
| **TypeScript / JS** | [`dependency-cruiser`](https://www.npmjs.com/package/dependency-cruiser) | Import rules, circular dependency detection, architectural layer boundaries[^43][^44][^45] | `.dependency-cruiser.cjs` |
| **Java / Kotlin** | [`ArchUnit`](https://www.archunit.org) | Package dependencies, layer rules, annotation placement, naming conventions[^46][^47][^48] | JUnit test class |
| **Go** | [`go-arch-lint`](https://github.com/fe3dback/go-arch-lint) | Package dependency rules via YAML config; supports hexagonal, DDD, MVC[^49] | `.go-arch-lint.yml` |
| **Go (JVM-inspired)** | [`archunit` (Go port)](https://github.com/kcmvp/archunit) | Layer, package, type, method rules[^50] | Go test |
| **Any** | Custom shell scripts | Any dependency analysis via `grep`, AST tools, or language-specific parsers | CI step |

**Minimal CI integration**:
```yaml
# Example: Python (GitHub Actions)
- name: Architecture lint
  run: lint-imports

# TypeScript
- name: Dependency check
  run: npx depcruise --validate .dependency-cruiser.cjs src

# Java / Kotlin — ArchUnit runs as part of the test suite automatically
```

### C4 + Structurizr — Diagrams as Code

The C4 model (Context, Containers, Components, Code) provides four zoom levels for communicating architecture to different audiences:[^51][^52]

| Level | Shows | Audience |
|---|---|---|
| C1 System Context | System + external actors/systems | Stakeholders, PM |
| C2 Container | Deployable units (apps, DBs, queues) | Developers, architects |
| C3 Component | Internal structure of a container | Developers |
| C4 Code | UML class diagram (optional; IDE can generate) | Developers |

**Structurizr** is the reference "models as code" tool for C4, developed by the C4 model's creator. Architecture is written in Structurizr DSL — a text file versioned with code — and rendered into interactive diagrams:[^53][^54]

```dsl
workspace {
  model {
    user = person "User"
    system = softwareSystem "My System" {
      webApp = container "Web App" "Next.js" "React"
      api = container "API" "FastAPI" "Python"
      db = container "Database" "PostgreSQL" "Database"
    }
    user -> webApp "uses"
    webApp -> api "calls"
    api -> db "reads/writes"
  }
  views {
    systemContext system "Context" { include * }
    container system "Containers" { include * }
  }
}
```

**Structurizr Lite** is free, self-hosted (Docker), and ideal for solo developers. As of 2025–2026, Structurizr supports AI agent integration: agents can auto-generate DSL from codebases and flag inconsistencies between ADRs, diagrams, and code.[^54][^55]

***

## Minimal Architecture-Governance Kit for a Solo Dev

This is the **minimum viable governance set** that pays compounding returns without becoming maintenance overhead:

### 1. ADR: Nygard Template in `docs/adr/`

```markdown
# ADR-001: Use PostgreSQL as primary data store

## Status
Accepted

## Context
Single deployable unit needs ACID transactions and JSONB for flexible schemas.
Avoiding multiple DB technologies to keep ops burden low.

## Decision
Use PostgreSQL for all persistent state in the initial modular monolith.

## Consequences
- Single migration workflow (Alembic / Flyway / golang-migrate).
- All services share one DB until extraction pressure justifies splitting.
- If a hot-path module is extracted, it gets its own Postgres schema first,
  then a separate instance when isolation is required.
```

Use `adr-tools` or `log4brains` to scaffold and browse.[^39][^40]

### 2. One Fitness Function in CI

Pick **one tool matching your primary language**, add it to CI:

- Python → `import-linter` with a `layers` contract (domain cannot import infra).[^41][^42]
- TypeScript → `dependency-cruiser` with a `no-circular` + layer rule.[^44][^45]
- Java/Kotlin → ArchUnit in the test suite; runs on every build.[^48]
- Go → `go-arch-lint` in CI YAML.[^49]

Start with one rule (no circular dependencies). Add rules incrementally as you document intentions. The rule set becomes a living specification of your intended architecture.[^43]

### 3. One Diagram Tool: Structurizr Lite

Run it locally with Docker (`docker run -p 8080:8080 -v $(pwd)/workspace:/usr/local/structurizr structurizr/lite`). Commit `workspace.dsl` to the repo. Update C1 + C2 diagrams for every significant structural change. Skip C3/C4 until a container is large enough to need its own component map.[^55]

***

## Pattern Catalog

| Pattern | When to use | Avoid when | Enforcement tool | Premature for solo? |
|---|---|---|---|---|
| Modular monolith | ≤ 50 eng, domain still evolving[^1][^5] | 50+ eng with Conway-aligned teams | import-linter, dependency-cruiser, ArchUnit | No — **this is the default** |
| Microservices | 50+ eng, 12+ BC, 10K+ rps, regulated isolation[^1][^2] | Small teams, unclear domain boundaries | Service mesh, contract testing (Pact) | ⚠️ YES — usually |
| Serverless / FaaS | Bursty stateless tasks, webhooks, async jobs[^9] | Latency-sensitive sync APIs, long-running tasks[^8] | Cost alerts, timeout tests | No — selective use OK |
| Event-driven | Decoupled fan-out, audit trail, async workflows[^10][^11] | Real-time sync requirements | Schema registry, consumer contract tests | No — selective use OK |
| Actor model | Per-entity stateful sessions, real-time tracking[^12] | Simple request/response services | Orleans/Akka cluster management | ⚠️ YES — unless domain demands it |
| Hexagonal / Ports & Adapters | Any non-trivial service with multiple adapters[^14] | Trivial CRUD microservice | import-linter, ArchUnit, dependency-cruiser | No |
| Vertical Slice | Feature-rich APIs, CQRS handlers[^15] | Heavily shared domain logic across slices | import-linter (independence contract) | No |
| Clean / Onion | Complex DDD domain[^56] | Simple domains; adds ceremony | ArchUnit layer rules | No — but hexagonal is simpler |
| Classic layered | Small service, simple domain | Anemic domain with complex logic | Any layer contract tool | No |
| Outbox pattern | Atomic DB + event publish[^25] | No distributed consumers | DB table + relay process or CDC | No — cheap to add |
| Choreography Saga | Linear distributed workflows[^26][^27] | Branching compensations, strict SLAs | Distributed tracing | No — if you already have events |
| Orchestration Saga | Complex branching workflows[^28] | Simple linear flows | Temporal / Step Functions dashboard | ⚠️ YES — orchestrator overhead |
| CQRS | Read/write divergence, multiple read models[^20] | Simple CRUD | Read model tests | ⚠️ YES — per-aggregate only |
| Event Sourcing | Audit trail, temporal queries, history-dependent logic[^20] | Simple domains, no audit requirement | EventStoreDB / append-only table | ⚠️ YES — high complexity |
| Data per service | True service independence[^12][^24] | Modular monolith (use schemas not separate DBs) | API contract tests | No — if you've split already |
| API Gateway | Unified entry point, auth, rate-limit[^57][^58] | Single client with simple routing | None needed | No |
| BFF | Multiple clients with different data contracts[^32][^33] | Single client app, small team[^34] | Consumer contract tests (Pact) | ⚠️ YES — until second client exists |
| ADR | Every costly-to-reverse decision[^38][^36] | Daily operational choices | adr-tools, log4brains | No — **always do this** |
| C4 + Structurizr | Communicating architecture at multiple zoom levels[^51][^59] | Trivial one-service apps | DSL in version control | No — Structurizr Lite is free |

***

## Bibliography (Verified Sources)

- [zanisssoftwares.com — Microservices vs Monolith 2026 Decision Framework][^1]
- [scalewithchintan.com — Microservices vs Monoliths vs Modular Monoliths 2025][^5]
- [ness.com — Modular Monolith vs Microservices 2026][^2]
- [martinfowler.com — MonolithFirst][^3]
- [enqcode.com — Rethinking Microservices 2026][^4]
- [linkedin.com — Microservices vs Monoliths in 2026: Karthik Chakravarthy][^6]
- [247labs.com — Serverless Architecture in 2025][^9]
- [conduktor.io — Outbox Pattern for Reliable Event Publishing (2026)][^25]
- [github.com/thomvaill/log4brains][^40]
- [codeopinion.com — Vertical Slice vs Clean Architecture][^60]
- [nadirbad.dev — Vertical Slice vs Clean Architecture 2025][^15]
- [ricofritzsche.me — Why Vertical Slices Won't Evolve from Clean Architecture][^61]
- [thebackenddevelopers.substack.com — Saga and Emerging Patterns Beyond 2PC][^28]
- [pasksoftware.com — Distributed Transaction Patterns][^27]
- [techtarget.com — 8 Best Practices for ADRs (2025)][^38]
- [archyl.com — ADR Complete Guide 2026][^36]
- [architectviewmaster.com — Building an ADR Library][^39]
- [github.com/seddonym/import-linter][^41]
- [import-linter.readthedocs.io][^62]
- [xebia.com — dependency-cruiser for frontend architecture][^43]
- [developers.cyberagent.co.jp — go-arch-lint in Practice][^49]
- [archunit.org][^48]
- [github.com/kcmvp/archunit][^50]
- [schibsted-vend.pl — C4 Model and Structurizr][^51]
- [docs.structurizr.com — Why "as code"][^54]
- [jdriven.com — Structurizr for Maintainable Architecture][^52]
- [dev.to/simonbrown — Getting Started with Structurizr Lite][^55]
- [geeksforgeeks.org — API Gateway vs BFF][^57]
- [microsoft.com — Backends for Frontends Pattern (Azure)][^33]
- [dev.to — BFF in 2025: Still Relevant?][^34]
- [ibm.com — Microservices Design Patterns][^12]
- [morling.dev — On Idempotency Keys 2025][^31]
- [thearchitectsnotebook.substack.com — Advanced Idempotency 2025][^30]
- [edgedelta.com — AWS Lambda Cold Start Impact 2025][^7]
- [milvus.io — Serverless Performance Trade-offs 2026][^8]
- [matterai.so — Event Sourcing vs CQRS 2026][^20]
- [softwareengineering.stackexchange.com — CQRS+ES Anti-Pattern][^22]
- [codeartify.substack.com — Domain Model vs DTOs (Ports & Adapters)][^17]
- [codeopinion.com — Microservices to Monolith][^63]
- [wondermentapps.com — Microservices Best Practices 2025][^24]

---

## References

1. [Microservices vs Monolith in 2026 — Architecture Decision Framework](https://zanisssoftwares.com/infographics/microservices-vs-monolith-2026) - In 2026, the modular monolith is the right starting architecture for most teams under 50 engineers, ...

2. [Modular Monolith vs Microservices: Key Differences & When to ...](https://www.ness.com/blog/modular-monolith-vs-microservices/) - Modular monolith vs microservices — compare architecture, scalability, cost, and team impact. Use ou...

3. [Monolith First - Martin Fowler](https://martinfowler.com/bliki/MonolithFirst.html) - A monolith-first strategy, where you should build a new application as a monolith initially, even if...

4. [Rethinking Microservices in 2026: When Modular Monolith ...](https://enqcode.com/blog/rethinking-microservices-in-2026-when-modular-monolith-architecture-actually-win) - A modular monolith aligns better with teams that need to move fast, share context, and evolve domain...

5. [Microservices vs Monoliths vs Modular Monoliths - Scale with Chintan](https://scalewithchintan.com/blog/microservices-monoliths-modular-monoliths-2025-choice) - Explore the future of software architecture in 2025: A deep dive into Monoliths, Microservices, and ...

6. [Microservices vs Monoliths in 2026: When to Choose What - LinkedIn](https://www.linkedin.com/pulse/microservices-vs-monoliths-2026-when-choose-what-karthik-chakravarthy-iibme) - 1. The Problem Isn't Monolith vs Microservices - It's Your Context · 2. When a Monolith Is Actually ...

7. [AWS Lambda Cold Starts: Impact and How to Reduce Them](https://edgedelta.com/company/knowledge-center/aws-lambda-cold-start-cost) - When Lambda cold starts matter, how the billing model affects costs, and practical strategies to cut...

8. [What are the performance trade-offs of serverless ...](https://milvus.io/ai-quick-reference/what-are-the-performance-tradeoffs-of-serverless-architecture) - One major trade-off is cold start latency. Serverless functions (e.g., AWS Lambda, Azure Functions) ...

9. [Serverless Architecture in 2025 | 247 Labs](https://247labs.com/serverless-architecture-in-2025/) - Event-driven application design aligns naturally with the serverless execution model. By structuring...

10. [Understanding Event-Driven Architecture and Serverless ... - Koyeb](https://www.koyeb.com/blog/understanding-event-driven-architecture-and-serverless-opportunities) - In event-driven architectures, events trigger applications. Adopting serverless simplifies app manag...

11. [Event-Driven Architectures vs. Event-Based Compute in Serverless ...](https://alexdebrie.com/posts/event-driven-vs-event-based/) - In this post, we'll look at both event-driven architecture and event-based compute. We'll examine th...

12. [What are microservices design patterns? - IBM](https://www.ibm.com/think/topics/microservices-design-patterns) - The database per service pattern ensures that each microservice owns and manages its own database, e...

13. [Scale-to-Zero Cold Start Latency: Why Serverless GPU ...](https://regolo.ai/scale-to-zero-cold-start-latency-why-serverless-gpu-breaks-real-time-ai-and-how-to-fix-it/) - While serverless GPU promises efficiency, the 30-60 second cold start delays it introduces make it u...

14. [The Hexagonal - Ports & Adapters Architecture | Alistair Cockburn](https://www.youtube.com/watch?v=ChUlRa0xsWo) - ... boundary ✓ The difference between driving and driven ... The Hexagonal - Ports & Adapters Archit...

15. [Vertical Slice vs Clean Architecture - Nadir Badnjevic](https://nadirbad.dev/vertical-slice-vs-clean-architecture) - Compare Vertical Slice vs Clean Architecture with real examples. Learn when each pattern fits, migra...

16. [1 question I often see online: Clean Architecture vs. ...](https://www.linkedin.com/posts/kristijankralj_1-question-i-often-see-online-clean-architecture-activity-7287371457859391488-DZ-R) - flexibility and scalability. This article breaks down N-Layered, Clean, and Vertical Slice architect...

17. [Adding Domain-Driven Design to Ports and Adapters - CodeArtify Blog](https://codeartify.substack.com/p/domain-model-vs-dtos) - DTOs. In this article, I will discuss what types of data structures exist and which ones should cont...

18. [The DTO dilemma - Professional Beginner](https://professionalbeginner.com/the-dto-dilemma/) - The main aspect of the Hexagonal architecture is: separation of concerns. To that extend the Domain ...

19. [CQRS and Event Sourcing: A Practical Guide for Autonomous Systems](https://teamhelix.ai/blog/cqrs-and-event-sourcing-practical-guide) - CQRS and event sourcing are not patterns you should apply everywhere. They are patterns you should a...

20. [Event Sourcing vs CQRS: Choosing the Right Pattern for Your Domain](https://www.matterai.so/guides/event-sourcing-vs-cqrs-choosing-the-right-pattern-for-your-domain) - CQRS separates read and write operations, while Event Sourcing persists state as a sequence of immut...

21. [Understanding Event Sourcing and CQRS Pattern - Mia-Platform](https://mia-platform.eu/blog/understanding-event-sourcing-and-cqrs-pattern/) - Event Sourcing is an architectural pattern that tracks changes in a domain by recording them as immu...

22. [CQRS+Event Sourcing as Top Level Architecture: Anti-Pattern](https://softwareengineering.stackexchange.com/questions/373857/cqrsevent-sourcing-as-top-level-architecture-anti-pattern) - Both CQRS and ES are patterns that can be employed when the use-case develops within a system. As su...

23. [5 Essential Microservices Design Patterns - Oso](https://www.osohq.com/learn/microservices-design-patterns) - Discover the top microservices design patterns to architect scalable, efficient, and reliable system...

24. [10 Microservices Architecture Best Practices for 2025](https://www.wondermentapps.com/blog/microservices-architecture-best-practices/) - Database Per Service pattern. This approach dictates that each microservice must manage its own priv...

25. [Outbox Pattern for Reliable Event Publishing](https://www.conduktor.io/glossary/outbox-pattern-for-reliable-event-publishing) - The Saga Pattern solves the broader problem of coordinating transactions across multiple services. T...

26. [Saga and Outbox Patterns for Microservices](https://www.linkedin.com/posts/elliotone_microservices-saga-vs-outbox-patterns-by-activity-7302779877915611137-r2mb) - Outbox Pattern (Distributed Transactions) For critical data ... 2️⃣ Saga Pattern – Manages distribut...

27. [Distributed Transaction Patterns](https://pasksoftware.com/distributed-transaction-patterns/) - Saga pattern describes the way to implement a long‑running transaction that spans multiple services ...

28. [Emerging Patterns Beyond Two-Phase Commit](https://thebackenddevelopers.substack.com/p/consistent-distributed-transactions) - No single global lock; just a chain of local commits and, if needed, local rollbacks. Key properties...

29. [Idempotency in System Design - DEV Community](https://dev.to/nk_sk_6f24fdd730188b284bf/idempotency-in-system-design-2jcj) - In distributed systems, idempotency transforms unreliable networks into predictable systems. It enab...

30. [Ep #19: Advanced Idempotency in System Design](https://thearchitectsnotebook.substack.com/p/advanced-idempotency-in-system-design) - Answer: Idempotency complements distributed transactions by ensuring individual operations within a ...

31. [On Idempotency Keys - Gunnar Morling](https://www.morling.dev/blog/on-idempotency-keys/) - 2025 distributed-systems. By adding a unique idempotency key to each message, you can enable consume...

32. [Why the BFF Pattern Matters: Simplifying Your Frontend's Backend ...](https://www.linkedin.com/pulse/why-bff-pattern-matters-simplifying-your-frontends-souza-gon%C3%A7alves-swm1f) - Independent Maintenance: Changes in one BFF don't affect other clients. BFF vs API Gateway. API Gate...

33. [Backends for Frontends Pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends) - Because each BFF service is smaller and less complex than a shared backend service, it can make the ...

34. [Backend-for-Frontend (BFF) in 2025: Still Relevant or Outdated?](https://dev.to/arkhan/backend-for-frontend-bff-in-2025-still-relevant-or-outdated-5dml) - With modern tools like GraphQL, API gateways, and microservices, some argue BFF is no longer necessa...

35. [10 Essential Microservices Architecture Best Practices for 2025](https://group107.com/blog/microservices-architecture-best-practices/) - To correctly implement the Database Per Service pattern, follow these actionable guidelines: Establi...

36. [Architecture Decision Records (ADR): The Complete Guide](https://www.archyl.com/blog/architecture-decision-records-complete-guide) - Architecture Decision Records capture the why behind your technical choices. This complete guide cov...

37. [adr: A .NET Tool for Creating & Managing Architecture ...](https://endjin.com/blog/adr-a-dotnet-tool-for-creating-and-managing-architecture-decision-records) - Architectural Decision Records (ADRs) capture context, options, decisions, and consequences. dotnet-...

38. [8 best practices for creating architecture decision records](https://www.techtarget.com/searchapparchitecture/tip/4-best-practices-for-creating-architecture-decision-records) - An effective ADR provides transparency in the decision-making process and creates a historical recor...

39. [Building an Architecture Decision Record (ADR) Library](https://www.architectviewmaster.com/blog/building-architecture-decision-record-adr-library/) - use open-source tools like adr-tools or log4brains for automation and structure. Keep them in a dedi...

40. [thomvaill/log4brains: ✍️ Architecture Decision Records ...](https://github.com/thomvaill/log4brains) - It enables you to log Architecture Decision Records (ADR) right from your IDE and to publish them au...

41. [seddonym/import-linter: Lint your Python architecture.](https://github.com/seddonym/import-linter) - Import Linter allows you to impose constraints on the imports between your Python modules. It also p...

42. [Linter for Python Architecture](https://roman.pt/posts/python-architecture-linter/) - If module A imports module B, then A depends on B. import-linter lets you specify the rules that dec...

43. [Taking Frontend Architecture Serious With Dependency-cruiser](https://xebia.com/blog/taking-frontend-architecture-serious-with-dependency-cruiser/) - With dependency-cruiser, you can enforce which imports are allowed. This enables you to create an ar...

44. [Visualize a Typescript Codebase with Dependency Cruiser](https://passionsplay.com/blog/visualize-a-typescript-codebase-with-dependency-cruiser/) - Dependency Cruiser is a powerful npm tool designed to analyze and visualize dependencies within Java...

45. [Avoid Cross Module Dependencies with Dependency Cruiser](https://dev.to/jacobandrewsky/avoid-cross-module-dependencies-with-dependency-cruiser-3b0b) - dependency-cruiser is a powerful tool for analyzing and validating dependencies in JavaScript and Ty...

46. [ArchUnit Guide – How to Unit Test Your Architecture - Pask Software](https://pasksoftware.com/archunit/) - ArchUnit will help you whenever the compiler will not make it, especially in enforcing a package str...

47. [ArchUnit in practice: Keep your Architecture Clean - codecentric AG](https://www.codecentric.de/en/knowledge-hub/blog/archunit-in-practice-keep-your-architecture-clean) - Learn how ArchUnit helps you maintain a clean software architecture, enforce rules and ensure long-t...

48. [ArchUnit: Unit test your Java architecture](https://www.archunit.org) - Start enforcing your architecture within 30 minutes using the test setup you already have ... May 7,...

49. [Practical Guide To Apply Clean Architecture In Go](https://developers.cyberagent.co.jp/blog/archives/59647/) - At its core, the main advantage of go-arch-lint is its ability to enforce architecture boundaries by...

50. [kcmvp/archunit: Golang Architecture Test Framework - GitHub](https://github.com/kcmvp/archunit) - archunit is a powerful and flexible library for enforcing architectural rules in your Go projects. I...

51. [How to master your architecture with the C4 model and Structurizr?](https://schibsted-vend.pl/blog/how-to-master-your-architecture-with-the-c4-model-and-structurizr/) - C4: A Comprehensive Framework for Modeling and Visualising System Architecture · System Context diag...

52. [Structurizr for Maintainable architecture - JDriven Blog](https://jdriven.com/blog/2024/10/structurizr) - Structurizr is a tool which can create diagrams for the 4 levels of C4 based purely on a DSL (Domain...

53. [Structurizr: Models as Code for C4 Software Architecture Diagrams](https://mcpmarket.com/server/structurizr) - Structurizr is the reference "models as code" tool for the C4 model, allowing users to define their ...

54. [Why “as code”? - Structurizr](https://docs.structurizr.com/as-code) - The C4 model is aimed at software engineering teams, providing a way for technical people to create ...

55. [Getting started with Structurizr Lite - DEV Community](https://dev.to/simonbrown/getting-started-with-structurizr-lite-27d0) - Structurizr Lite provides a quick and free way to get started with the Structurizr tooling. It suppo...

56. [Hexagonal vs. Clean Architecture: Same Thing Different Name?](https://www.reddit.com/r/programming/comments/1l7vun6/hexagonal_vs_clean_architecture_same_thing/) - flexibility and scalability. This article breaks down N-Layered, Clean, and Vertical Slice architect...

57. [API Gateway vs Backend For Frontend (BFF) - GeeksforGeeks](https://www.geeksforgeeks.org/system-design/api-gateway-vs-backend-for-frontend-bff/) - While an API Gateway acts as a centralized entry point for various backend services, the BFF pattern...

58. [API Gateway vs Backend For Frontend - Kuroco](https://kuroco.app/blog/api-gateway-vs-backend-for-frontend/) - An API gateway is a single point of entry for all clients fetching data from the system, while a bac...

59. [Structurizr](https://structurizr.com) - Structurizr is specifically designed to support the C4 model for visualising software architecture, ...

60. [Is Vertical Slice Architecture better than Clean ...](https://codeopinion.com/is-vertical-slice-architecture-better-than-clean-architecture-or-ports-and-adapters/) - Vertical Slice Architecture isn't better than Clean Architecture, Hexagonal Architecture / Ports & A...

61. [Why Vertical Slices Won't Evolve from Clean Architecture](https://ricofritzsche.me/why-vertical-slices-wont-evolve-from-clean-architecture/) - The natural evolution of Clean Architecture leads to Vertical Slices when you do fewer projects and ...

62. [Import Linter](https://import-linter.readthedocs.io) - Import Linter allows you to impose constraints on the imports between your Python modules. It also p...

63. [Microservices to Monolith - CodeOpinion](https://codeopinion.com/microservices-to-monolith/) - Want to switch from Microservices to a Monolith? If you can't build microservices, what makes you th...

