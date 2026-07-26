# Session handoff, 2026-07-26

Task: map the codebase, document every directory, and stand up a recurring
better-library audit, all under the grounded standard. Read this top to bottom
before touching the two new gate domains.

## Corrections to my own earlier claims in this session

Lead with these. Both were stated confidently earlier and both were wrong.

**1. The "74 phone numbers block the push" finding was wrong.** I reported that
three tracked corpus files held 74, 74 and 48 distinct phone numbers. Re-measured
with a hex-context filter, the counts are 17, 17 and 11, and **zero** are
Israeli-mobile-shaped. The 10-digit tokens all begin `17`, which makes them unix
epoch seconds; the 14-digit ones are `YYYYMMDDHHMMSS` date stamps. My regex had
been matching digit runs *inside sha256 hex strings*. Parsing
`features.csv`'s `filename` column properly across all 59 rows finds **0** rows
holding a mobile-shaped number.

The false-positive mode is worth remembering: `(?<!\d)\d{9,15}(?!\d)` matches
inside hex hashes. In `state/gate-runs.jsonl`, 55 of 65 matches were hash
substrings. Any digit-run PII check needs a hex-context exclusion.

**2. The push is not blocked.** The remote is
`github.com/ShovalBenjer/claude-setup`, `isPrivate: true`, and all three files
plus both handover files have been on it since commit `910dec2`, 2026-05-09.
Pushing the 18 local commits adds no exposure that is not already there.

**What is genuinely still true**, verified with the right instrument, counts only,
values never printed:

| file | finding |
|---|---|
| `research-papers/el-vadt/sales-agents-summary/HANDOVER.md` | 1 key-assignment shape and 1 `sk`-style token |
| `research-papers/docs-shoval/DEBUG_HANDOVER_20260112.md` | 1 email at `zonlineltd.com`, a third-party domain, not the operator's own |

Both tracked, both on the private remote since May. That is a real hygiene item
(rotate or rewrite history) but it is **not** a new blocker and **not** public.
Needs the operator's decision; do not rewrite history unilaterally.

## Wins, each with the check that backs it

**`codemap` domain PASSES.** `python tools/gate/gate.py run --project . --domain
codemap` prints `map clean: 361 dirs, all with a stated purpose,
docs/CODEBASE-MAP.md matches the repository`. 191 registry rows in
`docs/dir-purpose.txt`, zero undocumented directories, zero shadow rows, zero
stale rows. Purposes were written from the files, not the directory names: where a
tree is dead, vendored or a duplicate, its row says so.

**`git ls-files -z` fix, measured.** C-quoting non-ASCII paths was inventing five
directories whose names began with a literal quote character. They could never be
documented, and writing rows for them would have recorded the quoting bug as a
fact. Real undocumented count was 189, not 194.

**Staging before mapping, confirmed the hard way.** `git ls-files` sees only
tracked files, so the first map excluded `tools/map` and `docs/prior-art` because
they were still untracked. Staged, re-measured, 2 new undocumented appeared, rows
added, regenerated. A map written before `git add` is a map of nothing.

**17 prior-art records accepted**, up from 0. `python tools/map/codemap.py
prior-art --project .` accepts them and prints all 12 out-of-scope exclusions on
the failing path as well as the passing one.

**Three records recovered from a journal that a notification had truncated.**
`wf_e72d00fd-ba7` dropped 80,695 characters from its notification.
`~/.claude/projects/<proj>/<session>/subagents/workflows/<wf>/journal.jsonl` held
the full payloads, including `tools/gate`, `tools/review` and
`dot-claude/skills/prove-implementation/scripts`. Owed count fell 11 to 8 for
zero additional agent spend. **Read the journal before concluding a workflow
returned nothing.**

**63 tests pass**, `tools/gate/gate.py selftest` reaches its VERDICT line, and
commit `8d40794` carries the lot.

## Failures

**The weekly usage limit destroyed an 11-agent workflow.** `wf_4f1dbc88-dbb`
returned `{"records":[]}` with `agents_done 0, agents_error 11`, every failure
"You've hit your weekly limit", after burning 399,947 subagent tokens and 80 tool
uses. Nothing cached, so a resume re-runs from scratch. **A large fan-out late in
a session risks total loss; check remaining budget before spending 400k on one
barrier.**

**`prior_art` still FAILS**, by design, on 8 components: `dot-claude/bin` (3302),
`dot-claude/hooks` (791), `tools/audit` (1417), `tools/bus` (857), `tools/dolt`
(787), `tools/openrouter` (461), `tools/skilleval` (578), `tools/snapshot` (826).
That is the check working, not a regression.

**My commit swept in two files my message does not mention.**
`state/compact-log.md` (+1060) and `state/gate-runs.jsonl` were unstaged when I
checked and staged by the time I committed, most likely by a parallel session or a
hook. Both are legitimately tracked state and neither carries PII (checked). I did
not amend, because amending could clobber a concurrent session's staged work.
`git diff --cached --name-only` immediately before committing is the guard.

**Two records carry weaker evidence than the rest.** `tools/gate.json` and
`tools/review.json` came from a run whose schema asked for no `evidence` field.
Their evidence strings begin `DERIVED, not a separate evidence pass` and quote the
record's own citations. Re-verify first-hand before leaning on either.

**24 em dashes in `docs/CODEBASE-MAP.md`**, all from skills' own `SKILL.md`
frontmatter descriptions, zero from the 191 registry rows. A pre-existing
house-rule violation the map surfaced for the first time. Eight are
`dot-agents`/`dot-claude` duplicate pairs, so the edits must be coordinated.

## Pointers for the next agent

Cheap and unblocked, do first:

1. Write the 8 owed prior-art records. Constrain `verdict` with a JSON-Schema
   `enum` and say "the exact path assigned to you, nothing else": one agent
   returned a 244-character essay as its `component`, which the path validator
   rejects.
2. A workflow script cannot call `Date.now()`. Agents cannot stamp `reviewed` or
   `recheck_after`; the caller stamps them after the workflow returns. See
   `writerecs.py` / `writerecs2.py` in this session's scratchpad.
3. Finish the corpus iteration: 123 of 173 `research-papers/` files done.
4. State to the operator the reading I acted on but never stated: "minimal LOC
   documented (no commenting pep 8)" was read as terse one-line documentation in
   `docs/` and in generated maps, not inflated in-code comment ceremony.

Traps that cost time here:

- `codemap.py check --json` returns `dirs` as an **int** count. The list of
  undocumented paths is under `undocumented`. `len(d['dirs'])` raises TypeError.
- An agent-returned dir row is not a registry row. Of 123 returned, 41 had to be
  dropped: rows for files, for untracked cache dirs, for self-documenting dirs,
  and for a different repository entirely.
- "claude-sonnet-5 is temporarily unavailable, so auto mode cannot determine the
  safety of Bash" is a transient classifier outage. Retry the identical command.

Needs the operator's word: the two credential/PII hygiene items above; the three
safe corpus deletions (two `sources.json` that are exactly `[]`, one
byte-identical duplicate prompt); whether to push the 18 local commits, which is
now a plain yes-or-no with no exposure argument against it.
