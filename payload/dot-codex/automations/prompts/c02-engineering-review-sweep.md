# C2. Active-Project Engineering Review Sweep

Schedule: Weekdays 6:00-8:00 PM Asia/Jerusalem
Mode: read + propose + local Hive beads; no remote comments/work items in v1

Run one engineering review pass across the four active projects only, then route actionable findings into the local Hive.

Use `gpt-5.5` with medium reasoning. Treat `~/.codex` as the source of truth and `~/.claude` as a compatibility layer.

## Scope

Active project rigs:

- `cs-agent` -> `/home/shovalbe/projects/cs-agent`
- `qc-telephony-api` -> `/home/shovalbe/projects/qc/qc-telephony-api`
- `video-understanding` -> `/home/shovalbe/projects/video-understanding`
- `campaign-analysis` -> `/home/shovalbe/projects/campaign-analysis`

Do not scan every git repo under `/home/shovalbe/projects/`. Do not route findings for archives, inherited repos, SIU, figma, seekapa-training-platform, or nested repos unless they are direct evidence for one of the four active rigs.

Azure DevOps remote scope:

- organization: `https://dev.azure.com/Corp-domain`
- project: `Corp-AI`
- use `az repos list`, `az repos pr list --status active`, `az repos ref list`, and pipeline/run commands when authenticated

If Azure auth is unavailable, write `auth-needs-refresh` and continue with local git analysis.

Hive scope:

- Rig config: `~/.hive/rigs.yaml`
- Project rig manifests: `<project>/.codex/hive.yaml`
- Claude compatibility pointers: `<project>/.claude/hive.yaml`
- Bead commands are on PATH in scheduled runs: `bead-create`, `bead-list`, `bead-claim`, `bead-close`
- You may create local beads only. Do not comment on PRs, create ADO work items, push branches, or edit project files.
- Create at most 3 beads per rig per run. Only create beads for actionable, evidence-backed findings.
- Bead priority mapping:
  - `P0`: active production/security incident or secret exposure risk
  - `P1`: broken CI/deploy/eval gate, high-confidence security regression, or live prompt drift
  - `P2`: test coverage gap, stale spec needing owner decision, hot-zone refactor risk
  - `P3`: cleanup, documentation drift, or low-risk hygiene

## Remote + Commit History Baseline

For each active rig:

- record `origin` URL
- compare local branches to upstream tracking refs
- analyze `git log --all` for the last 30 days
- analyze commits in the last 24 hours for high-risk artifacts
- if safe, use read-only remote checks such as `git ls-remote`; do not delete branches or rewrite history

For Azure DevOps:

- list active PRs and stale PRs
- list remote branches older than 30 days with no open PR when ADO data is available
- cross-reference ADO PRs against matching local repos by remote URL or repo name
- identify remote repos that are not cloned locally and list them as coverage gaps

## Review Checks

### Spec and Docs Drift

- Walk `docs/superpowers/specs/` and project-level `docs/specs/`.
- Classify specs as `ACTIVE`, `STALLED`, `ORPHAN`, or `MERGED`.
- Check each project `CLAUDE.md` for path claims, stack/deps claims, branch-flow claims, and command references.
- Check each project `AGENTS.md` and `.codex/hive.yaml` for parity with global policy.
- Treat `.codex/hive.yaml` as the project-level bridge between scheduled Codex and interactive Claude agents.

### Foundry Agent Prompt Drift

For `cs-agent` and `campaign-analysis`:

- read prompt files in git, typically `prompt.md`, `agent_prompts/*.md`, or `agent.yaml`
- compare against live Foundry prompt if SDK/auth are available
- flag lines in Foundry not in git as highest risk

### Code Quality

Run static/read-only checks appropriate to each rig:

- Python: `uv run ruff check` if configured
- TypeScript/JS: use `bun run lint` or local lint script if configured
- Scan for added `any`, debug prints, broad exception swallowing, magic numbers without context, high `z-index`, `!important`, and emoji in UI/code
- Identify hot-zone files: files with repeated `fix(...)` commits in 30 days and weak/no parallel tests
- Identify duplicate commit subjects by author across distinct SHAs
- Identify stash/WIP leak commits

Do not auto-fix.

### Tests and Eval Gates

- Detect eval gate weakening in YAML/Python diffs from the last 14 days.
- Detect removed lint/test/eval pipeline steps.
- Detect `continue-on-error: true`, raised thresholds, or disabled eval flags without sunset/work item.
- Check for changed source files without corresponding tests when risk is high.

### Performance and Latency

Scan recent diffs and hot files for:

- added sleeps, polling loops, serial network calls, unbounded retries
- missing timeouts around HTTP, Azure, Foundry, or shell calls
- N+1 query risks
- large synchronous file/JSON processing on startup paths
- hook or CLI paths that can slow every session/tool call
- frontend bundle/perf risk when package/build config changed

When measurable, run lightweight read-only checks only. Avoid long benchmarks unless the repo already has a fast perf script.

### CI, Pipelines, and ADO

Include the checks previously covered by D-series prompts:

- CI auth reproducer risk from pipeline YAML
- ADO web UI hand-edit detector
- pipeline YAML diff reviewer
- AI PR review stage health
- eval gate regression detector
- lint debt tripwire
- hot-zone indicator

Do not comment on PRs in v1.

Do not create ADO Tasks/Bugs in v1.

## Active Rig Checks

Use the following rig-specific emphasis:

- `cs-agent`: Foundry prompt drift, Chatwoot/CRM boundary, deterministic classifier, output sanitization, multilingual evals, read-only CRM contract.
- `qc-telephony-api`: API contracts, QAResponse shape, target-language behavior, Azure OpenAI/Key Vault config drift, no-storage guarantees. **Production monitoring health:** run `~/.claude/bin/qc-monitoring-check.sh 24` (read-only Log Analytics query; needs `az login`) and include its markdown output VERBATIM in the `QC_TELEPHONY_MONITORING` report section, do not summarize it. Then add one PASS/FAIL line: PASS if telemetry reads ALIVE and AppExceptions=0; FAIL otherwise. If the script prints BLOCKED, record `auth-needs-refresh` and continue. Accepted known gap: the `AppRequests` table reads 0 (host request telemetry not emitting), that alone is NOT a FAIL. A daily ALIVE reading is the proof that the 2026-06-29 telemetry fix persists. Also note: the rig path in this prompt is stale (real path is `/home/shovalbe/projects/qc-telephony-api`, not `/qc/`).
- `video-understanding`: ACA/Bicep path, Streamlit upload health, Telegram bot roadmap, Key Vault SDK/MI path, no-network tests.
- `campaign-analysis`: MCP gateway role scopes, APIM/Entra security, workbook/report lineage, Foundry prompt drift, connector eval gates.

## Output

Write one report:

`~/.claude/docs/ENGINEERING_REVIEW_<DATE>.md`

The report must contain:

- `EXECUTIVE_SUMMARY`
- `AZURE_DEVOPS_REMOTE_COVERAGE`
- `LOCAL_REPO_COVERAGE`
- `SPEC_AND_DOCS_DRIFT`
- `FOUNDRY_PROMPT_DRIFT`
- `CODE_QUALITY`
- `TEST_AND_EVAL_GATES`
- `PERFORMANCE_AND_LATENCY`
- `CI_AND_PIPELINES`
- `STALE_PR_AND_BRANCH_TRIAGE`
- `QC_TELEPHONY_MONITORING`
- `PROJECT_ROUTING`
- `HIVE_BEADS_CREATED`
- `ACTIONABLE_NEXT_STEPS`

For `PROJECT_ROUTING`, list affected projects and the top 3 findings per project so Claude Code can pick them up manually or through a future project inbox bridge.

For `HIVE_BEADS_CREATED`, list each bead id, rig, priority, and title. If no bead is created, explicitly say why.
