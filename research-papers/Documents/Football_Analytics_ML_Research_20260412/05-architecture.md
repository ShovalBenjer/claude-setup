# Technical Architecture & Recommendations

## Pipeline Architecture

```
DATA ACQUISITION LAYER
+-- Apify Actors (scheduled)
|   +-- FlashScore Scraper (live scores, events, odds) -- 92K runs, battle-tested
|   +-- SofaScore Scraper PRO (match stats, player data)
|   +-- Understat xG Scraper (expected goals, shot maps)
|   +-- Transfermarkt Scraper (market values, transfers)
|   +-- Custom 365Scores Actor (reverse-engineer webws.365scores.com)
|
+-- Python soccerdata Library
|   +-- FBref (advanced stats, passing, shooting, defense)
|   +-- WhoScored (detailed match events, player ratings)
|   +-- Club Elo (team strength ratings)
|   +-- SoFIFA (player attributes)
|
+-- Open Datasets (ML training)
    +-- StatsBomb Open Data (event-level, free, high quality)
    +-- Wyscout (academic access)
    +-- Metrica Sports (3 matches with tracking data)

        |
        v

DATA PROCESSING LAYER
+-- ETL Pipeline (Python)
|   +-- Schema normalization across sources
|   +-- Deduplication (same match from multiple sources)
|   +-- Feature engineering (rolling averages, form metrics)
|   +-- Coordinate standardization (pitch normalization)
|
+-- Storage
    +-- PostgreSQL (structured match/player data)
    +-- Time-series DB (live match events during games)
    +-- Object store (model artifacts, embeddings)

        |
        v

ML/DL LAYER
+-- Offline Training (batch, nightly)
|   +-- xG+ Model (XGBoost + sequence features)
|   +-- Team Chemistry GNN (PyTorch Geometric)
|   +-- Injury Risk Model (Random Forest / XGBoost)
|   +-- Market Value Predictor (XGBoost + NLP embeddings)
|   +-- Referee Profile Builder (statistical + simple ML)
|
+-- Online Inference (real-time during matches)
    +-- Win Probability Model (updates per event)
    +-- Momentum Score (rolling 5-min window)
    +-- Fatigue Estimator (physical stats input)
    +-- Formation Recognizer (if tracking data available)

        |
        v

PRESENTATION LAYER
+-- API (FastAPI / Node.js)
+-- Web App (React / Next.js)
+-- Mobile App (React Native)
+-- Push Notifications (goal alerts + ML insight alerts)
```

## Key Architectural Decisions

1. **Multi-source by design.** Never depend on a single data source. Abstraction layer normalizes from 5+ sources. If one breaks, others fill the gap.

2. **Batch + real-time.** Historical analysis = nightly batch jobs. Live match features = streaming inference triggered by incoming events.

3. **StatsBomb open data for model training.** Free, high-quality, event-level with coordinates. Train/validate here, deploy on scraped data.

4. **Apify webhooks for pipeline orchestration.** `ACTOR.RUN.SUCCEEDED` fires webhook to backend, which pulls dataset and triggers ETL.

## Cost Estimates

| Component | Monthly Cost |
|-----------|-------------|
| Apify Scale tier (incl. credits) | $199 |
| Football scraping (within credits) | $40-65 |
| Residential proxies (~2 GB) | $14-16 |
| PostgreSQL (managed, small) | $15-50 |
| ML inference (CPU, no GPU needed for serving) | $20-50 |
| **Total infrastructure** | **~$100-200/month** |

For heavier operations (all UEFA leagues, historical backfill, match-day real-time): $200-400/month.

## Progressive Feature Rollout

### Phase 1: Weeks 1-4 (Data Pipeline + Quick Wins)

1. **Reverse-engineer 365Scores API.** Browser DevTools + mitmproxy on mobile app. Document endpoints, schemas, auth. (2-3 days)
2. **Deploy Apify pipeline.** FlashScore + Understat actors on daily schedules -> PostgreSQL. (1-2 days)
3. **Explore StatsBomb open data.** `statsbombpy` -> notebooks -> understand schema. (1-2 days)
4. **Build referee profiler.** Simple aggregation from scraped data. Low ML, high user interest. (2-3 days)
5. **Build xG+ model.** XGBoost with sequence features on StatsBomb data. Quickest novel metric. (1-2 weeks)

### Phase 2: Weeks 5-8 (Core ML Features)

1. **Team chemistry GNN prototype.** PyTorch Geometric on StatsBomb passing data. Single league/season. Per-pair chemistry score.
2. **Momentum scoring model.** Rolling-window analysis of event density + xG accumulation + territory. Real-time graph during live matches.
3. **Win probability model.** XGBoost on match state features, update per event.

### Phase 3: Weeks 9-12 (Advanced Features)

1. **Market value anomaly detector.** Transfermarkt values + FBref stats + news NLP sentiment.
2. **Substitution timing engine.** Physical stats + match state -> XGBoost -> prescriptive recommendations.
3. **Player similarity search.** Embedding space from player stats, cosine similarity for scouting.

### Phase 4: Weeks 13+ (Cutting Edge)

1. **Formation recognition.** Requires tracking data. Start with Metrica Sports open data for proof-of-concept.
2. **Set-piece recommender.** Geometric deep learning on corner/FK data.
3. **Counterfactual transfer simulation.** ScoutGPT-style generative model.

## Further Research Needs

1. **Tracking data access.** Investigate Metrica Sports, Second Spectrum for formation and fatigue features.
2. **User research.** Survey football fans on which features they'd pay for. Prioritize by demand, not technical novelty.
3. **Legal review.** ToS compliance and data redistribution rights per source before commercialization.

**Sources:** [1], [2], [3], [7], [17], [18]
