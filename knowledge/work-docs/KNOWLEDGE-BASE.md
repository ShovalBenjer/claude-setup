# Axia & Seekapa CS Agents -- Knowledge Base

## What This System Does (Plain English)

AI-powered customer service chatbots for Seekapa and Axia, two FSA-regulated forex trading platforms. Customers reach the agents through 4 channels (web widget, Telegram, WhatsApp, email). The agents answer FAQs from a knowledge base, authenticate customers via email OTP, pull account data from the CRM (PandaTS MySQL), and escalate compliance-sensitive queries to human agents via LiveAgent ticketing.

**Users**: Seekapa and Axia customers seeking account support, KYC status, trading information, and general platform help.

**Business value**: 24/7 customer support automation in 4 languages (EN, AR, ES, PT), reduced human agent workload for routine queries, mandatory compliance escalation for regulated topics (KYC, high-value withdrawals, legal identity changes).

## Architecture Overview

**Interactive diagram**: [system-arch-interactive.html](diagrams/system-arch-interactive.html) (13 nodes, 13-step guided tour) | [Macro view](diagrams/system-arch-interactive-macro.html) (8-group overview)

### Key Architectural Decisions

1. **Channel-agnostic routing**: All 4 channels (widget, Telegram, WhatsApp, email) are normalized to a unified internal format via `message_normalizer.py`. The channel router sends the normalized message to the AI agent and formats the response back for the originating channel. Adding a new channel requires only a new normalizer function.

2. **Dual authentication paths**: HMAC-signed deep links (for pre-authenticated users from parent apps) and email OTP (for unauthenticated users). Signed links prevent login ID guessing attacks; OTP provides email-based verification with 5-minute expiry and 3-attempt lockout.

3. **Brand-aware CRM routing**: Both Axia and Seekapa share the same Azure Function App, but queries are routed to the correct CRM database and table based on the `brand` parameter. PandaTS MySQL for detailed trading data, legacy SQL Server for OTP-verified customer records.

4. **Hard escalation gate (Step 0)**: The agent system prompt includes a mandatory first check for compliance-sensitive triggers (KYC rejected, >$50K withdrawals, legal identity, regulatory inquiries). These are escalated to human agents immediately, before any other processing.

5. **Hybrid test connector**: The test framework uses Applications endpoint for KB queries and FunctionToolConnector (raw Responses API) for CRM queries, because the Applications endpoint returns 500 for OpenAPI tool calls. Content safety refusal detection handles Azure AI's ~20% false positive rate.

## Domain Knowledge

### Lessons Learned
- **Content Safety false positives (~20% rate)**: Azure AI Content Safety filters intermittently refuse legitimate customer service responses. The agent connector detects refusal patterns and retries automatically. This is an Azure platform issue, not a prompt issue.
- **Agent prompt versioning is critical**: System prompts are iterated via multi-model debate (GPT-5 Pro + Gemini + Perplexity + Codex). Each version is kept in `agent-prompts/` for rollback capability. Current: Seekapa v36, AxiaCS v30.
- **OTP in-memory storage limits scalability**: OTP codes are stored in a thread-safe Python dict. This works for the current Consumption plan (single instance) but will not survive function app restarts or scale-out. Migration to Azure Table Storage or Redis is planned.
- **Two CRM databases serve different purposes**: PandaTS MySQL (detailed trading data: positions, history, balances) and legacy SQL Server (customer support records for OTP verification). Both are used concurrently -- they are not redundant.

### Common Pitfalls
- **Brand parameter must be lowercase**: CRM table routing uses `brand.lower()` for key lookup. Passing "Seekapa" instead of "seekapa" causes lookup failures.
- **Telegram bot token rotation**: The Telegram bot token is stored in Key Vault (`TELEGRAM_BOT_TOKEN`). If rotated, the webhook URL must be re-registered with Telegram's `setWebhook` API.
- **LiveAgent department IDs are placeholders**: The `ticket_categories.py` file has empty department IDs (`""`) that need to be filled from the LiveAgent admin panel before escalation will work in production.
- **Function keys vs signed tokens**: The Azure Function endpoints use Function Keys for API-level auth. Signed tokens provide customer-level auth. Do not confuse the two -- a valid Function Key does not authenticate a customer.

## Operations

### What Runs Automatically
| Component | Trigger | What It Does | Failure Impact |
|-----------|---------|-------------|----------------|
| Channel Router | HTTP POST from any channel | Routes messages to AI agent | Customer receives no response |
| OTP send/verify | Agent tool call | Authenticates customer for CRM access | Customer cannot access account data |
| Telegram Webhook | Telegram Bot API push | Receives and processes Telegram messages | Telegram channel goes silent |
| Rate Limiter cleanup | On each request (passive) | Expires old rate limit entries | Memory growth (non-critical) |

### How to Monitor Health
```bash
# Check function app status
az functionapp show --resource-group AZAI_group --name axia-seekapa-crm --query "state" -o tsv

# View live logs
az webapp log tail --resource-group AZAI_group --name axia-seekapa-crm

# List deployed functions
az functionapp function list --resource-group AZAI_group --name axia-seekapa-crm -o table

# Get function key for testing
az functionapp keys list --resource-group AZAI_group --name axia-seekapa-crm --query "functionKeys.default" -o tsv
```

### When Things Break
| Symptom | Check | Fix |
|---------|-------|-----|
| All channels return 500 | Azure AI Foundry project status | Check Foundry endpoint availability |
| OTP emails not arriving | ACS_CONNECTION_STRING env var | Verify Azure Communication Services config |
| CRM data returns empty | PandaTS MySQL connectivity | Check AXIA_CRM_HOST / SEEKAPA_CRM_HOST |
| Telegram bot not responding | Webhook registration | Re-register webhook URL with Telegram API |
| Escalation tickets not created | LiveAgent department IDs | Fill in actual IDs in `ticket_categories.py` |
| Content Safety blocking responses | Azure AI Content Safety logs | Retry (intermittent ~20%); adjust prompt if persistent |
| OTP codes lost after restart | In-memory storage limitation | Planned: migrate to Redis/Table Storage |
| Signed link validation fails | HMAC secret in Key Vault | Verify secret matches between generate and validate |

### Key Metrics to Watch
- **Content Safety refusal rate**: Should be < 25%. Higher indicates prompt issues.
- **OTP verification success rate**: Target > 90% (failed = wrong code or expired).
- **Escalation trigger rate**: Track which escalation categories fire most often.
- **CRM query latency**: PandaTS MySQL should respond in < 5s.

## Key Contacts and Dependencies

### Who Uses This System
- **Seekapa customers**: Forex trading platform users (seekapa.com)
- **Axia customers**: Forex trading platform users (axia brand)
- **Customer support managers**: Monitor escalation patterns

### External Dependencies
| Service | Purpose | Failure Impact |
|---------|---------|----------------|
| Azure AI Foundry | Hosts conversational agents (Seekapa + AxiaCS) | All channels return no response |
| PandaTS MySQL CRM (Axia) | Client profiles, trading data | Axia account queries fail |
| PandaTS MySQL CRM (Seekapa) | Client profiles, trading data | Seekapa account queries fail |
| SQL Server CRM (legacy) | Customer records for OTP verification | OTP verify returns no data |
| Azure Communication Services | OTP email delivery | Customers cannot authenticate |
| LiveAgent | Human agent escalation tickets | Escalation creates no ticket |
| Telegram Bot API | Telegram channel connectivity | Telegram channel goes silent |
| Azure Key Vault | Secrets for all integrations | Functions fail to start |

### Who to Ask About What
- **Agent prompt tuning**: See `agent-prompts/` directory, use multi-model debate
- **CRM schema**: `azure-function-crm/shared/crm_mysql_client.py` (documented 2026-01-12)
- **Test scenarios**: `tests/test_data/` and `tests/qa_scenarios_list.py`
- **Channel integration**: `azure-function-crm/shared/message_normalizer.py`
- **Deployment**: `DEPLOY-INSTRUCTIONS.md` and `DEPLOYMENT_STATUS.md`

## Quick Reference

### Important File Paths
| Path | Purpose |
|------|---------|
| `azure-function-crm/channel_router/__init__.py` | Central message routing (all channels) |
| `azure-function-crm/shared/message_normalizer.py` | Channel-specific message normalization |
| `azure-function-crm/shared/crm_mysql_client.py` | PandaTS CRM MySQL client (Axia + Seekapa) |
| `azure-function-crm/shared/otp_storage.py` | Thread-safe OTP storage (in-memory) |
| `azure-function-crm/shared/rate_limiter.py` | Rate limiting (10/email/hr, 100/IP/hr) |
| `azure-function-crm/shared/validators.py` | OWASP-compliant input validation |
| `azure-function-crm/shared/link_signing.py` | HMAC-SHA256 signed link generation/validation |
| `azure-function-crm/shared/liveagent_client.py` | LiveAgent REST API client for escalation |
| `azure-function-crm/shared/ticket_categories.py` | Escalation routing configuration |
| `azure-function-crm/send_otp/__init__.py` | OTP generation + email delivery |
| `azure-function-crm/verify_otp/__init__.py` | OTP verification + CRM data retrieval |
| `azure-function-crm/create_ticket/__init__.py` | LiveAgent ticket creation |
| `azure-function-crm/telegram_handler/__init__.py` | Telegram webhook handler |
| `agent-prompts/seekapa-system-prompt.md` | Seekapa agent system prompt (latest) |
| `agent-prompts/axia-cs-system-prompt.md` | Axia agent system prompt (latest) |
| `tests/agent_connector.py` | Hybrid test connector (KB + CRM) |
| `tests/deepeval_suite.py` | DeepEval agent evaluation metrics |
| `widget/` | Embeddable web chat widget (HTML/CSS/JS) |

### Key Environment Variables
| Variable | Source | Description |
|----------|--------|-------------|
| `AXIA_CRM_HOST` | Key Vault | PandaTS MySQL host for Axia (35.241.202.155) |
| `SEEKAPA_CRM_HOST` | Key Vault | PandaTS MySQL host for Seekapa (34.38.141.12) |
| `AXIA_CRM_PASSWORD` | Key Vault | MySQL password for Axia CRM |
| `SEEKAPA_CRM_PASSWORD` | Key Vault | MySQL password for Seekapa CRM |
| `CRM_SQL_SERVER` | Key Vault | Legacy SQL Server host |
| `CRM_SQL_DATABASE` | Key Vault | Legacy SQL Server database name |
| `CRM_SQL_USERNAME` | Key Vault | Legacy SQL Server username |
| `CRM_SQL_PASSWORD` | Key Vault | Legacy SQL Server password |
| `ACS_CONNECTION_STRING` | Key Vault | Azure Communication Services connection |
| `TELEGRAM_BOT_TOKEN` | Key Vault | Telegram Bot API token |
| `LIVEAGENT_API_URL` | Key Vault | LiveAgent REST API base URL |
| `LIVEAGENT_API_KEY` | Key Vault | LiveAgent API authentication key |
| `SIGNED_LINK_SECRET` | Key Vault | HMAC-SHA256 secret for link signing |

### API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/channel-router` | POST | Function Key | Central message routing (all channels) |
| `/api/send-otp` | POST | Function Key | Generate and send 6-digit OTP |
| `/api/verify-otp` | POST | Function Key | Validate OTP and return CRM data |
| `/api/generate-signed-link` | POST | Function Key | HMAC-signed deep links for channels |
| `/api/validate-token` | POST | Function Key | Validate signed token or email/login |
| `/api/create-ticket` | POST | Function Key | Create LiveAgent escalation ticket |
| `/api/get-client-info` | POST | Function Key | Basic client profile from CRM |
| `/api/get-full-client-context` | POST | Function Key | Complete client context |
| `/api/get-kyc-status` | POST | Function Key | KYC/compliance verification status |
| `/api/get-open-positions` | POST | Function Key | Current trading positions |
| `/api/get-trade-history` | POST | Function Key | Historical trades |
| `/api/get-trading-summary` | POST | Function Key | Aggregated trading statistics |
| `/api/get-transaction-history` | POST | Function Key | Deposit/withdrawal history |
| `/api/telegram-webhook` | POST | Telegram | Telegram Bot webhook |

### Production URLs
| Service | URL |
|---------|-----|
| Function App | `https://axia-seekapa-crm.azurewebsites.net` |
| AI Foundry (Seekapa) | `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai/applications/seekapa/` |
| AI Foundry (Axia) | `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai/applications/AxiaCS/` |
| Azure DevOps | `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents` |
