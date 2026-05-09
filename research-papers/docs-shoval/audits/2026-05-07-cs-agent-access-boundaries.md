# cs-agent — Access boundaries audit (IT admin / Networking / CRM)

Date: 2026-05-07
Auditor: cs-agent automated review
Scope: code at `/tmp/pr233-fix` (`feat/v110-account-verification`) and live Azure config for the deployed Function App.

Important live-config correction: the project notes describe the Function App as `axia-seekapa-crm.azurewebsites.net` but no Azure resource by that name exists in `AZAI_group`. The actually-running Function App backing this code is **`func-cs-agents-dev`** (host `func-cs-agents-dev.azurewebsites.net`). Every "live config" finding below is for that resource. If a separate `axia-seekapa-crm` exists in another subscription/tenant the same code may be deployed to a second site that wasn't visible to my CLI session — flag this for the IT/security team.

## 1. Executive summary

| # | Severity | Finding | One-line impact |
|---|----------|---------|-----------------|
| 1 | **P0** | Webhook is anonymous **and** HMAC signature secret is unset, so any internet caller can post arbitrary messages and trigger replies | Foundry abuse, customer-facing message injection, billing exfil, escalation-loop weaponisation |
| 2 | **P0** | Foundry, Chatwoot, and App Insights secrets are stored as **plaintext app settings**, not Key Vault references | Secret exposure to anyone with `Microsoft.Web/sites/config/list/action` (Reader+ on the site) |
| 3 | **P1** | Function App has **no VNET integration, no IP allowlist, public network access enabled, default-Allow on inbound rules**; Key Vault is also `publicNetworkAccess: Enabled` with 42 access policies | No network-layer defence; KV `Get` is reachable from anywhere with a valid token |
| 4 | **P1** | CRM bearer-token auth (`CRM_API_KEY`) for the v110 verifier is **missing entirely from app settings** while the code expects a KV reference | If the v110 flag is ever flipped on, the verifier will throw `RuntimeError` mid-conversation and degrade — no failure mode is silent, but the spec assumes the secret exists |
| 5 | **P2** | Two MySQL CRMs are reached by **public IP over the open internet** (35.241.202.155, 34.38.141.12 — Google Cloud) using a shared Azure egress IP pool, with no documented IP pinning | Hard to whitelist, hard to monitor, exposes plaintext credential surface to every Azure tenant on the shared NAT |

CRM data leak risk to other customers: **none observed in code**. Each conversation only ever loads its OWN customer's record, the v110 verifier requires email-then-deposit two-factor before exposing balances, and the only PII sent to Foundry is the Chatwoot profile (name + email) prefixed onto the customer's own message. See §4 for the trace.

---

## 2. IT admin perspective (privileges, identity)

### Findings

**ITA-1 (P0): Plaintext secrets in app settings.** The Foundry API key, Chatwoot API key, and App Insights key are raw values, not KV references. Anyone with `Microsoft.Web/sites/config/list/action` (granted by `Website Contributor`+) reads them. Evidence: `az functionapp config appsettings list -g AZAI_group -n func-cs-agents-dev --query "[?contains(name,'KEY')]"` returned `AZURE_AI_FOUNDRY_KEY` (84 chars plaintext), `CHATWOOT_API_KEY` (24 chars), `APPINSIGHTS_INSTRUMENTATIONKEY` (36 chars). The CRM passwords (`AXIA_CRM_PASSWORD`, `SEEKAPA_CRM_PASSWORD`, `LIVEAGENT_API_KEY`) are correctly KV-referenced. Code reads the plaintext ones directly at `channel_router/__init__.py:104` and `shared/chatwoot_client.py:46`.

**ITA-2 (P0): No HMAC enforcement on the webhook.** `chatwoot_handler/_gates.py:102-113` skips signature validation when `CHATWOOT_WEBHOOK_SECRET` is empty. Live config: variable unset (`az functionapp config appsettings list … --query "[?name=='CHATWOOT_WEBHOOK_SECRET']"` returned `[]`). With `chatwoot_handler/function.json:5` set to `"authLevel": "anonymous"`, the endpoint is open. An anonymous unsigned `POST /api/chatwoot-webhook` with a junk body returned **HTTP 200**. Any caller can drive Foundry calls, cause LiveAgent escalations, and inject customer-facing messages if they enumerate `conversation_id` for inbox 4.

**ITA-3 (P1): System-assigned MSI has zero RBAC role assignments.** `principalId: af8e4a2f-9e05-43d2-8d55-5001b1389570` (`az functionapp identity show -g AZAI_group -n func-cs-agents-dev`). `az role assignment list --assignee af8e…` returned 0 rows. Effective privilege is only via KV access policy. The MSI's Foundry path (`channel_router/__init__.py:111-131`, `DefaultAzureCredential` for `https://ai.azure.com/.default`) is dead code today — only used when `AZURE_AI_FOUNDRY_KEY` is empty, which it isn't.

**ITA-4 (P2): KV access policies sprawling.** `az keyvault show --name kv-seekapa-apps --query properties.{n:length(accessPolicies)}` returned **42**. Many likely stale (developer principals, retired apps). Convert KV to RBAC mode (`enableRbacAuthorization: false` today) and grant only `Key Vault Secrets User` to the MSI.

**ITA-5 (P2): `AzureWebJobsStorage` uses storage account key, not MSI.** Only `AzureWebJobsStorage` is set, not the `AzureWebJobsStorage__accountName` MSI form. Function content share is reached via plaintext storage key — the highest-blast-radius secret in the App Service model.

**ITA-6 (low): Function key generated on `chatwoot_handler` despite anonymous binding** — `az functionapp function keys list … --function-name chatwoot_handler` returned a `default` key. Cosmetic, but creates ambiguity about the auth source of truth.

### Recommendations (IT)

1. **Set `CHATWOOT_WEBHOOK_SECRET`** as a KV-referenced setting and provision the matching value in Chatwoot's webhook config. Same value in both. Rotate yearly.
2. **Move `AZURE_AI_FOUNDRY_KEY`, `CHATWOOT_API_KEY`, `APPINSIGHTS_INSTRUMENTATIONKEY` to KV references** — same syntax as the CRM passwords already use.
3. **Convert KV `kv-seekapa-apps` to RBAC mode** and grant the function MSI `Key Vault Secrets User` only. Decommission stale access policies.
4. **Switch `AzureWebJobsStorage` to identity-based** and grant the MSI `Storage Blob Data Owner` on the deployment storage account.
5. **Provision `CRM_API_KEY` in KV** before flipping `SEEKAPA_VERIFY_ENABLED=true` (see ITA-4, NET-3).

---

## 3. Networking perspective

### Findings

**NET-1 (P1): No VNET integration.** `virtualNetworkSubnetId: null`, `vnetRouteAllEnabled: false`. Outbound traffic exits via the shared Azure App Service NAT pool: 31 IPs in `20.240.x.x` plus `51.12.31.3` (`possibleOutboundIpAddresses`). The upstream MySQL hosts must whitelist that whole pool, which is shared with other Azure tenants on the same scale unit.

**NET-2 (P1): Public ingress, default-Allow, no IP allowlist.** `siteConfig.ipSecurityRestrictions` has a single `Allow Any priority=2147483647` rule. `publicNetworkAccess: "Enabled"`, `clientCertEnabled: false`. Anonymous probe returned HTTP 200 (see ITA-2). Transport floor is fine (`httpsOnly: true`, `minTlsVersion: 1.2`, `ftpsState: FtpsOnly`); the gap is auth-level.

**NET-3 (P1): `CRM_API_KEY` not set, but `seekapa_verifier.py:254-261` requires it.** `get_crm_bearer_from_env()` raises `RuntimeError` if missing. The env var is absent (`az functionapp config appsettings list … --query "[?name=='CRM_API_KEY']"` returned `[]`). Today harmless because `SEEKAPA_VERIFY_ENABLED` is also absent (default-off, `seekapa_verifier.py:53`), but flipping v110 on without provisioning the secret will degrade every account-balance probe at `chatwoot_handler/__init__.py:428-430`.

**NET-4 (P2): CRM endpoints reached over public internet.** `shared/crm_mysql_client.py:33,40` configure MySQL hosts `35.241.202.155` and `34.38.141.12` (Google Cloud public addresses). `pymysql.connect()` at lines 98-108 passes no `ssl=` parameter, so unless the server enforces TLS the password and query traffic cross the public internet in plaintext. Verify with `SHOW STATUS LIKE 'Ssl_cipher'` from a Function probe.

**NET-5 (P2): App Insights dependency tracking captures all outbound URLs.** `host.json:7-15` sets `enableDependencyTracking: true`. URLs to Foundry, Chatwoot, and CRM are retained. `redact_email()` in `seekapa_verifier.py:76-88` covers log lines but not dependency telemetry — anything that leaks into a query string is retained for the App Insights retention window.

**NET-6 (P2): KV `kv-seekapa-apps` publicly reachable.** `publicNetworkAccess: Enabled`, `networkAcls: null`. The 42 access policies are the only gate. After converting to RBAC mode (ITA-4), enable `networkAcls.defaultAction: Deny` with a private endpoint or the function subnet on bypass.

**NET-7 (low): No CORS lockdown** — `siteConfig.cors: null`. The webhook is POST-only so not currently relevant, but channel-router (`function`-auth) and the disabled `create-ticket` would matter if ever fronted by a browser SPA.

### Recommendations (Net)

1. **Add VNET integration + private endpoint to KV** at minimum. App Service v3 / Premium plans support outbound subnet integration with `vnetRouteAllEnabled: true`, then KV can flip to default-Deny.
2. **Pin egress** with NAT Gateway on the integrated subnet so the CRM whitelist becomes a single static IP, not 31 shared ones.
3. **Lock down inbound** to the Chatwoot egress IP(s) once known (or front the webhook with App Gateway / WAF). The `default-Allow` rule should be replaced with an explicit allowlist + final default-Deny.
4. **Set `CRM_API_KEY` before v110 launch**, KV-referenced.
5. **Audit App Insights dependency telemetry** for any captured URL fragments containing PII or tokens; configure telemetry processors / `excludedTypes` for sensitive paths.
6. **Migrate MySQL traffic** to either TLS-enforced MySQL (`ssl_ca`, `ssl_disabled=False` in `pymysql.connect`) or the v110 HTTPS endpoint design for both reads.

---

## 4. CRM access boundaries

### Findings

**CRM-1 (verified safe): Read-only enforcement.** `shared/crm_mysql_client.py` contains zero `INSERT`/`UPDATE`/`DELETE`/`DROP`/`TRUNCATE` statements (grep verified). All call sites use parameterized `%s` (lines 218, 310, 366, 422, 478, 541, 575, 628, 677, 722, 797). No f-string or `%`-format SQL. The CLAUDE.md claim holds at the code level.

**CRM-2 (P2): MySQL `ai_support` privileges not enforced from code.** Both brands use `ai_support` as the connection user. Defense-in-depth requires `SHOW GRANTS FOR 'ai_support'@'%'` to return only `SELECT` on `panda_db.*` — verify with the DBA.

**CRM-3 (verified safe): v110 verifier is HTTP POST only, output field-disciplined.** `seekapa_verifier.py:194-219` POST only, never PUT/PATCH/DELETE. Response parsed for a tight set: `customer.compliance_status` (305), `customer.language` (322), `customer.account_status` (313, 324), `deposits.items[-1].amount_usd` / `deposits.ftd_amount_usd` (230-238), and `trading_accounts[0].balance/equity/pnl` (246-251). No name/address/ID fields extracted. `_format_verified_reply` (`_verification_flow.py:167-173`) renders only `bal`, `eq`, `pnl`. Email is redacted in every log site (`seekapa_verifier.py:283, 287, 294, 301, 308, 347, 354, 360, 363`).

**CRM-4 (verified safe): Two-factor before any account-data egress.** `seekapa_verifier.py:125-127` (`can_expose_account_data`) returns true only when `outcome == VERIFIED`, which requires (a) email validates → (b) CRM HTTP 200 → (c) `compliance_status` in `{VERIFIED, ADVANCED VERIFIED, FULLY VERIFIED}` → (d) deposit within USD 1.0 (`:331-356`). Max 2 attempts (line 358), 5-min idle TTL (line 58). `_verification_flow.py:182-244` only calls `_format_verified_reply` at line 227 after `outcome == VERIFIED`.

**CRM-5 (verified safe): Cross-customer isolation.** Every CRM lookup is keyed on the customer's own input (their declared email). The handler does not pre-fetch CRM by Chatwoot identity, does not maintain a global cache by `conversation_id`, and does not pass any CRM record into the Foundry prompt. The Foundry prompt body (`chatwoot_handler/__init__.py:445-446`) is `[Hour: HH:00 UTC+3. CW profile: name: …, email: …] + customer message` — the CW profile is the sender's own. The verification cache (`_verification_flow.py:111-131`) is keyed on `conversation_id` under `_cache_lock` with hard cap 1024 + oldest-evict. No cross-conversation contamination path observed.

**CRM-6 (P2): CW profile (name + email) sent to Foundry per turn.** `_gates.py:52-73` prepends `[Hour: HH:00 UTC+3. CW profile: name: NAME, email: EMAIL]` to the message. Foundry is in-tenant (`brn-azai.services.ai.azure.com`) but data still leaves the function and lands in agent retention. Confirm DLP retention policy.

**CRM-7 (verified safe): No private-note leakage.** Only `create_ticket/__init__.py:162` calls `send_message(..., private=True)`, and that binding is `disabled: true` (`create_ticket/function.json:3`). The live `chatwoot_handler/__init__.py` calls `send_message(conversation_id, content)` without `private=True` at lines 362, 403, 411, 424, 469, 499.

**CRM-8 (P1): Error-path log surface.** `chatwoot_handler/__init__.py:286` logs body length only (safe); `:308-316` logs metadata (safe); `:454` truncates user_id to 20 chars (safe). But `channel_router/__init__.py:286-294` dumps up to 300 chars of the agent's HTTP error response (`err_body = e.response.text[:300]`). If Foundry echoes the prompt back in an error, the PII-prefixed message lands in App Insights. Cap or redact before logging.

**CRM-9 (P2): No rate limiting on the webhook.** `shared/rate_limiter.py` exists but is not imported by `chatwoot_handler/__init__.py`, `seekapa_verifier.py`, or `channel_router/__init__.py` (only `shared/validators` and `shared/chatwoot_client` are imported). Combined with ITA-2, an attacker can saturate Foundry tokens and DOS the CRM read replica at line speed.

**CRM-10 (P2): Error responses leak Python class names.** `chatwoot_handler/__init__.py:477` returns `f"{type(agent_err).__name__}: {agent_err}"`; `:528` adds `"X-Error-Type": type(e).__name__`. Mild fingerprinting; unnecessary on an internet-facing endpoint.

### Recommendations (CRM)

1. **DBA verifies `ai_support` MySQL user has only SELECT** on `panda_db.*` (CRM-2).
2. **Cap App Insights dependency telemetry retention** for the agent dependency type, or strip the request body field; do not log `e.response.text[:300]` raw (CRM-8).
3. **Wire `shared.rate_limiter`** into the webhook handler, keyed on `sender.id` + `inbox.id` from the unsigned payload (best you can do until ITA-2 lands), then re-key on signed-source once HMAC is enforced (CRM-9).
4. **Audit Foundry agent retention policy** for the seekapa agent — confirm CW-profile (name+email) retention is acceptable per DLP (CRM-6).

---

## 5. Verified safe (in scope, no finding)

- **CRM client is read-only** — verified at code level (CRM-1).
- **v110 verifier is HTTP POST only with field-discipline output** (CRM-3).
- **Two-factor enforced before any account-data egress** (CRM-4).
- **No cross-customer record contamination** in the verification-flow cache or the handler (CRM-5).
- **Email is redacted at every emitted log line** in `seekapa_verifier.py` (CRM-3).
- **Private notes are not posted on the customer-facing channel** (CRM-7).
- **HTTPS-only, TLS 1.2+, FTPS-only on the Function App** (transport floor is fine — NET-2 noted but transport itself is good).
- **Identity-collection sanitiser** strips redundant first-turn name/email asks when CW profile already has them (`chatwoot_handler/__init__.py:490-496`, `_sanitize.py:86-118`).
- **Banned-verb sanitiser + invented-money guard** prevent the bot from inventing minimum deposits (`_sanitize.py:74-78`).
- **Disconnect keyword + customer-escalation phrases** route to canonical replies, not LLM (`__init__.py:380-414`).
- **System-assigned MSI has zero RBAC role assignments** outside KV access policy — least-privilege from RBAC perspective (ITA-3).
- **CRM passwords ARE KV-referenced** (`AXIA_CRM_PASSWORD`, `SEEKAPA_CRM_PASSWORD`, `LIVEAGENT_API_KEY`).

---

## 6. Open questions for IT/security team

1. **Does a separate Function App `axia-seekapa-crm` exist** in another subscription/tenant? CLAUDE.md cites that hostname but it isn't in the `U-BTech - CSP (Z-Online)` subscription accessible to my session. If yes, all findings need to be re-run against it.
2. **What is the Foundry agent retention policy** for prompt + completion data? CRM-6 sends customer name + email per turn; confirm DLP signoff.
3. **Does the PandaTS MySQL `ai_support` user actually have SELECT-only privileges** at the database layer? Code is read-only, but defense-in-depth requires the DB-side check.
4. **Does the MySQL connection to `35.241.202.155` and `34.38.141.12` enforce TLS**, and if so what cipher? `pymysql.connect()` here passes no `ssl=` param.
5. **Who owns the 42 KV access-policy entries**, and which can be retired? Conversion to RBAC mode is the cleanest path, but requires a migration plan.
6. **Is there a documented IP-pinning expectation** between Azure and the upstream CRM? If yes, the shared `20.240.x` pool today doesn't satisfy it.
7. **Where is the `CRM_API_KEY` secret stored** today (in KV but not yet referenced from app settings? in the spec but not provisioned?) — required before v110 launch.
8. **Is the Chatwoot webhook configured to send `X-Chatwoot-Signature`** today? If yes, populating `CHATWOOT_WEBHOOK_SECRET` immediately closes ITA-2 with no upstream change.
