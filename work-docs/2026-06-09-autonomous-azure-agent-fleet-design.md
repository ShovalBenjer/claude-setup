# Autonomous Azure Agent Fleet — Design Doc

Date: 2026-06-09
Reader: Shoval
Status: decision-grade proposal

---

## Bottom line

Move the laptop-bound scheduled agents to **Azure Container Apps (ACA) Jobs** (cron) plus **Azure Functions Flex Consumption** where the code is already a Python Function. Cost is **~$0/month** within free tiers for a handful of daily jobs. Use **Managed Identity + Key Vault references** (no stored secrets), and send the daily digest via **Microsoft Graph `sendMail`** (drop Brevo SMTP). **AKS and an always-on orchestrator are overkill** for this workload — explicit no. Migrate in phases; do not boil the ocean.

Two changes are warranted **today regardless of hosting**: (1) replace Brevo SMTP with Graph `sendMail` (removes a third-party credential, stays Microsoft-native), and (2) verify no dead Office 365 connector webhook URLs remain in scripts (those connectors died 22 May 2026).

---

## 1. Current state

### What runs on the laptop today (from the audit)

All scheduling is **user crontab on WSL2** — no systemd timer, no cloud scheduler backs any of it.

| Job | Schedule (UTC) | IL time | What it does |
|---|---|---|---|
| `jira-reminder-refresh.py --monitoring` | `0 4 * * 0-4` | 07:00 (summer) | Combined Jira + Azure Monitor digest: Jira open tickets + AppInsights (4 components) + Storage metrics + Container App jobs + Activity Log → HTML email to shoval.be@i-sdd.com via Brevo SMTP |
| `jira-reminder-refresh.py` (no flag) | `0 13 * * 0-4` | 16:00 | Jira-only digest; emails only when tickets flagged |
| `a05-pst-email-action-mining` | `0 18 * * 1` | Mon 18:00 | Codex automation via `run-codex-automation.sh` |
| `a01-memory-curator-sweep` | `0 18 * * 0` | Sun 18:00 | Codex, high reasoning |
| `a09-forge-loop-compliance-score` | `0 18 * * 6` | Sat 18:00 | Codex, high reasoning |
| `a08-claudemd-drift-per-project` | `0 18 * * 2` | Tue 18:00 | Codex |
| `d05-hot-zone-indicator` | `0 18 * * 3` | Wed 18:00 | Codex |
| `archive_debug.sh` | `0 0 * * 0` | weekly | local maintenance |
| `wsl-guard.sh` | `*/5 * * * *` | — | WSL2-local health guard, meaningless off-laptop |

Supporting stack: **Hive bead bus** (`~/.hive/bin/hive.py`, SQLite `beads.db`, roles polecat/dogs/crew/witness/deacon, 4 active rigs in `rigs.yaml`), **27 Codex automation prompts** (a/c/d/n series, detect-only by design) run via `run-codex-automation.sh` (lock dir + log + last-message), and **session hooks** (SessionStart Jira banner, Stop worklog appender).

### What breaks when the laptop sleeps

Every scheduled job is silently dead while WSL2 is off. Concretely:

- **All cron fires miss** — no catch-up, no retry. A skipped 07:00 monitoring run just never happens.
- **`az login` token expiry** — `jira-reminder-refresh.py` reads JIRA-API-KEY + Brevo SMTP creds from KV `Shoval` via the `az` CLI refresh token. On expiry/offline it fails silently and writes `az-auth-needed.flag`; you only learn at the next interactive session via the SessionStart banner.
- **Codex CLI is a local process** — `run-codex-automation.sh` needs the WSL2 `codex` binary + network + key. No host = no automation.
- **`beads.db` is a single local SQLite file** — no replica. No bead can be created/claimed/closed while offline; the Hive bus is frozen.
- **Email transport is direct SMTP from WSL2** (port 587 → smtp-relay.brevo.com). No Azure relay or Logic App in between, so no host = no email.
- **PST pipeline + `wsl-guard.sh` are 100% laptop-bound** by definition.
- **Audit trail `~/.hive/audit.jsonl` is local-only** — no cloud sink, so off-laptop gaps are invisible after the fact.

### Key gap surfaced by the audit

There is **no dedicated scheduled Codex "Azure + Jira report" prompt**. The combined digest logic lives entirely inside `jira-reminder-refresh.py` (a raw Python cron job), so its findings **never enter the Hive bead bus** and are not surfaceable to other rig workers. The "Azure+Jira report" referenced in Codex memory (rollout 2026-06-01) was an ad-hoc session task, not a recurring automation.

---

## 2. Is moving to Azure going too far?

**Verdict: No — it is proportionate, provided you pick the right tier.** Going to AKS or an always-on orchestrator *would* be too far.

### Decision rule

1. **Agent is already a Python Azure Function** (e.g. the CS-agent / CRM stack) → **Azure Functions Flex Consumption + TimerTrigger** (NCRONTAB). Zero container packaging. Native Managed Identity + Key Vault references. Free tier (400K GB-s + 1M executions/month) absorbs the load. 2026 adds first-class Teams/Outlook agent triggers.
2. **Agent needs a container image** (Hive/Codex automations with non-Functions deps like the `codex` CLI) → **ACA Jobs (Consumption)** with cron schedule. ~$0/month within the free tier (180K vCPU-s + 360K GiB-s/month — a handful of daily 5-min jobs at 0.25 vCPU / 0.5 GiB uses ~11K vCPU-s). Bicep-native, same ADO CI/CD already in use, same `sentimarkregistry` ACR.
3. **Agent needs Foundry Toolbox (Code Interpreter / AI Search / MCP), managed thread history, or Teams publishing** → **Foundry Hosted Agents + Routines**. Integrates with existing `brn-azai` / `seekapa_ai`. ~$0.12/month compute + token cost. **Caveat: preview until ~July 2026; depend on it only after GA.**
4. **Agent must safely run AI-generated code mid-execution** → embed **ACA Dynamic Sessions** as a sub-step inside option 1 or 2. Never a standalone scheduler (no cron primitive, ephemeral, no persistent `$HOME`).
5. **Connector-heavy orchestration** (SAP/Salesforce/legacy) → Logic Apps. **Not our case** — WS1 is ~$180/month always-on, disproportionate for cron.
6. **AKS → never for this workload.** Minimum ~$70–150/month for one node, plus cluster lifecycle, for zero benefit at a handful of daily jobs. Official Microsoft guidance: use ACA unless you need direct Kubernetes API/control-plane access. We don't.

### Why proportionate

ACA Jobs / Functions at $0/month remove the laptop dependency, add Activity-Log + Log Analytics audit, replace laptop credential files with Managed Identity, and can emit the digest via Graph. The only added complexity is a container image or Function deploy — already the team's native pattern. The Codex automations are **stateless, read-only, detect-only by design** — the correct posture for cloud workers, with no session state to migrate.

### Where Azure is NOT worth it

Session-scoped roles (premortem, completeness critic, stakeholder lens, blast-radius estimator, ground-truth judge) add latency + cost if externalized. Run them as **synchronous subagents inside existing sessions**. Only roles needing 24/7 uptime or cross-session persistence (the digest, the cost watchdog enforcement layer, the security-auditor log) belong in Azure.

### Phased migration

**Phase 0 — unconditional, this week (no hosting change required)**
- Replace Brevo SMTP in `jira-reminder-refresh.py` with **Graph `sendMail`** from a shared mailbox (no extra Exchange license needed if one licensed user exists; grant `Mail.Send` to the identity via PowerShell, scoped via RBAC for Applications). Removes a rotating third-party secret.
- Grep `~/.codex` + `~/.claude/bin` for any `*.webhook.office.com` URLs; replace with a Power Automate Workflows "Send webhook alerts to a channel" URL (O365 connectors retired 22 May 2026).

**Phase 1 — lift the combined digest to ACA Jobs**
- Containerize the `jira-reminder-refresh.py --monitoring` logic. It is the **most Azure-ready component**: already calls AppInsights, Azure Monitor metrics, Container App jobs, Activity Log. Swap `az login` for `DefaultAzureCredential` (system-assigned MI) and KV reads from `az` subprocess to the MSI-authenticated SDK (`azure-monitor-query`, `azure-keyvault-secrets`).
- Deploy as an ACA Job, cron `0 4,13 * * 0-4` UTC, MI granted `Key Vault Secrets User` + reader on the monitored resources. **This is the missing "Azure + Jira report" as a first-class scheduled job.**
- Make it **emit a Hive bead** on threshold (per `_bead-emit-appendix.md`), so findings enter the bus. Beads move from local SQLite to **Azure Table Storage** (or Cosmos Table API) so the bus survives laptop-off.

**Phase 2 — daily "work done" digest emailed to Shoval**
- Extend the job to compose a daily "work done" summary: closed beads, merged ADO PRs (reuse `a11` logic), eval gate status, automation last-message highlights → Graph `sendMail` HTML to shoval.be@i-sdd.com.
- Build directly on Codex's existing Azure+Jira investigation output as the data source.

**Phase 3 — Jira (09:00/16:00) + Teams integration**
- Keep the **pull model** (job polls Jira REST v3 via JQL, API token from KV) — no Jira admin rights needed; heavy logic stays in the job, not in Jira rules.
- Post a compact **Adaptive Card** summary to a Teams channel — prefer **Graph `POST /teams/{id}/channels/{id}/messages`** (`ChannelMessage.Send`, durable, no orphan-flow risk) over the Workflows webhook (tied to a user identity, orphans if they leave).
- The 09:00 run stays the full monitoring digest; 16:00 stays Jira-only-when-flagged.

**Phase 4 — migrate remaining Codex automations rig-by-rig**
- Each Codex automation prompt → one ACA Job (KEDA cron). The 4-rig `rigs.yaml` routing maps cleanly to 4 ACA Job sets, each with a per-rig MI scoped to that rig's resource group + ADO repo. Move the lock-dir mutex to a **Blob lease** for multi-instance safety.

---

## 3. Agent persona roster

State of the art (2026) has moved past the orchestrator/worker binary to 4–8 role classes. The most under-deployed class is the **adversarial layer**. Map these onto the existing Hive roles so the fleet **extends, not replaces**:

- **polecat** = orchestrator/lead (assigns, routes)
- **dogs** = workers (do the task)
- **witness** = observer/critic (the natural home for completeness + consistency + stakeholder-lens roles)
- **deacon** = gatekeeper/approver (the natural home for premortem gate + HITL approval + blast-radius)
- *(crew = generic worker, valid in `hive.py` but unused in rigs)*

### GLOBAL personas (cross-project, wired into the orchestrator harness)

| Persona | Maps to | Purpose | Trigger |
|---|---|---|---|
| **Adversarial Verifier (Red-Teamer)** | witness | Assume the artifact already failed; output the 3 most likely failure vectors as falsifiable risk statements (Tiger / Paper-Tiger / Elephant). Never proposes fixes. | After any plan, PR, or architecture draft |
| **Premortem Gate** | deacon | Two-pass risk classification before any merge/deploy/stakeholder send; emits a signed checklist, not prose. | `/premortem` or pre-ship hook |
| **Completeness Critic** | witness | After synthesis: are all stated requirements addressed, edge cases named, assumptions explicit? Outputs a gap list, not a rewrite. | After any synthesis/summarization step |
| **Security Auditor** | witness | Check tool calls / MCP / inter-agent messages against the v2.0 failure-mode taxonomy; emit SBOM-style note with P0/P1/P2 severity. Flags, does not block. | Any action involving tool invocation or external data |
| **Cost Watchdog** | *infra middleware (not a chat agent)* | Per-session + fleet-level token ceilings + synchronous circuit breaker; emits cost telemetry per invocation. | Every agent spawn |
| **Stakeholder Lens** | witness/deacon | Re-read stakeholder-facing output: bottom line first? exactly one action? jargon defined? Rewrites only if 2+ criteria fail. (= the LTMD / Liron lens.) | Any output flagged stakeholder-facing |
| **Consistency Analyzer** | witness | After multi-step chains: are conclusions still entailed by earlier evidence? Output a claim → evidence provenance trace. | Long outputs citing prior agent steps (eval pipelines, Jira reports) |

### PROJECT-level personas (load on demand via skill/agent-skill pattern)

| Persona | Rig | Maps to | Purpose | Trigger |
|---|---|---|---|---|
| **Compliance & Allowlist Guard** | cs-agent | deacon | Check every CRM query against the allowlist before execution; strip internal identifiers (crm_client_source, queue names) from customer-facing output. | Every CRM API call + every customer-facing message gen |
| **Ground-Truth Judge** | campaign-analysis / eval | witness | Classify (prediction, ground_truth) → pass/fail + confidence + failure category, using a *different* model family (grok-4-1-fast primary, DeepSeek-V3.2 audit). Classifies only; never re-ranks. | Every eval row scored |
| **Blast-Radius Estimator** | all infra-touching | deacon | Before any `az`/Bicep write: list resources sharing a dependency, classify reversible/irreversible, emit tier-1/2/3 approval request showing the raw operation. Does not block. | Any Bash command touching `az` CLI or Bicep deploy |

Rationale for routing: a persona is **GLOBAL** if it fires on artifacts from any project (adversarial, premortem, completeness, security, cost, stakeholder, consistency). It is **PROJECT-level** if its correctness needs domain knowledge (CRM allowlist, eval rubric, infra blast-radius rules). **Cost Watchdog is the exception**: global in scope but implemented as infra middleware, not a conversational agent.

---

## 4. Self-adoptable security baseline checklist (prioritized)

Adopt in order. P0 = config-only, near-zero cost, largest blast-radius reduction — do today. P1 = active threat mitigations — before any agent goes Azure-hosted. P2 = defense-in-depth — defer for dev, do for prod.

**P0 (do today, config-only)**
- [ ] **Distinct Entra Agent ID per published agent** via federated credential trust (blueprint → agent identity → scoped token). No client secrets/certs anywhere. Assign roles to `agentIdentityId`, never to the bare MI. Dev agents share the project identity; publish to prod for a separate audit trail.
- [ ] **Least-privilege scoped RBAC** — data-plane roles only (Cognitive Services OpenAI User, Storage Blob Data Reader/Contributor, Cosmos DB Built-in Data Reader). **Never Contributor/Owner on an agent identity.** Scope to the resource, not the subscription. Audit with `az role assignment list --assignee <agentIdentityId>`.
- [ ] **Key Vault references for all secrets** — `@Microsoft.KeyVault(SecretUri=...)` in app settings; MI granted `Key Vault Secrets User` (RBAC is default for new vaults). Enable soft-delete + purge protection. Never read/echo/log secret values.

**P1 (before any agent is Azure-hosted)**
- [ ] **Prompt-injection / tool-poisoning defenses (layered)** — (1) Content Safety Prompt Shield on every ingress; (2) spotlighting: wrap retrieved content in randomized delimiters marked data-only; (3) Rule of Two: no single agent simultaneously processes untrusted input AND touches sensitive systems AND mutates external state without human approval; (4) strip Unicode Tag chars (U+E0000–U+E007F) + Markdown image syntax from outputs; (5) mTLS + signed payloads between agents.
- [ ] **MCP supply-chain controls** — pin every MCP server to exact version + SHA-256; allowlist approved servers, block all others; scan tool descriptions for instruction-like imperatives; run SBOM (Trivy/Syft) on MCP containers in CI; add MCP config paths to the ADO PR review gate.
- [ ] **HITL approval gates, tiered** — Tier 1-2 autonomous + logged; Tier 3 async Teams adaptive-card approval w/ timeout-to-reject; Tier 4 (branch delete, force-push, DB mutation, email/Teams send, third-party publish, Azure resource change) always explicit per-action, showing the **raw operation** (exact CLI/HTTP), not a summary. Fits the deacon role + existing bead bus.
- [ ] **Audit logging** — diagnostic settings (Audit/RequestResponse/Trace) → Log Analytics; App Insights auto-instrumentation per agent; Azure Monitor KQL alerts for (a) tool calls to non-allowlisted domains from sessions handling untrusted content, (b) p99 latency spikes, (c) agent-identity auth failures → Sentinel. Never log raw secrets or PII-bearing prompts.

**P2 (prod hardening, deferrable)**
- [ ] **Network isolation** — private endpoints on Foundry/OpenAI (disable public), VNet integration for Functions/ACA, egress FQDN allowlist via Azure Firewall/NAT (~$30/month), Private DNS zones. Egress allowlisting is the strongest single anti-exfiltration control — works even when injection succeeds.
- [ ] **DLP + output filtering** — Purview DLP on AI interactions (block PAN/national-ID/internal project names), sensitivity labels on sources, Azure OpenAI output content filtering (free), **Defender for Cloud AI threat protection** (highest-leverage single toggle for a solo operator), Purview Insider Risk "Risky AI usage" template.

---

## 5. Azure cert / free-learning plan (DP-700)

**Target: DP-700 (Fabric Data Engineer Associate).** Active and current (skills updated 2026-04-20). 100 min, pass at 700/1000, Microsoft Learn split-screen allowed. Three equally-weighted domains (30–35% each): implement/manage analytics solution; ingest/transform data; monitor/optimize.

### Free Fabric practice (no org capacity needed)

- **Path A (recommended) — personal-email Fabric trial.** Sign in to `app.fabric.microsoft.com` with a personal Outlook/Gmail account → Azure free account → Entra ID user → activate the **60-day trial** from the profile menu. Gives F4/F64 capacity, 1 TB OneLake, all workloads (Data Factory, Synapse Data Engineering, Real-Time Intelligence, Power BI). No credit-card charge unless you explicitly upgrade. (Copilot + Private Link not in trial — not on DP-700.)
- **Path B — M365 Developer Program sandbox** (E5, 90-day renewable, Power BI Pro). Caveat: Fabric trials are now restricted on tenants under 90 days old — establish the dev tenant first, age it, then activate Fabric.
- **Path C — FAIAD (Fabric Analyst in a Day) workshop** — free Microsoft-led one-day hands-on lab; uses a shared environment, so no personal capacity needed.

### Free-exam voucher path — TIME-CRITICAL

- **AI Skills Fest 2026** ran **8–12 June 2026**. To get a 100% free PearsonVue voucher (broadly eligible incl. DP-700; Certiport/MOS excluded): register at `aiskillsnavigator.microsoft.com/events/AISF2026`, complete one eligible skilling playlist fully during the window, then **submit the voucher claim form (mandatory — not auto-issued) by 12 June 2026 00:00 UTC.** Then redeem (schedule) by 18 Aug 2026, take the exam by 18 Oct 2026.
- **Today is 9 June — the claim window closes in ~3 days. This is the single highest-urgency item in this doc.**
- **Do NOT confuse with the Microsoft Credentials AI Challenge** (Jan–Mar 2026, now closed) — that was 50% off AB-730/731/900 only; DP-700 was never eligible.
- *Unverified:* DP-700 eligibility for the AISF voucher is sourced from a third-party aggregator (msfthub.com); some community posts suggest a lottery element. Treat DP-700 eligibility as **likely but unconfirmed** — complete the playlist + claim form anyway since it costs only 2–4h.

### Ordered DP-700 ramp (for someone who struggled on 6 questions)

Hardest areas without hands-on Fabric: **Real-Time Intelligence/KQL, Eventstreams, OneLake shortcuts, streaming ingestion pattern selection, Lakehouse optimization, monitoring/alerting.** All free, labs on the 60-day trial:

1. **"Get started with Microsoft Fabric"** learning path (8 modules, beginner; Lakehouse/Warehouse/RTI/SQL) — hands-on each module.
2. **"Get started with Real-Time Intelligence"** module — Eventstreams, KQL DBs, Eventhouses. Do the lab.
3. **"Create and manage OneLake shortcuts"** standalone module — community flags this as a question cluster.
4. **"Implement data engineering solutions using Microsoft Fabric"** (DP-700T00 course, 6 paths: ingest, lakehouse, real-time analytics, warehouses, manage environment, Activator).
5. **Official free DP-700 practice assessment** (linked from cert page) — find remaining gaps.
6. **Exam sandbox** (`aka.ms/examdemo`) — get used to interactive question formats.
7. **FAIAD workshop** — end-to-end reinforcement, no personal capacity needed.

Estimated 40–60h total, all free.

---

## 6. Ranked next actions

Effort: S (<1d) / M (1–3d) / L (>3d). Impact: how much it removes laptop fragility / risk.

| # | Action | Effort | Impact | New skill? |
|---|---|---|---|---|
| 1 | **Claim the AI Skills Fest free voucher** (complete a playlist + submit claim form before 12 Jun 00:00 UTC) | S | High (closes tomorrow) | — |
| 2 | **P0 security baseline** (Entra Agent ID, scoped RBAC, KV references) — config-only, today | S | High (biggest blast-radius cut) | extend existing `azure-keyvault-secrets` skill |
| 3 | **Phase 0: swap Brevo SMTP → Graph `sendMail`** + grep/replace dead O365 webhook URLs | S | Med-High (removes 3rd-party secret) | — |
| 4 | **Phase 1: containerize the combined digest as an ACA Job** w/ MI + KV, cron `0 4,13 * * 0-4`, emit Hive beads to Table Storage | M | High (removes laptop dependency for the most-used job) | **new GLOBAL skill: `aca-job-deploy`** |
| 5 | **Phase 2: daily "work done" digest** (closed beads + merged PRs + eval status → Graph email) | M | Med-High | extend #4 |
| 6 | **Phase 3: Jira(09/16) + Teams Adaptive Card** via Graph channel message | M | Med | extend #4 |
| 7 | **Wire GLOBAL personas as subagents** (red-teamer, premortem gate, completeness, consistency) into the orchestrator harness | M | Med | **new GLOBAL skills** (premortem already exists; add red-teamer/completeness/consistency) |
| 8 | **Cost Watchdog as infra middleware** (per-session + fleet token ceilings, sync circuit breaker) | M | Med-High (prevents runaway invoices) | **new GLOBAL skill/middleware** |
| 9 | **P1 security** (Prompt Shield, MCP pinning, HITL tiers, Log Analytics) before any agent goes hosted | L | High | **new GLOBAL skill: `mcp-supply-chain-pin`**; extend project skills |
| 10 | **DP-700 ramp** (steps 1–7) on the free Fabric trial | L | Med (career) | — |
| 11 | **Project personas** (CRM allowlist guard, ground-truth judge, blast-radius estimator) | M | Med | **PROJECT skills** per rig |
| 12 | **Phase 4: remaining Codex automations → per-rig ACA Jobs** w/ Blob-lease mutex | L | Med (full laptop independence) | extend #4 |

**New GLOBAL skills:** `aca-job-deploy`, `mcp-supply-chain-pin`, Cost-Watchdog middleware, plus persona skills (red-teamer / completeness-critic / consistency-analyzer; premortem + LTMD already exist).
**New PROJECT skills:** CRM Compliance Guard (cs-agent), Ground-Truth Judge (campaign-analysis/eval), Blast-Radius Estimator (infra-touching rigs).

---

## 7. References

**Azure hosting / cron agents**
- Jobs in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/jobs
- Billing in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/billing
- Comparing Container Apps with other Azure container options — https://learn.microsoft.com/en-us/azure/container-apps/compare-options
- Azure Functions at Build 2026 Update — https://techcommunity.microsoft.com/blog/appsonazureblog/azure-functions-at-build-2026-update/4524075
- Estimating consumption-based costs in Azure Functions — https://learn.microsoft.com/en-us/azure/azure-functions/functions-consumption-costs
- Timer trigger for Azure Functions — https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer
- Azure Functions Pricing — https://azure.microsoft.com/en-us/pricing/details/functions/
- Hosted agents in Foundry Agent Service (preview) — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents
- Foundry Agent Service at Build 2026 — https://devblogs.microsoft.com/foundry/agent-service-build2026/
- Foundry Agent Service Pricing — https://azure.microsoft.com/en-us/pricing/details/foundry-agent-service/
- Dynamic sessions in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/sessions
- What's new in Azure Logic Apps at Build 2026 — https://techcommunity.microsoft.com/blog/integrationsonazureblog/whats-new-in-azure-logic-apps-at-microsoft-build-2026/4524685
- ACA vs AKS: The 2026 Decision Matrix — https://www.dataa.dev/2026/05/08/azure-container-apps-vs-aks-the-2026-decision-matrix/
- Comparing AKS with Other Azure Container Options — https://learn.microsoft.com/en-us/azure/aks/compare-container-options-with-aks

**Reporting / email / Teams / Jira integration**
- Choosing the right Azure hosting model for AI agents — https://devblogs.microsoft.com/all-things-azure/hostedagent/
- user: sendMail (Graph v1.0) — https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0
- Managed identity to send email via Graph — https://learn.microsoft.com/en-us/answers/questions/5657693/how-to-use-azure-manage-identity-to-send-out-email
- Mail.Send RBAC for Applications — https://office365itpros.com/2026/02/17/mail-send-rbac-for-applications/
- ACS Email overview — https://learn.microsoft.com/en-us/azure/communication-services/concepts/email/email-overview
- ACS Email pricing — https://learn.microsoft.com/en-us/azure/communication-services/concepts/email-pricing
- Retirement of Office 365 connectors within Microsoft Teams — https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/
- Create an Incoming Webhook (Teams, Workflows template) — https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
- Teams messaging APIs in Microsoft Graph — https://learn.microsoft.com/en-us/graph/teams-messaging-overview
- Jira Cloud platform REST API v3 — https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
- Jira automation triggers (Scheduled/Cron) — https://support.atlassian.com/cloud-automation/docs/jira-automation-triggers/
- Python timer-trigger sample (azd + MI) — https://learn.microsoft.com/en-us/samples/azure-samples/functions-quickstart-python-azd-timer/starter-timer-trigger-python/

**Agent personas**
- Building Effective AI Agents (Anthropic) — https://www.anthropic.com/research/building-effective-agents
- How we built our multi-agent research system (Anthropic) — https://www.anthropic.com/engineering/multi-agent-research-system
- Building agents with the Claude Agent SDK — https://claude.com/blog/building-agents-with-the-claude-agent-sdk
- NIST AI Agent Red-Teaming Standards (CSA) — https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-red-teaming-standards-202603/
- Pre-mortem agent skill — https://explainx.ai/blog/premortem-agent-skill-risk-review-parcadei-2026
- Designing Agent Personas That Actually Work — https://agenticthinking.ai/blog/agent-personas/
- Courtroom-Style Multi-Agent Debate (PROClaim, arXiv 2603.28488) — https://arxiv.org/html/2603.28488v1
- Open Challenges in Multi-Agent Security (arXiv 2505.02077) — https://arxiv.org/html/2505.02077v2
- AI Agent Token Budget Enforcement 2026 (Waxell) — https://waxell.ai/blog/ai-agent-token-budget-enforcement
- Rethinking AI Agents: A Principal-Agent Perspective (CMR Berkeley) — https://cmr.berkeley.edu/2025/07/rethinking-ai-agents-a-principal-agent-perspective/
- Agent Architecture Patterns: 2026 taxonomy (Digital Applied) — https://www.digitalapplied.com/blog/agent-architecture-patterns-taxonomy-2026

**Security baseline**
- Updating the taxonomy of failure modes in agentic AI systems (Microsoft, Jun 2026) — https://www.microsoft.com/en-us/security/blog/2026/06/04/updating-taxonomy-failure-modes-agentic-ai-systems-year-red-teaming-taught-us/
- Agent identity concepts in Microsoft Foundry — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-identity
- Azure AI security best practices — https://learn.microsoft.com/en-us/azure/security/fundamentals/ai-security-best-practices
- Governance and security for AI agents (CAF) — https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/governance-security-across-organization
- RBAC for Microsoft Foundry — https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry
- Key Vault References as App Settings — https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references
- Grant app access to Key Vault via Azure RBAC — https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide
- Indirect Prompt Injection: 2026 State of the Art (Zylos) — https://zylos.ai/research/2026-04-12-indirect-prompt-injection-defenses-agents-untrusted-content/
- Prompt Injection Defense for Production AI Agents (Maxim) — https://www.getmaxim.ai/articles/prompt-injection-defense-for-production-ai-agents-a-complete-2026-guide/
- MCP Security Best Practices 2026 (Practical DevSecOps) — https://www.practical-devsecops.com/mcp-security-best-practices/
- State of MCP Security 2026 (PipeLab) — https://pipelab.org/blog/state-of-mcp-security-2026/
- MCP Server Security: Threat Model (General Analysis) — https://generalanalysis.com/guides/mcp-server-security
- Tool approval / human in the loop (Agent Framework) — https://learn.microsoft.com/en-us/agent-framework/agents/tools/tool-approval
- Monitor Foundry Agent Service with Azure Monitor — https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/metrics
- How to configure network isolation for Microsoft Foundry — https://learn.microsoft.com/en-us/azure/foundry/how-to/configure-private-link

**Cert / free-learning**
- Fabric Data Engineer Associate (DP-700) cert — https://learn.microsoft.com/en-us/credentials/certifications/fabric-data-engineer-associate/
- DP-700 Study Guide (Apr 2026) — https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/dp-700
- Fabric trial capacity (60-day, F4/F64, 1TB) — https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial
- Start a Fabric free trial with a personal email — https://learn.microsoft.com/en-us/fabric/fundamentals/free-trial-account-personal-email
- M365 Developer Program FAQ — https://learn.microsoft.com/en-us/office/developer-program/microsoft-365-developer-program-faq
- AI Skills Fest 2026 event page — https://aiskillsnavigator.microsoft.com/events/AISF2026
- Free voucher: AI Skills Fest 2026 (VladTalksTech) — https://vladtalkstech.com/microsoft-learning-and-credential-news/free-microsoft-certification-voucher-ai-skills-fest/
- AI Skills Fest voucher details (msfthub) — https://msfthub.com/vouchers/aiskillsfest/
- Get started with Microsoft Fabric (learning path) — https://learn.microsoft.com/en-us/training/paths/get-started-fabric/
- Course DP-700T00-A — https://learn.microsoft.com/en-us/training/courses/dp-700t00
- Create and manage OneLake shortcuts (DP-700 prep) — https://thedatacommunity.org/2026/06/03/create-and-manage-onelake-shortcuts-dp-700-exam-prep/
- Microsoft Credentials AI Challenge (closed) — https://learn.microsoft.com/en-us/credentials/microsoft-credentials-ai-challenge

### Unverified claims (carried from research — verify before depending)
- DP-700 eligibility for the AI Skills Fest voucher (third-party aggregator; possible lottery element).
- Foundry Hosted Agents / Routines billing + GA date (~July 2026 preview).
- O365 connector retirement enforcement date may vary by tenant (phased rollout).
- ACS Email $0.00025/email — verify against current pricing calculator.
- M365 dev-tenant <90-day Fabric-trial restriction — community-reported, not in official docs.
