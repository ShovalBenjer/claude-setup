# Latent Vector Workflow Rules

These rules translate vector-to-vector multi-LLM ideas into today's Claude/Gastown workflow system.

## Principle

Plain English handoffs are useful for humans but lossy for agent coordination. When a workflow has many agents, repeated handoffs, research synthesis, or eval feedback, prefer a dual channel:

- Human channel: compact claims, evidence, decisions, changed files, risks.
- Machine channel: structured state, embeddings, retrieval keys, eval scores, graph edges, sparse claim ids, and next-action vectors represented in files or databases.

Claude cannot directly pass hidden activations between closed models. Do not pretend it can. Approximate the useful parts with embeddings, vector stores, structured state, eval gradients, and reusable transition adapters.

## When To Use

Use Latent Systems Lab when any of these are true:

- More than 3 agents are working in parallel.
- Handoffs are repeating the same context in prose.
- Research synthesis depends on many semantically similar notes.
- A task needs recursive passes over the same model role.
- Eval signals should steer the next prompt, tool call, or agent assignment.
- The lead needs `claude-opus-4-8[1m]` but can shrink working memory through retrieval.

Do not use it for small one-shot edits, simple answers, or tasks where human-readable proof is the main deliverable.

## Relay Pattern

1. Mayor Opus defines the graph: nodes, edges, stop condition, and shared state schema.
2. Latent Systems Lab creates the state substrate: SQLite, DuckDB, JSONL, embeddings, vector index, or notebook.
3. Workers write compact state records instead of long prose dumps.
4. Evidence Clerk pins every state claim to a source, command, or artifact.
5. QA Lab turns eval results into routing signals.
6. Mayor Opus synthesizes from the state graph and emits a human-readable decision.

## State Record

Every machine-channel record should include:

```json
{
  "id": "stable-id",
  "task": "what this record answers",
  "agent": "persona-name",
  "claim": "short claim",
  "evidence": ["path/url/command"],
  "embedding_text": "semantic text to embed or retrieve",
  "score": 0.0,
  "confidence": "low|medium|high",
  "next_edges": ["other-record-id"],
  "risk": "remaining uncertainty"
}
```

## Differentiable-Agent Analogy

For closed LLM tooling, treat this as an analogy, not a claim of true end-to-end gradient flow:

- Dense vectors become embeddings and retrieval state.
- Trainable transitions become prompt adapters, routing policies, eval thresholds, and small local models when available.
- Weight sharing becomes recursive reuse of the same persona over multiple passes.
- Gradient descent becomes eval-driven iteration: score, route, patch, retest.

## Parallel Fanout

Preferred fanout shapes:

- Map: many agents answer independent questions into the same state table.
- Reduce: Evidence Clerk deduplicates and grounds claims.
- Critic: QA Lab or Review Board attacks the best current answer.
- Recursive loop: same persona reruns with only the changed state, not the full transcript.
- Router loop: Mayor changes agent assignment based on eval scores.

## Safety Rules

- Never hide final reasoning only in vectors. Human-readable evidence remains mandatory.
- Never use embeddings as proof. They are routing and recall aids.
- Do not store secrets, raw credentials, or private unredacted customer data in vector indexes.
- If a workflow creates a long-lived index, document source scope, refresh date, and deletion path.
