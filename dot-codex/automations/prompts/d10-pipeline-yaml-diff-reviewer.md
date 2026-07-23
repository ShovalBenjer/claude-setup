# D10. Pipeline YAML Diff Reviewer

Schedule: Daily 07:00 (covers overnight + early-morning hand-edits)
Repo root: all repos under `/home/shovalbe/projects/`
Mode: read + comment + Bug if P0 finding

For each PR opened or updated in the last 24h, check if `azure-pipelines.yml` or any `*.yml` under `.azure-devops/`, `pipelines/`, `.github/workflows/` was modified.

If yes:

1. Pull the diff for the YAML file(s) using `az repos pr show --id <pr-id> --output json` then fetch the file diff.

2. Run a 6-point review:

   a. **New auth steps** — credentials sourced via Key Vault (allowed) or hardcoded (never allowed, per `~/.claude/rules/production-safety.md`)?

   b. **New external service calls** — HEAD/GET only? Or POST/PUT/DELETE to `*.azurewebsites.net` or `*.corp-domain.com`? Flag the latter as P0 (production-safety violation).

   c. **Trigger changes** — does the trigger now include `master` or `stage` directly? Should be `feature/* → stage → master` only (per `~/.claude/rules/production-safety.md`).

   d. **Removed gates** — did any test/eval/lint step disappear?

   e. **Pool changes** — did the agent pool change? (Capacity drift, may break)

   f. **Variable references** — are all `$(VAR)` references defined either in pipeline vars or in linked variable groups?

3. Comment the review on the PR via `~/.claude/bin/work-item.sh comment <pr-id>` with each finding tagged `P0` / `P1` / `P2`.

4. If any P0 finding: also create an ADO Bug:

```bash
~/.claude/bin/work-item.sh create --type Bug \
  --title "Pipeline YAML P0 in PR #<pr-id>" \
  --tags "ci,pipeline-review,p0"
```

This automation IS the YAML reviewer when no human is online. Catches Yasha-style direct edits at 02:00–07:00 UTC before they merge.

Evidence cited: SHA `83a51eb` "Updated azure-pipelines.yml" (1-line, no body, by Yasha at 16:19 UTC — 5+ similar SHAs on the same branch). Plus SHAs `5394674`, `bff6ee0`, `bcb3f98`, `658cbc6` — pipeline edits with high blast radius and no automated review.
