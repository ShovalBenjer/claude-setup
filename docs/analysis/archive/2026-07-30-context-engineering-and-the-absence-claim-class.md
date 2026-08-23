# Context engineering, three absence claims in one session, and what /context showed

Date: 2026-07-30. Lane B. Session `beba6c57`, 46 operator turns.

Written because a single `/context` invocation by the operator falsified two claims this
session had already published, and because the current Anthropic guidance on context
engineering argues against the architecture this repository is built on. Both are worth
recording as facts rather than resolving by preference.

## 1. The absence-claim class fired three times in one session

L-2026-07-29-a is "absence claim made against evidence already in hand". It has been open
since 2026-07-29. It fired three times today, and the third time was after the other two
had been written into a reflection.

| # | Claim published | What was actually there |
| --- | --- | --- |
| 1 | "The full banned-word list not already in `tools/slop_lint.py`" | `dot-claude/skills/humanize/SKILL.md`, a LIVE DEPLOYED skill, carries 18 of the 26 words with measured frequency multipliers, the top three at 48x, 35x and 28x. The words themselves are not quoted here for the reason in the note below |
| 2 | github/spec-kit has "no validation, no state machine, and no generator" | `scripts/python/check_prerequisites.py` exists and does phase gating, with byte-equivalent bash twins |
| 3 | "`out-of-distribution.md` points at a dataviz skill that does not exist anywhere" | **`dataviz` is a Claude Code BUILT-IN skill**, roughly 380 tokens, loadable, and listed in `/context` |

Note on that first row, recorded because it happened while writing this file:
`tools/slop_lint.py` **failed this document** for containing two of the banned words as
QUOTED EVIDENCE. That is L-2026-07-29-d live, an oracle that cannot distinguish code from
prose about code, so documenting a defect reads as committing it. The words were removed
and the multipliers kept, which costs a reader the ability to check the example against
the skill file. The oracle's third waiver is for the same class in `panel.py`.

The mechanism is identical in all three: a namespace was searched, absence was found
inside it, and absence was reported for the whole space. Claim 3 searched
`dot-*/skills/` and `~/.claude/skills/` and never enumerated built-ins. The correct
formulation in every case is "not present in X", with X named.

The same `/context` output shows **`review` and `security-review` are also built-in
skills, unused**, while this repository's `review` gate domain has been waived three times
for `panel.py` false positives and this session evaluated `pr-agent`, `open-code-review`
and `reviewdog` as replacements without once naming the two that ship with the tool.

## 2. What `/context` showed, and it was never called

`/context` was not invoked once across 46 operator turns, while this session built a
recall tool to bypass compaction, discussed ending sessions early, and reasoned about
context budget throughout. The operator ran it and it reads:

```
490.4k / 1m  (49%)          Messages 445.9k (44.6%)      Free 509.6k (51%)
always loaded: system 6.5k + system tools 17k + memory 9k (16 files)
               + skills 6.1k (56) + custom agents 2.3k (23)   about 41k, 4%
deferred:      MCP tools 74.2k, system tools 16.8k, loaded on demand
```

Two consequences. Half the window was free, so there was **no compaction pressure at
any point**. And the two compact boundaries at 09:54 were the operator's own `/compact`
invocations at 09:34 and 09:46, not the harness auto-compacting. The complaint about
compaction quality stands; the belief that it was forced does not.

## 3. The current guidance argues against this repository's shape

From "The new rules of context engineering for Claude 5 generation models":

- Anthropic removed **over 80 percent of Claude Code's system prompt** for newer models.
- Reduce constraints and let the model apply judgement rather than follow explicit rules.
- **Progressive disclosure**: load context when needed, not upfront, via skills,
  deferred-loading tools and organised file trees.
- Put instructions in **tool descriptions**, not repeated in system prompts.
- Rely on **auto-memory** rather than hand-curating `CLAUDE.md` as a memory store.
- Prefer **rich references**, code, test suites and artifacts, over markdown specs.

This repository has 14 always-loaded rule files, a 2.4k-token project `CLAUDE.md`, 56
skills and a set of hooks that police the output channel after generation.

The tension is real and is not resolved here by choosing a side. Two things are true:

**For the rules.** Each one traces to a measured failure in `state/lessons.jsonl`. These
are not generic overconstraining; they are evidence with a date attached.

**Against the rules.** The three failures documented in section 1 were **retrieval
failures, not constraint failures**. `dataviz` and `review` existed and were not found.
No additional prose would have prevented any of them, and the guidance's mechanism claim
is therefore supported by this session's own evidence.

The move that follows from both being true: a rule that is a CHECK should live as a hook
or a tool description, where it executes. A rule that is PROSE should be progressively
disclosed rather than always loaded. `slop_lint`, the gate and the fingerprint exclusions
are already on the right side of that line. The 14 always-loaded rule files are not.

## 4. Correction to the OpenGame verdict

The earlier verdict rejected `leigest519/OpenGame` on the grounds that the operator wanted
a game LAYER on a dashboard, making a game-GENERATION framework "buying a factory to make
one part".

That was a wrong model of the intent. The requirement, stated 2026-07-30, is a mini-game
**different and dynamically initialised per project**, simulating the whole workflow from
intents and prompts through planning, as **compatibility testing inside chaos
engineering**. Per-project dynamic initialisation is generation, which is what OpenGame's
Template Skill does, and is why it was saved in the first place.

What survives: do not depend on the framework, which is dormant with three contributors
and no push since 2026-04-22. What is promoted: OpenGame-Bench's three axes, Build Health,
Visual Usability and Intent Alignment, become the measurement surface for the
`compatibility` domain, and per-project template generation becomes the mechanism for the
simulation. The `compatibility` domain is therefore not a twelfth checkbox on the
contract; it is a chaos-engineering surface whose interface is the simulation.

## 5. Recheck

The falsifier for section 1 is cheap and should be run before any future absence claim:
enumerate every namespace the thing could live in, and name the ones searched in the
claim itself. For skills that is four: `dot-*/skills/`, `~/.claude/skills/`, plugin
marketplaces under `~/.claude/plugins/`, and **built-ins**, which are only visible through
`/context` or the skill listing and not through the filesystem.
