# Jira Comment Drafting Rules

Global rule. Applies to every Jira comment on qboservices.atlassian.net (replies,
acks, status notes, handoffs), in every session and project. Companion to the
`shoval-voice-draft` and `jira-task-draft` skills and the CLAUDE.md output hard rule.

## Principle

A Jira comment is outward-facing: Amit, Yasha, Liron, and managers read it, and it
notifies watchers. Treat it like any other Jira write. Draft for review, post only on
explicit per-action OK. The reminder tooling (`~/.claude/bin/jira-reminder-refresh.py`)
is read-only; posting uses the Key Vault token (`Shoval/JIRA-API-KEY`) and happens only
after Shoval approves the exact text.

## Always

1. Draft, never auto-post. Produce the exact text, wait for explicit OK, then post.
   No silent comments. Same gate as any Jira write in CLAUDE.md Authorization.
2. Author in Shoval voice. Load `shoval-voice-draft` for any Jira comment. Bottom-line
   first, direct, warm, technical. Not Claude's register, not a report.
3. Write the comment in English. Jira is the written record, so default to English even
   when the upstream chat and the other commenters (e.g. Amit) used Hebrew. Tech nouns
   stay English anyway (QA, DEPARTMENT, FTD, cron, pipeline, dashboard, API). Switch to
   Hebrew only if Shoval explicitly asks for that issue.
4. Inherit the output hard rules. No em-dash or en-dash (use a comma, colon, period, or
   parentheses), no emojis, no AI-slop register. The CLAUDE.md HARD RULE already binds
   Jira; it is restated here because comments are where it slips.
5. Sound human, not generated. Beyond punctuation: no stand-in symbols (arrows), no rigid
   bullet symmetry, no rule-of-three, no telegraphic "X, cleaner than Y, go" compression.
   Match the other person's register, name the specific thing, leave it slightly rough (a
   contraction, a trailing "lmk"). See `shoval-voice-draft` > Sound Human. A perfectly
   parallel, symbol-studded comment reads as AI even with the em-dashes removed.

## Shape

- If it is an ack, one line is the whole comment.
- If it is substantive: one-line outcome, then up to three bullets (done / open / next),
  then one explicit ask. Do not restate the ticket back to the person who wrote it.
- Close the loop: when acking someone's request, name what you did about each point so
  they do not have to ask again.

## Register by recipient

Inherit the tone table in `shoval-voice-draft`. Quick map:
- Amit: casual peer. Mirror his opener ("אחי" level only if he opened that way).
  Direct, fast, bottom-line.
- Liron: status first, what is usable now, what to prioritize.
- Yasha: technical. Acknowledge the point, state the access/visibility boundary, ask
  for the next decision.
- Managers / external: more formal, ownership and approval explicit, no credentials.

## Honesty

- Never claim work, tests, approvals, or another person's words that did not happen.
- Scope the comment to the round actually shipped, not the whole epic. Moving an issue
  to QA does not mean every sub-ask is done.
- Bracket anything unverified for Shoval to confirm before posting: `[verify: ...]`.
- No secrets, tokens, or customer PII in a comment (inherit pii-handling).

## Worked example (DEV-5013 -> Ready for QA, reply to Amit)

Fuller handoff:

```
Talked with Amit today. Moving to Ready for QA for this round.

What's in:
- Email settings: you pick DEPARTMENT first, then who gets it, like you asked (it wasn't relevant without that), with a searchable dept picker.
- Email settings moved to their own tab, out of the Team/Agent view.

Ready for your QA, mainly email accuracy. If the site doesn't open from home, access goes through Cloudflare with Yasha (your allowlist got overwritten), so coordinate with him.

Tell me what's off and I'll fix it.
```

One-line ack variant:

```
Talked with Amit today, moving to Ready for QA. Email now picks DEPARTMENT then who receives it, like we agreed. Run your QA and tell me what's off.
```
