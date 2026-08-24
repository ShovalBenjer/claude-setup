---
description: Run reground plus evidence-backed likely next moves.
argument-hint: [lite|full] [optional focus]
---

You are running the `reground` skill in `/insights` mode. Read `/home/shovalbe/.agents/skills/reground/SKILL.md`.

Mode:
- `lite`: targeted dynamic commands plus likely next moves.
- `full`: full artifact/tree hygiene pass plus likely next moves.
- omitted: choose based on risk.

Shortcut for full mode:

```bash
rtk /home/shovalbe/.agents/skills/reground/scripts/reground-snapshot.sh "$PWD"
```

Use the output as evidence, then produce the `REGROUND` report and append `Likely Next Moves` with 3-5 concrete, evidence-backed observations. Include branch/root hygiene, recent data/artifact files, root cleanliness, and platform-engineering AI-coding risk before proposing action.

If `$ARGUMENTS` is non-empty, treat it as the focus area. Keep the command read-only unless the user separately asks for changes.
