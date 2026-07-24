## TASK: CA - external audio export endpoint (externalize /api/v1/audio)

- **Type:** Task
- **Reporter:** Yasha
- **Assignee:** Vladyslav Martynenko
- **Project:** DEV
- **Components / labels:** call-analyzer-api, external-api, backend

**Description:**
Expose the existing internal audio download (`GET /api/v1/audio/{externalId}`) under the external family as `GET /api/external/audio/{externalId}`, authenticated with `X-API-Token` like `/api/external/calls`. This removes the interactive-SSO/JWT requirement that blocks qc-telephony-api from pulling lead audio. Return a short-lived signed URL (preferred, so ElevenLabs fetches the bytes directly via cloud_storage_url) or stream `audio/mpeg`. The audio is keyed by `externalId`, which the calls list does not currently return, so also add `externalId` to `GET /api/external/calls` so the caller can map ACC to call to audio.

**Acceptance criteria:**
- `GET /api/external/audio/{externalId}` returns 200 with `{ "externalId", "audioUrl", "mimeType", "sizeBytes", "expiresAt" }`, or streams `audio/mpeg`. 404 when no audio.
- Authenticates with `X-API-Token` only: 401 without the key, 200 with it. No JWT, no interactive SSO on this route.
- The signed `audioUrl` is fetchable by an external client (ElevenLabs) with no extra auth, valid at least 30 minutes.
- `GET /api/external/calls?customerAcc=...&from=&to=` returns `externalId` (and a `hasAudio` flag) per call.
- Response carries no PII: no caller number, lead name, or agent identity. Whitelisted fields only.
- Documented in Swagger at calls.corp-domain.com/docs under the external/audio tag.

### Subtasks

- [ ] **SUB 1.1:** Add `GET /api/external/audio/{externalId}` as an external alias of the internal `/api/v1/audio/{externalId}`. Return a short-lived signed URL (or `audio/mpeg` stream); 404 if none.
      Description: The route qc-telephony-api calls to retrieve audio for transcription.
- [ ] **SUB 1.2:** Authenticate the route with `X-API-Token`, mirroring `/api/external/calls`. Reject without the key. No SSO/JWT on external routes.
      Description: Removes the interactive-login blocker that stopped pulling audio with the x-api-key.
- [ ] **SUB 1.3:** Add `externalId` and `hasAudio` to the `GET /api/external/calls` list response.
      Description: Lets the fan-out map ACC to call to audio and skip calls with no audio.
- [ ] **SUB 1.4:** Document the route in Swagger (calls.corp-domain.com/docs) and notify Shoval.
      Description: Vlad indicated Friday for the docs refresh.

---

**Related work, not this ticket (Shoval, qc-telephony-api):** repoint `/api/transcription/by-accounts` to transcribe through our own `/api/v2/transcribe` (+ `/batch`, `/webhook/elevenlabs`) using the `audioUrl` from this endpoint, so `func-qc-telephony-prod` traffic is non-zero. Gated on Yasha confirming bulk transcription routes through our API rather than direct ElevenLabs. Today runtime shows zero calls to our endpoints and ElevenLabs Scribe v2 used directly, so none of our documented endpoints are in the path yet.



## Call Analyzer current API (verified ground truth, for the ticket body)



External family `/api/external/*`, auth `X-API-Token` (the only family external callers may use):
- `GET /api/external/calls?customerAcc={ACC}&from=&to=` returns `{ calls: [{ callId, provider, realmId, transcriptionId }] }`
- `POST /api/external/calls/{callId}/transcribe` `{ provider, realmId, language }` returns `{ callId, transcriptionId, status }`



v1 family `/api/v1/*`, Bearer JWT via interactive SSO, internal only:
- `GET /api/v1/audio/{externalId}` (audio download, JWT-gated, not usable by a service)
- `POST /api/v1/auth/callback` (OAuth code to JWT + refresh)


**Reference URLs**
- Wiki (QC-Telephony, page 208): https://dev.azure.com/Corp-domain/Corp-AI/_wiki/wikis/Corp-AI.wiki/208/QC-Telephony
- qc-telephony-api (Azure, RG AZAI_group): https://func-qc-telephony-prod.azurewebsites.net
- qc-telephony-api repo: https://dev.azure.com/Corp-domain/Corp-AI/_git/qc-telephony-api
- Call Analyzer docs: https://calls.corp-domain.com/docs (audio tag)
- Call Analyzer repo: https://dev.azure.com/Corp-domain/Corp-domain/_git/call-analyzer-api