# SOTA 2026: DS Methods Research — Index

**Date:** 2026-04-15 | **Scope:** Cross-validation, Coverage Metrics, LLM Eval, AI Engineering

## Modules

| File | Topic |
|------|-------|
| [01-cross-validation.md](01-cross-validation.md) | Nested CV, Purged K-Fold, CPCV, Mondrian Conformal Prediction |
| [02-coverage-metrics.md](02-coverage-metrics.md) | PaCMAP vs UMAP, GD Coverage Metric (brother's work), Lipschitz extrapolation |
| [03-llm-agent-eval.md](03-llm-agent-eval.md) | Scalable eval without per-question LLM calls, embedding interpolation, calibration |
| [04-engineering-workflow.md](04-engineering-workflow.md) | TDD with AI agents, orchestration patterns, prompt engineering reliability |
| [05-notebook-updates.md](05-notebook-updates.md) | Concrete code cells to add to /notebook SKILL.md |
| [06-recommendations.md](06-recommendations.md) | Prioritized actions + bibliography |

## Executive Summary

**Cross-validation**: CPCV (Combinatorial Purged CV) is mandatory for any temporal/financial ML. Walk-forward alone is insufficient — it produces one backtest path, not a distribution. Mondrian CP gives conditional coverage guarantees; use MAPIE v0.9 (MondrianCP removed from v1 pending redesign).

**Coverage metrics**: The GD Coverage Metric (original work by a senior DS, not published) solves scalable agent eval via embedding topology + Lipschitz extrapolation + confidence-weighted scoring. PaCMAP beats UMAP for global structure visualization of high-dimensional embeddings (>10K points, 3072-dim).

**Scalable LLM eval**: No consensus published method. Tier 1: Lipschitz extrapolation (no LLM calls, lower bounds). Tier 2: weighted cosine interpolation (point estimates). Tier 3: cluster-sampled LLM eval (AgentLens pattern). Use Mondrian CP for conditional uncertainty.

**AI-assisted engineering**: Hook-enforced TDD cuts defect rates 40–60%. Codex dual-agent (Claude orchestrates, Codex executes in worktree) is the most reliable pattern for this setup. Scope injection at spawn reduces drift from ~40% to ~8% of tasks.

## Priority Actions

1. **This week**: CPCV in campaign-analysis FTD models. MAPIE v0.9 in pyproject.toml. Update `/notebook` skill.
2. **Next sprint**: GD Coverage Metric Phase 1–4 for cs-agent. Wire LANGFUSE_* to Azure KV.
3. **Medium term**: Centralized MCP on ACA. Automated CWS tracking via weekly Azure Function.
