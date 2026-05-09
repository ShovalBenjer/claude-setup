# Synthesis, Limitations & Methodology

## Patterns Identified

**Pattern 1: The Analytics Democratization Gap**

Professional clubs access StatsBomb Pro, Opta Analytics, and custom ML ($50K-$500K/year). Consumer apps deliver ~5% of available analytical depth. Academic papers publish techniques 2-5 years before any consumer product implements them. TacticAI was in Nature Communications in 2024 [7]; no consumer app offers corner kick analysis in 2026.

**Pattern 2: Data Abundance, Intelligence Scarcity**

Raw data exists across Apify actors, soccerdata, StatsBomb open data, and reverse-engineered APIs. A comprehensive dataset is buildable for near-zero cost. The gap isn't data -- it's the intelligence layer. Every consumer app shows the same Opta xG number. Differentiation comes from running your own models that produce metrics nobody else shows.

**Pattern 3: GNNs Are the Breakthrough Architecture**

Graph neural networks naturally model football's relational structure: players as nodes, interactions as edges, formations as subgraphs. TacticAI [7], HIGFormer [8], passing network analysis [28], counterattack prediction [29] all use GNN variants. Football's tactical complexity is fundamentally a graph problem.

## Novel Insights

**Insight 1: The "Second Screen" Opportunity**

No consumer app provides real-time tactical intelligence during live matches. A product showing "momentum shifted -- Team A's win probability dropped from 72% to 58% in last 5 minutes due to declining midfield control" transforms the viewing experience. Sports broadcasters pursued this with basic graphics but never with ML-powered insights.

**Insight 2: Fantasy Football as Distribution Channel**

FPL has 10M+ active players obsessing over player selection. A platform surfacing "Player X is undervalued by FPL pricing -- xG+ is 30% higher than cost implies" or "Player Y's injury risk is elevated" acquires users through the fantasy community before expanding to general fans.

**Insight 3: The Entain/Betting Angle**

365Scores was acquired by Entain (gambling) for $160M. The football analytics consumer market is deeply intertwined with betting. Features like referee profiling, momentum scoring, and win probability have direct betting-adjacent value. This is both an opportunity (large paying audience) and a risk (regulatory scrutiny).

## Limitations & Caveats

### Counterevidence

**Match prediction accuracy is modest.** HIGFormer achieves 52.19% on 3-class outcomes [8]; draw prediction is 24.53%. Presenting predictions as a key feature could undermine trust. **Mitigation:** Frame as probabilities and process insights, not binary outcomes.

**GPS/tracking data availability is limited.** Features like fatigue detection and formation recognition require tracking data available only for top leagues. FotMob's physical stats are PL only [19]. **Mitigation:** Phase 1 features should work with event data (widely available). Tracking-dependent features are Phase 3+.

### Known Gaps

- **365Scores API structure:** No public documentation. Reverse-engineering may reveal rate limits or auth that change feasibility.
- **Real-time inference latency:** Actual GNN inference benchmarks on match events not found in literature.
- **Legal and licensing:** Scraping ToS and commercial data redistribution rights not deeply investigated.

### Areas of Uncertainty

- **Data quality variance:** Sources report conflicting event data (different xG, event classifications). Normalization layer must handle this.
- **Model generalization:** StatsBomb open data overrepresents La Liga and NWSL. Models may not generalize to different playing styles.
- **Consumer willingness to pay:** No user research validates demand for these specific features.

---

## Methodology

### Research Process

| Phase | Activity |
|-------|---------|
| SCOPE | Decomposed into 5 vectors: data, consumer landscape, ML/DL, gap analysis, architecture |
| PLAN | 5 prioritized research paths with parallel execution strategy |
| RETRIEVE | 15+ parallel web searches + 3 deep-dive background agents + 6 page fetches |
| TRIANGULATE | Cross-referenced across sources. Verified no 365Scores actor (multiple angles). Confirmed ML maturity via citations. |
| OUTLINE REFINEMENT | Added GNN emphasis after finding 4 independent papers. Added 365Scores Entain/Opta details from agents. |
| SYNTHESIZE | Connected data + ML + gaps into 6 novel feature proposals with feasibility ratings |

### Sources Consulted

**Total:** 42+ sources

| Type | Count |
|------|-------|
| Academic journals (Nature, Springer, PLOS, IEEE, CVPR, arXiv) | 18 |
| Industry/product (Apify, Stats Perform, Google Cloud) | 10 |
| GitHub repositories | 5 |
| Consumer apps/review sites | 5 |
| News/blogs | 4+ |

**Temporal coverage:** 2018-2026, 70% from 2024-2026.

### Claims-Evidence Table

| Claim | Sources | Confidence |
|-------|---------|:----------:|
| No 365Scores Apify actor exists | [1], [13], [14], Apify agent | High |
| Consumer apps lack predictive features | [4], [5], [6], [19] | High |
| TacticAI preferred 90% over human tactics | [7] (Nature peer-reviewed) | High |
| GNNs model football's relational structure | [7], [8], [28], [29] | High |
| Injury prediction AUPRC 0.759 | [9], [33], [35] | Medium-High |
| 365Scores has 40M users, Opta data | [11], [12], [S1] | High |
| Set pieces = 20-26% of goals | [40] | Medium |
| 365Scores API at webws.365scores.com | LanusStats lib, agent research | Medium |
| Apify scraping costs $40-65/mo for 5 leagues | Apify pricing agent | Medium |
