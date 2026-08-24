# Recommendations & Bibliography

## Prioritized Actions

### Priority 1 — This Week

| Action | File | Command |
|--------|------|---------|
| CPCV in campaign-analysis FTD models | `evals/run_eval.py` | Replace walk-forward with `CombinatorialPurgedCV` |
| Pin MAPIE v0.9 | `pyproject.toml` | `"mapie==0.9.0"` in dev group |
| Add PaCMAP | `pyproject.toml` | `"pacmap>=0.7"`, `"hdbscan>=0.8"` |
| Update `/notebook` skill | `~/.claude/skills/notebook/SKILL.md` | Add cells 5b, 9b, 9c from `05-notebook-updates.md` |
| Wire INDEX.md into commit flow | `~/.claude/skills/commit-push-pr/SKILL.md` | Add `generate-index.sh <changed_project_dir>` to pre-ship |

### Priority 2 — Next Sprint

| Action | Owner | Notes |
|--------|-------|-------|
| GD Coverage Metric Phase 1–4 for cs-agent | Shoval | Embed GD questions, classify coverage, compute CWS |
| Wire LANGFUSE_* to Azure KV | Shoval | Secrets: `LANGFUSE-PUBLIC-KEY`, `LANGFUSE-SECRET-KEY`, `LANGFUSE-HOST` → kv-seekapa-apps |
| Add LANGFUSE_* to campaign-analysis-secrets DevOps variable group | Shoval | Then campaign-analysis CI eval gate is fully wired |
| Scope injection in all Agent() spawns | Shoval | Add files-to-touch + out-of-scope to every subagent prompt |

### Priority 3 — Medium Term

| Action | Notes |
|--------|-------|
| Centralized MCP server on ACA | Windsor + OneSignal + Call-Analyser → one remote endpoint. Both Foundry agents (MCPTool) and Claude Code users connect. |
| Automated CWS tracking | Weekly Azure Function: embed → classify → push to Langfuse → alert if CWS drops >5% |
| Calibrate Lipschitz constant per agent | Collect 200Q holdout, compute L empirically. Recompute quarterly. |
| PaCMAP white-gap visualization | Monthly report to Nes/Liron: which semantic regions have no agent coverage? |

## Limitations and Caveats

1. **GD Coverage Metric Lipschitz constant** (L=0.15) is a starting approximation. Calibrate after 4–6 weeks of data. L varies by domain: billing questions cluster tighter than campaign strategy questions.

2. **mlfinlab CPCV** requires commercial license. OSS fallback: implement manually from de Prado (2018) Ch. 12. The math is straightforward — 20–30 LOC.

3. **MondrianCP in MAPIE v1** is removed. Pin `"mapie==0.9.0"` explicitly. Monitor `scikit-learn-contrib/MAPIE` GitHub for v1.1 release notes.

4. **PaCMAP 2D projection** is for visualization only. Coverage distance computations happen in full 3072-dim space. Never use 2D coords for coverage radius thresholds.

5. **GD Coverage Metric has no peer review**. Treat CWS as a directional metric. Validate against sampled LLM judgments monthly until calibration is established.

6. **Embedding interpolation degrades for white gaps** — queries far from any GD question. Don't interpolate there; flag as "unknown quality" and route to Tier 3 eval.

## Bibliography

1. de Prado, M. L. (2018). *Advances in Financial Machine Learning*. Wiley. [CPCV — Ch. 7, 12]
2. Wang, Y., Huang, H., Rudin, C., & Shaposhnik, Y. (2021). Understanding How Dimension Reduction Tools Work. *JMLR*, 22(201). [PaCMAP benchmark]
3. Gustafsson, L. (2024). UMAP vs PaCMAP: Comparative Study. KTH Royal Institute of Technology. [GitHub: gustafssonlinnea/UMAP-vs-PaCMAP]
4. Barber, R., Candès, E., Ramdas, A., & Tibshirani, R. (2023). Conformal prediction beyond exchangeability. *Annals of Statistics*, 51(2), 816–845.
5. Angelopoulos, A. N., & Bates, S. (2023). Conformal Prediction: A Gentle Introduction. *Foundations and Trends in ML*, 16(4), 494–591.
6. MAPIE Development Team (2025). MAPIE v1.0 Release Notes. scikit-learn-contrib/MAPIE GitHub.
7. MLFinLab Documentation (2026). CombinatorialPurgedCV. Hudson & Thames. https://www.mlfinlab.com/en/latest/cross_validation/cvcv.html
8. KDD 2025 Tutorial. Evaluation and Benchmarking of LLM Agents. arXiv:2507.21504.
9. AgentLens (2025). Behavior Analysis for LLM Agents via Embedding Trajectory Analysis. ICLR 2026 Workshop on Memory and Evaluation.
10. LWT-MCPS (2025). Locally-Weighted Mondrian Conformal Prediction Scores for Heteroscedastic Tabular Data.
11. CPTC (2025). Conformal Prediction for Time-Series with Change-Point Detection.
12. Original author (2026). GD Coverage Metric: Roadmap & WBS [internal architecture presentation — 4 images, March 2026].
13. Anthropic (2026). Claude Code TDD enforcement via hooks. Claude Code documentation.
