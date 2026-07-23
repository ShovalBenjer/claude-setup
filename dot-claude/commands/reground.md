---
description: Re-read rules, tools, skills, memory cues, git/remote state, Jira reminders, docs, plans, tree hygiene, data artifacts, and AI-coding risk.
argument-hint: [lite|full] [optional focus]
---

You are running the `reground` skill. Read the canonical instructions from `/home/shovalbe/.agents/skills/reground/SKILL.md`.

Mode:
- `lite`: targeted dynamic commands only.
- `full`: full artifact/tree hygiene pass. Use the collector or equivalent dynamic Linux probes.
- omitted: choose lite or full based on risk.

Shortcut for full mode:

```bash
rtk /home/shovalbe/.agents/skills/reground/scripts/reground-snapshot.sh "$PWD"
```

Use command output as evidence, then produce the `REGROUND` report from the skill. Include branch/root hygiene, recent `.png/.xlsx/.csv/.parquet/.json` artifacts, root clutter, and the Ponytail plus platform-engineering AI-coding risk scan when full mode is selected or risk requires it.

If `$ARGUMENTS` is non-empty, treat it as the focus area and prioritize matching docs, Jira keys, memory entries, and recent artifacts. Do not modify files, refresh Jira, call cloud APIs, commit, kill processes, or start servers unless the user separately asks.
