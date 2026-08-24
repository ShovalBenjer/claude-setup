---
prd: intent-control-plane
ticket: none (internal platform brain)
status: active
owner: Shoval
created: 2026-07-11
---

# PRD: intent-control-plane (the platform brain)

The local-first intent ledger, retrieval, evidence, and self-improving-loop CLI behind the
session hooks. This table is the control plane; update status as work lands, do not spawn
dated notes. Companion to the estate PRD `~/docs/prd/2026-07-10-platform-standard.md` (this
package is its A2/A4/A5/A14/A16 implementation).

## Goal

Every turn's intent, proof requirement, and outcome is captured; retrieval surfaces content
not pointers; orchestration strategy and skill usage are measured and bias future decisions;
harness quality is trackable week over week. All local, tested, zero runtime deps.

## Stop condition

The CLI surface is packaged and reliable, the router/eval/policy/evolve loop is wired and
gate-enforced, and the repo meets the docs-control-plane standard.

## Acceptance table

Legend: done = verified live; partial = below bar; pending = not started.

| #   | Item | Status | Evidence |
|-----|------|--------|----------|
| P1  | Intent ledger + context pack + evidence CLI | done | schema.py + cli.py; `intent capture/extract/context-pack/evidence` |
| P2  | Router: keyword routes + corpus previews + usage-ranked skills | done | harness/router.py; corpus_snippets content, rank_by_usage |
| P3  | Six-dimension estate scorecard + project map (ast import graph) | done | standards.py, project_map.py; `intent repo-map` |
| P4  | Control-tower TUI (8 panels incl. context-degradation meter) | done | tower.py; `--once/--watch`, 244 tests |
| P5  | Skill-usage telemetry (populates session_events) | done | `intent log-skill` + PostToolUse hook wired |
| P6  | Strategy bandit (telemetry -> Beta -> cost-aware Thompson) | done | policy.py; `intent policy recommend`, `intent telemetry record` (ADR-0003) |
| P7  | sim2real cores wired + recorded (T4.1/4.3/4.4/4.7) | done | eval_cmds.py; `intent eval passk/kappa/trace-diff/tier1` |
| P8  | docs-to-contract retrieval | done | `intent retrieve` over ~/docs corpus (name+path+content) |
| P9  | Evolve tracker (golden-set delta, measurable weekly) | done | evolution.py; `intent evolve` |
| P10 | Local pre-commit gate (CI-BIND for a no-remote repo) | done | scripts/check.sh + .git/hooks/pre-commit; mypy --strict |
| P11 | Context-pack memory decay/entropy (relevance x freshness x novelty) | partial | see docs/specs; ranking is recency + lexical, decay/dedup pending |
| P12 | MCP adapter over the CLI (cross-agent surface) | pending | gated per ADR-0002 until the CLI surface is stable |
| P13 | Depth L3: population archive (stepping-stones + held-out keep gate + novelty) | done | archive.py + tests/test_archive.py (11 tests, 266 total green); spec AC-D1 [S1] |
| P14 | Company L4: per-persona scorecard + PIP/bench (asymmetric trust, significance guard) | done | company.py + tests/test_company.py (6 tests, 272 total green); spec AC-C1/C2 [S2] |
| P15 | Orchestration L2: guarded durable transitions over state_transitions | done | transitions.py + tests/test_transitions.py (7 tests, 279 total green); allow-list pass lifecycle, fail-closed, compensating revert; spec AC-O1/O2 [S3] |
| P16 | Depth L3: decomposed-rubric scorer + swarm_pass (deterministic-disposes) | done | rubric.py + swarm.py + tests (9 tests, 288 total green); deterministic-disposes, keep-if-better-and-novel, archive-all-as-stepping-stones, gradient_flat; spec AC-D2 [S4] |
| P17 | Depth L3: cost-aware per-pass bandit + advantage-conditioning | done | routing.py + tests/test_routing.py (7 tests, 295 total green); cost-aware select_model with hard budget cap (None=stop), RECAP advantage_exemplars + condition_prompt; spec AC-D3 [S5] |
| P18 | Layer 0: fix-commit provenance (SZZ + JIT risk + persona survival) | done | provenance.py + tests/test_provenance.py (7 tests incl. real-git smoke, 302 total green); classify + jit_risk + szz_link + survival_rate + persona rework/net-throughput; spec AC-F1/F2/F3 [S6] |
| P19 | Knowledge L1: tree-sitter symbol graph + graph_relevance | done | symbol_graph.py + tests/test_symbol_graph.py (4 tests, 306 total green); multi-lang extract_symbols (real tree-sitter) + pure graph_relevance; package is now zero-dep EXCEPT tree-sitter; spec AC-K1/K2 [S7] |
| P20 | Company L4: reflective rehire + grow-on-gap (human-gated) | done | roster_evolution.py + tests/test_roster_evolution.py (6 tests, 312 total green); propose_rehire/validate_rehire (held-out gate) + detect_coverage_gap + propose_new_persona; apply_roster_change refuses without human_approved; spec AC-C3/C4 [S8] |
| P21 | Anti-reward-hacking screen + scoped-diff + topology-fitness pre-check | done | guardrails.py + tests/test_guardrails.py (9 tests, 321 total green); reward_hacking_flags + is_scoped_diff + topology_fitness; spec constraints 6-7 |
| P22 | Fleet-init: read-only per-repo readiness scan (Phase 0, delegate-ready vs organize-first) | done | fleet_init.py + tests/test_fleet_init.py (5 tests, 326 total green); classify_dir + repo_readiness + scan_repo + fleet_report; ran live over ~/projects, 14 active repos, surfaced 4 repo-in-repo defects + fragmented TODOs |

## Premortem (5 failure modes)

1. Unwired scaffolds inflate confidence. Mitigation: every core reachable via a subcommand
   and gate-tested; `intent eval` wired P7.
2. The bandit optimizes an incomplete objective (solo's lead-context cost unmodeled).
   Mitigation: documented limit in ADR-0003; add a lead-context telemetry field.
3. Weekly evolve signal is noise without power. Mitigation: freeze the golden set, log volume.
4. cli.py re-bloats after the retrieval.py split. Mitigation: new command groups go to their
   own module (eval_cmds, policy, evolution), cli stays thin wiring.
5. Corp-production items (estate A6-A9) leak into this local repo. Mitigation: this package is
   local-only; Azure/ADO changes live in their own repos behind per-action OK.
