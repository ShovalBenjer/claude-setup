# Auto-Mode Task Backlog — 2026-05-12

Compiled from recent .md/.txt sources, eval runs, and the OTP QA suite. Every task lists its provenance + a concrete done-condition. Priority groups are independent of each other.

## P0 — Today, blocking

### T01. Training Platform PROD restore (HTTP 403 since 2026-05-08)
- **Source:** `docs/weekly-plan-2026-05-10.md` §"What I do this week" (Sun); MEMORY `project_training_platform_2026-05-10`; MEMORY `project_training_platform_unfork_plan` (2026-05-12)
- **Symptoms:** `COMP-SEEKAPAAITRAININGAPI-PROD` returning 403; SPA silently fails to mount (Playwright-verified); `func-training-prod` itself is healthy
- **Suspected root cause:** missing `AzureWebJobsStorage` + sitecontainer inheritance chain; same code deployed twice (func + containerized func), container variant broken
- **Plan:** delete the container deployment, keep func, fix SPA, **no FastAPI rewrite**
- **Done when:** API returns 200 on health probe, SPA loads, single deployment path documented; escalate to Yasha by EOD if not green

### T02. Auto-eval re-run after PR 254 lands (keyword_pass 72→≥85%)
- **Source:** `docs/eval-findings-2026-05-11.md` §"Next eval runs recommended" #1
- **Action:** trigger 50-row Foundry auto-eval on `seekapa:116` after PR 254 (brittle keyword fixes) merges; compare against run `654bf4c4-…`
- **Done when:** keyword_pass ≥ 85%, Groundedness ≥ 4.5, no new regressions in any of the 14 evaluators; portal link saved to `docs/eval-findings-2026-05-12.md`

### T03. v110.1 OTP — finish the 16-section QA suite + unset SMTP backdoor
- **Source:** `docs/qa/2026-05-11-v110.1-otp-full-qa-suite.md` (sections A–M, "Pass criteria for full sign-off")
- **Pre-state:** PR 262 hotfix merged, `SEEKAPA_VERIFY_ENABLED=true`, `SMTP_TEST_REDIRECT_EMAIL=shoval.be@i-sdd.com`
- **Sections:** A (happy path EN→AR / AR→AR / ES fallback / PT mixed) → B (phantom regression) → C (EMAIL retrigger) → D (resolve cleanup) → E (3-attempt cap) → F (resend + rate-limit) → G (cancel-equivalents) → H (NOT_FOUND/NOT_VERIFIED/INVALID) → I (TTL expiry) → J (replay) → K (multi-customer isolation, optional) → L (Brevo dashboard) → M (AppTraces + PII redaction)
- **Cleanup after pass:** `az functionapp config appsettings set ... SMTP_TEST_REDIRECT_EMAIL=` (CRITICAL — leaving it set leaks real customer OTPs to my inbox)
- **Rollback path:** `SEEKAPA_VERIFY_ENABLED=false` (30s restart)

## P1 — This week (Wed–Thu commitments)

### T04. Deliver HCTA to Yasha (overdue)
- **Source:** `docs/weekly-plan-2026-05-10.md` §Wed; Yasha deliverable track
- **Status:** overdue — Wed reserved with no other deliverables
- **Done when:** doc handed off, Yasha confirms receipt

### T05. Marketing Newsletter container migration kickoff
- **Source:** MEMORY `project_marketing_newsletter_container_migration` (2026-05-06 ask); `weekly-plan-2026-05-10.md` §Thu
- **Goal:** lift `func-marketing-newsletter` off EP1 plan → Docker on `sentimark-env` (largest persistent cost line)
- **Done when:** ACR image built, deploy script in repo, baseline parity test run, EP1 ready for decom

### T06. ORM scope-lock session (Thu)
- **Source:** `docs/weekly-plan-2026-05-10.md` §ORM-Agent; `~/projects/ORM-AGENT/ORM-PLAN.md`
- **Lock 5 open Qs:** auto-hide threshold, sales hand-off channel, DM-ask phrasing legal sign-off, X scope, operator console reuse
- **Volume baseline:** still TBD — Mohammad Da owes Q1 page-comment volume
- **Done when:** 5 Qs signed off in writing; Phase 1 (KB indexing) can start if approved

### T07. Marketing analytics 2 fixes + BI-collision strip (Wed)
- **Source:** `docs/weekly-plan-2026-05-10.md` §Wed
- **Fixes:** (a) call-lookup precision, (b) OneSignal email-template content
- **Strip:** remove "industry benchmark" outputs from the MCP (PR 247) so we don't publish numbers conflicting with BI
- **Done when:** both fixes merged + deployed; PR 247 landed

### T08. Video Flows decision call with Adnan (Wed)
- **Source:** `docs/weekly-plan-2026-05-10.md` §Decisions waiting #4 + active threads
- **Decision:** rebuild simplified 6-step UI (fields → preview → avatar → generate → edits → download) OR kill the project
- **Lean:** simplify-then-pilot with one marketing user; if no adoption in 2 weeks, kill
- **Done when:** decision recorded; if simplify, slice-1 ticket filed

### T09. FAQ → CRM hand-off spec draft (Thu, Q2 board commitment)
- **Source:** `docs/weekly-plan-2026-05-10.md` §Thu
- **Done when:** spec under `docs/specs/` with API surface + retention + auth boundary defined

### T10. v110 KB additions — Glossary + Objection-Handling upload
- **Source:** `docs/specs/2026-05-06-v110-deploy-runbook.md` §1
- **Files:** `kb-source/Seekapa_Glossary_v1.md`, `kb-source/Seekapa_Objection_Handling_v1.md`
- **Target:** vector store `vs_BhDnWqMdIsxjgv1f0sQOuwX6` via `kb-source/upload_to_foundry.py --execute --files glossary,objections`
- **Verify:** re-run `pull_kb.py`, grep for both filenames in snapshot
- **Done when:** snapshot diff shows +2 files, no replacements

## P1 — Eval & test quality (low-risk, high-leverage)

### T11. Populate `ground_truth` on ≥20 rows of `foundry_yasha_eval_v2.jsonl`
- **Source:** `docs/eval-findings-2026-05-11.md` §"Items proposed" #4
- **Effort:** 2–3 hours; ~2–3 sentence canonical answer per row
- **Unlocks:** Similarity (currently 1.20) + F1Score (currently 0.00) evaluators
- **Done when:** ≥20 rows have non-empty `ground_truth`, eval re-run reports Similarity ≥3 and F1 ≥0.5

### T12. TaskAdherence rehabilitation — populate `conversation_history`
- **Source:** `docs/eval-findings-2026-05-11.md` §"Next eval runs" #3
- **Action:** add `conversation_history` field to escalation rows so SDK can thread context into single-turn evaluation
- **Expected lift:** ~15pp on TaskAdherence (currently 0.64/5)
- **Done when:** field populated on all escalation-route rows; re-run shows TaskAdherence ≥3.0

### T13. SMOKE-17 — deposit timeline KB gap
- **Source:** `docs/eval-findings-2026-05-11.md` §"Real defects" SMOKE-17
- **Gap:** bot gives general deposit info but omits `2-4 hours` / `3-5 business days` windows
- **Action:** add explicit window section to FAQ KB; re-upload via `upload_to_foundry.py`
- **Done when:** SMOKE-17 passes on next eval run

### T14. SMOKE-20 — Hebrew gibberish handling
- **Source:** `docs/eval-findings-2026-05-11.md` §"Real defects" SMOKE-20
- **Defect:** `אנדרלמוסיה` → bot replied `"OK"` (Groundedness=1.0 because no claim to verify)
- **Two paths:**
  - (A) add low-confidence detector to `_pre_classifier` — fires when no language matches AND non-keyword AND len<20 → ask clarification
  - (B) treat short non-supported-language input as bare greeting trigger
- **Lean:** (A) — explicit detector, gives operator visibility; HE isn't in v109's EN/AR/ES/PT support set so this is the fallback path
- **Done when:** separate ticket filed (out of scope for PR 254), test fixture added, fix shipped

### T15. Variant A wording — TaskAdherence quirk (needs Yasha sign-off)
- **Source:** `docs/eval-findings-2026-05-11.md` §"Items proposed" #3
- **Two options:** (A) accept noisy metric (current Variant A reads "I've passed this…"), (B) passive-voice rephrase "Forwarded to our support team. Response may take longer…" — all 4 langs + update anti-loop markers
- **Blocker:** Yasha pick
- **Done when:** decision logged; if B, PR with all 4 lang strings + `_pre_classifier._ESCALATION_FIRED_MARKERS` update

### T16. Full 97-row eval baseline lock
- **Source:** `docs/eval-findings-2026-05-11.md` §"Next eval runs" #2
- **Action:** after T02 + T11 + T13 land, run full 97-row eval to lock baseline confidence intervals before further prompt edits
- **Done when:** baseline JSON checked into `qa_reports/v109-eval/`

## P1 — Platform hygiene (from 2026-05-11 sweep)

### T17. RTK hook decision — restore or formally retire (Claude-side)
- **Source:** `.claude/docs/PLATFORM_HYGIENE_2026-05-11.md` §HOOK_HEALTH "HIGH"; ACTIONABLE #1
- **State:** `.rtk-hook.sha256` missing; `rtk-rewrite.sh` missing
- **Decide:** restore via RTK tooling (regenerate hash, don't hand-edit), OR retire (remove RTK hash checks from hygiene prompts and mark Codex-only)
- **Done when:** decision recorded in MEMORY; either marker restored or hygiene prompts updated

### T18. Meme hooks hardening
- **Source:** `.claude/docs/PLATFORM_HYGIENE_2026-05-11.md` §HOOK_HEALTH "MEDIUM"; ACTIONABLE #2
- **Target:** `~/projects/claude-meme-hooks/hooks/*.sh` (NOT the symlinks)
- **Add:** `# budget: ...ms` header comment, `set -euo pipefail`, bounded cleanup for stale `/tmp/.claude-*` markers
- **Done when:** patches landed in claude-meme-hooks repo, symlinks pick up changes automatically

### T19. PST pipeline reconciliation
- **Source:** `.claude/docs/PLATFORM_HYGIENE_2026-05-11.md` §PST_PIPELINE_HEALTH "HIGH" + "MEDIUM"; ACTIONABLE #3 + #4
- **Action:** either restore `~/.claude/bin/pst-watch.sh`, `pst-to-memory.py`, `pst-to-db.py`, `pst-to-knowledge.py` OR update scheduled automations to call `~/.claude/cache/layer7/parse-mbox.py` directly
- **DB contract:** existing prompt expects `emails` table; actual table is `pst_messages` (663 rows). Prefer updating health check to `pst_messages`
- **Done when:** scripts at expected paths OR automations updated; health check passes against actual schema
- **MEMORY update:** mark `reference_claude_bin` PST-script paths as stale until restored (per hygiene proposal #1)

### T20. Hook budget annotations
- **Source:** `.claude/docs/PLATFORM_HYGIENE_2026-05-11.md` §HOOK_HEALTH "LOW"
- **Add:** `# budget: 50ms` header to every hook in `~/.claude/hooks/`
- **Done when:** all 5 hook scripts have explicit budget comments

## P2 — Strategic / cross-cutting

### T21. Centralized Marketing MCP gateway plan (Microsoft-native)
- **Source:** MEMORY `project_centralized_marketing_mcp` (2026-05-12)
- **Architecture:** APIM + per-platform ACA MCP servers + Entra role-gated access
- **Surfaces:** CRM, CallAnalyzer, GAds, Meta, Taboola, Snap, YT, X
- **Boundary:** Fabric+Dataverse stays as BI layer (no overlap)
- **Done when:** spec under `docs/specs/2026-05-12-centralized-marketing-mcp.md`, slice-1 (single platform proof-of-concept) scoped

### T22. Daily Market Reports v2 rebuild
- **Source:** MEMORY `project_daily_market_reports_v2`
- **Stack:** gpt-5.4-mini via Foundry + yfinance/statsmodels/autogluon only
- **Context:** Oded's `func-market-reports-prod` stopped 2026-05-06
- **Decision dependency:** weekly plan §Decision #1 — recommendation = **kill** (no internal owner); only proceed if Liron green-lights
- **Done when:** kill confirmed (close out) OR slice-1 spec drafted

### T23. Compliance Exam chase
- **Source:** `docs/weekly-plan-2026-05-10.md` §active threads + §Decision #2
- **Action:** chase Nissreen S. (Axia) for user-readiness gap list (Karim emailed 2026-05-07 delegating to her)
- **Don't:** decide integrate-or-leave until we have her list
- **Done when:** Nissreen reply received; decision recorded

### T24. Hiya call-branding rollout support (Nadav owns)
- **Source:** `docs/weekly-plan-2026-05-10.md` §Tue + §active threads
- **Outstanding:** Bluepine LTD company / VAT / signatory details to vendor (Olanda Katuruza). 48hr to live after signed
- **My role:** technical bridge if needed; Nadav drives
- **Done when:** signed contract submitted; live call branding verified

### T25. SOTA Foundry red-team re-run cadence
- **Source:** `docs/eval-findings-2026-05-11.md` §Update "redteam-v109-1778480180" (0/149 ASR)
- **Action:** add monthly cron via `/schedule` to re-run 10×4 red-team against current prompt
- **Done when:** schedule created, first auto-run completes, ASR delta tracked in `qa_reports/`

### T26. Pytest lastfailed sweep
- **Source:** `.pytest_cache/v/cache/lastfailed` (last touched 2026-05-12 15:32)
- **Scope:** most failures are in `projects/el-vadt/sales-agents/scripts/*` (archive paths) and `projects/social-intelligence-unit/tests/*` — both outside the cs-agent active scope
- **Action:** confirm these are inherited/archived and not part of current CI; if so, add to `.pytest_cache` ignore or delete the archive scripts
- **Done when:** lastfailed only shows tests on the active code paths

## P2 — Tracked, not started

### T27. Funnel/customer-journey deep work (campaign-analysis)
- **Sources:** `projects/campaign-analysis/Full_Funnel_Intelligence_Brief.docx`, `Seekapa_Dashboard_Forensic_Audit.docx`, `customer_journey_requirements.pdf`
- **Status:** stub — needs Liron/Yasha framing call to scope

### T28. QC Telephony — test_qa_agent failures (in `lastfailed`)
- **Source:** `.pytest_cache/v/cache/lastfailed` (lines 47–48 — TestQAAgentService::test_answer_question_first_query / _follow_up)
- **Action:** read the two tests, decide whether to fix or quarantine; coordinate with QC owner

### T29. Compliance-exam-docker-deploy + evaluate_exam (legacy `projects/`)
- **Source:** filesystem inventory — `projects/compliance-exam-docker-deploy/evaluate_exam/`
- **Action:** verify whether this is live or shelved; align with Compliance Exam decision (T23)

---

## Reference index

| Source | Path | What it gives |
|---|---|---|
| Weekly plan | `docs/weekly-plan-2026-05-10.md` | day-by-day this week, decisions queue, risks |
| Eval findings | `docs/eval-findings-2026-05-11.md` | scores, brittle-test fixes, real defects, cost |
| OTP QA suite | `docs/qa/2026-05-11-v110.1-otp-full-qa-suite.md` | 16-section sign-off matrix + cleanup |
| v110 deploy runbook | `docs/specs/2026-05-06-v110-deploy-runbook.md` | KB upload + flag rollout + rollback |
| OTP spec | `docs/specs/2026-05-10-seekapa-otp-verification-flow.md` | OTP architecture & invariants |
| Platform hygiene | `.claude/docs/PLATFORM_HYGIENE_2026-05-11.md` | hooks / skills / PST / RTK findings |
| Engineering reviews | `.claude/docs/ENGINEERING_REVIEW_2026-05-{02,05,06}.md` | code-quality sweeps, large |
| Eval datasets | `evals/data/intake_eval{,_v109,_v110}.jsonl` + `tests/test_data/foundry_yasha_eval_v{2,109}.jsonl` | eval row sources |
| Past eval results | `qa_reports/v109-eval/after-deploy-20260503-1649.json` + `baseline-against-v114-*.json` | reference scores pre/post-deploy |
| Codex review history | `qa_reports/codex-review/review-*.md`, `safety-*.md` | independent reviews |
| Recent reflections | `docs/reflections/2026-04-29-v109-yasha-multilingual.md`, `2026-04-30-v109-deploy-review-cleanup.md` | what shipped + lessons |

## Notes on what's NOT in this list

- v109 branch hygiene — already done this session (fast-forwarded to `a3b2bc55`)
- yesterday's tiktok scraper / Meta block prevention — out of cs-agent scope; tracked separately
- `client-eval keep-alive` work — MEMORY says scope was reduced 2026-05-10 to Corp-AI DevOps repos only
- nifty-chaum + tmp/stage-align-pr97 worktrees — prunable per `git worktree list`
- `func-training/qc` deployment env-var cleanup — MEMORY captures the wiring; only act if regression observed
