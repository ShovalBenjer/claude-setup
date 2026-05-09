# ML/DL Techniques Ready for Football Analytics Productization

## Established Techniques (Productized Elsewhere)

### Enhanced Expected Goals (xG+)

Traditional xG uses ~20 variables (shot distance, angle, body part, pressure) [22]. Recent advances:

| Approach | Key Innovation | Paper/Source |
|----------|---------------|-------------|
| Sequence-based xG | Events in 10s pre-shot window; "advancement factor" feature | [23] |
| Bayesian xG | 7-variable mixed-effects model matches StatsBomb accuracy | [24] |
| Skor-xG | Player skeleton/posture from video (CVPR 2025) | [25] |
| Player-adjusted xG | Incorporates player ability + psychological effects | [26] |
| xS (Expected Shots) | Models shot *creation* probability, not just conversion | arXiv 2512.00203 |

### Action Valuation: VAEP and xT

- **VAEP** (Valuing Actions by Estimating Probabilities): Values each action as change in goal probability over next 10 actions. Favors shooting.
- **xT** (Expected Threat): Location-only Markov chain model. More correlated with playmaking.
- **Library:** `socceraction` (KU Leuven) -- converts event streams to SPADL format, implements both.

### Expected Possession Value (EPV)

- Decomposes possession into subcomponents (passes, drives, shots) using pitch control.
- **OJN-EPV** (2025): U-Net CNN with ball height feature and dual-component pass value (reward + risk).

### Match Outcome Prediction

| Model | Accuracy | Key Innovation | Source |
|-------|----------|---------------|--------|
| HIGFormer (KDD 2025) | 52.19% (3-class) | Heterogeneous player-team graph transformer | [8] |
| CNN-Transformer hybrid | 86.7% (specific setup) | 1D CNN + Transformer attention | [30] |
| LLM-based prediction | Novel | Numerical features as contextual text | [31] |
| Large Events Model (LEM) | N/A (generative) | Simulates full matches from game state | [32] |

---

## Emerging Techniques (Strong Research, Limited Products)

### Foundation Models for Soccer

**This is the most significant emerging direction.**

| Model | Architecture | Key Capability | Paper |
|-------|-------------|----------------|-------|
| **LEM** (Large Events Model) | Tabular autoregressive MLP | Full match simulation, xP+ metric | [32] |
| **SoccerTransformer** | Transformer + self-supervised pre-training | Event classification, player ratings (F1: 0.814-0.862) | Springer 2025 |
| **ScoutGPT** | NanoGPT on event tokens | **Counterfactual player valuation** ("what if Player X joins Team Y?") | arXiv 2603.15212 |
| **Foundation Model for Soccer** | Transformer, 3 seasons training | Next-action prediction | arXiv 2407.14558 |

### Graph Neural Networks for Tactical Analysis

| System | Application | Key Result | Source |
|--------|------------|------------|--------|
| **TacticAI** (DeepMind + Liverpool) | Corner kick optimization | Preferred over human tactics 90% of time | [7] |
| **HDS-SGT** | Dynamic formation recognition | Dual-stream graph + temporal transformer | [27] |
| Counterattack GNN | Predicting successful counterattacks | Gender-specific binary classifiers | [29] |
| Passing network GCN | Player influence scoring | Nodes = players, edges = passes | [28] |

GNNs are the breakthrough architecture for football -- the sport's relational structure (players, interactions, formations) is fundamentally a graph problem. 4 independent papers confirm this.

### Player Embeddings and Representation Learning

- **NLP-inspired:** Word2Vec on event sequences (actions as "words", possessions as "sentences")
- **GCN-generated:** Node embeddings from player-similarity graphs for transfer recommendations
- **Spatial similarity index:** Novel spatial data analysis for player scouting

---

## Novel / Underexplored Areas (Academic Only, Not Productized)

### White Space Analysis

| Capability | Research? | Productized? | Difficulty |
|-----------|:---------:|:------------:|:----------:|
| Counterfactual player valuation ("what if?") | Yes (ScoutGPT) | No | Hard |
| Pressing intensity per player/team | Yes (2025) | No | Medium |
| Off-ball defensive contribution ratings | Yes (2025) | No | Medium |
| Team chemistry quantification | Partial | No | Hard |
| Set piece optimization (beyond corners) | Partial | No | Medium |
| Referee bias / consistency scoring | Yes (causal) | No | Medium |
| Fatigue risk per player per fixture | Yes (GPS models) | No | Hard (data) |
| Match simulation / what-if scenarios | Yes (LEM, ScoutGPT) | No | Hard |
| Natural language tactical explanations | Yes (MLLM + RAG) | No | Medium |
| Future player value forecasting | Yes (2025) | Partial | Medium |
| Diffusion-generated tactical scenarios | Early (SMGDiff) | No | Very Hard |

### Injury Prediction

- Ensemble ML achieves AUPRC 0.759 vs baseline 0.589 [9]
- Strength asymmetry contributes 18.4% to model performance [33]
- GPS + psychological data (RPE, pleasure, satisfaction) are strongest predictors [34]
- 4-year longitudinal study validates muscle injury risk prediction [35]
- Decision-theoretic framework combines risk predictions with squad selection [medRxiv 2025]

### Player Market Value

- XGBoost + random forest achieve highest accuracy [36]
- NLP features from news (sentiment, semantic embeddings) improve undervalued player detection [37]
- Defensive performance valuation addresses blind spot in traditional metrics [38]

---

## Key Tools and Libraries

| Tool | Purpose | URL |
|------|---------|-----|
| `kloppy` | Vendor-independent data model | kloppy.pysport.org |
| `socceraction` | VAEP + xT from event streams | github.com/ML-KULeuven/socceraction |
| `databallpy` | Synchronized tracking + event | PyPI |
| `OpenSTARLab` | Full framework: preprocessing, RL | github.com/open-starlab |
| `statsbombpy` | StatsBomb data client | PyPI |

## Curated Resource Lists

- [awesome-soccer-analytics](https://github.com/matiasmascioto/awesome-soccer-analytics)
- [awesome-machine-learning-on-soccer](https://github.com/MLonSoccer/awesome-machine-learning-on-soccer)
- [Edd Webster's football_analytics](https://github.com/eddwebster/football_analytics)

**Sources:** [7], [8], [9], [21]-[38]
