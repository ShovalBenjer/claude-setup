# Gastown Company Registry

This is the source-of-truth routing map for Claude's virtual-company operating model.

## Hard Boundaries

- Foundry/OpenAI/HeyGen/ElevenLabs agents are runtime, eval, media, or project-model surfaces. They are not coding subagents.
- Claude custom agents are the coding and orchestration personas.
- Codex is the execution and independent-review runner.
- Every skill has exactly one owning company persona. Secondary personas can collaborate, but ownership stays single.
- If a new skill is installed and not listed here, it is unwired and must be routed before serious work uses it.

## Operating Flow

1. Mayor Opus classifies the user's task.
2. Workflow Clerk creates or resumes a workflow context when the task is substantive.
3. Mayor selects company personas and their owned skills.
4. Agents receive fresh context packs, not raw transcript dumps.
5. Evidence Clerk records proof, source, pass/fail, and remaining risk.
6. QA Lab, Security Office, or Review Board gate the work when risk warrants it.
7. Latent Systems Lab designs non-prose coordination state when plain-text handoffs become the bottleneck.

## Model and Token Discipline

- Keep the default Claude Code session on Sonnet 5. Escalate the lead to Opus only when orchestration, broad synthesis, or risk justifies the token spend.
- Switch the lead to Fable only for unusually hard, long-horizon investigations or one critical synthesis thread.
- Use Sonnet 5 for most implementation, structured analysis, and specialist workers.
- Use Haiku for inventory, summarization, config scans, and cheap independent checks.
- Keep subagents narrow: one task, bounded files, bounded tools, explicit output schema, and no inherited full transcript unless the task is impossible without it.
- Prefer background shell polling over subagents for long waits, external job polling, and pure status checks.
- Fan out only when tasks are genuinely independent; otherwise keep the work in the lead loop and use parallel tool calls instead.

## Persona Owners

### Mayor Opus

Role: lead orchestrator, routing, fanout, synthesis, escalation.

Owned skills:
- `agent-team`
- `brainstorming`
- `codex-call`
- `context-i-forgot`
- `dispatch`
- `grill-me`
- `premortem`
- `quick-respond`
- `answer-question`
- `zoom-out`

### Workflow Clerk

Role: context reload, project state, long-running work continuity, task bus hygiene.

Owned skills:
- `context-hygiene`
- `end-session`
- `memory-curator`
- `obsidian-vault`
- `plant-task`
- `project-intake`
- `project-state`
- `reground`
- `workspace-brain`

### Evidence Clerk

Role: requirement anchoring, decision-grade evidence, research corpus, provenance.

Owned skills:
- `advisor`
- `decision-grade`
- `deep-research`
- `LTMD`
- `repo-compare`
- `requirement-anchor`

### Latent Systems Lab

Role: vector-state workflows, embedding relay, recursive model patterns, differentiable-agent prototypes, large-context compression.

Owned skills:
- `context-bounded-analyst`
- `notebook`

### Engineering Firm

Role: coding, TDD, simplification, local implementation quality.

Owned skills:
- `code-simplifier`
- `migrate-to-shoehorn`
- `refactor-pre-push`
- `scaffold-exercises`
- `setup-pre-commit`
- `tdd`

### QA Lab

Role: tests, evals, coverage, regressions, test triage.

Owned skills:
- `codex-ci`
- `coverage-enforcer`
- `eval-runner`
- `mutation-runner`
- `property-test-gen`
- `qa`
- `red-team`
- `red-team-review`
- `testing-pyramid`
- `triage-issue`
- `triage-tests`

### Review Board

Role: pre-ship review, reflection, minimalism, dead-code and bloat control.

Owned skills:
- `cleanup-crew`
- `heidegger-reflect`
- `ponytail`
- `ponytail-audit`
- `ponytail-help`
- `ponytail-review`
- `pre-ship-clean`
- `review`
- `watchdog`

### Architecture Office

Role: domain boundaries, system design, terminology, PRDs and issues.

Owned skills:
- `domain-model`
- `improve-codebase-architecture`
- `request-refactor-plan`
- `to-issues`
- `to-prd`
- `ubiquitous-language`

### Release Bureau

Role: git, PRs, ADO/GitHub flow, deployment readiness.

Owned skills:
- `azure-devops`
- `commit-push-pr`
- `deploy-prod`
- `git-guardrails-claude-code`
- `github-triage`

### Azure Ops Utility

Role: Azure runtime, cost, activity, Key Vault, azd, process state.

Owned skills:
- `azd`
- `azure-activity-watch`
- `azure-audit`
- `azure-cert-coach`
- `azure-keyvault-secrets`
- `azure-runtime`
- `kill-stale`
- `ops-status`

### Runtime Agents Division

Role: deployed AI agents and runtime/eval surfaces only. Never acts as a coding worker.

Owned skills:
- `agent-builder`
- `azure-foundry`
- `openai-agents`

### MCP and Tooling Office

Role: lazy connector activation, MCP/API adapters, browser inspection.

Owned skills:
- `apify-mcp`
- `elevenlabs-mcp`
- `heygen-mcp`
- `mcp-activation`
- `web-inspect`

### Security and Compliance Office

Role: PII, secrets, secure defaults, external-data safety.

Owned skills:
- `pii-scrubber`

### Data Bureau

Role: analytics, local data, notebooks, tabular reasoning.

Owned skills:
- `feature-investor`

### Product Studio

Role: UI, UX, frontend craft, design systems, product direction.

Owned skills:
- `design-an-interface`
- `frontend-design`
- `ui-ux-pro-max`

### Voice and Media Studio

Role: voice/video/visual explainers, generated media, interactive educational aids.

Owned skills:
- `blonde-designer`
- `visual-explainer`
- `voice-explainer`

### Communications Desk

Role: stakeholder messages, blogs, Jira drafts and reads, wiki pages, meeting notes.

Owned skills:
- `azure-wiki-onepager`
- `blog`
- `edit-article`
- `humanize`
- `jira-read`
- `jira-task-draft`
- `meeting-notes`
- `shoval-voice-draft`

### Conversation Layer

Role: operator chat mode, compression, persona toggles. Never used inside CI/eval/audit reports unless explicitly requested.

Owned skills:
- `caveman`
- `meme-control`
- `persona`

### Learning Desk

Role: certification, exercises, study plans.

Owned skills:
- `write-a-skill`

## Best-Practices Corpus

Local corpus:
- manifest: `~/.claude/corpus/sources.json`
- builder: `~/.claude/corpus/build_best_practices_corpus.py`
- db: `~/.claude/corpus/best_practices.sqlite3`

Use it for:
- coding practice lookups
- Azure Wiki pages
- persona rule generation
- review criteria
- architecture decisions
- latent/vector workflow design

Do not use it to reproduce full copyrighted books. Cite and summarize.
