# D4. Foundry Agent Version Bump Audit

Schedule: Mondays 09:00
Repo root: `/home/shovalbe/projects/cs-agent`, `/home/shovalbe/projects/HR-agent`, `/home/shovalbe/projects/campaign-analysis`
Mode: read + propose

For each Foundry agent repo, scan commits in the last 30 days matching subject regex `/v[0-9]+/`.

Extract per commit:
- agent name (from subject prefix or path)
- version number (the `v\d+`)
- date
- whether commit type is `feat` or `fix`

Build a per-agent timeline like:

```
agent | v7 (feat, Mar 22) | v71 (feat, Apr 1) | v72 (fix, Apr 4) | v73 (fix, Apr 8) | v74 (fix, Apr 12)
```

Compute `fix_burst_rate = count of fix() commits per version within 7 days of that version's deploy`.

For any agent with `fix_burst_rate > 2`: flag as **deployed-then-debugged** and write to `~/.claude/docs/AGENT_VERSION_AUDIT_<DATE>.md`:
- the timeline
- the diffs between consecutive versions
- a 1-paragraph hypothesis: was the version deployed without test coverage? Without spec? Without grilling?

Cross-reference with `~/.claude/projects/-home-shovalbe/memory/lesson_prompt_versioning.md`.

If any agent is at `vXX` where 5 of last 7 commits are fixes:
1. Suggest a rollback to `vXX-burst-start` in the report.
2. File an ADO Bug:

```bash
~/.claude/bin/work-item.sh create --type Bug \
  --title "Prompt regression cycle: <agent> v<XX>" \
  --tags "prompt-debt,foundry"
```

Evidence cited: campaign-analysis MFM agent v7 → v71 → v72 → v73 → v74 in 4 weeks (SHAs `8b36ce2`, `bcd9a64`, `d88cebb`, `4088920`, `fa1f4b6`). Three of the last four were `fix(mfm)` not `feat(mfm)`.
