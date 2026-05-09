# Engineering Review Sweep - 2026-05-02 18:51:25 UTC

Automation id: `c02-engineering-review-sweep`  
Run timestamp UTC: `20260502T184824Z`  
Workspace root: `/home/shovalbe`

## EXECUTIVE_SUMMARY
- Scanned 14 git repos under `/home/shovalbe/projects`.
- Azure DevOps remote coverage: `auth-needs-refresh`; local git analysis continued.
- Local findings generated: code_quality=92, gates=6, perf=8, ci=2, stale=29.
- No ADO comments or work items were created because remote PR/work item state was unavailable and the run is read + propose unless high-confidence PR mapping exists.

## AZURE_DEVOPS_REMOTE_COVERAGE
- Organization/project requested: `https://dev.azure.com/Corp-domain` / `Corp-AI`.
- Status: `auth-needs-refresh`.
- Blocker detail: Azure DevOps CLI reported that DevOps credentials are not set up and requested `az login` or `az devops login`.
- Active PRs, stale PRs, remote branch age, uncloned Azure repos, and pipeline/run health could not be fully evaluated without Azure DevOps CLI credentials.

Remote coverage gaps:
- ADO repo inventory unavailable: auth-needs-refresh, so uncloned remote repos could not be identified.

## BLOCKED
- Azure DevOps remote checks are BLOCKED by `auth-needs-refresh`; local git, docs, prompt-file inventory, static scan, and configured lint checks completed.
- Live Foundry prompt comparison is BLOCKED because no authenticated Foundry comparison target was established in this unattended pass.

## LOCAL_REPO_COVERAGE
| Repo | Origin | Branch | Dirty | Commits 30d | Commits 24h | Upstream notes | Remote heads |
|---|---|---:|---:|---:|---:|---|---|
| `projects` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents` | `feat/v109-yasha-multilingual` | 59 | 110 | 0 | behind feat/align-test-connector-to-production,feat/v109-yasha-multilingual,fix/codex-ci-endpoint, ahead feat/align-test-connector-to-production,feat/chatwoot-webhook-handler,fix/codex-ci-endpoint, no-track backup/feat-callanalyzer-before-stage-align,feat/callanalyzer-mcp-integration,main | failed |
| `projects/.archive/claude-orchestration` | `(no origin)` | `master` | 0 | 0 | 0 | no-track master | failed |
| `projects/.archive/el-vadt` | `(no origin)` | `master` | 0 | 0 | 0 | no-track master | failed |
| `projects/campaign-analysis` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis` | `feat/pipeline-sota-restructure` | 148 | 78 | 0 | behind master, ahead feature/pipeline-cleanup,master, no-track master-pre-reset-2026-04-27,test/ci-foundry-key-wire | failed |
| `projects/campaign-analysis/Onesignal` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis` | `feat/pipeline-sota-restructure` | 148 | 78 | 0 | behind master, ahead feature/pipeline-cleanup,master, no-track master-pre-reset-2026-04-27,test/ci-foundry-key-wire | failed |
| `projects/cs-agent` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents` | `feat/v109-yasha-multilingual` | 59 | 110 | 0 | behind feat/align-test-connector-to-production,feat/v109-yasha-multilingual,fix/codex-ci-endpoint, ahead feat/align-test-connector-to-production,feat/chatwoot-webhook-handler,fix/codex-ci-endpoint, no-track backup/feat-callanalyzer-before-stage-align,feat/callanalyzer-mcp-integration,main | failed |
| `projects/cs-agent/axia-seekapa-cs-agents-devops` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents` | `feat/v109-yasha-multilingual` | 0 | 92 | 0 | ahead feat/v107.3-prompt-optimizer-iter-kb-v2,feat/v109-yasha-multilingual, no-track feat/foundry-smoke-eval-gate,feat/typing-indicator,fix/issues-17-19 | failed |
| `projects/figma-4-all` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all` | `fix/land-bleed-port-disclaimer-ui-simplify` | 5432 | 0 | 0 | no-track master | failed |
| `projects/personal/jsq-slq` | `https://github.com/ShovalBenjer/JSQ-SLQ.git` | `main` | 3 | 0 | 0 | ok/none | failed |
| `projects/qc` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents` | `feat/v109-yasha-multilingual` | 59 | 110 | 0 | behind feat/align-test-connector-to-production,feat/v109-yasha-multilingual,fix/codex-ci-endpoint, ahead feat/align-test-connector-to-production,feat/chatwoot-webhook-handler,fix/codex-ci-endpoint, no-track backup/feat-callanalyzer-before-stage-align,feat/callanalyzer-mcp-integration,main | failed |
| `projects/qc/qc-telephony-api` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api` | `stage` | 0 | 43 | 0 | behind master, no-track feat/e2e-stage-only,feat/pipeline-script-extraction,fix/notifications-concise-failure | failed |
| `projects/seekapa-training-platform` | `(no origin)` | `fix/ci-manylinux-wheels` | 6 | 37 | 0 | behind master | failed |
| `projects/social-intelligence-unit` | `https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit` | `feat/video-generation-gemini-remotion-heygen` | 1283 | 0 | 0 | ahead feat/video-generation-gemini-remotion-heygen, no-track docs/claude-enhancement,docs/phase1-task-list,master | failed |
| `projects/social-intelligence-unit/src/seekapa-video` | `(no origin)` | `master` | 355 | 0 | 0 | no-track master | failed |

## SPEC_AND_DOCS_DRIFT
- `projects/docs/superpowers/specs/2026-04-25-ink-tui-next-level-forge-overlay.md`: STALLED (refs=0, age_days=6)
- `projects/campaign-analysis/docs/superpowers/specs/2026-03-30-call-analyzer-agent-v9-design.md`: ACTIVE (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-16-ffi-agent-scope-eval.md`: STALLED (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-18-ffi-v2-structured-agents.md`: MERGED (refs=1, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-crm-call-analyser-redeploy.md`: ACTIVE (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-live-batch-pipeline-design.md`: MERGED (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-components.md`: STALLED (refs=3, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-design.md`: STALLED (refs=4, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-eval.md`: STALLED (refs=3, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-flow.md`: STALLED (refs=3, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-mfm-workflow-readable-output-and-eval.md`: STALLED (refs=1, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-20-mfm-multiagent-redesign.md`: STALLED (refs=0, age_days=12)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-mcp-narrow-ship.md`: STALLED (refs=2, age_days=9)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-gates-and-tests.md`: MERGED (refs=0, age_days=9)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-retrieval-and-memory.md`: MERGED (refs=0, age_days=9)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-two-agent-foundry-native-redesign.md`: STALLED (refs=2, age_days=9)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-cja-v2-mcp-alignment.md`: STALLED (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-m365-copilot-ui-widgets-ux-edit.md`: MERGED (refs=0, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-mcp-seekapa-tools-v2.md`: MERGED (refs=2, age_days=4)
- `projects/campaign-analysis/docs/superpowers/specs/archive/2026-04-20-mfm-async-chat-design.superseded.md`: MERGED (refs=0, age_days=12)
- `projects/campaign-analysis/docs/specs/2026-04-07-agent_scoring_round6.md`: ACTIVE (refs=2, age_days=4)
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_common.md`: ACTIVE (refs=2, age_days=4)
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_prefetch.md`: STALLED (refs=2, age_days=4)
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_score_global.md`: STALLED (refs=2, age_days=4)
- `projects/cs-agent/docs/superpowers/specs/2026-03-25-chatwoot-handler-signal-escalation-design.md`: ORPHAN (refs=0, age_days=37)
- `projects/cs-agent/docs/specs/2026-04-18-align-test-connector-to-production.md`: STALLED (refs=0, age_days=14)
- `projects/cs-agent/docs/specs/2026-04-23-seekapa-prompt-v101-compact-style-kb-routing.md`: STALLED (refs=0, age_days=6)
- `projects/cs-agent/docs/specs/2026-04-28-v108-yasha-intake-flow.md`: ACTIVE (refs=0, age_days=4)
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-15-silver-eval-dataset.md`: ACTIVE (refs=1, age_days=12)
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-28-v108-yasha-intake-flow.md`: ACTIVE (refs=0, age_days=3)
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-29-v109-yasha-multilingual-intake.md`: MERGED (refs=2, age_days=3)
- `projects/qc/qc-telephony-api/docs/specs/2026-04-28-no-storage-qa.md`: STALLED (refs=1, age_days=4)
- `projects/seekapa-training-platform/docs/superpowers/specs/2026-03-29-email-reliability-scoring-fix-design.md`: STALLED (refs=1, age_days=19)
- `projects/seekapa-training-platform/docs/superpowers/specs/2026-04-05-email-session-lifecycle-refactor-design.md`: STALLED (refs=0, age_days=19)
- `projects/social-intelligence-unit/docs/superpowers/specs/2026-03-26-foundry-agent-orchestration-design.md`: ORPHAN (refs=0, age_days=37)
- `projects/social-intelligence-unit/docs/superpowers/specs/2026-04-14-heygen-v3-aca-integration.md`: STALLED (refs=1, age_days=18)

CLAUDE.md drift samples:
- P3: `projects/campaign-analysis/CLAUDE.md` references missing path `@unovis/ts`
- P3: `projects/cs-agent/CLAUDE.md` references missing path `bash`
- P3: `projects/qc/CLAUDE.md` references missing path `bash`
- P3: `projects/qc/qc-telephony-api/CLAUDE.md` references missing path `GET`
- P3: `projects/seekapa-training-platform/CLAUDE.md` references missing path `~/.claude/plans/`
- P3: `projects/social-intelligence-unit/CLAUDE.md` references missing path `—`

## FOUNDRY_PROMPT_DRIFT
- Live Foundry prompt comparison was not performed in this unattended pass because no authenticated Foundry target/SDK comparison path was established after Azure DevOps auth failed.
- `projects/campaign-analysis` no standard prompt files found by prompt.md / agent_prompts/*.md / agent.yaml scan.
- `projects/cs-agent` no standard prompt files found by prompt.md / agent_prompts/*.md / agent.yaml scan.

## CODE_QUALITY
- P3: `projects` - spec `docs/superpowers/specs/2026-04-25-ink-tui-next-level-forge-overlay.md` classified STALLED (refs=0, age_days=6)
- P2: `projects` - recent added lines match `broad_exception` (32 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/__init__.py`:12, `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28, `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P3: `projects` - recent added lines match `added_any` (6 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/__init__.py`:12, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28
- P2: `projects` - recent added lines match `debug_print` (2 hits); `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P2: `projects` - hot-zone file `azure-function-crm/chatwoot_handler/_gates.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `azure-function-crm/chatwoot_handler/__init__.py` appears in 10 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `scripts/deploy_seekapa_prompt.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `scripts/foundry_eval_gate.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `azure-pipelines.yml` appears in 15 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `azure-function-crm/channel_router/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects` - hot-zone file `tests/webhook_test_helpers.py` appears in 2 fix commits in 30d without obvious parallel test change
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-16-ffi-agent-scope-eval.md` classified STALLED (refs=0, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-19-marketing-funnel-manager-components.md` classified STALLED (refs=3, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-19-marketing-funnel-manager-design.md` classified STALLED (refs=4, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-19-marketing-funnel-manager-eval.md` classified STALLED (refs=3, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-19-marketing-funnel-manager-flow.md` classified STALLED (refs=3, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-19-mfm-workflow-readable-output-and-eval.md` classified STALLED (refs=1, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-20-mfm-multiagent-redesign.md` classified STALLED (refs=0, age_days=12)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-23-mcp-narrow-ship.md` classified STALLED (refs=2, age_days=9)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-23-two-agent-foundry-native-redesign.md` classified STALLED (refs=2, age_days=9)
- P3: `projects/campaign-analysis` - spec `docs/superpowers/specs/2026-04-28-cja-v2-mcp-alignment.md` classified STALLED (refs=0, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/specs/2026-04-07-batch_prefetch.md` classified STALLED (refs=2, age_days=4)
- P3: `projects/campaign-analysis` - spec `docs/specs/2026-04-07-batch_score_global.md` classified STALLED (refs=2, age_days=4)
- P2: `projects/campaign-analysis` - recent added lines match `debug_print` (169 hits)
- P2: `projects/campaign-analysis` - recent added lines match `broad_exception` (78 hits); `scripts/_grounded_finalize_v3.py`:3
- P3: `projects/campaign-analysis` - recent added lines match `added_any` (36 hits); `app_mcp/tools/call_analyzer_orchestrator.py`:2, `scripts/_grounded_xlsx_v3.py`:3, `app_mcp/tools/analysis/verdicts.py`:3
- P2: `projects/campaign-analysis` - hot-zone file `scripts/deploy_agent.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis` - hot-zone file `azure-pipelines.yml` appears in 11 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis` - hot-zone file `scripts/codex_review.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis` - hot-zone file `scripts/batch_agent_runs.py` appears in 3 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis/Onesignal` - hot-zone file `scripts/deploy_agent.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis/Onesignal` - hot-zone file `azure-pipelines.yml` appears in 11 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis/Onesignal` - hot-zone file `scripts/codex_review.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/campaign-analysis/Onesignal` - hot-zone file `scripts/batch_agent_runs.py` appears in 3 fix commits in 30d without obvious parallel test change
- P3: `projects/cs-agent` - spec `docs/superpowers/specs/2026-03-25-chatwoot-handler-signal-escalation-design.md` classified ORPHAN (refs=0, age_days=37)
- P3: `projects/cs-agent` - spec `docs/specs/2026-04-18-align-test-connector-to-production.md` classified STALLED (refs=0, age_days=14)
- P3: `projects/cs-agent` - spec `docs/specs/2026-04-23-seekapa-prompt-v101-compact-style-kb-routing.md` classified STALLED (refs=0, age_days=6)
- P2: `projects/cs-agent` - recent added lines match `broad_exception` (32 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/__init__.py`:12, `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28, `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P3: `projects/cs-agent` - recent added lines match `added_any` (6 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/__init__.py`:12, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28
- P2: `projects/cs-agent` - recent added lines match `debug_print` (2 hits); `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P2: `projects/cs-agent` - hot-zone file `azure-function-crm/chatwoot_handler/_gates.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `azure-function-crm/chatwoot_handler/__init__.py` appears in 10 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `scripts/deploy_seekapa_prompt.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `scripts/foundry_eval_gate.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `azure-pipelines.yml` appears in 15 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `azure-function-crm/channel_router/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent` - hot-zone file `tests/webhook_test_helpers.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - recent added lines match `debug_print` (72 hits); `scripts/eval_v108_against_prod.py`:16, `evals/scripts/v109_runner.py`:18, `evals/scripts/agent_endpoint_runner.py`:6
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - recent added lines match `broad_exception` (33 hits); `scripts/eval_v108_against_prod.py`:16, `evals/scripts/v109_runner.py`:18, `evals/scripts/agent_endpoint_runner.py`:6
- P3: `projects/cs-agent/axia-seekapa-cs-agents-devops` - recent added lines match `added_any` (23 hits); `scripts/eval_v108_against_prod.py`:16, `tests/test_v109_invariants.py`:5, `evals/scripts/v109_runner.py`:18, `evals/scripts/agent_endpoint_runner.py`:6
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `azure-function-crm/chatwoot_handler/_gates.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `azure-function-crm/chatwoot_handler/__init__.py` appears in 9 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `scripts/deploy_seekapa_prompt.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `scripts/foundry_eval_gate.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `azure-pipelines.yml` appears in 14 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `azure-function-crm/channel_router/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - hot-zone file `tests/webhook_test_helpers.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `azure-function-crm/chatwoot_handler/_gates.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `azure-function-crm/chatwoot_handler/__init__.py` appears in 10 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `scripts/deploy_seekapa_prompt.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `scripts/foundry_eval_gate.py` appears in 6 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `azure-pipelines.yml` appears in 15 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `azure-function-crm/channel_router/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/qc` - hot-zone file `tests/webhook_test_helpers.py` appears in 2 fix commits in 30d without obvious parallel test change
- P3: `projects/qc/qc-telephony-api` - spec `docs/specs/2026-04-28-no-storage-qa.md` classified STALLED (refs=1, age_days=4)
- P2: `projects/qc/qc-telephony-api` - recent added lines match `broad_exception` (7 hits); `src/api/function_app.py`:5, `src/api/shared/summary_agent_service.py`:1, `src/api/shared/qa_agent_service.py`:1
- P3: `projects/qc/qc-telephony-api` - recent added lines match `added_any` (2 hits); `tests/test_no_storage_qa.py`:2
- P2: `projects/qc/qc-telephony-api` - hot-zone file `azure-pipelines.yml` appears in 9 fix commits in 30d without obvious parallel test change
- P2: `projects/qc/qc-telephony-api` - hot-zone file `src/api/shared/qa_agent_service.py` appears in 3 fix commits in 30d without obvious parallel test change
- P3: `projects/seekapa-training-platform` - spec `docs/superpowers/specs/2026-03-29-email-reliability-scoring-fix-design.md` classified STALLED (refs=1, age_days=19)
- P3: `projects/seekapa-training-platform` - spec `docs/superpowers/specs/2026-04-05-email-session-lifecycle-refactor-design.md` classified STALLED (refs=0, age_days=19)
- P3: `projects/seekapa-training-platform` - recent added lines match `added_any` (1 hits); `frontend/tests/e2e/live-prod-smoke.spec.ts`:2
- P2: `projects/seekapa-training-platform` - recent added lines match `debug_print` (1 hits); `frontend/tests/e2e/live-prod-smoke.spec.ts`:2
- P2: `projects/seekapa-training-platform` - hot-zone file `azure-pipelines.yml` appears in 12 fix commits in 30d without obvious parallel test change
- P2: `projects/seekapa-training-platform` - hot-zone file `backend/health_check/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/seekapa-training-platform` - hot-zone file `backend/email_drip_sender/__init__.py` appears in 3 fix commits in 30d without obvious parallel test change
- P2: `projects/seekapa-training-platform` - hot-zone file `backend/shared/email_service.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/seekapa-training-platform` - hot-zone file `backend/webhook_elevenlabs/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P2: `projects/seekapa-training-platform` - hot-zone file `backend/sync_sessions/__init__.py` appears in 2 fix commits in 30d without obvious parallel test change
- P3: `projects/social-intelligence-unit` - spec `docs/superpowers/specs/2026-03-26-foundry-agent-orchestration-design.md` classified ORPHAN (refs=0, age_days=37)
- ... truncated 12 additional findings

## TEST_AND_EVAL_GATES
- P2: `projects` - pipeline/test/eval line removed in last-14d YAML/Python diff
- P2: `projects/campaign-analysis` - pipeline/test/eval line removed in last-14d YAML/Python diff
- P2: `projects/cs-agent` - pipeline/test/eval line removed in last-14d YAML/Python diff
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - pipeline/test/eval line removed in last-14d YAML/Python diff
- P2: `projects/qc/qc-telephony-api` - pipeline/test/eval line removed in last-14d YAML/Python diff
- P2: `projects/seekapa-training-platform` - pipeline/test/eval line removed in last-14d YAML/Python diff

## PERFORMANCE_AND_LATENCY
- P3: `projects` - recent added lines match `sleep_or_poll` (16 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28, `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P3: `projects` - recent added lines match `unbounded_retry` (8 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28
- P3: `projects/campaign-analysis` - recent added lines match `unbounded_retry` (20 hits); `scripts/_grounded_xlsx_v3.py`:3, `scripts/_grounded_finalize_v3.py`:3
- P3: `projects/campaign-analysis` - recent added lines match `sleep_or_poll` (18 hits); `app_mcp/tools/call_analyzer_orchestrator.py`:2
- P3: `projects/cs-agent` - recent added lines match `sleep_or_poll` (16 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28, `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- P3: `projects/cs-agent` - recent added lines match `unbounded_retry` (8 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28
- P3: `projects/cs-agent/axia-seekapa-cs-agents-devops` - recent added lines match `sleep_or_poll` (14 hits); `scripts/eval_v108_against_prod.py`:16
- P3: `projects/cs-agent/axia-seekapa-cs-agents-devops` - recent added lines match `unbounded_retry` (6 hits)

## CI_AND_PIPELINES
- P2: `projects/qc/qc-telephony-api` - pipeline `azure-pipelines.yml` has Azure auth-sensitive operations without obvious AzureCLI task wrapper
- P1: `projects/seekapa-training-platform` - pipeline `.github/workflows/e2e-tests.yml` contains `continue-on-error: true`

## STALE_PR_AND_BRANCH_TRIAGE
- ADO stale PR and remote branch triage: BLOCKED by `auth-needs-refresh`.
- P2: `projects` - local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
- P2: `projects` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- P2: `projects/campaign-analysis` - local branches behind upstream: master
- P2: `projects/campaign-analysis` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- P2: `projects/campaign-analysis/Onesignal` - local branches behind upstream: master
- P2: `projects/campaign-analysis/Onesignal` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- P2: `projects/cs-agent` - local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
- P2: `projects/cs-agent` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- P2: `projects/cs-agent/axia-seekapa-cs-agents-devops` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- P2: `projects/figma-4-all` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all/': Could not resolve host: dev.azure.com
- P2: `projects/personal/jsq-slq` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://github.com/ShovalBenjer/JSQ-SLQ.git/': Could not resolve host: github.com
- P2: `projects/qc` - local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
- P2: `projects/qc` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- P2: `projects/qc/qc-telephony-api` - local branches behind upstream: master
- P2: `projects/qc/qc-telephony-api` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api/': Could not resolve host: dev.azure.com
- P2: `projects/seekapa-training-platform` - local branches behind upstream: master
- P2: `projects/social-intelligence-unit` - `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit/': Could not resolve host: dev.azure.com
- P3: `projects` has local branches with last commit older than 30d: backup/feat-callanalyzer-before-stage-align, feat/callanalyzer-mcp-integration, feat/chatwoot-webhook-handler, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39, main, stage
- P3: `projects/.archive/claude-orchestration` has local branches with last commit older than 30d: master
- P3: `projects/.archive/el-vadt` has local branches with last commit older than 30d: master
- P3: `projects/campaign-analysis` has local branches with last commit older than 30d: master
- P3: `projects/campaign-analysis/Onesignal` has local branches with last commit older than 30d: master
- P3: `projects/cs-agent` has local branches with last commit older than 30d: backup/feat-callanalyzer-before-stage-align, feat/callanalyzer-mcp-integration, feat/chatwoot-webhook-handler, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39, main, stage
- P3: `projects/cs-agent/axia-seekapa-cs-agents-devops` has local branches with last commit older than 30d: feat/foundry-smoke-eval-gate
- P3: `projects/figma-4-all` has local branches with last commit older than 30d: fix/land-bleed-port-disclaimer-ui-simplify, master
- P3: `projects/personal/jsq-slq` has local branches with last commit older than 30d: main
- P3: `projects/qc` has local branches with last commit older than 30d: backup/feat-callanalyzer-before-stage-align, feat/callanalyzer-mcp-integration, feat/chatwoot-webhook-handler, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39, main, stage
- P3: `projects/social-intelligence-unit` has local branches with last commit older than 30d: docs/claude-enhancement, docs/phase1-task-list, feat/video-generation-gemini-remotion-heygen, master, stage
- P3: `projects/social-intelligence-unit/src/seekapa-video` has local branches with last commit older than 30d: master

## PROJECT_ROUTING
- `projects`
  - P2: local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
  - P2: recent added lines match `broad_exception` (32 hits); `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/__init__.py`:12, `projects/cs-agent/axia-seekapa-cs-agents/azure-function-crm/channel_router/_agent_client.py`:14, `projects/cs-agent/axia-seekapa-cs-agents/tests/agent_connector.py`:28, `projects/cs-agent/axia-seekapa-cs-agents/tests/function_tool_connector.py`:10
- `projects/campaign-analysis`
  - P2: local branches behind upstream: master
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
  - P3: spec `docs/superpowers/specs/2026-04-16-ffi-agent-scope-eval.md` classified STALLED (refs=0, age_days=4)
- `projects/campaign-analysis/Onesignal`
  - P2: local branches behind upstream: master
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
  - P2: hot-zone file `scripts/deploy_agent.py` appears in 6 fix commits in 30d without obvious parallel test change
- `projects/cs-agent`
  - P2: local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
  - P3: spec `docs/superpowers/specs/2026-03-25-chatwoot-handler-signal-escalation-design.md` classified ORPHAN (refs=0, age_days=37)
- `projects/cs-agent/axia-seekapa-cs-agents-devops`
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
  - P2: recent added lines match `debug_print` (72 hits); `scripts/eval_v108_against_prod.py`:16, `evals/scripts/v109_runner.py`:18, `evals/scripts/agent_endpoint_runner.py`:6
  - P2: recent added lines match `broad_exception` (33 hits); `scripts/eval_v108_against_prod.py`:16, `evals/scripts/v109_runner.py`:18, `evals/scripts/agent_endpoint_runner.py`:6
- `projects/figma-4-all`
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all/': Could not resolve host: dev.azure.com
- `projects/personal/jsq-slq`
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://github.com/ShovalBenjer/JSQ-SLQ.git/': Could not resolve host: github.com
- `projects/qc`
  - P2: local branches behind upstream: feat/align-test-connector-to-production, feat/v109-yasha-multilingual, fix/codex-ci-endpoint, fix/codex-foundry-agent, fix/escalation-perf-v39
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
  - P2: hot-zone file `azure-function-crm/chatwoot_handler/_gates.py` appears in 2 fix commits in 30d without obvious parallel test change
- `projects/qc/qc-telephony-api`
  - P2: local branches behind upstream: master
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api/': Could not resolve host: dev.azure.com
  - P2: recent added lines match `broad_exception` (7 hits); `src/api/function_app.py`:5, `src/api/shared/summary_agent_service.py`:1, `src/api/shared/qa_agent_service.py`:1
- `projects/seekapa-training-platform`
  - P2: local branches behind upstream: master
  - P2: recent added lines match `debug_print` (1 hits); `frontend/tests/e2e/live-prod-smoke.spec.ts`:2
  - P3: spec `docs/superpowers/specs/2026-03-29-email-reliability-scoring-fix-design.md` classified STALLED (refs=1, age_days=19)
- `projects/social-intelligence-unit`
  - P2: `git ls-remote --heads origin` failed: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit/': Could not resolve host: dev.azure.com
  - P3: spec `docs/superpowers/specs/2026-03-26-foundry-agent-orchestration-design.md` classified ORPHAN (refs=0, age_days=37)
  - P3: spec `docs/superpowers/specs/2026-04-14-heygen-v3-aca-integration.md` classified STALLED (refs=1, age_days=18)
- `projects/social-intelligence-unit/src/seekapa-video`
  - P2: configured `bun run lint` failed rc=1; first line: ~/projects/social-intelligence-unit/src/seekapa-video/src/Root.tsx

## ACTIONABLE_NEXT_STEPS
- Refresh Azure DevOps CLI credentials for `https://dev.azure.com/Corp-domain` (`az devops login` or tenant-approved AAD flow) and rerun C02 for PR/branch/pipeline coverage.
- Investigate P1: `projects/seekapa-training-platform` - pipeline `.github/workflows/e2e-tests.yml` contains `continue-on-error: true`

## VERIFICATION_EVIDENCE
- `rtk az account show --query {tenantId:tenantId,user:user.name} -o json` returned rc=0 before this script; Azure account exists, but Azure DevOps commands returned auth-needs-refresh.
- `rtk az repos list --organization https://dev.azure.com/Corp-domain --project Corp-AI --query [].name -o tsv` rc=1 (Azure DevOps repo listing auth check): Azure DevOps CLI reported login required before DevOps commands can run.
- `rtk uv run ruff check (cwd projects/campaign-analysis)` rc=0 (configured Python ruff check): All checks passed!
- `rtk bun run lint (cwd projects/social-intelligence-unit/src/seekapa-video)` rc=1 (configured JS/TS lint check): ~/projects/social-intelligence-unit/src/seekapa-video/src/Root.tsx /   28:7   warning  Unused eslint-disable directive (no problems were reported from 'global-require') /   29:44  error    A `require()` style import is forbidden                                            @typescript-eslint/no-require-imports /  / ~/projects/social-intelligence-unit...
