# Master Implementation Plan — what I build on "go"

Distilled from the whole session. Source docs: the four research reports + the consolidated
adopt-backlog (`2026-06-09-CONSOLIDATED-adopt-backlog.md`) + the CJA anchor + the learning trackers.

## Guardrails I will honor (your corrections, this session)
- **Model-tiered swarms:** haiku for mechanical/inventory, sonnet for research/audit/query, Opus only for synthesis/assembly. **One workflow at a time**, persist to disk, resume on any limit.
- **No new Azure resources / MCP / service connections / Entra apps Yasha would flag** — reuse existing: `az` CLI, typed SDKs, pipeline `System.AccessToken`, existing managed identities, permission toggles on existing identities.
- **No raw REST** — typed SDK (`azure-devops`, `azure.identity`) or `az devops invoke`.
- **"go" pre-authorizes the existing-code edits we discussed.** I still ask per-action for genuinely destructive ops (deleting a repo, dropping data, force-push, rotating live secrets).
- **Never** `git add` at `$HOME`; **no auto commit/push/deploy** — I edit the working tree + run gates; you ship via `/commit-push-pr`.
- **PII/secrets:** never read/echo; mask at the boundary; pre-write grep gate. Security findings are top priority.
- **Decision-grade output (LTMD):** number + provenance + what-it-means + one owned/dated action.
- **Learning mode:** where something is a learning rep, I teach Socratically (predict-then-verify), not hand-the-answer.
- **Verify, don't trust:** I review my own + subagent output adversarially before shipping (this session: caught the `scores_v2` leakage, the phantom `az repos pr comment`, the artifact-vs-comment gap).

## What stays YOURS (I can't / shouldn't)
1. Claim the **AI Skills Fest voucher by June 12** → spend on AI-103.
2. **Rotate live secrets** (training-platform admin pwd + test cred; SIU JWT) after I fix the code.
3. **Portal toggles:** Build Service "Contribute to pull requests"; service connection "Azure AI Developer" on `seekapa_ai`; branch-policy "Build Validation = Required".
4. Approve any new Azure resource **if** one becomes genuinely unavoidable (I'll flag + offer a no-new-resource alt first).
5. Decide whether to install the CLI tools (`mise`) — it's a machine change.
6. Commit/push/merge decisions.

---

## PHASE 1 — high-value, on "go" (main-loop edits + one model-tiered workflow)

### WS0 — Hive quick wins (config, fast, restores broken features)
- Wire `UserPromptSubmit` + `PostToolUse` in `~/.claude/settings.json` (verified empty at lines 60/125 — your voice/visual/meme have been silently dead). I verify the trigger script paths first.
- Set agent env `NO_COLOR=1` + `PAGER=cat` + `GIT_PAGER=cat`.
- Populate `~/.config/rtk/filters.toml` (az/func/pytest/ruff/bicep/azd/mypy/bun-test).

### WS-A — CJA analytics rescue (urgent, boss-facing)
- **A1 (additive):** DuckDB/Polars **catalog** over `scores_v3` + telephony + manifest → `outputs/_catalog/`. The context-room fix (query the catalog, not 146 xlsx).
- **A2 (edit existing — pre-authorized by "go"):** repoint `seekapa_deliverable.py:31` `scores_v2 → scores_v3`; add `agents.csv` PII masking at the boundary; add a pre-write PII grep gate.
- **A3 (model-tiered workflow):** answer the 6 on-disk questions (Q3/4/5/7/9/10) decision-grade → adversarial verify each number → assemble `outputs/<date>/deliverable/CJA-12-answers.md` + rebuild the workbook on v3. Q1/2/6/8/11 stubbed (CRM-join-pending); Q12 LTV = DIRECTIONAL.
- **A4:** visually read the 2 email PNG screenshots to confirm I'm answering the current ask.

### WS-PR — PR-precheck `/review` skill (Tier-2 core; no MCP, no new resource, no raw REST)
- Read `codex_pr_review.py` → lift its working `DefaultAzureCredential` auth.
- Build `/review` skill: composes **`codex` review (codex-call) + `testing-pyramid` on the diff + `/heidegger-reflect`** → one structured body. Per-project `projects.json`. Runs local + CI.
- Delivery via **`azure-devops` SDK `GitClient.create_thread()`** (or `az devops invoke`), authed with `System.AccessToken` (CI) / your PAT (local).
- Create `work-item.sh` (threads-based via SDK/CLI — not the phantom `az repos pr comment`).
- Stage the `AIPRReview` job back into `cs-agent-main/azure-pipelines.yml` (persistCredentials + token env); retire the artifact-only publish.

### WS-SEC — Security P0 (prep code; you rotate)
- training-platform: remove 3 hardcoded literals → KV/env refs; add auth guard on `set_manager_role`; drop localhost from prod CORS.
- SIU: JWT fallback → crash-on-unset, wire `kv-siu-prod`.
- cs-agent-main: remove hardcoded CRM IP default → fail-fast.

### WS-SKILLS — top new skills (additive)
- `requirement-anchor`, `context-bounded-analyst`, `decision-grade` linter, `pii-scrubber` hook (the CJA-failure cure).
- `azure-cert-coach` (AI-103 ramp + voucher path + Socratic drills tied to `/grill-me`).

---

## PHASE 2 — staged (sequenced, model-tiered swarm per batch; checkpoint between)

### WS-STD — per-project standards rollout (the modernization spine, 10 projects)
Per project, in priority order: secretless CI/CD (WIF) · observability (`azure-monitor-opentelemetry` + `structlog`) · container hardening (uv multi-stage + non-root + Trivy) · Bicep+AVM + `what-if` PR gate · library map applied (`orjson` hot paths, `pandera`/`hypothesis` at boundaries, `polars` only >100MB, **remove unused pandas/sklearn**) · pip→uv where still pip. (Specifics per project from B1 §4.)
- Project-specific notables: campaign-analysis **pandas-import bug**; qc **replace `unittest.mock` with VCR**; compliance-exam **add tests (currently 0) + activate declared-but-unwired structlog**; archive **video-generations** (your OK).

### WS-FLEET — autonomous Azure agent fleet (Tier 2 build, after PR-precheck proves the pattern)
- Lift the Jira+Azure digest to an **ACA Job** (az login → Managed Identity; beads → Azure Table Storage).
- **Graph `sendMail`** "work done" digest (replaces Brevo SMTP).
- Persona roster as **subagents** (red-teamer/premortem/completeness/consistency/security/cost/LTMD; project: CRM-guard/ground-truth-judge/blast-radius) extending the Hive roles.
- Security baseline P0/P1 as config.
- Infra skills: `kv-health`, `secretless-pipeline`, `aca-job-deploy`.

---

## PHASE 3 — ongoing
- Agent-shell tooling: `mise` install of `sd`/`mlr`/`hyperfine` (agent-safe) + human tools; rtk-first "Agent Shell Defaults" block into CLAUDE.md (on your OK to install).
- Learning support: Socratic AI-103 + fundamentals reps (predict-then-verify, review-me-like-a-PR), `/grill-me` on the week's hardest concept.

---

## Execution mechanics
- "go" runs **Phase 1** in order: WS0 → WS-A → WS-PR → WS-SEC → WS-SKILLS. WS-A's A3 and any per-project work use model-tiered swarms, one at a time.
- I **checkpoint** after each workstream (show diffs, no commit/push) so you steer.
- Phase 2/3 are staged on later "go"s — I won't blast all 10 projects at once (cap + sequencing discipline).
- Nothing deploys, nothing rotates, nothing merges without your explicit action on the YOURS list.
