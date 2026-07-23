<!--
  Reusable bead-emit stanza.
  How to use: append this block to the END of any existing automation prompt
  under ~/.codex/automations/prompts/ to convert that prompt from "writes a
  report" → "writes a report AND emits a bead when criteria are met."

  Substitute placeholders inline before append. Do NOT include this HTML
  comment in the appended copy — strip it.

  Placeholders:
    {RIG}             — cs-agent | campaign-analysis | qc-telephony-api | video-understanding | all
    {OWNER_ROLE}      — dogs | witness | crew
    {DEFAULT_PRIORITY}— P0 | P1 | P2 | P3
    {TRIGGER_SOURCE}  — the prompt's automation id (e.g. d09-eval-gate-regression-detector)
    {CRITERIA}        — one sentence describing the threshold that justifies a bead
-->

---

## Hive bead-emit

You are a night-shift worker. **Detect only — never fix.** If the criteria below are met, emit a bead to the Hive. Otherwise write the usual report and exit cleanly.

**Criteria for emitting a bead:** {CRITERIA}.

**On match — emit exactly one bead per finding:**

```bash
~/.hive/bin/bead-create \
  --rig {RIG} \
  --owner-role {OWNER_ROLE} \
  --priority {DEFAULT_PRIORITY} \
  --trigger-source {TRIGGER_SOURCE} \
  --source-id "$CODEX_AUTOMATION_RUN_AT" \
  --title "<≤80-char finding title>" \
  --body-from <path to a short markdown file you wrote with the evidence>
```

**Idempotency:** if `bead-create` exits non-zero with code 11 (`DUPLICATE_TRIGGER_SOURCE_ID`), that means the same finding was already filed by a previous run — log "already filed" and continue. Do NOT retry, do NOT raise priority.

**Non-emit path:** if criteria are not met, append one line to `~/.hive/observability/{TRIGGER_SOURCE}-rollup.jsonl`:

```json
{"run_at": "<CODEX_AUTOMATION_RUN_AT>", "rig": "{RIG}", "finding": "none", "checks_run": <N>, "duration_s": <N>}
```

**Constraints (re-stated for clarity, even if you have global rules):**
- Do not modify code, config, secrets, or repo state.
- Do not call other Polecats. Do not claim beads.
- Do not retry on transient failure beyond what the probe step allows.
- Token budget for this run: per `~/.codex/config/usage-budget.yaml`. If the runner injects `HIVE_MAX_INPUT_TOKENS`, respect it.
- If the probe itself fails (auth, network, missing tool), do NOT emit a finding bead. Instead emit ONE bead with `--owner-role crew --priority P2 --title "probe broken: {TRIGGER_SOURCE}"` so a Polecat can fix the probe.

**Exit codes for the runner:**
- `0` — clean run, no bead emitted (no finding).
- `0` — clean run, bead emitted (still 0; bead lifecycle is its own thing).
- `2` — probe broken (the "probe broken" bead above was emitted).
- non-zero anything else — Mayor will retry next window per stale-claim rules.
