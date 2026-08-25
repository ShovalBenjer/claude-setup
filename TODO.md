# TODO: Claude OS Roadmap

Strategic objectives, key results, initiative tracker, and risk log for the Claude OS
harness. Status mirrors docs/prd/claude-os.md and docs/prd/autonomy-ecosystem.md.
Fresh session? Read docs/SESSION-BOOT.md first.

---

## Strategic objectives

### O1: Mature the harness

All oracles are mutation-covered, the gate runs green on main, and every configured domain
is enforced. No waivers without expiry and a confirmed falsifier.

**Key results**
- KR1.1: `gate.py run` exits 0 on `main` with zero waivers.
- KR1.2: Every oracle in `tools/` has a selftest and a mutation spec that catches all
         applicable mutations.
- KR1.3: CI runs the full gate on every PR and every push to `main`.
- KR1.4: Zero stale drift in `skills_sync`, `pointers`, `rules_sync`, and
         `settings.json` oracles.

### O2: Ship the review fabric

Dual-model PR reviews with agreement gate, provenance, and audit trail on all opt-in
repos. No PR ships without external review.

**Key results**
- KR2.1: Every Shoval-owned repo has PR review CI wired.
- KR2.2: Agreement gate posts a `gh pr review` comment with `_provenance` + audit trace.
- KR2.3: Disagreement produces a digest for operator review, not silent skip.
- KR2.4: Review persona registry is fully populated with contracts and reputation scores.

### O3: Close the memory loop

Prompt capture, intent resolution, typed memory, and learning-card emitter form a closed
loop from input to knowledge.

**Key results**
- KR3.1: Intent capture is live and records every prompt with content-covered hash.
- KR3.2: Intent resolution joins tickets to source prompts; resolve rate >80%.
- KR3.3: Typed memory taxonomy (decisions / episodes / procedures / taste) is populated
         and weekly-curated.
- KR3.4: Learning-card emitter files cards from shipped work to the learning platform queue.

### O4: Consolidate the estate

One canonical skills tree, all hooks wired to live settings, all standards bound to
enforcement, and every document with a declared status and owner.

**Key results**
- KR4.1: `dot-claude/skills` is the single canonical tree; all 45 diverged forks carry a
         recorded decision (merged / superseded / archived).
- KR4.2: Every hook in `dot-claude/hooks` is wired in `settings.json` or explicitly
         retired with reason.
- KR4.3: Every imported standard in `docs/standards/` is bound to a hook, gate domain,
         or CI job.
- KR4.4: `docs/DOCMAP.md` reachability is >80%; `docs/INDEX.md` is regenerated and
         ratcheted.

### O5: Enable the ventures

new-recruit and daily-deep-learning inherit a working harness via
`tools/harness/harness.py exec` and run their own gate.

**Key results**
- KR5.1: Both ventures consume the harness without vendoring.
- KR5.2: Both ventures run `gate.py run` green on their own `main`.
- KR5.3: Harness changes propagate to ventures via PR, not manual copy.
- KR5.4: Shared oracles (slop_lint, append_only, rules_sync) are tested against both
         venture trees.

---

## Initiative tracker

### I1: Harness reliability

- [ ] Fix the `review` CI job that posts "Claude encountered an error after ~40s" on
      every run. Root cause is unknown; next action is to read the `ANTHROPIC_LOG=debug`
      output, not add theories.
- [ ] Wire `skills_sync.py check` into CI with a real drift threshold (not waived).
- [ ] Wire `pointers.py scan` into CI as a named gate domain.
- [ ] Add a `settings.json` oracle that compares hook sets and script basenames against
      the committed payload, not paths.
- [ ] Extend ruff + mypy coverage from `intent-control-plane/` to `tools/` and `tests/`.
- [ ] Fix the `bus.py` selftest ledger pollution: workflow-spawned selftests must write to
      an isolated ledger.

### I2: Review fabric

- [ ] Wire `panel.py` to consume `allocate.py` so a diff touching only `.md` does not pay
      for the security rule set.
- [ ] Run two allocated actors blind to each other on one real PR. Acceptance is a
      `state/reviews/*.json` whose `reviewer` is not `persona-panel/local`.
- [ ] Implement the `agreement` domain in `quality-contract.json` for two-model approval.
- [ ] Deploy Gemini review workflow (`gemini-review.yml`) and verify it runs on a real PR.
- [ ] Attribute bot actions to a GitHub App identity instead of `ShovalBenjer (User)`.

### I3: Memory and intent

- [ ] Wire intent ticket state machine transitions at the two points that already know:
      claim row being written, and completion gate at Stop.
- [ ] Improve intent resolution rate from 226/467 to >80% by investigating the three
      failure modes (rotated transcripts, per-host slugs, alternate capture paths).
- [ ] Build the retrieval layer over `state/`: flat FTS5 plus brute-force cosine.
- [ ] Implement the learning-card emitter in the weekly self-improve cron.
- [ ] Backfill the 241 unresolved intent tickets once resolution is reliable.

### I4: Estate hygiene

- [ ] Resolve all 45 diverged skills across `dot-claude/`, `dot-codex/`, and `dot-agents/`
      with a recorded decision each.
- [ ] Deploy or retire `dot-agents` (no live `~/.agents` on this machine).
- [ ] Decide `dot-codex` fate: merge into canonical tree, deploy to live, or archive.
- [ ] Reconcile the two persona vocabularies (`panel.py` and registry) or document why
      they stay separate.
- [ ] Bind all 6 imported standards in `docs/standards/` to enforcement.
- [ ] Archive closed TODO items to `docs/archive/` and regenerate `docs/DOCMAP.md`.

### I5: Venture enablement

- [ ] Wire `tools/harness/harness.py` as the canonical resolver in both ventures.
- [ ] Run `gate.py run --project ../new-recruit` and fix all uncovered domains.
- [ ] Run `gate.py run --project ../daily-deep-learning` and fix all uncovered domains.
- [ ] Replace stale `C:/Users/shova/claude-setup/tools/...` paths in daily-deep-learning's
      contract with the central harness resolution.

### I6: Dashboard and observability

- [ ] Build the session dashboard (Tauri + React) on the decided stack (rusqlite + React).
- [ ] Wire ledger-watch push via `notify-debounced` for live query results.
- [ ] Add `cargo test --workspace` and `npm run build` to the gate's `coverage_map`.
- [ ] Implement FleetView v0 as the operator-owned status surface.

---

## Risk log

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CI billing wall blocks hosted-runner PR checks | High | High | Self-hosted runners for gate and falsifiability jobs; operator to resolve GitHub billing. |
| `dot-agents` has no deploy target on this machine | Certain | Medium | Archive or build `~/.agents` runtime. Do not add a fourth sync checker without a live target. |
| 45 diverged skills create merge debt | High | High | One decision per fork, recorded in `state/pile-manifest.jsonl`. Picking by timestamp is not a decision. |
| Intent capture loses prompts due to missing transcript paths | Medium | Medium | Investigate the three failure modes; backfill is cheap once resolution is reliable. |
| Review fabric latency exceeds session timeout | Medium | Medium | Dual review runs in parallel; agreement gate is async. Set realistic SLA on the digest. |
| Operator decisions block lane work | High | Medium | Document open blocks explicitly in `docs/analysis/` and escalate via `gt_escalate` when stuck >2 attempts. |
| SQLite WAL corruption on abrupt shutdown | Low | High | All ledgers use WAL mode with checkpoint cron. Test recovery procedure monthly. |
| `bus.jsonl` hash chain breaks due to clock skew | Low | High | Hash chain is self-healing on rerun; `bus.py verify` runs in CI. |
| MCP tool descriptions carry hidden instructions | Low | High | Add the connector description scan to `pointers.py` per INV-4. |

---

## Open blocks requiring operator action

These items cannot proceed without the operator. They are listed here because an analysis
nobody reads is an analysis nobody acts on.

1. **Rotate the API key** exposed in the `e695af5` commit history. The value in that commit
   is dead credential if the key was rotated, but git history retains the original value.
   Requires history rewrite + force push, or accept that the value persists in GitHub's
   default branch history.
2. **PR-fabric opt-in repo list.** Which repos get automated review? The operator's approval
   is required before enabling on any new target.
3. **WhatsApp copilot cadence.** 2x daily proposed; coaching retro frequency open.
4. **dot-agents deploy target.** Build `~/.agents` or archive the tree.
5. **dot-codex merge decision.** One tree or three? Affects all 45 forked skills.
6. **GitHub billing wall.** Hosted-runner jobs fail on every PR. Operator must resolve
   billing or expand runner fleet.
7. **Zion board throughput.** 31 epics, 0 closed. The board is not the thing other projects
   inherit. Decide whether an epic-only board with no task issues is the surface that gets
   used.

---

## Done

- [x] Repo relocated + July state synced + pushed (SETUP-OS #1)
- [x] CLAUDE-OS.md single source of truth (#2)
- [x] Notification fabric: phone push + desktop toast (#3)
- [x] Always-fresh PR review workflow on 22 repos (#4), auth pending
- [x] PRD + 8 ADRs + persona spec + INDEX (this doc set)
- [x] kernel-anchor hook: deep-work discipline injected every prompt, live+wired (#5 partial)
- [x] slop_lint gate (Antislop banlist), verified exit-1 on hits
- [x] Repo portfolio graph: 22 nodes / 72 edges -> d2 + sqlite (#15)
- [x] Git branch health sweep: 22 repos, 80 branches, 20 merged-deletable, 2 drift (#17)
- [x] Daily digest generator over live state + cron 7:03 (#6 partial: needs always-on Task Scheduler)
- [x] FULL work-setup import from work-archive-2026-07-12: 23 personas + 14 hooks + 36 skills + tower/intent bins + work-docs/ + intent-control-plane/ (2026-07-24)
- [x] Intent capture slice LIVE: UserPromptSubmit hook, `tools/intent/capture_turn.py`, writes `~/.intent` plus chained `state/prompt-tickets.jsonl`
- [x] Resource ledger LIVE: `tools/intent/resources.py` + scanner. Backfill wrote 3855 sightings across 2712 resources.
- [x] Autonomy Stop gate LIVE: completion_gate.py blocks a turn that ends by handing the decision back with no blocker named.
- [x] ADR-0010..0015 + PRD + spec + charters + SESSION-BOOT + lessons ledger seed
- [x] AUTO-01/02 hook fire-proof
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2)
- [x] /slop gate command (P1.5, deployed)
- [x] Memory + web write pipe (P1.3) - real card written + recalled
- [x] Blast-radius grapher (P1.4)
- [x] Live review demonstrated: PR #2, GitHub-Claude caught 4/4 seeded defects + 2 bonus
- [x] supply-chain CI job fixed (pinned to v2.3.8)
- [x] codemap flipping red on gate's own next run fixed (gitignored state/reviews/*.json)
- [x] Four of 55 skills-drift items were comparator bugs (CRLF vs LF) fixed
- [x] rules.rs was generated from live file, not committed one; fixed
- [x] pointers waiver deleted rather than renewed; fixed
- [x] CHAN-01: ADR-0018 two-tier inter-agent channel + round-trip fidelity oracle
- [x] AUTO-10: Gemini API key provisioned and verified
- [x] skills_sync.py check exits non-zero on drift (was exiting 0)
- [x] waiver confirm mechanism: gate runs waived domain's command and fails if falsifier string is gone
- [x] EXT-1: append-only-write oracle for state/*.jsonl built and gate-wired
- [x] EXT-2: risk-classified pre-action guard built and selftested
- [x] EXT-3: skill-routing accuracy measured and gate-wired
- [x] EXT-6: connector-use ledger built and wired live
- [x] ABSORB-01/09: prior-art record schema extended with absorbed + absorption_status fields
- [x] ABSORB-02a: Dolt-as-database rejected with reasons
- [x] ABSORB-04: just-my-skills coherence-governor 419 lines saved
- [x] ABSORB-06: coverage boundary stated so it is not read as exhaustive
- [x] EXT-6: connector-use ledger BUILT and wired live
- [x] GPU-C: Modal API key provisioned for training-interpretability lane
- [x] qwen-code PARKED (operator: no interactive logins)
- [x] GitHub Models LIVE (gh-models extension installed, 36-model catalog)
- [x] DOCS-01: docs/INDEX.md rewritten from 22 to 113 of 114 documents listed
- [x] REFUTE-01: refute.py run fixed for WSL (21 held, 5 refuted, 0 broken)
- [x] GATE-COV-1: fail-closed coverage declaration built and gate-wired
- [x] lane A: ship_gate_stop.py committed-docs-only case classified and tested
- [x] docs/archive structure created and 37 analysis documents migrated
- [x] docs/DOCMAP.md regenerated (983 documents, 68 reachable)
