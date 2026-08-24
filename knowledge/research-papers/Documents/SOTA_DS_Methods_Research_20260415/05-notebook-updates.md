# /notebook Skill Updates: SOTA 2026

## Changes Required to SKILL.md

Add these cells to the standard notebook structure after Cell 5 (Preprocessing) and in Cell 9 (Evaluation).

---

## New Cell 5b — Cross-Validation Strategy

```python
# Cell 5b — Cross-Validation Strategy
# Auto-detect: temporal data → CPCV; IID → Nested CV

import numpy as np

# --- TEMPORAL DATA (time-series, financial, FTD prediction) ---
# pip install mlfinlab (commercial license required for full features)
# from mlfinlab.cross_validation import CombinatorialPurgedCV
# cv_temporal = CombinatorialPurgedCV(
#     n_splits=6, n_test_splits=2,
#     purge_pct=0.01, embargo_pct=0.005,
# )

# --- TABULAR IID ---
from sklearn.model_selection import KFold, cross_val_score
cv_tabular = KFold(n_splits=10, shuffle=True, random_state=42)
# Nested: inner loop for HPO, outer for generalization estimate

# --- CONFORMAL PREDICTION (all types) ---
# Pin: pip install "mapie==0.9.0"  (v1 removed MondrianCP)
# from mapie.mondrian import MondrianCP
# mondrian = MondrianCP(estimator=model, cv="prefit",
#                       groups=X["segment"], alpha=0.1)
# mondrian.fit(X_cal, y_cal)
# y_pred, y_intervals = mondrian.predict(X_test, groups=X_test["segment"])

print("CV strategy selected based on data type.")
print("Temporal → CPCV (n_splits=6, n_test_splits=2, purge=0.01)")
print("IID tabular → Nested CV (outer k=10, inner k=5)")
```

---

## New Cell 9b — Coverage Visualization (PaCMAP)

```python
# Cell 9b — Coverage Visualization
# Requires: embeddings from text-embedding-3-large (3072-dim) on eval set

# pip install pacmap
from pacmap import PaCMAP
import plotly.express as px
import pandas as pd

# Project evaluation set to 2D
reducer = PaCMAP(n_components=2, n_neighbors=10, random_state=42)
# embeddings_eval: (N, 3072) — embed X_test text via OpenAI before this cell
# X_2d = reducer.fit_transform(embeddings_eval)

# Visualize prediction space colored by predicted class/score
# coverage_df = pd.DataFrame({
#     "x": X_2d[:,0], "y": X_2d[:,1],
#     "label": y_pred.astype(str),
#     "score": y_prob.max(axis=1) if hasattr(y_prob, 'shape') else y_pred,
# })
# fig = px.scatter(coverage_df, x="x", y="y", color="label",
#                  title="Coverage Map: Prediction Space (PaCMAP 3072→2D)",
#                  labels={"x": "Semantic Dim 1", "y": "Semantic Dim 2"})
# fig.show()

print("PaCMAP cell ready. Provide embeddings_eval (N, 3072) to activate.")
```

---

## New Cell 9c — GD Coverage Metric (eval-type notebooks only)

```python
# Cell 9c — GD Coverage Metric
# Use when: notebook type is "eval" and golden dataset exists
# Requires: gd_embeddings (N, 3072), gd_scores (N,), user_embeddings (M, 3072)

from sklearn.metrics.pairwise import cosine_distances
import numpy as np

COVERAGE_RADIUS = 0.25   # cosine distance threshold — calibrate per domain
LIPSCHITZ_CONST = 0.15   # calibrate on validation holdout

def compute_gd_coverage(gd_embeddings, gd_scores, user_embeddings):
    dists = cosine_distances(user_embeddings, gd_embeddings)  # (M, N)
    nearest_dists = dists.min(axis=1)
    nearest_gd_idx = dists.argmin(axis=1)
    coverage_mask = nearest_dists <= COVERAGE_RADIUS
    nearest_scores = gd_scores[nearest_gd_idx]
    score_lb = np.maximum(0.0, nearest_scores - LIPSCHITZ_CONST * nearest_dists)
    gd_score = gd_scores.mean()
    coverage_pct = coverage_mask.mean()
    cws = gd_score * coverage_pct
    return {
        "gd_score": gd_score,
        "coverage_pct": coverage_pct,
        "confidence_weighted_score": cws,
        "score_lower_bounds": score_lb,
        "coverage_mask": coverage_mask,
    }

# --- Usage ---
# result = compute_gd_coverage(gd_embeddings, gd_scores, user_embeddings)
# print(f"GD Score:                  {result['gd_score']:.3f}")
# print(f"Coverage:                  {result['coverage_pct']:.1%}")
# print(f"Confidence-Weighted Score: {result['confidence_weighted_score']:.3f}")
```

---

## Updated Per-Project Defaults Table

| Project | Default type | CV method | GD Coverage |
|---------|-------------|-----------|-------------|
| campaign-analysis | timeseries + tabular | CPCV (FTD temporal labels) | Yes — agent vs user query coverage |
| qc | eval | Nested CV | Yes — GD Coverage Metric |
| cs-agent | eval | Nested CV | Yes — GD Coverage Metric |
| HR-agent | embedding | N/A (clustering) | No |

---

## Updated Dependencies (add to pyproject.toml dev group)

```toml
# Cross-validation
"mapie==0.9.0",          # Mondrian CP (pinned — v1 removed MondrianCP)
# "mlfinlab>=1.0",       # CPCV (commercial license required)

# Coverage visualization
"pacmap>=0.7",           # PaCMAP dimensionality reduction
"hdbscan>=0.8",          # Clustering for Tier 3 eval

# Existing (already in notebook skill)
"polars>=1.0",
"plotly>=5.0",
"great-tables>=0.10",
"autogluon.tabular>=1.1",
"shap>=0.45",
"optuna>=3.6",
"numba>=0.60",
```

---

## Trigger Updates

Add these triggers to notebook SKILL.md trigger list:

```markdown
## Triggers (updated)
- Data files detected in project dir (xlsx, csv, parquet)
- User asks to "analyze", "explore", "EDA", "model" data
- Agent eval result needs statistical analysis
- "scaffold run" requested on a dataset
- User says "coverage metric", "GD coverage", "CWS"  ← NEW
- User says "conformal prediction", "prediction intervals"  ← NEW
- Temporal/financial ML context detected  ← NEW (triggers CPCV cell)
```
