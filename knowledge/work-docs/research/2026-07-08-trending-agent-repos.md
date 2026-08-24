# Trending AI-Agent / Orchestration / Next-Gen Repos (2026-07-08)

GitHub-trending research (last ~4-6 weeks, as of July 2026) for a solo Claude Code (Opus) + Codex CLI
(gpt-5.5) operator. Star/date figures pulled live from the GitHub REST API 2026-07-07/08 (VERIFIED);
narrative from search snippets marked CLAIMED in citations. Companion to
2026-07-08-global-and-per-project-suggestions.md.

## Ranked (momentum + adoptability)

| # | Repo | Area | Novel / next-gen | Momentum | Pattern to adopt |
|---|------|------|------------------|----------|------------------|
| 1 | obra/superpowers | spec+skills methodology | full spec->plan->TDD->subagent methodology as 14 portable SKILL.md, auto-trigger across 9+ harnesses | ~248k stars, pushed 2026-07-06 | diff its skills vs gastown; port gaps; ship your rules as SKILL.md so they run from Codex too |
| 2 | anthropics/skills | agent-skills standard | Skills now a cross-vendor standard (agentskills.io, ~40 adopters, marketplace) | ~159k, 2026-07-01 | adopt the frontmatter/discovery convention so a skill loads unmodified from Codex/Cursor |
| 3 | openclaw/openclaw | autonomous personal agent | message-driven agent on the minimal Pi harness; fastest-growing repo ever | ~382k, 2026-07-07 | thin-core + downloadable-skills; but marketplace had 11-12% MALICIOUS skills, sandbox, never near creds |
| 4 | anomalyco/opencode | CLI/TUI agent | terminal-native, 75+ providers, LSP; neutral post-Anthropic split | ~183k, 2026-07-07 | second subscription-free harness to spot-check a Claude plan on the same task |
| 5 | github/spec-kit | spec-driven dev | spec as compiled artifact: /specify /plan /tasks /implement | ~119k, 2026-07-07 | make your PRD Control Plane executable as those 4 slash commands |
| 6 | earendil-works/pi | minimal harness | 4 tools, shortest prompt, context-handoff (hand a Claude trace to GPT mid-session) | ~68k, 2026-07-07 | study the context-handoff for the Opus-orchestrator -> Codex-executor split |
| 7 | openai/symphony | orchestration (SPEC) | the repo IS a SPEC.md: ticket -> isolated run -> PR -> human review; ports in 6 langs | ~26k, stable | formalize CI-gated ticket->agent dispatch as an executable spec; keep ambiguous work interactive |
| 8 | AgentWrapper/agent-orchestrator | orchestration | agent/runtime/tracker-agnostic; each parallel agent gets its own worktree+branch+PR | ~8k, 2026-07-07 | worktree-per-agent whenever >1 agent edits the same repo |
| 9 | anthropics/claude-agent-sdk-python | programmatic orchestration | subagents+hooks+permissions as an SDK; parent_tool_use_id tracing; up to 1000 subagents | ~7.5k, 2026-07-07 | move recurring workflows (weekly audit, eval, self-improve loop) onto the SDK for typed hooks + tracing |
| 10 | headroomlabs-ai/headroom | context engineering | reversible compression (lib/proxy/MCP), cuts tool-output tokens 60-95%; per-framework failure mining | ~57k, 2026-07-07 | front CRM/eval/log outputs through it before a subagent's context; keep reversible for evidence re-fetch |
| 11 | getzep/graphiti | agent memory / KG | temporal knowledge graph, facts carry validity windows; ships MCP server | ~28k, 2026-07-06 | upgrade intent recall so decisions/findings are superseded, not silently stale |
| 12 | gepa-ai/gepa | eval-driven self-improve | reflective prompt evolution: reads failure traces, proposes targeted rewrite (ICLR 2026 oral) | ~5.5k, daily | run failed eval rows through a reflect-and-rewrite step instead of hand-editing prompts |
| 13 | NousResearch/hermes-agent-self-evolution | self-improve (applied) | GEPA+DSPy create-curate-evolve on the agent's own skills/tools/prompt | ~4.5k, 2026-06-17 (no license) | periodic Curator that scores skills by usage and prunes/merges the dead ones |
| 14 | sentrux/sentrux | verifier / architectural health | Rust sensor scoring a codebase 0-10000 on 5 structural dims, exposed as 9 MCP tools | ~2.6k, stable v1 | give your Layer-7 sensor an ungameable geometric-mean score + expose as MCP |
| 15 | can1357/oh-my-pi | harness fork | hash-anchored edits (edit keyed to content hash, stale diff cannot corrupt a file) | ~16.5k, 2026-07-07 | check your Edit path guards stale content the same way |
| 16 | modelcontextprotocol (spec + servers) | MCP ecosystem | 2026-07-28 spec drops stateless-session req, adds Mcp-Method/Mcp-Name routing headers, MCP Apps | spec ~8.5k / servers ~88k | route MCP on the new headers or an open gateway (Portkey) once >1 server is in play |
| 17 | muratcankoylan/Agent-Skills-for-Context-Engineering | context engineering | context-degradation/compression/filesystem-context shipped AS skills | ~17k, 2026-06-29 | install as reference skills for a context-hygiene upgrade |
| 18 | nextlevelbuilder/goclaw | hardened orchestration | Go static binary, 5-layer permission chain, per-user encrypted keys | ~3.4k, 2026-07-07 | reference the 5-layer permission chain if any agent is ever exposed beyond the terminal |
| 19 | open-multi-agent/open-multi-agent | orchestration | coordinator builds a task DAG from a goal at runtime, auto-parallelizes | ~6.5k, 2026-07-06 | prototype runtime-DAG-from-goal so large-fanout dependency detection is not purely conversational |
| 20 | openai/codex | executor (yours) | June 2026: tiered plugin discovery, configurable delegation levels, rollout token budgets | ~96k, 2026-07-07 | set Codex delegation to explicit-only + rollout token budgets for the executor role |

Also noted: OpenSpec (~59k) and BMAD-METHOD (~50k) spec-driven flavors; Google Agent Quality Flywheel
(eval->fix loop, blog+GCP); Gemini CLI (~106k) reportedly sunset 2026-06-18 for closed Antigravity (an
argument for provider-agnostic design).

## Patterns to steal (personal Claude + Codex setup)
- Ship gastown personas + forge rules as portable SKILL.md so they run unmodified from Codex CLI (1,2).
- Reversible context compression in front of every subagent's tool output, not just at the end (10).
- Executable spec dispatch for CI-gated tickets; keep ambiguous work interactive (5,7).
- Worktree+branch+PR per agent whenever multiple agents edit the same repo (8; workflow isolation:'worktree').
- Move recurring workflows onto the Claude Agent SDK for typed hooks + subagent tracing (9).
- GEPA reflect-and-rewrite + a Hermes Curator pass = the self-improvement loop over your intent-plane (12,13).
- Ungameable architectural-health score exposed as an MCP tool (14). Temporal memory for recall (11).
- Route MCP on the new method/name headers or an open gateway once >1 server (16).
- SECURITY: never run untrusted marketplace skills against Azure/Jira/CRM creds; sandbox first (3).

## Citations (V=verified via GitHub API/fetch, C=search snippet)
openclaw V https://github.com/openclaw/openclaw ; opencode V https://github.com/anomalyco/opencode ;
pi V https://github.com/earendil-works/pi ; oh-my-pi V https://github.com/can1357/oh-my-pi ;
codex V https://github.com/openai/codex (C changelog https://developers.openai.com/codex/changelog) ;
symphony V https://github.com/openai/symphony (C https://openai.com/index/open-source-codex-orchestration-symphony/) ;
agent-orchestrator V https://github.com/AgentWrapper/agent-orchestrator ;
open-multi-agent V https://github.com/open-multi-agent/open-multi-agent ;
claude-agent-sdk V https://github.com/anthropics/claude-agent-sdk-python ;
goclaw V https://github.com/nextlevelbuilder/goclaw ; superpowers V https://github.com/obra/superpowers ;
skills V https://github.com/anthropics/skills ; spec-kit V https://github.com/github/spec-kit ;
MCP spec V https://github.com/modelcontextprotocol/modelcontextprotocol (C https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) ;
MCP servers V https://github.com/modelcontextprotocol/servers ; headroom V https://github.com/headroomlabs-ai/headroom ;
context-eng-skills V https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering ;
graphiti V https://github.com/getzep/graphiti ; gepa V https://github.com/gepa-ai/gepa ;
hermes V https://github.com/NousResearch/hermes-agent-self-evolution ; sentrux V https://github.com/sentrux/sentrux ;
Portkey gateway V https://github.com/Portkey-AI/gateway ; OpenSpec V https://github.com/Fission-AI/OpenSpec ;
BMAD V https://github.com/bmad-code-org/BMAD-METHOD ; Agent Quality Flywheel C https://developers.googleblog.com/driving-the-agent-quality-flywheel-from-your-coding-agent/
