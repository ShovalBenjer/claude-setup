# MCP Azure App Service Security Audit

## Executive Summary

1. **Critical: Public OAuth can still mint broad MCP bearers when Entra is not configured**: the deployment template explicitly falls back to `MCP_REQUIRE_ENTRA=false`, while the OAuth server supports dynamic public-client registration and all tools sit behind one coarse bearer gate.
2. **Critical: The MCP boundary exposes high-risk customer PII and regulated financial context**: CRM comments, Chatwoot identities/private notes, raw transcripts, and OneSignal payloads are returned with minimal policy enforcement at the tool boundary.
3. **High: Azure secret and deployment posture is not yet board-grade**: Key Vault MSI role assignment is commented out, registry credentials are injected as app settings, and the pipeline deploys directly to production without slot swap or image vulnerability gates.
4. Existing controls worth preserving: HTTPS-only App Service config, `minTlsVersion: 1.2`, HSTS/CSP/no-sniff headers, FastMCP DNS-rebinding protection, non-root container user, Key Vault client via `DefaultAzureCredential`, upstream error envelopes, token-redaction tests, and per-host outbound token buckets.
5. Strategic recommendation: position this MCP as the “secure BI edge” by making it more governed than internal BI: Entra-only federation, per-tool scopes, redacted data products, immutable audit logs, private networking, and release gates that BI spreadsheets cannot provide.

## Findings Table

| ID | Severity | Category | Affected Evidence | Exploit Scenario | Recommended Fix | Effort |
|---|---|---|---|---|---|---|
| F-01 | Critical | Identity | [infra/mcp.bicep:56](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:56), [infra/mcp.bicep:83](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:83), [infra/mcp.bicep:121](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:121), [app_mcp/server.py:210](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:210), [app_mcp/oauth.py:321](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:321) | The Bicep template states that empty Entra params make the app boot with open dev mode, then sets `MCP_REQUIRE_ENTRA` from that derived value. In that mode, any internet client that reaches `/oauth/register` can register a public client, complete PKCE locally, and receive a bearer for the MCP transport. | Remove the dev-mode fallback from production infrastructure. Make Entra tenant/client settings required for all non-local deployments, fail deployment when empty, and keep `MCP_REQUIRE_ENTRA=true` as an invariant. Keep local dev behavior only in test/local startup scripts. | S |
| F-02 | Critical | Data | [app_mcp/tools/crm.py:90](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/crm.py:90), [app_mcp/tools/crm.py:102](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/crm.py:102), [app_mcp/tools/crm.py:127](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/crm.py:127), [app_mcp/server.py:366](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:366) | `crm_get_customer` returns customer email, language, compliance status, financial deposit fields, trading balance/equity/PNL, and every decoded comment. Because comments are URL-decoded and returned without content filtering, production notes containing PINs, signed links, health disclosures, or KYC narrative can move from CRM into a general MCP client transcript. | Add a CRM response policy layer before MCP output: redact secrets, signed URLs, medical terms, government IDs, card/payment fragments, and high-risk free text by default. Split tools into `crm_get_customer_summary` and `crm_get_customer_sensitive_comments`, with the latter requiring elevated scope and audited justification. | M |
| F-03 | Critical | Data | [app_mcp/tools/chatwoot.py:98](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/chatwoot.py:98), [app_mcp/tools/chatwoot.py:109](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/chatwoot.py:109), [app_mcp/tools/chatwoot.py:123](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/chatwoot.py:123), [app_mcp/tools/chatwoot.py:209](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/chatwoot.py:209), [app_mcp/tests/test_chatwoot.py:267](/home/shovalbe/projects/campaign-analysis/app_mcp/tests/test_chatwoot.py:267) | Chatwoot conversation output lifts `name`, WhatsApp JID, CRM ACC, email, branch, country, compliance status, and client status into a single contact block. Message retrieval explicitly preserves private notes and full content; a broad MCP bearer can enumerate inbox conversations and retrieve internal agent notes. | Default Chatwoot tools to privacy-minimized output: hash or mask JID/email, remove private notes unless `include_private=true` is authorized by an elevated scope, and add server-side pagination/time bounds. Add tests proving private note content is excluded in default mode. | M |
| F-04 | High | Identity | [app_mcp/server.py:621](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:621), [app_mcp/oauth.py:220](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:220), [app_mcp/oauth.py:392](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:392), [app_mcp/oauth.py:421](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:421) | The bearer gate validates token signature/audience, but it does not enforce per-tool scopes, role claims, customer ownership, broker namespace, or named-recipient restrictions. A token with `mcp.tools` can reach CRM, transcripts, Chatwoot, OneSignal, Windsor, and analysis tools equally. | Introduce an authorization matrix at the MCP tool boundary: `crm.read.summary`, `crm.read.comments`, `chatwoot.read.public`, `chatwoot.read.private`, `calls.read`, `calls.transcribe`, `push.read`, `marketing.read`. Enforce Entra group/app-role claims and customer/broker constraints before calling each adapter. | M |
| F-05 | High | Identity | [app_mcp/oauth.py:37](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:37), [app_mcp/oauth.py:231](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:231), [infra/mcp.bicep:122](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:122), [app_mcp/server.py:627](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:627) | OAuth issuer and protected-resource metadata are derived from `MCP_OAUTH_ISSUER`, with a legacy default of `https://mcp-seekapa-tools.azurewebsites.net`. The system under review is served from a different host; issuer/resource/audience mismatch causes connector failures at best and confused-token acceptance at worst if multiple hosts remain alive. | Make the serving host canonical. Set `MCP_OAUTH_ISSUER` to the live host, retire legacy hostname traffic with redirect or deny, and remove legacy audience acceptance after token TTL. Add startup assertion that issuer host equals the configured App Service hostname for production. | S |
| F-06 | High | App | [app_mcp/tools/onesignal.py:1](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/onesignal.py:1), [app_mcp/tools/onesignal.py:70](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/onesignal.py:70), [app_mcp/tools/onesignal.py:88](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/onesignal.py:88), [app_mcp/server.py:445](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:445) | The OneSignal adapter says it has “No _shape() yet” and returns `resp.json()` directly for notification list and template retrieval. That passes vendor payload structure, delivery metadata, null-heavy fields, tags, segmentation, and identifiers through to any bearer-authorized MCP client. | Add strict OneSignal DTO shaping with an allowlist of fields needed by the pilot. Normalize external IDs to CRM ACC namespace or clearly mark unmapped identifiers; cap `limit`, block arbitrary raw template dumps by default, and add snapshot tests for “no unexpected fields.” | S |
| F-07 | High | Data | [app_mcp/tools/call_analyzer.py:333](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/call_analyzer.py:333), [app_mcp/tools/call_analyzer.py:350](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/call_analyzer.py:350), [app_mcp/tools/call_analyzer_orchestrator.py:44](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/call_analyzer_orchestrator.py:44), [app_mcp/tools/call_analyzer_orchestrator.py:121](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/call_analyzer_orchestrator.py:121) | Raw transcript endpoints return full ElevenLabs payloads, including text and word timeline. The orchestrator also inlines `transcript_text` and `transcript_words` into call bundles, making call speech available for downstream model prompts and logs unless every consumer is careful. | Keep raw transcript access only for scoring service paths, not general MCP users. Provide default redacted transcript segments, add content-classification flags, enforce short retention, and log every raw transcript request with Entra subject, ACC, call ID, and purpose. | M |
| F-08 | High | Azure | [infra/mcp.bicep:188](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:188), [infra/mcp.bicep:191](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:191), [app_mcp/config.py:95](/home/shovalbe/projects/campaign-analysis/app_mcp/config.py:95), [app_mcp/config.py:102](/home/shovalbe/projects/campaign-analysis/app_mcp/config.py:102) | The app code is built around Key Vault via `DefaultAzureCredential`, but the Bicep comments say the Key Vault role assignment was removed and open dev-mode settings are inlined so MSI to KV is not required for boot. In production, this creates drift risk: the app may run with inline secrets or fail open around missing secret governance. | Re-enable MSI-based Key Vault access as a deployment requirement. Grant only `Key Vault Secrets User` to the App Service managed identity, remove env-secret fallback from production, and add a `/readyz` gate that fails if required secrets are not fetched from KV. | M |
| F-09 | High | Azure | [infra/mcp.bicep:72](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:72), [infra/mcp.bicep:75](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:75), [infra/mcp.bicep:134](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:134), [azure-pipelines-mcp.yml:61](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:61), [azure-pipelines-mcp.yml:75](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:75) | The template supports ACR admin username/password and writes registry credentials into App Service settings. The pipeline also logs into GHCR with a PAT and deploys registry credentials directly through `az webapp config container set`, creating a static credential blast radius outside managed identity. | Use managed identity for ACR pull, disable ACR admin user, and store any unavoidable registry credential as a Key Vault reference until eliminated. Prefer Azure Container Registry with `AcrPull` assigned to the Web App identity; remove GHCR PAT dependency for production. | M |
| F-10 | Medium | Network | [infra/mcp.bicep:32](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:32), [infra/mcp.bicep:37](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:37), [infra/mcp.bicep:116](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:116), [app_mcp/_http_client.py:95](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:95) | Ingress restrictions allow broad Azure service tags and Azure Active Directory rather than a private endpoint or tightly scoped client egress. Outbound HTTP clients can reach any hard-coded public upstream host over internet TLS; there is no VNet integration, NAT egress pinning, Azure Firewall FQDN rule, or Private Link evidence in the repo config. | Move the Web App behind private endpoint or Access Restrictions scoped to verified client egress only. Add regional VNet integration, route outbound through Azure Firewall/NAT, and allow only required FQDNs: analyzer, CRM, Chatwoot, OneSignal, Windsor, Foundry, Entra, Key Vault. | L |
| F-11 | Medium | App | [app_mcp/_http_client.py:32](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:32), [app_mcp/_http_client.py:38](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:38), [app_mcp/_http_client.py:75](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:75), [app_mcp/server.py:621](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:621) | There is a per-host outbound limiter for upstream calls, but no inbound per-subject, per-IP, per-client, or per-tool quota at the FastAPI/MCP boundary. A valid bearer can repeatedly invoke transcript, CRM cohort, Chatwoot pagination, or Windsor queries and consume upstream quota or leak large volumes. | Add inbound throttling keyed by Entra `oid`, client ID, IP, and tool. Set lower quotas for raw transcript and customer-data tools, reject excessive page traversal, and emit rate-limit events to Log Analytics. | M |
| F-12 | Medium | App | [app_mcp/Dockerfile:24](/home/shovalbe/projects/campaign-analysis/app_mcp/Dockerfile:24), [app_mcp/Dockerfile:26](/home/shovalbe/projects/campaign-analysis/app_mcp/Dockerfile:26), [azure-pipelines-mcp.yml:44](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:44), [pyproject.toml:27](/home/shovalbe/projects/campaign-analysis/pyproject.toml:27) | Runtime dependencies in the Dockerfile are installed with broad lower bounds and no lockfile enforcement; the Dockerfile even allows `mcp>=1.0` while `pyproject.toml` pins `<2.0`. CI runs lint, mypy, and tests, but does not run Bandit despite it being a dev dependency, nor pip-audit/SBOM/container CVE scanning. | Build the container from the locked dependency graph, pin Docker runtime dependencies consistently with `pyproject.toml`, and add Bandit, pip-audit, Trivy/Defender image scan, and SBOM generation as pipeline gates before deploy. | S |
| F-13 | Medium | Azure | [azure-pipelines-mcp.yml:11](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:11), [azure-pipelines-mcp.yml:54](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:54), [azure-pipelines-mcp.yml:67](/home/shovalbe/projects/campaign-analysis/azure-pipelines-mcp.yml:67), [infra/mcp.bicep:142](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:142) | The infrastructure defines a staging slot, but the pipeline comment says slot-swap rollback is deferred and the deploy job pushes directly to the production Web App on `master`. A bad auth, networking, or data-redaction release can immediately affect the live pilot endpoint. | Restore staging deployment, run `/readyz`, OAuth metadata, bearer rejection, Entra login, and tool smoke tests against staging, then swap. Add automatic rollback if post-swap health or security probes fail. | M |
| F-14 | Medium | Compliance | [app_mcp/_logging.py:103](/home/shovalbe/projects/campaign-analysis/app_mcp/_logging.py:103), [app_mcp/server.py:647](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:647), [app_mcp/tools/crm.py:156](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/crm.py:156), [app_mcp/tools/chatwoot.py:198](/home/shovalbe/projects/campaign-analysis/app_mcp/tools/chatwoot.py:198) | Structured request IDs exist, but tool-level logs mostly capture latency and counts, not immutable business audit fields: Entra subject, client app, tool name, ACC/customer ID under a protected hash, data classification, purpose, and decision outcome. That weakens incident investigation, GDPR accountability, EU AI Act logging, SR 11-7 model governance, and CySEC AML review. | Add an audit event model emitted before and after every sensitive tool invocation. Store in Log Analytics with Diagnostic Settings and retention policy; include subject/client/tool/scope/purpose/result counts and hash identifiers with a tenant salt. | M |
| F-15 | Low | Network | [app_mcp/server.py:36](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:36), [app_mcp/server.py:119](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:119), [infra/mcp.bicep:102](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:102), [infra/mcp.bicep:105](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:105) | Good transport controls are present: HSTS, CSP, no-sniff, DNS-rebinding protection, HTTPS-only, TLS 1.2 minimum, FTPS disabled, and HTTP/2 enabled. Remaining gap is that TLS is platform-managed with no client certificate binding, mutual TLS, or explicit certificate pinning to upstreams. | Leave current headers and FastMCP transport protection in place. For board-grade internal access, evaluate App Service client certificates or gateway-level mTLS for MCP clients; do not add brittle application-level public CA pinning unless the upstreams support operational rotation. | M |

## Threat Model Diagram

~~~
Trust Boundary: Internet / End User
  Claude Desktop / Web Connector / Named-recipient URL
        |
        | HTTPS Bearer / OAuth 2.1 + PKCE
        v
Trust Boundary: Azure App Service
  FastAPI + FastMCP
  - /.well-known/oauth-authorization-server
  - /.well-known/oauth-protected-resource
  - /oauth/register, /oauth/authorize, /oauth/token
  - /mcp, /sse, /messages/*
        |
        | Bearer gate: signature + audience only
        v
  MCP Tool Surface
  - CRM tools
  - Call Analyzer tools
  - Chatwoot tools
  - OneSignal tools
  - Windsor tools
  - Layer-2 deterministic analysis
        |
        | DefaultAzureCredential
        v
Trust Boundary: Azure Key Vault
  KV shoval
  - CRM-API-KEY
  - CALL-ANALYSER-X-API
  - ONE-SIGNAL-* keys
  - WINDSOR-API-KEY
  - CHATWOOT-API-KEY

Trust Boundary: Upstream APIs
  analyzer.corp-domain.com
  az-corp.corp-domain.com
  corpim.corp-domain.com
  api.onesignal.com
  connectors.windsor.ai
  brn-azai.services.ai.azure.com
        |
        v
Trust Boundary: Customer / Regulated Data
  CRM comments, KYC, deposits, PNL, compliance status
  WhatsApp identity, JID, private notes, messages
  Call transcripts and word timelines
  Push notification metadata
  Marketing platform account data
~~~

## Remediation Roadmap

### Pri-1: This Week

1. **Force Entra-only production auth**: remediate F-01. Remove production dev-mode fallback, require Entra parameters at deployment, and verify `/startupz` reports `entra_enabled=true`.
2. **Kill broad bearer access**: remediate F-04. Add a first-pass per-tool authorization matrix even if all sensitive tools initially require the same elevated group.
3. **Redact CRM comments by default**: remediate F-02. Ship a server-side redaction layer and split raw comment access behind elevated scope.
4. **Minimize Chatwoot output**: remediate F-03. Mask email/JID and exclude private notes by default.
5. **Fix issuer/host canonicalization**: remediate F-05. Align `MCP_OAUTH_ISSUER`, protected-resource metadata, and live serving host; retire legacy host.
6. **Disable raw OneSignal pass-through**: remediate F-06. Return only an allowlisted notification summary until a governed data contract exists.
7. **Require MSI to Key Vault**: remediate F-08. Re-enable KV role assignment or perform a documented Owner action; fail readiness if secrets come from inline production env.

### Pri-2: This Month

1. **Raw transcript governance**: remediate F-07. Gate raw transcripts behind elevated scope and audit every access.
2. **Replace registry static credentials**: remediate F-09. Move production image pull to managed identity and ACR RBAC.
3. **Inbound quotas and abuse throttles**: remediate F-11. Add per-subject/tool quotas and cap pagination/fan-out.
4. **Pipeline security gates**: remediate F-12. Add locked dependency install, Bandit, pip-audit, SBOM, and container CVE scan.
5. **Staging slot and swap release flow**: remediate F-13. Deploy to staging, run security smoke tests, then swap.
6. **Immutable audit trail**: remediate F-14. Emit tool audit events to Log Analytics with retention and alert rules.

### Pri-3: This Quarter

1. **Private networking and egress control**: remediate F-10. Add private endpoint or narrow ingress, VNet integration, NAT/Azure Firewall, and FQDN allowlisting.
2. **mTLS or gateway-auth hardening**: remediate F-15. Evaluate client certificates at App Service or Azure Front Door/Application Gateway.
3. **Data-product contracts**: extend F-02/F-03/F-06/F-07 into governed MCP schemas with classification labels and retention rules.
4. **Board-grade BI replacement posture**: combine Entra groups, audit logs, redaction, and deterministic evidence trails into a security narrative that internal BI cannot match with exported spreadsheets.

## Compliance Mapping

| Finding | Priority | EU AI Act Art. 12 | GDPR Art. 32 | SR 11-7 | CySEC AML | MiFID II | Israeli Privacy Protection Law |
|---|---|---:|---:|---:|---:|---:|---:|
| F-01 | Pri-1 | Yes | Yes | Yes | Yes | Yes | Yes |
| F-02 | Pri-1 | Yes | Yes | Yes | Yes | Yes | Yes |
| F-03 | Pri-1 | Yes | Yes | Yes | Yes | Yes | Yes |
| F-04 | Pri-1 | Yes | Yes | Yes | Yes | Yes | Yes |
| F-05 | Pri-1 | Yes | Yes | No | No | Yes | Yes |
| F-06 | Pri-1 | Yes | Yes | Yes | No | Yes | Yes |
| F-08 | Pri-1 | No | Yes | Yes | Yes | Yes | Yes |
| F-07 | Pri-2 | Yes | Yes | Yes | Yes | Yes | Yes |
| F-09 | Pri-2 | No | Yes | No | Yes | Yes | Yes |
| F-11 | Pri-2 | No | Yes | Yes | Yes | Yes | Yes |
| F-12 | Pri-2 | No | Yes | Yes | No | Yes | No |
| F-13 | Pri-2 | No | Yes | Yes | Yes | Yes | No |
| F-14 | Pri-2 | Yes | Yes | Yes | Yes | Yes | Yes |

## Controls To Preserve

| Control | Evidence | Why It Matters |
|---|---|---|
| Security headers | [app_mcp/server.py:36](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:36), [app_mcp/server.py:639](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:639) | HSTS, CSP, no-sniff, and referrer policy are correct for a JSON-only MCP server. |
| DNS-rebinding protection | [app_mcp/server.py:119](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:119) | FastMCP transport host/origin checks reduce browser-origin and host-header abuse. |
| HTTPS/TLS baseline | [infra/mcp.bicep:102](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:102), [infra/mcp.bicep:105](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:105), [infra/mcp.bicep:106](/home/shovalbe/projects/campaign-analysis/infra/mcp.bicep:106) | HTTPS-only, TLS 1.2 minimum, and FTPS disabled are sound defaults. |
| Non-root container user | [app_mcp/Dockerfile:16](/home/shovalbe/projects/campaign-analysis/app_mcp/Dockerfile:16), [app_mcp/Dockerfile:41](/home/shovalbe/projects/campaign-analysis/app_mcp/Dockerfile:41) | Reduces container RCE blast radius. |
| Secret injection via auth classes | [app_mcp/_http_client.py:115](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:115), [app_mcp/_http_client.py:134](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:134) | Secrets are added by `httpx.Auth`, not hand-built tool headers. |
| Safe upstream error envelope | [app_mcp/_http_client.py:225](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:225), [app_mcp/tests/test_token_redaction.py:42](/home/shovalbe/projects/campaign-analysis/app_mcp/tests/test_token_redaction.py:42) | Prevents upstream URLs, ACCs, and tokens from leaking in error responses. |
| Token redaction tests | [app_mcp/_logging.py:48](/home/shovalbe/projects/campaign-analysis/app_mcp/_logging.py:48), [app_mcp/tests/test_token_redaction.py:53](/home/shovalbe/projects/campaign-analysis/app_mcp/tests/test_token_redaction.py:53) | Good foundation for audit-safe logging; extend it to PII redaction. |
| Outbound rate limiter | [app_mcp/_http_client.py:38](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:38), [app_mcp/_http_client.py:75](/home/shovalbe/projects/campaign-analysis/app_mcp/_http_client.py:75) | Protects upstream APIs from accidental burst fan-out. |
| OAuth PKCE and Entra ID token verification | [app_mcp/server.py:242](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:242), [app_mcp/server.py:342](/home/shovalbe/projects/campaign-analysis/app_mcp/server.py:342), [app_mcp/oauth.py:157](/home/shovalbe/projects/campaign-analysis/app_mcp/oauth.py:157) | PKCE and Entra JWT validation are implemented; the gap is production enforcement and per-tool authorization. |

