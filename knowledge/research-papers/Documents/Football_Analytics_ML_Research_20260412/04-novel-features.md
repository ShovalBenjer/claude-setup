# Six Novel Features That No Consumer App Delivers

## Feature Priority Matrix

| # | Feature | Data Needed | Difficulty | Differentiation | Phase |
|---|---------|-------------|:----------:|:---------------:|:-----:|
| 1 | Live Tactical Formation Recognition | Tracking/inferred coordinates | High | Very High | 4 |
| 2 | Real-Time Team Chemistry Score | Pass events with sender/receiver | Medium | Very High | 2 |
| 3 | Optimal Substitution Timing Engine | Physical stats + match events | Medium-High | High | 3 |
| 4 | Set-Piece Strategy Recommender | Set piece events + coordinates | High | Very High | 4 |
| 5 | Referee Tendency Profiler | Match events + referee name | Low-Medium | Medium | 1 |
| 6 | Player Market Value Anomaly Detector | Stats + values + news sentiment | Medium | Medium-High | 3 |

---

## Feature 1: Live Tactical Formation Heat Map with AI Recognition

Using the HDS-SGT architecture [27] or simplified version trained on StatsBomb open data (which includes player coordinates), display real-time formation shifts. Show when a 4-3-3 collapses into 4-5-1 under pressure, or transitions to 3-4-3 in attack.

No consumer app does this -- they show static pre-match formations only.

**Data:** Player position coordinates (tracking data or inferred from events).
**Architecture:** Dual-stream graph transformer (spatiotemporal graph attention + temporal transformer).
**Why hard:** Requires tracking data or strong inference from event sequences. Available for top leagues only.

---

## Feature 2: Real-Time Team Chemistry Score

Quantify how well specific player combinations work together using passing network GNN. Edges represent successful interactions (completed passes, 1-2 combinations, overlapping runs leading to chances). Output a "chemistry index" per pair and per team formation.

Research confirms team chemistry is underexplored quantitatively [39]. Chemistry is more predictive of team success than individual past performance (VAEP-based studies).

**Data:** Pass events with sender/receiver, spatial coordinates.
**Architecture:** PyTorch Geometric GNN. Shannon entropy of player-to-player interactions as proxy for tactical fluidity.
**Novel twist:** Show "chemistry delta" when a substitution happens -- did the sub improve or hurt team connectivity?

---

## Feature 3: Optimal Substitution Timing Engine

Combine fatigue detection (acceleration-speed profile decline) [10] with match state (score, time, momentum). Train XGBoost on historical substitution data + match outcomes.

Surface to users: "Player X's sprint frequency has dropped 30% since minute 60 -- teams that substitute at this point win 15% more often."

**Data:** Physical stats (distance, sprints, speed) + match events + substitution timing + outcomes.
**Why newly feasible:** FotMob started showing physical data for PL in 2025 [19].
**Bonus:** Combine with injury prediction model -- "Player Y's fatigue pattern matches pre-injury profiles from 4-year longitudinal data" [35].

---

## Feature 4: Set-Piece Strategy Recommender

Adapt TacticAI's geometric deep learning approach [7] beyond corners to free kicks and throw-ins. Set pieces account for 20-26% of all goals [40], yet no consumer app analyzes them.

Show users: which corner delivery type (inswinger vs outswinger vs short), which target zone, and which attacking runners produce the highest xG for Team A against Team B's defensive setup.

**Data:** Set piece events with coordinates, outcomes, player positions.
**Architecture:** Geometric deep learning, message-passing GNN (TacticAI pattern).
**Why high-impact:** Google DeepMind proved this works (90% preference) but didn't productize it for consumers.

---

## Feature 5: Referee Tendency Profiler

Build profiles per referee: cards/90, penalty award rate, home/away bias index, foul threshold, VAR override rate. Research shows referee bias persists even with VAR [41][42].

Pre-match display: "Tonight's referee averages 4.2 yellow cards/game, awards penalties 40% more than league average, has a 12% home team bias."

**Data:** Match events tagged with referee name, cards, fouls, penalties, outcomes.
**Why easy:** Straightforward aggregation + simple ML for bias detection. Can be built in days.
**Why valuable:** Directly useful for betting-adjacent audience (365Scores' Entain ownership validates this market).

---

## Feature 6: Player Market Value Anomaly Detector

Compare on-field performance (xG, xA, progressive passes, defensive actions) against Transfermarkt market value using ML [36][37]. Flag "undervalued" (strong performance, low value) and "overvalued" players. Add NLP sentiment from news for additional signal.

Fantasy football meets Moneyball.

**Data:** Player stats (FBref/Understat) + market values (Transfermarkt) + news sentiment.
**Distribution angle:** Fantasy football community (FPL has 10M+ players). Surface "Player X is undervalued by FPL pricing -- xG+ is 30% higher than cost implies."

---

## Additional Features from Research (Tier 2)

| Feature | Source | Notes |
|---------|--------|-------|
| Live win probability graph | Sportradar Momentum Widget exists but no consumer app integrates ML version | Quick win with XGBoost on match state |
| Pressing intensity heatmap | arXiv 2501.04712 (2025) | Spearman pitch control + logistic transform |
| Off-ball defensive ratings | arXiv 2601.00748 (2025) | Space denial, lane blocking, cover-shadowing |
| Counterfactual transfer sim | ScoutGPT (arXiv 2603.15212) | "What if Mbappe joined Arsenal?" |
| Natural language match insights | MLLM + RAG (WACV 2025) | Auto-generate tactical commentary |
| Momentum + pressure index | InPlayGuru model | Shot pressure, chance quality, territory patterns |

**Sources:** [7], [10], [19], [27], [35], [36], [37], [39], [40], [41], [42]
