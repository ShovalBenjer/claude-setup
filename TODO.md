# TODO: Claude OS

One TODO, grouped by layer, ticket-tagged (SETUP-OS + AUTO). Status mirrors
docs/prd/claude-os.md and docs/prd/autonomy-ecosystem.md. Fresh session? Read
docs/SESSION-BOOT.md first.

Read `docs/PLAN-SPINE.md` before picking up cross-surface work: it is the one
page connecting PRD to spec to current/next slice to ticket to % built, for
harness-gate, autonomy/AUTO, dashboard/DASH, voice/VOICE,
interpretability/Modal, persona-economy, intent-lifecycle, slm-swarm, and
kanban. Written 2026-08-17 glue pass, after a sweep found 26 planning docs
split BUILT 2 / PARTIAL 11 / PAPER 13 and no single spine.

## Active work

### INV: unfinished-work inventory

- [ ] INV-1 Execute the phased waterfall in
  `docs/analysis/2026-08-15-unfinished-work-inventory.md` (Phase 0 operator decisions
  first; Phase 2 quick hygiene is agent-doable).

### TELEMETRY: publish.py hardening (from Kilo review of PR #62, deferred 2026-08-12)

Operator decision 2026-08-12: telemetry should be OpenTelemetry, speced as part of
the communication / A2A layer, not grown as ad-hoc guards on publish.py.

- [ ] Spec: OpenTelemetry-based telemetry as part of A2A communication; decide what
  replaces collect.py/publish.py and what maps onto bus.py. Blocks the rows below
  from growing further.
- [ ] `post_discussion()` returns `r2.returncode` without checking the second GraphQL
  call's stdout; a data-level error with exit 0 advances the cursor and drops the batch
  silently. Guard like the first call. (kilo WARNING, PR #62 thread)
- [ ] `int(cfg["discussion"])` accepts 0 and negatives; fail fast on `number < 1`.
  (kilo SUGGESTION, PR #62 thread)

### REGISTRY: census re-verification (from Kilo review of PR #64, 2026-08-12)

- [ ] The 2026-08-12 registry rewire's census (39 ghosts removed, 19 skills assigned)
  is claimed in prose only. Add a check that re-parses gastown-company-registry.md
  with hooks/route.py parse_registry and diffs against ~/.claude/skills, so a future
  rewire ships with its measurement instead of a sentence about one.

### EXT: external landscape gaps (docs/analysis/2026-08-17-external-landscape-comparison.md)

- [ ] EXT-4 block/buzz follow-ups (docs/analysis/2026-08-17-repo-compare-block-buzz.md):
  WATCH rows for the ACP agent/tool protocol split and Nostr-signed per-agent audit
  events; re-check when a multi-agent server host or multi-principal threat model lands here

- [ ] DASH-1 Session dashboard, Tauri + React (docs/specs/2026-08-17-session-dashboard-direction.md):
  direction locked by operator 2026-08-17; build starts in its own worktree/PR,
  buzz clone as design anchor, ledger-read-only

- [ ] DASH-1 slice 1, program design (docs/specs/2026-08-17-session-dashboard-program-design.md):
  Rust ledger types, Tauri IPC contract, React component tree, five-slice plan.
  CORRECTIVE NOTE 2026-08-19: 39 dashboard/ files merged with no review artifact
  and no CI coverage; row 7 stays open. Gate coverage added 2026-08-19.

- [ ] BILL-1 GitHub Actions billing wall (found 2026-08-17 post-merge of PR #74):
  hosted-runner jobs on every PR fail in seconds with "recent account payments have failed
  or your spending limit needs to be increased". Operator-only: Settings, Billing and plans.
  Blocks browser-instrument-selftest and supply-chain on PRs 75/76/78/79/80.

### VOICE: unified voice channel

- [ ] VOICE-1 Unified voice channel for the workstation (operator, 2026-08-17):
  replace the type-into-a-.txt loop with STT in and TTS out. TTS works today via
  Windows System.Speech and the ElevenLabs MCP connector (VERIFIED live 2026-08-17).
  Engine choice is an OPEN OPERATOR BLOCK: Wispr Flow (endorsed) vs local Whisper.

### EXT-5: everything-claude-code watch items

- [ ] EXT-5 (docs/analysis/2026-08-17-repo-compare-everything-claude-code.md):
  the deterministic delivery-gate Stop-hook pattern, consolidated hook-dispatcher pattern,
  and git-remote-hash project scoping as a manually-gated tool.

### P-DASH: Dashboard / multi-session

- [ ] Evaluate adopting amirfish1/claude-command-center (MIT) as the missing
  session-dashboard layer (Kanban, spawn/resume, cost, cross-session).
  DO NOT rebuild (excavate-before-building).

### P3: Orchestration (L3)

- [ ] Scheduler consolidation; WSL systemd retired (#11); standing personas
- [ ] Concierge phone topology (#20)

### SETUP-PERSONA: reviewer allocation and identity

- [ ] PERSONA-02: only ONE actor declares `a11y`, so accessibility can never receive
  a decorrelated second opinion. Either a second actor declares it or the enum admits
  that a11y is single-opinion by construction.
- [ ] PERSONA-03: `panel.py` runs all five local personas on every change regardless
  of what changed. Wire it to consume `allocate.py`, so a diff touching only `.md`
  does not pay for the security rule set.
- [ ] PERSONA-05: ADR-0012's `auto:low` auto-merge is gated on a both-model approval
  that does not exist. Either build it or amend ADR-0004 and ADR-0012.
- [ ] PERSONA-06: run two allocated actors blind to each other on one real PR.
  Acceptance is a `state/reviews/*.json` whose `reviewer` is not `persona-panel/local`.
- [ ] PERSONA-07: every agent is `ShovalBenjer (User)`. A GitHub App per lane gives
  feed comments and PRs a `[bot]` identity.
- [ ] PERSONA-10: decorrelation is DECLARED, not measured. `allocate.py` hard-codes
  a hand-declared family string as a proxy. Run two actors on the same diff and
  observe the correlation.

### 2026-08-23 (lane A): prompts triaged, docs archived, WhatsApp links ledgered

- [ ] Every claude-setup prompt now has a checklist box on one of 18 themed issues,
  #91 to #108. Method in `docs/analysis/2026-08-23-prompt-triage.md`.
  Next: a session per theme moves boxes to OPEN.
- [ ] Saved-link triage, issue #90. 15 WhatsApp repos and 9 links with no verdict;
  `docs/analysis/2026-08-23-whatsapp-links-vs-plan.md`. 113 of 125 external-repo rows
  are `untriaged`.
- [ ] Dedup the books corpus by content hash in books-ingest; install calibre for mobi,
  djvulibre for djvu.
- [ ] Build the dashboard SQL tab on the stack decided in
  `docs/analysis/2026-08-23-dashboard-stack-and-supply-chain.md`.
- [ ] Pocock adopt queue from `docs/analysis/2026-08-23-pocock-skills-delta.md`:
  wait-what imported and live; still open: to-questionnaire, wizard,
  resolving-merge-conflicts. Also open: five 08-01 teardown follow-ups.
- [ ] `resources.py verify` breaks at row 3893 and nothing runs it (L-2026-08-23-a).
  Decide: add it to the gate as a domain, or stop calling the ledger chained.
- [ ] lane A: ship_gate_stop.py committed-docs-only case. DONE 2026-08-13.
  The 2026-08-13 docs-only fix classifies the WORKING diff vs HEAD, so a clean tree
  whose only delta since the last gated run is committed docs still hard-blocks.

<!-- prompt-tickets:begin generated by tools/intent/render_todo.py, do not hand-edit -->

## Prompt inbox: repo

No prompt tickets recorded for `repo`. Either nothing was typed against this checkout, or capture is not running here.

<!-- prompt-tickets:end -->

### Recent items (2026-08-19 and later)

- [ ] EXT-7 Gate-run hash-chaining, sabotage-resistance for the reporting chain
  (2026-08-19, external review via Agentica): extend the existing bus.jsonl
  hash-chain pattern to gate EXECUTIONS, so every gate.py run writes a signed
  append-only record. Operator decision needed: build now, defer, or decline.
  Recovered 2026-08-23 from worktree-rules-sync-repo-stack-reasoning.

- [ ] Issue and milestone reasoning is done, GitHub writes are not.
  See `docs/analysis/2026-08-23-issue-and-milestone-reasoning.md` for the full pass
  over all 56 open issues: which EPICs are still live vs done vs under-evidenced,
  why M1-M5 are kept, why T01-T18 prompt-triage series is the freshest layer.
  `state/prompt-tickets.jsonl` is 2313 rows 100% still CAPTURED with zero ever
  transitioned to TRIAGED. No issue was closed or edited; awaits operator sign-off.

### Ongoing structural items

- [ ] AUTO-06 ecosystem.db bootstrap from intent-control-plane schema + tools/eco/db.py
  (unblocks work-claims AUTO-04 + FleetView AUTO-19)
- [ ] AUTO-09 Scale nightly to tier-1 repos after 7 clean days
- [ ] AUTO-11 Merge-policy labels + auto-merge for auto:low
- [ ] AUTO-15: split resume rails into verifiable rows
- [ ] AUTO-18: register the real tasks (daily digest 07:03, weekly self-improve)
  and observe one unattended fire

- [ ] HOOKGATE-01 The compiled force-push rule disagrees with the live one.
  `python tools/hookgate/regen_rules.py` closes it in one command.

- [ ] HOOKPATH-01 A UserPromptSubmit hook FAILS CLOSED on a missing file and blocks
  the operator's prompt outright. Fixed for route.py by deploying it to
  ~/.claude/hooks/route.py; the other two hooks need a real deploy step.

- [ ] GATE-LOOP-01 `codemap` and `review` cannot both be green at the same time.
  Leave panel artifact uncommitted and codemap fails by one file; commit it and
  HEAD moves, so review fails. Fix is one of: have codemap exclude gate outputs,
  or key the review artifact by tree fingerprint.

- [ ] ABSORB-02 DoltHub option (c), the deferred half. Point-in-time reconstruction
  for ledgers that are gitignored. Concrete need exists: hiring_engine/ledger.sqlite
  holds 272 jobs with zero history.

- [ ] EXJOB-01 The 8 always-loaded global rules grounded in the ex-employer.
  RELABEL boundary-contracts, production-means-merged-and-smoked, read-whole-before-reasoning,
  hidden-trees. REWRITE foundry-deployment-per-project, pii-handling.
  RETIRE OR REFACTOR: jira-comment-drafting, repo-topology.

- [ ] PILE-01 The 29 forked skills, one decision each.
- [ ] PILE-02 The real architectural question behind "merge the dirs": dot-claude,
  dot-codex and dot-agents are payloads for THREE runtimes, so merging them into
  one source means the three runtimes share one tree.
- [ ] PILE-03 Session collision cost: two sessions, same day, same three problems,
  no shared state.

