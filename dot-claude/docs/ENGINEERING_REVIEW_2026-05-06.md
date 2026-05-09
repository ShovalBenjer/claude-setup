# Engineering Review Sweep - 2026-05-06

Automation id: `c02-engineering-review-sweep`
Run timestamp UTC: `20260506T171532Z`
Workspace root: `/home/shovalbe`

## EXECUTIVE_SUMMARY

- Local repos scanned: 17 git roots under `/home/shovalbe/projects`.
- Specs scanned: 44 markdown specs across home/project spec directories.
- Static/lint commands attempted where configured: 3.
- Azure DevOps remote coverage: auth-needs-refresh; repos returned `0`, active PRs returned `0`.
- Highest-confidence local risks: lint failures/unavailable scripts, recent source changes without matching tests, generated/dependency directories inside repo trees, and pipeline YAML auth/eval guardrail risks.

### BLOCKED
- Azure DevOps CLI remote coverage unavailable; recorded auth/network/tooling failure and continued local analysis.
- Evidence: `az repos list` rc `1`; `az repos pr list --status active` rc `1`; sample: `ERROR: Before you can run Azure DevOps commands, you need to run the login command(az login if using AAD/MSA identity else az devops login if using PAT token) to setup credentials.  Please see https://aka.ms/azure-devops`.

## AZURE_DEVOPS_REMOTE_COVERAGE

- Organization/project configured: `https://dev.azure.com/Corp-domain` / `Corp-AI`.
- `az account show` rc `0`.
- `az account show` may succeed while Azure DevOps commands still fail; recorded status: `auth-needs-refresh`.
- Active PRs, stale PRs, remote branches older than 30 days, and uncloned ADO repos could not be enumerated in this run.
- No ADO comments or work items were created because no high-confidence P0/P1 remote finding could be tied to an open PR in this unattended run.

## LOCAL_REPO_COVERAGE

- `projects`: branch `feat/v109-yasha-multilingual`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`, status `dirty`, remote heads read `0` rc `128`.
- `projects/.archive/claude-orchestration`: branch `master`, origin `NO_ORIGIN`, status `clean`, remote heads read `0` rc `n/a`.
- `projects/.archive/el-vadt`: branch `master`, origin `NO_ORIGIN`, status `clean`, remote heads read `0` rc `n/a`.
- `projects/ORM-AGENT`: branch `main`, origin `NO_ORIGIN`, status `dirty`, remote heads read `0` rc `n/a`.
- `projects/_inherited/automation-fabric`: branch `main`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/automation-fabric`, status `dirty`, remote heads read `0` rc `128`.
- `projects/_inherited/market-daily-reports`: branch `master`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/market-daily-reports`, status `clean`, remote heads read `0` rc `128`.
- `projects/campaign-analysis`: branch `fix/bare-url-mcp-alias`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis`, status `dirty`, remote heads read `0` rc `128`.
- `projects/campaign-analysis/Onesignal`: branch `fix/bare-url-mcp-alias`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis`, status `dirty`, remote heads read `0` rc `128`.
- `projects/cs-agent`: branch `feat/v109-yasha-multilingual`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`, status `dirty`, remote heads read `0` rc `128`.
- `projects/cs-agent/axia-seekapa-cs-agents-devops`: branch `feat/v110-account-verification`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`, status `dirty`, remote heads read `0` rc `128`.
- `projects/figma-4-all`: branch `fix/land-bleed-port-disclaimer-ui-simplify`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all`, status `dirty`, remote heads read `0` rc `128`.
- `projects/personal/jsq-slq`: branch `main`, origin `https://github.com/ShovalBenjer/JSQ-SLQ.git`, status `dirty`, remote heads read `0` rc `128`.
- `projects/qc`: branch `feat/v109-yasha-multilingual`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`, status `dirty`, remote heads read `0` rc `128`.
- `projects/qc/qc-telephony-api`: branch `hotfix/notify-bot-prefix-and-soft-fail`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api`, status `clean`, remote heads read `0` rc `128`.
- `projects/seekapa-training-platform`: branch `fix/add-weasyprint-dep`, origin `NO_ORIGIN`, status `dirty`, remote heads read `0` rc `n/a`.
- `projects/social-intelligence-unit`: branch `feat/video-generation-gemini-remotion-heygen`, origin `https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit`, status `dirty`, remote heads read `0` rc `128`.
- `projects/social-intelligence-unit/src/seekapa-video`: branch `master`, origin `NO_ORIGIN`, status `dirty`, remote heads read `0` rc `n/a`.

## SPEC_AND_DOCS_DRIFT

- `docs/specs/2026-04-15-silver-eval-dataset.md`: `ORPHAN`
- `docs/specs/2026-04-28-v108-yasha-intake-flow.md`: `ACTIVE`
- `docs/specs/2026-05-04-frontier-governance-axes.md`: `STALLED`
- `docs/specs/2026-05-04-pst-extraction-v1-run.md`: `STALLED`
- `projects/campaign-analysis/docs/specs/2026-04-07-agent_scoring_round6.md`: `ACTIVE`
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_common.md`: `ACTIVE`
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_prefetch.md`: `STALLED`
- `projects/campaign-analysis/docs/specs/2026-04-07-batch_score_global.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-03-30-call-analyzer-agent-v9-design.md`: `ACTIVE`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-16-ffi-agent-scope-eval.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-18-ffi-v2-structured-agents.md`: `MERGED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-crm-call-analyser-redeploy.md`: `ACTIVE`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-live-batch-pipeline-design.md`: `MERGED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-components.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-design.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-eval.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-flow.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-19-mfm-workflow-readable-output-and-eval.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-20-mfm-multiagent-redesign.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-mcp-narrow-ship.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-gates-and-tests.md`: `MERGED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-retrieval-and-memory.md`: `ORPHAN`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-23-two-agent-foundry-native-redesign.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-cja-v2-mcp-alignment.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-m365-copilot-ui-widgets-ux-edit.md`: `MERGED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-04-28-mcp-seekapa-tools-v2.md`: `MERGED`
- `projects/campaign-analysis/docs/superpowers/specs/2026-05-02-whatsapp-impact.md`: `STALLED`
- `projects/campaign-analysis/docs/superpowers/specs/archive/2026-04-20-mfm-async-chat-design.superseded.md`: `MERGED`
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-15-silver-eval-dataset.md`: `ORPHAN`
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-28-v108-yasha-intake-flow.md`: `ACTIVE`
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-29-v109-yasha-multilingual-intake.md`: `MERGED`
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-05-06-seekapa-account-verification-flow.md`: `MERGED`
- `projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-05-06-v110-deploy-runbook.md`: `MERGED`
- `projects/cs-agent/docs/specs/2026-04-18-align-test-connector-to-production.md`: `STALLED`
- `projects/cs-agent/docs/specs/2026-04-23-seekapa-prompt-v101-compact-style-kb-routing.md`: `STALLED`
- `projects/cs-agent/docs/specs/2026-04-28-v108-yasha-intake-flow.md`: `ACTIVE`
- `projects/cs-agent/docs/superpowers/specs/2026-03-25-chatwoot-handler-signal-escalation-design.md`: `ACTIVE`
- `projects/docs/superpowers/specs/2026-04-25-ink-tui-next-level-forge-overlay.md`: `STALLED`
- `projects/qc/qc-telephony-api/docs/specs/2026-04-28-no-storage-qa.md`: `STALLED`
- `projects/seekapa-training-platform/docs/superpowers/specs/2026-03-29-email-reliability-scoring-fix-design.md`: `STALLED`
- `projects/seekapa-training-platform/docs/superpowers/specs/2026-04-05-email-session-lifecycle-refactor-design.md`: `STALLED`
- `projects/social-intelligence-unit/docs/superpowers/specs/2026-03-26-foundry-agent-orchestration-design.md`: `MERGED`
- `projects/social-intelligence-unit/docs/superpowers/specs/2026-04-14-heygen-v3-aca-integration.md`: `STALLED`
- `projects/social-intelligence-unit/docs/superpowers/specs/2026-05-06-inhouse-video-pipeline-pivot.md`: `STALLED`

CLAUDE.md quick-scan:
- `.claude/CLAUDE.md`: contains non-bun JS command reference
- `projects/_inherited/automation-fabric/CLAUDE.md`: contains non-bun JS command reference
- `projects/campaign-analysis/CLAUDE.md`: no obvious path/command drift in quick scan
- `projects/cs-agent/CLAUDE.md`: no obvious path/command drift in quick scan
- `projects/qc/CLAUDE.md`: no obvious path/command drift in quick scan
- `projects/qc/qc-telephony-api/CLAUDE.md`: no obvious path/command drift in quick scan
- `projects/seekapa-training-platform/CLAUDE.md`: contains non-bun JS command reference
- `projects/social-intelligence-unit/CLAUDE.md`: contains non-bun JS command reference

## FOUNDRY_PROMPT_DRIFT

- SDK probe: `azure.ai.projects import available`.
- Live Foundry prompt comparison was not performed because unattended auth/SDK project routing was not safely established. This is a drift blind spot, not a clean bill of health.
- `projects/campaign-analysis` prompt candidates: `no prompt files found by expected patterns`. live Foundry compare skipped: SDK/auth path not validated in this unattended run.
- `projects/cs-agent` prompt candidates: `no prompt files found by expected patterns`. live Foundry compare skipped: SDK/auth path not validated in this unattended run.

## CODE_QUALITY

### projects
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/send_daily_briefing_test.py:143: except Exception:`
  - `projects/_inherited/automation-fabric/src/runtime/function_app.py:3830: except Exception:`
  - `projects/_inherited/automation-fabric/src/runtime/function_app.py:4238: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/campaign-analysis/agent_scoring_runtime.py:415: print("Runtime self-tests passed.")`
  - `projects/campaign-analysis/callanalyzer_pipeline.py:1162: print("=== CallAnalyzer Pipeline v2 (Professional Excel) ===\n")`
  - `projects/campaign-analysis/callanalyzer_pipeline.py:1164: print("[1/4] Loading and joining data...")`
- Scan `disabled-eval` hits: 10 sample(s).
  - `projects/.archive/Oded/archive/sentimark/function_app.py:8757: f"[Evaluation] Complete. Evaluated: {evaluated}, Skipped: {skipped}, "`
  - `projects/.archive/Oded/archive/sentimark/function_app.py:21253: "[PaperTradeEval] Complete: evaluated=%d, skipped=%d, errors=%d",`
  - `projects/.archive/Oded/archive/sentimark-docker-deploy/function_app.py:8757: f"[Evaluation] Complete. Evaluated: {evaluated}, Skipped: {skipped}, "`
- Scan `emoji` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:28: "en": "🚨 SPECIAL EDITION: War Impact — Seekapa Market Overview",`
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:29: "ar": "🚨 عدد خاص: تأثير الحرب — نظرة سيكابا على الأسواق",`
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:30: "es": "🚨 EDICIÓN ESPECIAL: Impacto Bélico — Seekapa Resumen del Mercado",`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:36: animation: none !important;`
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:37: transition: none !important;`
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:42: -webkit-print-color-adjust: exact !important;`
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/_inherited/automation-fabric/src/container-app/pipeline_orchestrator.py:348: await asyncio.sleep(self.config.video_rate_limit_seconds)`
  - `projects/_inherited/automation-fabric/src/runtime/send_test_premium_email.py:243: time.sleep(5)`
### projects/.archive/claude-orchestration
- Scan `added-any` hits: 3 sample(s).
  - `projects/.archive/claude-orchestration/azdo-mcp/tests/setup.ts:28: global.console.log = (...args: any[]) => {`
  - `projects/.archive/claude-orchestration/azdo-mcp/tests/setup.ts:37: global.console.warn = (...args: any[]) => {`
  - `projects/.archive/claude-orchestration/azdo-mcp/tests/setup.ts:43: global.console.error = (...args: any[]) => {`
- Scan `broad-except` hits: 5 sample(s).
  - `projects/.archive/claude-orchestration/legacy/claude-core/scripts/red_team_agent.py:503: except Exception:`
  - `projects/.archive/claude-orchestration/legacy/claude-core/scripts/job_runner.py:512: except Exception:`
  - `projects/.archive/claude-orchestration/legacy/claude-core/scripts/token_contract.py:495: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/.archive/claude-orchestration/legacy/launcher.py:19: print(f"{ts} {prefix} {msg}")`
  - `projects/.archive/claude-orchestration/legacy/launcher.py:81: print("=" * 40)`
  - `projects/.archive/claude-orchestration/legacy/launcher.py:82: print("Claude Code OS Launcher")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/.archive/claude-orchestration/legacy/claude-core/autonomous_loop.py:91: time.sleep(self.interval)`
  - `projects/.archive/claude-orchestration/legacy/claude-core/foundry_client.py:59: time.sleep(self.retry_delay * (2 ** attempt))`
  - `projects/.archive/claude-orchestration/legacy/claude-core/foundry_client.py:68: time.sleep(self.retry_delay * (2 ** attempt))`
### projects/.archive/el-vadt
- Scan `broad-except` hits: 10 sample(s).
  - `projects/.archive/el-vadt/sales-agents/scripts/agent_to_agent_voice_test.py:164: except Exception:`
  - `projects/.archive/el-vadt/sales-agents/src/database/service.py:77: except Exception:`
  - `projects/.archive/el-vadt/sales-agents/src/database/service.py:140: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/.archive/el-vadt/analysis/llm_extraction_template.py:55: print(f"Error analyzing {filepath}: {e}")`
  - `projects/.archive/el-vadt/analysis/llm_extraction_template.py:60: print("Please set OPENAI_API_KEY environment variable.")`
  - `projects/.archive/el-vadt/analysis/llm_extraction_template.py:66: print(f"Analyzing {len(files)} transcripts with GPT-4o...")`
- Scan `disabled-eval` hits: 2 sample(s).
  - `projects/.archive/el-vadt/sales-agents/scripts/test_evaluator.py:165: print(f"\nFull evaluator test skipped: {e}")`
  - `projects/.archive/el-vadt/sales-agents/src/testing/human_likeness_evaluator.py:486: logger.warning("openai package not installed, LLM evaluation disabled")`
- Scan `emoji` hits: 10 sample(s).
  - `projects/.archive/el-vadt/analysis/pattern_mining.py:106: f.write("🚨 CRITICAL AVOID ACTIONS:\n")`
  - `projects/.archive/el-vadt/sales-agents/braintrust-testing/run_evaluation.py:303: print("\n📊 Sending results to Braintrust...")`
  - `projects/.archive/el-vadt/sales-agents/braintrust-testing/transcript_analyzer.py:193: print(f"\n📥 Fetching transcripts for {agent['name']}...")`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/.archive/el-vadt/sales-agents/braintrust-testing/run_evaluation.py:239: await asyncio.sleep(1)`
  - `projects/.archive/el-vadt/sales-agents/scripts/test_extended_conversation.py:250: await asyncio.sleep(0.3)`
  - `projects/.archive/el-vadt/sales-agents/scripts/agent_to_agent_voice_test.py:373: await asyncio.sleep(0.05)`
### projects/ORM-AGENT
- Scan `added-any` hits: 10 sample(s).
  - `projects/ORM-AGENT/frontend/src/utils/sseParser.ts:9: // eslint-disable-next-line @typescript-eslint/no-explicit-any`
  - `projects/ORM-AGENT/frontend/src/utils/sseParser.ts:10: data: any;`
  - `projects/ORM-AGENT/frontend/src/utils/fileAttachments.ts:115: * Validate any file (image or document) based on its type.`
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 2 sample(s).
  - `projects/ORM-AGENT/frontend/src/contexts/AppContext.tsx:19: log: function (...args: unknown[]) { if (this.enabled) console.log(...args); },`
  - `projects/ORM-AGENT/.github/skills/validating-ui-features/test-files/code-sample.md:30: print(f"F({i}) = {fibonacci(i)}")`
- Scan `disabled-eval` hits: 1 sample(s).
  - `projects/ORM-AGENT/ORM-PLAN.md:190: 1. Run nightly 4-phase eval over 80 labeled comments per language. Goal: ≥85% triage accuracy on EN+AR, ≤2% false-positive auto-action rate.`
- Scan `emoji` hits: 10 sample(s).
  - `projects/ORM-AGENT/frontend/plugins/envcheck.ts:48: 📖 See the <a href="https://github.com/microsoft-foundry/foundry-agent-webapp#quick-start">README</a> for full setup instructions.`
  - `projects/ORM-AGENT/frontend/src/utils/__tests__/sseParser.test.ts:133: const line = 'data: {"type":"chunk","content":"Hello 世界 🌍"}';`
  - `projects/ORM-AGENT/frontend/src/utils/__tests__/sseParser.test.ts:136: expect(result?.data.content).toBe('Hello 世界 🌍');`
- Scan `high-z-index` hits: 1 sample(s).
  - `projects/ORM-AGENT/frontend/src/components/chat/UsageInfo.module.css:45: z-index: 1000;`
- Scan `important` hits: 7 sample(s).
  - `projects/ORM-AGENT/frontend/src/components/chat/ChatInput.module.css:47: background: transparent !important;`
  - `projects/ORM-AGENT/frontend/src/components/chat/ChatInput.module.css:53: background: var(--colorSubtleBackgroundHover) !important;`
  - `projects/ORM-AGENT/frontend/src/components/chat/ChatInput.module.css:58: background: var(--colorSubtleBackgroundPressed) !important;`
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/ORM-AGENT/frontend/src/utils/errorHandler.ts:169: await new Promise(resolve => setTimeout(resolve, delay));`
  - `projects/ORM-AGENT/frontend/src/services/chatService.ts:262: await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt - 1)));`
  - `projects/ORM-AGENT/frontend/src/services/chatService.ts:603: setTimeout(() => URL.revokeObjectURL(url), 100);`
### projects/_inherited/automation-fabric
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/automation-fabric/': Could not resolve host: dev.azure.com
- Scan `added-any` hits: 4 sample(s).
  - `projects/_inherited/automation-fabric/src/dashboard/scripts/global-teardown.ts:4: * This script runs after all tests complete to clean up any stale`
  - `projects/_inherited/automation-fabric/src/dashboard/__tests__/unit/ErrorBoundary.test.tsx:98: expect.any(Error),`
  - `projects/_inherited/automation-fabric/src/dashboard/__tests__/unit/ErrorBoundary.test.tsx:99: expect.objectContaining({ componentStack: expect.any(String) })`
- Scan `broad-except` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/send_daily_briefing_test.py:143: except Exception:`
  - `projects/_inherited/automation-fabric/src/runtime/function_app.py:3830: except Exception:`
  - `projects/_inherited/automation-fabric/src/runtime/function_app.py:4238: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/recon_page.py:18: print("1. Navigating to auth page...")`
  - `projects/_inherited/automation-fabric/recon_page.py:22: print(f"   Screenshot saved: {OUTPUT_DIR}/01_auth_page.png")`
  - `projects/_inherited/automation-fabric/recon_page.py:28: print(f"   HTML saved: {OUTPUT_DIR}/01_auth_page.html")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:28: "en": "🚨 SPECIAL EDITION: War Impact — Seekapa Market Overview",`
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:29: "ar": "🚨 عدد خاص: تأثير الحرب — نظرة سيكابا على الأسواق",`
  - `projects/_inherited/automation-fabric/src/runtime/war_edition_content.py:30: "es": "🚨 EDICIÓN ESPECIAL: Impacto Bélico — Seekapa Resumen del Mercado",`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:36: animation: none !important;`
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:37: transition: none !important;`
  - `projects/_inherited/automation-fabric/src/runtime/generate_oil_pdfs.py:42: -webkit-print-color-adjust: exact !important;`
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/_inherited/automation-fabric/src/container-app/pipeline_orchestrator.py:348: await asyncio.sleep(self.config.video_rate_limit_seconds)`
  - `projects/_inherited/automation-fabric/src/runtime/send_test_premium_email.py:243: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/minimal_email_test.py:29: time.sleep(5)`
### projects/_inherited/market-daily-reports
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/market-daily-reports/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 1 sample(s).
  - `projects/_inherited/market-daily-reports/src/runtime/activities/pdf_generator.py:188: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/_inherited/market-daily-reports/scripts/screenshot_pdfs.py:16: print(f"Found {len(pdf_files)} PDFs to convert\n")`
  - `projects/_inherited/market-daily-reports/scripts/screenshot_pdfs.py:19: print(f"Converting: {pdf_path.name}")`
  - `projects/_inherited/market-daily-reports/scripts/screenshot_pdfs.py:30: print(f"  -> {output_name} ({size_kb:.1f} KB)")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 10 sample(s).
  - `projects/_inherited/market-daily-reports/scripts/generate_sample_pdfs.py:190: {"emoji": "🟢", "likelihood": "Most Likely", "title": "Bullish Continuation", "description": "Industrial demand and dollar weakness push silver toward $32.", "ta`
  - `projects/_inherited/market-daily-reports/scripts/generate_sample_pdfs.py:191: {"emoji": "🟡", "likelihood": "Possible", "title": "Range Consolidation", "description": "Silver consolidates recent gains between $29-31.", "target": "Range: $2`
  - `projects/_inherited/market-daily-reports/scripts/generate_sample_pdfs.py:192: {"emoji": "🔴", "likelihood": "Risk Scenario", "title": "Sharp Pullback", "description": "Dollar strength or risk-off sentiment triggers correction.", "target": `
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 10 sample(s).
  - `projects/_inherited/market-daily-reports/scripts/convert_html_to_pdf.py:19: -webkit-print-color-adjust: exact !important;`
  - `projects/_inherited/market-daily-reports/scripts/convert_html_to_pdf.py:20: print-color-adjust: exact !important;`
  - `projects/_inherited/market-daily-reports/scripts/convert_html_to_pdf.py:24: animation: none !important;`
- Scan `sleep-poll` hits: 0 sample(s).
### projects/campaign-analysis
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 10 sample(s).
  - `projects/campaign-analysis/Onesignal/test_foundry_agent.py:104: except Exception:`
  - `projects/campaign-analysis/evals/compliance_evaluator.py:76: except Exception:`
  - `projects/campaign-analysis/evals/data_accuracy_evaluator.py:25: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/campaign-analysis/agent_scoring_runtime.py:415: print("Runtime self-tests passed.")`
  - `projects/campaign-analysis/callanalyzer_pipeline.py:1162: print("=== CallAnalyzer Pipeline v2 (Professional Excel) ===\n")`
  - `projects/campaign-analysis/callanalyzer_pipeline.py:1164: print("[1/4] Loading and joining data...")`
- Scan `disabled-eval` hits: 1 sample(s).
  - `projects/campaign-analysis/evals/run_eval.py:240: print("[eval] Langfuse not configured — skipping trace")`
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:69: time.sleep(wait)`
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:79: time.sleep(wait)`
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:234: time.sleep(TRANSCRIBE_DELAY)`
- Verification: `uv run ruff check` -> rc `0`; sample: All checks passed!
### projects/campaign-analysis/Onesignal
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 1 sample(s).
  - `projects/campaign-analysis/Onesignal/test_foundry_agent.py:104: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/campaign-analysis/Onesignal/test_foundry_agent.py:77: print(f"\n[{test_name}]")`
  - `projects/campaign-analysis/Onesignal/test_foundry_agent.py:78: print(f"Prompt: {prompt}")`
  - `projects/campaign-analysis/Onesignal/test_foundry_agent.py:79: print(f"URL: {url}")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 1 sample(s).
  - `projects/campaign-analysis/Onesignal/Social Media Automation with Claude   Copilot Studio   Azure AI Foundry.md:466: 22. [Connect Meta Graph API (Facebook/Instagram) To n8n - YouTube](https://www.youtube.com/watch?v=6XAErS9Q0oY) - Join our Free Skool community for Free n8n AI `
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 0 sample(s).
### projects/cs-agent
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/cs-agent/scripts/export_foundry_eval_to_md.py:257: print(f"Wrote {output_path}")`
  - `projects/cs-agent/scripts/export_foundry_eval_to_md.py:258: print(f"Runs exported: {len(runs)}")`
  - `projects/cs-agent/tests/live_bot_test.py:34: print("ERROR: WEBHOOK_URL not set")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/cs-agent/tests/live_bot_test.py:214: time.sleep(1)`
  - `projects/cs-agent/tests/live_bot_test.py:297: time.sleep(2)`
  - `projects/cs-agent/axia-seekapa-cs-agents/tests/escalation_test_runner.py:121: await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS - elapsed)`
### projects/cs-agent/axia-seekapa-cs-agents-devops
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 10 sample(s).
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/tests/create_qa_report_v2.py:195: except Exception:`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/tests/create_qa_report.py:28: except Exception:`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/tests/qa_scenarios_list.py:27: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/test_webhook_live.py:51: print(f"  [{'PASS' if ok else 'FAIL'}] Ping (non-message event): HTTP {result['status']}")`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/test_webhook_live.py:53: print(f"         Body: {result['body']}")`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/test_webhook_live.py:69: print(f"  [{'PASS' if ok else 'FAIL'}] Empty content skipped: HTTP {result['status']}")`
- Scan `disabled-eval` hits: 1 sample(s).
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/foundry_eval_gate.py:237: f'<testsuite name="foundry-smoke-eval" tests="{len(results)}" failures="{failures}" errors="0" skipped="0">'`
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/foundry_cost_audit.py:83: time.sleep(wait)`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_v108_against_prod.py:54: time.sleep(2 ** attempt)  # 1, 2, 4, 8s backoff`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_v108_against_prod.py:176: time.sleep(0.8)  # gentle throttle to avoid Foundry rate-limit 500s`
### projects/figma-4-all
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/figma-4-all/plugin/plugin.js:4: (()=>{var Pt=Object.defineProperty;var Dt=(l,e,t)=>e in l?Pt(l,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):l[e]=t;var M=(l,e,t)=>Dt(l,typeof e!="symb`
  - `projects/figma-4-all/plugin/plugin.js:233: var original={log:console.log.bind(console),warn:console.warn.bind(console),error:console.error.bind(console)};`
  - `projects/figma-4-all/plugin/plugin.js:271: console.log=function(){uiLog.info.apply(null,arguments);};`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 8 sample(s).
  - `projects/figma-4-all/plugin/plugin.js:4: (()=>{var Pt=Object.defineProperty;var Dt=(l,e,t)=>e in l?Pt(l,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):l[e]=t;var M=(l,e,t)=>Dt(l,typeof e!="symb`
  - `projects/figma-4-all/plugin/plugin.js:300: busyTimeout=setTimeout(function(){`
  - `projects/figma-4-all/plugin/plugin.js:402: var timer=setTimeout(function(){`
### projects/personal/jsq-slq
- Remote read check failed for origin: fatal: unable to access 'https://github.com/ShovalBenjer/JSQ-SLQ.git/': Could not resolve host: github.com
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 0 sample(s).
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 5 sample(s).
  - `projects/personal/jsq-slq/README.md:200: *   `[🔄]` **Comprehensive Documentation:** The model and findings are being documented for publication and wider use.`
  - `projects/personal/jsq-slq/README.md:205: *   `[🗓️]` **Integration with Real-World Traffic Data:**`
  - `projects/personal/jsq-slq/README.md:209: *   `[🗓️]` **Expansion to Multi-Intersection Networks:**`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 0 sample(s).
### projects/qc
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/qc/qc-telephony-api/tests/e2e/test_qa_quality.py:287: print(f"\nWithout translations: {response_no_trans.answer[:100]}...")`
  - `projects/qc/qc-telephony-api/tests/e2e/test_qa_quality.py:288: print(f"With translations: {response_with_trans.answer[:100]}...")`
  - `projects/qc/qc-telephony-api/tests/e2e/metrics/report_generator.py:247: print("\n" + "=" * 60)`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 2 sample(s).
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/qc/qc-telephony-api/docs/wiki/QC-Telephony.md:276: <button onclick="const el=this.parentElement.nextElementSibling; navigator.clipboard.writeText(el.innerText); this.textContent='Copied'; setTimeout(()=&gt;this.`
### projects/qc/qc-telephony-api
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api/': Could not resolve host: dev.azure.com
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/qc/qc-telephony-api/tests/e2e/test_qa_quality.py:287: print(f"\nWithout translations: {response_no_trans.answer[:100]}...")`
  - `projects/qc/qc-telephony-api/tests/e2e/test_qa_quality.py:288: print(f"With translations: {response_with_trans.answer[:100]}...")`
  - `projects/qc/qc-telephony-api/tests/e2e/metrics/report_generator.py:247: print("\n" + "=" * 60)`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 0 sample(s).
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 2 sample(s).
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/qc/qc-telephony-api/docs/wiki/QC-Telephony.md:276: <button onclick="const el=this.parentElement.nextElementSibling; navigator.clipboard.writeText(el.innerText); this.textContent='Copied'; setTimeout(()=&gt;this.`
### projects/seekapa-training-platform
- Scan `added-any` hits: 10 sample(s).
  - `projects/seekapa-training-platform/frontend/src/types/index.ts:33: [key: string]: any;`
  - `projects/seekapa-training-platform/frontend/src/mocks/sessionDetailMock.ts:87: text: 'agent: Hello, thank you for calling Seekapa! My name is Sarah. How can I help you today?\nuser: Hi, I am interested in opening a trading account, but I a`
  - `projects/seekapa-training-platform/frontend/src/mocks/sessionDetailMock.ts:127: 'Of course! The withdrawal formula takes into account your account balance, any active trades, and applicable fees. It is all outlined in your account dashboard`
- Scan `broad-except` hits: 2 sample(s).
  - `projects/seekapa-training-platform/backend/backfill_arabic_emails/__init__.py:46: except Exception:`
  - `projects/seekapa-training-platform/backend/personal_stats/__init__.py:109: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:82: print("Error: ELEVENLABS_API_KEY not set in environment")`
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:92: print("📥 Fetching original prompt from ElevenLabs...")`
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:130: print("🚀 Deploying fix to ElevenLabs...")`
- Scan `disabled-eval` hits: 1 sample(s).
  - `projects/seekapa-training-platform/backend/backfill_arabic_emails/__init__.py:11: re_evaluate: bool (default false) - Re-run LLM evaluation before sending`
- Scan `emoji` hits: 10 sample(s).
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:25: ## 🔐 أبداً لا تكشف إنك وكيل تدريب`
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:70: **🚨 قاعدة نهائية صارمة:**`
  - `projects/seekapa-training-platform/scripts/fix_arabic_level4_standalone.py:92: print("📥 Fetching original prompt from ElevenLabs...")`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 2 sample(s).
  - `projects/seekapa-training-platform/docs/reference/D3JS_RADAR_BAR_CHARTS_EXAMPLE.js:590: font-size: 10px !important;`
  - `projects/seekapa-training-platform/docs/reference/D3JS_RADAR_BAR_CHARTS_EXAMPLE.js:602: font-size: 9px !important;`
- Scan `sleep-poll` hits: 10 sample(s).
  - `projects/seekapa-training-platform/scripts/sync_and_email_today.py:360: time.sleep(2)`
  - `projects/seekapa-training-platform/scripts/email_arabic_reports_nissreen.py:255: time.sleep(EMAIL_DELAY_SECONDS)`
  - `projects/seekapa-training-platform/scripts/email_arabic_reports_nissreen.py:263: time.sleep(wait)`
### projects/social-intelligence-unit
- Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit/': Could not resolve host: dev.azure.com
- ruff check failed or unavailable (rc=1).
- Scan `broad-except` hits: 3 sample(s).
  - `projects/social-intelligence-unit/scripts/check_system.py:49: except Exception:`
  - `projects/social-intelligence-unit/scripts/import_raw_runs.py:82: except Exception:`
  - `projects/social-intelligence-unit/scripts/backfill_geo_from_platform_meta.py:21: except Exception:`
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/social-intelligence-unit/.kilocode/kilo.py:24: print(f"Error: Kilo orchestrator script not found at {ORCHESTRATOR_SCRIPT}")`
  - `projects/social-intelligence-unit/scripts/dedupe_video_job_outputs.py:66: print(`
  - `projects/social-intelligence-unit/scripts/abort_run.py:12: print("Error: APIFY_TOKEN environment variable not set")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 10 sample(s).
  - `projects/social-intelligence-unit/scripts/generate-videos-from-db.py:29: print(f"📊 Connecting to database: {DB_PATH}")`
  - `projects/social-intelligence-unit/scripts/generate-videos-from-db.py:71: print("💡 Using sample briefs instead...\n")`
  - `projects/social-intelligence-unit/scripts/generate-videos-from-db.py:147: print(f"📹 Generating video for: {brief['brief_id']}")`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 9 sample(s).
  - `projects/social-intelligence-unit/scripts/execute_18_runs_latam.py:225: time.sleep(2)`
  - `projects/social-intelligence-unit/scripts/ab_test_tiktok_freshness.py:93: time.sleep(10)`
  - `projects/social-intelligence-unit/scripts/backfill_enrich.py:104: time.sleep(1.0 / RATE_LIMIT)`
- Verification: `uv run ruff check` -> rc `1`; sample: Building siu @ file:///home/shovalbe/projects/social-intelligence-unit |   × Failed to build `siu @ |   │ file:///home/shovalbe/projects/social-intelligence-unit`
### projects/social-intelligence-unit/src/seekapa-video
- bun run lint failed or unavailable (rc=1).
- Scan `added-any` hits: 10 sample(s).
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/generate-avatar.ts:32: parsed.brand = args[++i] as any;`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/generate-avatar.ts:34: parsed.language = args[++i] as any;`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/validate-ffprobe.ts:43: const video = info.streams?.find((s: any) => s.codec_type === "video");`
- Scan `broad-except` hits: 0 sample(s).
- Scan `continue-on-error` hits: 0 sample(s).
- Scan `debug-print` hits: 10 sample(s).
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/verify_voiceover.py:22: print("ERROR: whisper not installed. Run: pip install openai-whisper")`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/verify_voiceover.py:88: print(f"Transcribing {args.audio} with Whisper ({args.model})...")`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/verify_voiceover.py:93: print(f"Extracted {len(word_timings)} words")`
- Scan `disabled-eval` hits: 0 sample(s).
- Scan `emoji` hits: 8 sample(s).
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/templates.ts:168: 📲 SIGNAL ALERT`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:345: console.log(`📹 ${report.title}`);`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:393: console.log('🎬 Video Generation & Inspection Workflow\n');`
- Scan `high-z-index` hits: 0 sample(s).
- Scan `important` hits: 0 sample(s).
- Scan `sleep-poll` hits: 6 sample(s).
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/heygen.ts:184: await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/elevenlabs-creative.ts:498: await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:41: const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));`
- Verification: `bun run lint` -> rc `1`; sample: /home/shovalbe/projects/social-intelligence-unit/src/seekapa-video/src/Root.tsx |   28:7   warning  Unused eslint-disable directive (no problems were reported from 'global-require') |   29:44  error    A `require()` style import is forbidden                                            @typescript-esl

Duplicate commit subjects by author across distinct SHAs:
- `fix(lint): ruff I001 + UP035 in v110 verification-flow imports` by `Shoval Be` appears 3 times; SHAs 5c2e09ac, 5c2e09ac, 5c2e09ac; repos projects, projects/cs-agent, projects/qc
- `feat(seekapa): v110 account-verification flow + KB additions` by `Shoval Benjer` appears 4 times; SHAs 8e5604ca, 8e5604ca, 8e5604ca, 8e5604ca; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `Merged PR 215: feat(seekapa): v109.5 — Yasha-style canonicals + FAQ-in-wiki + geography anchors` by `Shoval Benjer` appears 3 times; SHAs 35352ab2, 35352ab2, 35352ab2; repos projects, projects/cs-agent, projects/qc
- `docs(wiki): FAQ + Knowledge Base + Markets pages — wiki reachability for KB content` by `Shoval Benjer` appears 4 times; SHAs 422c3333, 422c3333, 422c3333, 422c3333; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `feat(seekapa): v109.5 — Yasha-style canonical replies refinement (post-prod-test review)` by `Shoval Benjer` appears 4 times; SHAs 5f7b23f6, 5f7b23f6, 5f7b23f6, 5f7b23f6; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `Merged PR 213: fix(ci): Notify bash hotfix + deploy script api refactor + v109 acceptance scorecard` by `Shoval Benjer` appears 4 times; SHAs cc0306ef, cc0306ef, cc0306ef, cc0306ef; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `fix(ci): Notify bash hotfix + deploy script api refactor + v109 acceptance scorecard` by `Shoval Benjer` appears 4 times; SHAs cb98f92d, cb98f92d, cb98f92d, cb98f92d; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `Merged PR 211: feat(seekapa): v109.2 — prompt optimize (-22%) + Telegram CI notifications + deploy guard` by `Shoval Benjer` appears 4 times; SHAs 0a695235, 0a695235, 0a695235, 0a695235; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `fix(lint): _pre_classifier.py — ruff UP045 + SIM110 + E501` by `Shoval Benjer` appears 4 times; SHAs f0005687, f0005687, f0005687, f0005687; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `feat(seekapa): v109.3 modularization — pre-LLM classifier + AR/ES/PT sanitizer + EXAMPLES split` by `Shoval Benjer` appears 4 times; SHAs ec6a497d, ec6a497d, ec6a497d, ec6a497d; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `fix(ci): Notify stage — pin pool to ubuntu-latest, gate to master deploys only` by `Shoval Benjer` appears 4 times; SHAs 4fc5a445, 4fc5a445, 4fc5a445, 4fc5a445; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `feat(seekapa): v109.2 — prompt optimization (23k→18k, -22%) + Telegram CI notifications + deploy-script silent-fail guard` by `Shoval Benjer` appears 4 times; SHAs b25ab1d6, b25ab1d6, b25ab1d6, b25ab1d6; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `Merged PR 210: feat(seekapa): v109.1 — forbidden phrases + chat-regurgitation rebuff + invariants + baseline` by `Shoval Benjer` appears 4 times; SHAs 3b8a6312, 3b8a6312, 3b8a6312, 3b8a6312; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `fix(seekapa): v109.1 review-fix sweep — case-6/case-11 collision, opener-only forbidden tests, AR/ES/PT enforcement, REPO path` by `Shoval Benjer` appears 4 times; SHAs 91878138, 91878138, 91878138, 91878138; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `feat(seekapa): v109.1 prompt patch — forbidden phrases + chat-regurgitation rebuff + 4 invariants + 5 eval rows + baseline scorecard` by `Shoval Benjer` appears 4 times; SHAs 3a8e1db5, 3a8e1db5, 3a8e1db5, 3a8e1db5; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `docs(wiki): reflect v108 live + v109 staged — Live-vs-Source matrix, AC table, deploy protocol` by `Shoval Benjer` appears 4 times; SHAs 0353e1be, 0353e1be, 0353e1be, 0353e1be; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `chore(repo): cleanup v109 working tree — gitignore eval-run dirs, commit pending docs/tests, remove obsolete PRODUCTION_* tests` by `Shoval Benjer` appears 4 times; SHAs d76d25b4, d76d25b4, d76d25b4, d76d25b4; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `Merged PR 201: feat(seekapa): v109 yasha multilingual + v2 escalation behaviors` by `Shoval Benjer` appears 4 times; SHAs 2ab2d191, 2ab2d191, 2ab2d191, 2ab2d191; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `feat(seekapa): v109 yasha multilingual + repetitive-failure + identity-guard` by `Shoval Benjer` appears 4 times; SHAs c7195071, c7195071, c7195071, c7195071; repos projects, projects/cs-agent, projects/cs-agent/axia-seekapa-cs-agents-devops, projects/qc
- `On feat/align-test-connector-to-production: v109-session-home-mods` by `Shoval Be` appears 3 times; SHAs 2bd8a022, 2bd8a022, 2bd8a022; repos projects, projects/cs-agent, projects/qc

## TEST_AND_EVAL_GATES

- `projects/seekapa-training-platform/.github/workflows/e2e-tests.yml`: continue-on-error true
- `projects/social-intelligence-unit/.github/workflows/ci.yml`: continue-on-error true
- Diff-level eval gate weakening was approximated from local 14-day changed files and pipeline text scans; ADO pipeline run history was unavailable due DevOps auth refresh need.

## PERFORMANCE_AND_LATENCY

- `projects` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/_inherited/automation-fabric/src/container-app/pipeline_orchestrator.py:348: await asyncio.sleep(self.config.video_rate_limit_seconds)`
  - `projects/_inherited/automation-fabric/src/runtime/send_test_premium_email.py:243: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/minimal_email_test.py:29: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/send_simple_test.py:59: time.sleep(5)`
- `projects/.archive/claude-orchestration` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/.archive/claude-orchestration/legacy/claude-core/autonomous_loop.py:91: time.sleep(self.interval)`
  - `projects/.archive/claude-orchestration/legacy/claude-core/foundry_client.py:59: time.sleep(self.retry_delay * (2 ** attempt))`
  - `projects/.archive/claude-orchestration/legacy/claude-core/foundry_client.py:68: time.sleep(self.retry_delay * (2 ** attempt))`
  - `projects/.archive/claude-orchestration/legacy/claude-core/scripts/budget_logger.py:99: time.sleep(args.interval)`
  - `projects/.archive/claude-orchestration/legacy/claude-core/scripts/state_watcher.py:195: time.sleep(1)`
- `projects/.archive/el-vadt` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/.archive/el-vadt/sales-agents/braintrust-testing/run_evaluation.py:239: await asyncio.sleep(1)`
  - `projects/.archive/el-vadt/sales-agents/scripts/test_extended_conversation.py:250: await asyncio.sleep(0.3)`
  - `projects/.archive/el-vadt/sales-agents/scripts/agent_to_agent_voice_test.py:373: await asyncio.sleep(0.05)`
  - `projects/.archive/el-vadt/sales-agents/scripts/agent_to_agent_voice_test.py:472: await asyncio.sleep(0.5)`
  - `projects/.archive/el-vadt/sales-agents/scripts/agent_to_agent_voice_test.py:546: await asyncio.sleep(0.01)`
- `projects/ORM-AGENT` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/ORM-AGENT/frontend/src/utils/errorHandler.ts:169: await new Promise(resolve => setTimeout(resolve, delay));`
  - `projects/ORM-AGENT/frontend/src/services/chatService.ts:262: await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt - 1)));`
  - `projects/ORM-AGENT/frontend/src/services/chatService.ts:603: setTimeout(() => URL.revokeObjectURL(url), 100);`
  - `projects/ORM-AGENT/frontend/src/components/ConversationSidebar.tsx:163: debounceRef.current = setTimeout(() => {`
  - `projects/ORM-AGENT/frontend/src/components/ChatInterface.tsx:106: const timer = setTimeout(() => setLiveRegionMessage(''), 1000);`
- `projects/_inherited/automation-fabric` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/_inherited/automation-fabric/src/container-app/pipeline_orchestrator.py:348: await asyncio.sleep(self.config.video_rate_limit_seconds)`
  - `projects/_inherited/automation-fabric/src/runtime/send_test_premium_email.py:243: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/minimal_email_test.py:29: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/send_simple_test.py:59: time.sleep(5)`
  - `projects/_inherited/automation-fabric/src/runtime/send_v10_test.py:79: time.sleep(2)`
- `projects/campaign-analysis` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:69: time.sleep(wait)`
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:79: time.sleep(wait)`
  - `projects/campaign-analysis/agent-batch/batch_fetch.py:234: time.sleep(TRANSCRIBE_DELAY)`
  - `projects/campaign-analysis/scripts/enrich_excel.py:152: time.sleep(wait)`
  - `projects/campaign-analysis/scripts/enrich_excel.py:178: time.sleep(5)`
- `projects/cs-agent` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/cs-agent/tests/live_bot_test.py:214: time.sleep(1)`
  - `projects/cs-agent/tests/live_bot_test.py:297: time.sleep(2)`
  - `projects/cs-agent/axia-seekapa-cs-agents/tests/escalation_test_runner.py:121: await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS - elapsed)`
  - `projects/cs-agent/axia-seekapa-cs-agents/tests/escalation_test_runner.py:175: await asyncio.sleep(wait_time)`
  - `projects/cs-agent/axia-seekapa-cs-agents/tests/escalation_test_runner.py:182: await asyncio.sleep(delay)`
- `projects/cs-agent/axia-seekapa-cs-agents-devops` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/foundry_cost_audit.py:83: time.sleep(wait)`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_v108_against_prod.py:54: time.sleep(2 ** attempt)  # 1, 2, 4, 8s backoff`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_v108_against_prod.py:176: time.sleep(0.8)  # gentle throttle to avoid Foundry rate-limit 500s`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_multilang.py:86: time.sleep(_backoff(attempt))`
  - `projects/cs-agent/axia-seekapa-cs-agents-devops/scripts/eval_multilang.py:92: time.sleep(_backoff(attempt))`
- `projects/figma-4-all` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/figma-4-all/plugin/plugin.js:4: (()=>{var Pt=Object.defineProperty;var Dt=(l,e,t)=>e in l?Pt(l,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):l[e]=t;var M=(l,e,t)=>Dt(l,typeof e!="symb`
  - `projects/figma-4-all/plugin/plugin.js:300: busyTimeout=setTimeout(function(){`
  - `projects/figma-4-all/plugin/plugin.js:402: var timer=setTimeout(function(){`
  - `projects/figma-4-all/plugin/plugin.js:1017: `;l.showUI(s,{width:z().UI.w,height:z().UI.h}),setTimeout(n,3e3),ue.initialize().then(function(){try{var o=l.currentPage&&l.currentPage.selection?l.currentPage.`
  - `projects/figma-4-all/plugin/src/infrastructure/agent-service.js:52: var timeoutId = setTimeout(function() { controller.abort(); }, this.timeoutMs);`
- `projects/qc` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/qc/qc-telephony-api/docs/wiki/QC-Telephony.md:276: <button onclick="const el=this.parentElement.nextElementSibling; navigator.clipboard.writeText(el.innerText); this.textContent='Copied'; setTimeout(()=&gt;this.`
- `projects/qc/qc-telephony-api` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/qc/qc-telephony-api/tests/test_session_memory.py:171: time.sleep(1.1)`
  - `projects/qc/qc-telephony-api/docs/wiki/QC-Telephony.md:276: <button onclick="const el=this.parentElement.nextElementSibling; navigator.clipboard.writeText(el.innerText); this.textContent='Copied'; setTimeout(()=&gt;this.`
- `projects/seekapa-training-platform` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/seekapa-training-platform/scripts/sync_and_email_today.py:360: time.sleep(2)`
  - `projects/seekapa-training-platform/scripts/email_arabic_reports_nissreen.py:255: time.sleep(EMAIL_DELAY_SECONDS)`
  - `projects/seekapa-training-platform/scripts/email_arabic_reports_nissreen.py:263: time.sleep(wait)`
  - `projects/seekapa-training-platform/scripts/email_arabic_reports_nissreen.py:745: time.sleep(BATCH_WAIT_SECONDS)`
  - `projects/seekapa-training-platform/scripts/email_qusai_reports.py:213: time.sleep(2)  # Rate limit`
- `projects/social-intelligence-unit` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/social-intelligence-unit/scripts/execute_18_runs_latam.py:225: time.sleep(2)`
  - `projects/social-intelligence-unit/scripts/ab_test_tiktok_freshness.py:93: time.sleep(10)`
  - `projects/social-intelligence-unit/scripts/backfill_enrich.py:104: time.sleep(1.0 / RATE_LIMIT)`
  - `projects/social-intelligence-unit/scripts/repopulate_meta_from_apify_history.py:72: time.sleep(wait_s)`
  - `projects/social-intelligence-unit/scripts/scrape_worker.py:38: time.sleep(args.poll if processed == 0 else 1)`
- `projects/social-intelligence-unit/src/seekapa-video` has sleep/polling samples that should be reviewed for timeouts/backoff:
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/heygen.ts:184: await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/elevenlabs-creative.ts:498: await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:41: const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:273: sleep(1000);`
  - `projects/social-intelligence-unit/src/seekapa-video/scripts/inspect-videos.ts:400: await sleep(3000);`
- No long benchmarks were run. This pass stayed to read-only scans and configured fast lint commands.

## CI_AND_PIPELINES

- `projects/.archive/Oded/archive/aeo-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/.archive/Oded/archive/anychat-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/.archive/Oded/archive/automation-fabric-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/.archive/Oded/archive/client-eval-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/.archive/Oded/archive/compliance-exam-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/.archive/Oded/archive/realtime-docker-deploy/azure-pipelines.yml`: CI auth reproducer risk strings
- `projects/campaign-analysis/azure-pipelines-mcp-sales.yml`: CI auth reproducer risk strings
- `projects/campaign-analysis/azure-pipelines-mcp.yml`: CI auth reproducer risk strings
- `projects/campaign-analysis/azure-pipelines-mcp-sales.yml`: CI auth reproducer risk strings
- `projects/campaign-analysis/azure-pipelines-mcp.yml`: CI auth reproducer risk strings
- `projects/seekapa-training-platform/.github/workflows/e2e-tests.yml`: continue-on-error true
- `projects/social-intelligence-unit/.github/workflows/ci.yml`: continue-on-error true
- ADO web UI hand-edit detection, AI PR review stage health, and run-level pipeline evidence were blocked by Azure DevOps CLI auth refresh requirement.

## STALE_PR_AND_BRANCH_TRIAGE

- Local upstream tracking refs were recorded per repo, but ADO active/stale PR state was unavailable.
- `projects/campaign-analysis` has gone upstream tracking refs: Corp|origin/Corp|[gone], ci-acr-push-foundry-rbac|origin/ci-acr-push-foundry-rbac|[gone], feature/fix-pipeline-buildctx-and-prompt-v14|origin/feature/fix-pipeline-buildctx-and-prompt-v14|[gone], feature/mcp-bicep-deploy|origin/feature/mcp-bicep-deploy|[gone], feature/mcp-foundation-and-chatwoot|origin/feature/mcp-foundation-and-chatwoot|[gone]
- `projects/campaign-analysis/Onesignal` has gone upstream tracking refs: Corp|origin/Corp|[gone], ci-acr-push-foundry-rbac|origin/ci-acr-push-foundry-rbac|[gone], feature/fix-pipeline-buildctx-and-prompt-v14|origin/feature/fix-pipeline-buildctx-and-prompt-v14|[gone], feature/mcp-bicep-deploy|origin/feature/mcp-bicep-deploy|[gone], feature/mcp-foundation-and-chatwoot|origin/feature/mcp-foundation-and-chatwoot|[gone]
- `projects/cs-agent/axia-seekapa-cs-agents-devops` has gone upstream tracking refs: chore/disable-create-ticket-baseline-eval|origin/chore/disable-create-ticket-baseline-eval|[gone], feat/agent-endpoint-baseline-scorecard|origin/feat/agent-endpoint-baseline-scorecard|[gone], feat/foundry-native-eval-runner|origin/feat/foundry-native-eval-runner|[gone], feat/prompt-v107.1-yasha-style|origin/feat/prompt-v107.1-yasha-style|[gone], feat/v109-config-v107.1-prompt-evals|origin/feat/v109-config-v107.1-prompt-evals|[gone]
- `projects/qc/qc-telephony-api` has gone upstream tracking refs: feat/aoai-managed-identity-auth|origin/feat/aoai-managed-identity-auth|[gone], feat/pipeline-yasha-notifications|origin/feat/pipeline-yasha-notifications|[gone], feat/restore-session-memory-sliding-ttl|origin/feat/restore-session-memory-sliding-ttl|[gone], fix/pipeline-kv-secret-names|origin/fix/pipeline-kv-secret-names|[gone], fix/pipeline-master-to-main|origin/fix/pipeline-master-to-main|[gone]
- `projects/seekapa-training-platform` has gone upstream tracking refs: chore/repo-cleanup|azure/chore/repo-cleanup|[gone]
- Remote branch age triage and cloned-vs-uncloned ADO repo gaps require refreshed Azure DevOps auth.

## PROJECT_ROUTING

- `projects`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- `projects/.archive/claude-orchestration`
  - Review `added-any` scan samples (3 shown in CODE_QUALITY).
  - Review `broad-except` scan samples (5 shown in CODE_QUALITY).
  - Review `debug-print` scan samples (10 shown in CODE_QUALITY).
- `projects/.archive/el-vadt`
  - Review `broad-except` scan samples (10 shown in CODE_QUALITY).
  - Review `debug-print` scan samples (10 shown in CODE_QUALITY).
  - Review `disabled-eval` scan samples (2 shown in CODE_QUALITY).
- `projects/ORM-AGENT`
  - Review `added-any` scan samples (10 shown in CODE_QUALITY).
  - Review `debug-print` scan samples (2 shown in CODE_QUALITY).
  - Review `disabled-eval` scan samples (1 shown in CODE_QUALITY).
- `projects/_inherited/automation-fabric`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/automation-fabric/': Could not resolve host: dev.azure.com
- `projects/_inherited/market-daily-reports`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/market-daily-reports/': Could not resolve host: dev.azure.com
- `projects/campaign-analysis`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- `projects/campaign-analysis/Onesignal`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis/': Could not resolve host: dev.azure.com
- `projects/cs-agent`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- `projects/cs-agent/axia-seekapa-cs-agents-devops`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- `projects/figma-4-all`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all/': Could not resolve host: dev.azure.com
- `projects/personal/jsq-slq`
  - Remote read check failed for origin: fatal: unable to access 'https://github.com/ShovalBenjer/JSQ-SLQ.git/': Could not resolve host: github.com
- `projects/qc`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents/': Could not resolve host: dev.azure.com
- `projects/qc/qc-telephony-api`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api/': Could not resolve host: dev.azure.com
- `projects/seekapa-training-platform`
  - Review `added-any` scan samples (10 shown in CODE_QUALITY).
  - Review `broad-except` scan samples (2 shown in CODE_QUALITY).
  - Review `debug-print` scan samples (10 shown in CODE_QUALITY).
- `projects/social-intelligence-unit`
  - Remote read check failed for origin: fatal: unable to access 'https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit/': Could not resolve host: dev.azure.com
  - ruff check failed or unavailable (rc=1).
- `projects/social-intelligence-unit/src/seekapa-video`
  - bun run lint failed or unavailable (rc=1).

## ACTIONABLE_NEXT_STEPS

1. Refresh Azure DevOps CLI auth for `https://dev.azure.com/Corp-domain` and rerun the remote half: repos, active PRs, stale branches, pipeline run health, and coverage gaps.
2. For repos with lint command failures, inspect whether the failure is real debt, missing dependencies, or stale script configuration; avoid editing until each failure is reproduced in that repo.
3. Prioritize projects with source changes but no parallel tests and hot-zone fix churn; add focused regression tests before behavior changes.
4. Establish a safe Foundry prompt comparison command per agent repo so future unattended sweeps can diff live prompt text against git without guessing project routing.
5. Review pipeline YAML files flagged for auth-risk strings, missing lint/test/eval steps, or `continue-on-error`; attach ADO run evidence after DevOps auth is restored.

## VERIFICATION_EVIDENCE

- `find /home/shovalbe/projects ... -name .git`: found `17` git roots via script.
- `az account show --query '{user:user.name,tenant:tenantId}' -o json`: rc `0`.
- `az repos list --organization https://dev.azure.com/Corp-domain --project Corp-AI -o json`: rc `1`; repos parsed `0`.
- `az repos pr list --organization https://dev.azure.com/Corp-domain --project Corp-AI --status active -o json`: rc `1`; active PRs parsed `0`.
- `projects/campaign-analysis`: `uv run ruff check` rc `0`.
- `projects/social-intelligence-unit`: `uv run ruff check` rc `1`.
- `projects/social-intelligence-unit/src/seekapa-video`: `bun run lint` rc `1`.
