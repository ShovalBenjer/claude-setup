---
name: repo-compare
description: Compare this harness against saved and newly published GitHub repos and produce an adopt/watch/ignore delta report. Triggers on "/repo-compare", "compare our system against new repos", "compare against the saved repos", "what does <repo> do that we don't", after a batch of repos lands in the resource ledger, or on a scheduled sweep. Read-only on GitHub. SKIP for single-claim novelty checks (use prior-art-gate) and for full research reports (use deep-research).
---

# repo-compare

Created 2026-08-11, lane A, from an operator instruction on 2026-08-11 after the same
request was scoped and dropped twice without a note (state/claims.jsonl rows 25, 28, 29:
"comparing against the WhatsApp GitHub repos which may never have been compared", then
the 2026-08-10 prime-agent analysis row whose output file was never written). The
recurring pattern is now a procedure so a session cannot drop it silently again.

## What it answers

"Given the repos I saved and what is newly published, what should this harness adopt,
what should it watch, and what is safely ignored?" The comparison target is the
claude-setup harness: gate and oracles, state ledgers, bus, refutation layer, skills
management, autonomy loop, prompt capture.

## Inputs

1. Saved corpus, from the chained ledger:

```bash
python3 - <<'EOF'
import json, re
seen = {}
for line in open('state/resource-ledger.jsonl'):
    for m in re.findall(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', line):
        seen[m.lower()] = seen.get(m.lower(), 0) + 1
print(len(seen), 'distinct repos')
for k in sorted(seen): print(k)
EOF
```

Measured 2026-08-11: 199 distinct repos. Rows with kind "see" and no later "note" are
the unexamined backlog; `python3 tools/intent/resources.py coverage` prints the split.

2. Fresh candidates, read-only search, only when the operator asked for "new" repos:

```bash
gh search repos "claude code agent harness" --sort updated --limit 10 --json fullName,description,stargazersCount,updatedAt
gh search repos "llm agent memory verification" --sort stars --limit 10 --json fullName,description,stargazersCount,updatedAt
```

3. Explicit repos named by the operator override both lists.

## Procedure

1. Pick candidates: operator-named first, else unexamined ledger repos newest first plus
   fresh search hits. Default cap 8 per run; print what was cut so the cap is visible.
2. Load our side from `CLAUDE-OS.md` and `docs/CODEBASE-MAP.md`. The axes: verification
   oracles, append-only state, multi-agent routing, autonomy loop, prompt capture,
   skills sync, secret hygiene.
3. Per candidate, metadata then README, no clone by default:

```bash
gh repo view <owner/name> --json description,stargazerCount,pushedAt,licenseInfo,primaryLanguage
gh api repos/<owner/name>/readme --jq .content | base64 -d | head -200
```

   Clone into a scratch dir only when the README cannot answer, and read-only.
4. Verdict per repo, one of three, each with its reason anchored to a file or README
   section in THEIR repo: ADOPT (name the mechanism and the exact place it lands here),
   WATCH (name what would change the answer), IGNORE (name why). No unsourced novelty
   or absence claims; prior-art-gate rules apply.
5. Write `docs/analysis/YYYY-MM-DD-repo-compare.md` with the verdict table and one
   paragraph per ADOPT. Run `python3 tools/slop_lint.py` on it.
6. Close the ledger loop, so coverage stops decaying:

```bash
python3 tools/intent/resources.py see "github.com/<owner/name>"
python3 tools/intent/resources.py note "github.com/<owner/name>" --ref docs/analysis/<the report>.md
```

   (Check `resources.py note -h` for the exact flag names before the first run.)

## Hard limits

- GitHub reads only: search, view, api GET. No stars, comments, issues, forks, or any
  write. No codex, no claude -p, no gws, no az, no paid API calls.
- An ADOPT verdict is a proposal. Implementation is a separate claimed session.
- If the run cannot finish, the report ships partial and names the repos not reached.
  A dropped comparison with no note is the exact failure this skill exists to end.
