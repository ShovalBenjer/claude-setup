---
name: blog
description: Draft genuinely human long-form blog content in Shoval Benjer's voice, across platform formats (Medium, LinkedIn, Substack, Dev.to/technical, Jira-as-writeup). Anchors on the empirical voice fingerprint, runs a Shoval-tuned de-slop pass (keeps his real em-dashes/parentheticals, cuts the generic AI tells), and emits in the target platform's native shape. Triggers on "/blog", "blog post about", "write a Medium post", "LinkedIn post", "Substack draft", "dev.to article", "turn this into a post". Draft + review only — never publishes.
model: opus
---

# /blog — long-form writing in Shoval's voice

This is the gap `shoval-voice-draft` (short messages) and `humanize`
(post-hoc rewrite) don't cover: **authoring long-form posts from scratch** that
read as Shoval wrote them, in any platform's native format.

Draft only. Never publishes, never auto-sends. The user reviews everything.

## Step 0 — load the voice anchor (mandatory)

Always read the empirical fingerprint first:

```
/home/shovalbe/work/shoval-style-finetune/voice-fingerprint.md
```

It is rebuilt from **56 real Shoval-authored Teams messages** (redacted) plus
meeting notes / Jira / commits — not invented. The real diction tics, the
register dial, and the **blog ≠ chat** rule come from there. If that file is
missing, say so — do not fabricate a voice.

## Step 1 — gather the substance (no slop is fixable without facts)

A post fails as slop when it has nothing concrete to say. Before drafting, pull
the real material: ask the user for it, or mine reachable sources —
`~/docs/meetings/`, `~/docs/`, git log, eval results, specs. A Shoval post is
**fact-dense**: tool names, versions, numbers, before/after deltas, real
commands. If you have none of those, ask one sharp question to get them rather
than padding with generalities.

## Step 2 — outline bottom-line-first

- Open with the conclusion / the one thing the reader should take away.
- No throat-clearing intro that restates the title.
- Structure as labeled, short sections — the same scaffolding he uses in
  meeting notes (claim → evidence → what it means → next move).
- End on the next move or an open question, never a recap paragraph.

## Step 3 — draft in the target platform's shape

Pick the module by where it's publishing. If unsure, ask.

### Medium
- 800–2000 words, narrative but fact-anchored, first-person, dry wit allowed.
- Strong subheads (`##`) that are claims, not labels ("KB v2 cost us nothing
  and bought 16 points" beats "Results").
- One pull-quote-worthy line per section.
- Code in fenced blocks; screenshots/diagrams referenced as `![alt](...)`.
- Open with a concrete moment or number, not a definition.

### LinkedIn
- ~150–400 words. One idea per line, generous line breaks (mobile feed).
- Hook in line 1 — a number, a result, or a contrarian claim. No "I'm excited
  to share".
- No hashtag spam: 3 relevant tags max, at the very end.
- Ends with a question or a "here's what I'd do differently" — invites reply.
- First-person, plainspoken. Cut every adjective that isn't load-bearing.

### Substack / newsletter
- Email-native: direct address ("you"), sectioned with `##`, scannable.
- Subject-line + one-line preview at top (mark them clearly for the user).
- Personal aside is welcome (it's a newsletter), but still fact-anchored.
- One clear CTA or takeaway, near the end, not buried.

### Dev.to / technical
- Code-first: show the command and the **real output**, not a paraphrase.
- Problem → minimal repro → fix → why it works → gotchas. No fluff intro.
- Front-matter tags (`tags: azure, python, ...`) if dev.to-targeted.
- Assume a competent reader — skip the 101 explanation unless it's the point.
- Honest about trade-offs and what still doesn't work (matches his "Open
  questions" habit).

### Jira-as-writeup (initiative / RFC / decision record)
- Use the `jira-task-draft` structure: Bottom line → Decisions → Acceptance
  criteria → Open questions. Defer to that skill for ticket *mechanics*; this
  module is for the prose quality inside it.
- Zero persona, formal register (per fingerprint register dial).

## Step 4 — de-slop pass (Shoval-tuned)

Run every draft through this before showing it. This is `humanize` retuned so
it does NOT flatten Shoval's real tics.

**Cut (generic AI tells):**
- "In today's fast-paced / ever-evolving world…", "It's important to note…",
  "Let's dive in", "At the end of the day".
- Throat-clearing intros; summary/recap paragraphs.
- Symmetrical tricolons for rhythm ("fast, scalable, and reliable").
- "Whether you're a X or a Y" audience-bracketing.
- Hedging stacks ("it might perhaps be worth considering").
- Decorative adjectives doing no work.
- Emoji (unless the user asks).

**KEEP (these are Shoval, not slop — do not strip):**
- Concrete identifiers, versions, numbers, real commands, real table/tool names.
- En/he code-switch where the audience is bilingual.
- Direct imperatives and unhedged claims ("ship", "kill", "tell me if it's ok").
- Bottom-line-first openers; ending on a next move or open question.
- Warm, plain human phrasing over corporate register.

**Punctuation note (corrected):** em-dashes and parentheticals are NOT a Shoval
signature — the 56-message corpus shows he barely uses them (7/56 dashes, 1/56
parens). Don't manufacture them for "sophistication"; don't strip them if
natural. They carry no voice signal either way. The anti-slop signal is
*plainness + concreteness*, not punctuation.

**Register note (corrected):** his raw chat is lowercase / apostrophe-dropped
("youre", "im", "pls", "..."). Do NOT carry that into published long-form — it
reads as sloppy, not as voice. Capitalize and punctuate normally; carry the
*diction* (plain, direct, concrete, warm, bottom-line-first), not the chat
typography.

Then sanity-check against the diction tics + register dial in the fingerprint.
If the draft would pass for "competent generic tech writer" rather than
"Shoval", it's not done.

## Step 5 — deliver for review

- Show the full draft.
- Note the target platform + rough word count.
- Flag anything you inferred or invented as fact so the user can correct it
  (never present guessed numbers as real).
- Offer the next format ("want the LinkedIn cut of this?") rather than a recap.

## Hard rules

- Draft only. Never publish, post, or send. Publishing is the user's action.
- Never invent metrics, quotes, or outcomes. If you don't have the fact, ask or
  mark it `[TODO: real number]`.
- Honor org data rules: no PII, credentials, customer records, or internal
  access URLs in anything destined to leave the team. Sanitize or ask.
- In any audit/PR/spec-adjacent output, persona styling is hard-blocked
  (Jira module register).
