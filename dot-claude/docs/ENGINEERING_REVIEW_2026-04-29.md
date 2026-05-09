# Engineering Review Sweep - 2026-04-29

Automation id: c02-engineering-review-sweep
Run timestamp UTC: 20260429T170750Z
Workspace root: /home/shovalbe
Report generated UTC: 2026-04-29T17:11:59.465944+00:00

## EXECUTIVE_SUMMARY

- Covered 14 git repos under /home/shovalbe/projects.
- Azure DevOps remote coverage: BLOCKED auth-needs-refresh or CLI unavailable; local analysis continued.
- High-signal findings: 16 candidate issues across artifact, gate, and static-check scans.
- No files were deleted or modified except this report.

## AZURE_DEVOPS_REMOTE_COVERAGE

- Command: `az account show -o json` -> exit 1
- Result: auth-needs-refresh; remote PR/branch/pipeline coverage unavailable.
- Error: `ERROR: Please run 'az login' to setup account.`

## LOCAL_REPO_COVERAGE

- projects: has origin; dirty; commits_30d=152; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`
- projects/.archive/Oded/archive/seekapa-training-platform: has origin; dirty; commits_30d=26; ls-remote exit 128; origin=`error: No such remote 'origin'`
- projects/.archive/claude-orchestration: has origin; clean; commits_30d=0; ls-remote exit 128; origin=`error: No such remote 'origin'`
- projects/.archive/el-vadt: has origin; clean; commits_30d=0; ls-remote exit 128; origin=`error: No such remote 'origin'`
- projects/campaign-analysis: has origin; dirty; commits_30d=76; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis`
- projects/campaign-analysis/Onesignal: has origin; dirty; commits_30d=76; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/campaign-analysis`
- projects/cs-agent: has origin; dirty; commits_30d=152; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`
- projects/cs-agent/axia-seekapa-cs-agents-devops: has origin; dirty; commits_30d=133; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`
- projects/figma-4-all: has origin; dirty; commits_30d=0; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/figma-4-all`
- projects/personal/jsq-slq: has origin; dirty; commits_30d=0; ls-remote exit 128; origin=`https://github.com/ShovalBenjer/JSQ-SLQ.git`
- projects/qc: has origin; dirty; commits_30d=152; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`
- projects/qc/qc-telephony-api: has origin; clean; commits_30d=33; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api`
- projects/social-intelligence-unit: has origin; dirty; commits_30d=0; ls-remote exit 128; origin=`https://dev.azure.com/Corp-domain/Corp-AI/_git/social-intelligence-unit`
- projects/social-intelligence-unit/src/seekapa-video: has origin; dirty; commits_30d=0; ls-remote exit 128; origin=`error: No such remote 'origin'`

## SPEC_AND_DOCS_DRIFT

- projects: specs=1; MERGED=1
-   - MERGED: projects/docs/superpowers/specs/2026-04-25-ink-tui-next-level-forge-overlay.md
- projects/.archive/Oded/archive/seekapa-training-platform: specs=2; ACTIVE=1, MERGED=1
-   - ACTIVE: projects/.archive/Oded/archive/seekapa-training-platform/docs/superpowers/specs/2026-03-29-email-reliability-scoring-fix-design.md
-   - MERGED: projects/.archive/Oded/archive/seekapa-training-platform/docs/superpowers/specs/2026-04-05-email-session-lifecycle-refactor-design.md
- projects/.archive/Oded/archive/seekapa-training-platform: CLAUDE.md contains command claims that may conflict with global bun/uv rules:
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:62: cd frontend && npm run dev
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:74: cd frontend && npm run test
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:77: npm run test:personal     # Personal dashboard tests
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:78: npm run test:team         # Team dashboard tests
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:79: npm run test:headed       # Run with visible browser
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:80: npm run test:ui           # Playwright UI mode
-   - projects/.archive/Oded/archive/seekapa-training-platform/CLAUDE.md:90: cd frontend && npm run build
- projects/campaign-analysis: specs=23; MERGED=5, ACTIVE=13, STALLED=5
-   - MERGED: projects/campaign-analysis/docs/superpowers/specs/2026-04-28-cja-v2-mcp-alignment.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-gates-and-tests.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-eval.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-18-ffi-v2-structured-agents.md
-   - MERGED: projects/campaign-analysis/docs/superpowers/specs/2026-04-19-marketing-funnel-manager-flow.md
-   - STALLED: projects/campaign-analysis/docs/superpowers/specs/2026-04-23-mcp-narrow-ship.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-23-redesign-retrieval-and-memory.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-28-m365-copilot-ui-widgets-ux-edit.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-04-19-crm-call-analyser-redeploy.md
-   - ACTIVE: projects/campaign-analysis/docs/superpowers/specs/2026-03-30-call-analyzer-agent-v9-design.md
- projects/cs-agent: specs=4; ACTIVE=3, STALLED=1
-   - ACTIVE: projects/cs-agent/docs/superpowers/specs/2026-03-25-chatwoot-handler-signal-escalation-design.md
-   - STALLED: projects/cs-agent/docs/specs/2026-04-18-align-test-connector-to-production.md
-   - ACTIVE: projects/cs-agent/docs/specs/2026-04-23-seekapa-prompt-v101-compact-style-kb-routing.md
-   - ACTIVE: projects/cs-agent/docs/specs/2026-04-28-v108-yasha-intake-flow.md
- projects/cs-agent/axia-seekapa-cs-agents-devops: specs=3; ACTIVE=3
-   - ACTIVE: projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-15-silver-eval-dataset.md
-   - ACTIVE: projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-28-v108-yasha-intake-flow.md
-   - ACTIVE: projects/cs-agent/axia-seekapa-cs-agents-devops/docs/specs/2026-04-29-v109-yasha-multilingual-intake.md
- projects/qc: CLAUDE.md contains command claims that may conflict with global bun/uv rules:
-   - projects/qc/CLAUDE.md:24: pip install -r requirements.txt
-   - projects/qc/CLAUDE.md:29: pip install -r requirements.txt
- projects/qc/qc-telephony-api: specs=1; MERGED=1
-   - MERGED: projects/qc/qc-telephony-api/docs/specs/2026-04-28-no-storage-qa.md
- projects/qc/qc-telephony-api: CLAUDE.md contains command claims that may conflict with global bun/uv rules:
-   - projects/qc/qc-telephony-api/CLAUDE.md:53: pip install -r requirements.txt
- projects/social-intelligence-unit: specs=2; ACTIVE=2
-   - ACTIVE: projects/social-intelligence-unit/docs/superpowers/specs/2026-03-26-foundry-agent-orchestration-design.md
-   - ACTIVE: projects/social-intelligence-unit/docs/superpowers/specs/2026-04-14-heygen-v3-aca-integration.md
- projects/social-intelligence-unit: CLAUDE.md contains command claims that may conflict with global bun/uv rules:
-   - projects/social-intelligence-unit/CLAUDE.md:40: - Bun + Vitest (not npm + Jest)

## FOUNDRY_PROMPT_DRIFT

- No cs-agent/hr-agent/campaign-analysis prompt files detected in the bounded patterns.

## CODE_QUALITY

- projects: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects: duplicate commit subjects by author: Shoval Benjer: feat(cost): add Foundry cost audit script + GPT 5.2 -> 5.4 nano migration plan (2); Shoval Benjer: docs(wiki): update all wiki pages to reflect current system state (2); Shoval Benjer: fix(tests): guard live_bot_test sys.exit, rename test_result helper (2); Shoval Benjer: fix(webhook): inject Yasha's conversation flow directive on first turn (2)
- projects: hot-zone files with repeated fix commits: azure-pipelines.yml (29), tests/test_chatwoot_webhook.py (12), azure-function-crm/chatwoot_handler/__init__.py (12), scripts/foundry_eval_gate.py (5), tests/live_bot_test.py (3)
- projects: HIGH RISK last-24h artifact filenames: [sensitive-path-redacted], [sensitive-path-redacted], [token-reference-path-redacted]
- projects/.archive/Oded/archive/seekapa-training-platform: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/.archive/Oded/archive/seekapa-training-platform: scan debug_prints matched 2259; samples: .claude/handover-20260204-4131ab.md:100:export [api-key-name-redacted]=[REDACTED] -c "import json; print(json.load(open('backend/local.settings.json'))['Values']['[api-key-name-redacted]'])" ...[truncated] | AUTH_VALIDATION_SUMMARY.txt:80:  python3 -c "[token-generation-example-redacted]" | WAVE1_QUICK_START.txt:49:  python -c "from backend.webhook_elevenlabs import main; print(' Import successful')"
- projects/.archive/Oded/archive/seekapa-training-platform: scan broad_exception matched 252; samples: backend/admin_setup/__init__.py:75:    except Exception as e: | backend/admin_unlock_level/__init__.py:104:    except Exception as e: | backend/admin_unlock_level/__init__.py:252:    except Exception as e:
- projects/.archive/Oded/archive/seekapa-training-platform: scan ui_force matched 44; samples: D3JS_RADAR_BAR_CHARTS_EXAMPLE.js:590:    font-size: 10px !important; | D3JS_RADAR_BAR_CHARTS_EXAMPLE.js:602:    font-size: 9px !important; | docs/diagrams/system-arch-interactive-macro.html:22:    .react-flow { background: #0d1117 !important; }
- projects/.archive/Oded/archive/seekapa-training-platform: scan typescript_any matched 250; samples: .claude/handover-20260204-4131ab.md:142:- Verify settings with GET after any PATCH | .claude/spanish_level_2.txt:93:   - ACCEPTABLE: Clear process (24-48hrs), explain fees if any, SPEI or wire transfer options, honest about AML checks | .claude/spanish_level_3.txt:90:    INCORRECT: Giving any specific number, even "conservadoramente 10%"
- projects/.archive/Oded/archive/seekapa-training-platform: WIP/stash/debug-like commit subjects: 1b86a6086e213b69273a1be1b20d78b3b8fba2f2	git stash	2026-04-16	WIP on fix/ci-deploy-no-environment: 050b63b fix(ci): add cold-start retry to smoke health check | e3532b3cc246a5df3ba67f78ccb23aeb35f9fb13	git stash	2026-04-16	index on fix/ci-deploy-no-environment: 050b63b fix(ci): add cold-start retry to smoke health check
- projects/.archive/Oded/archive/seekapa-training-platform: hot-zone files with repeated fix commits: azure-pipelines.yml (8), backend/email_drip_sender/__init__.py (3), backend/tests/test_ai_analyzer.py (2), backend/shared/email_service.py (2), backend/webhook_elevenlabs/__init__.py (2)
- projects/.archive/claude-orchestration: scan debug_prints matched 3511; samples: azdo-mcp/node_modules/@azure/core-auth/README.md:34:console.log([credential-key-redacted]); | azdo-mcp/node_modules/@azure/core-auth/README.md:37:console.log([credential-key-redacted]); | azdo-mcp/node_modules/@azure/core-auth/README.md:47:console.log([credential-key-redacted]);
- projects/.archive/claude-orchestration: scan broad_exception matched 2208; samples: azdo-mcp/node_modules/@azure/msal-browser/src/broker/nativeBroker/NativeMessageHandler.ts:121:        } catch (e) { | azdo-mcp/node_modules/@azure/msal-browser/src/broker/nativeBroker/NativeMessageHandler.ts:337:        } catch (err) { | azdo-mcp/node_modules/@azure/msal-browser/src/controllers/NestedAppAuthController.ts:254:        } catch (e) {
- projects/.archive/claude-orchestration: scan typescript_any matched 6444; samples: .specify/memory/MEMORY.md:84:- [ ] Other: [List any] | .specify/memory/RULES.md:129:npm run lint     # Fix any issues | azdo-mcp/node_modules/@azure/abort-controller/LICENSE:5:Permission is hereby granted, free of charge, to any person obtaining a copy
- projects/.archive/el-vadt: scan debug_prints matched 2603; samples: analysis/eda_dark_patterns.py:79:    print(f"Scanned {len(results)} files.") | analysis/eda_dark_patterns.py:80:    print("Top Vulnerability Flags:") | analysis/eda_dark_patterns.py:84:            print(f"- {row['filename']}: {matches}")
- projects/.archive/el-vadt: scan broad_exception matched 174; samples: analysis/eda_dark_patterns.py:61:    except Exception as e: | analysis/feature_extraction.py:134:    except Exception as e: | analysis/llm_extraction_template.py:54:    except Exception as e:
- projects/.archive/el-vadt: scan typescript_any matched 538; samples: .specify/memory/MEMORY.md:84:- [ ] Other: [List any] | .specify/memory/RULES.md:129:npm run lint     # Fix any issues | analysis/llm_extraction_template.py:29:5. **Compliance Violation**: Quote any text promising "No Risk" or "Guaranteed Profit".
- projects/campaign-analysis: `uv run ruff check` exit 1; err=`F401 [*] `typing.Any` imported but unused
  --> scripts/_grounded_prompt_v3.py:25:20
   |
24 | import re
25 | from typing import Any
   |                    ^^^
26 |
27 | # Hard-disqualifying phrases (Arabic + English + Spanish + Portuguese).
   |
help: Remove unused import: `typing.Any`

I001 [*] Import block is un-sorted or un-formatted
  --> tests/test_grounded_v3.py:29:1
   |
27 |   sys.path.insert(0, str(ROOT / "scripts"))
28 |
29 | / from scripts._grounded_prompt_v3 import (  # noqa: E402
 ...[truncated]`
- projects/campaign-analysis: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/campaign-analysis: scan debug_prints matched 408; samples: agent_prompt_v13_part1.txt:79:       import os; print([f for f in os.listdir('/mnt/data') if not f.startswith('.')]) | agent_prompt_v14.txt:79:       import os; print([f for f in os.listdir('/mnt/data') if not f.startswith('.')]) | agent_scoring_helpers.py:511:    print("Helper self-tests passed.")
- projects/campaign-analysis: scan broad_exception matched 30; samples: agent_prompt_v13_part2.txt:300:        except Exception: | agent_prompt_v13_part2.txt:309:        except Exception: | agent_prompt_v13_part2.txt:319:        except Exception:
- projects/campaign-analysis: scan typescript_any matched 97; samples: agent_prompt_v13_part1.txt:18:NOT file_search. NOT code_interpreter. NOT any other tool. ONLY get-cdr-metadata. | agent_prompt_v13_part1.txt:21:RULE 2  BANNED FIRST ACTIONS (any of these = protocol violation): | agent_prompt_v13_part1.txt:35:Do NOT ask the user for permission at any point during the pipeline.
- projects/campaign-analysis: duplicate commit subjects by author: Shoval Beigelman: Merge remote-tracking branch 'origin/master' into fix/ci-vector-store-env-bypass (2); Yasha Kohut: Update azure-pipelines.yml for Azure Pipelines (6); Shoval Beigelman: fix(ci): drop deployment job type; Stage 3 runs deploy_agent.py directly (2); Shoval Beigelman: fix(ci): switch to KV-loaded FOUNDRY-API-KEY + ruff cleanup (2)
- projects/campaign-analysis: WIP/stash/debug-like commit subjects: 5c92a029d70b8f02790db5ad1ce4b798db1ed24a	Shoval Beigelman	2026-04-20	WIP on feature/v59-realmid-fix-multi-agent: 348592e feat(mfm): Tranche 0  workflow emits readable markdown, no ...[truncated]
- projects/campaign-analysis: hot-zone files with repeated fix commits: azure-pipelines.yml (14), scripts/deploy_agent.py (7), scripts/codex_review.py (5), agent-memory/call-analyzer/api-reference.md (4), agent_prompt_v13_part1.txt (4)
- projects/campaign-analysis/Onesignal: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/campaign-analysis/Onesignal: duplicate commit subjects by author: Shoval Beigelman: Merge remote-tracking branch 'origin/master' into fix/ci-vector-store-env-bypass (2); Yasha Kohut: Update azure-pipelines.yml for Azure Pipelines (6); Shoval Beigelman: fix(ci): drop deployment job type; Stage 3 runs deploy_agent.py directly (2); Shoval Beigelman: fix(ci): switch to KV-loaded FOUNDRY-API-KEY + ruff cleanup (2)
- projects/campaign-analysis/Onesignal: WIP/stash/debug-like commit subjects: 5c92a029d70b8f02790db5ad1ce4b798db1ed24a	Shoval Beigelman	2026-04-20	WIP on feature/v59-realmid-fix-multi-agent: 348592e feat(mfm): Tranche 0  workflow emits readable markdown, no ...[truncated]
- projects/campaign-analysis/Onesignal: hot-zone files with repeated fix commits: azure-pipelines.yml (14), scripts/deploy_agent.py (7), scripts/codex_review.py (5), agent-memory/call-analyzer/api-reference.md (4), agent_prompt_v13_part1.txt (4)
- projects/cs-agent: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/cs-agent: duplicate commit subjects by author: Shoval Benjer: feat(cost): add Foundry cost audit script + GPT 5.2 -> 5.4 nano migration plan (2); Shoval Benjer: docs(wiki): update all wiki pages to reflect current system state (2); Shoval Benjer: fix(tests): guard live_bot_test sys.exit, rename test_result helper (2); Shoval Benjer: fix(webhook): inject Yasha's conversation flow directive on first turn (2)
- projects/cs-agent: hot-zone files with repeated fix commits: azure-pipelines.yml (29), tests/test_chatwoot_webhook.py (12), azure-function-crm/chatwoot_handler/__init__.py (12), scripts/foundry_eval_gate.py (5), tests/live_bot_test.py (3)
- projects/cs-agent: HIGH RISK last-24h artifact filenames: [sensitive-path-redacted], [sensitive-path-redacted], [token-reference-path-redacted]
- projects/cs-agent/axia-seekapa-cs-agents-devops: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/cs-agent/axia-seekapa-cs-agents-devops: scan debug_prints matched 365; samples: .claude/handover-20260203-c5ee66.md:197:print(resp.text, resp.error) | .claude/handover-20260203-c5ee66.md:201:print(resp.text, resp.error) | .claude/plans/2025-12-14-kb-replacement-test-optimization.md:84:print(response.output_text)
- projects/cs-agent/axia-seekapa-cs-agents-devops: scan broad_exception matched 65; samples: azure-function-crm/channel_router/__init__.py:486:    except Exception as e: | azure-function-crm/chatwoot_handler/__init__.py:137:        except Exception as exc: | azure-function-crm/chatwoot_handler/__init__.py:158:    except Exception as exc:
- projects/cs-agent/axia-seekapa-cs-agents-devops: scan ui_force matched 36; samples: docs/diagrams/system-arch-interactive-macro.html:22:    .react-flow { background: #0d1117 !important; } | docs/diagrams/system-arch-interactive-macro.html:23:    .react-flow__background { background: #0d1117 !important; } | docs/diagrams/system-arch-interactive-macro.html:24:    .react-flow__minimap { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important;  ...[truncated]
- projects/cs-agent/axia-seekapa-cs-agents-devops: scan typescript_any matched 320; samples: .claude/ai-foundry-connection-update-report.md:136:| `axia-crm-api` | 2026-02-03 |  Orphan (not referenced by any agent) | | .claude/handover-20260210-434dbd.md:87:- Spend 2-3 sentences on EMPATHY before any procedural steps | .claude/handover-20260210-434dbd.md:126:**Impact**: Results JSON sometimes shows PASS but pytest marks FAILED (or vice versa). 3 borderline tests at 0.6 score may flip on any run.
- projects/cs-agent/axia-seekapa-cs-agents-devops: duplicate commit subjects by author: Shoval Benjer: feat(ci): add small-budget foundry smoke eval gate (2)
- projects/cs-agent/axia-seekapa-cs-agents-devops: WIP/stash/debug-like commit subjects: debea7b88f55547a79e55e856afafb4c2593ba20	Shoval Benjer	2026-03-31	WIP on feat/codex-review-stage-ci: 6dc884e0 fix(ci): replace status-gate smoke test with assignee-gate
- projects/cs-agent/axia-seekapa-cs-agents-devops: hot-zone files with repeated fix commits: azure-pipelines.yml (26), tests/test_chatwoot_webhook.py (11), azure-function-crm/chatwoot_handler/__init__.py (11), scripts/foundry_eval_gate.py (5), azure-function-crm/chatwoot_handler/_gates.py (2)
- projects/personal/jsq-slq: scan debug_prints matched 94; samples: JSQ_SLQ_Expierement_V3.ipynb:291:        "    print(\"\\n--- Running Block 1: Validation ---\")\n", | JSQ_SLQ_Expierement_V3.ipynb:333:        "    print(\"\\n--- Running Block 2: Impact of K-Threshold ---\")\n", | JSQ_SLQ_Expierement_V3.ipynb:377:        "    print(\"\\n--- Running Block 3 (Rigorous): Preemptive vs. Non-Preemptive ---\")\n",
- projects/personal/jsq-slq: scan broad_exception matched 6; samples: Netivi_Israel_Data_Exploration.ipynb:442:        "except Exception as e:\n", | Netivi_Israel_Data_Exploration.ipynb:465:        "except Exception as e:\n", | Netivi_Israel_Data_Exploration.ipynb:489:        "except Exception as e:\n",
- projects/qc: `parse package.json` exit 999; err=`Expecting value: line 1 column 1 (char 0)`
- projects/qc: duplicate commit subjects by author: Shoval Benjer: feat(cost): add Foundry cost audit script + GPT 5.2 -> 5.4 nano migration plan (2); Shoval Benjer: docs(wiki): update all wiki pages to reflect current system state (2); Shoval Benjer: fix(tests): guard live_bot_test sys.exit, rename test_result helper (2); Shoval Benjer: fix(webhook): inject Yasha's conversation flow directive on first turn (2)
- projects/qc: hot-zone files with repeated fix commits: azure-pipelines.yml (29), tests/test_chatwoot_webhook.py (12), azure-function-crm/chatwoot_handler/__init__.py (12), scripts/foundry_eval_gate.py (5), tests/live_bot_test.py (3)
- projects/qc: HIGH RISK last-24h artifact filenames: [sensitive-path-redacted], [sensitive-path-redacted], [token-reference-path-redacted]
- projects/qc/qc-telephony-api: scan debug_prints matched 18; samples: bin/_breadcrumb.sh:38:print(f"{stage}  {job}  {step}") | bin/_breadcrumb.sh:40:    print(f"Script failed with exit code: {code}") | bin/notifications.sh:37:payload=$(python3 -c 'import json,os; print(json.dumps({"chat_id": os.environ["CHAT_ID"], "text": os.environ["MSG"]}))')
- projects/qc/qc-telephony-api: scan broad_exception matched 10; samples: bin/_breadcrumb.sh:18:except Exception: | src/api/function_app.py:230:    except Exception as e: | src/api/function_app.py:313:    except Exception as e:
- projects/qc/qc-telephony-api: scan typescript_any matched 48; samples: .claude/handover-20260128-v2.md:32:- Now accepts any ISO language code (ar, es, pt, en, he, fr, de, zh, ja, etc.) | .claude/handover-20260128-v2.md:33:- GPT-5 handles translation for any language pair | .claude/handover-20260128-v2.md:112:1. **Dynamic Languages**: GPT-5 handles any language pair; specific prompts only improve quality for known languages
- projects/qc/qc-telephony-api: duplicate commit subjects by author: Yasha Kohut: Update azure-pipelines.yml for Azure Pipelines (3); Shoval Benjer: docs(wiki): write QC-Telephony wiki page (2); Shoval Benjer: feat(qc-api): stateless Q&A v2.2 + model swap to gpt-5.4-mini (2)
- projects/qc/qc-telephony-api: hot-zone files with repeated fix commits: azure-pipelines.yml (5), src/api/shared/qa_agent_service.py (3)
- projects/social-intelligence-unit: scan debug_prints matched 469; samples: .claude/audits/0.2-playwright-audit.md:717:        console.log(`\n${route.name} console output:`); | .claude/audits/0.2-playwright-audit.md:718:        consoleLogs.forEach((log) => console.log(log)); | .claude/hooks/heidegger-remind.sh:21:print(json.dumps({'continue': True, 'systemMessage': msg}))
- projects/social-intelligence-unit: scan broad_exception matched 105; samples: .claude/audits/0.2-playwright-audit.md:710:      } catch (err) { | .claude/hooks/sqlite-readonly-guard.sh:15:except Exception: | .claude/schemas/dedupe-algorithm-spec.md:143:    except Exception:
- projects/social-intelligence-unit: scan ui_force matched 35; samples: docs/architecture/siu-system-arch-interactive.html:22:    .react-flow { background: #0d1117 !important; } | docs/architecture/siu-system-arch-interactive.html:23:    .react-flow__background { background: #0d1117 !important; } | docs/architecture/siu-system-arch-interactive.html:24:    .react-flow__minimap { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important ...[truncated]
- projects/social-intelligence-unit: scan typescript_any matched 410; samples: .claude/audits/0.2-playwright-audit.md:14:2. **Console Errors**  Capture any JavaScript errors, warnings, deprecations | .claude/audits/0.2-playwright-audit.md:157:- [ ] Result cards visible (if any results) | .claude/audits/AUDIT-INTAKE.md:284:- Zero console errors on any route
- projects/social-intelligence-unit/src/seekapa-video: `bun run lint` exit 1; err=`$ eslint ./src
error: script "lint" exited with code 1`
- projects/social-intelligence-unit/src/seekapa-video: scan debug_prints matched 435; samples: .agent/skills/performance-optimize/SIU Performance Skills.md:462:python -c "import platform; print(platform.machine())" | .agent/skills/remotion-best-practices/rules/can-decode.md:54:  console.log("Video can be decoded"); | .agent/skills/remotion-best-practices/rules/can-decode.md:56:  console.log("Video cannot be decoded by this browser");
- projects/social-intelligence-unit/src/seekapa-video: scan broad_exception matched 371; samples: .agent/skills/remotion-best-practices/rules/can-decode.md:29:  } catch { | .agent/skills/remotion-best-practices/rules/extract-frames.md:186:} catch (error) { | .agent/skills/remotion-best-practices/rules/extract-frames.md:226:} catch (error) {
- projects/social-intelligence-unit/src/seekapa-video: scan ui_force matched 6; samples: .remotion/bundle/634.bundle.js:4730:          cssText: `${style.cssText} !important;` | .remotion/bundle/634.bundle.js:90910:    position: static !important; | .remotion/bundle/634.bundle.js:90938:    z-index: 1000;
- projects/social-intelligence-unit/src/seekapa-video: scan typescript_any matched 236; samples: .agent/skills/performance-optimize/SIU Performance Skills.md:93:**SIU impact:** Pre-commit hooks become sub-second. You can lint on every save in VSCode without any lag on M1.[^10] | .agent/skills/performance-optimize/SIU Performance Skills.md:500:4. **Use Polars for ingestion normalization**  replace any pandas code in the flattenstandardizesanitize pipelin ...[truncated] | .agent/skills/performance-optimize/SIU Performance Skills.md:553:22. [Stop the SQLite Performance Wars: Your Database Can ...](https://javascript.plainenglish.io/stop-the-sqlite-pe ...[truncated]

## TEST_AND_EVAL_GATES

- projects/.archive/Oded/archive/seekapa-training-platform: possible gate weakening in recent YAML/Python diff:
-   - `+needs_openai = pytest.mark.skipif(`
-   - `+- Arabic skip logic constants (commit a6a65f8 regression)`
-   - `+    def test_skips_llm_if_evaluation_failed(self, mock_query, mock_llm):`
-   - `+# Arabic email skip  commit a6a65f8 regression`
-   - `+        """Dead-letter threshold is 5 attempts."""`
-   - `+    # Skip standard email for Arabic sessions  they get the full Arabic report only.`
-   - `+    _skip_arabic_standard_pending()`
-   - `+def _skip_arabic_standard_pending() -> None:`
- projects/campaign-analysis: possible gate weakening in recent YAML/Python diff:
-   - `+                 { [ -z "$DEPLOY_RESULT" ] || [ "$DEPLOY_RESULT" = "Succeeded" ] || [ "$DEPLOY_RESULT" = "Skipped" ]; } && \`
-   - `+    Pipeline path: set `FOUNDRY_VECTOR_STORE_ID` to skip the data-plane`
-   - `+        print("  (skipping memory-file refresh; run with user identity to update)")`
-   - `+                "Standard no-money objection handling (installment, starter amount) was skipped",`
-   - `+    parser.add_argument("--resume", action="store_true", help="Skip accounts already in output JSONL")`
-   - `+    parser.add_argument("--submit", default=None, help="Submit a pre-built JSONL (skip the build step)")`
-   - `+        f"  Code Interpreter: {'enabled (no pre-attached files)' if include_code_interpreter else 'DISABLED (--no-ci)'}"`
-   - `+                    "skipped": True,`
- projects/cs-agent/axia-seekapa-cs-agents-devops: possible gate weakening in recent YAML/Python diff:
-   - `+    """C2: identity-solicit strip must skip when reply contains route marker."""`
-   - `+    def test_strip_skipped_when_route_marker_present(self):`
-   - `+    def test_strip_skipped_full_form_with_name_and_email_ask(self):`
-   - `+AI agent, and replies via the Chatwoot API. Signal-driven escalation: skips`
-   - `+def _ok_response(skipped: bool = False, reason: str | None = None,`
-   - `+    if skipped:`
-   - `+        body["skipped"] = True`
-   - `+def _skip(reason: str, **log_kw: Any) -> func.HttpResponse:`
- projects/qc/qc-telephony-api: possible gate weakening in recent YAML/Python diff:
-   - `+              -m "not skip_ci"`
-   - `+            TRANSLATION_THRESHOLD: $(translationThreshold)`
-   - `+            QA_ANSWER_THRESHOLD: $(qaAnswerThreshold)`
-   - `+            QA_CITATION_THRESHOLD: $(qaCitationThreshold)`
-   - `+        in(dependencies.E2ETests.result, 'Succeeded', 'Skipped', 'SucceededWithIssues'),`

## PERFORMANCE_AND_LATENCY

- projects/.archive/Oded/archive/seekapa-training-platform: scan sleep_polling matched 39; samples: E2E_TESTING_SUMMARY.txt:313:   Use waitForLoadState('networkidle') instead of setTimeout | backend/shared/elevenlabs_client.py:107:                time.sleep(wait_time) | backend/shared/elevenlabs_client.py:481:            time.sleep(poll_interval)
- projects/.archive/Oded/archive/seekapa-training-platform: scan missing_timeout_clues matched 54; samples: backend/ai_reports/__init__.py:420:        response = requests.post(url, headers=headers, json=payload, timeout=30) | backend/docs/api/API_QUICK_REFERENCE.md:146:    response = requests.get( | backend/docs/api/API_QUICK_REFERENCE.md:155:    response = requests.get(
- projects/.archive/claude-orchestration: scan sleep_polling matched 429; samples: azdo-mcp/node_modules/@azure/msal-browser/src/broker/nativeBroker/NativeMessageHandler.ts:164:            this.timeoutId = window.setTimeout(() => { | azdo-mcp/node_modules/@azure/msal-browser/src/broker/nativeBroker/NativeMessageHandler.ts:317:                clearTimeout(this.timeoutId); // Clear setTimeout | azdo-mcp/node_modules/@azure/msal-browser/src/interaction_handler/SilentHandler.ts:90:        const timeoutId = window.setTimeout(() => {
- projects/.archive/el-vadt: scan sleep_polling matched 49; samples: gemini_sales_conversation.txt:2118:    time.sleep(1)  # 60 calls/min rate limit | sales-agents/braintrust-testing/run_evaluation.py:239:        await asyncio.sleep(1) | sales-agents/scripts/agent_to_agent_voice_test.py:373:            await asyncio.sleep(0.05)
- projects/.archive/el-vadt: scan missing_timeout_clues matched 61; samples: gemini_sales_conversation.txt:2700:        requests.post('https://axia-seekapa-crm.azurewebsites.net/api/analyze-call', json=call_data) | sales-agents/CLAUDE.md:120:resp = requests.get('https://api.elevenlabs.io/v1/convai/agents', headers=headers) | sales-agents/CLAUDE.md:125:resp = requests.get(f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}', headers=headers)
- projects/campaign-analysis: scan sleep_polling matched 17; samples: app_mcp/_http_client.py:66:                await asyncio.sleep(wait) | app_mcp/_http_client.py:214:        await asyncio.sleep(delay) | scripts/_whatsapp_ai.py:60:                time.sleep(5 * (attempt + 1))
- projects/cs-agent/axia-seekapa-cs-agents-devops: scan sleep_polling matched 48; samples: azure-function-crm/channel_router/__init__.py:305:            await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff | azure-function-crm/chatwoot_handler/__init__.py:234:        time.sleep(_retry_backoff(attempt)) | docs/diagrams/system-arch-interactive-macro.html:1045:          setTimeout(function () {
- projects/qc/qc-telephony-api: scan sleep_polling matched 1; samples: docs/wiki/QC-Telephony.md:276:    <button onclick="const el=this.parentElement.nextElementSibling; navigator.clipboard.writeText(el.innerText); this.textContent='Copied'; setTimeou ...[truncated]
- projects/social-intelligence-unit: scan sleep_polling matched 53; samples: docs/api/manus_connectors_index.md:51:      setTimeout(() => setCopiedUuid(null), 2000); | docs/api/manus_openai-compatibility.md:112:    time.sleep(5)  | docs/api/manus_openai-compatibility.md:646:while True:
- projects/social-intelligence-unit: scan missing_timeout_clues matched 3; samples: docs/api/manus_openai-compatibility.md:212:pdf_response = requests.get(pdf_url) | docs/api/manus_openai-compatibility.md:214:upload_response = requests.put(file_record.upload_url, data=pdf_response.content) | docs/api/manus_openai-compatibility.md:438:    response = requests.get(image_url)
- projects/social-intelligence-unit/src/seekapa-video: scan sleep_polling matched 256; samples: .agent/skills/performance-optimize/SIU Performance Skills.md:289:    time.sleep(5)  # blocks the entire event loop! | .agent/skills/remotion-best-practices/rules/extract-frames.md:168:setTimeout(() => controller.abort(), 5000); | .agent/skills/remotion-best-practices/rules/extract-frames.md:197:  const timeoutId = setTimeout(() => {
- projects/social-intelligence-unit/src/seekapa-video: scan missing_timeout_clues matched 17; samples: .agents/skills/heygen/references/assets.md:138:        response = requests.post( | .agents/skills/heygen/references/authentication.md:71:response = requests.get( | .agents/skills/heygen/references/avatars.md:138:    response = requests.get(

## CI_AND_PIPELINES

- projects/.archive/Oded/archive/seekapa-training-platform: pipeline/workflow files: projects/.archive/Oded/archive/seekapa-training-platform/azure-pipelines.yml, projects/.archive/Oded/archive/seekapa-training-platform/.github/workflows/deploy-frontend.yml, projects/.archive/Oded/archive/seekapa-training-platform/.github/workflows/e2e-tests.yml
- projects/.archive/Oded/archive/seekapa-training-platform: review gate-hit details in TEST_AND_EVAL_GATES before merging related PRs.
- projects/campaign-analysis: pipeline/workflow files: projects/campaign-analysis/azure-pipelines.yml, projects/campaign-analysis/azure-pipelines-mcp-rollback.yml, projects/campaign-analysis/azure-pipelines-mcp.yml
- projects/campaign-analysis: review gate-hit details in TEST_AND_EVAL_GATES before merging related PRs.
- projects/cs-agent/axia-seekapa-cs-agents-devops: pipeline/workflow files: projects/cs-agent/axia-seekapa-cs-agents-devops/azure-pipelines.yml
- projects/cs-agent/axia-seekapa-cs-agents-devops: review gate-hit details in TEST_AND_EVAL_GATES before merging related PRs.
- projects/qc/qc-telephony-api: pipeline/workflow files: projects/qc/qc-telephony-api/azure-pipelines.yml
- projects/qc/qc-telephony-api: review gate-hit details in TEST_AND_EVAL_GATES before merging related PRs.
- projects/social-intelligence-unit: pipeline/workflow files: projects/social-intelligence-unit/azure-pipelines.yml

## STALE_PR_AND_BRANCH_TRIAGE

- No active PR data available from ADO in this run.
- projects: local branch tracking issues: feat/align-test-connector-to-production     1510f768 [origin/master: ahead 4, behind 48] feat(platform): Ink Skill Cards TUI + Stop banner  live | fix/codex-ci-endpoint                       a44f87d6 [origin/stage: ahead 1, behind 9] fix(ci): fix remaining variable refs + guard integration tests | fix/codex-foundry-agent                     950bcc37 [origin/stage: ahead 1, behind 7] fix(ci): resolv ...[truncated]
- projects/campaign-analysis: local branch tracking issues: Corp                                         bfb1a1d [origin/Corp: gone] Merged PR 168: feat(mcp): add chatwoot read-only tools + complete container foundation | ci-acr-push-foundry-rbac                     9930ac2 [origin/ci-acr-push-foundry-rbac: gone] fix(ci): use acr login for docker publish | feature/fix-pipeline-buildctx-and-prompt-v14 a4b2c45 [origin/feature/fix-pipeline-buildctx-and-prompt-v14: gone] fix(ci): pipeline buildContext + commit agent_prompt_v14.txt | feature/mcp-foundation-and-chatwoot          900d044 [origin/feature/mcp-foundation-and-chatwoot: gone] feat(mcp): add chatwoot read-only tools + complete container foundation
- projects/campaign-analysis/Onesignal: local branch tracking issues: Corp                                         bfb1a1d [origin/Corp: gone] Merged PR 168: feat(mcp): add chatwoot read-only tools + complete container foundation | ci-acr-push-foundry-rbac                     9930ac2 [origin/ci-acr-push-foundry-rbac: gone] fix(ci): use acr login for docker publish | feature/fix-pipeline-buildctx-and-prompt-v14 a4b2c45 [origin/feature/fix-pipeline-buildctx-and-prompt-v14: gone] fix(ci): pipeline buildContext + commit agent_prompt_v14.txt | feature/mcp-foundation-and-chatwoot          900d044 [origin/feature/mcp-foundation-and-chatwoot: gone] feat(mcp): add chatwoot read-only tools + complete container foundation
- projects/cs-agent: local branch tracking issues: feat/align-test-connector-to-production     1510f768 [origin/master: ahead 4, behind 48] feat(platform): Ink Skill Cards TUI + Stop banner  live | fix/codex-ci-endpoint                       a44f87d6 [origin/stage: ahead 1, behind 9] fix(ci): fix remaining variable refs + guard integration tests | fix/codex-foundry-agent                     950bcc37 [origin/stage: ahead 1, behind 7] fix(ci): resolv ...[truncated]
- projects/cs-agent/axia-seekapa-cs-agents-devops: local branch tracking issues: chore/disable-create-ticket-baseline-eval                  de498bbf [origin/chore/disable-create-ticket-baseline-eval: gone] Merged PR 167: docs(wiki): Foundry agent vs application endpoint divergence
- projects/qc: local branch tracking issues: feat/align-test-connector-to-production     1510f768 [origin/master: ahead 4, behind 48] feat(platform): Ink Skill Cards TUI + Stop banner  live | fix/codex-ci-endpoint                       a44f87d6 [origin/stage: ahead 1, behind 9] fix(ci): fix remaining variable refs + guard integration tests | fix/codex-foundry-agent                     950bcc37 [origin/stage: ahead 1, behind 7] fix(ci): resolv ...[truncated]
- projects/qc/qc-telephony-api: local branch tracking issues: hotfix/fix-e2e-target-language     47ef0f1 [origin/hotfix/fix-e2e-target-language: gone] fix(ci,e2e): widen E2E gate to PRs/hotfix and de-brittle Hebrew fixture | hotfix/pipeline-skipped-expression dc6c09b [origin/hotfix/pipeline-skipped-expression: gone] fix(ci): replace invalid skipped() with in(dependencies.E2ETests.result,...)

## PROJECT_ROUTING

- projects
  - Review last-24h high-risk artifact filenames before any push.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/.archive/Oded/archive/seekapa-training-platform
  - Review possible test/eval gate weakening in recent YAML/Python diffs.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/.archive/claude-orchestration
  - Review scan samples for broad exceptions/debug prints/any usage where relevant.
- projects/.archive/el-vadt
  - Review scan samples for broad exceptions/debug prints/any usage where relevant.
- projects/campaign-analysis
  - Review possible test/eval gate weakening in recent YAML/Python diffs.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/campaign-analysis/Onesignal
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/cs-agent
  - Review last-24h high-risk artifact filenames before any push.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/cs-agent/axia-seekapa-cs-agents-devops
  - Review possible test/eval gate weakening in recent YAML/Python diffs.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/personal/jsq-slq
  - Review scan samples for broad exceptions/debug prints/any usage where relevant.
- projects/qc
  - Review last-24h high-risk artifact filenames before any push.
  - Fix or explicitly triage failing configured static checks.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/qc/qc-telephony-api
  - Review possible test/eval gate weakening in recent YAML/Python diffs.
  - Add/strengthen tests around hot-zone files with repeated fix commits.
- projects/social-intelligence-unit
  - Review scan samples for broad exceptions/debug prints/any usage where relevant.
- projects/social-intelligence-unit/src/seekapa-video
  - Fix or explicitly triage failing configured static checks.

## ACTIONABLE_NEXT_STEPS

- Refresh Azure CLI authentication and rerun remote section: `az login` or restore the scheduled automation Azure context, then rerun this sweep.
- projects: run/fix `parse package.json`; current exit 999.
- projects/.archive/Oded/archive/seekapa-training-platform: run/fix `parse package.json`; current exit 999.
- projects/.archive/Oded/archive/seekapa-training-platform: inspect recent gate diff and add a sunset/work item if any weakening is intentional.
- projects/campaign-analysis: run/fix `uv run ruff check`; current exit 1.
- projects/campaign-analysis: inspect recent gate diff and add a sunset/work item if any weakening is intentional.
- projects/campaign-analysis/Onesignal: run/fix `parse package.json`; current exit 999.
- projects/cs-agent: run/fix `parse package.json`; current exit 999.
- projects/cs-agent/axia-seekapa-cs-agents-devops: run/fix `parse package.json`; current exit 999.
- projects/cs-agent/axia-seekapa-cs-agents-devops: inspect recent gate diff and add a sunset/work item if any weakening is intentional.
- projects/qc: run/fix `parse package.json`; current exit 999.
- projects/qc/qc-telephony-api: inspect recent gate diff and add a sunset/work item if any weakening is intentional.
- projects/social-intelligence-unit/src/seekapa-video: run/fix `bun run lint`; current exit 1.

## VERIFICATION_EVIDENCE

- Repo discovery: `find /home/shovalbe/projects -maxdepth 3 -name .git -type d` found 14 repos after recursive script discovery.
- RTK available: `/home/shovalbe/.local/bin/rtk`, version check completed before sweep.
- Azure account command exit: 1.
- projects: git log 30d lines=152; status bytes=815; static checks=1; scans=0.
- projects/.archive/Oded/archive/seekapa-training-platform: git log 30d lines=26; status bytes=74; static checks=1; scans=6.
- projects/.archive/claude-orchestration: git log 30d lines=0; status bytes=0; static checks=0; scans=4.
- projects/.archive/el-vadt: git log 30d lines=0; status bytes=0; static checks=0; scans=5.
- projects/campaign-analysis: git log 30d lines=76; status bytes=815; static checks=2; scans=4.
- projects/campaign-analysis/Onesignal: git log 30d lines=76; status bytes=815; static checks=1; scans=0.
- projects/cs-agent: git log 30d lines=152; status bytes=815; static checks=1; scans=0.
- projects/cs-agent/axia-seekapa-cs-agents-devops: git log 30d lines=133; status bytes=815; static checks=1; scans=5.
- projects/figma-4-all: git log 30d lines=0; status bytes=815; static checks=0; scans=0.
- projects/personal/jsq-slq: git log 30d lines=0; status bytes=80; static checks=0; scans=2.
- projects/qc: git log 30d lines=152; status bytes=815; static checks=1; scans=0.
- projects/qc/qc-telephony-api: git log 30d lines=33; status bytes=0; static checks=0; scans=4.
- projects/social-intelligence-unit: git log 30d lines=0; status bytes=815; static checks=0; scans=6.
- projects/social-intelligence-unit/src/seekapa-video: git log 30d lines=0; status bytes=815; static checks=1; scans=6.
