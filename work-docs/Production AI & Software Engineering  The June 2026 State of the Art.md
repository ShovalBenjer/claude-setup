# Production AI & Software Engineering: The June 2026 State of the Art

> **Audience:** Senior AI engineers designing production systems for thousands to millions of users. Fundamentals are not explained. Every recommendation is evidence-backed and production-validated.

***

## Executive Summary

The defining shift of 2026 is the convergence of AI systems and production software infrastructure. **Context engineering** has displaced prompt engineering as the primary skill. **Durable execution** (Temporal) has become mandatory for multi-step agent workflows. **vLLM** remains the production-default inference engine, with **SGLang** winning on multi-turn and agentic workloads. **MCP** has become the universal tool protocol, releasing its 2026-07-28 stateless spec. Python's toolchain has been unified around **uv + Ruff + Pyright + Pydantic v2**. **Valkey** has displaced Redis as the default in-memory store at every major cloud provider. **Modular monolith** architecture has rehabilitated itself against premature microservices decomposition. On security, **OAuth 2.1** is the mandatory replacement for OAuth 2.0.

The top ten highest-ROI investments for AI engineering teams right now, in priority order:
1. Prefix caching + continuous batching on LLM inference (free throughput)
2. Context engineering: stable-first prompt ordering + explicit cache markers
3. Hybrid RAG: BM25 + dense retrieval + cross-encoder reranking
4. OpenTelemetry GenAI semantic conventions for full-stack AI traces
5. Temporal for durable agent workflows
6. Valkey/pgvector migration (Redis license + free vector search)
7. uv + Ruff + Pyright (10–100x developer toolchain speedup)
8. KEDA for GPU/AI autoscaling on Kubernetes
9. OAuth 2.1 + PKCE across all auth flows
10. SBOM generation in CI/CD (regulatory requirement by 2027)

***

## Part I: AI Infrastructure

### LLM Inference Engines

The three engines that matter for production LLM inference in 2026 are **vLLM**, **SGLang**, and **TensorRT-LLM**. Hugging Face put TGI into maintenance mode in December 2025 and now points teams toward vLLM or SGLang for new deployments.[^1]

**vLLM** is the serving-first production default: runs on every hardware platform (NVIDIA, AMD, Trainium, TPUs), has the largest community, the most Helm charts, and the most production deployments globally. Its PagedAttention algorithm virtually eliminates KV cache memory fragmentation, enabling continuous batching that often doubles throughput over static approaches. It handles 70B+ model deployments with tensor parallelism without additional configuration complexity.[^2]

**SGLang** wins on multi-turn, RAG, and agentic workloads. Its RadixAttention caches shared computation across requests — for a 2000-token system prompt served to 1000 users, you avoid recomputing 2 billion tokens of redundant attention. On 8B models, SGLang benchmarks show roughly 16,200 tok/s versus vLLM at 12,500 tok/s — a **29% throughput advantage**. On 70B+ models, the gap narrows to 3–5%. SGLang also overlaps grammar mask generation with GPU inference for structured output enforcement, while vLLM shows noticeable throughput degradation at batch sizes of 8+ when guided decoding is enabled.[^3][^1]

**TensorRT-LLM** extracts 15–30% additional throughput over vLLM but only on NVIDIA hardware, requires engine compilation per model version (hours to days), and has significantly higher operational complexity. Use it when peak NVIDIA performance is the overriding constraint and the model won't change for months.[^2]

| Engine | Best For | Throughput | Hardware | Ops Complexity | Verdict |
|---|---|---|---|---|---|
| vLLM | General production, batch, diverse hardware | Baseline | Multi-platform | Low | **Default** |
| SGLang | Multi-turn chat, agents, RAG, structured output | +29% on 8B, +3-5% on 70B | NVIDIA/AMD | Low | **Preferred for AI apps** |
| TensorRT-LLM | Max throughput, static models, NVIDIA-only | +15-30% over vLLM | NVIDIA only | High | Specialized |
| Ollama | Local dev, prototyping | Low | Multi-platform | Zero | Dev only |

**Principal Engineer view:** Approve vLLM for most teams. Migrate to SGLang if your workload has shared prefixes (system prompts, RAG documents appearing repeatedly). Reject TensorRT-LLM unless you have a dedicated MLOps team and a stable model with a performance SLA you cannot meet otherwise.

### Key Inference Optimizations

**Prefix caching** is the single highest-leverage optimization for applications with shared system prompts, shared documents, or multi-turn conversations. Once enabled, prefill cost on cached tokens drops to near zero. With Anthropic's `cache_control` markers or OpenAI's automatic prefix caching, production teams report 75–90% cost savings on stable prefixes. The rule: put your largest, most stable content at the top of the prompt — system instructions, tool definitions, few-shot examples — and keep variable user content at the bottom.[^4][^5][^3]

**Continuous batching** (in-flight batching) evicts finished sequences and immediately admits new ones, keeping the GPU full without waiting for the longest request in a batch to complete. This alone often doubles throughput versus static batching and carries zero quality risk.[^3]

**Speculative decoding** uses a small draft model to propose K candidate tokens, then verifies them in a single forward pass of the main model. Effective speedup is 1.5–3× when the draft model accepts approximately 70% of proposed tokens. Critical constraint: speculative decoding improves single-request latency but can reduce total throughput when GPU utilization is already high. Use it for latency-sensitive, low-concurrency scenarios — interactive coding assistants, real-time streaming agents. Do not deploy it on batch processing endpoints.[^6][^3]

**Quantization** standard in 2026: FP8 on Hopper (H100) and Blackwell (B200) is the new default — minimal quality degradation, halved memory, doubled effective batch capacity. INT8 with AWQ or SmoothQuant for Ampere (A100) deployments.[^6]

**Prefill/decode disaggregation** is an emerging architecture for high-throughput deployments. Prefill is compute-bound (scales with prompt length squared); decode is memory-bandwidth-bound. Running them on separate GPU pools eliminates head-of-line blocking where a long-prefill request delays decode for other users.[^3]

### KV Cache Engineering

The KV cache is the central performance primitive of LLM inference. Without caching, each decode step recomputes attention over the full sequence — quadratic cost. PagedAttention (vLLM) applies OS-inspired paging: the cache is split into fixed-size pages stored non-contiguously and tracked via block tables, reducing fragmentation and allowing more concurrent requests per GPU.[^7][^3]

Multi-Query Attention (MQA) and Grouped-Query Attention (GQA) — used by Llama 3, Mistral, Qwen — reduce the number of K/V heads, shrinking cache size significantly while retaining model quality. This is a model architecture choice, not an inference engine choice, but it directly determines how many concurrent users fit in GPU memory.

***

## Part II: AI Agent Engineering

### Architecture Decision: Agent vs. Workflow

The most expensive mistake in agent engineering is building an agent when a workflow would suffice.

- **Workflows** are deterministic sequences. The LLM is called at defined points but does not control flow. Use when: the task is well-specified, the sequence is known, reliability and auditability are paramount. Examples: document extraction pipeline, structured data generation, Q&A over a knowledge base.
- **Agents** are LLM-controlled loops with tool access. The model decides what to call, when to stop, and how to chain results. Use when: the task is underspecified, the sequence is unknown in advance, or the problem requires adaptive planning. Examples: coding assistants, research agents, autonomous data analysis.

The failure mode of premature agentification is an LLM making planning decisions it consistently gets wrong, with no deterministic fallback. Start with a workflow. Add agency only when the deterministic path demonstrably cannot solve a class of real user problems.

### Framework Comparison (2026)

| Framework | Architecture | Strengths | Weaknesses | Best For |
|---|---|---|---|---|
| LangGraph | Graph-based state machines | Fine-grained control, stateful, streaming, LangSmith integration | Steep learning curve, verbose | Complex enterprise agents, multi-provider |
| OpenAI Agents SDK | Python-native, handoff pattern | Simple, streaming built-in, 26,900 GitHub stars, 10.3M monthly downloads[^8] | OpenAI-centric | New projects on OpenAI models |
| AutoGen | Event-driven multi-agent | Scalable complex multi-agent workflows | Experimental-leaning | Research, complex collaboration |
| CrewAI | Role-based crews | Simple setup, 20-minute onboarding | Limited control flow | Straightforward multi-agent tasks |
| Temporal | Durable workflow engine | Crash-proof, fault-tolerant, production-grade | Not LLM-native, requires separate orchestration | Long-running workflows with side effects |
| Mastra | TypeScript-first | Modern DX, type safety | Smaller ecosystem | TypeScript AI applications |

**The critical insight of 2026:** LangGraph and Temporal are **not alternatives** — they solve different problems. LangGraph models agent reasoning and tool flow. Temporal keeps multi-step execution durable when workers restart, networks fail, or processes crash. Once real side effects (payments, emails, API calls, database writes) enter an agent workflow, both are typically needed. The open-source `langgraph-temporal` integration runs a LangGraph StateGraph as a Temporal Workflow with automatic recovery.[^9][^10]

**Principal Engineer view:** Reject LangChain expression language for new projects. Use LangGraph directly. Require Temporal for any workflow with real-world side effects, multi-hour execution, or human approval steps. Reserve AutoGen and CrewAI for internal tooling and research contexts where operational reliability requirements are lower.

### Model Context Protocol (MCP)

MCP has become the universal tool protocol connecting AI assistants to data sources, services, and tooling. As of May 2026, the PulseMCP registry lists over 5,500 MCP servers. The 2026-07-28 release candidate represents the largest protocol revision since launch: stateless core (scales on ordinary HTTP infrastructure), MCP Apps for server-rendered UIs, Tasks extension for long-running work, and OAuth/OIDC-aligned authorization.[^11][^12][^13]

**MCP vs. REST vs. CLI decision matrix:**

| Criterion | CLI | REST | MCP |
|---|---|---|---|
| Agent discoverability | Manual tool registration | Client must hardcode schema | Dynamic capability discovery |
| Authentication | Session-scoped | Per-request headers | OAuth/OIDC aligned (2026 spec) |
| Streaming | Limited | SSE/WebSocket | First-class |
| IDE integration | Full | Limited | Native (Cursor, VS Code) |
| Long-running tasks | Process lifecycle | Polling | Tasks extension (2026) |
| Best for | Dev tools, scripts | Public APIs, external integrations | AI assistants, agent tool access |

For internal tooling that agents need to call, MCP is the 2026 default. For public-facing APIs consumed by humans or external services, REST remains correct. CLI tools exposed via MCP servers are the canonical pattern for developer tooling.

### Memory Architecture

Production agent memory systems in 2026 have four tiers, corresponding to Karpathy's "LLM as CPU, context window as RAM" model:[^5][^14]

1. **In-context (working memory):** The current conversation, retrieved documents, tool results. Managed via LangChain's four strategies: Write (persist externally), Select (retrieve relevant), Compress (summarize old turns), Isolate (separate agent contexts).[^14]
2. **Episodic (session memory):** Stored between turns of a conversation session, typically in Redis/Valkey with TTL. Enables continuity without filling the context window.
3. **Semantic (long-term memory):** Embeddings of past interactions, decisions, preferences — retrieved via vector similarity. Enables personalization at scale.
4. **Procedural (instructions):** System prompts, behavioral rules, tool definitions. Cached aggressively — these should never be recomputed per request.

**Four failure modes to architect against** (Karpathy/LangChain framework):[^4]
- **Context Poisoning:** A hallucinated fact compounds across turns, corrupting all downstream reasoning
- **Context Distraction:** Conversation history overload drowns the relevant instruction
- **Context Confusion:** Irrelevant retrieved noise degrades tool selection accuracy
- **Context Clash:** Contradictory information from different turns creates incoherent behavior

### Durable Execution

Temporal's core primitive is crash-proof execution: all variables, including local variables, survive process crashes and are restored in a new process, after which execution continues as if the failure never occurred. This is not checkpointing — it is virtualized execution across a series of processes. The operational benefit for AI agents is elimination of the entire class of "we need to retry from step 4 because step 7 failed" logic that teams otherwise write manually.[^15]

The failure mode of using only LangGraph without durable execution: a 20-step research agent that fails at step 19 restarts from scratch. At scale, this creates both user-facing reliability failures and GPU cost overruns from redundant recomputation.

***

## Part III: Context Engineering

Context engineering is the discipline of deciding, per call, what information the model sees, in what order, at what cost, and with what caching behavior. Andrej Karpathy's framing — "the delicate art and science of filling the context window with just the right information for the next step" — has become the organizing principle of production AI teams in 2026.[^16][^14]

**The 2026 production stack:**
- Cached stable prefix (system instructions, tool definitions, examples)
- Dynamically retrieved context (RAG results, relevant documents)
- Retrieved few-shot examples (domain-specific input/output pairs)
- Structured XML/JSON scaffolding
- Strict output contracts (JSON schema, structured outputs)
[^17]

### Prompt Architecture

The canonical 2026 prompt scaffold:[^17]
```xml
text>
  {retrieved docs, files, prior context}
</context>
<examples>
  <example>
    <input>...</input>
    <output>...</output>
  </example>
</examples>
<task>
  Plain-English description of what you want.
</task>
<output_format>
  Exact schema, types, and constraints.
</output_format>
```

**Stable-first ordering is non-negotiable.** The top of the prompt should be the part that never changes across requests: role, policies, domain guide, tool definitions, invariant examples. The bottom should be the part that does change: retrieved docs, user turn, tool results. This is not stylistic — it is what makes caching work and keeps critical instructions out of the lossy middle of the window.[^16]

### Prompt Caching

Prompt caching (Anthropic `cache_control`, OpenAI automatic prefix caching, Gemini explicit cache) delivers 75–90% cost reduction and 85% latency reduction on cached prefixes. The implementation rule: mark your stable system block and stable tool-schema block explicitly, keep those blocks **byte-identical** across calls, and re-warm caches every 5 minutes if traffic is bursty. A cache hit rate below 60% on a repetitive workload indicates a structural prompt ordering problem.[^5][^17]

**Treat prompts as programs, not strings.** Version them, diff them, test them against a golden eval set on every change. A prompt regression is indistinguishable from a code regression in its user-facing impact but is invisible to standard CI without explicit prompt evaluation.[^17][^5]

***

## Part IV: RAG Systems

### The Retrieval Maturity Ladder

In 2026, industry analysis consistently shows that when RAG fails, the failure point is retrieval 73% of the time, not generation. The optimization ladder:[^18]

**Level 1 (Basic):** Fixed/recursive chunking, vector search only, results piped directly to LLM.

**Level 2 (Better chunking):** Semantic chunking that respects document structure. Recommended chunk sizes: documentation/knowledge base: 512–1024 tokens with 128-token overlap; code: function-level or class-level using AST parsing; legal/contracts: clause-level with full paragraph context. Expected improvement over Level 1: 9–70% in recall depending on baseline quality.[^18]

**Level 3 (Hybrid retrieval):** BM25 + dense retrieval in parallel, fused with Reciprocal Rank Fusion (RRF). Weaviate and Elasticsearch support this natively. For Pinecone, a separate BM25 index (OpenSearch or Typesense) is required with application-layer result merging. Expected improvement: 25% reduction in tokens sent to LLM, better exact-match recall.[^18]

**Level 4 (Reranking):** Cross-encoder reranking stage after hybrid retrieval. A typical production pipeline: retrieve top-50 with hybrid search → rerank to top-5 → pass to LLM. Expected improvement: 15–48% in overall retrieval quality. The leading open-source rerankers in 2026: BGE-Reranker-v2, Cohere Rerank 3, Jina Reranker v2. The Hierarchical Re-ranker Retriever (HRR) approach — sentence-level + 512-token chunks for retrieval, rerank, then expand to 2048-token parent chunks for generation — achieves both fine-grained retrieval and sufficient context.[^19][^20]

**Level 5 (Production pipeline):** All three working together. Semantic chunking + hybrid retrieval + reranking. This is what serious production systems use.[^20]

### Embedding Models

In 2026, `gte-Qwen2` beats OpenAI text-embedding-3 on the MTEB leaderboard. For production, `text-embedding-3-large` with Matryoshka dimension reduction (256 dims for initial retrieval, full 3072 dims for reranking) provides the best cost/quality tradeoff. Never embed in the hot path — always batch embedding during off-peak hours.[^21][^18]

### Semantic Caching

Cache the embedding of common queries. If a new query is cosine-similarity > 0.95 to a cached query, return the cached answer. This reduces LLM calls by 30–50% on typical production workloads.[^18]

### ColBERT and Late Interaction

ColBERT's late interaction model — compute token-level embeddings at index time, score against query token embeddings at retrieval time via MaxSim — outperforms bi-encoder models especially on technical and multi-concept queries. It is computationally more expensive than bi-encoders but cheaper than full cross-encoders. Use it when retrieval quality is the dominant concern and latency budget allows the extra computation.

***

## Part V: Vector Databases

### Decision Matrix

| Scenario | Choice | Rationale |
|---|---|---|
| Existing PostgreSQL app, < 50M vectors | **pgvector / pgvectorscale** | No second database, joins against application data work natively |
| Vectors at center of new app, speed matters | **Qdrant** | ~10–25% faster than Weaviate/Milvus on common workloads, p99 ~12ms at 10M vectors[^22] |
| Need built-in hybrid search | **Weaviate** | Native keyword+vector in single query, good managed cloud option |
| Zero ops budget, can pay for it | **Pinecone** | Fully managed serverless, 70% market share[^23] |
| Python prototyping | **Chroma** | Zero-friction setup |
| Billions of vectors with ops team | **Milvus or Vespa** | Mature sharding and partitioning at scale |

**pgvector update:** With pgvectorscale extension, PostgreSQL now delivers 471 QPS at 99% recall on 50M vectors — 11.4× better than Qdrant on the same benchmark, competitive with Pinecone. For the vast majority of production RAG systems with < 50M vectors, pgvector eliminates the need for a dedicated vector database entirely.[^23][^22]

**Principal Engineer view:** The vector database market is oversized relative to actual requirements. Start with pgvector. Only migrate to a purpose-built vector store when you hit a concrete bottleneck — storage at 50M+ vectors, recall-at-latency requirements your PostgreSQL deployment cannot meet, or hybrid search requirements that justify the operational overhead of a second database.

***

## Part VI: AI Evaluation

### Evaluation Architecture

Production AI evaluation in 2026 has three layers that must all be present:

**1. Offline evaluation (pre-deployment):** A golden test set of representative inputs with expected outputs. Run on every prompt change, model change, or retrieval pipeline change. This is regression testing for AI. Tools: Langfuse datasets, Braintrust, OpenAI Evals, RAGAS.[^24]

**2. Online evaluation (production sampling):** LLM-as-judge running on 10–20% of production traffic. Score outputs for criteria like hallucination, faithfulness, relevance, instruction-following, toxicity. The judge score is written back as a span attribute in OpenTelemetry, making it queryable alongside latency and token data. The pattern: "show me all traces where quality score < 0.7 AND retrieval returned fewer than 3 documents."[^25]

**3. Human evaluation:** For high-stakes domains (medical, legal, financial), a structured annotation workflow on sampled production outputs. Scale with crowdworkers once annotation guidelines are calibrated.

### LLM-as-Judge Best Practices

LLM-as-judge evaluators are prompts, and they require the same engineering discipline as production prompts: version them, test them, and retrain calibration when distribution shifts. Key failure modes:[^26]
- **Positional bias:** The judge prefers the first option in pairwise comparisons
- **Length bias:** Longer answers receive higher scores regardless of quality
- **Self-preference bias:** GPT-4 judges prefer GPT-4 outputs

Mitigation: use multiple judges from different model families, calibrate against human-labeled samples, track calibration drift over time.[^24]

### Evaluation Tools

| Tool | License | Key Strength | Best For |
|---|---|---|---|
| Langfuse | MIT (self-host) | Full-stack tracing + evals, prompt management | Primary observability + eval platform |
| Braintrust | SaaS | Strong dataset management, excellent UX | Teams prioritizing eval workflow |
| Arize Phoenix | Open source | OTel-native, LLM-as-judge via `phoenix.evals` | Self-hosted eval + tracing |
| RAGAS | Open source | RAG-specific metrics (faithfulness, relevance) | RAG pipeline evaluation |
| OpenAI Evals | Open source | Benchmark-style evaluation | Model comparison, regression |

***

## Part VII: AI Observability

### OpenTelemetry as the Foundation

OpenTelemetry is the correct telemetry standard for AI observability because it provides vendor-neutral distributed tracing, metrics, and logs across LLM calls, agent workflows, and traditional infrastructure — in a single pipeline. The GenAI semantic conventions standardize AI-specific attributes: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reason`. OpenInference semantic conventions extend this for agentic pipelines with tool call correlation attributes.[^27][^28][^25]

**Architecture:** Application code → OpenTelemetry SDK (with OpenLLMetry or OpenInference auto-instrumentation) → OTLP Exporter → OTel Collector → Observability backend (Langfuse, Phoenix, Datadog, Grafana Tempo).[^29]

**Critical implementation rules:**
- Create the root span at the very start of the request lifecycle. Batch processors buffer child spans until the root arrives; late root spans cause silent attribution failures.[^25]
- Never log raw completion content as a span **attribute** in production — span attributes are indexed and stored long-term. Use span **events** for completion content and apply sanitization at the event level.[^25]
- Use 100% sampling in development/staging. In production: 10–30% head-based sampling at trace level, with tail-based sampling triggered on errors or high-latency traces.[^25]

### The Observability Control Plane

OpenTelemetry is the data plane. Production AI observability also requires a control plane: a layer that applies evaluation scoring, hallucination detection, and policy enforcement on top of the telemetry. The two-platform pattern that production teams use: OpenTelemetry instrumentation (via Traceloop OpenLLMetry) for telemetry, paired with Langfuse or Datadog for evaluation and cost attribution, and optionally Helicone as a proxy for fine-grained per-request cost tracking.[^28][^27]

### What to Monitor

**Core metrics per request:** TTFT (time to first token), tokens/second, input/output token counts, cost per request, cache hit rate, retrieval recall (for RAG), tool call success rate (for agents).

**Aggregate alerts:**
- TTFT p95 > 2s
- Cost per request 30-day trend increasing >20%
- Cache hit rate dropping below 60%
- Retrieval quality score (LLM-as-judge) dropping below threshold
- Tool call error rate > 5%

***

## Part VIII: Backend Engineering

### API Protocol Selection

**REST** remains the default for all public-facing APIs. The 2024 Postman State of the API Report shows REST at 86% adoption, GraphQL at 29%, gRPC at 11%. REST in 2026 is schema-first OpenAPI — generate clients, validate requests, generate documentation from a single `openapi.yaml`. The simplicity, universal tooling, and native HTTP caching remain unbeatable for public API surfaces.[^30]

**gRPC** dominates internal service-to-service communication at organizations that have committed to it. Protocol Buffers binary serialization is 3–10× smaller than JSON. HTTP/2 multiplexing eliminates head-of-line blocking. Strongly typed contracts enable compiler-level safety. Benchmark: gRPC at 8ms latency versus REST at ~50ms for inter-service calls, 10,000 requests/second throughput with lower CPU usage. The operational cost: Protobuf schema management, a schema registry, and teams that understand HTTP/2 debugging.[^31]

**GraphQL** is correct when many different clients query a complex data graph and over-fetching / under-fetching is a real, measured problem. The correct architecture: gRPC microservices internally, GraphQL as a Backend-for-Frontend (BFF) aggregation layer for mobile/web clients, REST for public API surfaces.[^30]

**tRPC** for TypeScript monorepos where a single team owns both API and client — eliminates the schema overhead of GraphQL while providing end-to-end type safety.[^32]

**The honest 2026 recommendation:** REST for public APIs (default), gRPC for high-volume internal service-to-service traffic, GraphQL for client-facing APIs where the data-shape mismatch problem actually exists, tRPC for TypeScript full-stack teams.[^30]

### WebSockets and SSE for AI Applications

**Server-Sent Events (SSE)** are the correct protocol for LLM streaming responses: unidirectional, HTTP/1.1 compatible, trivially proxied, natively supported by every CDN and load balancer. SSE is what OpenAI, Anthropic, and every major LLM API uses for streaming.

**WebSockets** add bidirectional communication — use them when the client also needs to send messages in the same connection (e.g., voice assistants, real-time collaborative agents, interruption signals). The operational overhead of WebSocket connection management at scale (connection state, reconnection logic, load balancer stickiness) is significant. Default to SSE unless bidirectionality is a hard requirement.

### Clean Architecture for AI Systems

The architectural pattern that survives scale: **Vertical Slice Architecture** over layered (controller/service/repository) architecture for AI-heavy systems. Each use case (e.g., "run a research agent") is a self-contained slice with its own data access, business logic, and I/O. This maps naturally to agent workflows where each workflow has distinct data requirements and is not shared across the codebase.

**Hexagonal Architecture (Ports and Adapters)** remains the correct pattern for making AI systems testable. The LLM client, vector store client, and tool executors are adapters behind ports — replaced by test doubles in unit tests, by real implementations in integration tests (via Testcontainers), and by actual production services in deployment.

***

## Part IX: Distributed Systems

### Microservices vs. Modular Monolith

The 2026 consensus, supported by multiple systematic literature reviews and high-profile company reversals: **start with a modular monolith, decompose into microservices only when a concrete bottleneck demands it**.[^33][^34]

A modular monolith is a single deployable application internally divided into clearly defined, independent modules, each owning its logic and enforcing strict boundaries — not a tangled legacy codebase. The key discipline: **vertical slices by business capability, not horizontal layers by technical type**. Each module owns its data, its API surface, and its dependencies.[^34]

**Signals that justify microservices decomposition:**
- Independent scaling requirements (one module requires 100× more capacity than others)
- Different deployment cadences across teams that are creating coordination bottlenecks
- Team size beyond coordination capacity (Conway's Law enforcement)
- Regulatory isolation requirements (PCI, HIPAA data segregation)
- Proven performance bottleneck that architectural isolation would resolve

The failure mode of premature microservices: distributed monolith — all the operational complexity of microservices with none of the independence benefits, because services share databases and call each other synchronously in request chains.[^35]

### Event-Driven Architecture

The **Outbox Pattern** is the correct solution to the dual-write problem: when a database write and a message publish must both succeed atomically. Write to the `outbox` table in the same database transaction as the business data. A separate relay process (or CDC connector like Debezium) reads from the outbox and publishes to the message bus. This gives exactly-once delivery semantics without distributed transactions.[^36]

The **Saga Pattern** coordinates distributed transactions across services with explicit compensating transactions for rollback. Choreography-based sagas (services react to events) are simpler to implement but harder to debug. Orchestration-based sagas (a central coordinator, implemented in Temporal) provide better observability and are easier to reason about at scale.

**CQRS** (Command Query Responsibility Segregation) separates the write model from the read model. Justified when: read and write workloads have fundamentally different scaling requirements, the read model requires denormalization that would corrupt the write model, or different consistency levels are appropriate for reads versus writes. Not justified as a general pattern — adds significant complexity (synchronization lag, eventual consistency bugs, dual model maintenance).

### Message Queue Selection

| Queue | Throughput | Retention | Latency | When To Use |
|---|---|---|---|---|
| Kafka / Redpanda | Very High (millions/sec) | Long (days-years) | ~10ms | Event streaming, audit log, CDC, event sourcing |
| RabbitMQ | High (100K/sec) | Short (processed) | ~1ms | Task queues, work distribution, RPC |
| NATS JetStream | Very High | Configurable | Sub-ms | Service mesh communication, pub/sub at scale |
| SQS | Moderate | 14 days | ~100ms | AWS-native task queues, serverless triggers |
| Redpanda | Very High | Long | ~10ms | Kafka-compatible without ZooKeeper |

**Mature systems use multiple queues** by workload type: Kafka for event streams requiring replay (audit, CDC, analytics); RabbitMQ for task queues requiring precise routing and acknowledgment; NATS for sub-millisecond service communication.[^36]

**Kafka is overkill for 90% of teams.** The operational cost — ZooKeeper (or KRaft), partition management, consumer group coordination, replication factor tuning — is significant. If you don't need log-based retention, replay semantics, or millions of events per second, start with RabbitMQ or SQS.[^37]

**Redpanda** is Kafka-compatible, C++-based, ZooKeeper-free, and operationally simpler. For teams that need Kafka semantics without Kafka's operational overhead, Redpanda is the current recommendation.[^38]

***

## Part X: Caching

### Valkey vs Redis

In 2024, Redis changed its license from BSD to SSPL/RSALv2, triggering a Linux Foundation fork: **Valkey**. By mid-2026, Valkey is the default in-memory store for new projects at AWS ElastiCache, Google Cloud Memorystore, and Akamai. For the vast majority of use cases — caching, session storage, pub/sub, rate limiting, job queues — feature sets are equivalent and the license is the only meaningful difference.[^39][^40]

**Valkey advantages:** Up to 270% higher throughput and 70% lower latency via I/O multithreading (vs Redis 7.2), up to 40% improved memory efficiency. Fully open source (BSD). Backed by AWS, Google, Oracle, Ericsson.[^41]

**Use Redis** if your organization has an existing commercial Redis Enterprise agreement, or if you need Redis Stack features (JSON, full-text search, vector search) that haven't reached Valkey parity in your version.

### Single-Flight / Cache Stampede Prevention

Cache stampede (thundering herd) occurs when a popular cache entry expires and hundreds of concurrent requests simultaneously miss to the database. **Single-flight** (Go `singleflight`, Python equivalent patterns) deduplicates concurrent requests for the same key — only one request fetches from the database; all others wait for the result. This pattern is production-mandatory for any high-traffic cache entry.[^42]

**Probabilistic early rehydration** (PER): a cache entry becomes "soft-expired" before the hard TTL, with probability increasing as expiry approaches. Background goroutines/tasks recompute the value before expiry. This prevents stampedes without the complexity of distributed locks.

### Cache Hierarchy for AI Applications

For AI applications with expensive LLM calls, a tiered cache strategy:

1. **L1 (in-process):** LRU cache of request embeddings or completion results. Sub-millisecond access. Sized to ~1000 hot entries per process instance.
2. **L2 (Valkey/Redis):** Shared semantic cache across all instances. Cosine similarity lookup — if a new query embedding is within 0.05 of a cached query, return the cached response. 30–50% LLM call reduction on production workloads.[^18]
3. **L3 (database/vector store):** Full retrieval pipeline. Only reached on true cache misses.

***

## Part XI: Production Python

### The 2026 Standard Toolchain

The Astral toolchain has unified Python development: `uv` for package management + virtual environments, `Ruff` for linting and formatting, `Pyright` (or Astral's `ty`) for type checking. The migration from pip + virtualenv + black + flake8 + isort + mypy to uv + Ruff + Pyright is the single highest-ROI developer productivity improvement available to Python teams.[^43]

| Tool | Replaces | Speed Improvement |
|---|---|---|
| uv | pip, pip-tools, poetry, virtualenv | 10–100× faster installs |
| Ruff | flake8, black, isort, pylint | 100× faster than flake8 |
| Pyright | mypy | 5–10× faster, strict mode recommended |
| pytest | unittest | Industry standard |

**CI template:**
```yaml
- uses: astral-sh/setup-uv@v4
- run: uv sync
- run: uv run ruff check .
- run: uv run pyright
- run: uv run pytest
```


### Pydantic v2 and FastAPI

Pydantic v2 (Rust core) is 5–50× faster than v1 for validation. All new Python projects should use Pydantic v2. FastAPI's native Pydantic v2 integration means request/response validation is essentially free versus application logic. Use `model_config = ConfigDict(strict=True)` in production models to prevent coercion surprises.[^44]

For AI applications, **PydanticAI** and **instructor** provide structured output extraction from LLM responses using Pydantic schemas — the correct pattern for parsing LLM JSON output reliably.

### AsyncIO in Production

FastAPI with `asyncio` and a connection pool (psycopg3 + psycopg_pool, or asyncpg for PostgreSQL) can handle thousands of concurrent requests per process with sub-10MB memory overhead per connection. The critical rule: **never block the event loop**. CPU-bound operations must be offloaded to a thread pool (`asyncio.to_thread`) or process pool. LLM inference calls are I/O-bound and safe to await directly.

**Failure mode:** using `asyncio` while calling synchronous blocking libraries (requests, psycopg2, synchronous file I/O) in async handlers. This serializes all requests behind the blocking call. Use `aiohttp`/`httpx` for HTTP, `asyncpg`/psycopg3 async API for PostgreSQL, `aiofiles` for file I/O.

### Python 3.14

Python 3.14 (beta as of 2026) introduces free-threaded mode (no GIL for CPU-bound parallel execution in threads) as an opt-in flag (`-X gil=0`). For CPU-bound AI preprocessing (tokenization, embedding normalization, data transformation), free-threaded Python eliminates the need for multiprocessing in many cases. Not yet production-recommended — standard GIL Python 3.12/3.13 remains the production baseline.[^45]

***

## Part XII: Cloud Native Engineering

### Kubernetes Architecture for AI Workloads

**KEDA (Kubernetes Event-Driven Autoscaling)** is the correct autoscaling primitive for AI workloads in 2026. Standard HPA scales on CPU/memory, which are lagging indicators for LLM serving (a queue of 10,000 pending requests doesn't manifest as CPU pressure until the GPU is saturated). KEDA scales on queue depth, Kafka consumer lag, custom metrics, or — via custom external scalers — direct GPU utilization metrics via NVML. KEDA was accepted as a CNCF graduated project and is in production at organizations including Microsoft, RedHat, and Cloudera.[^46][^47]

**GPU autoscaling pattern:**
1. Custom DaemonSet runs on every GPU node, calls NVML, reads local GPU utilization
2. Serves metrics over gRPC using KEDA's ExternalScaler interface
3. KEDA operator drives HPA decisions based on GPU utilization
[^46]

This is the same pattern as Kubernetes device plugins and the metrics server — a per-node agent that collects local hardware data.

### GitOps and Progressive Delivery

**ArgoCD** is the production standard for GitOps-driven deployment. Git is the single source of truth for desired state; ArgoCD continuously reconciles actual cluster state to match. ArgoCD detects drift and alerts or auto-corrects, providing both stability and auditability.[^48]

**Argo Rollouts** extends this with progressive delivery: canary deployments that gradually shift traffic to new versions, blue-green deployments for instant traffic switching, and automated analysis that monitors custom metrics and triggers automatic rollback on anomaly detection. In 2026, ArgoCD + Argo Rollouts is the standard pattern for zero-downtime deployments of AI services.[^49]

**Feature flags** (OpenFeature standard, LaunchDarkly, Flagsmith) complement canary deployments for A/B testing prompt changes and model versions against live traffic without a deployment boundary.[^50]

### Service Mesh

**Istio** with the Kubernetes **Gateway API** (replacing the legacy Ingress resource) is the 2026 standard for production service mesh. Key capabilities: mTLS between all services (zero-trust networking), fine-grained traffic management (weight-based routing for canary deployments), circuit breaking at the mesh level, and distributed tracing injection.

The operational reality: Istio adds ~10ms latency overhead per hop and significant control plane resource requirements. Do not adopt Istio for its own sake — justify it by a concrete security or traffic management requirement.

***

## Part XIII: Observability

### OpenTelemetry as the Data Plane

OpenTelemetry is the production standard for distributed tracing, metrics, and logs — across AI and non-AI workloads alike. The three-signal model:

- **Traces:** The full call graph from user request through orchestrator, sub-agents, tool calls, database queries, and LLM invocations. Each step is a span with structured attributes.
- **Metrics:** RED (Request rate, Error rate, Duration) for services; USE (Utilization, Saturation, Errors) for infrastructure; custom AI metrics (token usage, cache hit rate, retrieval quality score).
- **Logs:** Structured JSON logs correlated to trace IDs for debugging specific request failures.

**SLOs over dashboards.** Define error budgets: latency p99 < X ms, error rate < Y%. Alert on budget burn rate, not on individual threshold crossings. A spike that consumes 10% of a 30-day error budget at 2 AM is actionable; a temporary p99 spike that resolves in 30 seconds is not.

### Prometheus and Grafana

**Prometheus** remains the standard for metrics collection and alerting. **Grafana** for dashboards, with Loki for logs and Tempo for traces. The unified Grafana stack — all four signals correlated in one platform — is the current production default for self-hosted observability.[^29]

For LLM cost observability, Helicone (proxy-based) provides the most precise per-request cost attribution with zero instrumentation changes. For teams that already use Datadog, its LLM Observability module integrates LLM-specific metrics alongside existing infrastructure monitoring.[^28]

***

## Part XIV: Security

### OAuth 2.1 and OIDC

**OAuth 2.1** consolidates a decade of security best practices into a single specification. Changes from OAuth 2.0 that are **mandatory** in new systems:[^51]

- PKCE is required for **all** clients, including confidential server-side clients
- The implicit grant is **removed** — use Authorization Code + PKCE for all SPAs and mobile apps
- The password/ROPC grant is **removed** — use Authorization Code flow
- Redirect URIs require **exact match** — no wildcards
- Bearer tokens **prohibited in query strings** — Authorization header only
- Refresh tokens for public clients require rotation or sender-constraining (DPoP/mTLS)

**Migration checklist:**[^52]
1. Audit: grep codebase for `grant_type=password` and `response_type=token`
2. Enable PKCE everywhere (backward compatible with most servers)
3. Audit redirect URI registrations for wildcards
4. Enable refresh token rotation for SPAs

### JWT Best Practices

JWTs in 2026: **short expiry** (15 minutes for access tokens), **RS256 or ES256** (never HS256 for distributed systems), **not stored in localStorage** (XSS vector) — use HTTP-only cookies or memory. Verify the `iss`, `aud`, `exp`, and `azp` claims on every request. Token introspection endpoints for revocation support.

### Passkeys

WebAuthn/Passkeys are the 2026 production standard for user authentication — phishing-resistant, no password database to breach, cross-device sync via platform authenticators. Major identity providers (Auth0, Okta, Cognito) support passkeys. For B2C consumer applications, passkeys are the recommended primary authentication method. For enterprise/B2B, OIDC with an enterprise identity provider (Okta, Azure AD) remains correct.

### Supply Chain Security

**SBOMs** (Software Bill of Materials) are moving from voluntary to mandatory. The EU Cyber Resilience Act takes effect in 2027; CISA requirements are tightening. Generate CycloneDX or SPDX SBOMs automatically in CI/CD — 2 hours of setup, immediate value during the next major CVE disclosure.[^53]

**SLSA** (Supply-chain Levels for Software Artifacts): Level 1 (automated builds with provenance) → Level 2 (signed provenance, hosted build platform) → Level 3 (hardened builds, isolated environments). The 80/20 approach: SLSA Level 2 with GitHub Actions builders and Sigstore signing. Only pursue Level 3 for critical infrastructure or customer compliance requirements.[^54][^53]

**Vault** (HashiCorp, or cloud-native equivalents: AWS Secrets Manager, GCP Secret Manager) for all secret management. No secrets in environment variables, no secrets in configuration files committed to Git, no secrets in container images. Rotate all credentials automatically on a 30-day or shorter cycle.

### Row-Level Security for Multi-Tenant AI Systems

PostgreSQL RLS is the correct implementation of multi-tenancy at the database layer for AI applications that store per-user context, conversation history, or embeddings. Define policies using `current_setting('app.current_tenant_id')` and enforce at the database layer, not the application layer. This provides defense-in-depth against application-layer authorization bugs that could expose tenant data.

***

## Part XV: Data Engineering

### Orchestration

**Dagster** has emerged as the modern orchestration default for new data engineering projects in 2026. Its software-defined assets model (pipelines defined around the datasets they produce, not the tasks they execute) provides better lineage, observability, and testability than Airflow's task-centric DAGs. Dagster's integrated metadata tracking and type-aware execution are directly compatible with dbt integration.[^55]

**Apache Airflow** remains the most widely deployed orchestrator by volume — it is the safe choice for organizations with existing Airflow investments and large teams familiar with it. For new greenfield projects, Dagster or Prefect are the current recommendations.[^56]

**dbt** (data build tool) is the production standard for SQL-based data transformation. dbt Core + Dagster is the canonical 2026 data stack for analytics engineering. dbt Core handles transformation logic, lineage, and documentation; Dagster handles scheduling, dependency management, and observability.

### Lakehouse Architecture

**Apache Iceberg** is the winning open table format for large-scale analytics. It provides ACID transactions on S3/GCS/ADLS, schema evolution, time-travel queries, and is supported natively by Snowflake, Databricks, BigQuery, and Apache Spark/Flink. Delta Lake (Databricks-native) is a strong alternative but more ecosystem-specific.

For AI data pipelines, the Lakehouse pattern (raw data → Bronze/Silver/Gold layers on Iceberg tables, queried by DuckDB for local analysis and Spark/Flink for large-scale processing) is the current architecture standard.

**DuckDB** for local and single-process analytics: zero-config, in-process columnar query engine, reads Iceberg/Parquet/CSV/JSON natively, runs embedded in Python. For any analytics workload that fits on a single machine (< 100GB working set), DuckDB eliminates the need for a separate analytics database.[^56]

***

## Part XVI: Testing

### Testing Strategy for AI Systems

**Testcontainers** for all integration tests involving databases, message queues, or other external dependencies. Real containers, not mocks. A PostgreSQL container with your actual schema is a 30-second startup cost that eliminates an entire class of "works in unit tests, fails in production" bugs.[^57]

**Property-based testing with Hypothesis** is the standard for testing AI input processing, prompt assembly, schema validation, and data transformation functions. Hypothesis generates hundreds of edge-case inputs automatically and reports the simplest failing example — the most important property for debugging. Properties to test: roundtrip (serialize/deserialize returns original), invariants (sorting preserves length), idempotency (applying an operation twice returns the same result).[^58][^57]

**Performance regression testing:** EXPLAIN ANALYZE assertions in CI for critical query paths (verified at query plan level, not just execution time). Load testing with Locust or k6 against a staging environment before every production release.

**Chaos engineering:** Randomly kill replicas in staging using Chaos Mesh or LitmusChaos. Introduce latency on external dependencies. Verify circuit breakers and retry logic under realistic failure conditions. Netflix's chaos engineering principles remain the standard — test failure recovery in a controlled environment before it happens unpredictably in production.

### AI-Specific Testing

**Prompt regression testing:** A golden eval set of representative inputs with expected outputs, run on every prompt change. Track: did the change improve the metrics it was intended to improve? Did it regress any other metric?[^17]

**Agent testing:** Test each tool function in isolation with unit tests. Test the agent's tool selection logic with scripted scenarios. Test end-to-end workflows with Testcontainers providing real dependencies. Avoid mocking the LLM itself in integration tests — use a lightweight model (GPT-4o-mini, Haiku) against the real API with deterministic seed where available.

***

## Part XVII: CI/CD

### Build Pipeline Standards

**GitHub Actions** with aggressive build caching is the 2026 default for most organizations. Key optimizations: cache Python environments via `uv` lock file hash, cache Docker layer builds, cache test database container images.

**ArgoCD** for GitOps-driven Kubernetes deployment. The GitOps loop: developer merges to main → CI builds and pushes Docker image → CI updates image tag in GitOps repo → ArgoCD detects change and reconciles cluster state.[^49]

**Preview environments** (Ephemeral environments per pull request, deployed via Argo CD ApplicationSets or Vercel-style preview deployments) are the highest-ROI CI/CD investment for teams building AI applications: each PR gets a real endpoint with the new prompt logic that reviewers can test directly.

***

## Decision Trees

### "What inference engine should I use?"
1. Is hardware non-NVIDIA (AMD, Trainium, TPUs)? → **vLLM** (only multi-platform option)
2. Is your workload batch processing or templated prompts with minimal prefix reuse? → **vLLM**
3. Is your workload multi-turn chat, agents, or RAG with shared prefixes? → **SGLang**
4. Is the model stable for months and peak NVIDIA performance is the #1 priority? → **TensorRT-LLM**
5. Is this local development or prototyping? → **Ollama**

### "Do I need a vector database?"
1. Total vectors < 50M AND you already run PostgreSQL? → **pgvector/pgvectorscale** (done)
2. Pure vector workload, speed matters? → **Qdrant**
3. Need built-in hybrid search (keyword + vector)? → **Weaviate**
4. Zero ops, can pay? → **Pinecone**
5. Billions of vectors with real ops team? → **Milvus or Vespa**

### "What agent framework should I use?"
1. Is the workflow deterministic and the sequence known in advance? → **No agent needed, build a workflow**
2. Is this TypeScript? → **Mastra**
3. Is this primarily OpenAI models, low complexity? → **OpenAI Agents SDK**
4. Does it require multi-provider, complex control flow, or enterprise observability? → **LangGraph**
5. Does it have real-world side effects, human approvals, or multi-hour execution? → **LangGraph + Temporal**
6. Is this research or experimental multi-agent collaboration? → **AutoGen**

### "Monolith or microservices?"
1. Team < 8 engineers? → **Modular monolith**
2. Domain is still being discovered? → **Modular monolith**
3. Do you have more than one module that requires 10×+ different scaling? → Consider microservices for that module only
4. Do you have independent deployment requirements enforced by Conway's Law? → Microservices for those teams
5. Default answer for most teams in 2026 → **Modular monolith until proven otherwise**

***

## Principal Engineer Review

### What a Principal Engineer from Google/OpenAI/Stripe/Cloudflare would:

**Approve:**
- vLLM / SGLang for inference serving (not rolling your own)
- Temporal for durable agent workflows
- OpenTelemetry for all observability (including GenAI conventions)
- uv + Ruff + Pyright as the Python toolchain
- pgvector for < 50M vectors co-located with PostgreSQL
- Valkey replacing Redis
- Modular monolith as default architecture
- OAuth 2.1 + PKCE with ROPC removed
- Testcontainers for integration tests
- ArgoCD + Argo Rollouts for progressive delivery
- KEDA for AI workload autoscaling

**Reject:**
- Building a custom LLM serving engine
- LangChain expression language (use LangGraph directly)
- Mocking the LLM in integration tests
- Microservices for teams < 8 engineers
- Offset pagination on large tables (use keyset)
- Storing secrets in environment variables
- OAuth implicit grant in any new system
- LangGraph without Temporal for workflows with real side effects
- pgvector at > 100M vectors without pgvectorscale
- Static batching in LLM inference

**Simplify:**
- Reduce agent frameworks to one: either OpenAI Agents SDK or LangGraph, not both
- Collapse observability vendors: one tracing backend (Langfuse or Datadog), one metrics backend (Prometheus + Grafana)
- Remove custom RAG chunking logic — use semantic/structural chunking from a maintained library

**Delay:**
- Free-threaded Python 3.14 in production (wait for 3.14 stable and ecosystem readiness)
- SLSA Level 3+ unless you are critical infrastructure or have explicit compliance requirements
- Disaggregated prefill/decode serving unless you have a real latency SLA problem
- Passkeys for B2B enterprise (wait for SSO/OIDC adoption to reach parity)

**Redesign:**
- Any LLM application without prompt caching (this is leaving 60–90% of cost on the table)
- Any RAG system that doesn't have reranking (the quality gap is 15–48%)
- Any agent system without structured output enforcement (JSON schema / constrained decoding)
- Any AI system without LLM-as-judge production sampling

***

## Maturity Model (Levels 1–5 Across Domains)

### AI Inference
- **L1:** Direct API calls to OpenAI/Anthropic, no caching, no monitoring
- **L2:** Streaming responses, retry logic, basic error handling
- **L3:** vLLM/SGLang self-hosted or managed, continuous batching, FP8 quantization
- **L4:** Prefix caching, KV cache optimization, speculative decoding, cost/latency dashboards
- **L5:** Disaggregated prefill/decode, multi-GPU tensor parallelism, model routing, SLO-based scheduling

### Agent Engineering
- **L1:** Simple ReAct loop with an LLM
- **L2:** Structured tool definitions, basic error handling, retry on failure
- **L3:** LangGraph state machines, MCP tool protocol, streaming to client
- **L4:** Temporal durable execution, human-in-the-loop approval, full trace observability
- **L5:** Multi-agent systems with specialized roles, self-evaluation and reflection, adaptive planning

### RAG Systems
- **L1:** Fixed-size chunking, single vector search
- **L2:** Recursive chunking, SOTA embedding model
- **L3:** Hybrid retrieval (BM25 + dense), RRF fusion
- **L4:** Cross-encoder reranking, semantic caching, hierarchical chunking
- **L5:** Agentic RAG with query decomposition, citation tracking, freshness management, RAGAS evaluation in CI

### Observability
- **L1:** Application logs only
- **L2:** Prometheus metrics, Grafana dashboards
- **L3:** OpenTelemetry distributed traces, structured logging
- **L4:** GenAI semantic conventions, LLM-as-judge production sampling, cost attribution
- **L5:** SLO-based alerting, error budget burn rate, causal attribution across full stack

### Security
- **L1:** Basic authentication, HTTPS
- **L2:** OAuth 2.0, JWT, Vault for secrets
- **L3:** OAuth 2.1 + PKCE, RLS for multi-tenant data, SBOM generation
- **L4:** Passkeys, SLSA Level 2, contextual vulnerability analysis
- **L5:** Zero-trust networking (Istio mTLS), supply chain attestations, continuous compliance posture

***

## Anti-Patterns to Avoid in 2026

1. **Over-fetching context:** Sending 30 retrieved chunks "to be safe." Retrieval recall past k=8 typically degrades quality by drowning relevant chunks. Tune k per route.
2. **Mocking LLMs in integration tests:** Tests pass, production fails. Use real lightweight models with Testcontainers.
3. **Implicit grant OAuth:** Removed in OAuth 2.1. If you still use it, you are shipping a known vulnerability.
4. **Synchronous blocking in async handlers:** Serializes all requests. Profile first.
5. **Static batching in LLM inference:** Continuous batching is a configuration change that typically doubles throughput.
6. **Premature microservices:** More teams have been burned by this than by staying monolithic too long.
7. **UUID v4 primary keys on high-write tables:** Random distribution destroys B-tree locality. Use UUIDv7 (time-ordered) or BIGSERIAL.
8. **Storing tokens in localStorage:** HTTP-only cookies or in-memory only.
9. **No prompt versioning:** You cannot debug a regression you cannot reproduce. Version prompts like code.
10. **LangGraph without Temporal for production workflows with side effects:** The first network failure at step 15 of 20 will cost you more engineering time than the Temporal integration would have.

***

## The June 2026 Standard vs. State of the Art vs. Best Practice

| Topic | Industry Standard | State of the Art | Enduring Best Practice |
|---|---|---|---|
| LLM Inference | vLLM + continuous batching | SGLang + disaggregated prefill/decode | Continuous batching + prefix caching |
| Agent Orchestration | LangGraph | LangGraph + Temporal | Durable execution for side effects |
| Tool Protocol | MCP (2025 spec) | MCP 2026-07-28 stateless | Standard protocols over custom integrations |
| RAG | Hybrid retrieval | HRR + agentic RAG + adaptive control | Reranking before generation |
| Observability | Prometheus + Grafana | OTel GenAI + LLM-as-judge | Instrument everything before optimizing |
| Python Toolchain | uv + Ruff | uv + Ruff + Pyright strict | Type safety + fast iteration |
| Cache | Valkey | Valkey + semantic cache | Cache at every layer |
| Auth | OAuth 2.0 | OAuth 2.1 + Passkeys | PKCE mandatory, implicit removed |
| Architecture | Microservices | Modular monolith → selective decomposition | Logical boundaries before physical ones |
| Data Orchestration | Airflow | Dagster + dbt | Asset-centric pipelines |
| Supply Chain | SBOM | SLSA Level 2 + contextual analysis | SBOMs in CI before SLSA |
| Kubernetes Scaling | HPA (CPU-based) | KEDA (event-driven + GPU-aware) | Scale on the right signal |

---

## References

1. [vLLM vs SGLang 2026: H100 Benchmarks Inside | TECHSY](https://techsy.io/en/blog/vllm-vs-sglang) - SGLang wins for dynamic, multi-turn workloads. vLLM is perfectly adequate for batch inference and te...

2. [vLLM vs Ollama vs SGLang vs TensorRT-LLM - The AI Engineer](https://theaiengineer.substack.com/p/vllm-vs-ollama-vs-sglang-vs-tensorrt) - vLLM is the production default. SGLang beats vLLM by 29% on throughput , RAG, agents). TensorRT-LLM ...

3. [LLM Inference Optimization: A Practical Guide for AI Engineers (2026)](https://jobsbyculture.com/blog/llm-inference-optimization-guide-2026) - Master KV cache optimization, quantization, speculative decoding, Flash Attention, and continuous ba...

4. [Context Engineering Guide 2026: Beyond Prompting - Shareuhack](https://www.shareuhack.com/en/posts/context-engineering-guide-2026) - DEV Community's Gabriel Henrique documents that prompt caching in production systems can achieve 75-...

5. [Prompt Engineering Best Practices 2026 | Thomas Wiegold Blog](https://thomas-wiegold.com/blog/prompt-engineering-best-practices-2026/) - Prompt engineering best practices have fundamentally changed. Learn what works in 2026—context engin...

6. [LLM Inference in 2026: How It Works, Latency & Cost - Future AGI](https://futureagi.com/blog/llm-inference-human-prompts-2025/) - Prefix caching stores the KV cache for that shared prefix and reuses it on subsequent requests, drop...

7. [LLM Inference Optimization Techniques - Redwerk](https://redwerk.com/blog/llm-inference-optimization-techniques/) - Speculative decoding uses a cheap draft model (or a speculative process) to propose several future t...

8. [The best open source frameworks for building AI agents in 2026](https://www.firecrawl.dev/blog/best-open-source-agent-frameworks) - The OpenAI Agents SDK is a lightweight Python framework released in March 2025 with over 26,900 GitH...

9. [Temporal vs LangGraph (2026): Durable Agent Architecture - Cordum](https://cordum.io/blog/temporal-vs-langgraph) - -LangGraph already supports durable execution with checkpoints, but durable behavior depends on how ...

10. [pradithya/langgraph-temporal - GitHub](https://github.com/pradithya/langgraph-temporal) - Temporal integration for LangGraph — durable execution for stateful AI agents. Run your existing Lan...

11. [The 2026-07-28 MCP Specification Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) - Model Context Protocol (MCP) specification is now available: a stateless protocol core, the Extensio...

12. [Introducing the Model Context Protocol - Anthropic](https://www.anthropic.com/news/model-context-protocol) - The Model Context Protocol is an open standard that enables developers to build secure, two-way conn...

13. [MCP Adoption Statistics 2026](https://mcpmanager.ai/blog/mcp-adoption-statistics/) - Model Context Protocol (MCP) As of today (10/22/2025), the popular MCP registry, PulseMCP, has over ...

14. [Context Engineering > Prompt Engineering: What Changed for ...](https://bigdataboutique.com/blog/from-prompt-engineering-to-context-engineering) - Context engineering designs the full information environment (retrieved docs, tool outputs, memory, ...

15. [The definitive guide to Durable Execution - Temporal](https://temporal.io/blog/what-is-durable-execution) - Learn what Durable Execution is and how it enables developers to quickly create reliable application...

16. [Context Engineering Best Practices (2026): A 12-Point Checklist](https://sureprompts.com/blog/context-engineering-best-practices-2026) - A 12-point checklist for context engineering in 2026: budget the window, cache the stable prefix, lo...

17. [Prompt Engineering in 2026: Context Beats Cleverness - NovaKit](https://www.novakit.ai/blog/prompt-engineering-2026-context-over-cleverness) - This is context engineering. The 2026 stack: prompt caching, few-shot examples pulled via RAG, struc...

18. [RAG Production Guide 2026: Retrieval-Augmented Generation](https://lushbinary.com/blog/rag-retrieval-augmented-generation-production-guide/) - This guide covers what actually works in production: chunking strategies, embedding model selection,...

19. [Hierarchical Re-ranker Retriever (HRR)](https://arxiv.org/pdf/2503.02401.pdf) - ...information retrieval - too large a chunk dilutes semantic
specificity, while chunks that are too...

20. [Beyond Basic RAG: Chunking, Hybrid Search, and Reranking](https://www.onsomble.ai/blog/advanced-rag-optimization) - This article covers three techniques that take RAG from functional to genuinely good: smarter chunki...

21. [Production-Ready RAG on Open Models: Chunking, Retrieval ...](https://regolo.ai/production-ready-rag-on-open-models-chunking-retrieval-reranking-evaluation/) - Naive RAG setups chunk blindly, embed with weak models, retrieve irrelevant chunks, and pipe garbage...

22. [Vector databases compared 2026: pgvector vs Qdrant vs Weaviate](https://layerbase.com/blog/vector-databases-compared-2026) - Public benchmarks have Qdrant about 10-25% faster than Weaviate or Milvus on common workloads. P99 a...

23. [When to Use pgvector vs Pinecone vs Weaviate - DEV Community](https://dev.to/polliog/postgresql-as-a-vector-database-when-to-use-pgvector-vs-pinecone-vs-weaviate-4kfi) - PostgreSQL now delivers 471 QPS at 99% recall on 50M vectors. That's 11.4x better than Qdrant and co...

24. [LLM Evaluation 101: Best Practices, Challenges & Proven Techniques](https://langfuse.com/blog/2025-03-04-llm-evaluation-101-best-practices-and-challenges) - In this post, we'll walk through some tried-and-true best practices, common pitfalls, and handy tips...

25. [Setting Up LLM Observability Pipelines in 2026 - MLflow](https://mlflow.org/articles/setting-up-llm-observability-pipelines-in-2026/) - Unlock efficient debugging by setting up LLM observability pipelines. Learn to trace every layer and...

26. [The Rage Clicks of LLM apps: High-Signal Production Monitoring for ...](https://langfuse.com/blog/2026-04-01-llm-as-a-judge-production-monitoring) - How to use LLM-as-a-judge to detect when your users say "f**k" - and other high-signal events worth ...

27. [OpenTelemetry AI Observability Guide | Fiddler AI Blog](https://www.fiddler.ai/blog/opentelemetry-ai-observability-guide) - A practitioner's guide to using OpenTelemetry as your AI telemetry foundation, and understanding whe...

28. [8 Best AI Agent Observability Tools in 2026 - AY Automate](https://www.ayautomate.com/blog/best-ai-agent-observability-tools) - Compare the 8 best AI agent observability tools in 2026. Tracing, evals, and LLM cost tracking acros...

29. [AI Observability and Agent Monitoring 2026 | Zylos Research](https://zylos.ai/research/2026-01-16-ai-observability-agent-monitoring) - Comprehensive analysis of AI observability tools, platforms, and best practices for monitoring LLM a...

30. [gRPC vs REST vs GraphQL: A Battle-Tested Comparison | BirJob](https://www.birjob.com/blog/grpc-rest-graphql) - gRPC vs REST vs GraphQL: A Battle-Tested Comparison. In 2022, our team migrated a microservices syst...

31. [REST vs gRPC vs GraphQL - 90% of Developers Choose Wrong!](https://www.youtube.com/watch?v=ygM1VwtPF_k) - REST vs gRPC vs GraphQL - Which API style should you use 2026 In this video, I'll show you EXACTLY w...

32. [GraphQL vs REST in 2026: API Architecture Decision - Digital Applied](https://www.digitalapplied.com/blog/graphql-vs-rest-2026-api-architecture-decision-matrix) - REST still powers the majority of public APIs in 2026, while GraphQL has moved firmly into productio...

33. [Back to the Future: From Microservice to Monolith](https://arxiv.org/pdf/2308.15281.pdf) - Recently the trend of companies switching from microservice back to monolith
has increased, leading ...

34. [Rethinking Microservices in 2026: When Modular Monolith ...](https://enqcode.com/blog/rethinking-microservices-in-2026-when-modular-monolith-architecture-actually-win) - Neither architecture is universally better. Modular monoliths work best for small to mid-sized teams...

35. [Microservices vs. Monolithic Architectures in Real-Time Distributed ...](https://jisem-journal.com/index.php/journal/article/view/13614) - This article will discuss the differences between microservice and monolithic architecture in real-t...

36. [Choosing the Right Message Broker: Kafka vs RabbitMQ vs NATS](https://www.linkedin.com/pulse/choosing-right-message-broker-kafka-vs-rabbitmq-nats-chakravarthy-hftge) - So let's talk about Kafka, RabbitMQ, and NATS the way production systems experience them. -The First...

37. [Kafka Is Overkill for 90% of Teams - BirJob](https://www.birjob.com/blog/kafka-overkill-redpanda-nats-message-broker) - Why most teams don't need Kafka. Comparison of Redpanda, NATS, SQS, and RabbitMQ with cost breakdown...

38. [Apache Kafka alternatives: comparison guide - Redpanda](https://www.redpanda.com/guides/kafka-alternatives) - Learn how Apache Kafka compares with Pulsar, RabbitMQ, NATS, Amazon Kinesis, and Redpanda for scalab...

39. [What is Valkey? A comparison with Redis](https://redis.io/blog/what-is-valkey/) - Valkey forked from Redis in 2024. Compare the two on data structures, vector search, licensing, and ...

40. [Valkey in 2026: What Happened When Redis Changed Its License](https://www.codercops.com/blog/valkey-redis-fork-open-source-2026) - By mid-2026, Valkey is the default in-memory store for new projects at most cloud providers. AWS Ela...

41. [Redis OSS vs. Valkey - Difference Between Caches - AWS](https://aws.amazon.com/elasticache/redis/) - The most important difference is Valkey is fully open source (BSD licensing) and will always be open...

42. [How to Reduce DB Load with Request Coalescing in Python](https://oneuptime.com/blog/post/2026-01-23-request-coalescing-python/view) - Request coalescing, also known as request deduplication or single-flighting, is a technique where co...

43. [Python tools I used in 2025 - brtkwr.com](https://brtkwr.com/posts/2025-12-27-python-tools-i-used-in-2025/) - The Astral toolchain (uv + ruff + ty) is shaping up to be the complete Python setup - all Rust-based...

44. [The New Python Workflow Everyone Is Switching To (uv + Ruff + ...](https://python.plainenglish.io/the-new-python-workflow-everyone-is-switching-to-uv-ruff-pydantic-v2-aa2077384f51) - uv + Ruff + Pydantic v2 is what happens when Python tooling finally catches up to developer expectat...

45. [Python Production Setup 2026: Tools That Actually Work](https://blog.stackademic.com/python-production-setup-2026-tools-that-actually-work-f30e92fcb0fd) - This one recommends what actually works in production. Covering uv, Ruff, FastAPI with Pydantic v2, ...

46. [GPU autoscaling on Kubernetes with KEDA: Building an external ...](https://www.cncf.io/blog/2026/05/27/gpu-autoscaling-on-kubernetes-with-keda-building-an-external-scaler/) - Building custom external scalers is a powerful way to extend the CNCF ecosystem. It shows how a grad...

47. [KEDA | Kubernetes Event-driven Autoscaling](https://keda.sh) - With KEDA, you can drive the scaling of any container in Kubernetes based on the number of events ne...

48. [GitOps Workflows with Progressive Delivery and Canary Deployments](https://uplatz.com/blog/gitops-workflows-with-progressive-delivery-and-canary-deployments/) - Implement safer deployments with GitOps workflows. This guide covers progressive delivery strategies...

49. [How to Implement Progressive Delivery with ArgoCD - OneUptime](https://oneuptime.com/blog/post/2026-01-25-progressive-delivery-argocd/view) - Learn how to implement progressive delivery strategies with ArgoCD and Argo Rollouts, including cana...

50. [Feature-Flagged Progressive Delivery: Argo Rollouts + OpenFeature](https://towardsaws.com/feature-flagged-progressive-delivery-argo-rollouts-openfeature-bd93c8ddd75f) - Progressive delivery combines Argo Rollouts for controlled traffic shifts with OpenFeature for featu...

51. [OAuth 2.0 vs OAuth 2.1: What Changed? - LoginRadius](https://www.loginradius.com/blog/engineering/oauth-2-0-vs-oauth-2-1) - Compare OAuth 2.0 vs OAuth 2.1, key security changes, deprecated flows, and a practical migration ch...

52. [OAuth 2.0 vs 2.1: What Changed and How to Migrate - Aembit](https://aembit.io/blog/oauth-2-1-guide-migration-security/) - OAuth 2.1 eliminates implicit flow, mandates PKCE, and requires exact redirect matching. Learn what ...

53. [SBOMs vs SLSA: Which Supply Chain Security Do You Need?](https://www.practical-devsecops.com/sbom-vs-slsa-software-supply-chain-security-comparison/) - SBOMs list what's in your software. SLSA verifies how it was built. Learn when you need each, and wh...

54. [What is The SLSA Framework? Supply-chain Levels for ... - Wiz](https://www.wiz.io/academy/application-security/slsa-framework) - SLSA is a consensus-based, cross-industry effort that gives security and development teams a shared ...

55. [Data Pipeline Orchestration Tools: Top 6 Solutions in 2026 - Dagster](https://dagster.io/learn/data-pipeline-orchestration-tools) - Dagster is an open-source data orchestrator built for modern data engineering teams that need reliab...

56. [Got told 'No one uses Airflow/Hadoop in 2026'. : r/dataengineering](https://www.reddit.com/r/dataengineering/comments/1qqsfmm/got_told_no_one_uses_airflowhadoop_in_2026/) - Having used Prefect and Dagster in production, I personally recommend Dagster for its better overall...

57. [How to Build Property-Based Testing with Hypothesis - OneUptime](https://oneuptime.com/blog/post/2026-01-30-how-to-build-property-based-testing-with-hypothesis/view) - Learn how to use property-based testing with Hypothesis in Python to discover edge cases and improve...

58. [Hypothesis](https://hypothesis.works) - Hypothesis is the property-based testing library for Python. With Hypothesis, you write tests which ...

