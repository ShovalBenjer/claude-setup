# Consolidated Adopt Backlog — 2026-06-09

> **STATUS 2026-07-29: NOT LIVE. Do not read the rows below as a queue.**
>
> This backlog is 50 days old and was never worked. Adoption measured today by
> running checks against this machine, not by reading status fields. Coverage is
> 12 of 26 rows; the other 14 target employer Azure, ADO, or external repos and
> cannot be checked from here.
>
> | row | claim | measured 2026-07-29 |
> |---|---|---|
> | 2 | wire dead `UserPromptSubmit` + `PostToolUse` hooks | HALF. `UserPromptSubmit` gained 2 matchers on 2026-07-29, 50 days late and for an unrelated project (intent capture). `PostToolUse` still empty. |
> | 3 | `NO_COLOR` / `PAGER` / `GIT_PAGER` in agent env | NOT DONE |
> | 4 | populate `~/.config/rtk/filters.toml` | VOID. File missing, and the `rtk` binary does not exist on this machine, so the row is unexecutable as written. |
> | 12 | adopt `orjson`, `pandera`, `hypothesis`, `instructor`, `polars`, `structlog` surgically | 0 of 6. Zero import sites across `tools/`, `intent-control-plane/src/`, `tests/`. |
> | 16 | Beads to Azure Table Storage | NOT DONE. No beads artifact found anywhere in the tree. |
> | 20 | CJA-cure skills: `requirement-anchor`, `context-bounded-analyst`, `decision-grade`, `pii-scrubber` | **DONE, 4 of 4.** The only row that fully landed. |
> | 21 | infra skills: `kv-health`, `secretless-pipeline`, `aca-job-deploy`, `mcp-supply-chain-pin` | 0 of 4 |
> | 22 | Azure / GitHub / ADO / Sentry / Context7 MCP servers | NOT DONE. `mcpServers` is empty in `dot-claude/settings.json`. |
> | 23 | install `sd`, `mlr`, `hyperfine` via `mise` | 0 of 4 binaries present |
> | 24 | rtk-first "Agent Shell Defaults" block into CLAUDE.md | NOT DONE. Zero hits in either `CLAUDE.md`. |
> | 25 | claim AI Skills Fest voucher by June 12 | EXPIRED, deadline passed 47 days ago |
> | 26 | AI-103 ramp | operator-owned, not measurable from disk |
>
> One row of twelve landed. One is void. The rest are open or expired.
>
> Reviving any row means re-verifying its premise first: this document names live
> Azure resources, a `set_manager_role` auth hole, and committed credentials, all
> as of 2026-06-09. Those facts are 50 days stale and some are security-relevant.
> Row 1 in particular (rotate P0 creds) should be re-checked against the live
> estate before it is either worked or dropped, and it is out of lane B.
>
> Context for why this sat: `docs/reflections/2026-07-29-what-is-going-wrong.md`.

Single source of truth. Merges four reports (work them top-down):
- A — CJA rescue: `projects/campaign-analysis/docs/CJA-REQUIREMENT-OF-RECORD.md`
- B1 — Stack modernization + hive: `docs/audits/2026-06-09-stack-modernization-and-hive-upgrade.md`
- B2 — Agent shell + MCP: `docs/audits/2026-06-09-agent-shell-and-mcp-layer.md`
- C — Autonomous Azure fleet: `docs/2026-06-09-autonomous-azure-agent-fleet-design.md`
- Learning: `docs/ai-103-study-tracker.md` + `docs/fundamentals-mastery-plan.md`

Owner: **me** = Claude can do it; **you** = needs Shoval (rotate live secrets, Azure portal, exam). Effort S/M/L. Risk low/med/high.

## DO NOT ADOPT (decision-rules confirmed)
- ❌ Kubernetes / AKS — ACA covers it; AKS = ~$70–150/mo, zero benefit.
- ❌ Terraform — Bicep + AVM wins for an Azure-only shop.
- ❌ Self-hosted Grafana / Managed Prometheus — App Insights via OTel Distro is the correct default; Prometheus only justified on AKS/Arc/high-cardinality (none apply).
- ❌ `@modelcontextprotocol/server-postgres` — confirmed read-only-bypass; and no active Postgres source anyway.
- ❌ Blanket `polars` / blanket CLI-map adoption — use surgically (see below).

## Tier 0 — DO NOW (safe, mostly config-only, today)
| # | Action | Owner | Effort | Risk | Src |
|---|---|---|---|---|---|
| 1 | **Rotate + fix P0 creds:** training-platform `set_manager_role` unauth + committed admin pwd + test cred; SIU JWT fallback. Rotate live secrets, add auth guard, → KV. | you+me | S | — | B1 |
| 2 | **Wire dead hive hooks** — `settings.json` `UserPromptSubmit`=[] (line 60) + `PostToolUse`=[] (line 125). Restores voice/visual/meme. | me | S | low | B1 |
| 3 | **Agent env: `NO_COLOR=1` + `PAGER=cat` + `GIT_PAGER=cat`** — kills ANSI token waste fleet-wide, zero install. | me | S | low | B2 |
| 4 | **Populate `~/.config/rtk/filters.toml`** with `az` / `func` / `pytest` / `ruff` filters (noisiest token sources). | me | S | low | B2 |
| 5 | **Security baseline P0:** Entra Agent ID per agent, scoped *data-plane* RBAC (never Contributor/Owner), Key Vault references. | you+me | S | low | C |
| 6 | Remove `cs-agent-main` hardcoded CRM IP default → fail-fast on unset. | me | S | low | B1 |
| 7 | Archive `video-generations` (dead duplicate of `video-understanding`). | you | S | low | B1 |

## Tier 1 — Cross-project standard (the modernization spine)
| # | Action | Owner | Effort | Risk | Src |
|---|---|---|---|---|---|
| 8 | **Secretless CI/CD → Workload Identity Federation** on every ADO pipeline (only training-platform has it). Use the 7-day-revert conversion tool; scope UAMI to RG. | you+me | M | med | B1 |
| 9 | **Observability: `azure-monitor-opentelemetry` + `structlog`** everywhere (near-zero today; opencensus dead in cs-agent-main). | me | M | low | B1/C |
| 10 | **Container hardening:** `uv` multi-stage + non-root + Trivy scan gate + SBOM on all Dockerfiles. | me | M | med | B1 |
| 11 | **IaC: Bicep + AVM + `what-if` PR gate + Deployment Stacks**; replace `listKeys`/root-key outputs with MI. | me | L | med | B1 |
| 12 | **Library map, surgically:** `orjson` hot paths · `pandera`/`pydantic` at data boundaries · `hypothesis` property tests · `instructor` typed extraction · `polars` ONLY where datasets warrant. (`uv` mostly done — keep `requirements.txt` for Functions remote build.) | me | M | low | B1 |
| 13 | Make non-blocking test/audit gates **blocking** (pip-audit `continueOnError`, `|| true`, manual eval gates). | me | S | low | B1 |

## Tier 2 — Autonomous fleet (move off the laptop)
| # | Action | Owner | Effort | Risk | Src |
|---|---|---|---|---|---|
| 14 | **Lift the Jira+Azure digest to an ACA Job** (cron `0 4,13 * * 0-4`), swap `az login`→Managed Identity, `azure-monitor-query`/`keyvault` SDKs. The missing "Azure+Jira report" as a first-class job. | me | M | med | C |
| 15 | **Brevo SMTP → Graph `sendMail`** (kills a 3rd-party secret). | me | S | low | C |
| 16 | **Beads → Azure Table Storage** so the bus survives laptop-off (currently 1 local SQLite, no replica; 67/70 beads stale-open). | me | M | med | B1/C |
| 17 | Phase the rest of the Codex automations → per-rig ACA Jobs (Blob-lease mutex). | me | L | med | C |
| 18 | **Persona roster** extending Hive roles — global: red-teamer · premortem · completeness · consistency · security · cost-watchdog · LTMD; project: CRM-guard · ground-truth-judge · blast-radius. (Session-scoped = subagents, NOT Azure-hosted.) | me | M | low | C |
| 19 | Security P1 (before any agent is hosted): Prompt Shield, MCP pinning, tiered HITL gates, Log Analytics audit. | me | L | med | C |

## Tier 3 — Hive skills + MCP + CLI tooling
| # | Action | Owner | Effort | Risk | Src |
|---|---|---|---|---|---|
| 20 | **CJA-failure cure skills:** `requirement-anchor` · `context-bounded-analyst` · `decision-grade` linter · `pii-scrubber` hook. | me | M | low | A/B1 |
| 21 | **Infra skills:** `kv-health` · `secretless-pipeline` · `aca-job-deploy` · `mcp-supply-chain-pin`. | me | M | low | B1/C |
| 22 | **Add MCP servers (read-only first, secrets via env/KV):** Azure MCP (`microsoft/mcp`, Reader), GitHub (fine-grained read PAT), Azure DevOps (remote+Entra), Sentry (org:read OAuth), Context7 (maxTokens=3000). | you+me | M | low | B2 |
| 23 | **Install dual-use CLIs via `mise`:** `sd` (import migrations), `mlr` (eval-CSV/cost aggregation), `hyperfine` (perf-regression loops). | me | S | low | B2 |
| 24 | **rtk-first "Agent Shell Defaults" block** into CLAUDE.md; human-only TUI tools (eza/bat/delta/fzf/zoxide/atuin/btop/yazi/zellij/broot) installed but NEVER agent-invoked. | me | S | low | B2 |

## Tier 4 — You (career / independence)
| # | Action | Owner | Effort | Risk | Src |
|---|---|---|---|---|---|
| 25 | **Claim AI Skills Fest voucher (by June 12)** → spend on **AI-103**. | you | S | — | Learning |
| 26 | AI-103 ramp (1 hr/day) + **fundamentals discipline** (predict-then-verify, review-me-like-a-PR). | you | L | — | Learning |

## Verified this session (not just agent claims)
- P0 creds: `set_manager_role` + `JWT_SECRET` files confirmed present (host grep).
- Hive hooks empty: `settings.json:60,125` confirmed.
- CJA workbook on leaky `scores_v2` confirmed (`seekapa_deliverable.py:31`).
- No dead `webhook.office.com` URLs (clean).
- Map corrections: ripgrep 1.9–36× (not 10–50×); `sd` 2–11× workload-specific; `xh` vs HTTPie not curl.
