# Data Layer: 365Scores + Apify + Scraping Ecosystem

## Finding 1: 365Scores API Is Undocumented but Reverse-Engineerable

365Scores has served 40M sports fans since 2012, delivering real-time scores across 1,000+ football leagues in 40 languages [11][12]. Acquired by **Entain** (LSE-listed, $9.2B market cap gambling company) for **$160M in April 2023**. Founded by IDF Mamram alumni. Platform runs on Google Cloud with Looker for BI [12].

365Scores has a **5-year partnership with Stats Perform (Opta)** signed 2021 -- meaning their data is Opta-grade, the gold standard for football [S1].

### Known API Surface

**Base URL:** `https://webws.365scores.com/web/`

| Endpoint | Path | Key Parameters | Returns |
|----------|------|----------------|---------|
| All Scores | `/games/allscores` | `sports`, `competitionIds`, `startDate`, `endDate`, `onlyLiveGames` | Games array with teams, status |
| Game Results | `/games/results/` | `competitions={id}` | Historical match results |
| Single Game | `/game/` | `gameId`, `matchupId`, `topBookmaker=14` | Full match: lineups, events, chart |
| Game Stats | `/game/stats/` | `games={id}` | Match statistics |
| League Stats | `/stats/` | `competitions={id}`, `withSeasons=true` | Top performers, season stats |

**Common params:** `appTypeId=5` (web), `langId` (1=EN), `timezoneName`, `userCountryId`

### App Data Exposed (Football)

- Live scores, match timelines (goals, cards, subs)
- Lineups and squad info, league standings/fixtures
- **xG and xGOT** analysis, **shot maps**
- **Player heatmaps** (confirmed via API endpoints)
- Head-to-head records, recent form
- Betting odds (pre-match and live)
- Live Penalty Taker feature
- News, transfers, predictions

### What Is NOT Available

- No confirmed pass-level event data (individual passes, tackles as raw events)
- No confirmed tracking data (player positioning coordinates)
- No public documentation of the full data model
- No public developer API or data licensing to third parties

### Community Libraries

| Library | URL | Status |
|---------|-----|--------|
| `LanusStats` (threesixfivescores.py) | github.com/federicorabanos/LanusStats | **Most comprehensive** -- league stats, match data, heatmaps |
| `py_365scores` (PyPI) | github.com/kkristof200/py_365scores | Last updated ~2021, MIT license |
| `python-365scores` | github.com/irwimscott/python-365scores | Basic GET request demo |

### Legal Risks

1. **Opta data licensing:** Underlying data is Opta-licensed. Stats Perform actively enforces licensing. Redistributing scraped Opta data is high-risk.
2. **Entain ownership:** Gambling companies are litigious about data IP.
3. **Private API:** `webws.365scores.com` is internal infrastructure, not a public service.
4. **Publisher ToS** prohibits copying or creating derivative works of Company material [16].
5. **robots.txt** does NOT blanket-disallow crawling but allowed paths are mainly for SEO.

**Bottom line:** Technically straightforward (unauthenticated JSON API), legally risky for commercial use. For production: license from Stats Perform / API-Football / Sportmonks.

---

## Finding 2: Apify Ecosystem Covers Most Sources Except 365Scores

### Existing Football Actors (Apify Store)

| Actor | Source | Runs | Users | Data |
|-------|--------|------|-------|------|
| FlashScore Scraper | FlashScore | **92,104** | 288 | Live scores, odds, events, 30+ sports |
| SofaScore Scraper PRO | SofaScore | 4,023 | 292 | Match stats, live scores, players, teams |
| Transfermarkt Scraper | Transfermarkt | 705 | 85 | Player values, transfer history |
| Football Fixtures API | Football-Data.org | 6,127 | 7 | Match schedules, standings |
| FOOTBALL API DATA | Multiple | 3,136 | 43 | Realtime all football data |
| Understat xG Scraper | Understat | -- | -- | Expected goals, shot data |
| Premier League API | PL | 198 | 15 | PL-specific stats |
| Opta Ranking Scraper | Opta | 148 | 10 | 13K+ teams, power rankings |

**Gaps:** No actors for 365Scores, FotMob, WhoScored, or Soccerway.

### Anti-Bot Landscape by Site

| Site | Protection | Solution | Rate Limit |
|------|-----------|----------|------------|
| FlashScore | Heavy JS rendering | Headless browser + proxy (Apify actors handle it) | Moderate |
| SofaScore | Cloudflare, tightening | **1 req / 25-30s** to avoid 403. Residential proxies required | Strict |
| Transfermarkt | Cloudflare | Browser automation (Playwright) required | Moderate |
| FotMob | Light (mobile API) | Simple HTTP requests work (`pyfotmob`) | Generous |

### Apify Cost Estimate: 5 Major Leagues Daily

| Component | Monthly Cost (Scale tier) |
|-----------|--------------------------|
| FlashScore live scores (2x/day) | $3.75 |
| SofaScore match stats | $2.25 |
| Transfermarkt valuations (weekly) | $0.25 |
| Actor per-result fees | $20-40 |
| Residential proxy (~2 GB/mo) | $14-16 |
| **Total** | **$40-65/month** |

At Scale tier ($199/mo with $199 credits), football scraping fits within included credits.

### Complementary: `soccerdata` Python Library

Covers 8 sources with unified Pandas DataFrames and local caching [3]:

Club Elo, ESPN, FBref, Football-Data.co.uk, SofaScore, SoFIFA, Understat, WhoScored

### Alternative Approaches

| Approach | Cost | Best For |
|----------|------|----------|
| `soccerdata` library | Free | Quick prototype, research, 8 sources |
| Apify actors | $40-65/mo | Production scraping, anti-bot handled |
| Crawlee self-hosted | ~$20/mo | Cost-optimized, full control |
| API-Football / Sportmonks | $20-100/mo | Guaranteed uptime, documented, legal |
| Direct API reverse-engineering | Free | FotMob, SofaScore mobile APIs |

### Open Datasets for ML Training

| Dataset | Type | Coverage |
|---------|------|----------|
| StatsBomb Open Data | Event + 360 | WC 2022, EURO 2024, Copa 2024, select leagues |
| Wyscout | Event data | 1 season across 5 leagues + 2 international |
| Metrica Sports | Tracking + event | 3 anonymized matches |
| SoccerNet | Video + annotations | 550+ broadcast games, CV tasks |
| Google Research Football | RL simulation | Physics-based 3D for multi-agent RL |

**Sources:** [1], [2], [3], [11], [12], [13], [14], [15], [16], [17], [18], [S1]
