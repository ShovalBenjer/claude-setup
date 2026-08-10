# COMMIT / PR / CODE REVIEW upgrade spec: github.com/ShovalBenjer

Scope: 32 repos (27 public, 5 private). Everything below marked **[V]** was executed read-only this session; **[I]** is inference and says what would confirm it.

---

## 1. Broken, blocked, and newly found

| # | Finding | Status |
|---|---|---|
| B1 | **Zero enforcement on all 27 public repos.** Not "protection off" but "no ruleset object exists": `repos/ShovalBenjer/sqltok/rulesets` returns `[]`, and `branches/<default>/protection` returns 404 on all 27. | [V] |
| B2 | **Private repos are unprotectable at $0.** Both `/branches/main/protection` AND `/rulesets` return 403 `"Upgrade to GitHub Pro or make this repository public"` on `claude-setup`. Rulesets are not a free workaround for private repos. | [V] |
| B3 | **Check names are heterogeneous, so a shared required-checks list is impossible today.** Real check-run names: `lint-and-test (3.12)` (sqltok), `test (3.11)` (agenteval-bench), `test (3.13)` (mcp-guard), `MSRV (1.85)` / `cargo-deny (licenses/bans/sources)` / `fuzz smoke (nightly, non-blocking)` (protobuf-fuzz-guard). Matrix legs suffix the job name, so adding a Python version silently breaks any pinned context. | [V] |
| B4 | **Three default branches are red right now.** `sqltok/main` = failure,failure (failing since 2026-07-23). `argmax_solution/main` = 3 failures. `agenteval-bench/main` = mixed. Turning on required checks before fixing these makes those repos unmergeable. | [V] |
| B5 | **Two repos run no CI on their default branch at all.** `matchiq/main` and `altius-financial-analysis/main` return zero check-runs. matchiq's CI only ever ran on `pull_request` for `gt/*` branches. | [V] |
| B6 | **The `eval` false positive was patched but the class is still live.** panel.py:218-231 now requires `eval(` with no space. I built a differential harness against the repo's own corpus using panel.py's real `run_local` filtering: **3 HIGH `sql-concat` findings on a scraped LinkedIn job description.** Exact mechanism at `archive/job-data/scraped_linkedin_jobs.json:472`: the prose `"Maintain and update tasks in tools like Monday"` supplies `UPDATE`, the unbounded `.*` spans ~900 characters of English, and `"2+ years of experience"` supplies `\+\s*\w+`. Same defect class as `eval`, different pattern, still blocking. | [V] |
| B7 | **The `sql-concat` pattern misses the most common real Python SQL injection.** My true-positive suite found `cur.execute(f"SELECT * FROM t WHERE a={x}")` is **not** matched by the shipped pattern, because it requires `f['\"]` to appear *after* the SQL keyword and in an f-string it appears before. The pattern is simultaneously too loose on prose and too tight on the real defect. | [V] |
| B8 | **Only one reviewer, one model family.** Every repo's `claude-code-review.yml` runs `claude-sonnet-5` alone. Their own standing rule ("same diff to each reviewer, then an agreement gate; a second reviewer must never just read the first one's summary") is unimplemented. | [V] |
| B9 | **The review prompt is fixed and identical across all repos.** Directly contradicts their own written position that fixed eval prompts are worthless because models detect evaluation. | [V] |
| U1 | `actor_id: 5` = Admin repository role in `bypass_actors`. Cannot be confirmed without a write. Verification command in section 6. | [I] |
| U2 | `enforcement: "evaluate"` (dry-run) is believed Enterprise-only for repo-level rulesets. The rollout below does not depend on it. | [I] |

**Already correct, do not rebuild:** `claude-code-review.yml` fires on `synchronize` with `concurrency.cancel-in-progress: true`, which is exactly their "every push to a PR starts a fresh review" rule, implemented properly. [V] `CLAUDE_CODE_OAUTH_TOKEN` exists in all 10 repos sampled. [V]

---

## 2. Core design decision: one normalizing check

B3 is the blocker that makes the naive plan fail. Do **not** pin `test (3.11)` in a ruleset. Add one non-matrix aggregator job named `gate` to every repo. The ruleset then requires exactly two contexts everywhere, and per-repo CI variation is absorbed below the enforcement boundary.

`~DEFAULT_BRANCH` handles the `main`/`master` split (`protobuf-fuzz-guard`, `crowd-transcribe`, and private `phone-social-reminder` are `master`). [V]

### `.github/workflows/gate.yml` (identical in all 27 repos)

```yaml
name: gate
on:
  pull_request:
  push:
    branches: [main, master]
concurrency:
  group: gate-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  ship-gate:
    name: gate                      # THE required context. Never a matrix job.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 0 }
      - uses: ShovalBenjer/ship-gate@v1     # see section 3
        with:
          project: .
          domains: build,unit,types,security,docs,perf
```

### Aggregating existing CI instead (for repos whose ci.yml already does the work)

Append to the existing `ci.yml`, do not rewrite it:

```yaml
  gate:
    name: gate
    if: always()
    needs: [test]          # or [lint-and-test], or [test, clippy, rustfmt, cargo-deny]
    runs-on: ubuntu-latest
    steps:
      - name: aggregate
        run: |
          echo "needs.test.result=${{ needs.test.result }}"
          [ "${{ needs.test.result }}" = "success" ] || exit 1
```

`needs.<job>.result` is already the aggregate across all matrix legs, so this survives adding or dropping a Python version.

---

## 3. Prerequisite: extract the gate into a public repo

`gate.py` and `panel.py` live in `C:\Users\shova\claude-setup\tools\`, which is private, and a public repo's CI cannot clone it without a PAT. [V]

Create **public** `ShovalBenjer/ship-gate` containing `tools/gate/gate.py`, `tools/review/panel.py`, and an `action.yml`. This is also the "package the consolidated system as your own distribution" recommendation from the tooling review, applied to the one component that CI structurally requires.

Before publishing, run their own secret scan on exactly those two files and confirm zero hits. `gate.py` carries `SECRET_PATTERNS` and a `PUBLIC_TEST_VECTORS` allowlist; publishing the detector is fine, publishing the corpus is not. This is the one step in this spec that needs explicit per-action approval, because it is third-party publication.

---

## 4. Ship gate to CI mapping

The `pipeline` domain (`ci_runs_gate`) exists to catch local-green diverging from merged-green. The mapping closes that loop by making CI run the same `gate.py`, not a re-implementation.

| Local domain | CI home | Contract |
|---|---|---|
| `build` | `gate` job | `gate.py` runs the contract's `cmd` |
| `unit` | `gate` job | same |
| `types` | `gate` job | same |
| `security` | `gate` job | builtin `secret_scan`, keeps the `PUBLIC_TEST_VECTORS` allowlist |
| `docs` | `gate` job | builtin `docs_touched`, `base` set to `origin/${{ github.base_ref }}` |
| `perf` | `gate` job | `required: false`, non-blocking |
| `pipeline` | **satisfied by existence of the `gate` check** | This is the domain that turns green *because* of this rollout. Remove its waiver only after phase 1 lands. |
| `review` | **separate `review` check** | Different owner, different failure mode. Do not fold into `gate`. |
| `e2e` | not required in CI yet | Currently `na_reason` in `new-recruit`. For repos with a served app, this becomes a third context later, not now. |
| `a11y_ux` | not required in CI yet | Same. |

Two required contexts total: `gate` and `review`. `perf`, `e2e`, `a11y_ux` stay advisory until they have a real instrument.

---

## 5. The ruleset JSON

Two files. Phase 3 cannot block a normal push; phase 4 can.

### `ruleset-phase3.json` (safe, cannot brick anything)

```json
{
  "name": "default-branch-baseline",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" }
  ]
}
```

This blocks only branch deletion and force-push. Both are already on their per-action-approval list, so this ruleset enforces a rule they already hold. Ordinary `git push` is unaffected.

### `ruleset-phase4.json` (the real gate)

```json
{
  "name": "default-branch-gate",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }
  ],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": true,
        "required_status_checks": [
          { "context": "gate",   "integration_id": 15368 },
          { "context": "review", "integration_id": 15368 }
        ]
      }
    }
  ]
}
```

**Four fields are load-bearing against bricking. Do not "tighten" them:**

- `required_approving_review_count: 0`. **GitHub does not permit approving your own pull request.** On a solo account any value above 0 makes every PR permanently unmergeable. This is the single highest-probability way to brick this account.
- `bypass_actors` with the admin role. Preserves the emergency direct push while the habit forms. Removed in phase 5, per repo, only after that repo has merged real PRs.
- `strict_required_status_checks_policy: false`. `true` forces every branch up to date with the default branch before merge, which on a solo workflow means re-running CI on every merge of anything else. Turn on later if ever.
- `do_not_enforce_on_create: true`. Prevents the ruleset from rejecting branch creation.

`integration_id: 15368` is the GitHub Actions app, confirmed empirically from a live check-run payload on `mcp-guard`, not from memory. [V]

---

## 6. Rollout order

Every phase is reversible, and each ends with an observable check.

### Phase 0: publish the gate (needs approval, one time)
Create public `ShovalBenjer/ship-gate`. Verify:
```bash
gh api repos/ShovalBenjer/ship-gate --jq '{visibility, default_branch}'
```

### Phase 1: add workflows, enforce nothing
Add `gate.yml` and the two-reviewer `review.yml` (section 7) to all 27 public repos via PR. No ruleset exists yet, so a broken workflow cannot block anything.

Confirm both checks are actually reporting under the exact required names:
```bash
for r in $(gh api "users/ShovalBenjer/repos?per_page=100&type=owner" --jq '.[].name'); do
  db=$(gh api repos/ShovalBenjer/$r --jq .default_branch)
  echo -n "$r ($db): "
  gh api "repos/ShovalBenjer/$r/commits/$db/check-runs" \
    --jq '[.check_runs[] | select(.name=="gate" or .name=="review") | .name+"="+(.conclusion//"pending")] | join(" ")'
done
```
Do not advance until every repo prints both `gate=` and `review=`. A name mismatch here is the failure that phase 4 would otherwise turn into a lockout.

### Phase 2: fix the red branches
`sqltok`, `argmax_solution`, `agenteval-bench` (B4), and give `matchiq` + `altius-financial-analysis` a push trigger (B5). Required checks against a branch that has never been green is the second most likely way to brick this.

### Phase 3: apply the baseline ruleset (cannot block a push)
```bash
for r in $(gh api "users/ShovalBenjer/repos?per_page=100&type=owner" --jq '.[] | select(.private==false) | .name'); do
  echo "== $r"
  gh api --method POST "repos/ShovalBenjer/$r/rulesets" --input ruleset-phase3.json --jq '.id'
done
```

### Phase 4: pilot the real gate on ONE repo first
```bash
gh api --method POST repos/ShovalBenjer/mcp-guard/rulesets --input ruleset-phase4.json --jq '.id'
```
`mcp-guard` is the pilot because its default branch is fully green (3/3 success). [V]

Then verify the bypass actually works, which resolves U1:
```bash
gh api repos/ShovalBenjer/mcp-guard/rulesets/<ID> --jq '.bypass_actors'
gh api repos/ShovalBenjer/mcp-guard/rules/branch/main --jq '[.[].type]'
git -C <clone> commit --allow-empty -m "probe: ruleset bypass" && git push
```
If the push is rejected, `actor_id: 5` is not admin. Fix by reading the effective rules above and adjusting, or delete the ruleset (escape hatch below).

### Phase 5: roll out to the remaining 26, then drop bypass
Only after the pilot merges one real PR end to end. Drop `bypass_actors` per repo, not globally.

### Escape hatch, valid at every phase
A repository admin can always delete a ruleset via API. This is guaranteed and does not depend on U1:
```bash
gh api "repos/ShovalBenjer/<repo>/rulesets" --jq '.[] | [.id, .name, .enforcement] | @tsv'
gh api --method DELETE "repos/ShovalBenjer/<repo>/rulesets/<ID>"
```

---

## 7. Fixing the fixed-pattern reviewer

Their own position applied to their own tool: the panel is a fixed oracle, and B6 plus B7 are what fixed oracles do. The 2026-07-26 `eval` patch fixed one instance. Patching patterns one at a time is exactly the "small patch reported as done" loop they rejected. Five layers, in dependency order.

### 7.1 Bound the spans (immediate, but explicitly not sufficient)

Replace `sql-concat` at panel.py:211-213:

```python
("sql-concat", HIGH, [],
 r"(?i)(?:\b(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^;\n]{0,80}?"
 r"(?:\+\s*\w+|\$\{|%\s*\(|%s['\"]\s*%|\.format\(|f['\"])"
 r"|f['\"][^'\"\n]{0,60}?\b(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^'\"\n]{0,120}?\{\w)",
 "SQL assembled from variables instead of bound parameters"),
```

Measured on this repo, differential against the old pattern [V]:

| | old | new |
|---|---|---|
| True positives caught (6-case suite incl. f-string, `%`, `.format`, template literal) | 3/6 | **6/6** |
| Parameterized-query true negatives | 2/2 | 2/2 |
| False positives, 900-file corpus (json/yml/html/py) | 3 HIGH | **0** |

**Residual, stated rather than discovered later:** a *compressed* prose line still matches. `"Maintain and update tasks in tools like Monday. Requirements: 2+ years"` fits inside the 80-character bound and fires. The real corpus does not contain that shape, but the class is not dead. This is the proof that 7.1 is a mitigation and 7.2 is the fix.

### 7.2 Kill the class: never run code patterns over prose spans

The `lang == "md"` exclusion at panel.py:411-420 is one file extension. The original `eval` false positive was in **HTML**, and B6 is in **JSON**. Neither is excluded.

Add a prose-span guard before pattern evaluation:

```python
PROSE_HINT = re.compile(r"[A-Za-z]{2,}\s+[A-Za-z]{2,}\s+[A-Za-z]{2,}")

def is_prose_span(text: str) -> bool:
    """A span with many words, high alpha ratio, and no operator syntax is English."""
    s = text.strip()
    if len(s) < 40:
        return False
    words = s.split()
    if len(words) < 12:
        return False
    alpha = sum(c.isalpha() or c.isspace() for c in s) / len(s)
    ops = sum(s.count(c) for c in ";{}=<>|&")
    return alpha > 0.80 and ops <= 2 and bool(PROSE_HINT.search(s))
```

Applied at three levels:
- **`.py` / `.ts` / `.js`:** use stdlib `tokenize` for Python and skip `COMMENT` and `STRING` tokens outright. This is exact, not heuristic, and it is the correct instrument.
- **`.json` / `.yaml` / `.html` / `.toml`:** run `is_prose_span` on the matched region. A HIGH that matches only inside a prose span is **demoted to LOW "possible"**, never dropped silently, and the demotion is written into the artifact.
- Record every demotion in the artifact so a suppression is a named exception, matching the pattern `secret_scan` already uses for `PUBLIC_TEST_VECTORS`.

### 7.3 Self-calibration: make the oracle measured, not fixed

Add `panel.py precision --corpus <ref>`. It runs every registered check against merged history, which by definition shipped, and records a per-pattern false-positive rate in the artifact. Any pattern above threshold auto-demotes from blocking to advisory until someone fixes it. This is the operational form of "fixed evals are worthless": the panel stops asserting its own accuracy and starts measuring it.

### 7.4 Adversary stage: mutation, per builder to reviewer to adversary

Add `panel.py mutants`. For each of the 32 checks, generate synthetic true positives and assert the panel catches each. A check catching none of its own mutants is dead code.

This is not speculative. Their own comment at panel.py:269-272 records that `unawaited` "matched nothing for its whole life and the selftest is what said so." B7 is a second instance found this session by exactly this method. A standing mutation job finds the rest without being asked.

### 7.5 Two blind reviewers plus an agreement gate

Fixes B8 and B9. `review.yml`, three jobs, artifact-isolated so neither reviewer can read the other:

```yaml
name: review
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
concurrency:
  group: review-${{ github.event.pull_request.number }}
  cancel-in-progress: true      # keeps "@claude review always" behaviour

jobs:
  reviewer-deterministic:       # family A: no model, cannot be socially engineered
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 0 }
      - run: python tools/review/panel.py run --project . --base origin/${{ github.base_ref }}
      - uses: actions/upload-artifact@v4
        with: { name: review-a, path: state/reviews/ }

  reviewer-model:               # family B: never sees review-a
    runs-on: ubuntu-latest
    permissions: { contents: read, pull-requests: write, id-token: write }
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 0 }
      - id: seed                # 7.5b randomisation, per their own written position
        run: |
          echo "n=$(( ${{ github.run_id }} % 4 ))" >> $GITHUB_OUTPUT
      - uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          track_progress: true
          prompt_file: .github/review-prompts/${{ steps.seed.outputs.n }}.md
      - uses: actions/upload-artifact@v4
        with: { name: review-b, path: state/reviews/ }

  review:                       # THE required context
    name: review
    needs: [reviewer-deterministic, reviewer-model]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/download-artifact@v4
        with: { path: /tmp/reviews }
      - run: python tools/review/agree.py --a /tmp/reviews/review-a --b /tmp/reviews/review-b
```

**Agreement gate semantics** (`agree.py`), which is the part that matters:

- Both pass, no HIGH from either: **pass**.
- Either reports a HIGH: **fail**.
- The two disagree on a HIGH: **fail and label `review-disagreement`**. Disagreement escalates, it never auto-passes. A gate that resolves disagreement by picking the lenient reviewer is not a gate.
- Either reviewer job errored: **fail**, with the reason named. This mirrors `ship_gate_stop.py`'s own stated principle that a guard which cannot run must announce it, never silently pass.

**7.5b randomisation.** Four prompt variants in `.github/review-prompts/{0,1,2,3}.md`, differing in phrasing and in the order of the five focus areas, selected by `run_id % 4`. Same review contract, different surface, so a diff cannot be tuned against a single fixed prompt.

**Note on the third reviewer.** `panel.py --allow-external` (OpenRouter free tier) is a genuine third family at $0, but it is barred for `new-recruit` and any repo carrying resumes or candidate data. B6 landed in `archive/job-data/scraped_linkedin_jobs.json`, which is exactly that data. Enable external review per repo, never account-wide, and never on repos in the hiring lane.

---

## 8. The unprotectable private repos

Five repos, all 403 on both enforcement APIs: `claude-setup`, `Resonant-Harmonics-Agents`, `claude-memes-skills`, `oren-roast-hq`, `phone-social-reminder` (`master`). [V]

There is no server-side enforcement at $0. Say so plainly rather than shipping something that looks like a gate.

**Rejected:** making `claude-setup` public. It is the repo their own rules name as holding `.credentials.json`, `.setup-token-tmp`, `.token-flow/oauth.png`, and `history.jsonl`. Publishing it to obtain free rulesets trades a real secret for a process control.

**Rejected:** an Actions workflow that auto-reverts a bad push to main. Revert and force-push are on their explicit per-action-approval list, and an unattended agent performing them is exactly the "stop guard" they rejected.

**Recommended, honest, $0: detection plus a steering redirect, labelled as detection.**

```yaml
# .github/workflows/gate.yml, private-repo variant. Append to the shared file.
  guard:
    if: github.event_name == 'push' && github.ref == format('refs/heads/{0}', github.event.repository.default_branch)
    needs: [ship-gate]
    if: always()
    runs-on: ubuntu-latest
    permissions: { contents: read, issues: write }
    steps:
      - if: needs.ship-gate.result != 'success'
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner, repo: context.repo.repo,
              title: `gate red on ${context.sha.slice(0,12)} (direct push to default branch)`,
              labels: ['gate-red'],
              body: `Direct push bypassed review. Gate result: ${{ needs.ship-gate.result }}\nRun: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`
            })
```

Paired with a local pre-push hook that **redirects rather than blocks**, matching their "no stop guards, redirects that keep it flowing" rule:

```bash
# .git/hooks/pre-push in each private repo
#!/bin/sh
branch=$(git rev-parse --abbrev-ref HEAD)
default=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||')
[ "$branch" = "${default:-main}" ] || exit 0
echo "note: pushing straight to $branch. To route through review instead:"
echo "  git branch work/\$(date +%s) && git reset --hard origin/$branch && git checkout work/... && git push -u origin HEAD"
exit 0   # never blocks
```

**Calibration:** the workflow is detection after the fact, and the hook is client-side and bypassable with `--no-verify`. Neither is enforcement. The only enforcement path for these five repos is GitHub Pro, which is a spend decision, not an engineering one, and it belongs to the operator. Surface it, do not act on it.

---

## 9. Acceptance criteria

| Criterion | Observable check |
|---|---|
| Every public repo has a ruleset | `gh api repos/ShovalBenjer/$r/rulesets --jq 'length'` returns non-zero for all 27 |
| Both required checks report under the exact names | phase 1 loop prints `gate=` and `review=` for all 27 |
| Direct push to a protected default branch is refused | `git commit --allow-empty && git push` returns a ruleset rejection after bypass is dropped |
| The operator is never locked out | ruleset DELETE succeeds at every phase |
| `sql-concat` no longer fires on job data | `panel.py run` on a diff touching `archive/job-data/` yields 0 HIGH |
| Reviewers are independent | `review-b` artifact contains no reference to `review-a` findings |
| Dead patterns are found automatically | `panel.py mutants` exits non-zero on any check that catches none of its own mutants |
| `pipeline` domain turns green on measurement | `gate.py run --domain pipeline` passes with its waiver removed, not extended |

---

## 10. Files

- `C:\Users\shova\claude-setup\tools\review\panel.py` (854 lines): 7.1 replaces lines 211-213; 7.2 adds the prose guard used at line 421; the md-only exclusion is lines 411-420
- `C:\Users\shova\claude-setup\tools\gate\gate.py` (1293 lines): domain list line 88, review contract lines 229-249, `review_artifact` line 614
- `C:\Users\shova\.claude\hooks\ship_gate_stop.py`: the Stop-boundary enforcement, unchanged by this spec
- `C:\Users\shova\Downloads\new-recruit\quality-contract.json`: `pipeline` waiver expires 2026-08-01; phase 1 is what lets it be removed rather than renewed

**Not done, needs approval:** publishing `ShovalBenjer/ship-gate` (third-party publication). Nothing in this session wrote, committed, or mutated any file or any GitHub state; all 40-odd API calls were GET.