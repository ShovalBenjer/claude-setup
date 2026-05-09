# Forge Loop Compliance Score - 2026-05-03

## Scope
- Automation id: `a09-forge-loop-compliance-score`
- Run timestamp UTC: `20260503T131438Z`
- Audit window: `2026-04-26T13:14:38+00:00` through `2026-05-03T13:14:38+00:00`
- Sources: `~/.claude/projects/**/*.jsonl`, `~/.claude/history.jsonl`, and fallback/current transcript store `~/.codex/sessions/**/*.jsonl`.
- Privacy: session bodies, prompt text, credentials, emails, and message contents were not copied into this report.

## Per-Session Table
| session_id | source | branch | score | missing_steps |
|---|---|---|---:|---|
| `019dcd86-2682-70c2-a90b-62dd3e10fab5` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dcf5f-2f1a-7ae0-8307-f85a280297a1` | codex | `feature/fix-pipeline-buildctx-and-prompt-v14` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dcf63-72e4-7060-8b24-32f7e4c8cb5b` | codex | `feature/fix-pipeline-buildctx-and-prompt-v14` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dcfe5-30b8-7922-a57e-9ba3d04c28b9` | codex | `feat/align-test-connector-to-production` | 3/8 | PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd32d-ae70-7593-a339-704820d765d0` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd330-b499-7d92-9d35-2850f12e9e51` | codex | `feat/align-test-connector-to-production` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dd35c-c678-73c3-9b5a-f7c62d43df5a` | codex | `feature/mcp-bicep-deploy` | 1/8 | SPEC, PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, CI BIND |
| `019dd35f-459d-7fe0-ae3a-96bdb48bea3d` | codex | `feature/mcp-bicep-deploy` | 2/8 | PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, CI BIND |
| `019dd35f-e5ec-70f2-8a8c-5c7f4af07d87` | codex | `feature/mcp-bicep-deploy` | 0/8 | SPEC, PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dd439-4fef-7e32-907a-651c1c02645d` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd45e-4b53-7a33-9242-44168f1db2c8` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd469-e4e3-7091-a3d6-f5a1f8c70322` | codex | `feat/align-test-connector-to-production` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dd49e-a17d-7072-b3a9-4882a76fae72` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd4a0-209b-75c1-91d7-6e1400ff777b` | codex | `feat/align-test-connector-to-production` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dd81c-55d7-75d2-b386-6731940bb989` | codex | `feat/align-test-connector-to-production` | 3/8 | PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd8e4-3f2a-7613-a165-a20ec5007925` | codex | `feat/align-test-connector-to-production` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dd8e7-613b-75e2-b55c-0e313b6641d5` | codex | `feat/align-test-connector-to-production` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `60618ff4-3e71-4002-9641-1b59981d7983` | claude | `HEAD` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT |
| `4e83080b-6346-42b4-8f16-aae417e6fb33` | claude | `HEAD` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `44f1ac7d-9664-478e-975f-cb33ce82e6bf` | claude | `fix/ci-vector-store-env-bypass` | 4/8 | PREMORTEM, REFACTOR, COVERAGE, REFLECT |
| `c8c10db9-ddc7-4022-ace6-755f65117fdd` | claude | `fix/ci-vector-store-env-bypass` | 3/8 | SPEC, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dda36-1ddb-7df0-8602-bb63db9aed09` | codex | `feat/v109-yasha-multilingual` | 3/8 | PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `31bdaa14-eb62-4bc1-a3b2-1e86e98b373d` | claude | `feat/v109-yasha-multilingual` | 4/8 | PREMORTEM, RED, COVERAGE, CI BIND |
| `019ddb4a-25b4-78c1-bc2a-ec10e198cbfb` | codex | `feat/v109-yasha-multilingual` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019ddb7a-dc7c-74e1-a2ec-f8d7a3dffce5` | codex | `feat/v109-yasha-multilingual` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `17d1e50d-e2ed-4ec1-91c2-69e4ed0aebfd` | claude | `HEAD` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT |
| `55db6394-5cfb-43c9-a98e-1a22fcc4f612` | claude | `feat/v109-yasha-multilingual` | 1/8 | SPEC, PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, CI BIND |
| `a7556abc-da70-48d3-93bd-7e92e47cc7b4` | claude | `fix/ci-test-hardening` | 3/8 | SPEC, PREMORTEM, REFACTOR, COVERAGE, CI BIND |
| `e833951e-4ee3-46bb-9358-c231fcec90ed` | claude | `HEAD` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `d6e90edd-2588-4716-b6db-8f920cfed9e7` | claude | `HEAD` | 5/8 | SPEC, REFACTOR, REFLECT |
| `3764bc87-5b7c-49ae-9c72-84eb41777742` | claude | `feat/v109-yasha-multilingual` | 3/8 | PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `3fbe19c4-109e-4fe9-b46a-5cb875b09e4c` | claude | `feat/pipeline-sota-restructure` | 1/8 | SPEC, PREMORTEM, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `8268abcb-06e4-462f-b2dc-d859443631a0` | claude | `HEAD` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `5362e9af-8c18-40ca-b67c-1c5947ad7d48` | claude | `HEAD` | 3/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE |
| `26a96953-4586-49af-9f4c-a9e1c4cfc4e6` | claude | `fix/ci-manylinux-wheels` | 3/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE |
| `77905e27-b68a-43c7-ac98-2827375a0729` | claude | `feat/pipeline-sota-restructure` | 2/8 | PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `0307ece1-155f-4dc6-93bc-263e3f20ecc0` | claude | `feat/v109-yasha-multilingual` | 0/8 | SPEC, PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `019dea05-5849-7d82-83bf-65beeb8802cd` | codex | `feat/v109-yasha-multilingual` | 3/8 | PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `72048c5c-9104-4f87-bf26-26280adc8f00` | claude | `HEAD` | 7/8 | RED |
| `e34cbeb8-c795-4f68-9d19-76ace1a8da92` | claude | `feat/v109-yasha-multilingual` | 7/8 | RED |
| `019dea9c-718b-7be2-80d9-266f146582e8` | codex | `feat/v109-yasha-multilingual` | 2/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, CI BIND |
| `019dea9e-82bf-7c12-8bcb-31dec5bd5555` | codex | `feat/v109-yasha-multilingual` | 1/8 | SPEC, PREMORTEM, RED, REFACTOR, COVERAGE, REFLECT, CI BIND |
| `f542fb40-7829-4f1f-ab26-e632bd351130` | claude | `feat/v109-yasha-multilingual` | 1/8 | SPEC, PREMORTEM, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND |

## Trend
| window_start | window_end | matching_sessions | average_score |
|---|---|---:|---:|
| 2026-04-05 | 2026-04-12 | 0 | n/a |
| 2026-04-12 | 2026-04-19 | 12 | 1.92/8 |
| 2026-04-19 | 2026-04-26 | 12 | 2.08/8 |
| 2026-04-26 | 2026-05-03 | 43 | 2.19/8 |

4-week rolling average: `2.06/8`

## Top 3 Most-Missed Steps
- `REFACTOR`: missed in 40 of 43 matched sessions
- `COVERAGE`: missed in 40 of 43 matched sessions
- `PREMORTEM`: missed in 39 of 43 matched sessions

## SessionStart Banner Nudge
Forge-loop compliance is below 5/8. For implementation turns next week, start with: spec under `docs/superpowers/specs/`, 5 failure modes, failing test evidence, passing test evidence, acceptance-criteria-to-test mapping, `/simplify`, `/heidegger-reflect`, and CI green confirmation after push.

## Verification Evidence
- `find /home/shovalbe/.claude -type f -name '*.jsonl' -mtime -28`: located legacy Claude project/history transcripts in the 28-day window.
- `find /home/shovalbe/.codex/sessions -type f -name '*.jsonl' -mtime -7 | wc -l`: returned `25` at collection time.
- Parser input files seen: `156` total (`26` Claude, `130` Codex).
- Parser files within 28 days and at or before run timestamp: `79`; within 7 days: `49`.
- Matched implementation sessions in last 7 days: `43`.

## Method Notes
- Sessions were included only when user-side text contained one of: `implement`, `fix`, `add feature`, `build`, or `refactor`.
- Axis scoring used transcript evidence heuristics and command/order markers. Ambiguous evidence was scored as missing rather than inferred.
- `RED` was credited only when failing-test language appeared before the first detected edit/write tool marker; `GREEN` only after that marker.
