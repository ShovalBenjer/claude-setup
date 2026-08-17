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

## STT (input side)

The operator's stated preference is Wispr Flow (wisprflow.ai): he has used it
and it injects text system-wide, where Win+H refuses remote apps such as WSL
terminals. Recorded as preference pending his confirmed install; the VOICE-1
ticket owns the unified channel and the engine block stays open until then.
