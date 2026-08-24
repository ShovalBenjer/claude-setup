# Consumer App Gap Analysis

## Finding 3: Consumer Football Apps Have Hit a Feature Ceiling

### What All Major Apps Offer (converging feature set)

| Feature | 365Scores | FotMob | SofaScore | FlashScore |
|---------|-----------|--------|-----------|------------|
| Live scores + event timeline | Y | Y | Y | Y |
| Basic stats (possession, shots, corners) | Y | Y | Y | Y |
| League tables + fixtures | Y | Y | Y | Y |
| xG (Expected Goals) | Y (xG + xGOT) | Y (xG timelines) | Y | N |
| Shot maps | Y | Y | Y | N |
| Player heatmaps | Y | N (confirmed) | Y (player + team) | N |
| Player ratings | ? | Y (0-10) | Y (3-10, proprietary) | N |
| Physical stats (distance, speed) | N | Y (PL only, 2025) | Y (PL only) | N |
| Live match animation | Y (Match Tracker) | N | Y | N |
| Betting odds | Y (Entain) | N | Limited | Y (comparison) |

**Data source:** 365Scores = Opta (5yr deal). FotMob = Opta. SofaScore = Opta + proprietary. FlashScore = proprietary feeds [S1][20].

### Rating System Differences

SofaScore uses 4 positional classifications, FotMob uses 13, WhoScored uses 16+. These systems capture different aspects and are not interchangeable [20].

### What NONE of Them Offer

1. **Predictive analytics** -- win probability evolution during match
2. **Tactical formation recognition** -- real-time or post-match dynamic shifts
3. **Player fatigue / performance decline tracking** -- sprint frequency decay
4. **Team chemistry / synergy metrics** -- how well player pairs work together
5. **Referee tendency profiles** -- cards/90, penalty rate, home bias index
6. **Set-piece optimization insights** -- corner/FK strategy analysis
7. **Player similarity search** -- find comparable players for scouting
8. **Enhanced xG (xG+)** -- using shot sequence context, not just shot position
9. **Passing network visualization** -- with influence scoring per node
10. **Injury risk indicators** -- based on workload, fixture congestion
11. **Counterfactual analysis** -- "what if we sign Player X?"
12. **Pressing intensity metrics** -- off-ball defensive contribution
13. **Match simulation / what-if scenarios** -- LEM-style game state simulation

### The Democratization Gap

Professional clubs use StatsBomb Pro, Opta Analytics, and custom ML models costing $50K-$500K/year. Consumer apps deliver roughly **5% of the analytical depth** available to professional analysts. Academic papers publish techniques 2-5 years before any consumer product implements them.

**Example:** TacticAI (corner kick optimization) was published in Nature Communications in 2024. No consumer app offers corner kick analysis in 2026.

**Sources:** [4], [5], [6], [19], [20], [S1]
