# Football Analytics with Apify + 365Scores + ML/DL: Novel Features & Architecture

**Research Date:** 2026-04-12 | **Mode:** Standard | **Sources:** 42+ | **Word Count:** ~7,500 across modules

## Executive Summary

- **Data Layer Gap:** No dedicated Apify actor exists for 365Scores. The 365Scores API is undocumented publicly but reverse-engineerable -- known base URL: `https://webws.365scores.com/web/`. Mature Apify actors exist for FlashScore (92K runs), SofaScore (4K runs), Understat, and Transfermarkt. The `soccerdata` Python library covers 8 additional sources with unified DataFrames.

- **Consumer App Ceiling:** 365Scores, FotMob, and SofaScore provide live scores, basic xG, player ratings, and recently physical stats. None offer predictive analytics, tactical pattern recognition, fatigue modeling, team chemistry quantification, referee bias detection, or set-piece optimization.

- **ML/DL Opportunity:** Academic research has produced production-ready techniques no consumer app implements: GNNs for passing network analysis (TacticAI, 90% preferred over human tactics), transformer-based match prediction (HIGFormer), injury prediction from GPS+psychological data (AUPRC 0.759), and foundation event models (LEM, SoccerTransformer).

- **Novel Feature Set:** 6 features no consumer app offers: (1) live tactical formation recognition, (2) real-time team chemistry scoring, (3) optimal substitution timing, (4) set-piece strategy recommendations, (5) referee tendency profiling, (6) player market value anomaly detection.

**Primary Recommendation:** Build data pipeline using Apify (FlashScore + SofaScore actors) + soccerdata (FBref + Understat) + StatsBomb open data, then layer ML models. Start with xG+ and live momentum scoring as quickest differentiation path.

**Confidence Level:** Medium-High.

## Report Modules

| Module | File | Content |
|--------|------|---------|
| Data Layer | [01-data-layer.md](01-data-layer.md) | 365Scores API, Apify actors, soccerdata, scraping costs |
| Consumer Gaps | [02-consumer-gaps.md](02-consumer-gaps.md) | What 365Scores/FotMob/SofaScore offer vs. don't |
| ML/DL Techniques | [03-ml-techniques.md](03-ml-techniques.md) | SOTA: xG+, GNNs, transformers, injury prediction |
| Novel Features | [04-novel-features.md](04-novel-features.md) | 6 features nobody has built + white space analysis |
| Architecture | [05-architecture.md](05-architecture.md) | Pipeline design, cost estimates, recommendations |
| Synthesis | [06-synthesis.md](06-synthesis.md) | Patterns, insights, limitations, methodology |
| Bibliography | [07-bibliography.md](07-bibliography.md) | All 42 citations |
