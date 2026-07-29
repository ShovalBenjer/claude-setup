# Handoff: numerical stack preference was invisible to general sessions

From the `new-recruit` voice-metrics work, 2026-07-29.

## What happened

I built an embedding and a corpus-statistics pipeline on NumPy plus the stdlib
`statistics` module. The operator's reaction: the Polars/Numba preference was
stated in past work and had rules for it.

He was right that it exists. It was written in:

- `dot-agents/skills/notebook/SKILL.md` — "polars, never pandas", `@jit` for hot
  numerical loops
- `dot-agents/skills/review/SKILL.md` — the pandas → polars swap table
- `dot-claude/agents/data-bureau.md`, `evidence-clerk.md`,
  `latent-systems-lab.md` — DuckDB/Polars for tabular state

**Every one of those loads only when that skill or agent is invoked.** I invoked
none of them, because the task did not look like "data science" or "review" from
the outside: it looked like building a text scorer. So the preference was
present in the repository and absent from the session.

`~/.claude/rules/` had 16 rules and none covered the numerical stack.

## The fix, already applied

New standing rule: `dot-claude/rules/numerical-stack.md`, synced to
`~/.claude/rules/`. Canonical and live are in sync at 17 rules.

Per `docs-control-plane` the rule is the single authoritative location; this
handoff does not restate it. Read the rule for the actual guidance.

The short version of *why it is a three-way split, not "use Polars"*: Polars
replaces pandas for tabular work, Numba replaces hot Python loops, and NumPy
stays for linear algebra. "Use Polars" is the wrong instruction for an
eigendecomposition, and a rule that said so would be ignored the first time it
was obviously wrong.

## Concrete debt in `~/.claude/skills/voice-metrics/`

Not fixed. Listed so it is not rediscovered.

| file | what it does now | should be |
| --- | --- | --- |
| `profiles.py` | `statistics.median` / `pstdev` over Python lists, ~35k messages, per metric | Polars expressions over a DataFrame; the percentile set is one `quantile` call per column |
| `voice_engine.py` `_counts()` | per-n-gram Python loop, roughly 7.8M iterations, memoised `blake2b` | the genuine `@njit` candidate, and the actual bottleneck |
| `voice_engine.py` `load_threads()` | `sqlite3` cursor into Python lists, filtered with a comprehension | Polars `read_database` or DuckDB over the SQLite file, filtered lazily |
| `voice_engine.py` PCA | `np.linalg.eigh` on a 2048×2048 covariance | **correct as-is.** Leave it in NumPy |

The measured behaviour of the skill (88% real-message pass rate, 0-12% impostor)
is unaffected by any of this: it is a performance and house-style debt, not a
correctness one. Do not let a rewrite silently change the scores; the validation
harness is `validate_scorer.py` and it should produce the same numbers after.

## The general lesson for the setup repo

A preference encoded only inside a skill is conditional on that skill being
recognised as relevant, and relevance is judged from the surface of the task.
Anything meant to hold across all sessions belongs in `dot-claude/rules/`.

Worth an audit: which other standing preferences currently live only in skill or
agent files, and would be equally invisible to a session that never triggers
them.

---

## System improvements from the design/redesign session (append 2026-07-29)

Concrete, evidence-backed findings for improving `claude-setup` itself.

### 1. Ship-gate scoping bug (real false positive, fix this)

`dot-claude/hooks/ship_gate_stop.py` fired on a quality claim while `cwd` was
`new-recruit`, but **every change in the session was in `daily-deep-learning`**.
The gate keys on cwd + quality-language, not on whether the current diff touches
the gated project. Fix: before firing, check `git diff --name-only` (and staged)
against the gated project's tracked scope; if no changed path belongs to the
gated tree, do not fire. Otherwise cross-repo work trips a gate for a project it
never touched.

### 2. Stop-hook tension has no arbiter

`completion_gate` / `ship_gate` (stop-and-verify) pull against the follow-through
gate (do not hand decisions back). A single turn can satisfy one and violate the
other, and this session bounced between them. Proposal: follow-through should
suppress when the turn explicitly names a genuine operator-only decision or an
external blocker (both were named and it still read as "handing back");
ship_gate should suppress per (1). Encode the precedence rather than letting
three independent hooks each veto.

### 3. Hooks that earned their keep this session (evidence to adopt the fuller set)

- `prior_art_gate` caught a real novelty overclaim ("nobody turns their own
  failures into named modes") that a search refuted (FAGEN, MAST, TRAIL,
  LangSmith). Correct fire.
- `completion_gate` repeatedly caught uncalibrated "done/verified" claims that
  turned out false on measurement (contrast 2.28:1, untested mobile).
These validate the recall's open "DECIDE" item: adopt the 6-hook enforcement
layer, not the 4-hook live set.

### 4. Promote a design-verify discipline (a skill or rule)

Designing-by-impression failed hard measurable checks this session; measuring
caught them. Codify a pre-"design done" gate:
- WCAG contrast calc on every fg/bg pair (hero number was 2.28:1, claimed pass).
- Responsive render + horizontal-overflow audit at 390/768/1024 (a clamp bug
  crowded the hero at 390; invisible until rendered).
- Color never the only signal (secondary ×/✓ encoding; 8% CVD).
- No glassmorphism on primary data containers.
- Reduced-motion gate; motion must mean state change, not decoration.
The tool for this already exists and should move to `claude-setup`:
`~/.claude/skills/case-ledger-post/shots.py` (overflow + clipped-in-scroll +
stuck-invisible + `--measure` ancestor-width + cache-disable).

### 5. Validated workflow templates worth codifying

- Judge-panel: N distinct-angle drafts -> adversarial voice + sharpness judges
  -> editor synthesis. Produced the article's analytical spine.
- Adversarial re-grade: independent readers + a skeptical critic caught a
  thesis-level integrity contradiction a structural rubric (26/30) missed. This
  is why the case-ledger rubric gained an 11th criterion (internal consistency).
- Art-direction fan-out: 4 committed identities + judges, then build the winner.
Save these as named scripts under `claude-setup/.claude/workflows/`.

### 6. Delegation gap (behavioural, for a rule/nudge)

Iterative visual exploration was authored serially in the main loop instead of
fanned out to parallel agents / the `product-studio` agent. A standing nudge:
for visual/variant exploration, prefer parallel agents over serial authoring.

### 7. Work cadence (operator feedback, now a standing rule)

Operator was dissatisfied with short 1-15 min converge-and-ask cycles: wants a
senior-worker cadence. Front-load all questions before running, then execute a
long autonomous stretch, self-handle blockers, and at the next checkpoint discuss
only blockers and decisions, not progress recaps or teaching-back. Encoded as
`dot-claude/rules/work-cadence.md` (synced live). This is the behavioural
counterpart to the follow-through hook's measured cost (~66 restart turns, ~940
min/week). Pairs with the hook-tension fix in item 2: the cadence rule tells the
model what to do; the hook precedence tells the gates when to allow it.

### 8. Lane A unused; Lane E (Content & Publishing) created

Operator confirmed 2026-07-29: **Lane A (Concierge) has never been used, not
once.** Marked in charters.md as a removal/rethink candidate — sessions open
straight into an implementation lane, so the RC/phone intake role it assumes has
never run. Decide: build the intake, fold it into another lane, or retire Lane A.

**Root cause of this whole session's lane drift:** the blog/social/case-study
work had no owning lane, so a large content effort (the-bench post to 26/30, a
syndication engine, per-platform hook strategy, two skills) ran silently under a
resume-engine (Lane C) session. Added **Lane E — Content & Publishing** to
charters.md to own the writing artifacts + syndication strategy, taking pipeline
plumbing from B, with posting gated to the operator and a PII/consent gate before
syndication.

**Follow-ups for B:** sync the three Lane-E skills from `~/.claude/skills` to
`claude-setup` canonical — `case-ledger-post`, `syndication-engine`,
`voice-metrics` (plus `case-ledger-post/shots.py`, the responsive/a11y audit tool
flagged in item 4). Right now they exist only in the live `~/.claude/skills`, not
in version control.

---

## Resume-engine session, evening of 2026-07-29 (append)

Lane C. Session `53bf3dee`. Nine commits on
`fix/approval-revoke-and-font-race`, gate PASS at each step (runs #70-#74,
`state/gate-runs.jsonl`). What matters here is not the commits: it is four
findings about the setup itself, three of which cost real quality this session.

### 9. The gate cannot tell a skip from a pass (adopt this fix)

Recorded as `L-2026-07-29-i`. A generator bug deleted every money figure from
all 12 shipped resumes and left NUL bytes behind. The four tests that assert
those claims **skipped** ("appears in no shipped HTML") instead of failing, so
pytest reported `89 passed, 4 skipped`, and the gate's `unit` domain read that
exit code as PASS. Corrupt artifacts, green gate.

Two concrete changes for `claude-setup`:

- `tools/gate/gate.py` should parse and record the skip count per run, and
  treat **an increase in skips against the previous recorded run for the same
  project** as a red domain. The signal here was `92 passed` becoming
  `89 passed, 4 skipped`, and nothing looked at it.
- House rule for oracle authors: a consistency check that may legitimately
  skip needs a companion integrity check that cannot. The local fix
  (`resumes_2026/tests/test_screening_fit.py::test_no_control_bytes_reach_any_shipped_html`)
  is the pattern: assert the artifact is well-formed, separately from
  asserting it agrees with the source.

### 10. Design-verify discipline applies to print artifacts, not just web

Item 4 above scoped this to web UI. This session shipped a resume redesign and
called it good **without rendering it once**; the operator's reaction was "ai
slop", and he was right. The render existed as a file the whole time. The rule
should read: no design claim without looking at the rendered output, whatever
the medium. The cheap mechanism on Windows is already in-repo: launch the
automation Chrome profile on 9224 and use `cdp_driver.py shot`.

Related environment note worth recording: the automation Chrome on 9224 does
not survive the session, and the launch invocation is not written down
anywhere except `.claude/commands/cdp.md` (which documents the **Edge/9223**
variant only). The Chrome/9224 line that works:
`chrome.exe --remote-debugging-port=9224 --user-data-dir=C:\Users\shova\.claude\automation-chrome-profile --no-first-run <url>`.

### 11. Confidentiality of measurements is a general rule, not a resume rule

The resumes carried log-exact internal values (an employer's lead count to the
unit, funnel percentages to the point). They read as machine-pasted because
they were, and they publish an employer's operational data on a document that
leaves the building. `~/.claude/rules/pii-handling.md` covers personal data and
says nothing about internal operational measurements.

Proposed rule text, for whoever owns the rules directory: a public artifact
carries **banded** internal measurements (counts rounded, percentages on a
five-grid, money in ranges); exact values live in the private evidence pack for
defence in an interview or review. Public, reproducible figures (named
benchmarks, public repos) stay exact and are exempt by name. The local
enforcement (`resumes_2026/tests/test_number_polish.py`) has the allowlist
pattern worth copying: each exemption carries its provenance inline.

### 12. Requirements-before-recommendation (behavioural, candidate rule)

I recommended sending an application for a role whose hard gates (5+ years,
MSc/PhD) the operator misses, without having fetched the posting's
requirements, and attached the generic resume variant when a company-specific
variant carrying first-party evidence about that exact employer existed. Both
were one tool call away.

The repo already ships `/requirement-anchor` for precisely this and it went
unused, which is the same failure shape as item 1 of this document: a
capability that exists but is conditional on someone recognising the task as
the kind that triggers it. Saved to project memory as
`feedback_requirements-before-recommendation`; worth promoting to a standing
rule if outbound recommendations are going to keep happening from any lane.

### Open, owned by the operator, unchanged by this session

Resume **content** authority (the manifest-versus-generator disagreement, 39
unbacked claims) and the layout thesis. The design remains a one-column
template with better type; the operator's standing critique is that a screening
document should be structured around the ten-second read, and that work is not
done.
