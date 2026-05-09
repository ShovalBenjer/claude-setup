# Manifold Learning & Coverage Metrics (2026)

## PaCMAP: Best for Coverage Visualization

### Benchmark (2024–2025)

| Method | Local structure | Global structure | Speed >10K pts | Stability |
|--------|----------------|-----------------|----------------|-----------|
| t-SNE | Excellent | Poor | Slow | Low (stochastic) |
| UMAP | Good | Moderate | Fast | Moderate |
| **PaCMAP** | **Good** | **Excellent** | **Fast** | **High** |
| TriMAP | Moderate | Good | Moderate | High |

**Source**: Gustafsson/KTH 2024 systematic comparison; Wang et al. JMLR 2021.

**Winner for coverage visualization**: PaCMAP. Preserves between-cluster distances critical for seeing which agents' GD zones overlap or diverge. Deterministic (set `random_state`). No parameter tuning beyond `n_neighbors`.

```python
from pacmap import PaCMAP

reducer = PaCMAP(
    n_components=2,
    n_neighbors=10,    # local neighborhood
    MN_ratio=0.5,      # mid-near pair weight
    FP_ratio=2.0,      # far-pair weight
    random_state=42,   # reproducibility
)
X_2d = reducer.fit_transform(embeddings_3072)  # (N, 3072) → (N, 2)
```

**Rule**: PaCMAP for global topology (coverage zones). t-SNE for local cluster drill-down. UMAP for production monitoring (faster re-embed).

---

## GD Coverage Metric

> Original work by a senior data scientist. Architecture documented here. Not yet published.

### Problem

A Golden Dataset (GD) of N hand-crafted questions evaluates agent quality. Real traffic has M >> N questions, many untested. Standard GD score = quality on tested questions only.

```
GD_score = 0.92    (agent handles test questions well)
Coverage  = 0.73   (only 73% of real traffic falls in GD coverage zones)
CWS       = 0.67   (true expected quality across ALL real traffic)
```

Confidence-Weighted Score (CWS) = GD_score × coverage% is the metric that reflects real-world reliability.

### 8-Phase Pipeline

```
Phase 0: Design Alignment — define domains, agents, evaluation owners
Phase 1: Embedding Pipeline — embed all GD questions + user questions (text-embedding-3-large, 3072-dim)
Phase 2: Coverage Metrics — define coverage_zone per GD question (radius r_i in embedding space)
Phase 3: LLM Agent Score — run standard GD eval → score(q_i) per GD question
Phase 4: Topic Coverage — PaCMAP 2D projection, HDBSCAN cluster labeling
Phase 5: Platform View — scatter plot: all agents' coverage zones, white gaps visible
Phase 6: Score Extrapolation — Lipschitz interpolation for uncovered user questions
Phase 7: Agent Recommendations — per-agent coverage%, uncovered high-traffic questions
Phase 8: Platform Recommendations — white gap analysis → new agent/GD backlog
```

### Coverage Zone Classification

```python
from sklearn.metrics.pairwise import cosine_distances
import numpy as np

COVERAGE_RADIUS = 0.25   # cosine distance threshold (calibrate per domain)

def classify_coverage(user_embeddings, gd_embeddings):
    # user_embeddings: (M, 3072), gd_embeddings: (N, 3072)
    dists = cosine_distances(user_embeddings, gd_embeddings)  # (M, N)
    nearest_dists = dists.min(axis=1)           # (M,)
    coverage_mask = nearest_dists <= COVERAGE_RADIUS
    nearest_gd_idx = dists.argmin(axis=1)       # (M,)
    return coverage_mask, nearest_dists, nearest_gd_idx
```

### Lipschitz Score Extrapolation

**Key insight**: If GD question q_i scores s_i and user question u_j is at embedding distance d, then:

```
score_estimate(u_j) ≥ s_i - L × d(u_j, q_i)
```

where L is the Lipschitz constant (calibrated empirically). This gives a **lower bound** — conservative but theoretically sound.

```python
LIPSCHITZ_CONST = 0.15   # calibrate on validation holdout

def extrapolate_scores(nearest_dists, nearest_gd_idx, gd_scores):
    nearest_scores = gd_scores[nearest_gd_idx]
    score_lb = np.maximum(0.0, nearest_scores - LIPSCHITZ_CONST * nearest_dists)
    return score_lb

# Calibrate L on holdout where you have both interpolated AND actual LLM scores:
def calibrate_lipschitz(val_distances, val_actual_scores, val_gd_scores):
    gd_scores_for_nearest = val_gd_scores[val_distances.argmin(axis=1)]
    score_diffs = np.abs(val_actual_scores - gd_scores_for_nearest)
    nearest_dists = val_distances.min(axis=1)
    L = np.max(score_diffs / (nearest_dists + 1e-8))
    return L * 1.1   # 10% safety margin
```

### CWS Computation

```python
def compute_cws(gd_scores, coverage_mask):
    gd_score = gd_scores.mean()
    coverage_pct = coverage_mask.mean()
    cws = gd_score * coverage_pct
    print(f"GD Score:                  {gd_score:.3f}")
    print(f"Coverage:                  {coverage_pct:.1%}")
    print(f"Confidence-Weighted Score: {cws:.3f}")
    return cws
```

### Platform-Wide Visualization (replicating the diagram)

```python
import plotly.express as px
import pandas as pd

def plot_platform_coverage(gd_2d, user_2d, gd_agents, gd_scores, coverage_mask):
    user_df = pd.DataFrame({
        "x": user_2d[:,0], "y": user_2d[:,1],
        "status": ["Covered" if c else "Uncovered" for c in coverage_mask],
    })
    fig = px.scatter(user_df, x="x", y="y", color="status",
                     color_discrete_map={"Covered": "#2ecc71", "Uncovered": "#e74c3c"},
                     title="Platform-Wide Coverage View (3072-dim → 2D via PaCMAP)")

    for agent in set(gd_agents):
        mask = [a == agent for a in gd_agents]
        fig.add_scatter(
            x=gd_2d[mask,0], y=gd_2d[mask,1],
            mode="markers", marker_symbol="star", marker_size=14,
            name=f"GD: {agent}",
        )
    fig.update_layout(
        xaxis_title="Semantic Dimension 1",
        yaxis_title="Semantic Dimension 2",
    )
    return fig
```

**White gaps** (regions where no agent has GD coverage) are visible as uncovered red clusters far from any star. These drive the Phase 8 platform backlog: which new agents or GD questions to create.

### Calibration Notes

- `COVERAGE_RADIUS = 0.25` is a starting point. Validate: for a holdout of questions with known coverage/non-coverage, tune threshold to maximize F1 of coverage classification.
- Lipschitz constant must be per-domain (billing vs campaign questions have different smoothness).
- Recompute monthly as GD expands.

## Sources

- Wang, Y. et al. (2021). Understanding PaCMAP. JMLR 22(201).
- Gustafsson, L. (2024). UMAP vs PaCMAP Systematic Study. KTH.
- Original author (2026). GD Coverage Metric — Roadmap & WBS [internal presentation].
- Angelopoulos & Bates (2023). Conformal Prediction: A Gentle Introduction. FnTML 16(4).
