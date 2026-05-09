# Shoval Benjer — Claude Setup + Research Bundle

Built 2026-05-08. A snapshot of my Claude Code setup, research artifacts, presentations, and master plans.

## Contents

```
claude-setup/
├── dot-claude/              ← copy of ~/.claude/  (no caches/sessions/secrets)
│   ├── skills/              23 user-authored skills
│   ├── hooks/               5 hooks (meme-* + voice/visual triggers)
│   ├── bin/                 13 helper scripts (a2a, generate-voice, play-meme, etc.)
│   ├── commands/            2 slash commands (cdp, commit-push-pr)
│   ├── config/              memes.json + meme registry
│   ├── docs/                personal Claude Code docs
│   ├── plans/               saved /plan outputs
│   ├── CLAUDE.md            global per-session instructions
│   ├── settings.json        permissions + hooks + env (no secrets)
│   ├── policy-limits.json   hard limits
│   ├── handover-*.md        rolling handover docs (Jan–Feb 2026)
│   ├── ai-foundry-connection-update-report.md
│   ├── production-readiness-sign-off.md
│   └── Azure Resource Management Guidelines for oded (2).docx
│
├── home-dotfiles/           HOME-level dotfiles (renamed dot-* for portability)
│   ├── dot-mcp.json         per-project MCP server registry
│   ├── dot-claudeignore     ignore rules for $HOME-as-repo
│   ├── dot-crontab-bak-*    cron schedules (health reminders + observability)
│   └── AGENTS.md            Codex agent configuration
│
├── master-plans/            the planning docs that drive the setup
│   ├── CLAUDE-CODE-MASTER-PLAN-2026-05-03.md      ← v2, current
│   ├── claude-setup-master-plan-2026-05-02.md     ← v1, superseded
│   ├── claude-setup-tasks-2026-05-02.md
│   ├── claude-skills-scatter-2026-05-03.md
│   ├── claude-skills-triage-2026-05-03.md
│   ├── cleanup-proposal.md
│   ├── claude-code-experimental-features.md
│   └── FIX-BWRAP-WSL.md
│
├── research-papers/         the deep-dive documents I authored / curated
│   ├── home-md/             25 long-form research markdowns (HOME-level)
│   │   • From 2028 — Looking Back on 2026 Agentic Coding
│   │   • Autonomous Agentic Coding Systems (Deep Dive)
│   │   • Futuristic Learning Stack (April 2026)
│   │   • AI Engineering 2030–2035 Frontiers
│   │   • 2026 Mathematics & Statistics Frontier
│   │   • Q-Learning, Deep RL & March 2026 Research
│   │   • Claude Code Complete Issue Map
│   │   • azure-wiki-onepager-skill
│   │   • compass_artifact_wf-... (research export)
│   │   • plus master plans (also under master-plans/)
│   │
│   ├── Documents/           11 dated research subfolders
│   │   • CDP_Kick_Research_20260507
│   │   • CRM_Call_Analyser_Tool_Selection_Research_20260418
│   │   • CS_Agent_Eval_Research_20260415
│   │   • CS_Agent_Eval_SOTA_Audit_20260406
│   │   • ElevenLabs_Scribe_Research_20260427/28
│   │   • Executive_MCP_Research_20260507
│   │   • Football_Analytics_ML_Research_20260412
│   │   • Foundry_Workflows_Research_20260419
│   │   • SIU_InHouse_Video_Research_20260506
│   │   • SOTA_DS_Methods_Research_20260415
│   │
│   ├── Prompts/             curated prompt library + style guides
│   ├── knowledge/           knowledge-base scaffolding
│   │
│   ├── docs-shoval/         ~/docs (audits + specs + reflections + research)
│   │   ├── audits/          Azure dormancy audit, CS-agent boundary audit, incident write-ups
│   │   ├── specs/           silver eval dataset, v108 yasha intake, frontier governance, PST extraction
│   │   ├── reflections/     7 honest end-of-task retrospectives
│   │   └── research/        AI bot security best practices
│   │
│   └── el-vadt/             sales-agent research project (the "research papers" exemplar)
│       ├── docs/            books + papers consulted (Spin Selling, Challenger Sale,
│       │                    Cialdini's Psychology of Persuasion, How Emotions Are Made, etc.)
│       │                    plus my Maryam v6.8 prompt research and ElevenLabs comparisons
│       ├── sales-agents-summary/   handover, final report, prompts (no source dump)
│       ├── specify-memory/  .specify framework memory
│       └── analysis/        analysis artifacts
│
├── pptx/                    every .pptx I authored
│   • AI_Status_Meeting_May_2026 - Copy.pptx           (root copy)
│   • AI_Status_Meeting_May_2026 - Copy - Copy.pptx    (board meeting copy)
│   • azure_costs_jan_may_2026.pptx                    (cost analysis Jan–May 2026)
│   • ORM_intial_Design.pptx                           (ORM agent design)
│   • azureops-copilot-agent.pptx                      (azure-devops-agent design)
│   • ai-solutions-portfolio-2025-v3.pptx              (Oded portfolio archive)
│
└── startup-scripts/         every install/setup shell I touched
    • claude-meme-hooks-startup.sh   (the new fixed installer; 344 lines, idempotent)
    • siu-kilocode-install.sh
    • siu-py-setup.sh
    • qc-telephony-install-deps.sh
    • campaign-analysis-install-deps.sh
    • claude-orchestration-setup-mcp-env.sh
    • vision-analysis-setup-security.sh
    • startup.md (campaign-analysis design doc)
```

## What's deliberately not here

- `~/.claude/cache/` (5 GB of LanceDB / Foundry cache)
- `~/.claude/assets/` (downloaded meme clips + venv with torch/sentence-transformers)
- `~/.claude/plugins/` (third-party marketplace skills, ~28 MB)
- `~/.claude/projects/` (per-session conversation blobs, ~83 MB)
- `~/.claude/sessions/`, `shell-snapshots/`, `file-history/`, `paste-cache/` (ephemeral state)
- `~/.claude/mcp-servers/` (built MCP server binaries — checked into upstream repos already)
- `el-vadt/sales-agents/` (497 MB of source — under git, can be re-cloned)
- `el-vadt/sales-agents.zip` (359 MB duplicate)

## Companion archive

`claude-meme-hooks-20260508.zip` ships alongside this bundle — the standalone meme-hooks project (project source + 2 downloaded mp4 clips), built earlier today.

## How to restore

1. Unzip somewhere (e.g. `~/restore-2026-05-08/`).
2. `cp -r dot-claude/skills dot-claude/hooks dot-claude/bin dot-claude/commands ~/.claude/`
3. Review `dot-claude/settings.json` and merge with current `~/.claude/settings.json` (the `hooks` block is the meaningful part — re-running `~/projects/claude-meme-hooks/startup.sh` re-patches it idempotently).
4. Pptx + research papers — wherever you want them.
