# Scalable LLM Agent Evaluation (2026)

## The Problem

Standard LLM-as-judge: per-question GPT-4 call. At 10K daily queries × 5 agents = 50K calls/day ≈ $150/day. The field has **no published consensus** alternative (confirmed: KDD 2025, ICLR 2026 MemAgents Workshop). The GD Coverage Metric + Lipschitz extrapolation is the most principled approach currently available.

## The Tier Hierarchy

### Tier 1 — Lipschitz Extrapolation (0 LLM calls, lower bounds)

From `02-coverage-metrics.md`. Uses GD scores + embedding distance to bound quality on unseen questions. Conservative (lower bound), but free after initial GD evaluation and embedding pass.

**Cost**: O(M × N) cosine distances (matrix multiply, GPU-accelerated). ~$5/day for embeddings only.

**When to use**: Daily monitoring dashboard, alert if CWS drops >5%.

### Tier 2 — Weighted Cosine Interpolation (0 LLM calls, point estimates)

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_distances

def interpolate_score(user_emb, gd_embs, gd_scores, k=5):
    """
    Weighted average of k nearest GD scores by inverse distance.
    More accurate than Tier 1 but gives point estimate, not bound.
    """
    dists = cosine_distances(user_emb.reshape(1,-1), gd_embs)[0]  # (N,)
    topk_idx = np.argsort(dists)[:k]
    weights = 1.0 / (dists[topk_idx] + 1e-8)
    return float(np.average(gd_scores[topk_idx], weights=weights))
```

**When to use**: Per-question score for covered queries. Don't use for uncovered (white gap) queries — flag those instead.

### Tier 3 — Cluster-Sampled LLM Eval (AgentLens pattern)

AgentLens (2025) approach: embed all interactions, cluster in embedding space (HDBSCAN), sample 1 representative per cluster for LLM evaluation, apply cluster score to all members.

```python
import hdbscan
import numpy as np

def cluster_sample_eval(embeddings, agent_responses, llm_judge_fn, min_cluster_size=10):
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(embeddings)
    
    cluster_scores = {}
    for cluster_id in set(labels):
        if cluster_id == -1:   # noise → flag for Tier 4
            continue
        cluster_mask = labels == cluster_id
        cluster_embs = embeddings[cluster_mask]
        # Find centroid-nearest member as representative
        centroid = cluster_embs.mean(axis=0)
        dists = np.linalg.norm(cluster_embs - centroid, axis=1)
        rep_idx = np.where(cluster_mask)[0][dists.argmin()]
        # ONE LLM call per cluster
        cluster_scores[cluster_id] = llm_judge_fn(agent_responses[rep_idx])
    
    # Assign cluster score to all members
    scores = np.full(len(embeddings), np.nan)
    for cluster_id, score in cluster_scores.items():
        scores[labels == cluster_id] = score
    return scores
```

**Cost**: O(clusters) LLM calls, typically 10–50× cheaper than per-question eval.

### Tier 4 — Reference-Free Heuristics (0 LLM calls, process metrics)

| Metric | Measures | Threshold (cs-agent) |
|--------|----------|---------------------|
| Tool call success rate | Did agent invoke tool correctly? | >85% |
| Escalation rate | Did agent say "I don't know"? | <15% |
| Response time P95 | Latency | <3s |
| Format compliance | JSON/markdown valid? | >99% |

Zero LLM cost, but measures process not quality. Use as circuit-breaker alerts only.

## Recommended Daily Pipeline (Seekapa)

```
Daily (Azure Function, ~$5/day):
  1. Batch-embed all agent interactions via text-embedding-3-large
  2. Classify coverage (Tier 1: covered / uncovered)
  3. Interpolate scores for covered queries (Tier 2)
  4. Compute CWS per agent → push to Langfuse
  5. Flag uncovered queries → add to GD expansion backlog

Weekly (~$20/week):
  6. Cluster uncovered queries (HDBSCAN)
  7. Sample 1 per cluster → LLM evaluation (Tier 3) → expand GD
  8. Recompute Lipschitz constant on updated GD
  9. PaCMAP visualization → white gap report

Monthly:
  10. Full calibration: compare interpolated vs actual LLM scores (holdout 200Q)
  11. Update COVERAGE_RADIUS and LIPSCHITZ_CONST per agent
  12. Publish CWS trend to Nes/Liron (Langfuse dashboard)
```

## Calibration

### Reliability Diagram (Calibration Check)

```python
from sklearn.calibration import calibration_curve
import plotly.graph_objects as go

fraction_pos, mean_pred = calibration_curve(
    y_true=(actual_llm_scores > 0.7).astype(int),
    y_prob=interpolated_scores,
    n_bins=10,
)
fig = go.Figure()
fig.add_scatter(x=[0,1], y=[0,1], mode="lines", name="Perfect calibration")
fig.add_scatter(x=mean_pred, y=fraction_pos, mode="lines+markers", name="Model")
fig.update_layout(title="Interpolation Calibration", xaxis_title="Predicted", yaxis_title="Actual")
```

### Mondrian CP for Conditional Uncertainty

Wrap interpolated scores in conformal prediction intervals, grouped by semantic cluster:

```python
# Group = semantic cluster of the question (from HDBSCAN labels)
# Gives: "For billing questions, score ∈ [0.65, 0.85] at 90% confidence"
# Use MAPIE v0.9 MondrianCP with groups=cluster_labels
```

## Sources

- KDD 2025 Tutorial: Evaluation and Benchmarking of LLM Agents. arXiv:2507.21504.
- AgentLens (2025): Behavior Analysis for LLM Agents via Embedding Trajectory. ICLR 2026 Workshop.
- Confident AI (2025): Golden Dataset evaluation standards. confident-ai.com
- GD Coverage Metric (2026): see 02-coverage-metrics.md
