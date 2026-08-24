# QC Telephony API

Stateless HTTP API for call transcript translation, Q&A with grounded citations, direct ElevenLabs Scribe v2 transcription, and an async, callback-driven batch transcription pipeline. Designed as a passive worker for the call analyzer middleware.

| Item | Value |
|------|-------|
| Version | v2.7 |
| Runtime | Azure Functions, PremiumV3, Linux Python 3.11 |
| Environment | Production |
| Base host | `func-qc-telephony-prod.azurewebsites.net` |

## Quick start

```
curl -X POST "https://func-qc-telephony-prod.azurewebsites.net/api/translate?code=$QC_FUNCTION_KEY" \
-H "Content-Type: application/json" \
-d '{
  "callId": "demo-001",
  "language": "ar",
  "targetLanguage": "en",
  "segments": [
    { "speakerId": "speaker_0", "start": 0.0, "end": 2.4, "text": "السلام عليكم" }
  ]
}'
```

Replace `$QC_FUNCTION_KEY` with the per-route function key from Key Vault `kv-seekapa-apps`. A 200 response carries `sourceLanguage`, `targetLanguage`, and per-segment `originalText` plus `translatedText`. Detailed shapes are in the API reference.

## Authentication

All non-anonymous routes require an Azure Functions per-route function key passed either as the `?code=` query parameter or as the `x-functions-key` HTTP header. Keys live in `kv-seekapa-apps` and are rotated quarterly. The `/api/health` route is anonymous and intended for liveness probes.

```
curl -H "x-functions-key: $QC_FUNCTION_KEY" "$BASE/api/agent/query"
curl "$BASE/api/agent/query?code=$QC_FUNCTION_KEY"
```

| Concern | Where |
|---------|-------|
| Function key storage | Azure Key Vault `kv-seekapa-apps`, secret name `QC-Telephony-FunctionKey-{route}` |
| Key rotation cadence | Quarterly, manual via the Function App App Keys blade |
| AAD upgrade | Tracked as a v2.5 candidate. Function keys are the only auth surface today. |
| Outbound to Azure OpenAI | Managed Identity, PR 209. No key handling on the AOAI side. |
| Outbound to ElevenLabs | `xi-api-key` from `kv-seekapa-apps/ElevenLabs-ApiKey`. Server side only. Never returned to callers. |

## Conventions

### Request and response shapes

| Convention | Detail |
|------------|--------|
| Body format | All bodies are `application/json` unless a route explicitly accepts `multipart/form-data`, as in Scribe v2 transcribe. |
| Timestamps | Decimal seconds from the start of the call, using `start` and `end`. |
| Speaker labels | Opaque strings such as `speaker_0` and `speaker_1`. The API does not identify speakers across calls. |
| Language codes | ISO 639-1 lower case, such as `ar`, `en`, `he`, `es`, `pt`, `ru`, and `uk`. The transcribe endpoint accepts any Scribe v2 supported language. The translate endpoint is dialect aware for `ar`, `es`, and `pt` to `en` or `he`. |

### Error envelope

Failures return a JSON body with `error`, `message`, and optional `code`. Validation errors return 400; auth failures return 401; upstream LLM failures return 502; archive tier audio sources return 409.

```json
{
  "error": "VALIDATION_ERROR",
  "message": "segments must contain between 1 and 500 items",
  "code": "SEGMENTS_REQUIRED"
}
```

### Idempotency

Translate and Q&A routes are pure functions of their input. The same request produces the same response within the model stochasticity boundaries, with temperature 0 where possible. The transcribe and batch routes accept an `idempotency_key` or `Idempotency-Key` header where documented for safe retries.

## API reference

Endpoint stability labels:

| Label | Meaning |
|-------|---------|
| GA | Production stable, supported |
| STAGED | Merged to `main`, awaiting deploy |
| DEPRECATED | Scheduled for removal, do not adopt |
| PLANNED | Specced, not yet implemented |

### GET /api/health GA

Anonymous liveness probe. Returns `{ "status": "ok" }` and the running build SHA. Intended for Azure Monitor availability tests and external uptime probes.

```
curl "https://func-qc-telephony-prod.azurewebsites.net/api/health"
```

Response 200:

```json
{ "status": "ok", "build": "6746385" }
```

### POST /api/translate GA

Translate call transcript segments from a source language to a target language. Preserves segment timestamps and speaker labels. Injects `translatedText` alongside `originalText`.

Request parameters:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| callId | string | yes | Caller assigned unique identifier for the call |
| language | string | yes | Source language ISO 639-1 code, such as `ar`, `es`, or `pt` |
| targetLanguage | string | no, default `en` | Target language ISO 639-1 code, `en` or `he` |
| duration | number | no | Call duration in seconds, informational |
| segments | array | yes | 1 to 500 `Segment` objects with `speakerId`, `start`, `end`, and `text` |

Request:

```
curl -X POST "$BASE/api/translate?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "callId": "call_123",
  "language": "es",
  "targetLanguage": "en",
  "segments": [
    { "speakerId": "speaker_0", "start": 0.0, "end": 5.0, "text": "Hola, buenos dias" }
  ]
}'
```

Response 200:

```json
{
  "callId": "call_123",
  "sourceLanguage": "es",
  "targetLanguage": "en",
  "duration": null,
  "segments": [
    {
      "speakerId": "speaker_0",
      "start": 0.0,
      "end": 5.0,
      "originalText": "Hola, buenos dias",
      "translatedText": "Hello, good morning"
    }
  ]
}
```

Errors:

| Status | error | When |
|--------|-------|------|
| 400 | VALIDATION_ERROR | Body fails Pydantic validation, such as missing fields or segments out of bounds |
| 401 | UNAUTHORIZED | Function key missing or invalid |
| 502 | LLM_ERROR | Upstream Azure OpenAI failed after retries |

### POST /api/telephony/translate GA

Telephony format translation. Identical translation semantics to `POST /api/translate`, but the request shape mirrors the call analyzer CDR structure: `audioId`, `duration`, `speakers`, `segments`, `wordCount`, and `createdAt`. Response mirrors input with `originalText` plus `translatedText` injected per segment.

Use this from CDR-driven pipelines where the upstream object already matches the call analyzer schema. Use `POST /api/translate` for other callers.

```
curl -X POST "$BASE/api/telephony/translate?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "audioId": "AUD-2026-05-12-001",
  "language": "ar",
  "targetLanguage": "he",
  "duration": 120.5,
  "wordCount": 150,
  "speakers": ["speaker_0", "speaker_1"],
  "segments": [
    { "speakerId": "speaker_0", "start": 0.0, "end": 5.0, "text": "مرحبا" }
  ],
  "createdAt": "2026-05-12T10:00:00Z"
}'
```

Same error envelope as `POST /api/translate`.

### POST /api/agent/query GA

Question answering over a single call transcript. Returns a concise answer with grounded segment citations. Optional in-process session memory, with 60-minute sliding TTL, allows follow-up questions by `callId` without resending segments.

Request parameters:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| callId | string | yes | Identifier for the call, also used as the session memory key |
| language | string | yes | Source language of the transcript |
| question | string | yes | Free-form question, minimum one character |
| segments | array | yes for the first request | Transcript segments. Required on first call. Optional on follow-ups within 60 minutes. |
| translatedSegments | array | no | Pre-translated segments to give the model in both languages |

First call request. Segments are required:

```
curl -X POST "$BASE/api/agent/query?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "callId": "call_123",
  "language": "ar",
  "question": "What was the customer complaining about?",
  "segments": []
}'
```

Response 200:

```json
{
  "callId": "call_123",
  "question": "What was the customer complaining about?",
  "answer": "The customer reported that their order arrived three days late.",
  "confidence": 0.88,
  "relevantSegments": [
    {
      "speakerId": "speaker_0",
      "start": 12.4,
      "end": 18.1,
      "text": "...",
      "translation": "..."
    }
  ]
}
```

Errors:

| Status | error | When |
|--------|-------|------|
| 400 | SEGMENTS_REQUIRED | First request for a callId without segments. Returns 400 instead of a magic string answer. |
| 401 | UNAUTHORIZED | Function key missing or invalid |
| 502 | LLM_ERROR | Upstream Azure OpenAI failed after retries |

### POST /api/agent/summary DEPRECATED

Cited call summary. Every claim grounds to one or more 0-based segment indices. Ungrounded claims are dropped server side as an anti-hallucination guard.

Removal scheduled. This route was added on the `master` branch lineage and never landed on `main`. When the next pipeline run promotes `main` to prod, this route disappears. The activity audit found no production callers in source. If you depend on it, contact the API owner before the next deploy.

```
curl -X POST "$BASE/api/agent/summary?code=$KEY" \
-H "Content-Type: application/json" \
-d '{ "callId": "...", "language": "es", "segments": [] }'
```

### DELETE /api/session/{callId} GA

Evict the in-process session memory entry for a callId. Useful when a long-running operator session is closed and any cached transcript state should be purged immediately. The cache also self-expires after a 60-minute sliding window.

```
curl -X DELETE "$BASE/api/session/call_123?code=$KEY"
```

Response 200:

```json
{ "callId": "call_123", "evicted": true }
```

### POST /api/v2/transcribe GA

Direct ElevenLabs Scribe v2 speech-to-text. **Sync by default; async when `callback_url` is provided.**

**Sync mode** (no `callback_url`): send multipart audio, receive the transcript in the response. Max 200 MB per request, 210-second timeout. If ElevenLabs processing exceeds 210 seconds, add `callback_url` to switch to async.

**Async mode** (`callback_url` present in multipart form): returns 202 immediately. ElevenLabs processes in the background and POSTs the result to your `callback_url` when done. Handles files up to 2 GB. Zero storage on our side.

**URL-only async** (JSON body with `cloud_storage_url` + `callback_url`): ElevenLabs fetches the audio directly - the file never passes through this service.

Speaker hints are applied server side: `use_multi_channel=1` for stereo telephony, `num_speakers=2` for mono (fixes the multi-speaker bloat that unconstrained Scribe v1 diarization produced on two-party calls). Any Scribe v2 supported language is accepted.

The `metadata` part is optional: a bare `-F audio=@call.mp3` works, with `call_id` defaulted from the filename, language auto-detected, and mono `num_speakers=2` applied. Fields may also be passed individually instead of a JSON blob, e.g. `-F call_id=... -F language_code=ar -F stereo=false`.

Multipart fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| audio | file | yes (sync and file-based async) | Binary audio file. `call_id` defaults from filename if omitted. |
| callback_url | string | no | If present, switches to async mode. Returns 202. |
| call_id | string | no | Propagated to response. Defaults from filename. |
| language_code | string | no | ISO 639-1 hint. Auto-detected if omitted. |
| stereo | string | no | `true` enables `use_multi_channel`. Default `false`. |
| num_speakers | string | no | Speaker count hint, 1-8. Ignored when `stereo=true`. Default 2. |
| metadata | JSON part | no | Alternative to individual fields: a JSON blob with all of the above except `audio`. |

JSON body fields (async URL-only):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cloud_storage_url | string | yes | HTTPS URL. ElevenLabs fetches it directly (up to 2 GB). |
| callback_url | string | yes | Endpoint to receive the completed transcript. |
| call_id | string | no | Defaults from URL filename. |
| language_code | string | no | ISO 639-1 hint. |
| stereo | bool | no | Default false. |
| num_speakers | int | no | Default 2. |

Sync request (bare file, no callback):

```
curl -X POST "$BASE/api/v2/transcribe?code=$KEY" \
-F "audio=@call.mp3;type=audio/mpeg" \
-F "language_code=ar"
```

Async request (file with callback):

```
curl -X POST "$BASE/api/v2/transcribe?code=$KEY" \
-F "audio=@call.mp3" \
-F "language_code=ar" \
-F "callback_url=https://analyzer.corp-domain.com/api/internal/qc-callback"
```

Async request (URL, JSON body, large or long audio):

```
curl -X POST "$BASE/api/v2/transcribe?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "cloud_storage_url": "https://store/signed/call.mp3?sig=...",
  "language_code": "ar",
  "callback_url": "https://analyzer.corp-domain.com/api/internal/qc-callback"
}'
```

Response 200 (sync):

```json
{
  "call_id": "1772457109.130",
  "transcription_id": "tx-...",
  "language_code": "ar",
  "language_probability": 0.97,
  "text": "Hello world!",
  "words": [
    { "text": "Hello", "start": 0, "end": 0.5, "type": "word", "speaker_id": "speaker_1", "logprob": -0.124 }
  ],
  "segments": [],
  "engine": "scribe_v2"
}
```

Response 202 (async):

```json
{ "transcription_id": "tx-...", "call_id": "...", "status": "accepted" }
```

Errors:

| Status | error | When | Recovery |
|--------|-------|------|----------|
| 400 | VALIDATION_ERROR | Missing or malformed multipart fields | Check that `audio` part is present |
| 400 | MULTIPART_REQUIRED | JSON body sent without `callback_url` | Send multipart audio for sync, or add `cloud_storage_url` + `callback_url` for async |
| 400 | MISSING_AUDIO | JSON body without `cloud_storage_url` | Provide `cloud_storage_url` or send multipart audio |
| 413 | AUDIO_TOO_LARGE | Audio body exceeded 200 MB sync ceiling | Use `callback_url` + `cloud_storage_url` for large files |
| 504 | STT_TIMEOUT | ElevenLabs took > 210s on sync path | Add `callback_url` to switch to async mode |
| 502 | STT_UPSTREAM_ERROR | ElevenLabs returned an HTTP error | Check audio format and encoding; ElevenLabs may be experiencing issues |
| 502 | STT_CONFIG | `ELEVENLABS_API_KEY` not set or Key Vault reference broken | Contact ops to verify app settings on `func-qc-telephony-prod` |
| 500 | STT_ERROR | Unexpected server error | Check App Insights traces on `func-qc-telephony-prod-insights` |

### POST /api/v2/isolate GA

Denoise / isolate speech from an audio file - a mirror of ElevenLabs Audio Isolation (convert). Send the file, get the cleaned audio back. Useful before transcription on noisy recordings; callers may chain `/api/v2/isolate` then `/api/v2/transcribe`.

```
curl -X POST "$BASE/api/v2/isolate?code=$KEY" \
-F "audio=@call.mp3" \
--output clean.mp3
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| audio | file | yes | The audio to isolate (`multipart/form-data`) |
| file_format | string | no | `pcm_s16le_16` or `other` (default `other`) |

Response 200 is the isolated audio bytes (`Content-Type: audio/mpeg`); nothing is persisted. Caps at 25 MB (sync ceiling). Returns 400 if the body is not multipart or the `audio` part is missing, 413 if oversize, 502 if the ElevenLabs key is not configured. Uses the same server-side `xi-api-key` as transcribe.

### POST /api/transcription/by-accounts GA

Marketing and sales self-service entry point. Caller posts a list of customer account codes. The route fans out across the call analyzer external API to discover and trigger transcription for every matched call. Returns one row per call with its transcription identifier and status. Caps `accounts` at 200 per request.

```
curl -X POST "$BASE/api/transcription/by-accounts?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "accounts": ["ACC30318549", "ACC30316817"],
  "providers": ["voicespin"],
  "date_from": "2026-05-01",
  "date_to": "2026-05-26"
}'
```

Response 200:

```json
{
  "accounts": [
    {
      "acc": "ACC30318549",
      "calls": [
        {
          "callId": "1772457109.130",
          "transcriptionId": "tx-...",
          "status": "completed"
        }
      ]
    }
  ],
  "summary": {
    "accounts_total": 2,
    "calls_total": 14,
    "calls_failed": 0
  }
}
```

### POST /api/v2/transcribe/batch GA

Submit N URL-based calls async in one request. Each item's `audio_url` is passed to Scribe as `cloud_storage_url`. Each completion is POSTed to `callback_url` independently as it finishes - the caller aggregates. **Zero storage: no batch row, no orchestrator.** Binary files use `POST /api/v2/transcribe` with a `callback_url` (one per call). Fan-out is bounded by `max_concurrency`.

```
curl -X POST "$BASE/api/v2/transcribe/batch?code=$KEY" \
-H "Content-Type: application/json" \
-d '{
  "items": [
    { "call_id": "1772457109.130", "audio_url": "https://store/signed/A.mp3?sig=...", "language": "ar" }
  ],
  "callback_url": "https://analyzer.corp-domain.com/api/internal/qc-callback"
}'
```

Response 202:

```json
{ "accepted": 2, "submitted": [ { "call_id": "...", "transcription_id": "tx-..." } ], "errors": [] }
```

### POST /api/webhook/elevenlabs GA

ElevenLabs async-completion intake - **stateless forward**. Anonymous at the platform layer (the HMAC signature is the auth). Verifies `ElevenLabs-Signature`, then forwards the per-call result to the `callback_url` in `webhook_metadata`, signed with `X-QC-Signature`. Non-verifying requests return 401 and forward nothing. On callback-delivery failure we return non-2xx so ElevenLabs re-delivers (our only retry mechanism, no state).

#### Per-call callback contract

For every completed call we POST to the caller's `callback_url`:

```
POST {callback_url}
X-QC-Signature: sha256=<hmac_sha256 over the raw body, caller's shared secret>
Content-Type: application/json

{
  "call_id": "1772457109.130",
  "transcription_id": "tx-...",
  "status": "completed",
  "language_code": "ar",
  "text": "...",
  "words": [ { "text": "...", "start": 0.0, "end": 0.5, "type": "word", "speaker_id": "speaker_1" } ]
}
```

The caller verifies `X-QC-Signature` with its shared secret. Batch jobs get one callback per call; the caller aggregates.

## Roadmap: planned routes

Spec: `docs/superpowers/specs/2026-05-26-v4-campaign-endpoint.md`, rev 3, passive batch API. Endpoints 1 to 3 and 5 shipped in v2.4. Endpoint 4 and the artifact downloads remain planned.

| Route | Status | Purpose |
|-------|--------|---------|
| POST /api/v2/summarize/batch | PLANNED | Azure OpenAI Global Batch for summary, translate, or v4 deep-dive modes. Chains from a `transcribe_batch_id` or accepts inline transcripts. |
| GET /api/v2/{transcribe,summarize}/batch/{id}/{artifact} | PLANNED | SAS redirect downloads for per-artifact files such as `results.jsonl`, `report.xlsx`, `verification-log.md`, and `summaries.jsonl`. 10-minute TTL. |

## Errors

| HTTP | error code | When | Recovery |
|------|-----------|------|----------|
| 400 | VALIDATION_ERROR | Pydantic validation failed on request body | Inspect `message` for the bad field. Correct and retry. |
| 400 | SEGMENTS_REQUIRED | First Q&A request for a callId without segments | Resend with `segments` populated. |
| 401 | UNAUTHORIZED | Function key missing or invalid | Refresh key from `kv-seekapa-apps`. Verify quarterly rotation did not drop you. |
| 409 | ARCHIVED_BLOB | URL variant points to archive tier blob that has not been rehydrated | Rehydrate to hot or cool tier, 15 minutes to 15 hours, then retry. |
| 413 | AUDIO_TOO_LARGE | Multipart audio body exceeded 200 MB sync ceiling | Use `callback_url` + `cloud_storage_url` for large files, or split the file. |
| 400 | STAGING_KEY_EXPIRED | A batch item referenced a `staging_key` that no longer exists, past its 24h TTL | Re-upload via `POST /api/v2/staging` and resubmit the item. |
| 401 | WEBHOOK_UNVERIFIED | ElevenLabs webhook HMAC signature missing, malformed, stale, or wrong | Verify the shared `ElevenLabs-WebhookSecret` and clock skew under 30 minutes. |
| 502 | STAGING_CONFIG / BATCH_STORE_CONFIG / STT_CONFIG | Required storage or upstream config missing on the Function App | Provision the storage account, container, and app settings. See Architecture. |
| 503 | DURABLE_UNAVAILABLE | Durable Functions extension not loaded in the deployed venv | Confirm `azure-functions-durable` is installed and the extension bundle is present. |
| per item | OUT_OF_RETENTION | A batch source aged past the 1-year voicespin retention window, upstream 404 or 409 | Rehydrate from archive tier and resubmit that `call_id`. The batch itself does not fail. |
| 502 | LLM_ERROR | Azure OpenAI failed after the retry budget, 3 attempts with exponential backoff | Treat as transient. Surface to the user. Retry idempotently if appropriate. |
| 504 | STT_TIMEOUT | ElevenLabs took > 210s on the sync transcribe path | Add `callback_url` to the request to switch to async mode. |
| 502 | STT_UPSTREAM_ERROR | ElevenLabs returned an HTTP error (4xx/5xx) on the transcribe path | Check audio format and encoding. ElevenLabs may be experiencing issues. |
| 500 | STT_ERROR | Unexpected error on the transcribe path | Check App Insights traces on `func-qc-telephony-prod-insights`. |

## Languages

| Layer | Source | Target | Notes |
|-------|--------|--------|-------|
| Transcription, POST /api/v2/transcribe | Any Scribe v2 language, 99 supported, including `ar`, `en`, `he`, `ru`, `uk`, `es`, `pt` | n/a, transcribes to source language | `language_code` is optional. Scribe v2 auto-detects when omitted. `keyterms`, up to 50 entries of 20 characters each, biases the decoder. |
| Translation, POST /api/translate, POST /api/telephony/translate | `ar` Levantine/Gulf/MSA; `es` LatAm/Castilian; `pt` Brazilian/European | `en`, `he` | Dialect-aware prompts. The API accepts any ISO code in `language` or `targetLanguage`, but only the curated pairs are quality graded. |
| Q&A, POST /api/agent/query | Matches transcript language | Answer is rendered in the question language | Reasoning is in context against the transcript embedded in the system prompt. |

## Architecture

| Component | Azure resource | Notes |
|-----------|---------------|-------|
| Function host | `func-qc-telephony-prod`, Azure Functions Python v2, Linux, PremiumV3 | Always warm. Shares App Service Plan `ASP-AZAIPROJECTS`. |
| LLM | Azure OpenAI, `brn-azai/gpt-5.4-mini-qc-api-telephony` | Managed Identity auth, PR 209. No key handling. |
| STT | ElevenLabs Scribe v2, `api.elevenlabs.io/v1/speech-to-text` | Single `POST /api/v2/transcribe` endpoint handles sync and async. Call analyzer continues to call Scribe v1 directly until migrated. |
| Session memory | In-process dict cache, 60-minute sliding TTL | No external storage. Cache is per instance. Rewritten in v2.7 (PR 331) after storage account `stqctelephonyapi` was decommissioned. |
| Telemetry | Application Insights, `func-qc-telephony-prod-insights`, workspace-based, linked to `workspace-groupK0Th` | Provisioned 2026-05-26, PR 293. OpenTelemetry-based emit via `azure-monitor-opentelemetry`. `APPLICATIONINSIGHTS_CONNECTION_STRING` must be set as an app setting AND `configure_azure_monitor()` must be called at module load (both are in place as of PR 293). |
| CI / CD | Azure Pipelines, `azure-pipelines.yml`, definition `qc-telephony-api-ci`, deploys from `main` | Legacy VSO Deployment Center on the Function App is still pinned to `master`. Scheduled for retirement after the next clean pipeline-driven deploy. |
| Secrets | Azure Key Vault, `kv-seekapa-apps`, hyphenated naming: `AzureOpenAI-Key`, `AzureOpenAI-Endpoint`, `ElevenLabs-ApiKey` | Quarterly rotation. Pipeline fetches via `AzureKeyVault@2`. |

## Observability

Application Insights captures per-route request counts, latency percentiles, dependency tracing into Azure OpenAI and ElevenLabs, log statements, and unhandled exceptions. KQL queries against the workspace:

```
requests
| where timestamp > ago(24h)
| summarize n = count(), p50_ms = percentile(duration, 50), p95_ms = percentile(duration, 95) by name
| order by n desc
```

```
dependencies
| where target contains "openai" and timestamp > ago(24h)
| summarize n = count(), p50 = percentile(duration, 50), p95 = percentile(duration, 95) by name, resultCode
```

The Functions runtime requires `configure_azure_monitor()` to be called at module load on Linux Python. Setting only `APPLICATIONINSIGHTS_CONNECTION_STRING` is insufficient. Both are in place as of PR 293.

## Versioning

The API follows pragmatic semantic versioning.

| Change type | Rule |
|-------------|------|
| Major | Breaking changes to request or response shapes, or auth |
| Minor | New endpoints or backwards-compatible additions |
| Patch | Bug fixes and operational improvements |

Versions are tagged in the `qc-telephony-api` ADO repo, such as `v2.3` and `v2.2.1`. Each tag corresponds to a single Function App deployment.

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| v2.7 | 2026-06-16 | `POST /api/v2/transcribe/async` merged into `POST /api/v2/transcribe` - add `callback_url` to the request for async mode. Sync timeout raised from 90s to 210s. New error codes: `STT_TIMEOUT` (504) and `STT_UPSTREAM_ERROR` (502). Silent empty-detail 500 on timeout eliminated. |
| v2.6 | 2026-05-27 | Stateless zero-storage redesign (spec rev 4). New `POST /api/v2/transcribe/async` + stateless `POST /api/v2/transcribe/batch` (fan-out, per-call callbacks); `/api/webhook/elevenlabs` rewritten to forward (no Durable). `cloud_storage_url` for large/long audio (ElevenLabs fetches up to 2 GB); direct cap 25 MB -> 200 MB. Retired staging blob, qc-batches table, Durable orchestrator, and `/api/v2/staging`. Nothing stored on our side. |
| v2.5.1 | 2026-05-27 | `POST /api/v2/transcribe` response now includes the raw ElevenLabs fields `text` and `words[]` (per-word `speaker_id`/`logprob`/`type`), per Vlad. Passed through verbatim; the grouped `segments[]` view is retained, so the response is a superset. |
| v2.5 | 2026-05-27 | New endpoint `POST /api/v2/isolate`, PR 309 - mirrors ElevenLabs Audio Isolation (convert): multipart audio in, isolated `audio/mpeg` out, optional `file_format`, up to 25 MB. Lets callers denoise before transcription (isolate -> transcribe). |
| v2.4.2 | 2026-05-27 | Breaking: `POST /api/v2/transcribe` is now binary-only, PR 307. The JSON `audio_url` input (Variant A) is removed; a non-multipart body returns 400 `MULTIPART_REQUIRED`. Callers send the file via multipart. No known prod caller used the URL form. |
| v2.4.1 | 2026-05-27 | `POST /api/v2/transcribe` Variant B accepts a bare binary file, PR 306. `metadata` part optional; `call_id` defaults from the filename; fields acceptable as individual form fields. Unblocks file-only callers that cannot share a URL. |
| v2.4 | 2026-05-27 | Passive Batch API, PR 304. New endpoints: `POST /api/v2/staging`, `POST /api/v2/transcribe/batch`, `POST /api/webhook/elevenlabs`. `POST /api/v2/transcribe` gains the multipart Variant B path. Durable Functions orchestrator for the transcribe path; verified end-to-end on a local Durable host plus Azurite, 5-item batch with HMAC-signed callback. Batch items default to mono, `num_speakers=2`. Post-deploy config required: app settings `ElevenLabs-WebhookSecret`, callback secret, storage connection, plus the `qc-staging` container and 24h lifecycle rule. |
| v2.3 | 2026-05-26 | Pipeline KV secret name fix, PR 293. Application Insights provisioned and instrumented via OpenTelemetry. Direct ElevenLabs Scribe v2 transcription endpoint, PR 291. Account-keyed batch transcription dispatch, PR 285. Passive Batch API spec rev 3 committed. |
| v2.2.1 | 2026-05-06 | In-process session memory cache restored, 60-minute sliding TTL, PR 217. Reversed the 2026-04-28 stateless-only stance. |
| v2.2 | 2026-04-28 | Stateless Q&A. Removed Azure Table Storage session memory. Model swap to `gpt-5.4-mini-qc-api-telephony`. |
| v2.1 | 2026-02-15 | Crash fixes, request timeouts, graceful degradation on upstream failures. |
| v2.0 | 2026-01-26 | Initial release: translation plus Q&A API with E2E quality validation suite. |
