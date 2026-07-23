# Local model stress test — 2026-07-23

Point-in-time hardware probe + throughput benchmark to decide what open model this
machine can run and what it is genuinely useful for.

## Hardware (measured)
- GPU: NONE discrete. Intel Iris Plus (integrated, shares RAM, no CUDA).
- CPU: Intel i7-1065G7 (2019 Ice Lake ultrabook), 4 cores / 8 threads, 1.3 GHz base.
- RAM: 16 GB total; typically 3-5 GB free with Chrome+WhatsApp+Claude live.
- Disk: 492 GB free (not a constraint).
- Runner: Ollama installed; qwen2.5:1.5b and qwen2.5:7b already pulled.

## Throughput (Ollama /api/generate, temp 0, measured)
| Model | tok/s | RAM behavior | Verdict |
|---|---|---|---|
| qwen2.5:1.5b (~1 GB, Q4) | 13.8 | comfortable | USABLE — the sweet spot |
| qwen2.5:7b (~4.7 GB, Q4) | 3.5 | drove free RAM to 0.6 GB (thrash) | technically runs, practically NO alongside work |
| 14B+ | — | exceeds RAM | NO |

## Capability finding (honest)
- A 1.5B is too weak ZERO-SHOT: it echoed the enum schema literally on 4/5 routing
  cases instead of choosing a value.
- With FEW-SHOT examples + `format:json`, it scored 5/5 correct on route AND risk
  (delete->high, deploy->high, question->low), ~3.5s/call after warmup.
- What it CANNOT do at this size: review code, judge Claude's output, be a
  decorrelated refuter, write user-facing prose. Not a reviewer, not a judge.

## The genuine uses for THIS hardware
1. **Local intent+risk classifier / router pre-filter** (BUILT: tools/local/route_classify.py).
   Cheap first-pass triage before Claude: tags route + risk locally, $0, offline,
   private (no data leaves the box — pii-handling). The risk tag feeds the approval
   gate (high => require approval). Needs few-shot (baked into the script).
2. **Local embeddings** (recommended, not yet wired): a small embedding model
   (nomic-embed-text ~275 MB) is CPU-fast and reliable — powers L2 memory retrieval,
   semantic repo-graph edges, and dedup. This is the higher-value second use; pull
   when RAM is free.

## Decision
Local model = a free, private, mechanical-triage lane on hardware you already own.
It is NOT a reviewer/judge — that role needs a real GPU + a 30-70B open model
(rented ephemerally per ADR-0009 direction), or stays with Claude/Codex. The laptop's
job is cheap high-volume classification + embeddings, not judgment.
