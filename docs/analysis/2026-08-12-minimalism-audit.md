# Minimalism audit: ponytail + caveman across code, prose, and config

Date: 2026-08-12. Read-only findings plus one applied cut. Point-in-time `analysis/`
scan. Two independent passes cross-checked: a review-board ponytail-audit and a
ledger-verified sighting list from the parallel CLI/permissions session (its evidence
is `state/*.jsonl` and PR #66 landed today).

## Headline: the code is not the bloat

Both passes spot-checked `tools/*.py` (gate.py 1,654 lines, panel.py 1,386, bus.py
1,243) for the ponytail lens: reinvented stdlib, speculative abstraction, decorative
banner comments, docstrings restating signatures. Came back clean. argparse used
properly, hash-chain uses stdlib `hashlib` directly, banners are structural section
markers. A full-repo grep for reinvented retry/config/deepcopy patterns was empty. So
the "caveman optimization on code writing" lens has almost nothing to cut. The bloat is
entirely (a) per-session prose tax and (b) dead/unused config.

## Per-session token tax (read every session, measured)

| Surface | Words/session | Recoverable | Risk |
|---|---|---|---|
| 26 rule files (`dot-claude/rules/`) | ~11,300 | 30-40% | Medium: narrative is deliberate audit trail |
| 81 skill `description:` frontmatter | 3,437 | ~60% | Low: routing metadata, no history |

### Applied cut (1 of 81): ui-ux-pro-max

Description went 119 -> 62 words. Every routing keyword kept (stack names, style names,
action verbs); the enumerated catalogs (`50+ styles, 161 palettes, 57 pairings...`) were
already restated verbatim in the body (line 8), so removing them from the loaded line is
lossless for routing. A batch pass over the 14 next-fattest is in flight with the same
rule: keep sentence-one + trigger keywords, drop catalogs that are also in the body,
never drop a unique trigger word.

MEASURED RESULT (not estimated): compressing the 15 fattest descriptions moved the
81-file total from 3,437 to 3,271 words, a 166-word cut, with zero broken frontmatter and
every trigger phrase preserved (verified by re-parsing all 81 files). This is well short
of the ~1,000-word cut first estimated: the fat concentrates less than assumed, and
several targets (case-ledger-post, voice-metrics, syndication-engine) held their bulk in
the body, not the description, so there was little to cut there. A subagent self-reported
larger per-file cuts (e.g. blonde-designer 119->51); re-measurement showed 119->66, so the
166-word total is the trustworthy figure, not the per-file report. The largest remaining
offender, jira-read at 120 words, was outside the batch; the long tail is fatter than
scoped, but chasing it risks mis-cutting a routing trigger for diminishing return.

## The rules-tree tension (why NOT to caveman these blindly)

`model-selection.md` (958w, the largest rule) states its own governing principle: closing
a contradiction by rewriting the losing side is how a rule stops describing anything. The
incident narratives in `the-loop-may-act`, `accepting-architectures`, `calibrated-claims`
are the audit trail that stops a future session silently re-breaking the rule. Blind
compression deletes the "why" and reintroduces the mistakes these files exist to prevent.

Safe structural move (not deletion): keep the live rule at the top of each file, relocate
the dated incident history to a `docs/adr/` changelog block below it. Same words on disk,
smaller per-turn read. Estimated ~30% off the rules tax with zero history loss. This is a
per-file operator decision (accepting-architectures: block by block), not a batch job.

## Placement defects (global rules that should be project-scoped)

- `jira-comment-drafting.md` (632w): one Jira workspace's comment tone.
- `foundry-deployment-per-project.md` (657w): one Azure Foundry account's naming.

Both sit in the GLOBAL rules tree, so every session in every repo pays 1,289 words for
context that only fires in a Jira or Azure task. Move to the consuming repos' own
`CLAUDE.md`. Caught independently by both passes. Loses nothing: the content only applies
when that context is live.

## Dead / unused config (the only real "code" cut)

- 12 hook files in `dot-claude/hooks/` are one-line stubs pointing at `/home/shovalbe/`
  (a home absent on this machine). Confirmed dead. `tools/audit/pointers.py scan` is the
  existing oracle; run it for the exact list before deleting.
- 23 of 29 hooks are unwired in live `settings.json`. Some legitimately superseded, some
  orphaned; needs the pointers.py output to separate the two.
- `tools/intent/capture_turn.py` (198 lines): its enrichment import has failed silently on
  all 401 recorded turns (CLI-peer finding, verify against `state/`). Runs on every
  UserPromptSubmit, produces nothing.
- `prompt-router.sh`: 13-line shim onto an absent module (`best_practices.sqlite3`).
- `intent-control-plane/repo_health.py`: enforces file/func/class budgets, referenced by
  no pyproject script, gate, or CI. Runs nowhere.

## The punchline for this exact task

Seven overlapping minimalism skills, each with ZERO lifetime uses per `state/skill-use.jsonl`:
ponytail, ponytail-audit, ponytail-help, ponytail-review, code-simplifier, cleanup-crew,
plus the built-in `/simplify`. The compression pass's cleanest first act is to collapse
six of its own siblings into one. Catalog-wide: 80 skills installed, 21 ever used since
logging began 2026-07-27; 18 of 23 personas never spawned. The never-used lists are the
deletion shortlist. (PR #66, landed today, did the census and initial rewiring.)

## Ranked next actions

1. DONE: compressed the 15 fattest skill descriptions. Measured 166 words/session saved
   (3,437->3,271), zero risk, frontmatter verified intact. Less than the ~1,000 first
   estimated; the fat was shallower than assumed.
2. Collapse the 7 zero-use minimalism skills to 1 (removes 6, all unused).
3. Run `tools/audit/pointers.py scan`, delete the 12 confirmed stub hooks.
4. Move the 2 project-specific rules out of the global tree (1,289 words/session in this repo).
5. OPERATOR-DECISION, per file: relocate rule-file incident history to docs/adr/ (~30% of the 11,300-word rules tax). Not a batch job; each file's history is deliberate.

Housekeeping: `docs/sagemaker-hyperpod.md` (a stray untracked AWS-docs fetch at docs root)
should be removed from the main checkout; the repo's delete-guard blocks a worktree rm and
it is outside this worktree.
