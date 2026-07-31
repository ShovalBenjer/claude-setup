---
name: voice-metrics
description: Measure a draft against the real corpus before sending it. Per-use-case metric rules, a locally-fitted idiolect embedding, randomised burst variants, and Hebrew/English spell check. Use when drafting a WhatsApp message, blog post, or any outbound text that has to sound like a specific person.
---

# voice-metrics

Scores a draft against measured statistics from the local corpus instead of
against an impression of how someone writes. Everything runs offline; the
WhatsApp corpus is private message content and nothing here sends it anywhere.

Companion to `shoval-voice-draft` (which decides what to say) and
`whatsapp-query` (which produces the corpus).

## What is measured versus what is asserted

Two kinds of number live in `profiles.py` and they must not be confused.

- **MEASURED**: produced by `voice.py fit` from the corpus. Regenerate, never
  hand-edit. Length bands, burst-run bands, evenness bands.
- **RULED**: a style decision with no corpus behind it, such as "no em dashes".
  Asserted, and marked as asserted.

## Known limitation, load-bearing

**There is no sender direction in the corpus.** `genericStorage.dec.db` is
WhatsApp Desktop's search mirror and has no sender column; no other decrypted
store has one either. So every per-contact profile is **thread-level, both sides
combined**. A figure like "median 20 chars" describes the conversation, not one
writer. Label it that way.

An unsupervised recovery was attempted and **rejected by its own diagnostic**.
Clustering each thread into two voices and picking the side that recurs across
threads produced a strong-looking contrast (owner-side cross-thread agreement
+0.884 versus counterparty +0.430, permutation p<0.001), but speakers alternate
and those labels do not: alternation minus chance was -0.010 at message level,
-0.019 at 30s, -0.012 at 90s, +0.006 at 300s. The clusters were generic-versus-
thread-specific vocabulary, which reproduces the same contrast with no speaker
information in it. Reproduce with `diag_turns.py`. `separate_speakers()` is kept
only so the negative result stays runnable; **do not use its output as
authorship.**

## Commands

```bash
# measure profiles from the corpus (writes profiles.json)
python voice.py --db <dir>/genericStorage.dec.db fit --contact "<chatId or name>"

# score a draft
python voice.py --db ... check draft.txt --profile whatsapp_<id> \
    --rules whatsapp_close --embed

# randomised burst groupings, ranked
python voice.py --db ... variants lines.txt --profile whatsapp_<id> \
    --rules whatsapp_close --embed --top 3

# print the asserted rules for a surface
python voice.py rules whatsapp_close
```

`--embed` turns on the corpus-similarity check. Without it only the shape gates
and the marker rules run, which is fast and still catches most problems.

## How the pieces work

**Idiolect embedding** (`voice_engine.py`). Hashed character 3-4-gram TF-IDF,
PCA to 64 dimensions, fitted on this corpus only. numpy is the sole dependency.
A pretrained sentence encoder is the wrong tool: those embed meaning, and voice
matching needs handwriting. Two messages with identical meaning and different
spelling habits must land far apart, which is the opposite of what a semantic
encoder does. A hosted embedding API is also barred outright, because the input
is private message content.

**Corpus similarity** (`voice_score.py`). Mean similarity to the k=8 nearest
real messages, reported as a percentile of how corpus-like real messages are.
Not distance to the corpus centroid: that was tried first and failed, because
the centroid of a diffuse casual cloud sits in generic-language territory, so
bland text scores well by construction (formal Hebrew hit p76 and passed every
time). kNN asks whether anything in the corpus actually looks like this.

The target is a **band, not a maximum**. A draft more corpus-like than 97% of
real messages is flagged, not rewarded, because maximising similarity produces
the most average possible message, which is itself the generated-text signature.

**Randomisation** (`voice_variants.py`). Given lines to send, the deterministic
choice is to group them at the corpus median, and repeating that makes every
message the same shape. So burst sizes are drawn from the empirical
distribution, N variants are generated, each is scored, and they are ranked.
Seeded: same seed, same variants.

Each burst is a separate send and is scored as one, against the per-message
profile. The run is scored separately against the run profile. Scoring the
concatenation against a per-message profile compares 18 sends to the length of
one, fails every variant identically, and tells you nothing.

**Marker rules** (`profiles.py: HARD_FAIL`). Register is invisible to shape
gates: formal Hebrew at plausible length passes all of them. The marker list
closes that gap, and **every entry was counted against the corpus before being
added**. Candidates that occur in real chat were dropped, including several that
sound equally formal: משמעותי (37 hits), נא ל (35), קריטי (22), אשר (4),
מדובר ב (4), and לא רק...אלא גם (4). That last is textbook negative parallelism
and is still real usage here. Re-run `mine_markers.py` before adding anything.

## Measured performance

`validate_scorer.py`, trained on the first 80% of a thread and tested on the
held-out 20%:

| input | passes | note |
| --- | --- | --- |
| real held-out messages | 88% | true-accept |
| the actual rejected draft | 0% | the 700-char block that started this |
| English at chat length | 0% | caught by the script check |
| generated-register Hebrew | 0% | caught by the marker rules |
| formal Hebrew | 12% | weakest case |

Corpus-similarity alone, as AUC against held-out real: 0.93 for the rejected
draft, 0.91 formal, 0.81 English, 0.74 generated register. Informative, and not
reliable enough to reject on by itself, which is why it fails only below p10 and
warns to p25. At p10 the false-reject rate on real messages is 10% and it
catches 39% of impostors. **The shape and marker gates do most of the work.**

## Spell check

`lexicon/spellcheck.py`, Hebrew from hspell 1.4 (324,329 inflected forms:
wolig nouns/adjectives, woo verbs, wolig-on-shemp verbal nouns, plus the
milot/extrawords/biza files), English from dwyl/english-words (370,105).

```bash
python lexicon/spellcheck.py draft.md
python lexicon/spellcheck.py --include-code message-draft.md
```

`--include-code` matters for message drafts, where the deliverable itself sits
in fenced blocks so it stays copyable; without the flag the fences are stripped
and the actual message is never checked.

It surfaces unknowns for triage rather than auto-correcting. Slang and loanwords
(מופז, איזי, קלאסי, הוואטסאפ) will flag and are usually correct.

Rebuild the Hebrew lexicon with `lexicon/build_lexicon.py` against an extracted
hspell tree. Two things that are easy to get wrong: the verb generator is `woo`,
not `woo.pl`, and `shemp.dat` must be run back through `wolig.pl` or the lexicon
has no verbal nouns at all (no חיפוש, no התכתבות).

## Use cases covered

`whatsapp_close`, `whatsapp_acquaintance`, `whatsapp_logistics`, `blog_post`,
`devto`, `x`, `bluesky`, `github_readme`, `recruiter_reply`. Each names its
binding gates, its percentile band, its ceilings, whether it sends as a burst,
a single message, a thread or a document, and its non-numeric rules. Run
`voice.py rules` to print them.

## Before sending

- Refit if the corpus changed. Profiles are only as current as the last `fit`.
- `sends over run p95` means the content is too long for one run. Cut lines;
  do not merge them into bigger sends.
- Spell check with `--include-code` for message drafts.
- A passing score is not approval to send. Sending is a separate decision that
  needs the operator.
