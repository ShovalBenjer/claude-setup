# Claude Code Setup — Master Plan (Reconciled)

> **SUPERSEDED 2026-05-04** by `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`. That v2 absorbed everything in this v1 plus subsequent audits. Keep this file for archaeology only.

**Date:** 2026-05-02
**Inputs reconciled:**
- `~/From 2028  Looking Back on 2026 Agentic Coding...md` (the 7-layer 2030 vision)
- `~/Futuristic Learning Stack...April 2026 Edition.md` (measurement + learning stack)
- `~/Autonomous Agentic Coding Systems...2025–2030 Deep Dive.md` (research grounding)
- `~/AI Engineering 2030–2035 Scientific Frontiers...md` (career frame)
- `~/claude-code-experimental-features.md` (concrete feature punch list)
- `~/cleanup-proposal.md` (`$HOME`-as-repo hygiene)
- `~/claude-setup-tasks-2026-05-02.md` (this weekend's research roundup)
- Windsor.ai live connector inventory (this session)
- GitHub profile `ShovalBenjer` (this session)

---

## Part 1 — Meta Ads via Windsor: What's actually wired and what to do

### What's connected (i-sdd account `shovalbeisddcom`)

| Connector | Accounts | Notable brands |
|---|---|---|
| **facebook** | **40** | Seekapa, Axia (App + IL), Traders Academy, DailyVesting/DailyInvesting, WhatsAppSignals (1+2), MIC (Markets Insider Club), Q8 Trade [Httpool], Wonder Care (RO), CalendarTrader, Top 10 Apps Ever, Al Manara, ST-Agency, BeZ Online HR, plus regional MS/GCCMM/TS/WS/TA spend accounts |
| **google_ads** | 37 | Axia per-region (UAE/KSA/BHR/KWT/OMN/QTR/Brazil), SeeKapa (UAE/KSA/Kuwait/Qatar), Traders Academy main + AFF, Daily Vesting per-region, WhatsApp Signals per-region, MIC per-region (one suspended) |
| **linkedin** | 4 | Trader's Ad Account (x2), Ali's Ad Account, Trader Academy |
| **tiktok** | 4 | GCCMM, AccountSeekapa, BP-General, Academy-TA |
| **snapchat** | 2 | MITSO MARKETING, Traders_Academy |
| **taboola** | 1 | smarttool-network |
| **sendinblue** | 1 | tech@corp-domain.com |

### What this enables (high-leverage, low-effort)

1. **Cross-brand spend sanity check** — pull `spend / impressions / CTR / ROAS` for the 40 FB accounts in one query, surface outliers (waste vs winners). One Windsor `get_data` call across all account IDs.
2. **Seekapa-specific funnel join** — the only FB account explicitly tagged "Seekapa" is `3946579275574051` ("I.S.D.D Communication Ltd - Seekapa"). Join that with Google Ads `Seekapa - UAE/KSA/Kuwait/Qatar` accounts for the multilingual rollout you're shipping (v109).
3. **GCC market view** — UAE/KSA/Bahrain/Kuwait/Oman/Qatar are split across many accounts. Build one dashboard query that aggregates by region instead of by ad account — natural fit for the new yasha-multilingual flow.
4. **Suspended account hygiene** — `MIC - UAE (SUSPENDED)` is still in the connector list. Audit for stale/suspended accounts before spend reports get noisy.
5. **Channel mix report** — TikTok + Snapchat + Taboola have a single account each per brand; trivial to build a "non-Meta share of spend" view.

### Concrete first query (when you want it)

```
get_fields → facebook → list valid metric IDs (file already saved this session at
  ~/.claude/projects/.../tool-results/mcp-claude_ai_Windsor_ai-get_fields-*.txt)
get_data → facebook → fields=[date, account_name, campaign, spend, impressions, clicks, ctr, cpc]
         → date_preset=last_30d → all 40 account IDs
```
Output: 30-day per-campaign spend table. Pipe into a notebook for outlier detection, or into LanceDB for embedding-based campaign clustering (ties to the 2028 vision's measurement layer).

### Meta Ads CLI (the FB blog post) — verdict UPDATED

Original advice was "skip unless you run ads". You **do** run ads — at material scale (40 accounts). Revised:

- **Useful for:** programmatic bulk operations Windsor doesn't support (creating ad sets from a CSV, pausing campaigns by tag, bulk creative uploads).
- **Useful for:** scripting the suspended-account audit with a `pause-everything-on-suspension` guardrail.
- **Not useful for:** what Windsor already does (analytics pulls, performance reports). Don't duplicate.
- **Action:** install once on your dev box, gated behind a Key Vault token, with a **read-only-by-default** wrapper script. Default `--paused` for all create commands. Don't grant it to any agent until you've validated it manually.

---

## Part 2 — GitHub `ShovalBenjer`: Activate professionally

**Current state (per profile fetch):**
- Tel Aviv, "Solution Engineer" in bio
- 21 repos visible to GitHub but you say all private since you joined i-sdd
- Pinned (per profile API): AdMaven Data Engineering (ETL), Altius Financial Analysis, Time Twist Visualizer (Rust TUI), Bank Product Prediction, plus PoCs PhantomReach and SoloSolve AI
- Personal email `Shovalb9@gmail.com` listed; work email is `shoval.be@i-sdd.com`
- Badges: Pair Extraordinaire, Quickdraw, Pull Shark x2, YOLO

> **Verify before acting** — the profile fetch shows 21 repos but you say all private. Possible the WebFetch summarizer hallucinated repo names. Confirm by visiting the profile yourself before promoting anything; if the "pinned" list above is wrong, the rest of this section is still directionally right.

### What to do, in order

1. **Audit what's actually public vs private** — log in, list all 21 repos, mark each: keep-private / make-public / archive / delete. Anything tied to i-sdd, Seekapa, customers, or proprietary code stays private. Educational + personal projects (Time Twist Visualizer, Bank Product Prediction, AR/NLP PoCs) are candidates for public.

2. **Profile README v1** — replace the spreadsheet quote with a 5-line bio that signals: Solution Engineer @ i-sdd, AI agents on Azure (Seekapa/Axia), interests = autonomous coding agents + ad-tech data engineering, Israel-based, contact via LinkedIn. Pin 4–6 strong public repos.

3. **One showcase repo** — pick the most polished private project that's de-coupled from work IP and turn it into a public flagship. Time Twist Visualizer (Rust TUI for git history) is your best bet: niche enough to stand out, Rust signals systems chops, no employer entanglement.

4. **Open-source contributions, not just personal repos** — given the Navan ML role from yesterday's research, the highest-signal move is PRs to vLLM, Hugging Face TRL, or DeepEval. One merged PR to any of those outweighs five new personal repos.

5. **Wire `gh` CLI on this machine** — `gh` is missing per yesterday's session. Install via `apt`/`bun`/snap so `commit-push-pr` skill works against GitHub repos (not just Azure DevOps).

6. **Decouple personal email** — your GitHub uses `Shovalb9@gmail.com`. If you want this profile visible at i-sdd, decide whether to add `shoval.be@i-sdd.com` as a verified secondary or keep work strictly in Azure DevOps and personal strictly in GitHub. Either is fine — pick one and be consistent.

---

## Part 3 — Reconciled 2030 setup roadmap (the 7-layer stack)

Mapping the 2028 vision doc against what's **actually** in `~/.claude/` today.

| Layer | Vision spec | Today | Delta |
|---|---|---|---|
| **1. Memory** | 4-level CLAUDE.md hierarchy + `.claude/rules/` | `MEMORY.md` only; no `CLAUDE.md` at `$HOME`; `AGENTS.md` is Codex-only | Add `~/.claude/CLAUDE.md` (global) + per-project `CLAUDE.md`. Externalize 5 rules into `.claude/rules/`. |
| **2. Hooks** | UserPromptSubmit + Pre/PostToolUse + Pre/PostCompact + SessionStart/End + SubagentStart/Stop | Only UserPromptSubmit (voice + visual triggers) | Wire **3 priority hooks**: `PreToolUse` (deny-list for `rm -rf`, `git push --force`, `.env` writes), `PreCompact` (snapshot eval/TODO state), `SubagentStop` (voice 60-word recap). Source: experimental-features.md §1, §3. |
| **3. Subagents** | Curated fleet: planner, code-explorer, security-reviewer, test-writer, performance-auditor, memory-curator, dep-watcher | None custom; using built-in Explore/Plan/general-purpose | Create `memory-curator` first (Stop-hook driven, ACE pipeline) — highest leverage per the 2028 doc. Then `security-reviewer` with `user`-scope memory. Then `test-writer` write-restricted to `tests/`. |
| **4. Skills** | Reusable behavioral packages with frontmatter (paths, model, effort, allowed-tools, hooks) | 0 Claude skills. ~25 Codex skills (per AGENTS.md) | Port the 5 most-used Codex skills with proper frontmatter: `commit-push-pr`, `eval-runner`, `red-team-review`, `web-inspect`, `cleanup-crew`. Each gets its own SKILL.md with `paths:` + `model:` + `effort:`. |
| **5. Slash commands** | Codified workflows (`/spawn-team`, `/coverage-map`, `/audit-deps`, `/consolidate-memory`, etc.) | 1: `commit-push-pr.md` | Add `/spawn-team` (parallel subagent decomp), `/consolidate-memory` (triggers memory-curator), `/audit-deps` (Seekapa Python pkgs + Azure Functions runtime). |
| **6. MCP** | 2–3 core globally + per-project + lazy load. Curated: GitHub, Postgres, Tavily, LanceDB, DeepEval, Linear, Firecrawl | telegram + playwright (lazy). Foundry MCP at `~/.claude/mcp-servers/azure-foundry-mcp` (not in `.mcp.json`?) | Inventory: confirm Foundry MCP is wired. Add (per need): GitHub (after `gh` install), LanceDB-custom for the observability layer, Context7 to local config (currently auto-listed only). |
| **7. Observability + self-measurement** | Stop hook → embed → LanceDB → DeepEval 5% LLM-judge → weekly UMAP coverage → golden expansion → CI/CD regression | None | This is the biggest gap and the highest-value buildout. Don't try to do it all — start with **Stop hook → log session metadata to JSONL** + **DeepEval deterministic checks**. Defer LanceDB + UMAP until you have ≥100 sessions logged. |

### Existing groundwork from `cleanup-proposal.md` (status)

- ✅ A2 hardening done: `.git/info/exclude` + `.npmrc` fixed
- ⏳ A1 ($HOME repo move to `~/projects/axia-seekapa-cs-agents/`) — **deferred decision**, recommend doing this BEFORE Layer 1 work, otherwise new `CLAUDE.md` files at `$HOME` get tangled with the worktree
- ⏳ B (138MB .pst) — stale, just move it
- ⏳ K (track `~/.claude/hooks/` + `~/.claude/bin/` in a dotfiles repo) — **prerequisite for Layer 2/3 buildout**, otherwise hook code is unbacked

---

## Part 4 — Sequencing: what to actually do, in what order

### This week (5 small wins, all reversible)

1. **Move `$HOME` worktree out** (cleanup A1) — `mv` the seekapa worktree to `~/projects/axia-seekapa-cs-agents/`, re-init `$HOME` as a tiny dotfiles repo. **Prerequisite for everything else.**
2. **Install `gh` CLI** — unblocks `commit-push-pr` for GitHub flow.
3. **Track hooks + bin in dotfiles repo** — `~/.claude/hooks/` + `~/.claude/bin/` get versioned to `github.com/ShovalBenjer/dotfiles` (private). Disaster-recovery hedge.
4. **Write `~/.claude/CLAUDE.md`** — 30-line global rules file: terse-output, no-emojis, RTL handling, Codex-vs-Claude split, destructive-op authorization. Mirrors what's already in `MEMORY.md` feedback entries but in the right file for Claude to load on every session.
5. **Audit GitHub repos** — login, list 21 repos, decide keep-private/public/archive. Update profile README. ~1 hour.

### Next 2 weeks (Layer 2 + Meta data win)

6. **Wire 3 priority hooks** — `PreToolUse` deny-list, `PreCompact` snapshot, `SubagentStop` voice recap (per the 2028 doc + experimental-features.md picks).
7. **First Windsor cross-brand report** — pull last-30d FB spend across all 40 accounts, build one notebook that flags outliers. This is a 2-hour task that gives you immediate ad-tech leverage and seeds the "ad ops at i-sdd" portfolio piece.
8. **Install Understand-Anything on Seekapa** (carryover from yesterday's plan) — biggest leverage for current work.

### Month 2 (Layers 3–4)

9. **Build `memory-curator` subagent** — Stop-hook driven, runs ACE pipeline (BulletSelector → Reflector → Curator → Playbook). The single most important subagent per the 2028 doc.
10. **Port 3 Codex skills to Claude** — `commit-push-pr`, `eval-runner`, `red-team-review`. Each with frontmatter (`paths:`, `model:`, `effort:`).
11. **claude-obsidian** (carryover) — set up the vault, ingest your 15 research markdowns, validate `/autoresearch`.

### Month 3+ (Layer 7 — observability, the moat)

12. **Stop hook → JSONL session log** — minimal version: write `{session_id, timestamp, prompt, tool_calls, output_summary}` per session to `~/.claude/observability/sessions.jsonl`. Wire DeepEval deterministic checks (format, PII, regex constraints).
13. **Golden dataset (50 examples)** — built from real Seekapa session failures.
14. **Embedding store (LanceDB)** — only after ≥100 sessions logged, or you're optimizing nothing.
15. **5% LLM-as-judge sample** with G-Eval + bias correction (per `Futuristic Learning Stack` Part II).

### Quarter 2+ (the learning system, not just measurement)

16. **Weekly UMAP coverage topology** + gap-driven golden expansion
17. **Confidence-tier routing** (0.90+/0.70–0.89/<0.70) at the PreToolUse hook
18. **Reward Machine experiments** — per `Futuristic Learning Stack` Part III, this is where Markov ends and the 2026 frontier lives. Tie to the Navan ML role gap-closing.

---

## Part 5 — Career-path reconciliation (Navan + GitHub + 2030 frontier)

The Navan Senior ML Engineer role from yesterday is the **calibration target** for the next 6 months. Your current ad-tech work (this Windsor inventory) plus your 2030 vision documents plus the GitHub showcase plus the Seekapa eval/agent work form a coherent narrative if pitched right:

> "Solution engineer running 40+ Meta ad accounts across MENA + LATAM at i-sdd, building agentic eval infrastructure for production AI agents (Seekapa OTP, Axia intake), with a 2026→2028 roadmap toward verifiable autonomous coding systems."

Concrete one-quarter milestones that triple-count (Navan-fit + i-sdd value + public portfolio):

- **Stand up a vLLM container** serving a quantized 7B model — closes the Navan gap, can host an internal Seekapa eval-judge cheaply, becomes a public blog post.
- **One merged PR to DeepEval, vLLM, or HF TRL** — public contribution, signals the right stack.
- **Public write-up of the Windsor → LanceDB → embedding-clustering pipeline** for ad campaign anomaly detection — combines your day job with the 2028 measurement layer story. Doesn't leak proprietary data; the *pattern* is the artifact.

Don't apply to Navan yet. Build these three things first, then the application writes itself.

---

## Source files (re-read when needed)

- `~/From 2028  Looking Back on 2026 Agentic Coding — What to Build Today.md` — the 7-layer master spec
- `~/claude-code-experimental-features.md` — Q1 2026 feature inventory + first-wave picks
- `~/Futuristic Learning Stack...April 2026 Edition.md` — measurement + math frontier
- `~/Autonomous Agentic Coding Systems...2025–2030 Deep Dive.md` (and `(1).md` dup) — research grounding
- `~/AI Engineering 2030–2035 Scientific Frontiers...md` — career frame
- `~/cleanup-proposal.md` — `$HOME` hygiene status
- `~/claude-setup-tasks-2026-05-02.md` — yesterday's weekend research
- This file — master reconciliation
