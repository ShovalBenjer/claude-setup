# ElevenLabs Scribe — Cost & Parallelization for qc-call-analyzer

**Date:** 2026-04-28
**Question:** Should qc-call-analyzer migrate from current Scribe to v2 or v3?
**Answer in one line:** **You're already on `scribe_v2`. There is no `scribe_v3`. The only real upgrade lever is `scribe_v2 → scribe_v2_realtime`, which costs +77% and is only worth it if you need <150ms streaming for live calls (you don't — this is batch CDR processing).**

---

## 1. What you're running today

Two call sites in qc-call-analyzer pin the model:

- `src/transcription/stt_service.py:225` — `"model_id": "scribe_v2"`
- `src/api/shared/elevenlabs_stt.py:172,241` — `"model_id": "scribe_v2"`

The docstrings say "Scribe v1" but the actual `model_id` string sent on every request is `scribe_v2`. So the migration to v2 already happened and was never relabeled.

## 2. The model lineup (April 2026, official)

| model_id | Status | Type | Latency | Languages | Source |
|---|---|---|---|---|---|
| `scribe_v1` | Deprecated ("outclassed by v2") | Batch | n/a | 99 | [1] |
| `scribe_v2` | **Current SOTA batch** | Batch (file upload) | seconds-minutes | 90+ | [1][2] |
| `scribe_v2_realtime` | Current realtime | Streaming | ~150ms | 90+ | [1][3] |
| `scribe_v3` | **Does not exist** | — | — | — | [4][5] |

Three independent confirmations that no v3 STT model has been announced for 2026: ElevenLabs `/docs/overview/models` lists only v1/v2/v2_realtime [1]; the 2026 Medium guide explicitly lists current STT as v2/v2_realtime only [4]; ElevenLabs Realtime page describes "Scribe v2 Realtime" as the newest [3]. The "v3" label in the ElevenLabs ecosystem belongs to **Eleven v3** (a TTS model), not STT.

## 3. Pricing

From [elevenlabs.io/pricing/api](https://elevenlabs.io/pricing/api) [2]:

| Model | $/hour | $/minute | Δ vs current |
|---|---|---|---|
| `scribe_v1`/`scribe_v2` (current) | $0.22 | $0.0037 | baseline |
| `scribe_v2_realtime` | $0.39 | $0.0065 | **+77%** |
| Entity detection add-on | +$0.07 | +$0.0012 | optional |
| Keyterm prompting add-on | +$0.05 | +$0.0008 | optional |

**Cost impact at current scale**: Yasha's batch processes one CDR run; assuming a representative 1000 hours/month of processed audio, moving to realtime adds ~$170/mo. At 5000 hr/mo, $850/mo.

## 4. Parallelization & concurrency

ElevenLabs concurrency is **plan-tiered**, shared across all endpoints (TTS, STT, Realtime):

| Plan | Base concurrent | Burst (2× rate) |
|---|---|---|
| Free | 2 | up to 6 |
| Starter ($6/mo) | 3 | up to 9 |
| Creator ($22/mo) | 5 | up to 15 |
| Pro ($99/mo) | 10 | up to 30 |
| Scale ($299/mo) | 15 | up to 45 |
| Business ($990/mo) | 15 | up to 45 |
| Enterprise | "Elevated" (negotiated) | custom |

Source: [help.elevenlabs.io](https://help.elevenlabs.io/hc/en-us/articles/14312733311761) [6]; burst pricing [7]. STT specifically has **elevated concurrency** vs other endpoints per the docs, but the exact STT-only number is not published — you read `current-concurrent-requests` and `maximum-concurrent-requests` response headers at runtime to discover it [8].

**Implication for batch processing**: At Pro tier ($99/mo), you can run 10 concurrent Scribe v2 transcriptions; if each takes 2 min for a 10-min call (5× realtime), throughput ≈ 50 call-mins per wall-clock minute. Bursts allow 30× concurrency for 2× cost on the bursted requests only — useful for Yasha's batch run but not steady state.

The model_id you choose (v2 vs v2_realtime) **does not change** the concurrency tier. It only changes per-stream latency and per-hour price. Realtime gives you 1 stream per concurrent slot streaming at 1× audio rate; batch gives you N parallel files faster than realtime.

## 5. Arabic dialect coverage

- **MSA, Egyptian, Levantine (Syrian/Lebanese/Palestinian), Gulf (Khaleeji), Maghrebi (Moroccan/Algerian/Tunisian)** all named explicitly on the [ElevenLabs Arabic STT page](https://elevenlabs.io/speech-to-text/arabic) [9].
- Aggregate WER: **3.1% on FLEURS, 5.5% on Common Voice** (ElevenLabs published numbers, not per-dialect breakdown) [9].
- AssemblyAI Universal-3-Pro is the closest competitive benchmark; an independent 2026 head-to-head [10] showed AssemblyAI Universal-3-Pro slightly ahead on English narrative, Scribe v2 ahead on multilingual + diarization. For your Arabic + ES + PT mix Scribe stays the better choice.

## 6. Recommendation

**Do not migrate.** You're on `scribe_v2`. Three concrete actions:

1. **Cosmetic fix**: update the docstrings in `stt_service.py:147,216` from "Scribe v1" to "Scribe v2" so the next reader doesn't get confused. ~5-line PR.
2. **Document the choice**: add a one-paragraph "STT model: scribe_v2 (batch). Realtime not used — call processing is post-call CDR-driven, not live." to qc-call-analyzer/CLAUDE.md.
3. **Keep an eye on v3**: ElevenLabs has shown a pattern of v(n) → v(n) Realtime → v(n+1). If Scribe v3 ships in 2026 H2, re-evaluate then. Set a calendar reminder for Aug/Sept 2026.

**Realtime is a bad fit for your pipeline** because:
- Batch is +77% cheaper per hour
- Yasha's `ScheduledJob` runs over CDR records — they're already-recorded audio, not live streams
- Realtime adds operational complexity (websocket lifecycle, partial transcript handling, VAD) for zero quality gain on recorded audio

If you ever stand up a **live agent-coaching** or **real-time call quality** feature, that's when Realtime becomes worth the +77%. Until then, no.

---

## Sources

1. [ElevenLabs Models Documentation](https://elevenlabs.io/docs/overview/models) — official model list
2. [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api) — official pricing
3. [Scribe v2 Realtime — 150ms Latency API](https://elevenlabs.io/realtime-speech-to-text)
4. [ElevenLabs in 2026: The Complete Guide (Medium)](https://medium.com/the-ai-entrepreneurs/elevenlabs-in-2026-the-complete-guide-to-v3-agents-music-and-scribe-7f3c3bdfd201)
5. [Speech to Text — ElevenLabs Documentation](https://elevenlabs.io/docs/capabilities/speech-to-text)
6. [How many requests can I make? — ElevenLabs Help](https://help.elevenlabs.io/hc/en-us/articles/14312733311761)
7. [Burst Pricing — ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/guides/burst-pricing)
8. [API Error Code 429 — ElevenLabs Help](https://help.elevenlabs.io/hc/en-us/articles/19571824571921)
9. [Free Arabic Speech to Text — ElevenLabs](https://elevenlabs.io/speech-to-text/arabic)
10. [AssemblyAI Universal-3-Pro vs ElevenLabs Scribe v2](https://www.assemblyai.com/blog/assemblyai-universal-3-pro-vs-elevenlabs-scribe-v2-compared)

## Methodology note

Standard mode, 4 web searches + 2 web fetches against official ElevenLabs domains and one independent benchmark. No paywalled or first-party leaked roadmap was consulted — all claims trace to publicly accessible URLs. The "no v3 exists" claim is based on absence-of-evidence in three independent 2026-dated sources; if a private/beta v3 is in your account's tenant, this report would not catch it.
