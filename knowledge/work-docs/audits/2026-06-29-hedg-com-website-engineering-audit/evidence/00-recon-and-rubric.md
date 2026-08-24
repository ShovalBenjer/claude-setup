# hedg.com Engineering Audit, Evidence Pack 00: Recon + Rubric

Date: 2026-06-29. Target: https://hedg.com (CFD/forex broker, Seekapa family).
Method: passive external observation only. No login, no form submission, no active
probing of api.hedg.com. Any token/PII value is redacted, never reproduced or decoded.

## 1. Transport + edge

- hedg.com (apex) -> 301 -> https://hedg.com/en/ (200). www.hedg.com -> 301 -> apex -> /en/.
- Edge: Cloudflare (server: cloudflare, cf-ray ...-TLV = Tel Aviv PoP). cf-cache-status BYPASS on first hop, HIT on /en/.
- Protocol observed via curl: HTTP/2. HTTP/3 (h3/QUIC) NOT advertised in response headers seen (no alt-svc). To confirm in browser (curriculum "transport modernity" axis).
- TLS verify OK (ssl_verify_result=0). HSTS: max-age=31536000; includeSubDomains; preload (strong).
- Homepage /en/ HTML doc ~178 KB, curl single-fetch time_total ~0.27s (origin/edge fast; full render TBD).

## 2. Security headers (apex + /en/)

Present and good:
- strict-transport-security: max-age=31536000; includeSubDomains; preload
- x-content-type-options: nosniff
- x-frame-options: SAMEORIGIN
- referrer-policy: strict-origin-when-cross-origin
- permissions-policy: geolocation=(), microphone=(self), camera=()  (microphone=self likely for VoiceSpin WebRTC voice)
- content-security-policy present with default-src 'none' baseline (strong skeleton)

Findings:
- x-powered-by: PHP/8.2.5  -> stack/version disclosure; 8.2.5 is an old patch level (8.2.x shipped many security fixes after .5). FINDING (P2 disclosure + P2 patch hygiene if accurate).
- CSP script-src includes 'unsafe-inline' AND 'unsafe-eval' AND data:  -> defeats most of the XSS protection the default-src 'none' baseline would otherwise give. FINDING (P1 for a fintech).
- CSP is otherwise well-formed: object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'. Good.

## 3. CSP allowlist -> third-party fingerprint (~13 external origins)

- code.jquery.com (jQuery, legacy)
- googletagmanager.com + google-analytics.com (GTM + GA)
- s3.tradingview.com + scanner.tradingview.com + tradingview-widget.com + tradingview.com (charting widgets)
- challenges.cloudflare.com (Turnstile CAPTCHA)
- cdn.amplitude.com + api2.amplitude.com (Amplitude product analytics)
- widget.trustpilot.com (Trustpilot reviews)
- cdn.jsdelivr.net (third-party CDN for libs)
- connect.facebook.net (Facebook pixel)
- static.cloudflareinsights.com (Cloudflare RUM)
- clarity.ms + c.clarity.ms (Microsoft Clarity = session replay + heatmaps)
- trackflare.net (unidentified custom tracking endpoint; flag for the team)
- api.hedg.com (first-party backend API)
- wss://webrtc.voicespin.com:7777 + webrtc.voicespin.com (VoiceSpin WebRTC click-to-call)
- google.com + maps.google.com (Maps / reCAPTCHA frames)

Implication: heavy tracking surface (GA + Amplitude + Clarity session replay + FB pixel + trackflare)
is a GDPR/consent and supply-chain concern for a regulated broker. Build-vs-buy looks sane
(charting, reviews, CAPTCHA, voice all bought, not built).

## 4. Cookies set at first page load (pre-auth, anonymous visitor)

- webrtc_user_id = <uuid>; Secure; path=/; Max-Age=1209600. NOT HttpOnly, NO SameSite.
- webrtc_jwt_token = [REDACTED JWT, RS256]; Secure; path=/; Max-Age=3600. NOT HttpOnly, NO SameSite.
  FINDING (P1): a JWT is issued to anonymous visitors at first load and stored in a cookie that is
  Secure but not HttpOnly (XSS-exfiltratable) and not SameSite (CSRF exposure). Token value is NOT
  reproduced or decoded here, per data-protection policy. Confirm scope/claims with the team.
- preferred_language = en; Secure; path=/; Max-Age=2592000; SameSite=Lax (correct flags).

## 5. robots.txt + sitemap

- WordPress site. robots.txt updated June 2026 ("SEO audit fix, removed invalid Content-Signal directive").
- Blocks: /wp-admin/ /wp-includes/ /wp-login.php /wp-register.php /xmlrpc.php /feed/ /trackback/
  /cgi-bin/ /cdn-cgi/ /wp-json/ /wp-content/plugins/ /wp-content/cache/ (reasonable hardening).
- Blocks "hidden/staging language prefixes": /ko/ /ja/ /zh-hk/ (incomplete i18n shipped to prod; minor).
- Allows /wp-content/themes/ and /wp-content/uploads/ (needed for render).
- Sitemap: https://hedg.com/wp-sitemap.xml (default WP sitemap; /sitemap.xml 301 -> 200 text/xml).

## 6. Tech stack inference

WordPress (PHP 8.2.5) marketing site, Cloudflare edge/CDN, separate api.hedg.com backend,
TradingView charting, VoiceSpin WebRTC voice, jQuery-era front end. This is a classic
"WordPress brochure + separate trading backend" split, common for brokers.

---

## RUBRIC A: Data-layer (from "Excellent SQL Engineering, June 2026"), externally-observable subset

Observable on a public site (yes/partial): pagination style (keyset vs offset in URL/XHR params),
cache-control/ETag/Age on JSON endpoints, SQL/stack-trace leakage in error bodies, sequential
integer IDs in URLs/API (enumeration/IDOR risk), GraphQL introspection exposure, version/Server
header leakage, TTFB on repeated data calls (cache tiering), search/filter latency vs result size
(sargability/N+1 proxy), money/date typing in JSON.

Inference-only: N+1 (waterfall shape), overload shedding (503 vs hang), server-side rollups, typing.

Active-probe only (NOT executed, recommend authorized test): SQL injection, IDOR/tenant isolation,
secrets-in-bundle exfiltration. Treat as red-flag hypotheses to confirm with the team.

Citable verdicts: reject UUIDv4 PKs (approve UUIDv7), reject deep OFFSET pagination (keyset >10K rows),
reject string-built SQL (parameterize; whitelist dynamic identifiers), reject FK-less schemas,
mandatory pg_stat_statements + auto_explain, approve HTTP 503 overload shedding over queue-and-hang,
approve DB-layer RLS for tenant isolation, reject MD5 + plaintext creds (SCRAM-SHA-256), approve
single-flight request coalescing, set lock_timeout on every locking migration.

## RUBRIC B: Principal-engineer grading lens (from "Principal Engineer Curriculum, June 2026")

Pillar 1 Systems: transport modernity (HTTP/3 at edge, TLS1.3), edge/origin routing (anycast CDN,
<50ms, cache-aware), caching discipline (Cache-Control/ETag/immutable hashed assets, CDN HIT ratio),
streaming TTFT (shell renders fast, content streams; LCP/INP), reliability signals (graceful
degradation, status page, sane error pages).

Pillar 2 Architecture: API design (noun resources, /v1/ path versioning, keyset pagination,
RFC 7807 errors, idempotency keys, OpenAPI 3.1), bounded-context integrity, dependency hygiene /
third-party risk (minimal vetted 3p, SRI, no render-blocking vendors), build-vs-buy, evolutionary
fitness functions.

Pillar 3 Product: conversion-path clarity (one instrumented critical path, North Star), analytics
instrumentation (event-based), feature-flag/rollout maturity, trust + compliance signals
(ToS/Privacy, GDPR/CCPA consent, risk warnings, license/regulatory disclosure -> fintech-critical
and highly observable), pricing coherence.

Pillar 4 AI: streaming AI UX, trust calibration (sources, confidence, graceful failure),
human-on-the-loop (reversible by default, confirm irreversible). If no AI feature ships, mark
"not present" (a positioning finding, not a pass).

Citable standards: "ADR written after implementation is a changelog entry, not a decision record";
"Buy for generic capabilities (auth, payments, email, search), build for core differentiation";
"Enable HTTP/3 at the edge for all new services, the configuration is trivial, fallback is automatic";
"alert on burn rate, not when the budget is exhausted"; "cost per inference, not cost per GPU-hour";
"right-size to workload, not prestige"; "perceived performance tracks TTFT more than total response
time"; "reversibility by design, confirm irreversible actions regardless of automation level";
"users who cannot assess AI confidence either over-trust or under-trust".

## RUBRIC C: Production AI & SW Eng maturity ladder + verdicts (doc 1)

Security ladder: L1 basic auth+HTTPS; L2 OAuth2.0/JWT/Vault; L3 OAuth2.1+PKCE, RLS, SBOM;
L4 Passkeys, SLSA L2; L5 zero-trust mTLS, attestations, continuous compliance.
Anti-patterns relevant here: tokens in localStorage/non-HttpOnly cookies (use HttpOnly or memory),
OAuth implicit grant, UUIDv4 PKs on high-write tables, offset pagination on large tables,
secrets in env vars, no prompt versioning (if AI present).
