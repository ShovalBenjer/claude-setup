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
- `brainstorming`
- `codex-call`
- `dispatch`
- `grill-me`
- `premortem`

### Workflow Clerk

Role: context reload, project state, long-running work continuity, task bus hygiene.

Owned skills:
- `end-session`
- `reground`
- `workspace-brain`
- `skillmap`
- `wayfinder`

### Evidence Clerk

Role: requirement anchoring, decision-grade evidence, research corpus, provenance.

Owned skills:
- `advisor`
- `decision-grade`
- `deep-research`
- `LTMD`
- `repo-compare`
- `requirement-anchor`
- `prior-art-gate`
- `youtube-distill`

### Latent Systems Lab

Role: vector-state workflows, embedding relay, recursive model patterns, differentiable-agent prototypes, large-context compression.

Owned skills:
- `context-bounded-analyst`

### Engineering Firm

Role: coding, TDD, simplification, local implementation quality.

Owned skills:
- `code-simplifier`
- `refactor-pre-push`
- `prove-implementation`

### QA Lab

Role: tests, evals, coverage, regressions, test triage.

Owned skills:
- `coverage-enforcer`
- `eval-runner`
- `mutation-runner`
- `property-test-gen`
- `red-team`
- `red-team-review`
- `testing-pyramid`
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
- `review`
- `watchdog`
- `ship-gate`

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
- `commit-push-pr`
- `github-triage`

### Azure Ops Utility

Role: Azure runtime, cost, activity, Key Vault, azd, process state.

Owned skills:
- `azure-activity-watch`
- `azure-audit`
- `azure-runtime`
- `kill-stale`
- `ops-status`

### Runtime Agents Division

Role: deployed AI agents and runtime/eval surfaces only. Never acts as a coding worker.

Owned skills:
- `agent-builder`
- `openai-agents`

### MCP and Tooling Office

Role: lazy connector activation, MCP/API adapters, browser inspection.

Owned skills:
- `web-inspect`

### Security and Compliance Office

Role: PII, secrets, secure defaults, external-data safety.

Owned skills:
- `pii-scrubber`

### Data Bureau

Role: analytics, local data, notebooks, tabular reasoning.

Owned skills:
- `feature-investor`
- `whatsapp-query`

### Product Studio

Role: UI, UX, frontend craft, design systems, product direction.

Owned skills:
- `frontend-design`
- `ui-ux-pro-max`

### Voice and Media Studio

Role: voice/video/visual explainers, generated media, interactive educational aids.

Owned skills:
- `blonde-designer`
- `meme-gen`
- `voice-explainer`

### Communications Desk

Role: stakeholder messages, blogs, Jira drafts and reads, wiki pages, meeting notes.

Owned skills:
- `blog`
- `humanize`
- `meeting-notes`
- `shoval-voice-draft`
- `gws-gmail`
- `gws-gmail-read`
- `gws-gmail-triage`
- `gws-shared`
- `recipe-create-gmail-filter`
- `recipe-label-and-archive-emails`
- `case-ledger-post`
- `syndication-engine`
- `voice-metrics`

### Conversation Layer

Role: operator chat mode, compression, persona toggles. Never used inside CI/eval/audit reports unless explicitly requested. `meme-gen` (Voice and Media Studio) carries the identical hard-block: never in CI/PR/eval/audit output, per `output-channel-routing.md`.

Owned skills:
- `persona`
- `explain-simply`
- `i-have-adhd`

### Learning Desk

Role: certification, exercises, study plans.

Owned skills:
- `write-a-skill`
- `learn-on-demand`

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
## Rewired 2026-08-12

Census against the installed estate (80 skills) and state/skill-use.jsonl: 19 unowned skills assigned above (they included the three most-used skills and the three mandated gates), and 39 ghost entries removed (owned in this file but not installed; nearly all Seekapa-era). The census method: parse this file with hooks/route.py parse_registry, diff against ~/.claude/skills.

## Connector routing (added 2026-08-12)

The claude.ai connectors are configured server-side; nothing on disk lists them, so
until now no rule told a session which to reach for and most sat unused. Route by
task, not by novelty:

- Library/framework/API question, any language: `Context7` before memory or web search.
- Azure or Microsoft anything: `Microsoft Learn` (docs search + fetch + code samples).
- Technical web search or page fetch: `Exa` over the default WebSearch.
- Research papers, prior-art sweeps: `alphaXiv` (and `Scholar Gateway` for cross-source).
- Math, unit conversions, symbolic checks: `Wolfram`.
- Cloudflare estate (Pages, Workers, D1/KV/R2): `Cloudflare Developer Platform`.
- Diagrams for docs/PRs: `Mermaid Chart` validation, `Lucid` only for shared boards.
- O'Reilly for book-grounded practice lookups (metadata/summary discipline applies).

- Voice, TTS briefings, generated audio/media: `ElevenLabs` (verified live
  2026-08-17, eleven_v3 through ffplay/WSLg; owned by Voice and Media Studio;
  per-line credits, so briefings yes, long transcripts no).
- Cross-app automation with no dedicated connector: `Zapier` (MCP and Tooling
  Office; enable actions per use, never broadly).
- AWS estate work, if any returns: `AWS` connector (Azure Ops Utility owns cloud
  ops; AWS rows are read-only checks like the i-0a9036 instance question).

Usage is measured as of 2026-08-17: every mcp__* call appends to
state/connector-use.jsonl via the connector-usage-log.sh PostToolUse hook, the
connector twin of skill-use.jsonl. A connector claimed as "wired" with zero rows
there is prose, not wiring.

Dormant by re-auth, operator-only fix from claude.ai settings: Coursera, Google Cloud
BigQuery, Stack Overflow. Irrelevant to this estate's work and fine to ignore or
disconnect: Booking.com, Tripadvisor, Dice, Indeed, ZipRecruiter, FMP, Twilio,
Roboflow, HyperFrames, Canva, Learning Commons. A connector with no row here gets one
before serious use, same rule as skills.

## Tool ownership (added 2026-08-19)

`tools/*` entries are not skills and are deliberately kept out of the `### Persona`
blocks above: `hooks/route.py parse_registry` and
`intent_control_plane.gastown.parse_registry` both attribute every backtick-quoted
bullet under the nearest `### ` heading to that persona, so a tool bullet placed
inside a persona block (even under its own sub-heading) would leak into the skill
census the next audit reads. This section stays outside any `### ` block on
purpose. Findings from the 2026-08-19 unowned-tools sweep, checked against each
tool's row in `docs/dir-purpose.txt`, not assigned from the suggestion alone:

- **tools/antigravity** -- Runtime Agents Division. The `agy` CLI, a real local
  reimplementation of an Antigravity command line (wraps the google-antigravity
  SDK behind this repo's GEMINI_API_KEY convention and a free-tier data-boundary
  refusal). Third-party agent-runtime integration, not a coding subagent, matching
  this persona's charter exactly.
- **tools/coffee** -- Latent Systems Lab. The coffee-break v2 social loop:
  `futures.py` is a reputation-betting board over `state/futures.jsonl`,
  `smoking.py` a frustration-triggered gripe cycle reading `state/gate-runs.jsonl`
  for triggers. Non-prose coordination state over a ledger substrate is this
  persona's charter.
- **tools/health** -- Release Bureau, not Azure Ops Utility. Inspected: it is a
  read-only git branch-health sweep (`branch_sweep.py`) across GitHub source repos
  via `gh`, classifying branches merged/stale/active. That is branch/PR hygiene,
  the Release Bureau's charter (git, PRs, ADO/GitHub flow), and has no Azure
  content, so the audit's suggested fit is overridden here rather than followed.
- **tools/reclaim** -- Azure Ops Utility. Executes a verified filesystem
  reclamation plan (archive/delete), dry-run by default. System-hygiene charter,
  approximate fit for local disk as the audit suggested; confirmed by reading
  `tools/reclaim/reclaim.py` and its manifest row in `state/reclaim-manifest.jsonl`.
- **tools/local** -- Mayor Opus. Runs a local qwen2.5:1.5b Ollama classifier to
  cheaply triage a request's route and risk before escalating to Claude, logging
  each decision to the flywheel jsonl for router training. This is a routing/
  dispatch function, matching the audit's suggestion.

Unowned, by design (inspected, no persona charter fits without forcing it):

- **tools/workspace** -- genuine grab-bag on inspection: the lane chooser and its
  launchers/taskbar-pin scripts (`Start-Claude.ps1`, `make_lane_launchers.py`,
  `repoint_taskbar_pin.ps1`) sit alongside unrelated one-off scripts that repair
  public repositories and measure per-repo activity. No single persona owns both
  halves without stretching; left unowned rather than forced onto Workflow Clerk.
- **tools/wsl** -- one-off WSL2 migration helpers (Makefile plus scripts moving
  work onto the ext4 side for the measured git-status latency win). Environment
  migration tooling, not a standing charter any persona holds; left unowned by
  design, same treatment as `tools/lib`.

Left standing, not merged: **tools/channel** has its own `README.md` and is called
out as defensible in the audit that raised the merge-with-`tools/bus` question.
Judgment call taken per the audit's own default (leave standing when documented
and defensible); no merge performed.
