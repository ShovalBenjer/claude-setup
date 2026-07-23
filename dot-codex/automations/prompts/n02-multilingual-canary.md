# n02-multilingual-canary — Dogs / cs-agent

**Role:** Dogs
**Rig:** cs-agent
**Effort:** low (`CODEX_REASONING_EFFORT=low`)
**Schedule:** 18:10 IL nightly Sun–Thu
**Owner:** Shoval Benjer
**Purpose:** Detect Hebrew/Arabic multilingual regressions on the deployed AxiaCS / seekapa Foundry agents BEFORE Yasha or a customer hits them. Detect only — never fix.

This file is the reference template for the other 10 new night-shift workers (`n01`, `n03–n11`, `h01–h05`). Clone it, swap the Inputs / Probe / Criteria sections, leave the Constraints + Emit + Exit-Codes blocks alone.

---

## Inputs (read before probing — do NOT modify these files)

- **Skill in scope:** `~/.claude/skills/azure-runtime/SKILL.md` — protocol for calling deployed Foundry agents in `brn-azai`.
- **Skill in scope:** `~/.claude/skills/eval-runner/SKILL.md` — judge invocation pattern (`grok-4-1-fast-reasoning-2-eval`).
- **Rule in scope:** `~/.codex/automations/prompts/d09-eval-gate-regression-detector.md` — share its threshold logic (`pass_threshold = 0.7`).
- **Hive config:** `~/.hive/rigs.yaml` → `rigs.cs-agent.canary` — override threshold if present, else default 0.7.
- **Canary dataset:** `/home/shovalbe/projects/cs-agent/evals/multilingual-canary.jsonl` — 5 rows: 2 he, 2 ar, 1 en-as-control. Schema: `{lang, query, expected_intent, ground_truth_summary}`.
- **Foundry endpoint:** `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai` (memory `reference_foundry_seekapa_ai`).
- **Target agent ids:** `seekapa`, `AxiaCS` (memory `project_seekapa`).
- **Hooks in scope:** none. Workers do not trigger hooks.

## Probe steps

For each target agent in `[seekapa, AxiaCS]`:

1. For each row in the canary dataset:
   a. Create a thread, post the `query`, run the agent. Token cap per row: `1500 input / 120 output`. Timeout: 30s.
   b. Capture the assistant reply text + tool-call trace.
   c. Score the reply against `expected_intent` and `ground_truth_summary` using the eval-runner judge protocol — judge model: `grok-4-1-fast-reasoning-2-eval`, judge cost cap: `400 input / 80 output`.
2. Aggregate: per-agent pass-rate (judge score ≥ 0.7), per-language pass-rate, per-row score.
3. Write the full results table to `/tmp/n02-out-$CODEX_AUTOMATION_RUN_AT.md` as a 3-column markdown table.

Total wall time budget: 90 s. If exceeded, abort the remaining rows and proceed to the "Emit" step with whatever you have — note `partial_run: true` in the rollup row.

## Criteria for emitting a bead

Emit a `dogs` bead at **P1** if any of:
- Per-agent pass-rate < `0.7` (default; override via `~/.hive/rigs.yaml`)
- Any single he or ar row scored < `0.5` (catastrophic miss on a non-English row)
- Agent returned an error / no response on any row (network excluded — covered by the "probe broken" path)

Emit at **P0** instead if:
- Both `seekapa` AND `AxiaCS` have pass-rate < `0.5` simultaneously — that's a stack-wide multilingual outage, not a row regression.

---

## Hive bead-emit

You are a night-shift worker. **Detect only — never fix.** If the criteria below are met, emit a bead to the Hive. Otherwise write the usual report and exit cleanly.

**Criteria for emitting a bead:** see "Criteria" section above.

**On match — emit exactly one bead per finding:**

```bash
~/.hive/bin/bead-create \
  --rig cs-agent \
  --owner-role dogs \
  --priority "$PRIORITY" \
  --trigger-source n02-multilingual-canary \
  --source-id "$CODEX_AUTOMATION_RUN_AT" \
  --title "<≤80-char finding title — include which agent + which lang failed>" \
  --body-from "/tmp/n02-out-$CODEX_AUTOMATION_RUN_AT.md"
```

Where `PRIORITY` is `P0` or `P1` per the criteria.

**Idempotency:** if `bead-create` exits non-zero with code 11 (`DUPLICATE_TRIGGER_SOURCE_ID`), the same finding was already filed by a previous run — log "already filed" and continue.

**Non-emit path:** append one line to `~/.hive/observability/n02-multilingual-canary-rollup.jsonl`:

```json
{"run_at": "<CODEX_AUTOMATION_RUN_AT>", "rig": "cs-agent", "finding": "none", "agents_checked": 2, "rows": 5, "pass_rate_seekapa": 0.X, "pass_rate_axiacs": 0.X, "duration_s": <N>}
```

**Constraints:**
- Do not modify code, config, secrets, or repo state.
- Do not call other Polecats. Do not claim beads. Do not call other agents besides the two targets and the judge.
- Do not echo customer queries from the canary file containing PII. The 5 rows are synthetic by construction; if any row appears non-synthetic, abort with exit code 2 and emit a "probe broken" bead.
- Token budget for this run: ≤ `15000 input / 2500 output` total across all probe steps + judge calls. If `HIVE_MAX_INPUT_TOKENS` is injected by the runner, take the smaller of the two.
- If the probe itself fails (auth to brn-azai, judge model unreachable, canary file missing), do NOT emit a finding bead. Instead emit ONE bead with `--owner-role crew --priority P2 --title "probe broken: n02-multilingual-canary"` so a Polecat can fix the probe.

**Exit codes for the runner:**
- `0` — clean run, no bead emitted (all canaries passed).
- `0` — clean run, finding bead emitted (still 0).
- `2` — probe broken; the "probe broken" bead above was emitted.
- non-zero anything else — Mayor will retry next window per stale-claim rules.

---

## What this template encodes for cloning

When you write `n01`, `n03–n11`, or any of the `h0X` Hive-hygiene workers, keep the **shape identical**:

1. **Header block** — Role, Rig, Effort, Schedule, Purpose. One line each.
2. **Inputs section** — every skill / rule / hook / config file the worker reads, with absolute paths. Workers must NEVER discover paths at runtime.
3. **Probe steps** — numbered, deterministic, with token budgets and timeouts on every external call.
4. **Criteria section** — exact thresholds for each priority level. Default thresholds inline; override path through `~/.hive/rigs.yaml`.
5. **Hive bead-emit block** — copy verbatim from `_bead-emit-appendix.md`, fill placeholders, no other edits.
6. **Constraints block** — copy verbatim; add probe-specific lines only at the end.
7. **Exit-codes block** — copy verbatim. Do NOT invent new exit codes per worker.

The shape is the contract. If a future worker breaks the shape, the Hive runner will not be able to parse it deterministically, and Mayor will refuse to schedule it.
