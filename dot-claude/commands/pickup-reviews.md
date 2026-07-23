---
description: Pull open Codex review findings from Hive for the current project and turn one into the next concrete task.
argument-hint: [optional rig or bead id]
---

You are running the Codex review pickup bridge.

Use the current directory to infer the Hive rig unless `$ARGUMENTS` names a rig or bead id.

Required flow:

1. Read recent scheduled review context:
   - `~/.claude/docs/ENGINEERING_REVIEW_*.md`
   - `~/.claude/docs/CLAUDEMD_DRIFT_*.md`
   - `~/.claude/docs/HOT_ZONES_*.md`
2. Read open Hive beads for the inferred rig:
   - `~/.hive/bin/bead-list --rig <rig>`
   - or direct SQLite only if the CLI cannot filter precisely.
3. Pick the highest-priority bead relevant to the user's current prompt.
4. Claim it before implementation:
   - `~/.hive/bin/bead-claim --rig <rig> --claimed-by claude:<short-task>`
5. Implement only the claimed slice.
6. Verify with real commands.
7. Close the bead with durable evidence:
   - `~/.hive/bin/bead-close <id> --evidence-url <commit-sha-or-report-path>`

If no bead should be picked up, say why explicitly and continue with the user's requested task.
