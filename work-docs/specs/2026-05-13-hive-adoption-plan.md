# Hive Adoption Plan — Gas Town Roles, Auto-Beads, Unified Codex+Claude Bus

**Date:** 2026-05-13
**Owner:** Shoval Benjer
**Status:** Spec — not yet implemented. Tick 1 is the next concrete deliverable.
**Companion:** `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md` (master plan), `~/.claude/projects/-home-shovalbe/memory/MEMORY.md` (memory index).
**Forge Loop axes hit by this spec:** SPEC ✓, PREMORTEM ✓ (§9), COVERAGE plan (§8), REFLECT trigger (§10).

---

## 1. Goal

One sentence: build a shared work bus (the **Hive**) that lets Codex and Claude run the same Gas Town role taxonomy — Mayor / Polecats / Refinery / Witness / Deacon / Dogs / Crew — across all four i-sdd Rigs (Cs-agent, Campaign-analysis, qc-telephony-api, seekapa-training-platform), with auto-created beads flowing in from real triggers (PRs, eval failures, code-blast-radius alerts, prod errors, suspicious activity), Polecats fanning out to sub-agents per bead, and the whole thing running 18:00–20:00 IL time at zero additional cost.

This collapses five separate "next moves" into one architecture and re-uses every skill already shipped under their new role label.

---

## 2. Researched tech inventory

Each row: what it is, how it's used in this stack, source, status, where it slots into the Hive.

### 2.1 Gas Town (Steve Yegge)
- **What:** Multi-agent orchestrator. Defines the 7-role hierarchy (Mayor / Polecats / Refinery / Witness / Deacon / Dogs / Crew) and the work-unit vocabulary (Rigs = projects, Beads = issue-atoms). Bakes attribution, completion time, revision count, work history into orchestration so model A and model B are comparable on real work. Per the deep-research report (§13 + §149): the canonical practical example of lifecycle-aware evaluation built INTO the agent runtime, not as an external add-on.
- **How used here:** Source taxonomy for the Hive. Not deployed as a service — we adopt the vocabulary and role split, store beads in SQLite, build per-Rig Polecat skills locally. Kilo Code's hosted Gas Town variant is GitHub/GitLab-only (memory: research from 2026-05-09 session), so it cannot post review comments on the i-sdd Azure DevOps repos — that's why we self-host the pattern.
- **Source:** `github.com/steveyegge/gastown` (referenced in `~/.claude/history.jsonl` 2026-05-09 user prompt).
- **Status:** Pattern only — not installed. Inspires Hive design (§4).
- **Slot:** **The whole taxonomy.** Rigs / Beads / 7 roles ARE Gas Town.

### 2.2 Understand-Anything (Lum1104)
- **What:** Code-knowledge-graph plugin. Ships 8 skills (`/understand`, `/understand-chat`, `/understand-dashboard`, `/understand-diff`, `/understand-domain`, `/understand-explain`, `/understand-knowledge`, `/understand-onboard`) + 9 sub-agents (architecture-analyzer, article-analyzer, assemble-reviewer, domain-analyzer, file-analyzer, graph-reviewer, knowledge-graph-guide, project-scanner, tour-builder) + an `auto-update-prompt` hook. Produces `.understand-anything/knowledge-graph.json` + an interactive React-Flow dashboard. `/understand-diff` produces blast-radius for a diff.
- **How used here:**
  - **Trigger:** Wire `/understand-diff` into `commit-push-pr` pre-flight. Threshold (`blast_radius > N modules`) emits a `Polecat` bead in the matching Rig.
  - **Consumer-side helper:** Polecats consume the knowledge-graph to know which files matter for a bead's scope.
  - **Caveat:** `/understand` writes `.understand-anything/` to CWD. Because `$HOME` IS the seekapa worktree ([[project_home_as_repo]]), it MUST be invoked from a clean cwd, not `$HOME`.
- **Source:** `github.com/Lum1104/Understand-Anything`. Marketplace added 2026-05-13.
- **Status:** ✅ Installed 2026-05-13, v2.7.0, user scope, enabled. Scan validation still pending (memory: `project_understand_anything_install`).
- **Slot:** **Polecat sub-agent + bead producer.**

### 2.3 GBrain
- **What:** A pattern, not a tool you `pip install`. Per the deep-research report (§13, §56, §61, §131, §149): fast local CI gates + replay on captured real queries + LongMemEval bundled. Evaluation lives IN the runtime — failures from production auto-populate the replay set, making the eval surface evolve with reality instead of going stale.
- **How used here:**
  - Adopt the **replay-set-from-prod-failures** mechanism into the existing 4-phase Foundry eval pipeline. Eval rows currently curated; under GBrain pattern, every Foundry agent run where `evaluation_score < threshold` auto-appends `(input, golden_if_known, actual)` to `evals/replay/`. Nightly eval picks up new rows.
  - Bonus: LongMemEval is a public memory benchmark — worth pinning a copy under `evals/longmem/` once the replay loop works.
- **Source:** Cited only via `citeturn21view0`, `citeturn38view0` in the report — no public GitHub URL captured locally. URL TBD; user to provide canonical link if known.
- **Status:** Pattern adoption — not installed. Inspires §5.2 (eval-failure → bead trigger).
- **Slot:** **Dogs role.** Production-truth replay is exactly what Dogs do.

### 2.4 HyperAgents
- **What:** Per the deep-research report (§13, §37): adds explicit meta-evaluation metrics and warns that **evaluation gaming can distort apparent progress if the reward signal is weak**. Cited alongside OpenAI's CoT monitoring, Anthropic's reward-tampering work, and the Reward Hacking Benchmark as the source for the "checker bypass tests, seeded loopholes, adversarial judge tests, evaluator mutation tests" pattern.
- **How used here:**
  - **Meta-eval layer on top of the GBrain replay set.** Before trusting a bead's "closed/evidence" claim, the Deacon must run at least one adversarial-judge test on the bead's evidence. Seeded loopholes catch agents that paper over failures rather than fix them.
  - Adds an audit field per closed bead: `meta_eval_score` (0/1 — passed/failed adversarial judge).
- **Source:** Cited via `citeturn23view1` only. URL TBD.
- **Status:** Pattern adoption — not installed.
- **Slot:** **Deacon role.** Hard gate on bead-close.

### 2.5 RTK (Rust Token Killer)
- **What:** Token-optimized CLI proxy. Wraps shell commands and filters/compresses output before the model sees it. Per `~/RTK.md`: usage is `rtk <cmd>` (e.g. `rtk git status`), with `rtk gain` for token-savings analytics and `rtk proxy <cmd>` for raw passthrough. Codex-side is already RTK-aware.
- **How used here:**
  - **Enforcement.** Add a Claude `PreToolUse` hook on `Bash` that rewrites every `cmd` → `rtk cmd` unless already prefixed (≈15 lines, in `~/.claude/hooks/`). This is what makes the Polecat × sub-agent fan-out affordable — every shell call goes through RTK before it touches the context window.
  - **Witness metric.** `rtk gain` output is captured into each Layer-7 snapshot at `~/.claude/observability/snapshots/`. Weekly audit reports cumulative tokens-saved.
- **Source:** Binary at `/home/shovalbe/.local/bin/rtk` (ELF, ~9.5 MB, static-pie linked, stripped). Origin/repo URL not captured locally; treat `~/RTK.md` as the local source of truth.
- **Status:** ✅ Installed at `~/.local/bin/rtk`. Codex side already routes through it. Claude-side hook is TODO.
- **Slot:** **Cost reducer at the I/O boundary.** Not a role itself — a horizontal layer every role uses.

### 2.6 Obscura
- **What:** Rust headless browser for AI agents and scraping. CLI is `obscura serve --port 9222 --stealth` (CDP-style endpoint on `:9222`). Gives agents *eyes* on real UIs (mount-time, console errors, screenshot, fill-form, etc.) without driving Chrome/Edge.
- **How used here:**
  - **Drop-in Playwright backend.** Per the Codex rollout summary at `~/.codex/memories/rollout_summaries/2026-04-26T07-05-12-GEzd-obscura_playwright_cdp_migration.md`: Codex-side already has `~/.codex/bin/obscura-cdp` (start + health-check) and `~/.codex/bin/playwright-mcp-obscura` (starts Obscura, execs `@playwright/mcp --cdp-endpoint=...`). The 2026-04-26 migration was partial (user-aborted); finishing it is a Tick-2 sub-task.
  - **Post-deploy gate.** Polecat in every Rig with a frontend runs Obscura via CDP: nav canonical route → assert mount time < 3 s → assert zero console errors. Would have caught the training-platform SPA silent-mount failure (memory: `project_training_platform_2026-05-10`).
- **Source:** Binary at `/home/shovalbe/.local/bin/obscura` (ELF, ~77 MB, dynamically linked, not stripped). Project URL not captured locally; per memory: "Rust headless browser for AI agents/scraping." `cdp` skill defaults to Obscura on Linux.
- **Status:** ✅ Installed at `~/.local/bin/obscura`. Codex Playwright MCP rewires done in MCP configs across `~/.mcp.json`, `~/.codex/config.toml`, `projects/campaign-analysis/.mcp.json`, `projects/figma-4-all/.mcp.json`, `projects/qc/.mcp.json`, `projects/cs-agent/.mcp.json`. End-to-end smoke test still pending (turn aborted).
- **Slot:** **Polecat sub-agent (UI eyes) + Witness (evidence screenshots).**

### 2.7 Meta Ads CLI (Facebook)
- **What:** Facebook's official Marketing-API CLI ([announcement](https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli) 2026-04-29). Python 3.12+, `uv tool install` / `pipx`. Wraps create/read/update/delete on campaigns/ad-sets/ads via long-lived system-user access token. Defaults created ad resources to PAUSED.
- **How used here:**
  - **Container-side only.** Not on `$HOME`. Built into the Meta-tier ACA MCP container in the centralized marketing MCP gateway plan ([[centralized-marketing-mcp]], phase P1). Surfaced via APIM `/mcp/meta/*` with Entra appRoles (Reader/Operator/Manager) and tier-2 Conditional Access.
  - **Credentials:** Pulled from `kv-mcp-platforms` by the container's system-assigned MI — `app_id`, `app_secret`, `system_user_access_token`, `ad_account_id`. Never `.env`.
  - **Validation step:** Before committing to the CLI as the executor, compare against direct `facebook_business` SDK calls. The CLI's value is mostly (a) PAUSED default and (b) uniform CRUD surface — both reproducible without it.
- **Source:** `developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli`.
- **Status:** Not installed (correctly so — belongs in container, not `$HOME`). Tracked as task #3 with corrected scope (memory: `project_meta_ads_cli_scope`).
- **Slot:** **Crew (executor backend) inside the Meta-MCP container.** No direct role in the Hive itself — interacts via APIM-gated tool calls a Polecat makes during a campaign-analysis bead.

### 2.8 claude-obsidian (Daniel Agrici)
- **What:** Heavy plugin (11 skills) turning Claude into a vault organizer with citation-backed Q&A, autoresearch, and lint.
- **How used here:**
  - **Deferred.** A1 of the original setup task list. Worth revisiting only after Tick 3 is closed and the Hive is real — at that point a vault for `docs/` + memory + audit logs becomes useful as a Witness search index.
- **Source:** `github.com/AgriciDaniel/claude-obsidian`. Marketplace install: `claude plugin marketplace add AgriciDaniel/claude-obsidian && claude plugin install claude-obsidian@claude-obsidian-marketplace`.
- **Status:** Deferred (task #2). Side-worktree trial before daily-driver.
- **Slot:** **Future Witness search index.** Not on the critical path.

---

## 3. Gas Town roles → existing skills mapping

Most roles already exist as skills with different names. Re-labelling + dispatch table, not rewrites.

| Role | Existing skill / artefact | What it gains under the Hive |
|---|---|---|
| **Mayor** | You typing `Pick up` (interactive) | A cron-Mayor (Codex routine) opens the 18:00 IL window: scans open beads, prioritises, dispatches to Polecats. |
| **Polecats** (executor per Rig) | `red-team-review` is the multi-persona-via-subagents template | Per-Rig declared in `~/.hive/rigs.yaml` with allowed sub-agents + per-bead token budget. |
| **Refinery** (clean output) | `simplify`, `humanize`, `refactor-pre-push`, `code-simplifier` | Auto-trigger on bead-close before Deacon gate. |
| **Witness** (evidence) | Layer-7 snapshots (`~/.claude/observability/snapshots/`), `sessions.db`, `~/.codex/memories/`, `~/.claude/cache/a2a/audit.jsonl` | Bead row gains `evidence_url` (PR link / run id / eval row id / screenshot). RTK `gain` added to snapshot schema. |
| **Deacon** (policy) | `coverage-enforcer`, `premortem`, forge-loop axis check, `commit-push-pr` gates | Hard gate on bead-close. Runs at least one HyperAgents-style adversarial-judge test on evidence → writes `meta_eval_score`. |
| **Dogs** (hunt regressions) | `eval-runner` 4-phase pipeline, `heidegger-reflect`, `azure-activity-watch`, `azure-audit` | GBrain pattern: prod failure → auto-bead. Dogs claim and triage. |
| **Crew** (support / executors) | `codex-call`, `dispatch`, `azure-runtime`, `agent-builder`, `azure-resource-investigator`, `foundry-agent-inspector`, `eval-row-diagnoser` | Bead-aware dispatch — Codex picks claimed bead by id, writes evidence back. |

Read this table as: "If we adopt Gas Town vocab, the only NEW work is the **bead bus** + the **role dispatcher**; every individual capability is already shipped."

---

## 4. The Hive — minimum-viable architecture

One small artefact set both CLIs read from. Nothing exotic.

```
~/.hive/
├─ beads.db              # SQLite, lockable via flock
├─ rigs.yaml             # per-Rig: polecat skills, sub-agent fan-out cap, budget
├─ audit.jsonl           # append-only; mirrors ~/.claude/cache/a2a/audit.jsonl
└─ bin/
   ├─ bead-create        # POSIX; called from triggers
   ├─ bead-claim         # atomic claim with side-id + agent-id (BEGIN IMMEDIATE)
   ├─ bead-close         # writes evidence_url, runs Deacon gate, emits to audit
   └─ bead-list          # both CLIs enumerate
```

**Bead schema (one row, 14 cols):**
```sql
CREATE TABLE beads (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  rig             TEXT NOT NULL,                       -- cs-agent | campaign-analysis | qc-telephony-api | seekapa-training-platform
  title           TEXT NOT NULL,
  body_md         TEXT,
  status          TEXT CHECK(status IN ('open','claimed','closed','killed')) DEFAULT 'open',
  priority        TEXT CHECK(priority IN ('P0','P1','P2','P3')),
  owner_role      TEXT CHECK(owner_role IN ('polecat','dogs','crew','witness')),
  parent_bead     INTEGER REFERENCES beads(id),
  created_by      TEXT NOT NULL,                       -- trigger name
  claimed_by      TEXT,                                -- "codex:agent_xxx" | "claude:session_yyy"
  evidence_url    TEXT,
  blast_radius    INTEGER,                             -- nullable
  deadline        TEXT,
  meta_eval_score INTEGER,                             -- HyperAgents adversarial-judge result; 1 = passed
  created_at      TEXT DEFAULT (datetime('now')),
  updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_beads_status_rig ON beads(status, rig);
CREATE INDEX idx_beads_priority ON beads(priority);
```

**Why SQLite + JSONL not a queue server:**
- Both CLIs already have Python.
- `flock`-protected SQLite handles hundreds of beads/day comfortably.
- No daemon to babysit.
- Survives WSL reboot.
- Upgradable to Cosmos Free tier later if cross-machine access is needed (Yasha, etc.).

---

## 5. Auto-bead triggers (5 listeners)

Each ≈30–50 LOC Python. Run via cron 18:00–20:00 IL. All call `bead-create`.

### 5.1 ADO PR / review-comment listener
- **Source:** Azure DevOps webhook → small Python `webhook_listener.py` on a free ACA Consumption (scales to zero).
- **Produces:** bead per PR opened, per review comment posted (owner_role=`polecat`, P2 default; P0 if title prefixed `[P0]`).
- **Maps to Gas Town:** This IS what Kilo Code's hosted Gas Town does for GitHub/GitLab — we re-implement for ADO because Kilo Code doesn't support ADO.

### 5.2 Eval-row-failure listener (GBrain pattern)
- **Source:** `eval-runner` skill output. Hook into the existing 4-phase pipeline (`grok-4-1-fast-reasoning-2-eval` primary + DeepSeek-V3.2 audit).
- **Produces:** bead with `(input, golden, actual, judge_rationale, kb_hits)` evidence, owner_role=`dogs`, P1.
- **Replay loop:** Closed beads with passing `meta_eval_score` AND new fix get appended to `evals/replay/` so nightly eval keeps regression-protected.

### 5.3 Understand-Anything blast-radius listener
- **Source:** `commit-push-pr` pre-flight hook runs `/understand-diff` on staged diff.
- **Produces:** bead when `blast_radius > N modules` (N tuned per Rig in `rigs.yaml`), owner_role=`polecat`, P2.
- **Carries:** the impacted module list as `body_md`. Polecat fans out to module-owner sub-agents.

### 5.4 Production-error listener
- **Source:** App Insights / Foundry agent run-trace errors via small Python poller (no Sentinel needed for v1).
- **Produces:** bead owner_role=`dogs`, severity-mapped (P0 for 5xx storm, P1 for repeated error in one trace, P2 for warnings).
- **Witness link:** trace id / Application Insights URL → `evidence_url`.

### 5.5 Suspicious-activity listener (`azure-activity-watch` integration)
- **Source:** Existing `azure-activity-watch` skill — detects when someone other than `shoval.be@i-sdd.com` stops/restarts/deletes/resizes resources in `AZAI_group`.
- **Produces:** bead owner_role=`polecat`, P0, with activity-log link.
- **Origin:** memory `project_yasha_stop_incident` — Yasha stopped 2 web apps on 2026-05-03 without notice. This trigger exists because of that.

---

## 6. Polecats × sub-agents (per-Rig declaration)

`~/.hive/rigs.yaml` declares each Rig's Polecat lineup and budget envelope.

```yaml
rigs:
  cs-agent:
    polecats:
      - id: kb-polecat
        subagents: [foundry-agent-inspector, eval-row-diagnoser]
        budget_per_bead: 60_000   # input tokens cap
        max_subagents_concurrent: 2
      - id: deploy-polecat
        subagents: [azure-resource-investigator, azure-activity-watch]
        budget_per_bead: 40_000
        max_subagents_concurrent: 2
    max_polecats_concurrent: 2

  campaign-analysis:
    polecats:
      - id: meta-mcp-polecat
        subagents: [foundry-agent-inspector]   # later: meta-ads-cli wrapper inside the container
        budget_per_bead: 50_000
      - id: ui-polecat
        subagents: [obscura-cdp-runner]        # Obscura post-deploy gate
        budget_per_bead: 30_000
    max_polecats_concurrent: 2

  qc-telephony-api:
    polecats:
      - id: telephony-polecat
        subagents: [azure-resource-investigator, eval-row-diagnoser]
        budget_per_bead: 50_000
    max_polecats_concurrent: 1

  seekapa-training-platform:
    polecats:
      - id: training-polecat
        subagents: [azure-resource-investigator, obscura-cdp-runner]
        budget_per_bead: 60_000
    max_polecats_concurrent: 1
```

**Claim semantics:**
- `bead-claim` does `BEGIN IMMEDIATE; SELECT … WHERE status='open' AND rig=? ORDER BY priority, created_at LIMIT 1; UPDATE … SET status='claimed', claimed_by=? WHERE id=?; COMMIT;`.
- Side+agent string format: `codex:agent_xxx` or `claude:session_yyy`.
- TTL: if a claimed bead has no `evidence_url` after 30 min, Mayor un-claims it (cron sweep).

**Fan-out pattern:** Polecat skill invokes the existing `Agent` tool (Claude) or its Codex equivalent with `subagent_type` matching each declared sub-agent, in parallel. Already proven by `red-team-review` skill.

---

## 7. Codex ↔ Claude bridge — one Hive, two CLIs

Current state: `dispatch` skill is Claude → Codex only. Audit at `~/.claude/cache/a2a/audit.jsonl`. `codex-call` is similar.

Two additions close the loop:

### 7.1 `bead-claim` is atomic across both sides
- The `BEGIN IMMEDIATE` transaction means whichever side claims first wins; the other gets nothing on that row. No message broker needed.
- Both sides write to the same `~/.hive/audit.jsonl`.

### 7.2 Codex companion script `~/.codex/bin/bead-pick`
- Polls open beads matching its allowed roles (`crew`, `dogs`, optionally `polecat` per `rigs.yaml`) every 5 minutes during the 18:00–20:00 IL window.
- Picks the highest-priority match, claims, runs the matching Codex skill/automation, writes `evidence_url` back, sets `status='closed'`.
- This makes Codex an independent consumer of the Hive — no Claude orchestrator required to run a routine bead.

Effect: a true producer-consumer Hive with Codex as a worker pool and Claude as an interactive orchestrator (or vice-versa per bead) — no extra daemon, no MCP gateway, no Cosmos.

---

## 8. Implementation ticks (smallest first)

### Tick 1 — Hive skeleton + RTK enforcement (1–2 h)
- Create `~/.hive/` tree + `beads.db` (apply schema in §4).
- Write `bead-create`, `bead-claim`, `bead-close`, `bead-list` — ≈150 LOC POSIX shell + Python.
- Write Claude `PreToolUse` hook on `Bash` rewriting cmd → `rtk cmd` (≈15 LOC, drop into `~/.claude/hooks/`).
- Verify: insert a hand-crafted bead, claim from a fresh Claude session, close with a fake `evidence_url`, see audit row.
- **Acceptance:** all four `bead-*` scripts callable from both Codex and Claude shells; RTK hook intercepts at least one `Bash` call and produces non-zero `rtk gain`.

### Tick 2 — First real producer: Understand-Anything → bead-create
- Pre-flight hook in `commit-push-pr` runs `/understand-diff` on staged diff.
- If `blast_radius > N` (default N=4, per-Rig override), call `bead-create` with body=`module list`, owner_role=`polecat`, priority=`P2`.
- Validation target: most recent merged PR 268 — re-run `/understand-diff` against its diff offline, confirm threshold logic.
- Finish the Obscura/Playwright-MCP migration (the 2026-04-26 turn was aborted) as a side-task: smoke-test `~/.codex/bin/playwright-mcp-obscura` end-to-end, confirm `:9222` CDP responds, then mirror the wiring on the Claude `cdp` skill.
- **Acceptance:** synthetic diff (touch 5 modules) → bead lands in `beads.db` with `blast_radius=5`, status=`open`, rig set correctly.

### Tick 3 — First real consumer: `kb-polecat` on `cs-agent` Rig
- Polecat skill at `~/.claude/skills/kb-polecat/SKILL.md` (or Codex equivalent) — declares fan-out to `foundry-agent-inspector` + `eval-row-diagnoser`.
- Hook eval-runner row failures (§5.2) to `bead-create` with `created_by=eval-runner`.
- Polecat claims, fans out, aggregates, calls Refinery (`simplify`), runs Deacon gate (coverage-enforcer + an adversarial-judge test → `meta_eval_score`), closes with `evidence_url` = eval row id + run trace.
- **Acceptance:** seed a failing eval row → bead appears within 60 s → Polecat claims within next Mayor tick → bead closes with `meta_eval_score=1` and Deacon-passed evidence link.

After Tick 3: one producer + one consumer + one Rig + one Polecat = closed loop. Fan out (more Rigs, more Polecats, more triggers) is now mechanical.

---

## 9. PREMORTEM — 5 failure modes (required by Forge Loop)

1. **Polecat × sub-agent fan-out runaway.** A Polecat spawns sub-agents that spawn sub-agents. Token bill explodes.
   - **Mitigation:** `budget_per_bead` enforced in the Polecat skill itself by token-counting wrapper around the `Agent` tool. Hard cap. `max_subagents_concurrent` per Polecat. `max_polecats_concurrent` per Rig.

2. **Race condition on claim.** Two Claudes (or one Claude + one Codex) try to claim the same bead within the same millisecond.
   - **Mitigation:** `BEGIN IMMEDIATE` + `UPDATE … WHERE status='open' AND id=?` — only one transaction commits, the other sees `rowcount=0` and retries with a different bead.

3. **Stale claims / abandoned beads.** A session crashes mid-bead; the row sits `claimed` forever.
   - **Mitigation:** Mayor cron-sweep un-claims any bead with `status='claimed' AND updated_at < now()-30min`. Audit logs the un-claim.

4. **Deacon gates fire false positives → no bead ever closes.** Adversarial judges are pessimistic; a healthy fix gets `meta_eval_score=0` and the bead loops.
   - **Mitigation:** Deacon failure logs to audit with full reason. After 3 consecutive failures on the same bead the Mayor escalates to interactive Shoval review (writes a `needs_input` flag).

5. **Hive becomes a back-channel that bypasses Fabric / governance.** Polecats start writing to prod CRM or pulling raw call transcripts because the Hive lets them.
   - **Mitigation:** Per [[centralized-marketing-mcp]]: APIM + Entra appRoles gate every sensitive call. Polecats interact with prod ONLY via the centralized MCP gateway — never direct SDK or direct DB. The Hive carries beads; the MCP carries calls. Different surfaces, different gates.

---

## 10. Out of scope (deliberate)

- A web UI for the Hive. CLI + `bead-list` is enough for v1.
- A scheduler more complex than cron. The 18:00–20:00 IL window is a hard `*/5 18-19 * * *` cron, nothing fancier.
- Cosmos / cross-machine sharing — SQLite v1 only. Upgrade later if Yasha or remote Codex need access.
- Replacing Fabric / Power BI as the analytical surface. Hive is operational; Fabric is analytical (per memory `project_centralized_marketing_mcp`).
- Migrating off Azure DevOps to GitHub. Repo platform split is fixed (memory: `project_repo_split`).
- Running outside the 18:00–20:00 IL window. Cost cap is real.

---

## 11. Open decisions for Shoval before Tick 1

These have safe defaults — flag any disagreement:

1. **SQLite at `~/.hive/beads.db`** vs Cosmos Free tier from day 1. Default: SQLite.
2. **Mayor identity** = Codex routine on cron, not Claude (Claude needs interactive auth in this setup). Default: Codex routine.
3. **Deacon strictness** = adversarial-judge gate is BLOCKING on bead-close. Default: blocking. Means fewer beads close but cleanly.
4. **RTK enforcement scope** = ALL Bash from Claude routes through RTK, no exceptions. Default: all. Skip-list configurable in the hook.
5. **First Rig** = `cs-agent` for Tick 3 (most mature, most existing skills aligned). Confirm before Tick 3.

---

## 12. References

- Master plan: `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`
- Original setup tasks (A1-A4): `~/claude-setup-tasks-2026-05-02.md`
- Deep research report (Gas Town / GBrain / HyperAgents synthesis): `~/docs/deep-research-report (2).md` §13, §37, §56, §61, §131, §149
- Testing practices: `~/docs/testing_practices.txt`
- Codex Obscura migration rollout (partial, 2026-04-26): `~/.codex/memories/rollout_summaries/2026-04-26T07-05-12-GEzd-obscura_playwright_cdp_migration.md`
- RTK usage: `~/RTK.md`
- Memory pointers: `~/.claude/projects/-home-shovalbe/memory/MEMORY.md` — especially `project_centralized_marketing_mcp`, `project_understand_anything_install`, `project_meta_ads_cli_scope`, `project_yasha_stop_incident`, `project_repo_split`, `project_home_as_repo`.

## 13. Repos / sources (canonical)

| Tool | URL | Status here |
|---|---|---|
| Gas Town | `https://github.com/steveyegge/gastown` | Pattern adoption — not installed |
| Understand-Anything | `https://github.com/Lum1104/Understand-Anything` | Installed v2.7.0, 2026-05-13 |
| claude-obsidian | `https://github.com/AgriciDaniel/claude-obsidian` | Deferred (A1) |
| Meta Ads CLI | `https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli` | Container-only (A3 reframed) |
| GBrain | URL TBD — referenced in deep-research-report via citeturn refs | Pattern adoption only |
| HyperAgents | URL TBD — referenced in deep-research-report via citeturn refs | Pattern adoption only |
| RTK (Rust Token Killer) | Local — `~/RTK.md`, binary `~/.local/bin/rtk` | Installed; origin URL not captured |
| Obscura | URL TBD — Rust headless browser for AI agents; binary `~/.local/bin/obscura` | Installed; Codex Playwright MCP partially wired |
