# SOTA Cross-Validation (2026)

## Decision Tree

```
Is data IID (tabular, no temporal leakage)?
├─ YES → Nested Cross-Validation
│         Inner k=5 (HPO), Outer k=10 (generalization estimate)
└─ NO → Temporal?
         ├─ Simple horizon, no label overlap → Walk-Forward (TimeSeriesSplit)
         │   Problem: one backtest path, high variance, not SOTA alone
         ├─ Overlapping labels, financial ML → Purged K-Fold
         │   Purge samples within embargo window of test set
         └─ Need backtest distribution → CPCV (SOTA)
```

## Combinatorial Purged CV (CPCV)

**Why CPCV beats Walk-Forward**: Walk-forward = 1 backtest path. CPCV = C(N,k) unique test paths, giving a *distribution* over Sharpe/AUC — essential to detect overfitting to a single historical regime.

```python
from mlfinlab.cross_validation import CombinatorialPurgedCV

cv = CombinatorialPurgedCV(
    n_splits=6,        # N groups to divide time-series into
    n_test_splits=2,   # k test groups per combo → C(6,2) = 15 paths
    purge_pct=0.01,    # % observations purged around test boundary
    embargo_pct=0.005, # % embargo after test to prevent leakage
)

for train_idx, test_idx in cv.split(X, y, groups=t1):  # t1 = label end time
    model.fit(X[train_idx], y[train_idx])
    score = model.score(X[test_idx], y[test_idx])
```

**2024–2025 advances**:
- **Bagged CPCV**: Average predictions (not just metrics) across all C(N,k) paths. ~30% variance reduction vs single-path OOB [de Prado 2024].
- **Adaptive CPCV**: Dynamically adjusts purge_pct based on autocorrelation of labels. Critical when FTD windows vary (3-day vs 30-day conversion).

**Practical trigger**: If test AUC varies >0.05 across walk-forward folds → switch to CPCV.

**License note**: mlfinlab full features require Hudson & Thames commercial license. OSS alternative: implement manually from de Prado (2018) Ch. 12 pseudocode.

## Mondrian Conformal Prediction

**What it gives**: Conditional coverage guarantee per group. Not average performance — group-conditional: "For Campaign advertisers, prediction interval contains true value with ≥90% probability."

**Library status 2026**:
- MAPIE v0.9: `MondrianCP` available — **use this version**
- MAPIE v1.x: `MondrianCP` **removed** pending redesign. Use manual workaround.

```python
# Pin to v0.9 in pyproject.toml: "mapie==0.9.0"
from mapie.mondrian import MondrianCP

mondrian = MondrianCP(
    estimator=your_model,
    cv="prefit",
    groups=X["segment"],   # e.g. advertiser vs publisher
    alpha=0.1,             # 90% coverage
)
mondrian.fit(X_cal, y_cal)
y_pred, y_intervals = mondrian.predict(X_test, groups=X_test["segment"])
# y_intervals shape: (n, 2) — [lower, upper] per sample
```

**MAPIE v1 workaround** (if pinning is blocked):
```python
from mapie.regression import MapieRegressor
from sklearn.base import clone

# Manual Mondrian: separate MapieRegressor per group
models = {}
for group in X_cal["segment"].unique():
    mask = X_cal["segment"] == group
    mapie = MapieRegressor(estimator=clone(base_model), cv="prefit")
    mapie.fit(X_cal[mask], y_cal[mask])
    models[group] = mapie
```

**2025 papers**:
- **LWT-MCPS** (2025): Mondrian CP for heteroscedastic tabular — locally-weighted calibration per variance stratum
- **CPTC** (2025): CP for time-series with change-point detection — recalibrates on regime shift

## Full Toolkit Summary

| Scenario | Method | Library | Key params |
|----------|--------|---------|-----------|
| Tabular IID | Nested CV | sklearn | outer k=10, inner k=5 |
| Time-series simple | Walk-Forward | sklearn `TimeSeriesSplit` | gap=h |
| Financial / overlapping labels | Purged K-Fold | mlfinlab | purge=0.01, embargo=0.005 |
| Backtest distribution | **CPCV** | mlfinlab | n_splits=6, n_test_splits=2 |
| Conditional coverage | **Mondrian CP** | MAPIE v0.9 | groups=segment, alpha=0.1 |
| Any → intervals | Standard CP | MAPIE v1 | cv="prefit", alpha=0.1 |

## Sources

- de Prado, M. L. (2018). *Advances in Financial Machine Learning*. Wiley. Ch. 7, 12.
- MLFinLab Docs (2026): https://www.mlfinlab.com/en/latest/cross_validation/cpcv.html
- MAPIE v1 Release Notes (2025): scikit-learn-contrib/MAPIE GitHub
- LWT-MCPS paper (2025) — locally-weighted Mondrian conformal scores
