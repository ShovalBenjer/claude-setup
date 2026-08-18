---
name: explain-simply
description: "Use when the operator asks for a simple, plain, or clear explanation, says he does not follow, or asks what is broken in plain language. Also use before any status update, decision summary, blocker list, handoff, or report a human must act on. Applies sourced plain-language rules with an executable checker that measures the draft instead of trusting it."
model: opus
---

# explain-simply - write it so the reader can act, then measure that you did

A style rule nothing measures is a wish. This repo has shipped several: the rule
and its violation looked the same from outside. So this skill ships a checker
beside it. Run the checker on your draft before you send it.

The checker sits beside this file. Both paths below work. The same two files live
in the repo and in the deployed tree, byte for byte.

```bash
# from the claude-setup repo root
python dot-claude/skills/explain-simply/plain.py check DRAFT.md
# from anywhere, using the deployed copy
python ~/.claude/skills/explain-simply/plain.py check DRAFT.md
# prove the checker's own rules can still fire
python dot-claude/skills/explain-simply/plain.py selftest
```

## When to use

- The operator asks for a simple or plain explanation, or says he does not follow.
- You are about to send a status update, a blocker list, or a decision summary.
- You are about to write a handoff someone else has to act on.
- A long report is forming and nobody asked for a report.

## SKIP when

- The artifact is code, a spec, a schema, or a commit message.
- The reader asked for depth on one narrow point.
- You are writing a claim row, where the wording is a contract and not prose.

## The rules, and where they come from

Source: `digital.gov/guides/plain-language/writing`, the host that
`plainlanguage.gov` now redirects to. Numbers come from the federal
plain-language guidance.

- Write in the active voice. Name who does the thing.
- Write in the present tense.
- Cut hidden verbs. A verb turned into a noun needs a weak verb to hold it up.
  `We conduct an analysis of the data` becomes `we analyze the data`.
- Use the shorter word. Say `use`, not `utilize`.
- Keep sections and paragraphs short. One topic per paragraph.
- Expand an acronym at or before its first use.

The limits the checker enforces, each one measured and not assumed:

| limit | value |
| --- | --- |
| words in one sentence | `25` |
| average words per sentence | `20` |
| share of sentences in active voice | more than `0.5` |
| sentences in one paragraph | `5` |

Three sources gave nothing and are listed so their absence is visible. The
Department of Labor plain-language document returned `HTTP 403`. The `wid.org`
copy of the federal guidelines returned binary this session could not parse. The
Australian Style Manual page on sentence length timed out.

## This repo's own rules, on top of the sourced ones

These do not come from any style guide. They come from failures here.

Lead with what is broken, blocked, unknown, or skipped. Put the passing work
after it. A reader who stops halfway must still have the bad news.

Separate what you will do yourself from what you need the operator to do. Mixing
them is how a blocker sits for a week. Every item you hand him gets the exact
command, and the way back out.

Never put a number in prose unless a command produced it. The checker enforces
this: a numeral in the text must also appear in code somewhere in the same
document. The `24%` to `64%` figure survived in resume copy for weeks with
nothing behind it, and then had to be pulled. So the rule is mechanical now, not
a matter of care.

Name the instrument. "The suite passes" is a feeling. A command and its exit code
is evidence.

## What the checker reports

Each finding names its own check, worst first. The names are stable, so a claim
can quote one.

- `unbacked_number` - a numeral in prose that no code in the document carries.
- `passive_majority` - half or more of the sentences are passive.
- `avg_sentence_too_long` - the average sentence runs past the limit.
- `sentence_too_long` - one sentence runs past the limit.
- `paragraph_too_long` - one paragraph holds too many sentences.
- `hidden_verb` - a weak verb propping up a noun that should be the verb.
- `unexplained_acronym` - an acronym used before anything expands it.
- `jargon` - a long word or a wordy phrase with a shorter form.
- `passive_sentence` - advisory only. It prints, and it never fails the run.

That last one is deliberate. Passive detection is a heuristic, so it
over-reports. A single hit is information. Only the ratio decides pass or fail.

## Honest limits of the checker

It reads the shape of the writing. It cannot tell whether the writing is true.
A draft can pass every check here and still be wrong. It can still bury the
failure, and still hand the operator a blocker with no command attached.

The checker raises the floor. It does not do the thinking.

Sentence splitting uses a regex and not a parser. A reference such as `Sec. 3`
splits wrongly. Headings, code, table rows, and links are removed before
measurement, because a heading is not a sentence and would corrupt every length.

## Proof this checker can fail

A green selftest is unfalsified, not verified. So each rule has a case that must
fire and a case sitting exactly on its limit that must stay quiet. Then every
guarantee gets broken on a copy, one at a time, and the selftest has to go red.

```bash
python tools/audit/mutate.py --spec plain
```

Claim `C-026` in `state/claims-verify.jsonl` carries that command. The
falsifiability job in `.github/workflows/ship-gate.yml` runs the selftest, and
`mutate.py --spec all` covers this spec with the rest.
