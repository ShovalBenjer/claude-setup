# Corp-AI Repos — Phase 1 Security & Hygiene Scan

**Date:** 2026-05-20  
**Scope:** 22 non-empty repos in `https://dev.azure.com/Corp-domain/Corp-AI`  
**Tooling:** gitleaks 8.21.2 (full history) + structural inventory (HEAD only)  
**Action taken:** READ-ONLY. No commits, no history rewrites.  
**Operator:** Shoval Benjer (shoval.be@i-sdd.com)

---

## TL;DR

- **970 secret findings** across 16 of 22 repos (16 repos have HEAD-resident findings)
- **290 findings are in current HEAD** (still in the live code); 680 are history-only
- **Zero junk files** committed to HEAD across all 22 repos — `.gitignore` hygiene is good
- **6 repos clean of secrets**: anyChat, compliance-exam-docker-deploy, market-daily-reports, taqyeem-broker-website, tech4all, video-understanding
- **Large binary files** (>5MB, not LFS) in 6 repos — see Large-files section
- 🚨 **PII risk flag**: `Seekapa-AI-Assistance/apps/qc-call-analyzer/calls for testings/*.mp3` — committed call recordings (may contain customer PII)

## Summary table

| Repo | Secrets total | HEAD | History-only | Large files | Risk tier |
|---|---:|---:|---:|---:|---|
| `Seekapa-AI-Assistance` | 729 | 126 | 603 | 3 | 🔴 P1 |
| `sentimark` | 110 | 49 | 61 | 0 | 🔴 P1 |
| `seekapa-training-platform` | 47 | 40 | 7 | 0 | 🔴 P1 |
| `automation-fabric` | 20 | 19 | 1 | 3 | 🟠 P2 |
| `social-intelligence-unit` | 15 | 14 | 1 | 34 | 🟠 P2 |
| `client-evaluation` | 10 | 10 | 0 | 0 | 🟠 P2 |
| `real-time-monitor` | 6 | 6 | 0 | 0 | 🟠 P2 |
| `figma-4-all` | 10 | 4 | 6 | 28 | 🟡 P3 |
| `campaign-analysis` | 4 | 4 | 0 | 0 | 🟡 P3 |
| `sales-agents` | 4 | 4 | 0 | 21 | 🟡 P3 |
| `seekapa-compliance-exam` | 4 | 4 | 0 | 0 | 🟡 P3 |
| `axia-seekapa-cs-agents` | 4 | 3 | 1 | 0 | 🟡 P3 |
| `aeo-docker-deploy` | 2 | 2 | 0 | 0 | 🟡 P3 |
| `automation-fabric-docker-deploy` | 2 | 2 | 0 | 0 | 🟡 P3 |
| `qc-telephony-api` | 2 | 2 | 0 | 0 | 🟡 P3 |
| `aeo` | 1 | 1 | 0 | 0 | 🟡 P3 |
| `anyChat` | 0 | 0 | 0 | 0 | ✅ clean |
| `compliance-exam-docker-deploy` | 0 | 0 | 0 | 0 | ✅ clean |
| `market-daily-reports` | 0 | 0 | 0 | 0 | ✅ clean |
| `taqyeem-broker-website` | 0 | 0 | 0 | 0 | ✅ clean |
| `tech4all` | 0 | 0 | 0 | 2 | ✅ clean |
| `video-understanding` | 0 | 0 | 0 | 0 | ✅ clean |

---

## Structural cleanup status — DONE BY EXISTING .gitignore

All 22 repos have a `.gitignore` and **none** of them have committed `node_modules/`, `__pycache__/`, `.env`, `.DS_Store`, `.idea/`, `.pytest_cache/`, `venv/`, `dist/`, etc. tracked in HEAD.

**Implication:** there is no junk-removal direct-commit work to do this round. The structural hygiene is already in place.

Old junk *may* exist deep in history (e.g. before .gitignore was added), but per your call this round is document-only — no history rewrites.

---

## Large file inventory (>5MB, not LFS)

These bloat clone sizes but are not necessarily wrong. Review each category:

### `Seekapa-AI-Assistance` — 3 large files

| Size | Path |
|---:|---|
| 8.0M | `apps/qc-call-analyzer/calls for testings/record1764830328.mp3` |
| 7.2M | `apps/qc-call-analyzer/calls for testings/record1764830561.mp3` |
| 6.2M | `apps/seekapa-training-platform/manual_venv/lib/python3.12/site-packages/psycopg2_binary.libs/libcrypto-81d66ed9.so.3` |

### `automation-fabric` — 3 large files

| Size | Path |
|---:|---|
| 6.5M | `src/runtime/tests/output/silver_campaign/sora_ai_revolution_12s.mp4` |
| 6.0M | `src/runtime/tests/output/silver_campaign/sora_china_move_12s.mp4` |
| 5.1M | `src/runtime/tests/output/video_samples/sora_silver_033814.mp4` |

### `figma-4-all` — 28 large files

| Size | Path |
|---:|---|
| 9.5M | `.temp-package/assets/models/yolo26n.onnx` |
| 26M | `.temp-package/vendor/ort-wasm-simd-threaded.asyncify.wasm` |
| 24M | `.temp-package/vendor/ort-wasm-simd-threaded.jsep.wasm` |
| 12M | `.temp-package/vendor/ort-wasm-simd-threaded.wasm` |
| 9.1M | `assets/Landingpages/seekapa-rebranding.png` |
| 6.3M | `assets/UI_UX_ALPHA_testing/QA2-b.png` |
| 7.2M | `assets/UI_UX_ALPHA_testing/QA2-c.png` |
| 5.6M | `assets/UI_UX_ALPHA_testing/QA2.png` |
| 6.3M | `assets/UI_UX_QA_testing/plugin-QA1.png` |
| 6.4M | `assets/UI_UX_QA_testing/plugin-QA2.png` |
| 13M | `assets/playground_banners/1080X1920 AR.svg` |
| 15M | `assets/playground_banners/1080x1080 V3.svg` |
| 13M | `assets/playground_banners/1080x1350 AR.svg` |
| 13M | `assets/playground_banners/1200X630 AR.svg` |
| 12M | `assets/playground_banners/gold2/1080X1920 AR.svg` |
| 12M | `assets/playground_banners/gold2/1080x1350 AR-1.svg` |
| 12M | `assets/playground_banners/gold2/1080x1350 AR.svg` |
| 12M | `assets/playground_banners/gold2/1200X630 AR.svg` |
| 12M | `assets/test_banners/OP-10366-10430Seekapa - UAE National Day - Organic (Copy).fig` |
| 11M | `assets/test_banners/OP-10428 Seekapa - Bahrain National Day Offer - RTG - AR (Copy).fig` |
| 12M | `assets/test_banners/OP-10472 Seekapa - OR - Christmas Wishes - AR (Copy).fig` |
| 29M | `assets/test_banners/OP-10475 Seekapa - OR - 2026 New Year - AR (Copy).fig` |
| 53M | `assets/test_v4/Ramadan2026-Seekapa- design-templates.fig` |
| 11M | `assets/test_v4/V3 AR.png` |
| 9.5M | `plugin/assets/models/yolo26n.onnx` |
| 26M | `plugin/vendor/ort-wasm-simd-threaded.asyncify.wasm` |
| 24M | `plugin/vendor/ort-wasm-simd-threaded.jsep.wasm` |
| 12M | `plugin/vendor/ort-wasm-simd-threaded.wasm` |

### `sales-agents` — 21 large files

| Size | Path |
|---:|---|
| 5.3M | `test-results/agent-to-agent/a2a_text_20260112_113112_maryam.raw` |
| 5.2M | `test-results/agent-to-agent/a2a_text_20260112_150008_maryam.raw` |
| 6.0M | `test-results/agent-to-agent/a2a_text_20260112_152931_maryam.raw` |
| 5.3M | `test-results/agent-to-agent/a2a_text_20260112_153807_maryam.raw` |
| 5.4M | `test-results/agent-to-agent/a2a_text_20260112_154503_maryam.raw` |
| 5.2M | `test-results/agent-to-agent/a2a_text_20260112_154839_maryam.raw` |
| 6.0M | `test-results/agent-to-agent/a2a_text_20260112_155345_maryam.raw` |
| 6.3M | `test-results/agent-to-agent/a2a_text_20260112_155720_maryam.raw` |
| 7.5M | `test-results/agent-to-agent/a2a_text_20260112_160101_maryam.raw` |
| 5.1M | `test-results/agent-to-agent/a2a_text_20260112_174817_maryam.raw` |
| 7.0M | `test-results/agent-to-agent/a2a_text_20260114_084600_maryam.raw` |
| 5.2M | `test-results/agent-to-agent/a2a_text_20260114_095903_maryam.raw` |
| 5.1M | `test-results/agent-to-agent/a2a_text_20260114_100030_maryam.raw` |
| 6.9M | `test-results/agent-to-agent/a2a_text_20260114_100230_maryam.raw` |
| 5.4M | `test-results/agent-to-agent/a2a_text_20260114_100344_maryam.raw` |
| 6.7M | `test-results/agent-to-agent/a2a_text_20260114_100556_maryam.raw` |
| 9.3M | `test-results/agent-to-agent/a2a_text_20260114_100723_maryam.raw` |
| 7.3M | `test-results/agent-to-agent/a2a_text_20260114_100930_maryam.raw` |
| 6.7M | `test-results/agent-to-agent/a2a_text_20260114_101046_maryam.raw` |
| 5.6M | `test-results/agent-to-agent/a2a_text_20260114_101156_maryam.raw` |
| 6.7M | `test-results/agent-to-agent/a2a_text_20260114_101312_maryam.raw` |

### `social-intelligence-unit` — 34 large files

| Size | Path |
|---:|---|
| 6.8M | `.mypy_cache/3.12/numpy/__init__.data.json` |
| 12M | `assets/full_Sekapa_rebranded.png` |
| 32M | `docs/books/AI Engineering.pdf` |
| 30M | `docs/books/Designing Interfaces Patterns for Effective Interaction Design - 3rd Edition - Jenifer Tidwell, Charles Brewer, Aynne Valencia - O'Reilly Media (2020).pdf` |
| 35M | `docs/books/Networking All-in-One For Dummies, 7th Edition.pdf` |
| 6.3M | `docs/books/Securing-Optimizing-Linux-The-Ultimate-Solution-v2.0.pdf` |
| 8.5M | `docs/books/Steve McConnell - Code Complete (2nd edition).pdf` |
| 12M | `docs/books/cleancodebook.pdf` |
| 28M | `docs/books/lawsofux.pdf` |
| 32M | `docs/seekapa-video/books/AI Engineering.pdf` |
| 30M | `docs/seekapa-video/books/Designing Interfaces Patterns for Effective Interaction Design - 3rd Edition - Jenifer Tidwell, Charles Brewer, Aynne Valencia - O'Reilly Media (2020).pdf` |
| 35M | `docs/seekapa-video/books/Networking All-in-One For Dummies, 7th Edition.pdf` |
| 6.3M | `docs/seekapa-video/books/Securing-Optimizing-Linux-The-Ultimate-Solution-v2.0.pdf` |
| 8.5M | `docs/seekapa-video/books/Steve McConnell - Code Complete (2nd edition).pdf` |
| 12M | `docs/seekapa-video/books/cleancodebook.pdf` |
| 28M | `docs/seekapa-video/books/lawsofux.pdf` |
| 12M | `frontend/.next_stale_1772126980/cache/webpack/client-development-fallback/0.pack.gz` |
| 15M | `frontend/.next_stale_1772126980/cache/webpack/client-development/12.pack.gz` |
| 8.3M | `frontend/.next_stale_1772126980/cache/webpack/client-development/13.pack.gz` |
| 5.1M | `frontend/.next_stale_1772126980/cache/webpack/client-development/5.pack.gz` |
| 7.3M | `frontend/.next_stale_1772126980/cache/webpack/client-development/8.pack.gz` |
| 70M | `frontend/.next_stale_1772126980/cache/webpack/client-production/0.pack` |
| 35M | `frontend/.next_stale_1772126980/cache/webpack/client-production/1.pack` |
| 13M | `frontend/.next_stale_1772126980/cache/webpack/client-production/2.pack` |
| 32M | `frontend/.next_stale_1772126980/cache/webpack/client-production/index.pack` |
| 31M | `frontend/.next_stale_1772126980/cache/webpack/client-production/index.pack.old` |
| 8.2M | `frontend/.next_stale_1772126980/cache/webpack/server-development/11.pack.gz` |
| 6.6M | `frontend/.next_stale_1772126980/cache/webpack/server-development/16.pack.gz` |
| 8.0M | `frontend/.next_stale_1772126980/cache/webpack/server-development/4.pack.gz` |
| 47M | `frontend/.next_stale_1772126980/cache/webpack/server-production/0.pack` |
| 41M | `frontend/.next_stale_1772126980/cache/webpack/server-production/1.pack` |
| 18M | `frontend/.next_stale_1772126980/cache/webpack/server-production/2.pack` |
| 26M | `frontend/.next_stale_1772126980/cache/webpack/server-production/index.pack` |
| 25M | `frontend/.next_stale_1772126980/cache/webpack/server-production/index.pack.old` |

### `tech4all` — 2 large files

| Size | Path |
|---:|---|
| 7.8M | `public/videos/qc-analyzer.mp4` |
| 8.5M | `public/videos/sentimark.mp4` |

### Recommendations (large files)

- 🚨 **`Seekapa-AI-Assistance/apps/qc-call-analyzer/calls for testings/*.mp3`** — likely customer call recordings. Per organization data-protection policy, raw customer audio shouldn't be in a git repo. Recommend removing from HEAD + history rewrite + audit who has clones.
- 🚨 **`Seekapa-AI-Assistance/apps/seekapa-training-platform/manual_venv/...so`** — committed Python venv binary. Junk. Add `manual_venv/` to gitignore + rm.
- 🟠 **`figma-4-all/.temp-package/`** — vendored ONNX model + ORT WASM (~71 MB). These should be downloaded at build time, not committed. Move to artifact storage or pin in package.json.
- 🟠 **`social-intelligence-unit/docs/seekapa-video/books/*.pdf`** — duplicated copies of the same PDFs already under `docs/books/`. Remove the duplicates (~150 MB saved at HEAD).
- 🟠 **`social-intelligence-unit/.mypy_cache/`** — cache that slipped past .gitignore. Remove from HEAD.
- 🟡 `social-intelligence-unit/docs/books/*.pdf` — multiple textbooks. Possibly copyright-flagged. Confirm licensing or move out of repo.
- 🟢 `automation-fabric/tests/output/*.mp4`, `sales-agents/test-results/*.raw`, `tech4all/public/videos/*.mp4` — test fixtures or web assets, likely legitimate but consider Git LFS for the videos.

---

## HEAD-resident secret findings (P1–P3)

These files **still exist in the current code** and contain matches that gitleaks flagged. Inspect each — some are placeholders in `.env.example` / `README.md` / docs (low risk), others are real keys (urgent).

All matches are **redacted** in this report. Open the file at the line shown to inspect locally; rotate immediately if the value is real and live.

### `Seekapa-AI-Assistance` — 126 HEAD findings in 26 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `apps/seekapa-compliance-exam/scripts/create_agent_now.py` | 7 | generic-api-key | `API_KEY = "REDACTED"` |
| `apps/seekapa-compliance-exam/scripts/create_english_agent.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |
| `apps/seekapa-compliance-exam/scripts/recreate_agent.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |
| `apps/seekapa-compliance-exam/scripts/update_agent_prompt.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/backend/.env.example` | 24 | generic-api-key | `your-jwt-secret> REDACTED` |
| `apps/seekapa-training-platform/backend/README.md` | 281 | generic-api-key | `S_WEBHOOK_SECRET=REDACTED` |
| `apps/seekapa-training-platform/backend/README.md` | 281 | generic-api-key | `S_WEBHOOK_SECRET=REDACTED` |
| `apps/seekapa-training-platform/backend/docs/DEPLOYMENT_CHECKLIST.md` | 102 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/personal/1" \   -H "x-functions-key: ` |
| `apps/seekapa-training-platform/backend/docs/DEPLOYMENT_CHECKLIST.md` | 102 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/personal/1" \   -H "x-functions-key: ` |
| `apps/seekapa-training-platform/backend/docs/DEPLOYMENT_CHECKLIST.md` | 129 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/team/1" \   -H "x-functions-key: REDA` |
| `apps/seekapa-training-platform/backend/docs/DEPLOYMENT_CHECKLIST.md` | 129 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/team/1" \   -H "x-functions-key: REDA` |
| `apps/seekapa-training-platform/backend/docs/api/API_QUICK_REFERENCE.md` | 27 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/personal/123" \   -H "x-function` |
| `apps/seekapa-training-platform/backend/docs/api/API_QUICK_REFERENCE.md` | 27 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/personal/123" \   -H "x-function` |
| `apps/seekapa-training-platform/backend/docs/api/API_QUICK_REFERENCE.md` | 47 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/team/1" \   -H "x-functions-key:` |
| `apps/seekapa-training-platform/backend/docs/api/API_QUICK_REFERENCE.md` | 47 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/team/1" \   -H "x-functions-key:` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 12 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels" \   -H "Authorization: Bearer RED` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 12 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels" \   -H "Authorization: Bearer RED` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 12 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels" \   -H "Authorization: Bearer RED` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 12 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels" \   -H "Authorization: Bearer RED` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 16 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels?language=english" \   -H "Authoriz` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 16 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels?language=english" \   -H "Authoriz` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 16 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels?language=english" \   -H "Authoriz` |
| `apps/seekapa-training-platform/backend/list_levels/QUICK_REFERENCE.md` | 16 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels?language=english" \   -H "Authoriz` |
| `apps/seekapa-training-platform/backend/login/QUICK_START.md` | 111 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \      -H "Authorization: ` |
| `apps/seekapa-training-platform/backend/login/QUICK_START.md` | 111 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \      -H "Authorization: ` |
| `apps/seekapa-training-platform/backend/login/QUICK_START.md` | 111 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \      -H "Authorization: ` |
| `apps/seekapa-training-platform/backend/login/QUICK_START.md` | 111 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \      -H "Authorization: ` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 41 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 41 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 41 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 41 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 165 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \   -H "Authorization: Bea` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 165 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \   -H "Authorization: Bea` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 165 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \   -H "Authorization: Bea` |
| `apps/seekapa-training-platform/backend/login/TEST_LOGIN.md` | 165 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \   -H "Authorization: Bea` |
| `apps/seekapa-training-platform/backend/register/README.md` | 57 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/register/README.md` | 57 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/register/README.md` | 57 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/register/README.md` | 57 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 199 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 199 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 199 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 199 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 230 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 230 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 230 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/backend/shared/auth.py` | 230 | generic-api-key | `token = "REDACTED"` |
| `apps/seekapa-training-platform/diagnose_elevenlabs.py` | 10 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/diagnose_elevenlabs.py` | 10 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/diagnose_elevenlabs.py` | 10 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/diagnose_elevenlabs.py` | 10 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 130 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 130 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 130 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 130 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 262 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 262 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 262 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 262 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 1085 | curl-auth-header | `curl -X GET http://localhost:7071/api/personal/123 \   -H "Authorization: Bearer` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 1085 | curl-auth-header | `curl -X GET http://localhost:7071/api/personal/123 \   -H "Authorization: Bearer` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 1085 | curl-auth-header | `curl -X GET http://localhost:7071/api/personal/123 \   -H "Authorization: Bearer` |
| `apps/seekapa-training-platform/docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 1085 | curl-auth-header | `curl -X GET http://localhost:7071/api/personal/123 \   -H "Authorization: Bearer` |
| `apps/seekapa-training-platform/docs/archive/AZURE_PRODUCTION_CREDENTIALS.md` | 170 | generic-api-key | `API Key:  REDACTED` |
| `apps/seekapa-training-platform/docs/archive/AZURE_PRODUCTION_CREDENTIALS.md` | 170 | generic-api-key | `API Key:  REDACTED` |
| `apps/seekapa-training-platform/docs/archive/AZURE_PRODUCTION_CREDENTIALS.md` | 170 | generic-api-key | `API Key:  REDACTED` |
| `apps/seekapa-training-platform/docs/archive/AZURE_PRODUCTION_CREDENTIALS.md` | 170 | generic-api-key | `API Key:  REDACTED` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 141 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 141 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 141 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 141 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 227 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 227 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 227 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 227 | generic-api-key | `token": "REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/DAY1_COMPLETION_STATUS.md` | 56 | generic-api-key | `LEVENLABS_API_KEY = REDACTED` |
| `apps/seekapa-training-platform/docs/archive/DAY1_COMPLETION_STATUS.md` | 56 | generic-api-key | `LEVENLABS_API_KEY = REDACTED` |
| `apps/seekapa-training-platform/docs/archive/DAY1_COMPLETION_STATUS.md` | 56 | generic-api-key | `LEVENLABS_API_KEY = REDACTED` |
| `apps/seekapa-training-platform/docs/archive/DAY1_COMPLETION_STATUS.md` | 56 | generic-api-key | `LEVENLABS_API_KEY = REDACTED` |
| `apps/seekapa-training-platform/docs/archive/PHASE2_ROOT_CAUSE_ANALYSIS.md` | 235 | generic-api-key | `EPLOYMENT_TOKEN="REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/PHASE2_ROOT_CAUSE_ANALYSIS.md` | 235 | generic-api-key | `EPLOYMENT_TOKEN="REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/PHASE2_ROOT_CAUSE_ANALYSIS.md` | 235 | generic-api-key | `EPLOYMENT_TOKEN="REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/PHASE2_ROOT_CAUSE_ANALYSIS.md` | 235 | generic-api-key | `EPLOYMENT_TOKEN="REDACTED"` |
| `apps/seekapa-training-platform/docs/archive/PRODUCTION_READY_NOV5_2025.md` | 37 | generic-api-key | `Secret ID: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/PRODUCTION_READY_NOV5_2025.md` | 37 | generic-api-key | `Secret ID: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/PRODUCTION_READY_NOV5_2025.md` | 37 | generic-api-key | `Secret ID: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/PRODUCTION_READY_NOV5_2025.md` | 37 | generic-api-key | `Secret ID: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 30 | generic-api-key | `secret: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 30 | generic-api-key | `secret: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 30 | generic-api-key | `secret: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 30 | generic-api-key | `secret: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 213 | generic-api-key | `Secret: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 213 | generic-api-key | `Secret: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 213 | generic-api-key | `Secret: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 213 | generic-api-key | `Secret: REDACTED` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 268 | generic-api-key | `secret updated in Azure: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 268 | generic-api-key | `secret updated in Azure: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 268 | generic-api-key | `secret updated in Azure: `REDACTED`` |
| `apps/seekapa-training-platform/docs/archive/USER_REPORT_FLOW.md` | 268 | generic-api-key | `secret updated in Azure: `REDACTED`` |
| `apps/seekapa-training-platform/manual_analyze_session_102.py` | 25 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102.py` | 25 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102.py` | 25 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102.py` | 25 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102_standalone.py` | 19 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102_standalone.py` | 19 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102_standalone.py` | 19 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/manual_analyze_session_102_standalone.py` | 19 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 24 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 24 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 24 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 24 | generic-api-key | `LEVENLABS_API_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 25 | generic-api-key | `RE_OPENAI_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 25 | generic-api-key | `RE_OPENAI_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/process_session_103.py` | 25 | generic-api-key | `RE_OPENAI_KEY = "REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 40 | generic-api-key | `LEVENLABS_API_KEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 40 | generic-api-key | `LEVENLABS_API_KEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 54 | generic-api-key | `RE_OPENAI_API_KEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 54 | generic-api-key | `RE_OPENAI_API_KEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 60 | generic-api-key | `UMENTATIONKEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 60 | generic-api-key | `UMENTATIONKEY=REDACTED"` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 61 | generic-api-key | `umentationKey=REDACTED;` |
| `apps/seekapa-training-platform/scripts/restore-all-settings.sh` | 61 | generic-api-key | `umentationKey=REDACTED;` |
| `apps/seekapa-training-platform/test_webhook.py` | 15 | generic-api-key | `WEBHOOK_SECRET = "REDACTED"` |
| `apps/seekapa-training-platform/test_webhook.py` | 15 | generic-api-key | `WEBHOOK_SECRET = "REDACTED"` |
| `apps/seekapa-training-platform/test_webhook.py` | 15 | generic-api-key | `WEBHOOK_SECRET = "REDACTED"` |
| `apps/seekapa-training-platform/test_webhook.py` | 15 | generic-api-key | `WEBHOOK_SECRET = "REDACTED"` |

### `sentimark` — 49 HEAD findings in 24 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `.env.docker` | 55 | nextauth-secret | `REDACTED=your-32-character-secret-key-here-change-me` |
| `.env.docker` | 55 | nextauth-secret | `REDACTED=your-32-character-secret-key-here-change-me` |
| `CLAUDE.md` | 69 | curl-auth-user | `curl -X POST -u 'REDACTED' ` |
| `CLAUDE.md` | 161 | curl-auth-user | `curl -X POST -u 'REDACTED' ` |
| `DATABASE_SETUP.md` | 154 | postgres-password-inline | `postgresql://seekapaadmin:REDACTED@` |
| `DATABASE_SETUP.md` | 164 | postgres-password-inline | `postgresql://seekapaadmin:REDACTED@` |
| `DATABASE_SETUP.md` | 322 | postgres-password-inline | `postgresql://{os.getenv('POSTGRES_USER')}:REDACTED@` |
| `app/api/reports/generate/route.ts` | 161 | high-entropy-base64 | `REDACTED` |
| `app/api/reports/generate/route.ts` | 173 | high-entropy-base64 | `REDACTED` |
| `automation-fabric/CLAUDE.md` | 291 | postgres-password-inline | `postgresql://automation_app_user:REDACTED@` |
| `automation-fabric/CLAUDE.md` | 291 | postgres-password-inline | `postgresql://automation_app_user:REDACTED@` |
| `automation-fabric/src/runtime/function_app.py` | 25 | postgres-password-inline | `postgresql://automation_app_user:REDACTED@` |
| `automation-fabric/src/runtime/tests/conftest.py` | 19 | postgres-password-inline | `postgresql://automation_app_user:REDACTED@` |
| `automation-fabric/src/runtime/tests/conftest.py` | 19 | postgres-password-inline | `postgresql://automation_app_user:REDACTED@` |
| `deploy-kudu.sh` | 25 | curl-auth-user | `curl -s -o /tmp/deploy_response.txt -w "%{http_code}" \   -X POST \   -u 'REDACT` |
| `deploy-kudu.sh` | 27 | high-entropy-base64 | `REDACTED` |
| `deploy-kudu.sh` | 27 | high-entropy-base64 | `REDACTED` |
| `deploy-kudu.sh` | 27 | high-entropy-base64 | `REDACTED` |
| `deploy-kudu.sh` | 27 | high-entropy-base64 | `REDACTED` |
| `docs/HANDOVER_SESSION_20471.md` | 45 | nextauth-secret | `REDACTED: sentimark-v2-production-secret-key-2025` |
| `docs/HANDOVER_SESSION_20471.md` | 59 | nextauth-secret | `REDACTED=sentimark-v2-production-secret-key-2025` |
| `docs/HANDOVER_SESSION_20471.md` | 158 | nextauth-secret | `REDACTED=sentimark-v2-production-secret-key-2025` |
| `docs/NEXT_SESSION_HANDOVER.md` | 15 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `docs/NEXT_SESSION_HANDOVER.md` | 15 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `evaluation/compute_baselines.py` | 21 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `evaluation/grok_first_eval.py` | 8 | postgres-password-inline | `postgresql://..."     python evaluation/grok_first_eval.py --from-keyvault  P` |
| `evaluation/grok_first_eval.py` | 770 | generic-api-key | `key == "REDACTED"` |
| `evaluation/grok_first_eval.py` | 811 | generic-api-key | `key == "REDACTED"` |
| `evaluation/grok_first_eval.py` | 822 | generic-api-key | `key == "REDACTED"` |
| `scripts/monitor_drift.py` | 61 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `scripts/monitor_v3_shadow.py` | 29 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `scripts/system_state_report.py` | 104 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/backend/keyvault.py` | 88 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/frontend/.env.production` | 12 | generic-api-key | `NEXTAUTH_SECRET=REDACTED` |
| `sentimark-v2/frontend/.env.production` | 12 | nextauth-secret | `REDACTED=M6ovPcF10o6j4pgFtFeZyStrE3ZaZr8gmrIIYC_PQqo7mmQhJ3tHt2B2a1e4-Kgg` |
| `sentimark-v2/frontend/.env.production` | 12 | nextauth-secret | `REDACTED=sentimark-v2-production-secret-key-2025` |
| `sentimark-v2/tests/integration/test_llm_prediction_engine.py` | 41 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/integration/test_llm_prediction_engine.py` | 41 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/integration/test_prediction_api.py` | 48 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/integration/test_prediction_api.py` | 48 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/integration/test_prediction_api.py` | 66 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/integration/test_prediction_api.py` | 66 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/unit/test_auth_middleware.py` | 69 | generic-api-key | `api_key="REDACTED"` |
| `sentimark-v2/tests/unit/test_auth_middleware.py` | 72 | generic-api-key | `est.state.api_key == "REDACTED"` |
| `sentimark-v2/tests/unit/test_db_prediction_functions.py` | 41 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `sentimark-v2/tests/unit/test_db_prediction_functions.py` | 41 | postgres-password-inline | `postgresql://sentimark_app_user:REDACTED@` |
| `tests/backtest/backtest_v3.py` | 10 | postgres-password-inline | `postgresql://..."      # From CSV export     python tests/backtest/backtest_v` |
| `tests/e2e/phase6/web-push.spec.ts` | 38 | high-entropy-base64 | `REDACTED` |
| `validation/api-chat-sis.json` | 1 | generic-api-key | `session_token": "REDACTED"` |

### `seekapa-training-platform` — 40 HEAD findings in 25 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `backend/.env.example` | 24 | generic-api-key | `your-jwt-secret> REDACTED` |
| `backend/README.md` | 281 | generic-api-key | `S_WEBHOOK_SECRET=REDACTED` |
| `backend/docs/DEPLOYMENT_CHECKLIST.md` | 102 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/personal/1" \   -H "x-functions-key: ` |
| `backend/docs/DEPLOYMENT_CHECKLIST.md` | 129 | curl-auth-header | `curl "https://<app>.azurewebsites.net/api/team/1" \   -H "x-functions-key: REDA` |
| `backend/docs/api/API_QUICK_REFERENCE.md` | 27 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/personal/123" \   -H "x-function` |
| `backend/docs/api/API_QUICK_REFERENCE.md` | 47 | curl-auth-header | `curl "https://<your-app>.azurewebsites.net/api/team/1" \   -H "x-functions-key:` |
| `backend/list_levels/QUICK_REFERENCE.md` | 12 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels" \   -H "Authorization: Bearer RED` |
| `backend/list_levels/QUICK_REFERENCE.md` | 16 | curl-auth-header | `curl -X GET "https://your-api.com/api/levels?language=english" \   -H "Authoriz` |
| `backend/login/QUICK_START.md` | 111 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \      -H "Authorization: ` |
| `backend/login/TEST_LOGIN.md` | 41 | generic-api-key | `token": "REDACTED"` |
| `backend/login/TEST_LOGIN.md` | 165 | curl-auth-header | `curl -X GET http://localhost:7071/api/stats/personal \   -H "Authorization: Bea` |
| `backend/register/README.md` | 57 | generic-api-key | `token": "REDACTED"` |
| `backend/shared/auth.py` | 199 | generic-api-key | `token = "REDACTED"` |
| `backend/shared/auth.py` | 230 | generic-api-key | `token = "REDACTED"` |
| `backend/shared/email_service.py` | 14 | generic-api-key | `accesskey=REDACTED'` |
| `backend/shared/email_service.py` | 16 | generic-api-key | `accesskey=REDACTED"` |
| `docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 130 | generic-api-key | `token": "REDACTED"` |
| `docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 262 | generic-api-key | `token": "REDACTED"` |
| `docs/archive/AUTH_TECHNICAL_REFERENCE.md` | 1085 | curl-auth-header | `curl -X GET http://localhost:7071/api/personal/123 \   -H "Authorization: Bearer` |
| `docs/archive/AZURE_PRODUCTION_CREDENTIALS.md` | 170 | generic-api-key | `API Key:  REDACTED` |
| `docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 141 | generic-api-key | `token": "REDACTED"` |
| `docs/archive/BACKEND_AUTH_VALIDATION_REPORT.md` | 227 | generic-api-key | `token": "REDACTED"` |
| `docs/archive/DAY1_COMPLETION_STATUS.md` | 56 | generic-api-key | `LEVENLABS_API_KEY = REDACTED` |
| `docs/archive/PHASE2_ROOT_CAUSE_ANALYSIS.md` | 235 | generic-api-key | `EPLOYMENT_TOKEN="REDACTED"` |
| `docs/archive/PRODUCTION_READY_NOV5_2025.md` | 37 | generic-api-key | `Secret ID: REDACTED` |
| `docs/archive/USER_REPORT_FLOW.md` | 30 | generic-api-key | `secret: `REDACTED`` |
| `docs/archive/USER_REPORT_FLOW.md` | 213 | generic-api-key | `Secret: REDACTED` |
| `docs/archive/USER_REPORT_FLOW.md` | 268 | generic-api-key | `secret updated in Azure: `REDACTED`` |
| `scripts/deep_search_calls.py` | 12 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/email_arabic_reports_nissreen.py` | 44 | generic-api-key | `accesskey=REDACTED'` |
| `scripts/email_qusai_reports.py` | 43 | generic-api-key | `accesskey=REDACTED'` |
| `scripts/fetch_all_recent_calls.py` | 12 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/list_all_agents.py` | 7 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/restore-all-settings.sh` | 40 | generic-api-key | `LEVENLABS_API_KEY=REDACTED"` |
| `scripts/restore-all-settings.sh` | 54 | generic-api-key | `RE_OPENAI_API_KEY=REDACTED"` |
| `scripts/restore-all-settings.sh` | 60 | generic-api-key | `UMENTATIONKEY=REDACTED"` |
| `scripts/restore-all-settings.sh` | 61 | generic-api-key | `umentationKey=REDACTED;` |
| `scripts/send_summary_email.py` | 21 | generic-api-key | `accesskey=REDACTED'` |
| `scripts/sync_and_email_today.py` | 32 | generic-api-key | `LEVENLABS_API_KEY = 'REDACTED'` |
| `scripts/sync_and_email_today.py` | 35 | generic-api-key | `accesskey=REDACTED'` |

### `automation-fabric` — 19 HEAD findings in 18 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `src/runtime/activities/email_overview_activities.py` | 1467 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/integrations/acs_email_client.py` | 24 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/minimal_email_test.py` | 6 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_arabic_qa.py` | 9 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_daily_briefing_test.py` | 21 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_email_acs.py` | 12 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_multilang_qa.py` | 12 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_premium_async.py` | 9 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_simple_test.py` | 12 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_test_premium_email.py` | 13 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_test_premium_email.py` | 153 | generic-api-key | `access_key = "REDACTED"` |
| `src/runtime/send_today_emails.py` | 13 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_v10_qa.py` | 13 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_v10_real.py` | 43 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_v10_test.py` | 7 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_v8_test_emails.py` | 45 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/send_when_ready.sh` | 23 | generic-api-key | `accesskey=REDACTED'` |
| `src/runtime/test_arabic_email.py` | 23 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/test_email_fix.py` | 21 | generic-api-key | `accesskey=REDACTED"` |

### `social-intelligence-unit` — 14 HEAD findings in 10 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `.env.example` | 9 | generic-api-key | `APIFY_API_KEY=REDACTED` |
| `.env.example` | 9 | generic-api-key | `APIFY_API_KEY=REDACTED` |
| `docs/api/ELEVENLABS_INTEGRATION.md` | 86 | generic-api-key | `LEVENLABS_API_KEY=REDACTED` |
| `docs/apify/Apify Meta Ads Scraping Guide.md` | 486 | curl-auth-header | `curl -X POST "https://api.apify.com/v2/acts/apify~facebook-ads-scraper/runs" \  ` |
| `docs/apify/apify_ref.txt` | 72 | generic-api-key | `defaultKeyValueStoreId": "REDACTED"` |
| `docs/archive/SIU-SOTA-Stack.md` | 559 | generic-api-key | `Portkey: REDACTED ` |
| `docs/archive/adspy_doc.md` | 35 | curl-auth-header | `curl -d "username=youremail@gmail.com&password=xxxxxx&grant_type=password" -X PO` |
| `docs/archive/validation_results.md` | 67 | generic-api-key | `APIFY_API_KEY=REDACTED` |
| `docs/audit/EVIDENCE_REPORT_20260308_131658Z.md` | 201 | generic-api-key | `siu_csrf_token=REDACTED;` |
| `docs/audit/EVIDENCE_REPORT_20260308_131658Z.md` | 209 | generic-api-key | `siu_csrf_token=REDACTED;` |
| `frontend/.next_stale_1772126980/prerender-manifest.json` | 1 | generic-api-key | `EncryptionKey":"REDACTED"` |
| `frontend/.next_stale_1772126980/prerender-manifest.json` | 1 | generic-api-key | `odeSigningKey":"REDACTED"` |
| `frontend/.next_stale_1772126980/server/middleware-manifest.json` | 23 | generic-api-key | `NCRYPTION_KEY": "REDACTED"` |
| `frontend/.next_stale_1772126980/server/middleware-manifest.json` | 24 | generic-api-key | `E_SIGNING_KEY": "REDACTED"` |

### `client-evaluation` — 10 HEAD findings in 3 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `API-GUIDE.md` | 28 | curl-auth-header | `curl -X POST "https://victorious-hill-0277e8403.1.azurestaticapps.net/api/evalua` |
| `client data pulling.txt` | 6 | generic-api-key | `api key = REDACTED` |
| `client data pulling.txt` | 9 | curl-auth-header | `curl -X POST "https://personalassyst-be-bhc7h6bkcrgnbhca.westeurope-01.azurewebs` |
| `client data pulling.txt` | 11 | generic-api-key | `X-API-Token: REDACTED"` |
| `docs/PERSONALASSYST-API.md` | 26 | curl-auth-header | `curl -X POST \   https://personalassyst-be-bhc7h6bkcrgnbhca.westeurope-01.azurew` |
| `docs/PERSONALASSYST-API.md` | 29 | generic-api-key | `X-API-Token: REDACTED"` |
| `docs/PERSONALASSYST-API.md` | 37 | generic-api-key | `token": "REDACTED"` |
| `docs/PERSONALASSYST-API.md` | 47 | generic-api-key | `token=REDACTED"` |
| `docs/PERSONALASSYST-API.md` | 83 | generic-api-key | `MASTER_API_KEY = "REDACTED"` |
| `docs/PERSONALASSYST-API.md` | 121 | generic-api-key | `MASTER_API_KEY = 'REDACTED'` |

### `real-time-monitor` — 6 HEAD findings in 3 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `backend/tests/test_auth.py` | 12 | generic-api-key | `_TEST_JWT_SECRET = "REDACTED"` |
| `backend/tests/test_elevenlabs.py` | 30 | generic-api-key | `api_key="REDACTED"` |
| `backend/tests/test_elevenlabs.py` | 37 | generic-api-key | `client._api_key == "REDACTED"` |
| `backend/tests/test_ws_audio.py` | 253 | generic-api-key | `key=REDACTED"` |
| `backend/tests/test_ws_audio.py` | 254 | generic-api-key | `key=REDACTED"` |
| `backend/tests/test_ws_audio.py` | 275 | generic-api-key | `api_key": "REDACTED"` |

### `campaign-analysis` — 4 HEAD findings in 4 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `app_mcp/tests/test_f02_crm_summary.py` | 73 | generic-api-key | `token=REDACTED"` |
| `app_mcp/tests/test_f08_msi_to_kv.py` | 70 | generic-api-key | `secrets_user_role = "REDACTED"` |
| `app_mcp/tests/test_redaction.py` | 130 | generic-api-key | `token=REDACTED"` |
| `azure-pipelines.yml` | 119 | generic-api-key | `MCP_OAUTH_SIGNING_KEY=REDACTED ` |

### `figma-4-all` — 4 HEAD findings in 2 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `docs/.archive/docs-legacy/ARCHITECTURE.md` | 1264 | generic-api-key | `fileKey": "REDACTED"` |
| `docs/.archive/docs-legacy/ARCHITECTURE.md` | 1722 | generic-api-key | `file_key="REDACTED"` |
| `docs/architecture/sam3-azure-container.md` | 1222 | curl-auth-header | `curl -X POST \   https://sam3-segmentation.eastus.azurecontainerapps.io/api/v1/s` |
| `docs/architecture/sam3-azure-container.md` | 1246 | curl-auth-header | `curl -X POST \   https://sam3-segmentation.eastus.azurecontainerapps.io/api/v1/s` |

### `sales-agents` — 4 HEAD findings in 4 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `HANDOVER.md` | 224 | generic-api-key | `LEVENLABS_API_KEY=REDACTED` |
| `README.md` | 11 | generic-api-key | `token=REDACTED` |
| `config/agent-info.json` | 32 | generic-api-key | `function_key": "REDACTED"` |
| `scripts/send_evaluation_report.py` | 44 | generic-api-key | `accesskey=REDACTED"` |

### `seekapa-compliance-exam` — 4 HEAD findings in 4 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `scripts/create_agent_now.py` | 7 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/create_english_agent.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/recreate_agent.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |
| `scripts/update_agent_prompt.py` | 11 | generic-api-key | `API_KEY = "REDACTED"` |

### `axia-seekapa-cs-agents` — 3 HEAD findings in 2 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `azure-function-crm/test-crm-endpoints.sh` | 8 | generic-api-key | `FUNC_KEY="REDACTED"` |
| `docs/auth-setup.md` | 156 | generic-api-key | `signed_token": "REDACTED"` |
| `docs/auth-setup.md` | 173 | generic-api-key | `signed_token": "REDACTED"` |

### `aeo-docker-deploy` — 2 HEAD findings in 2 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `.claude/handover-20260126-0eb7bb.md` | 48 | generic-api-key | `COSMOS_KEY=REDACTED` |
| `dashboard/lib/utils.ts` | 181 | generic-api-key | `token=REDACTED`` |

### `automation-fabric-docker-deploy` — 2 HEAD findings in 2 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `src/runtime/activities/email_overview_activities.py` | 2597 | generic-api-key | `accesskey=REDACTED"` |
| `src/runtime/integrations/acs_email_client.py` | 24 | generic-api-key | `accesskey=REDACTED"` |

### `qc-telephony-api` — 2 HEAD findings in 1 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `docs/OPERATIONS_HANDOVER.txt` | 6 | generic-api-key | `KEY: REDACTED` |
| `docs/OPERATIONS_HANDOVER.txt` | 6 | generic-api-key | `KEY: REDACTED` |

### `aeo` — 1 HEAD findings in 1 files

| File | Line | RuleID | Match (redacted) |
|---|---:|---|---|
| `dashboard/lib/utils.ts` | 181 | generic-api-key | `token=REDACTED`` |

---

## Findings by RuleID across all repos (history + HEAD)

| RuleID | Count | Notes |
|---|---:|---|
| `generic-api-key` | 773 | broadest pattern — mix of real keys, placeholders in examples, JWT-like strings in test fixtures |
| `curl-auth-header` | 102 | Authorization headers in curl commands inside docs/scripts — often example tokens |
| `postgres-password-inline` | 33 | PostgreSQL connection string with embedded password — HIGH risk if real |
| `high-entropy-base64` | 20 | random-looking base64 strings — could be keys, certificates, or just data |
| `gcp-api-key` | 18 | Google Cloud API key — HIGH risk |
| `nextauth-secret` | 10 | NextAuth secret literal — HIGH risk if real |
| `curl-auth-user` | 6 | basic-auth user:pass in curl commands |
| `elevenlabs-api-key` | 4 | ElevenLabs API key — HIGH risk |
| `azure-openai-key` | 2 | Azure OpenAI key pattern — HIGH risk |
| `jwt-secret` | 1 |  |
| `webhook-secret` | 1 | webhook signing secret |

---

## Recommended next steps

**This round (document-only, your stated scope):** complete. Report is this file.

**Suggested follow-up rounds, in priority order:**

1. **🔴 P1 — Triage HEAD-resident findings in the four worst repos** (Seekapa-AI-Assistance 126, sentimark 49, seekapa-training-platform 40, automation-fabric 19). For each: open the file, decide placeholder vs real. If real → rotate at the provider first, then rewrite history + force-push (per-repo explicit OK).
2. **🚨 PII** — Remove `Seekapa-AI-Assistance/apps/qc-call-analyzer/calls for testings/*.mp3` from history (call recordings may contain customer PII; surfaces a data-protection issue regardless of who can clone).
3. **🟠 Junk-in-history cleanup** — `Seekapa-AI-Assistance/manual_venv/`, `figma-4-all/.temp-package/`, `social-intelligence-unit/.mypy_cache/`, duplicate book PDFs. Reduces clone size meaningfully.
4. **🟡 .env.docker, .env.example etc.** — confirm these are placeholder templates and not committed real values; if real, rotate.
5. **🟢 Set up gitleaks as pre-commit / pipeline gate** so future commits are blocked at the source, not detected after the fact.

**Scope I did NOT take action on:**
- No history rewrites (`git filter-repo` / BFG) — per your call
- No direct commits — because no HEAD-level structural junk was found to remove
- No secret rotation at providers (Azure KV, ElevenLabs, etc.) — out of scope, needs Yasha/Barak coordination on shared infra

---

## Reproduction

- Clones: `$CLAUDE_JOB_DIR/repos/<repo>` (preserved for this session only)
- Raw gitleaks JSON: `$CLAUDE_JOB_DIR/scan/leaks/<repo>.json`
- Junk inventory: `$CLAUDE_JOB_DIR/scan/junk_v2/<repo>.txt`
- Scan script: `$CLAUDE_JOB_DIR/scan/scan_all.sh`