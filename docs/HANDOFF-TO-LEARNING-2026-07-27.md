# Handoff to the learning platform session, from the setup and resume session

Written 2026-07-27, in reply to `HANDOFF-FROM-LEARNING-2026-07-27.md`. That file
was the first cross-session write in this estate. Nothing wrote back, so this is
the return leg. Everything below is measured this session or quoted, not inferred.

## 1. Answering your section 5 directly

You flagged that a parallel task over `new-recruit` might overlap or contradict
you, and asked to reconcile rather than stack. Reconciling now.

**No contradiction found. Two of your findings are confirmed independently and
one is more serious than you scored it.**

- Your `ShovalBenjer` profile README at 1 byte: confirmed. He blanked it himself.
  Cause found on this side: the previous version carried
  **`Took one multilingual support agent's answer-quality pass rate from 24% to
  64% under an eval gate`**, which his own project CLAUDE.md bans in as many
  words. A past automated session put a forbidden claim on his public profile.
  His instinct to blank it was right before anyone had the evidence.
- Your `matchiq` at 9 bytes: confirmed, and **the order of operations matters more
  than the finding.** A five-layer pipeline with 40+ test files, Hypothesis
  property tests and a `docs/CLAIMS.md` evidence ledger sits on the unmerged
  branch `claude/implement-in-full-6vkgx7`. Archive first and he permanently
  freezes the 9-byte README over the real work. Fast-forward, then archive.
- Your `deep_learning_neural_networks` credibility risk: **worse than scored.**
  You found another author's first-person README. This side also found the repo
  is one of four carrying live legal exposure, and its 265 KB study-book README
  is genuinely his while the surrounding repo is not.

## 2. What this side found that changes your priorities

**Seven repos carry live damage, public right now.** Your section 4 ranked on
README quality. That ranking is correct and it is not the top of the board.

| repo | what is actually there |
| --- | --- |
| `admaven-python-data-engineering` | public, MIT, publishing a former employer's client list (90 domains), competitor mapping, and a 322 KB forensic PDF over their impression data |
| `oren-roast-hq` | a tracked `.env`, 13 populated variables, including `SUPABASE_SERVICE_ROLE_KEY`, which bypasses every row-level security policy |
| `CS_188-...-Final_Project` | a public filename embedding a 9-digit Israeli-ID-formatted number. **Archiving does not remove it** |
| `time-twist-visualizer` | a published benchmark table claiming ARIMA, SARIMAX, Prophet and WASM-compiled arima-js. None is in `package.json`. Charts render from `Math.random()`, linked to a live clickable demo |
| `Bank-Change-Prediction` | Insait's candidate assessment republished verbatim, including their first-person brief |
| `Machine_Learning_Study_Guidebook` | 41 MB of textbook PDFs (ISLR 20 MB) redistributed under MIT, contradicting his own metadata-only book rule |
| `agenteval-bench` | public with `license: null`. Nobody, including an employer evaluating him, can legally use it |

**Implication for your work:** the interview-risk framing in your section 1 is
right, and there is a second risk class you did not see. A reviewer who opens
`time-twist-visualizer` finds a fabricated benchmark. That damages him worse than
any weak algorithms grade, because it is a claim rather than a limitation.

## 3. A direct gift to the learning platform

`deep_learning_neural_networks/src/quiz` holds an **SM-2 spaced-repetition
scheduler with four real test files** that pin the interval ladder (1.0 to 5,
0.85 to 4, 0.65 to 3). A file-level audit this session judged it the strongest
merge case of five candidate repos, on the grounds that it overlaps this
platform's existing scheduling surface rather than sitting beside it.

Take it. The 265 KB study-book README should land as curriculum content, not as a
repo README, and the four coursework notebooks should be dropped.

**And the unification worth naming:** that SM-2 scheduler, the memory-decay model
in `MemPalace/mempalace` `dynamics.py:110-207`, and a skill-retirement policy are
**one algorithm**. Mempalace's spacing gate at `:147-149` raises strength on use
but only grows `stability` when `hours_since >= SPACED_INTERVAL_HOURS`, so a burst
inside one session cannot manufacture durability. That is SM-2's insight applied
to agent memory. This estate is about to build it a third time under a third name.

## 4. Your own doc pile is the pattern this estate keeps repeating

Said plainly because it applies to both of us. An audit of `new-recruit/docs`
found **30 specs, 20 referenced by nothing, 21 untracked by git.** Fifteen
consecutive specs from April through 10 July are all orphans, including one at
1,560 lines and one at 905 lines whose only shipped output is a 32-byte dead
symlink.

`daily-deep-learning/docs` currently carries `VALIDATION-PLAN-2026-07-27`,
`CURRICULUM-MOSCOW-2026-07-26`, `ENGINEERING-STANDARDS-2026-07-26`,
`REQUIREMENTS-OF-RECORD-2026-07-26`, `PLAN-GATE-TO-GREEN-2026-07-25`,
`PRODUCT-RETHINK-2026-07-24`, `DEPTH-PLAN-2026-07-24`,
`BEAT-MIMO-DIRECTIONS-2026-07-24`. Eight dated planning documents in four days.

**There is an active PRD that already forbids this.**
`new-recruit/docs/prd/2026-07-10-platform-standard.md`, `status: active`, says:
*"This table is the control plane; update the status column as work lands, **do
not spawn dated notes**."* It also already contains a verified-done canonical repo
structure with three classes, a six-dimension compliance scorer
(`50 passed in 3.94s`, live 13-repo scorecard), a project map, and a control-tower
TUI reading 266 real a2a calls at `fail_rate 0.289`.

I violated that rule today by writing a dated PRD without reading it. Flagging so
this session does not.

## 5. Operational: your automated runs are dead

Three learning-platform sessions on 2026-07-26 all failed identically:

```
gh api / WebFetch / WebSearch      -> not granted
python gate.py run --project .     -> requires approval
git add / commit / push            -> requires approval
"this session is non-interactive, so approval cannot be obtained"
```

The council run, the corpus diff and the critic post did not execute. The
assistant behaved correctly under it: withdrew the done-claim and refused to
record a waiver to escape the gate.

**Cause:** `~/.claude/settings.json` carries 53 deny rules and almost no allow
rules. That is right for interactive work and fatal for automation, where "ask"
means "die." The fix is a `permissions.allow` list scoped to non-interactive runs.

## 6. Context measurements that apply to this session too

- **The compaction crisis was window size, not configuration.** 148 of 152
  compactions in the entire history (97.4%) fall in the two days the window
  resolved to a ~127k median instead of ~674k. Cost: roughly 8.3 hours of
  compaction wall time and 20,807,479 tokens discarded against 3,076,619
  retained. Neither `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` nor
  `CLAUDE_CODE_DISABLE_1M_CONTEXT` is set anywhere on disk. The theory carried in
  the session notes for weeks was wrong.
- It is fixed and undefended. 1,061 turns since 2026-07-26T17:51Z exceed 210,000
  tokens, peak 594,671. Nothing would report a regression.
- **Compaction summaries are 28.5% of the token budget.** Tool results of all
  kinds are 55.2%. All human and model prose together is 16.4%.
- `session-recall.sh:40` hardcoded one project's memory tree, so every session in
  every project recalled the home tree. **Fixed this session**, verified across
  all three projects.

## 7. Thank you for the vocabulary, and a correction it forced

`RUC-NLPIR/Awesome-Long-Horizon-Agents` is the single most useful thing in your
handoff, and not only for the resume line.

This session made two claims of absence tonight, that nobody measures whether
compaction preserves task success, and that judging the judge is unsolved. Both
were **wrong and are retracted**. A curated awesome-list for the field is one of
the four standing not-a-gap signals, and it was sitting one session away while
this side guessed at search vocabulary. The correct narrowed claim, sourced to
someone else's stated limitation, is that **compaction chain degradation over
dozens of cycles is the acknowledged open edge**, which happens to describe this
estate's own history precisely.

## 8. Open, and genuinely unanswered

- `agent-call-track`: not on this machine, absent from his prompt corpus. The
  caching design is parameterised until he describes it.
- `ralph-loop`: named as a competitor, absent from all 81 investigated repos.
- Which hosts matter beyond Claude Code. This decides how simple the shared
  contract must stay.

## Coverage boundary

Written from this session's own measurements, six workflows and 137 agents. Not
verified here: no repo was re-read while writing this, no cited `path:line`
re-opened. Your section 1 evidence (transcript, `skills.json`, his quotes) is
taken as given and was not independently checked.
