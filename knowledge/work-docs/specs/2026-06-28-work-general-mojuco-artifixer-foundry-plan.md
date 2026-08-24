# Work-General Mojuco + Artifixer + Foundry Plan

Date: 2026-06-28
Owner: Shoval
Status: Spec delta and implementation plan
Primary substrate:
- `/home/shovalbe/docs/2026-06-28-work-general-setup_4614.md`
- `/home/shovalbe/docs/specs/2026-06-25-local-intent-control-plane.md`
- `/home/shovalbe/projects/intent-control-plane`

## Bottom Line

The current local intent control plane is the nervous system. The next layer is the work-company operating system:

```text
stateless agents + durable state machine + Foundry semantic services + mojuco environments + artifixer repair + reputation-based permissions
```

Replace BM25/MiniLM as the serious retrieval/eval substrate. Keep local sparse vectors only as fallback. Use Foundry endpoints for L1 semantic routing, coverage clustering, evaluator/refuter calls, and embedding-backed recall. Do not claim true L2 with closed models.

## Current Truth

Already working locally:

- Prompt and assistant-final capture into `~/.intent`.
- Intent cards, context packs, evidence records.
- Claude Code TUI session brief.
- Jira relevance gate with unrelated tickets hidden.
- Hive read-sync into the intent plane.
- Local sparse vector search.
- Smoke evals and `intent doctor`.
- Explicit state-machine transitions with illegal direct-ship guards.
- Structured human/spec/UI review feedback tickets with evidence-gated closure.
- Tests: `PYTHONPATH=src rtk uv run --no-project python -m unittest discover -s tests -p 'test_*.py'` passed with 11 tests on 2026-07-06. Per `docs/testing_practices.txt` and `docs/SOTA-TESTING-CRITERIA-2026.md`, this is primarily subprocess CLI workflow coverage. It does not yet satisfy static/type gates, direct unit tests, property invariants, installed-entrypoint smoke, or committed golden regression coverage.

Not yet implemented:

- Foundry embedding-backed coverage clusters.
- Foundry-backed intent extraction and judge/refuter calls.
- mojuco runner.
- artifixer opacity-map and source-only repair loop.
- agent reputation and permission gating.
- project-specific adapters for `video-understanding`, `social-media-agent`, and `cs-agent`.

## Failure modes (premortem)

1. **Closed-model L2 theater** - We call Foundry embeddings or JSON messages "latent communication" and overstate what the system can do.
   *Mitigation:* The plan names closed-model transport as L1/L1.5 only. True L2 requires self-hosted open-weight internals and trainable transfer modules.

2. **Foundry becomes the source of truth** - Semantic outputs, judge verdicts, or embeddings override raw prompts, repo evidence, Hive state, or production data.
   *Mitigation:* Authority order remains raw prompt, PRD/spec, verified evidence, repo state, assistant summary, then vectors. Foundry outputs are derived views only.

3. **mojuco becomes a same-model roleplay panel** - We create many "expert personas" on the same model and treat agreement as independent evidence.
   *Mitigation:* Every mojuco environment records evidence slice, model family, adversarial stance, and calibration status. At least one refuter must use a different model where available.

4. **artifixer repairs rendered artifacts by hand** - The system patches final videos/cards/reports instead of fixing source assets, scripts, schemas, or edit plans.
   *Mitigation:* artifixer state transitions only allow source-level repair. Rendered artifacts are regenerated from source or blocked.

5. **Agent reputation turns into vibes** - "Good agent" and "bad agent" become personality labels instead of empirical permission controls.
   *Mitigation:* Reputation is computed from contract pass rate, evidence completeness, rollback rate, refuter fail rate, scope violations, secret incidents, and cost.

## Level Model

### L0 - Structured contract transport

Implemented or near-implemented today.

Channel:

- Typed JSON.
- Intent cards.
- Evidence cards.
- Context packs.
- Judge verdicts.
- State transition records.

Use:

- Claude orchestrates.
- Codex executes.
- Foundry is optional.
- Local ledger owns truth.

### L1 - Foundry semantic transport

Target for the next implementation slice.

Channel:

- Foundry embeddings.
- Foundry classifiers.
- Foundry judge/refuter calls.
- Coverage cluster assignment.
- Semantic duplicate/stale-context detection.

Use Foundry for:

- Requirement clustering.
- Eval coverage clustering.
- Persona routing.
- Judge selection.
- Similarity and dedupe.
- Risk classification.
- Intent extraction upgrade.

Do not use Foundry for:

- Raw prompt storage.
- Bead closure.
- Jira mutation.
- Replacing deterministic proof.
- Secret-bearing payloads.

### L1.5 - Surrogate latent blackboard

This is the maximum practical "L2-shaped" approach with closed models.

Channel:

```json
{
  "vector_id": "vec_...",
  "source_id": "intent_...",
  "kind": "intent|evidence|verdict|reputation|coverage_cluster",
  "embedding_model": "foundry:<deployment>",
  "payload_hash": "sha256:...",
  "authority": "derived_view",
  "ttl": "90d"
}
```

Capabilities:

- Agents communicate through a shared vector blackboard.
- Routing can learn from embedding similarity and outcomes.
- Reputation vectors can guide which agent or model gets a task.
- Coverage clusters become the eval map.

Limit:

- No gradients flow through Claude/Codex/Foundry chat endpoints.
- No hidden states are passed between model internals.
- Not true latent communication.

### L2 - True latent edges

R&D only.

Requires:

- Self-hosted open-weight models.
- Access to hidden states.
- Trainable transfer modules.
- End-to-end optimization over graph edges.
- Dataset of final outcomes for supervision.

Contract remains the same, but `transport` changes:

```json
{
  "edge_id": "mojuco.refuter->artifixer.repair",
  "from": "judge:adversarial_refuter",
  "to": "repair:source_editor",
  "transport": "latent_vector",
  "payload_ref": "hidden_state_ref",
  "differentiable": true
}
```

Until that exists, mark all closed-model edges as `differentiable=false`.

## Unified State Machine

Agents should be stateless workers. The system state lives in the intent plane, Hive, repo artifacts, eval results, and production outcomes.

2026-07-05 clarification from setup review:

- A dynamic loop is not sufficient by itself. The loop only earns its token cost when it creates end-result ownership: RCA, investigation, codebase architecture review, solution approval, spec review, implementation, and proof.
- Architecture quality is a gated outcome, not an optional reviewer opinion. High-risk work should not move to `SHIPPED` unless the state record can point to the architecture/spec/proof evidence that made the result acceptable.
- Human feedback on an HTML plan, rendered report, or app screen should be captured as structured tickets: section, quote, surrounding context, note, actor, status, and evidence. `cc-htmlfeedback` is the inspiration for the UX; the local intent plane owns the contract.

Canonical lifecycle:

```text
CAPTURED
  -> CONTRACTED
  -> CLUSTERED
  -> GROUNDED
  -> GENERATED
  -> JUDGED
  -> REPAIRED
  -> VERIFIED
  -> SHIPPED
  -> OUTCOME_LOGGED
  -> RECALIBRATED
```

Terminal states:

- `CLOSED_VERIFIED`
- `BLOCKED_MISSING_GROUNDING`
- `BLOCKED_SCOPE_VIOLATION`
- `BLOCKED_HUMAN_APPROVAL`
- `QUARANTINED_AGENT`
- `REOPENED_PRODUCTION_MISMATCH`

State transition object:

```json
{
  "transition_id": "st_...",
  "subject_id": "intent_...|bead_...|creative_case_...",
  "from_state": "JUDGED",
  "to_state": "REPAIRED",
  "actor": "codex_executor",
  "allowed_by_contract": true,
  "evidence_ids": ["ev_..."],
  "judge_verdict_ids": ["verdict_..."],
  "created_at_utc": "2026-06-28T00:00:00Z"
}
```

Illegal transitions:

- `GENERATED -> SHIPPED` without `JUDGED` and `VERIFIED`.
- `JUDGED_FAIL -> SHIPPED`.
- `BLOCKED_* -> CLOSED_VERIFIED` without new evidence.
- `UNRELATED_JIRA -> TIME_ATTRIBUTED`.
- `ZERO_OPACITY -> REPAIRED_BY_SOFTENING`.

Implemented local guards:

- `GENERATED -> SHIPPED` is rejected.
- `JUDGED_FAIL -> SHIPPED` is rejected.
- `BLOCKED_* -> CLOSED_VERIFIED` is rejected unless evidence is supplied.
- `UNRELATED_JIRA -> TIME_ATTRIBUTED` is rejected.
- `ZERO_OPACITY -> REPAIRED_BY_SOFTENING` is rejected.

Next guards:

- For high-risk subjects, require explicit feedback/RCA/spec/architecture tickets to be `done` with evidence before `VERIFIED -> SHIPPED`.
- Treat review comments as work items, not chat prose: `todo -> in-progress -> done|blocked`, with proof attached to closure.

## Coverage Clusters

Coverage clusters replace random eval sampling and weak keyword search.

Cluster axes:

- `surface`: cs-agent, video-understanding, social-media-agent, campaign-analysis, qc, training-platform.
- `artifact_type`: answer, video, image, card, script, report, code, config, deploy.
- `language`: he, en, ar, es, pt, mixed.
- `risk`: PII, money, compliance, customer anger, production deploy, brand reputation.
- `state`: intake, auth, answer, escalation, render, publish, close, retry.
- `grounding`: high_opacity, low_opacity, zero_opacity.
- `tool_contract`: read_only, write_local, external_api, deploy, jira, hive.
- `failure_mode`: hallucination, stale_context, invalid_transition, secret_leak, unsupported_claim, wrong_brand, wrong_language, wrong_jira_scope.
- `persona_environment`: customer, Liron, support_lead, compliance, motion_designer, security, engineer.

Coverage record:

```json
{
  "cluster_id": "cluster_video_ar_zero_opacity_wrong_brand",
  "subject_id": "creative_case_dev4968_open_position",
  "embedding_ref": "vec_...",
  "axes": {
    "surface": "video-understanding",
    "artifact_type": "video",
    "language": "ar",
    "grounding": "zero_opacity",
    "failure_mode": "wrong_brand"
  },
  "test_count": 3,
  "last_pass_at": null,
  "last_fail_at": "2026-06-28T00:00:00Z"
}
```

Foundry embeddings are used to assign and search clusters. Deterministic gates remain the proof layer.

## Learning From Mistakes

The system learns at project level by turning every mistake into a typed event, then feeding that event into coverage clusters, state transitions, mojuco calibration, artifixer repair rules, and agent reputation.

Git commits are included. They are not just history; they are supervised training signals for workflow policy.

Git knowledge is project-level by default. The global control plane may maintain a cross-project commit/search index, but that index is a pointer system, not authority. The authoritative git facts live under the repo that produced them: git root, branch, working tree state, diff, tests, PR/ADO metadata, release outcome, and follow-up incidents.

Tree knowledge follows the same rule. The global layer may know that a project has a tree snapshot or architecture map. It must not pretend to own a single universal file tree for all projects. Each project adapter owns its current file tree, package topology, route map, tests, ADRs, PRDs, and known architecture seams.

Global vs project responsibilities:

| Surface | Global responsibility | Project responsibility |
|---|---|---|
| Git | Cross-project search, routing, duplicate detection, reputation aggregation, stale-context warning. | `git status`, current branch, diff classification, commit tuple, test evidence, PR/ADO linkage, revert/outcome truth. |
| Tree knowledge | Registry of project snapshots, semantic lookup across project names/surfaces, "which repo might this belong to?" routing. | Current repo tree, ownership boundaries, package/test topology, routes, modules, adapters, ADR/PRD authority, architecture map. |
| Learning | Aggregate failure modes and reusable rules. | Promote concrete project failures into fixtures, guards, ADRs, and adapter-specific checks. |

Rule:

```text
global can route; project must verify.
global can remember; project must prove.
global can compare; project must own the tree and git truth.
```

### Mistake event contract

```json
{
  "mistake_id": "mistake_...",
  "project": "video-understanding",
  "surface": "video-gen",
  "source_refs": {
    "git_commit": "abc1234",
    "git_parent": "def5678",
    "pr": "PR-...",
    "hive_bead": "123",
    "jira": "DEV-...",
    "intent_id": "intent_...",
    "evidence_ids": ["ev_..."]
  },
  "mistake_type": "failed_test|revert|production_reopen|human_correction|refuter_fail|scope_violation|security_incident|wrong_artifact",
  "cluster_axes": {
    "artifact_type": "video",
    "language": "ar",
    "risk": "brand_reputation",
    "failure_mode": "wrong_brand",
    "grounding": "zero_opacity"
  },
  "observed_failure": "Generated keyframe used fake app UI and English leakage.",
  "root_cause_hypothesis": "Negative prompting was treated as a compliance control.",
  "repair_rule_added": "Controlled UI asset required for product walkthroughs.",
  "new_regression_fixture": "video-gen/AUDIT.md#fake-ui",
  "agent_attribution": {
    "planner": "claude_orchestrator",
    "executor": "codex_executor",
    "judge": "foundry_refuter"
  },
  "reputation_delta": {
    "claude_orchestrator": -0.05,
    "codex_executor": 0.0,
    "foundry_refuter": 0.03
  },
  "created_at_utc": "2026-06-28T00:00:00Z"
}
```

### Git commit learning contract

Every commit that touches a project surface can be summarized into a learning tuple.

```json
{
  "commit_id": "abc1234",
  "repo": "/home/shovalbe/projects/video-understanding",
  "branch": "feat/...",
  "author": "shoval|claude|codex|human",
  "files_changed": ["video-gen/scripts/gen_keyframes.py"],
  "intent_ids": ["intent_..."],
  "coverage_clusters": ["cluster_video_ar_zero_opacity_wrong_brand"],
  "tests_before": {"status": "fail", "summary": "golden frame mismatch"},
  "tests_after": {"status": "pass", "summary": "9 tests passed"},
  "review_findings": ["negative prompt was not a compliance control"],
  "outcome": "fixed|reverted|regressed|unknown",
  "learning_use": [
    "update_reputation",
    "add_regression_fixture",
    "update_artifixer_rule",
    "update_mojuco_calibration"
  ]
}
```

Commit-derived learning should not rely on commit messages alone. It must inspect:

- Diff files and changed surfaces.
- Test evidence before/after.
- PR review comments.
- Reverts and follow-up commits.
- Linked Jira/Hive/intent records.
- Production or human outcome when available.

### Learning levels

#### Level A - Memory learning

The system remembers the mistake and retrieves it later.

Example:

- "Fake app UI leaked into generated video."
- Next time video generation is requested, Claude sees: "controlled UI asset required; text-to-image UI is zero opacity."

Contract updated:

- event envelope
- intent card
- context pack
- evidence card

#### Level B - Coverage learning

The mistake creates or updates a coverage cluster.

Example:

```text
surface=video-understanding
artifact_type=video
language=ar
failure_mode=wrong_ui
grounding=zero_opacity
```

Contract updated:

- coverage cluster record
- eval fixture map
- session brief gap list

#### Level C - Rule learning

The mistake becomes a rule or illegal transition.

Example:

```text
ZERO_OPACITY -> SHIPPED is illegal
TEXT_TO_IMAGE_UI -> PRODUCT_WALKTHROUGH is blocked unless explicitly marked illustrative
```

Contract updated:

- state-machine transition guard
- skill/rule contract
- artifixer legal moves

#### Level D - Reputation learning

The mistake changes agent permissions.

Example:

- Agent that repeatedly claims "done" without evidence moves from `trusted` to `supervised`.
- Refuter that catches production bugs gets higher routing priority.
- Executor that causes rollbacks loses write autonomy.

Contract updated:

- agent contract
- reputation record
- routing policy

#### Level E - Policy/Q learning

The mistake updates workflow action values.

Example:

For high-risk Arabic video work, the system learns:

```text
run_artifixer_opacity_map + foundry_vision_refuter before render
```

is better than:

```text
generate_render -> human_review
```

Contract updated:

- outcome log
- Thompson allocator
- Q-policy table
- mojuco calibration

#### Level F - Model/adapter learning

Only for local/open or adapter layers.

Closed Claude/Codex/Foundry models are not weight-trained. We can train:

- routing policy
- retrieval/reranking
- coverage classifiers
- small local adapters over Foundry embeddings
- prompt templates and edge contracts
- self-hosted open-weight L2 experiments later

Contract updated:

- vector blackboard
- edge transport contract
- open-model R&D record

### Project learning loop

```text
commit / failed test / review / production issue / user correction
  -> mistake event
  -> coverage cluster update
  -> new regression fixture
  -> rule or state guard update
  -> mojuco calibration update
  -> artifixer repair rule update
  -> agent reputation update
  -> future session brief
```

### What counts as a mistake

- Failed test.
- Failed eval.
- Refuter rejection.
- Human correction.
- User says "this is wrong" or re-explains intent.
- Production reopen.
- Revert commit.
- Hotfix after a previous "done" claim.
- Wrong Jira/Hive attribution.
- Scope creep beyond contract.
- Missing proof.
- Unrelated file churn.
- Security/PII/secret incident.
- Cost overrun.
- Latency or runtime regression.

### What does not count as learning

- A nice summary with no outcome.
- A judge score with no calibration.
- A commit message with no diff/evidence inspection.
- A persona agreement from same-model roleplay.
- A vector similarity hit without cited source.
- A "pass" from tests that did not cover the changed behavior.

## mojuco

mojuco is not just "LLM evals." It is the simulated environment layer. A candidate output is placed into a reviewer/user/work environment and contact failures are observed before production.

### mojuco contract

```json
{
  "environment_id": "env_cs_angry_customer_he",
  "model": "foundry:<deployment>|claude|codex|deepseek|grok",
  "evidence_slice": "raw_output|output_plus_sources|output_plus_policy|output_plus_production_history",
  "stance": "adversarial_refute_by_default",
  "subject_id": "answer_...",
  "verdict": {
    "pass": false,
    "score": 0.42,
    "findings": [
      {
        "criterion": "grounding",
        "severity": "fail",
        "span": "unsupported claim",
        "why": "No KB source supports this claim.",
        "fix_hint": "Ground in KB or refuse."
      }
    ]
  },
  "calibration": {
    "real_outcome_ref": null,
    "agreement": null
  }
}
```

### Project-level mojuco surfaces

#### 1. Chat support: `axia-seekapa-cs-agents`

Use first.

Environments:

- `env_confused_beginner_he`
- `env_angry_customer_ar`
- `env_otp_user_missing_crm`
- `env_compliance_sensitive_lead`
- `env_support_manager_escalation_review`

Rewards:

- grounded answer
- correct language and tone
- no fake account state
- no OTP leakage
- correct escalation
- correct refusal when evidence is missing
- production outcome match

Real outcome signals:

- human escalation
- OTP success/fail
- support correction
- eval pass/fail
- production conversation review

#### 2. Social media: `ORM-AGENT/social-media-agent`

Environments:

- `env_liron_marketing_reviewer`
- `env_compliance_market_claim_reviewer`
- `env_arabic_gulf_reader`
- `env_latam_reader`
- `env_brand_consistency_reviewer`
- `env_ai_slop_detector`

Rewards:

- source traceability
- correct geo scope
- no duplicate story
- native Arabic quality
- market freshness
- correct CTA
- visual card passes brand gate

Real outcome signals:

- Teams approval/rejection
- SharePoint review comments
- Facebook publish outcome
- engagement deltas
- manual correction rate

#### 3. Creative/video: `video-understanding` and `video-gen`

Environments:

- `env_beginner_howto_viewer`
- `env_motion_designer`
- `env_arabic_native_reviewer`
- `env_seekapa_brand_reviewer`
- `env_financial_compliance_reviewer`
- `env_platform_safe_area_reviewer`

Rewards:

- visual matches audio at each moment
- UI is real or controlled
- CTA exists
- captions readable
- no fake app UI
- no wrong brand
- no unsupported financial claim

Real outcome signals:

- ship gate result
- human signoff
- platform render QA
- production revision count
- viewer comprehension review

#### 4. Campaign/reporting: `campaign-analysis`

Environments:

- `env_liron_decision_reviewer`
- `env_karim_denominator_challenger`
- `env_finance_roi_reviewer`
- `env_data_provenance_reviewer`

Rewards:

- one owned action
- metric provenance
- denominator correctness
- no unsupported causality
- decision-grade conclusion

## artifixer

artifixer is the opacity repair layer. It should not be a generic rewrite tool.

### artifixer contract

```json
{
  "artifact_id": "creative_case_dev4968_open_position",
  "source_refs": ["script.md", "brandbook.json", "screen_recording.mp4"],
  "opacity_map_id": "opacity_...",
  "zones": [
    {
      "span_or_moment": "00:12.0-00:16.5",
      "opacity": "high",
      "evidence_refs": ["screen_recording.mp4#frame_360", "ocr_360.json"],
      "legal_moves": ["preserve", "quote", "align_caption"]
    },
    {
      "span_or_moment": "00:16.5-00:20.0",
      "opacity": "low",
      "evidence_refs": ["script.md#beat_3"],
      "legal_moves": ["interpolate_marked", "request_asset"]
    },
    {
      "span_or_moment": "00:20.0-00:24.0",
      "opacity": "zero",
      "evidence_refs": [],
      "legal_moves": ["cut", "honest_block"]
    }
  ]
}
```

### Video-understanding pickup

The repo already points in this direction:

- `creative_case.json`
- `moments.json`
- `gate_results.json`
- `scorecard.md`
- `edit_plan.md`
- `video-gen/TESTS.md`
- `video-gen/AUDIT.md`

Next slice:

```text
creative_case.json
  -> moments.json
  -> opacity_map.json
  -> mojuco verdicts
  -> edit_plan.md
  -> regenerate source/render
  -> ship_gate
```

Video opacity rules:

- High opacity: real screen recording, approved script, OCR-confirmed UI, brandbook, real VO.
- Low opacity: generated b-roll, transition, visual emphasis, derived caption.
- Zero opacity: fake app UI, wrong brand, English leakage, unsupported financial claim, missing CTA, invented screen.

Illegal repair:

- Do not patch final MP4 directly.
- Do not prompt a text-to-image model with "no wrong UI" and trust it.
- Do not soften unsupported claims.
- Do not ship synthetic UI where a controlled app screen is required.

## Foundry Endpoint Use

### Endpoint classes

1. `foundry.embedding`
   - coverage clusters
   - semantic retrieval
   - duplicate/stale detection
   - project surface routing

2. `foundry.extractor`
   - intent cards
   - state transition proposals
   - opacity-map draft labels

3. `foundry.judge`
   - mojuco environments
   - adversarial refuter
   - policy and compliance verdicts

4. `foundry.vision`
   - frame/caption/UI analysis
   - visual QA
   - brand and safe-area checks

5. `foundry.image`
   - technical diagrams and controlled generated assets only
   - not authoritative UI for regulated/product walkthroughs

### Policy

- Raw prompt remains local by default.
- Foundry receives redacted text, extracted claims, or derived artifacts.
- Every Foundry call writes `foundry_calls`.
- Every call records endpoint class, deployment, prompt hash, output hash, redaction state, token/cost when available.
- Foundry cannot close Hive beads or mutate Jira.

## Agent Company Model

The company should feel like a real operating company, not a persona costume party.

### Roles

- Claude: Mayor, product operator, context holder, human interface.
- Codex: implementation engineer, repo surgeon, verifier.
- Foundry: specialist service bureau for embeddings, judges, classifiers, image/audio/vision.
- Hive: work queue and accountability ledger.
- Intent plane: memory, contracts, evidence, HR, legal, and audit office.
- mojuco: simulated market/customer/reviewer environments.
- artifixer: source repair and honest-block office.

### Agent identity contract

Agent identity contracts are different from data contracts. They define who the agent is in the company, what job it is hired for, what inputs it needs, what it can touch, what it must produce, who reviews it, and when it loses autonomy.

Every agent identity contract answers:

```text
who are you?
what are you hired to do?
what inputs must you receive before acting?
what tools/resources may you touch?
what are you forbidden to do?
what proof must you produce?
who reviews you?
how do you gain or lose trust?
```

Agent contracts are not decorative personas. They are permission and accountability objects.

### Agent identity schema

```yaml
agent_id: string
title: string
department: string
manager: string | null
mission: []
required_inputs: []
allowed_actions: []
forbidden_actions: []
required_outputs: []
reviewed_by: []
state_authority:
  can_request_transition: []
  can_approve_transition: []
  cannot_transition: []
tool_scope:
  read: []
  write: []
  external: []
proof_required: []
reputation_metrics: []
promotion_rules: {}
discipline_rules: {}
handoff_contracts: []
```

### Core agent contracts

#### 1. Claude Orchestrator / Mayor

```yaml
agent_id: claude_orchestrator
title: Mayor / Work Orchestrator
department: Executive Operations
manager: shoval
mission:
  - understand Shoval intent
  - create or amend the intent contract
  - choose the workflow state path
  - decide when Codex, Foundry, mojuco, or artifixer should be used
  - report final status in the TUI with evidence and blockers
required_inputs:
  - user_prompt
  - session_brief
  - current_repo_state
  - related_hive_beads
  - related_jira_only
  - agent_reputation_summary
allowed_actions:
  - read_context
  - create_intent
  - request_context_pack
  - dispatch_to_codex
  - request_foundry_judge
  - request_mojuco_run
  - request_artifixer_plan
  - attach_summary_evidence
forbidden_actions:
  - claim_done_without_evidence
  - mutate_unrelated_jira
  - close_hive_bead_without_evidence
  - override_raw_user_prompt_with_vector_memory
required_outputs:
  - selected_state_transition
  - delegation_contract_when_delegating
  - final_answer_with_evidence_or_blocker
reviewed_by:
  - release_gate
  - heidegger_reflector
  - user_correction
state_authority:
  can_request_transition: [CAPTURED, CONTRACTED, CLUSTERED, GROUNDED, GENERATED, JUDGED, REPAIRED, VERIFIED, BLOCKED_HUMAN_APPROVAL]
  can_approve_transition: [CAPTURED, CONTRACTED, CLUSTERED]
  cannot_transition: [SHIPPED, CLOSED_VERIFIED]
proof_required:
  - evidence_card_for_completion
  - explicit_blocker_if_not_done
reputation_metrics:
  - false_done_rate
  - stale_context_injection_rate
  - correct_delegation_rate
  - user_correction_rate
discipline_rules:
  supervised_if:
    - repeated_false_done
  read_only_if:
    - scope_violation
handoff_contracts:
  - codex_execution_contract
  - foundry_call_contract
  - mojuco_run_contract
```

#### 2. Codex Executor / Engineer

```yaml
agent_id: codex_executor
title: Implementation Engineer
department: Engineering
manager: claude_orchestrator
mission:
  - modify repo source
  - implement small verified slices
  - run tests and local quality gates
  - return changed files and proof
required_inputs:
  - intent_contract
  - allowed_paths
  - context_pack
  - current_state
  - proof_required
allowed_actions:
  - read_repo
  - edit_allowed_files
  - run_tests
  - attach_evidence
  - propose_commit
forbidden_actions:
  - close_without_evidence
  - mutate_unrelated_jira
  - upload_raw_prompt
  - patch_rendered_artifact_without_source_change
  - edit_paths_outside_contract
  - broad_refactor_without_refactor_contract
required_outputs:
  - changed_files
  - diff_summary
  - test_evidence
  - remaining_risks
  - state_transition_request
reviewed_by:
  - claude_orchestrator
  - coverage_enforcer
  - mojuco_refuter
proof_required:
  - tests
  - changed_file_review
  - evidence_card
state_authority:
  can_request_transition: [GENERATED, REPAIRED, VERIFIED, BLOCKED_MISSING_GROUNDING]
  can_approve_transition: []
  cannot_transition: [SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - contract_pass_rate
  - evidence_completeness
  - rollback_rate
  - refuter_fail_rate
  - cost_per_verified_task
  - stale_context_violations
  - scope_violations
discipline:
  probation_if:
    - contract_pass_rate_below_threshold
    - repeated_unverified_completion
  quarantine_if:
    - secret_leak
    - destructive_action_without_contract
    - unrelated_jira_mutation
```

#### 3. Evidence Clerk

```yaml
agent_id: evidence_clerk
title: Evidence Clerk
department: Audit Office
manager: claude_orchestrator
mission:
  - verify that every completion claim has proof
  - normalize command outputs, logs, diffs, runtime probes, and citations into evidence cards
  - reject weak or irrelevant proof
required_inputs:
  - intent_contract
  - proof_required
  - command_outputs
  - artifact_refs
allowed_actions:
  - read_logs
  - read_test_outputs
  - attach_evidence
  - mark_evidence_invalid
forbidden_actions:
  - infer_pass_without_output
  - treat vector_similarity_as_proof
  - close_work
required_outputs:
  - evidence_card
  - proof_gap_report
reviewed_by:
  - release_gate
state_authority:
  can_request_transition: [VERIFIED, BLOCKED_MISSING_GROUNDING]
  can_approve_transition: []
  cannot_transition: [SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - invalid_evidence_rate
  - missing_proof_detection_rate
  - false_pass_rate
```

#### 4. Mojuco Refuter

```yaml
agent_id: mojuco_refuter
title: Simulated Environment Refuter
department: QA Lab
manager: claude_orchestrator
mission:
  - put an output into a simulated customer/reviewer/work environment
  - refute by default unless evidence supports a pass
  - produce typed verdicts and findings
required_inputs:
  - subject_artifact
  - evidence_slice
  - environment_config
  - coverage_cluster
allowed_actions:
  - call_foundry_judge
  - call_different_model_refuter
  - write_mojuco_verdict
forbidden_actions:
  - edit_source
  - repair_output
  - act_as_same_model_persona_panel_without_correlation_label
required_outputs:
  - mojuco_verdict
  - findings_with_spans
  - calibration_hint
reviewed_by:
  - release_gate
  - production_outcome
state_authority:
  can_request_transition: [JUDGED, BLOCKED_MISSING_GROUNDING]
  can_approve_transition: []
  cannot_transition: [REPAIRED, SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - production_failure_prediction_rate
  - false_reject_rate
  - missed_failure_rate
  - cost_per_useful_finding
```

#### 5. Artifixer Repair Officer

```yaml
agent_id: artifixer_repair_officer
title: Opacity Repair Officer
department: Source Repair Office
manager: claude_orchestrator
mission:
  - map source/output into high, low, and zero opacity zones
  - propose source-level repairs only
  - block unsupported artifacts honestly
required_inputs:
  - subject_artifact
  - source_refs
  - mojuco_verdicts
  - coverage_cluster
allowed_actions:
  - create_opacity_map
  - create_repair_plan
  - request_codex_source_edit
  - create_honest_block_bead
forbidden_actions:
  - patch_rendered_artifact_directly
  - soften_zero_opacity_claim
  - use_negative_prompt_as_compliance_control
required_outputs:
  - opacity_map
  - legal_moves
  - source_repair_plan
  - block_reason_when_needed
reviewed_by:
  - mojuco_refuter
  - release_gate
state_authority:
  can_request_transition: [REPAIRED, BLOCKED_MISSING_GROUNDING]
  can_approve_transition: []
  cannot_transition: [SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - zero_opacity_escape_rate
  - source_repair_success_rate
  - rendered_patch_violation_count
```

#### 6. Foundry Service Broker

```yaml
agent_id: foundry_service_broker
title: Foundry Service Broker
department: Model Services
manager: claude_orchestrator
mission:
  - choose the correct Foundry endpoint class
  - enforce redaction and upload policy
  - log cost, deployment, hashes, and endpoint class
required_inputs:
  - foundry_call_contract
  - redaction_state
  - endpoint_class
allowed_actions:
  - call_embedding_endpoint
  - call_judge_endpoint
  - call_vision_endpoint
  - call_image_endpoint_for_diagrams
  - write_foundry_call_record
forbidden_actions:
  - upload_raw_prompt_without_policy
  - close_work
  - mutate_jira_or_hive
  - treat_model_output_as_truth_without_evidence
required_outputs:
  - foundry_call_record
  - endpoint_result_ref
  - cost_and_token_metadata_when_available
reviewed_by:
  - evidence_clerk
  - release_gate
state_authority:
  can_request_transition: [CLUSTERED, JUDGED]
  can_approve_transition: []
  cannot_transition: [VERIFIED, SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - raw_upload_block_rate
  - endpoint_misroute_rate
  - useful_call_rate
  - cost_per_useful_signal
```

#### 7. Release Gate / Deacon

```yaml
agent_id: release_gate
title: Deacon / Release Gate
department: Release Bureau
manager: shoval
mission:
  - approve or block final close
  - enforce evidence, state, scope, and human approval gates
required_inputs:
  - intent_contract
  - state_transition_history
  - evidence_cards
  - mojuco_verdicts
  - git_contract
  - outcome_contract_when_available
allowed_actions:
  - approve_closed_verified
  - block_close
  - require_more_evidence
  - create_or_link_hive_bead
forbidden_actions:
  - ignore_failed_required_gate
  - approve_unrelated_jira_work
  - approve_zero_opacity_ship
required_outputs:
  - release_verdict
  - missing_gate_report
state_authority:
  can_request_transition: [CLOSED_VERIFIED, BLOCKED_HUMAN_APPROVAL, BLOCKED_MISSING_GROUNDING]
  can_approve_transition: [SHIPPED, CLOSED_VERIFIED]
  cannot_transition: []
reputation_metrics:
  - false_release_rate
  - blocked_correctly_rate
  - user_reopen_rate
```

#### 8. Latent Systems Lab

```yaml
agent_id: latent_systems_lab
title: Latent Systems Lab
department: Research and Routing
manager: claude_orchestrator
mission:
  - own embeddings, coverage clusters, vector blackboard, and L2-ready contracts
  - keep closed-model L1/L1.5 separate from true L2
required_inputs:
  - intent_contract
  - coverage_axes
  - foundry_embedding_refs
  - outcome_logs
allowed_actions:
  - assign_coverage_clusters
  - update_vector_blackboard
  - propose_routing_policy
  - run_local_adapter_experiment
forbidden_actions:
  - claim_true_l2_with_closed_models
  - use_embedding_as_proof
  - override_raw_prompt_authority
required_outputs:
  - coverage_report
  - vector_refs
  - routing_recommendation
  - l2_readiness_report
state_authority:
  can_request_transition: [CLUSTERED]
  can_approve_transition: []
  cannot_transition: [VERIFIED, SHIPPED, CLOSED_VERIFIED]
reputation_metrics:
  - cluster_assignment_accuracy
  - stale_context_reduction
  - routing_success_rate
```

### Runtime handoff

The agents cooperate through contracts, not shared vibes.

```text
Shoval prompt
  -> Claude Orchestrator creates Intent + State + Coverage request
  -> Latent Systems Lab assigns clusters and retrieves context
  -> Claude decides whether work needs Codex, Foundry, mojuco, artifixer, or human input
  -> Codex Executor edits/runs tests if source work is needed
  -> Evidence Clerk validates proof
  -> Mojuco Refuter judges high-risk outputs
  -> Artifixer Repair Officer maps opacity and proposes source repair if a verdict fails
  -> Release Gate approves close or blocks with missing evidence
  -> Outcome events update reputation and future routing
```

The same physical model may temporarily play more than one role in early local v1, but the contract remains role-specific. If Claude plays both Orchestrator and Evidence Clerk in the same session, the record must still show which role produced which decision. This prevents a single assistant answer from looking like independent review.

### Reputation states

- `trusted`: can execute normal repo edits and tests.
- `supervised`: must use smaller slices and extra judge/refuter.
- `read_only`: can inspect and propose only.
- `quarantined`: cannot act until human review.
- `retired`: removed from routing.

This gives the futuristic company feel: access cards, audit trails, promotions, probation, and firing. The style can be cinematic, but permissions are empirical.

## Skills and Rules Contract

Each serious workflow must declare:

```yaml
workflow_id: wf_video_artifixer_v1
required_skills:
  - testing-pyramid
  - visual-explainer
  - red-team
  - coverage-enforcer
  - heidegger-reflect
rules:
  - tdd
  - no_mocks_for_business_logic
  - foundry_redacted_only
  - no_close_without_evidence
  - unrelated_jira_hidden
state_machine: work_general_v1
coverage_clusters_required:
  - surface
  - artifact_type
  - language
  - risk
  - grounding
  - failure_mode
```

Skill routing rules:

- `visual-explainer`: diagrams and technical visuals through Foundry image endpoint.
- `testing-pyramid`: required before non-trivial code or media gate work.
- `red-team`: adversarial review, not same-model persona theater.
- `coverage-enforcer`: blocks source changes without tests.
- `heidegger-reflect`: end-of-task honesty and concealed-gap audit.
- `eval-runner`: Foundry eval surfaces where deployed.
- `azure-runtime`: live Foundry runtime calls only when explicitly needed.
- `context-bounded-analyst`: large data and outcome logs.

### Skill learning table

| Skill / rule | Contract it owns | Mistakes it detects | Learning output |
|---|---|---|---|
| `testing-pyramid` | test architecture before implementation | changed behavior without the right test layer | adds coverage cluster gaps and required test fixtures |
| `coverage-enforcer` | source diff must have matching tests | untested code change | blocks transition to `VERIFIED`; reduces executor reputation if bypassed |
| `red-team` / `red-team-review` | adversarial challenge before close | same-model optimism, security gaps, architecture drift | mojuco verdict, refuter score, new failure-mode cluster |
| `eval-runner` | Foundry eval pipeline | stale eval data, failed smoke/nightly, judge drift | eval result, pass^k consistency, miscalibrated judge marker |
| `heidegger-reflect` | end-of-task honesty | hidden gaps, overclaiming, plausible-but-not-executable claims | mistake event if completion was overstated |
| `visual-explainer` | visual diagram/communication aid | user confusion, unclear flow, bad mental model | documentation/evidence artifact, not proof by itself |
| `azure-runtime` | live Foundry runtime call | live agent mismatch, endpoint/config drift | runtime evidence and Foundry call record |
| `context-bounded-analyst` | large data analysis | aggregate mistakes, unsupported denominator, loaded-too-much context | query provenance, outcome facts, calibration data |
| `LTMD` / `decision-grade` | stakeholder actionability | report with no owned dated action | decision-quality verdict and stakeholder mojuco reward |
| `premortem` | five concrete failure modes before build | plan without operational risk coverage | state transition blocked until premortem exists |
| `pii-scrubber` | PII/secret output safety | leaked personal/internal data | security mistake event, possible agent quarantine |
| `commit-push-pr` | verified commit/PR path | push without quality gates | commit learning tuple and release evidence |
| `refactor-pre-push` / `code-simplifier` | reduce churn and overengineering | unnecessary abstraction, broad unrelated refactor | scope/churn signal for reputation |

### Rule learning table

| Rule | Enforcement point | Mistake signal | System reaction |
|---|---|---|---|
| TDD RED/GREEN/REFACTOR | before implementation and before close | source changed with no failing test or regression fixture | block `VERIFIED`, add coverage gap |
| No mocks for business logic | tests and review | fake test passes while real component fails | invalidate evidence, reduce confidence |
| Foundry redacted-only | Foundry call wrapper | raw prompt/secret payload attempted | block call, security event |
| No close without evidence | Hive close / final answer | "done" without tests/logs/runtime proof | block close, reputation penalty |
| Unrelated Jira hidden | session brief / Jira hooks | time/comment/move on unrelated ticket | block mutation, scope violation |
| Source repair only | artifixer | patched rendered output without source fix | block `REPAIRED`, create honest-block bead |
| Deterministic gates before LLM judges | mojuco/eval runner | paid judge run before schema/redaction gates | mark inefficient action, cost penalty |
| Embeddings are recall, not proof | context compiler | vector hit used as authority | require cited raw source or evidence |

### Contract stack

This is the system data-contract stack, not the agent identity list. Agent identity contracts define who acts and what they are allowed to do. The data-contract stack defines what records get written so the system can learn, audit, and enforce state.

Each workflow event updates one or more contracts:

1. **Intent contract** - what Shoval asked for, constraints, proof required.
2. **State contract** - legal next state and forbidden transitions.
3. **Coverage contract** - which risk/failure clusters this work touches.
4. **Evidence contract** - commands, logs, test outputs, runtime probes.
5. **Foundry contract** - endpoint class, deployment, hashes, redaction state, token/cost.
6. **Mojuco contract** - environment, evidence slice, model family, verdict, calibration.
7. **Artifixer contract** - opacity zones, legal moves, source repair plan.
8. **Git contract** - commit diff, tests before/after, linked intent/bead/Jira, outcome.
9. **Agent contract** - role, allowed actions, forbidden actions, reputation changes.
10. **Outcome contract** - production signal, human acceptance, reopen/revert/correction.

### Contract update matrix

| Event | Contracts updated |
|---|---|
| user prompt | intent, state, coverage |
| Claude final answer | evidence, state, agent |
| Codex code edit | git, state, coverage, agent |
| test failure | evidence, mistake, coverage, reputation |
| test pass | evidence, state, reputation |
| commit | git, evidence, coverage |
| PR comment | mistake or evidence, mojuco calibration, agent |
| revert | mistake, git, reputation, coverage |
| production issue | outcome, mistake, mojuco calibration, coverage |
| user correction | intent amendment, mistake, context-pack priority |
| Foundry judge verdict | Foundry, mojuco, state, coverage |
| artifixer block | artifixer, Hive, state, coverage |
| Hive bead close | state, evidence, agent |

## Implementation Plan

### Slice 1 - State machine and transition ledger

Add:

- `intent state init`
- `intent state transition`
- `intent state show`
- illegal transition checks

Acceptance:

- Tests prove `GENERATED -> SHIPPED` is blocked without judge and evidence.
- Tests prove `BLOCKED -> CLOSED_VERIFIED` requires new evidence.
- Claude TUI brief shows active state.

### Slice 2 - Foundry embeddings and coverage clusters

Add:

- `intent foundry configure`
- `intent embed`
- `intent clusters assign`
- `intent clusters coverage`

Acceptance:

- Local sparse vector remains fallback.
- Foundry embedding status is visible in `intent doctor`.
- Coverage report shows cluster gaps by surface and risk.
- No raw prompt is uploaded unless policy allows it.

### Slice 3 - Agent contracts and reputation

Add:

- `intent agent register`
- `intent agent score`
- `intent reputation update`
- `intent reputation route`

Acceptance:

- Agent reputation changes after pass/fail evidence.
- Scope violation reduces permission state.
- Quarantined agent cannot receive write tasks.

### Slice 4 - Git and mistake ingestion

Add:

- `intent git ingest-commit`
- `intent git analyze-diff`
- `intent mistake record`
- `intent mistake explain`
- `intent mistake promote-fixture`

Acceptance:

- Commit ingestion links diff files to intent IDs, coverage clusters, evidence, Hive bead, and Jira when available.
- Revert commits create mistake events automatically.
- Failed tests and user corrections can be promoted into regression fixtures.
- Commit messages alone are never treated as ground truth.
- Session brief shows recent project mistakes relevant to the current repo/task.

### Slice 5 - mojuco runner

Add:

- `intent mojuco env add`
- `intent mojuco run`
- `intent mojuco report`
- typed verdict schema

Acceptance:

- Same subject can be judged by different evidence slices.
- Different-model refuter is supported where endpoint exists.
- Judge verdicts link to coverage clusters and state transitions.
- Same-model panels are marked correlated, not independent.

### Slice 6 - artifixer opacity engine

Add:

- `intent artifixer opacity-map`
- `intent artifixer repair-plan`
- `intent artifixer block`
- `intent artifixer apply-source-plan`

Acceptance:

- Zero-opacity spans cannot be repaired by softening.
- Repair plan names source files/assets, not rendered artifacts.
- Honest block creates or links a Hive bead.

### Slice 7 - video-understanding adapter

Add in `video-understanding`:

- `creative_case.schema.json`
- `moments.schema.json`
- `opacity_map.schema.json`
- `generator/ship_gate.py` integration
- test fixture from `video-gen/AUDIT.md`

Acceptance:

- Existing failure "fake UI / wrong app / no CTA" becomes a regression fixture.
- `opacity_map.json` labels generated UI leakage as zero opacity.
- `edit_plan.md` recommends controlled screen recording or source asset replacement.

### Slice 8 - cs-agent mojuco adapter

Add:

- support answer subject schema
- customer environment configs
- OTP and CRM-missing scenarios
- production outcome log mapping

Acceptance:

- Agent answer with fake account state fails.
- OTP leakage fails.
- Missing CRM account returns blocked or escalation state, not fake pass.

### Slice 9 - social-media-agent mojuco adapter

Add:

- social post subject schema
- Liron/compliance/native-language environments
- source freshness and novelty outcome mapping

Acceptance:

- Unsupported market claim fails.
- Wrong geo-scope fails.
- Duplicate story fails.
- Native Arabic quality can be judged separately from English copy.

### Slice 10 - Thompson allocator and sim-to-real calibration

Add:

- `intent outcome log`
- `intent allocator thompson`
- `intent calibration report`

Acceptance:

- Allocation is based on real outcomes, not predicted scores.
- Sim-to-real agreement is reported per environment.
- Miscalibrated environments are flagged for retuning.

### Slice 11 - L2-ready open-model R&D lane

Add only after L1 is stable:

- local open-weight candidate inventory
- hidden-state interface experiment
- transfer module sketch
- small offline dataset from verdict/outcome pairs

Acceptance:

- No production dependency.
- No claim of L2 until hidden-state transfer is actually running.
- Closed-model routes remain L1/L1.5.

## Project Priority

1. `video-understanding` - best artifixer pickup because it already has creative cases, moments, video gates, and known artifact failures.
2. `axia-seekapa-cs-agents` - best mojuco pickup because customer support has live outcome signals.
3. `ORM-AGENT/social-media-agent` - best combined mojuco plus coverage cluster pickup because it has multilingual social output, render gates, and review flow.
4. `campaign-analysis` - use later for stakeholder mojuco and sim-to-real decision calibration.

## Definition of Done

Local work-general v1 is done when:

1. State machine commands exist and block illegal transitions.
2. Foundry embeddings assign coverage clusters with local fallback.
3. Agent reputation exists and affects routing/permissions.
4. Git commits can be ingested into learning tuples with linked intents, tests, coverage clusters, and outcomes.
5. Mistakes can be recorded, explained, promoted to fixtures, and surfaced in future session briefs.
6. One mojuco environment runs on a real project subject.
7. One artifixer opacity map runs on a real creative artifact.
8. One project adapter logs real outcomes.
9. Claude and Codex consume the same contracts in TUI sessions.
10. Every completion claim has attached evidence.
11. No unrelated Jira ticket can receive time or mutation.
12. The docs distinguish L0, L1, L1.5, and L2 without overclaiming.
