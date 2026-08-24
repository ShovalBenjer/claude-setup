# Session Post-Mortem: 2026-06-28 Work-General Mojuco + Artifixer Plan

## What was accomplished

- Read `docs/2026-06-28-work-general-setup_4614.md`.
- Audited the current local intent-control implementation against the work-general setup.
- Generated a visual architecture audit via `visual-explainer`.
- Created `docs/specs/2026-06-28-work-general-mojuco-artifixer-foundry-plan.md`.
- Linked the new plan from `docs/2026-06-28-work-general-setup_4614.md` and `docs/specs/2026-06-25-local-intent-control-plane.md`.
- Expanded the plan with:
  - L0 / L1 / L1.5 / L2 boundaries.
  - Foundry endpoint roles.
  - state-machine lifecycle.
  - coverage clusters.
  - mojuco project surfaces.
  - artifixer opacity repair.
  - learning from mistakes, including git commits.
  - agent identity contracts separated from system data contracts.
  - skills/rules learning table.

## What was learned

- The previous "10 contracts" framing was valid as a data-contract stack but wrong as an answer to "who are the agents." Agent identity contracts must be first-class.
- Closed Claude/Codex/Foundry models cannot provide true L2 latent hidden-state communication. The correct closed-model lane is L1/L1.5: embeddings, vector blackboard, routing, coverage clusters, and policy learning around the models.
- `video-understanding` is the strongest first artifixer pickup because it already has creative gates, `moments`, `video-gen/TESTS.md`, and a concrete artifact failure audit.
- `axia-seekapa-cs-agents` is the strongest first mojuco pickup because support has live outcome signals.
- `ORM-AGENT/social-media-agent` is a strong second mojuco/coverage pickup because it has multilingual content, render gates, and review flows.

## Decisions made

- Treat Foundry as a service bureau, not truth storage.
- Keep local intent ledger + Hive + repo + production outcomes as authority.
- Add project-level mistake learning from commits, PRs, test failures, reverts, production issues, and user corrections.
- Split agent identity contracts from data contracts.
- Define eight core agent roles: Claude Orchestrator, Codex Executor, Evidence Clerk, Mojuco Refuter, Artifixer Repair Officer, Foundry Service Broker, Release Gate, Latent Systems Lab.

## What's unfinished

- Implement the plan in `projects/intent-control-plane`.
- Add state transition commands.
- Add git commit ingestion and mistake records.
- Add Foundry embedding-backed coverage clusters.
- Add agent reputation storage and routing.
- Add mojuco runner.
- Add artifixer opacity-map engine.
- Add first project adapter, likely `video-understanding`.

## Process observations

- The plan became clearer after separating "agent contract" from "data contract."
- The user wants a company-operating-model feel, but it must be empirical: permissions, reputation, proof, and discipline, not persona flavor.
- The heidegger-reflect framework file is still missing at `docs/prompts/Heidegar_self_reflect_oded.md`; the skill itself remains usable, but the referenced framework doc is setup debt.

## Security notes

- `visual-explainer` called Azure Foundry image generation and saved a local PNG.
- No secrets were intentionally read or written.
- End-session cleanup ran against `/tmp/.Codex-*`, `/tmp/.secret-*`, `/tmp/.token-*`, and `/tmp/.python_history`.

