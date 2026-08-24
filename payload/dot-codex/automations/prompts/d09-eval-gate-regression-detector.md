# D9. Eval Gate Regression Detector

Schedule: Weekdays 09:45
Repo root: `/home/shovalbe/projects/cs-agent`, `/home/shovalbe/projects/campaign-analysis`
Mode: read + ADO comment on PR

Scan diffs of the last 14 days. For each `azure-pipelines.yml` or eval-related YAML/Python diff, detect these anti-patterns:

1. `continue-on-error: true` added to an eval step
2. `condition: succeededOrFailed()` added to a deploy step downstream of eval
3. eval step removed from the `dependsOn` chain
4. eval step's `failureThreshold` raised
5. an eval row marked `.skip` or commented out without an issue link
6. environment variables flipped to disable an eval (e.g., `RUN_EVAL=0`, `SKIP_EVAL=1`, `EVAL_DISABLED=true`)

For each match:
- commit sha + author + branch
- 1-line "what was disabled"
- 1-line "what risk this carries" — classify per `~/.claude/projects/-home-shovalbe/memory/lesson_eval_gate_reliability.md`:
  - **code regression** (your test caught a real change) — never disable
  - **config drift** (external dep flapped) — temporary skip OK with sunset date

Output `~/.claude/docs/EVAL_GATE_REGRESSIONS_<DATE>.md`.

For each match: comment on the source PR (if open):

```bash
~/.claude/bin/work-item.sh comment <pr-id> "$(cat <<'EOF'
Eval gate disabled in this PR (sha <X>). Per lesson_eval_gate_reliability.md: classify as code regression vs config drift. If config drift, attach a sunset date or work item ID. If code regression, do not merge.
EOF
)"
```

**Do NOT block the PR.** The user has authority to disable. Only flag.

Evidence cited: cs-agent SHAs `f25d7977` (endpoint fix), `33b26297` (AAD auth fix), `b4378681` (cold-start fix), `2c8455d4` (assignment gate + content safety retry). Eval gate keeps breaking — sometimes the fix is "disable it temporarily" and that disable lingers.
