# Explicit Program of Work — 2026-06-09

Owner: Shoval. Orchestrator: Claude (Opus 4.8, ultracode). Executor model tiers vary per step.
Two threads converged into one program: (1) the **CJA analytics rescue** (urgent — bosses waiting),
(2) the **stack-modernization + hive audit** (original task), plus (3) the **CLI/MCP + hive self-improvement**.

---

## Operating constraints (learned this session)

- **Cap discipline.** A shared session cap (reset 7:20pm Asia/Jerusalem) was tripped by ~31 concurrent Opus subagents (~1.06M tokens). Rules now: **never run two big workflows concurrently; sequence them. Mechanical reads/audits → haiku/sonnet; Opus only for synthesis/assembly. Persist every workflow output to disk. Resume via `resumeFromRunId` (cached agents replay free). Probe with one cheap main-loop step before a large fan-out.**
- **Safety.** Web research = PUBLIC tech terms only (no internal names/URLs/secrets). Local audits = read-only, never echo secrets/PII. No `git add` at `$HOME`. No deleting the v2 corpus or duplicate repos without explicit OK. No paid scoring runs (keep the prior agent's refusal of an unbounded paid run).
- **Output bar.** Every analytic answer is decision-grade: number + provenance(query+path) + what-it-means + one owned/dated action; tagged ACTIONABLE vs DIRECTIONAL.

---

## TRACK A — CJA analytics rescue (PRIORITY)

Goal: turn `docs/CJA-REQUIREMENT-OF-RECORD.md` (the 12-question anchor I just wrote) into real, defensible answers, context-bounded so it never blows the window again.

### A1 — Data catalog (main-loop, cap-safe, FIRST)
- Inspect `scores_v3` schema + telephony + manifest/master tables; build a one-time **DuckDB/Polars catalog** persisted to `outputs/_catalog/` (columns, row counts, key coverage, v3-path assertion). This is the context-room fix: agents query the catalog + read only their slice, never load 146 xlsx.

### A2 — Hygiene fixes (main-loop, needs your OK — existing code)
- Repoint `scripts/report/seekapa_deliverable.py:31` `scores_v2` → `scores_v3`.
- Add PII-masking of `agents.csv` at the pipeline boundary (pseudonymise names/emails).
- Add a pre-write grep gate that fails if any output contains an email/phone/raw name column.

### A3 — `cja-answer-engine` (WORKFLOW, right-sized, after A1/A2)
- **Phase Answer** (parallel, sonnet): one agent per **on-disk-answerable** question — Q3 (Answer-Rate 6-layer), Q4 (speed-to-lead), Q5 (attempt cadence), Q7 (promise-match L13), Q9 (objections), Q10 (language-barrier false-flags). Each runs a DuckDB/Polars query over `scores_v3`+telephony, computes the metric per the PDF definition, returns a COMPACT structured answer.
- **Phase Verify** (pipeline, sonnet): adversarial verifier per answer — re-derive a second way, check for v2 contamination / double-count / wrong join / leakage. Confirm or refute.
- **Phase Assemble** (opus): write `outputs/2026-06-09/deliverable/CJA-12-answers.md` (decision-grade, all 12: the 6 answered, the 5 CRM-join-pending stubbed with exactly what's needed, Q12 LTV flagged DIRECTIONAL/model-gap) + a rebuilt workbook on v3.
- ~13 agents, mostly sonnet. Runs alone.

### A4 — Fresh-input check (main-loop)
- Visually read the PNG screenshots in `docs/Sales Statuses.eml` (3) + `docs/Consumer insights.eml` (8) to confirm I'm not solving a stale ask; fold into the anchor's open-items.

### A5 — Model gaps (note, not fake)
- Lead-Quality(0–100), FTD-probability, LTV(30/90/365) models are unbuilt → Q1/Q12 partly DIRECTIONAL. Propose a separate AutoML/Foundry build as a follow-up; do not fabricate predictions.

---

## TRACK B — Stack modernization + hive audit (resume after 7:20pm, sequenced)

### B1 — resume `stack-modernization` (`wf_79642646-93f`)
- Edit the script: per-project audits → haiku/sonnet; leave the 6 cached research domains + cs-agent-main audit untouched (replay free). Re-run: 3 failed research (data-serialization, ml-validation-eval, claude-hive-sota), 9 project audits, hive+codex audits, per-project synthesis, assemble, critic.
- Output: `~/docs/audits/2026-06-09-stack-modernization-and-hive-upgrade.md`.

### B2 — re-run `agent-shell-and-mcp` (fresh; nothing cached)
- 3 research (rtk-aware CLI triage, MCP landscape+security, install/wiring) + synth + assemble.
- Output: `~/docs/audits/2026-06-09-agent-shell-and-mcp-layer.md`.

### B3 — merge (main-loop)
- Consolidated cross-project backlog; the CJA rescue stands as the worked example of the campaign-analysis upgrade.

---

## TRACK C — Hive self-improvement + new skills (additive; after B1's hive plan)

Scaffold the highest-leverage NEW skills (each a SKILL.md + assets; present before activation):
1. **`requirement-anchor`** — given a project + a spec (PDF/eml), extract a compact requirement-of-record + answer-map, enforce read-before-build. (The CJA fix, generalized — kills "build-before-reground".)
2. **`context-bounded-analyst`** — for any data project: build a DuckDB/Polars catalog + answer questions via lazy queries returning compact results. (The context-room fix.)
3. **`decision-grade` linter** (extends LTMD) — reject any deliverable lacking number+provenance+meaning+owned/dated action.
4. **`pii-scrubber` hook** — PreToolUse/Stop hook scanning outputs for name/email/phone before write/commit.
5. (From B1 research) **`bicep-iac-lint`** + **`secretless-pipeline`** skills.

---

## TRACK D — Cross-cutting config (main-loop)

- Wire the anchor + reground-before-build so it actually fires (project CLAUDE.md pointer / settings hook).
- Add the rtk-aware "Agent Shell Defaults" block to CLAUDE.md (from B2): agent calls stay rtk-compressed; `sd`/`fd`/`hyperfine` added as dual-use; pretty tools (eza/bat/delta/yazi) are human-only.

---

## Sequencing under the cap

`A1 (now) → A2 (now, on your OK) → A4 (now) → A3 workflow → [7:20pm] → B1 → B2 → B3 → C → D`
One workflow at a time. Cheap step first to probe the cap. Resume on any hit.

## Premortem (5 failure modes + mitigations)
1. **Cap re-hit** → sequence, cheaper models, resume-from-runId, persist.
2. **Leaky v2 contamination** → catalog asserts v3 path; verifier checks every number.
3. **PII in deliverable** → mask step + pre-write grep gate.
4. **Answering a stale ask** → anchor is the contract; screenshot review; PandaTS-dead flagged.
5. **Numbers bosses distrust** → adversarial verify + provenance + ACTIONABLE/DIRECTIONAL honesty + reconcile revenue to CRM actuals (Windsor is 40–70% off).

## What only you can answer (genuine inputs)
- **OK to edit `seekapa_deliverable.py` (v2→v3) + rebuild the workbook?**
- **CRM revenue/comments for Q1/Q2/Q6/Q8/Q11:** Yasha endpoint pull, or is there a master/deposits parquet already on disk? (decides which questions answerable now)
- **Scaffold new skills now, or after the audit?**
- Confirm: no paid scoring runs without an explicit bounded approval.
