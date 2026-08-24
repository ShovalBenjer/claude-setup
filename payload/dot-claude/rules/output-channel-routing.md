# Output-channel routing: how a session picks voice, meme, artifact, diagram, or text

Operator-directed 2026-08-17, drafted as a cross-lane proposal by the
interview-prep session and adopted by lane A the same date. TTS is a default
channel, not a novelty; the question a session asks is "which channel fits this
message", not "should I bother".

## The table

- **TTS** (Windows System.Speech via powershell, verified 2026-08-17; reference
  implementation say.sh in the interview-prep project): away-from-screen or
  tired signals, long-run status updates, spoken drill or coaching questions.
  Never for code, tables, or anything the operator must re-read.
- **Meme** (meme-gen skill, persona register): mirror when the operator opens
  in meme register, and proactively when a moment genuinely lands, per the
  memes-and-expressive-channels memory. Hard-blocked in audits, PRs, CI, eval
  reports (the persona rule already binds this; this row cross-references it).
- **HTML artifact**: deliverables meant to be studied or shared. Never for a
  single-fact answer.
- **Diagram**: three or more interacting parts, flows, architecture.
- **Plain text**: the default, in the short scannable shape the
  terminal-reports-outpace-reading memory fixes.

## The fuller catalogue (operator's Buzz research, Gemini chat "AI Agent
Communication on Buzz", 2026-08-17; ensure-this-is-in directive)

The five channels above are the workstation subset of a wider mode space the
operator mapped for agent-human communication, to be implemented as the
dashboard/buzz UI grows: micro-signals (emoji reactions and stickers as
low-noise acks: eyes-on when starting, check when done), voice notes and
huddle-style TTS briefings, annotated screenshots and diff previews,
interactive prompts/form widgets for approvals, and code-native events
(patches, review comments, signed workflow triggers). Its interaction policy
maps by register: high-signal/low-noise gets reactions and silent updates;
social moments get memes and stickers; deep engineering gets threaded markdown
and cited diffs; urgent escalation gets direct mentions and voice. Sessions
should already behave by that policy today where the substrate exists (text,
memes, TTS); the rest lands with DASH-1.

## STT (input side)

The operator's stated preference is Wispr Flow (wisprflow.ai): he has used it
and it injects text system-wide, where Win+H refuses remote apps such as WSL
terminals. Recorded as preference pending his confirmed install; the VOICE-1
ticket owns the unified channel and the engine block stays open until then.
