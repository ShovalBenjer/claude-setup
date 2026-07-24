# Follow-up: heal partial transcripts at the STORAGE layer (not just at report time)

**Drafted:** 2026-06-07 · **Status:** local draft (paste into Jira by hand)
**Relates to:** PR #329 (fix/session-insert-enums) — report-layer re-fetch already shipped.

## Context
PR #329 fixes the *symptom*: Arabic reports were attaching a transcript that ends
mid-conversation. The report now re-fetches the authoritative transcript from
ElevenLabs at render time. But the **stored** transcript in `call_recordings` is
still partial for affected sessions, and the scoring that ran on the partial is
never revisited. This ticket fixes the storage-layer root cause.

## Root cause (confirmed)
A partial transcript becomes *sticky*:
1. **Idempotency guard drops the fuller 2nd webhook.** `webhook_elevenlabs/__init__.py:155-166`
   returns `duplicate` once the first `post_call_transcription` set
   `status='COMPLETED'` + a binary `overall_score`. A later, more complete webhook
   never reaches `store_transcript` (line 247).
2. **Re-fetch only fires under 50 chars.** `shared/session_scoring.py:78-85` re-fetches
   from ElevenLabs only when the stored transcript is `< 50` chars. A partial that is
   `>= 50` chars is scored as-is, `scoring_source` flips to `llm` (line ~128), and
   `reconcile_scoring` never re-enqueues it.
3. **Completion gate is truthiness-only.** `shared/elevenlabs_client.py:448-451`
   (`is_conversation_complete`) passes on any non-empty transcript, so a still-finalizing
   partial can be accepted by the poll path.

## Proposed work (acceptance criteria)
- [ ] Webhook: when a `post_call_transcription` arrives for an already-COMPLETED
      conversation, **compare transcript completeness** (turn count) and overwrite
      `call_recordings.transcript_text` via `store_transcript` if the new one is
      strictly more complete — without re-sending the report or re-billing scoring
      unnecessarily. (Relax the guard to allow transcript refresh, keep dedup on the
      report-send + scoring side.)
- [ ] Re-score trigger: if the stored transcript is replaced by a materially more
      complete one, re-enqueue scoring (reset `scoring_source` or add a
      `transcript_refreshed_at` signal `reconcile_scoring` reads).
- [ ] Optional: raise the `score_session` re-fetch trigger from "<50 chars" to a
      duration-aware heuristic (e.g. re-fetch when stored turns look short relative to
      `duration_seconds`).
- [ ] Backfill one-shot: sweep recent COMPLETED sessions, re-fetch from ElevenLabs,
      and heal any `call_recordings` rows whose stored transcript is shorter than the
      source. (Bounded by the ElevenLabs rate limiter.)
- [ ] Tests: pure-function completeness comparison reused from `email_drip_sender`
      (`_transcript_completeness`); webhook idempotency test proving a fuller 2nd
      webhook updates the stored transcript but does NOT re-send the report.

## Premortem (5 failure modes)
1. Relaxing the guard re-sends duplicate report emails → keep send-dedup separate from
   transcript-refresh dedup.
2. Re-scoring churns cost/credits on every duplicate webhook → only re-score on a
   *strictly more complete* transcript, debounced.
3. ElevenLabs returns a transient partial on re-fetch and overwrites a fuller stored
   copy → only overwrite when strictly more complete (turn count primary).
4. Backfill sweep hammers ElevenLabs → batch + respect the client rate limiter/circuit
   breaker; cap per run.
5. `scoring_source` reset re-opens a flood in `reconcile_scoring` → gate on an explicit
   `transcript_refreshed_at > scored_at` condition, not a blanket reset.

## Post-deploy task (separate, manual)
After PR #329 deploys to `func-training-prod`, resend Basel's report so it carries the
full transcript: `POST /api/ops/send-report?session_id=<basel_session_id>`. (Resending
before deploy just re-attaches the same partial, because prod still runs the old code.)
