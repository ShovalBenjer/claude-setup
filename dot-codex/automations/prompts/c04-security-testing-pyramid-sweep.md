# C4. Security and Testing Pyramid Sweep

Schedule: Thursdays 8:00-8:30 PM Asia/Jerusalem
Mode: read + propose + local Hive beads; no code edits in v1

Run one cross-rig audit that maps each active project to the security pyramid and modern testing pyramid.

Use `gpt-5.5` with medium reasoning. Treat these as canonical references:

- `/home/shovalbe/docs/testing_practices.txt`
- `/home/shovalbe/docs/research/2026-05-07-ai-bot-security-best-practices.md`
- `/home/shovalbe/docs/specs/2026-05-13-hive-adoption-plan.md`
- `/home/shovalbe/.hive/rigs.yaml`
- each active project `.codex/hive.yaml`
- each active project `AGENTS.md`

## Active Rigs

Active set re-baselined 2026-06-10 (archived projects removed; lp-creation is the ebook TASK, not a
rig, so excluded). Paths are dirs under `/home/shovalbe/projects/`:

- `axia-seekapa-cs-agents`   (PROD — CS agent, Azure Functions; was `cs-agent`)
- `seekapa-training-platform` (PROD — React/Vite web; highest fix-churn 51%)
- `campaign-analysis`        (PROD — MCP + report jobs; fix-churn 45%)
- `qc-telephony-api`         (PROD — transcription backend; no CI pipeline yet)
- `video-understanding`      (PROD, single-user; video-gen sub-part is emerging)
- `ORM-AGENT`                (EMERGING — new monorepo, 0 tests; treat test-coverage gap as a finding)

For each rig also report: fix-commit ratio over the last 120 commits (flag > 35% as a churn smell
tied to a missing-test surface) and tests/src ratio.

## Security Pyramid Checks

For each rig, classify evidence for:

- secrets in Key Vault or managed identity path
- no secrets printed or committed
- least-privilege tools and DB contracts
- prompt injection / retrieved-content boundary
- output validation and URL/domain allowlists where relevant
- PII and transcript/data handling policy
- audit trail with prompt/model/tool versions where relevant
- deploy path gated through CI or explicit approval
- red-team/eval cadence

## Testing Pyramid Checks

For each rig, classify evidence for:

- static/type/lint checks
- unit tests
- property/invariant tests
- component tests
- contract/API schema tests
- integration tests
- E2E/system smoke
- eval/red-team suites for agentic behavior
- mutation/fuzz/performance coverage when justified
- production-bug regression tests

## Output and Routing

Write one report:

`~/.claude/docs/SECURITY_TESTING_PYRAMID_<DATE>.md`

Sections:

- `EXECUTIVE_SUMMARY`
- `RIG_COVERAGE_MATRIX`
- `SECURITY_PYRAMID_GAPS`
- `TESTING_PYRAMID_GAPS`
- `HIGH_RISK_MISSING_EVIDENCE`
- `HIVE_BEADS_CREATED`
- `ACTIONABLE_NEXT_STEPS`

Create at most 2 beads per rig:

- `P1`: missing security control with plausible production/customer-data risk.
- `P2`: missing contract/eval/regression gate for a live integration.
- `P3`: documentation drift or low-risk test taxonomy cleanup.
