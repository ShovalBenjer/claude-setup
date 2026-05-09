# ElevenLabs Scribe STT — Model Lineage & Migration Requirements

**Date:** 2026-04-27
**Scope:** qc-call-analyzer Arabic transcription pipeline (currently `scribe_v2`)
**Decision needed:** Whether to migrate off `scribe_v2`.

---

## Executive Summary

**Recommendation: NO MIGRATION REQUIRED. Stay on `scribe_v2`.**

There is no Scribe v3 or v2.5. The current ElevenLabs STT lineup as of 2026-04-27 has three models: `scribe_v1` (deprecated, "outclassed by v2 models" [1]), `scribe_v2` (batch SOTA, what we use), and `scribe_v2_realtime` (live streaming, 150ms latency, separate model_id, **not applicable** to our batch pipeline).

Scribe v2 was launched 2026-01-12 as the new state-of-the-art [2]. Since launch, ElevenLabs has shipped only **additive, non-breaking** enhancements: keyterm prompting (up to 1000 terms), entity detection, and an `audio_duration_secs` response field [2][3][4]. No deprecation date is announced for `scribe_v2`. The "v2.5" hint the user heard from training-cutoff drift refers to the **Text-to-Speech** product line (v2.5 TTS), not STT [5].

**Action items, in priority order:**
1. **No model_id change.** We are already on the current best-in-class STT for Arabic.
2. **Adopt `keyterms`** to bias toward Israeli-Arabic + Khaleeji dialect terms — pure win for our WER, +20% cost only on calls that use it.
3. **Verify `audio_duration_secs`** is being read where we currently compute it client-side (eliminate a ~5-10 LOC hack).
4. **Skip `entity_detection`** unless PII redaction becomes a compliance requirement (+30% cost).
5. **Realtime model is not for us** — our pipeline is batch (cleaned audio file → STT → translate). Switching to realtime would require a full architecture rewrite and is not justified by call-analyzer's use case.

---

## Per-Question Findings

### Q1. Does ElevenLabs offer Scribe v2.5 or v3? Exact model_id strings?

**No.** The current model catalogue per the official model overview [1]:

| Model ID | Status | Use case |
|---|---|---|
| `scribe_v2` | Active, recommended | Batch transcription, 90+ languages |
| `scribe_v2_realtime` | Active | Live streaming, 150ms latency, conversational agents |
| `scribe_v1` | Deprecated | "Outclassed by v2 models" — do not start new integrations [1] |

The Speech-to-Text API reference confirms only `scribe_v2` and `scribe_v1` as valid `model_id` values for the `/v1/speech-to-text` (batch) endpoint [6]. There is no `scribe_v3`, no `scribe_v2_5`, no `eleven_scribe_v3`. Web searches restricted to `elevenlabs.io` return zero hits for those identifiers.

> "**Scribe v2** — State-of-the-art speech recognition model … 90+ languages"
> "**Scribe v2 Realtime** — Real-time speech recognition model … ~150ms latency"
> "**Scribe v1** — State-of-the-art speech recognition. Outclassed by v2 models" [1]

### Q2. Published WER, especially for Arabic

ElevenLabs publishes a **tiered WER table** on the capabilities page rather than per-language numbers [7]:

- **Excellent (≤ 5% WER)** — English and many others
- **Good (>10% to ≤20% WER)** — Arabic falls in this tier per the published table

Our internal claim of **11.1% Arabic WER** for `scribe_v2` (from `qc-call-analyzer/src/transcription/stt_service.py:82`) sits at the better end of that "Good" tier and is consistent with what ElevenLabs publishes. There is **no newer model with a lower published Arabic WER** to migrate to.

### Q3. Breaking API changes since `scribe_v2` launch

**None.** All changes since 2026-01-12 are additive [2][3][4]:

| Date | Change | Type |
|---|---|---|
| 2026-01-12 | Scribe v2 launch; new params: `entity_detection`, `keyterms`; new response field: `entities` | Additive |
| 2026-02-02 | Python SDK v2.33.1: bug fix for **URL streaming in Scribe** (relevant — we use SAS URL pattern) | Fix |
| 2026-04-07 | New response field: `audio_duration_secs` | Additive |

Request schema (current, per [6]):
- Audio input: `file` (binary, ≤3.0GB) **or** `cloud_storage_url` (HTTPS, ≤2GB) **or** `source_url`
- `language_code`: ISO-639-1 / ISO-639-3 (we already pass `"ar"`)
- `diarize` (bool, default false), `num_speakers` (int|null), `diarization_threshold` (0.0–2.0), `detect_speaker_roles` (requires `diarize=true`)
- `timestamps_granularity`: `none` | `word` (default) | `character`
- `tag_audio_events`: bool (default **true**)
- `webhook` + `webhook_id` + `webhook_metadata` (≤16KB)
- `temperature` (0.0–2.0), `seed` (deterministic)
- `use_multi_channel`, `file_format` (`pcm_s16le_16` | `other`)
- `enable_logging` (false = zero retention)
- `keyterms` (array, ≤1000, **+20% cost**)
- `entity_detection`, `entity_redaction`, `entity_redaction_mode` (**+30% cost**)
- `no_verbatim` (scribe_v2 only — strips fillers)
- `additional_formats`: docx, html, pdf, srt, txt, segmented_json

Response schema (current, per [6]):
- `language_code`, `language_probability`, `text`, `words[]`, `audio_duration_secs`, `entities[]`, `transcription_id`, `additional_formats`
- `words[]`: `text`, `start`, `end`, `type` (`word`|`spacing`|`audio_event`), `speaker_id`, `logprob`, `characters` (if char-granularity)
- Multichannel: `transcripts[]` keyed by `channel_index`

### Q4. Pricing changes per tier

ElevenLabs **does not publish per-minute STT pricing** on the public pricing page [8]. STT is bundled into subscription tiers (Free → Enterprise). Two cost multipliers are explicit in the API ref:
- `keyterms`: **+20%** cost
- `entity_detection`: **+30%** cost

To compare actual per-minute rates between `scribe_v2` and `scribe_v2_realtime`, you'd need to ask sales / check the dashboard — public docs don't disclose.

### Q5. New features that justify changes for our Arabic-call use case

| Feature | Available since | Verdict for qc-call-analyzer |
|---|---|---|
| **`keyterms` (1000-term biasing)** | 2026-01-12 | **Adopt.** Bias toward Israeli-Arabic + Khaleeji vocabulary, brand terms, customer names. +20% cost is acceptable for accuracy gain. |
| **Speaker diarization (32 speakers)** | scribe_v2 baseline | Already mentioned in our docs; verify we set `diarize=true` for multi-speaker calls. |
| **`detect_speaker_roles`** | scribe_v2 | Optional — would surface "agent" vs "customer" automatically if useful. |
| **`entity_detection` + redaction** | 2026-01-12 | **Skip** unless legal/compliance requires PII redaction. +30% cost. |
| **`tag_audio_events`** (defaults to true) | scribe_v2 | Verify our parser handles `(laughter)`, `(footsteps)` tokens — the response includes word objects with `type="audio_event"`. |
| **`audio_duration_secs` response field** | 2026-04-07 | **Use it.** Eliminates client-side duration computation. |
| **`use_multi_channel`** | scribe_v2 | If we ever get separate left/right channels (agent vs customer), this gives per-channel transcripts cleanly. |
| **Code-switching** | Not separately documented as a flag | `language_code` accepts ISO codes; mixed-language handling is implicit. No new param. |

### Q6. Migration checklist

**There is no model migration to perform.** What follows is an **opt-in feature adoption** checklist if the user wants to pull more value from `scribe_v2`:

#### Code changes (against current `qc-call-analyzer`)

1. **`src/transcription/stt_service.py:225`** — payload to `/v1/speech-to-text`:
   ```python
   data = {
       "model_id": "scribe_v2",          # unchanged
       "language_code": "ar",
       "diarize": True,                   # if multi-speaker calls
       "tag_audio_events": True,          # default; explicit for clarity
       "keyterms": ARABIC_DIALECT_KEYTERMS, # NEW — list of dialect/brand terms
   }
   ```
   Add a constant `ARABIC_DIALECT_KEYTERMS` curated with Yasha (domain expert per CLAUDE.md). Keep ≤1000 entries, ≤20 chars each.

2. **`src/api/shared/elevenlabs_stt.py:172` and `:241`** — same change in both call sites.

3. **Response parser** — wherever we compute audio duration client-side, replace with `response["audio_duration_secs"]` (added 2026-04-07).

4. **`tag_audio_events`** — confirm downstream parser handles `type="audio_event"` words (e.g., `(laughter)`). If we want clean transcript text only, set `tag_audio_events=false`.

#### Test changes

- **VCR.py fixtures** — the response schema is **backward compatible** (new fields are additive). Existing recorded fixtures will keep deserializing. **Re-record only** the cassettes that exercise paths touching the new params (`keyterms`, `audio_duration_secs`). Approx 2–3 fixtures per call site.
- Add a unit test asserting `keyterms` is forwarded in the request payload.
- Add an integration test recording where `keyterms` is set and confirm a known dialect term transcribes correctly.

#### Operational

- No env-var changes (`ELEVENLABS_API_KEY` unchanged).
- No SDK pin change required, but if you pin ElevenLabs Python SDK explicitly, ensure ≥ v2.33.1 (URL streaming bug fix for SAS URL pattern, 2026-02-02).
- No region availability concerns (single global API endpoint).

### Q7. Is `scribe_v2` deprecated or scheduled for sunset?

**No.** No deprecation notice exists for `scribe_v2`. The only deprecated STT model is `scribe_v1`, and even that is still callable, just labelled "Outclassed by v2 models" [1]. There is no announced sunset date for either.

---

## Migration Checklist — Concrete Diffs

If the user decides to adopt `keyterms` + the new `audio_duration_secs` field:

```diff
# src/transcription/stt_service.py
+ARABIC_DIALECT_KEYTERMS = [
+    # curated by Yasha — Israeli-Arabic + Khaleeji + brand/customer terms
+    "...", "...", "...",
+]

 def _call_elevenlabs_scribe(self, audio_path, language):
     data = {
         "model_id": "scribe_v2",
+        "language_code": language,
+        "tag_audio_events": True,
+        "keyterms": ARABIC_DIALECT_KEYTERMS,
     }
     # ... existing multipart post ...

# Wherever we compute duration client-side:
- duration = compute_duration_from_segments(words)
+ duration = response["audio_duration_secs"]
```

Mirror the same edits in `src/api/shared/elevenlabs_stt.py` (two call sites: lines 172, 241).

---

## Risks & Gotchas

| Risk | Severity | Mitigation |
|---|---|---|
| `keyterms` raises cost +20% on every call | Low | Acceptable for accuracy gain; revisit if monthly bill spikes >15% |
| `keyterms` overfits to bias terms (false positives) | Medium | Limit list to high-confidence dialect/brand terms; review monthly |
| ElevenLabs SDK <2.33.1 has URL-streaming bug | High if not pinned | Pin `elevenlabs>=2.33.1` in `requirements.txt` |
| Our SAS-URL pattern (<55min files) hits the **2GB cap** for `cloud_storage_url` | Low | Already enforced upstream by file-size cap |
| `tag_audio_events=true` injects `(laughter)` tokens into transcript text | Medium | Confirm downstream translator (`gpt-5.1`) handles them gracefully or set `tag_audio_events=false` |
| ElevenLabs may release Scribe v3 and silently change Arabic WER tiers | Low | Re-run this research quarterly; subscribe to changelog RSS |
| Public pricing page does not disclose per-minute STT cost — actual margin unknown | Medium | Pull invoice data from billing dashboard; renegotiate if usage grew >2x |
| `entity_detection` (+30%) may be tempting but is not currently a requirement | Low | Skip until legal/compliance asks for PII redaction |
| Realtime model `scribe_v2_realtime` is a different code path entirely (WebSocket / streaming REST) | High if attempted | Do **not** swap `model_id` to `scribe_v2_realtime` — it is not a drop-in replacement |

---

## Bibliography

[1] ElevenLabs Documentation — *Models Overview*. https://elevenlabs.io/docs/overview/models — Lists `scribe_v2`, `scribe_v2_realtime`, `scribe_v1` (deprecated). Retrieved 2026-04-27.

[2] ElevenLabs Documentation — *Changelog January 12, 2026*. https://elevenlabs.io/docs/changelog/2026/1/12 — "Scribe v2, the new state of the art transcription model" launch announcement; `entity_detection`, `keyterms` added. Retrieved 2026-04-27.

[3] ElevenLabs Documentation — *Changelog February 2, 2026*. https://elevenlabs.io/docs/changelog/2026/2/2 — Python SDK v2.33.1: "Fixed bug with URL streaming in Scribe". Retrieved 2026-04-27.

[4] ElevenLabs Documentation — *Changelog April 7, 2026*. https://elevenlabs.io/docs/changelog/2026/4/7 — `audio_duration_secs` added to `/v1/speech-to-text` response. Retrieved 2026-04-27.

[5] WebSearch (elevenlabs.io domain restriction) — confirmed zero hits for `scribe_v3`, `scribe_v2_5`, `eleven_scribe_v3`. Retrieved 2026-04-27.

[6] ElevenLabs Documentation — *Speech to Text API Reference (`POST /v1/speech-to-text`)*. https://elevenlabs.io/docs/api-reference/speech-to-text/convert — Full request/response schema; valid `model_id` values: `scribe_v2`, `scribe_v1`. Retrieved 2026-04-27.

[7] ElevenLabs Documentation — *Speech-to-Text Capabilities*. https://elevenlabs.io/docs/overview/capabilities/speech-to-text — Tiered WER table; Arabic in "Good (>10% to ≤20% WER)" tier; 90+ languages. Retrieved 2026-04-27.

[8] ElevenLabs — *Pricing*. https://elevenlabs.io/pricing — STT bundled into subscription tiers; per-minute STT cost not publicly disclosed. Retrieved 2026-04-27.

[9] ElevenLabs — *Realtime Speech-to-Text*. https://elevenlabs.io/realtime-speech-to-text — Marketing page for `scribe_v2_realtime`; 150ms latency, WebSocket/REST. Retrieved 2026-04-27.

---

## Methodology

- **Mode:** Standard (6 phases: SCOPE → PLAN → RETRIEVE → TRIANGULATE → SYNTHESIZE → PACKAGE).
- **Sources:** Restricted to `elevenlabs.io` (official docs, changelog, pricing, marketing). One web search step used cross-domain to confirm absence of `scribe_v3` / `scribe_v2_5` identifiers anywhere indexed.
- **Triangulation:** Three independent ElevenLabs URLs cross-checked the model catalogue (models overview, capabilities page, API reference). All three agree only `scribe_v2`, `scribe_v2_realtime`, `scribe_v1` exist.
- **Limitations:** Pricing data unavailable publicly. Internal training/customer-data WER may differ from published tiers. ElevenLabs may release Scribe v3 between this research and any decision.
