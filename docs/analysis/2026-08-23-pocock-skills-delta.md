# mattpocock/skills: what we are not using, and why, 2026-08-23

Operator ask: iterate over Matt Pocock's skills and say what we are not using and why,
with https://www.youtube.com/watch?v=0oXOOlqVu5M as context. That video is Theo's review
of the repo ("So I tried Matt's skills...", t3.gg, read from YouTube's oembed endpoint);
its transcript was not fetched (the Chrome-to-Gemini drive the youtube-distill skill needs
was not exercised in this pass), so nothing below leans on it. The repo was read directly:
36 SKILL.md frontmatters at HEAD (pushed 2026-08-21, 233k stars, MIT), diffed against the
80-skill live tree and against the full teardown this repo already did on 2026-08-01
(`docs/analysis/archive/2026-08-01-pocock-skills-teardown.md`, v1.1.0, 38 skills then).

## What we already run from him (so the delta is honest)

Imported on 08-01 and live in `~/.claude/skills` today: `writing-great-skills` (his
writing-for-agents, MIT attribution), `skillmap` (our router answer to his index), and the
`disable-model-invocation` pattern (5 skills flipped). Same-name or same-function
equivalents already installed: grill-me, code-review/review, improve-codebase-architecture,
domain-model + ubiquitous-language, to-issues (his to-tickets), to-prd (his to-spec),
github-triage (his triage), deep-research + advisor (his research), tdd via the
tdd-enforcement rule + testing-pyramid + tdd-slice-planner agent, end-session (his
handoff/claude-handoff), wayfinder, learn-on-demand (his teach), /loop native (his
loop-me), and the bash rm/push guards plus hookgate (his git-guardrails-claude-code).

## Not using: adopt candidates, each with the incident that argues for it

| his skill | gap here | the evidence it would have fired |
|---|---|---|
| `wait-what` ("Stop. That last message did not land: re-pitch it.") | explain-simply exists but triggers on a request for explanation; nothing owns the one-word interrupt that says the previous answer failed | the operator typed exactly this three times in the ticket corpus: "explain to me more simply you wrote a lot and i dont follow along" (08-23), "what left you tlaking to high for me" (07-31), "note that everything you did here i dont understand" (08-12). Those are wait-what invocations spelled out by hand. |
| `to-questionnaire` (turn a decision you cannot answer into a questionnaire for someone else) | accepting-architectures demands block-by-block operator decisions; no skill renders open blocks as a fillable form | the open-model plan has waited since 08-12 on "five operator blocks A to E"; a questionnaire is the shape that gets five answers in one sitting instead of five sessions |
| `wizard` (generate an interactive bash script walking a human through steps only they can perform) | NEEDS OPERATOR moments are handed over as prose | today alone produced three: the sudoers line, the Todoist OAuth, the GitHub billing fix. Each was a paragraph the operator had to parse; a generated `wizard.sh` with pause-and-verify steps is strictly less reading |
| `resolving-merge-conflicts` | no skill owns an in-progress conflict; the landing-beats-asking memory is advice, not a procedure | PR #68 hit merge conflicts five times in one evening (08-12); prompt-tickets.jsonl carries 25 chain breaks from exactly these merges |

## Not using: concepts worth stealing, no import

- `diagnosing-bugs` (hypothesis-loop with a HITL script): prove-implementation covers
  cause-uncertain fixes but has no diagnosis loop shape. Steal the loop structure if a
  debugging skill is ever written; his HITL template is 50 lines.
- `prototype` (throwaway build to answer a design question): /diverge samples candidates
  on paper; his position is that some questions are only answered by a disposable build.
  Compatible with prove-implementation's evidence bar; adopt the concept, not the skill.
- `codebase-design` (DESIGN-IT-TWICE, deep-modules vocabulary): the vocabulary layer
  under improve-codebase-architecture, which we imported without it.

## Not using: deliberate leaves, with the reason on record

- `writing-beats` / `writing-fragments` / `writing-shape`: our outbound writing runs on
  voice-metrics, an idiolect fitted to the operator (n=35,472 messages). His writing
  skills encode his voice; importing them would fight the fitted profile, which is the
  one asset nobody else's setup has.
- `grilling` (the model-invoked twin of grill-me): rejected by his own economics, which
  the 08-01 teardown adopted; we keep grill-me user-only and pay zero standing context.
- `implement` / `implement-spec` / `setup-matt-pocock-skills`: his execution loop and
  installer; ours is the forge loop plus the gate, and a second execution protocol is
  drift, not coverage.
- `migrate-to-shoehorn`, `setup-pre-commit` (Husky), `setup-ts-deep-modules`
  (dependency-cruiser), `scaffold-exercises`: TypeScript-ecosystem tooling for stacks we
  touch only in dashboard/web; coverage-enforcer and refactor-pre-push own the pre-push
  seam repo-wide, and a JS-only second hook chain would split enforcement.
- `ask-matt` (persona QA over his own corpus): the pattern is real and we already run it
  in the other direction as codex-call and the review panel personas.

## The finding that outranks any single skill

The 08-01 teardown named five follow-ups: description pruning (ours averaged 308 chars to
his 116), the in-progress/deprecated bucket split, the rules negation audit, wayfinder-
onto-Zion, and a router-freshness check in pointers.py. As of today zero of five have
happened, while the repo we measured moved (38 skills to 36, three new writing skills, a
wizard template, changesets discipline). That is the absorption-stops-at-analysis pattern
the WhatsApp sweep found this morning wearing a different shirt: reading is done same-day,
verdicts land in the ledger, and the acted-on fraction is what actually decays. The four
adopt candidates above are small precisely so this pass can break that pattern; wait-what
is one file.

Ledger: `state/external-repos.jsonl` row for mattpocock/skills moves untriaged ->
adopt-patterns with this document as the why. Issue #90 box ticked; #93 holds the operator
prompts that asked for this.
