# Harness Structure Standard + REPO-MAP - 2026-07-09

Status: reference. Imported from new-recruit 2026-08-04. Companion to docs/standards/agentic-repo-standard.md, not yet reconciled with it.

The structure standard for the local Gastown harness/TUI/control-plane, plus a map of
where everything lives and the work items left. Companion to
`repo-enterprise-maturity-todo-2026-07-09.md` (product repos) and the ADR at
`~/projects/intent-control-plane/docs/adr/0001-harness-is-a-python-package-with-thin-bash-adapters.md`.

## Thesis: adopt the AI-native principles, not its template

`Next-Gen AI-Native Repo Structure (July 2026).md` is a strong standard for one shape: a
LangGraph-style multi-agent Python application (orchestrator/planner/executor as `.py`
files, `prompts/`, tiered `memory/`, `state/` schemas, `workflows/` graphs). We are not
that. We are a harness + TUI + local control plane, and our agent-app pieces already exist
in a valid, different shape:

| Doc's contract | Ours (already exists, differently) |
|---|---|
| `agents/*.py` | Claude Code subagents + Codex + gastown personas (registry prose) |
| `tools/registry.py` | Claude built-in tools + MCP servers + skills |
| `prompts/*_v2.md` | `SKILL.md` + `CLAUDE.md` + `rules/` (git-versioned) |
| `memory/` + `state/` | `intent-control-plane` (SQLite) + `~/.claude` memory + hooks |
| `workflows/` graphs | the Workflow tool scripts + the hook chain |

The doc has a blind spot for dev-tooling / harness / TUI projects. Forcing the harness into
its tree would be cargo-culting. Take its universal parts (toolchain, LOC budgets,
docstrings, `src` layout, tests split, one-store-per-concern, machine-readability); ignore
its agent-app directory tree.

## REPO-MAP: the five roots

```
~ ($HOME)              ALSO a git worktree of the axia-seekapa-cs-agents Azure DevOps repo
                       (origin Corp-AI/_git/axia-seekapa-cs-agents, branch feat/v109-yasha-multilingual).
                       The harness physically lives inside a product repo. THE anomaly.
│
├── .claude/           Claude Code harness (orchestrator side)
│   ├── CLAUDE.md        global instructions   settings.json  hooks/perms/model
│   ├── hooks/           SessionStart/UserPromptSubmit/Stop/PreTool shims
│   ├── bin/             scripts (self-improve.py, statusline.sh = the TUI, a2a bridges)
│   ├── skills/  rules/  the prompt + policy layer (gastown registry, boundary rules)
│   ├── corpus/          best_practices.sqlite3 (FTS over ~/docs) + build script
│   ├── agents/ commands/ config/ channels/
│   ├── cache/           sessions.db (Layer 7), lancedb/ (dormant meme vectors)
│   └── projects/-home-shovalbe/memory/   MEMORY.md + auto-memory
│
├── .codex/            Codex executor side (mirror of the harness)
│   ├── AGENTS.md  RTK.md  config.toml
│   ├── hooks/ skills/ rules/   unified with ~/.claude via bin/sync-setup.sh
│   ├── agent-control/recall.sqlite   automations/  memories/
│   └── goals_1.sqlite logs_2.sqlite memories_1.sqlite   (Codex state)
│
├── .intent/           intent control plane runtime state (owned by the package below)
│   ├── config.toml  intent.db (SQLite)  ledger/events.jsonl
│   └── evals/ indexes/ context-packs/ logs/          the cleanest root
│
├── projects/          deployable product repos (one git repo each) + the harness package
│   ├── intent-control-plane/   THE tested harness package (src + tests + ADR)
│   ├── agent-call-tracker/ qc-telephony-api/ axia-seekapa-cs-agents/ ...   product repos
│   └── *-wt/  *.backup-*/  .archive/   worktrees, backups, archive (clutter to fold)
│
└── docs/              this corpus (SOTA research + standards); indexed by ~/.claude/corpus
```

### How the roots relate

- Claude (orchestrator) and Codex (executor) share skills/hooks/rules via
  `~/.claude/bin/sync-setup.sh` (additive symlink union) and talk over the a2a bridge.
- Hooks in `.claude`/`.codex` are thin shims that call the `intent` CLI and the harness
  package (`intent_control_plane.harness.router` / `.self_improve`), which read `~/.intent`
  and the corpus.
- The corpus indexes `~/docs`. Because `~/docs` sits under `$HOME`, it is entangled with
  the CS-agents repo working tree (part of the anomaly).

## The harness structure standard (universal principles, applied to us)

1. Any Python in the harness is a `uv`+`ruff`+`mypy`+`pyproject` package with tests, not a
   loose untested script. Reference: `intent-control-plane`. Gap: `~/.claude/bin/*.py`.
2. LOC budgets are enforced by `python -m intent_control_plane.repo_health <path>` (file
   300/500, function 30/50, class 150/300).
3. Google-style docstrings on public API; skip trivial helpers.
4. Decision logic is tested library code; hooks and scripts are thin adapters (ADR-0001).
5. One store per concern: SQLite for relational + lexical FTS; at most one dense vector
   store, and only when a query needs it. No orphaned stores.
6. The setup must be localizable: this REPO-MAP is the entry point; naming is consistent.
7. Prompts/personas are versioned by git (skills/rules), not `v1/v2` files. Adequate.
8. Clean tree: no loose artifacts, backups, or worktrees mixed with source. The
   `$HOME`-as-repo overlap is the standing violation.

## Work items left (prioritized backlog)

Done (2026-07-09): harness A/B/C (tested router + self-improve, dead-hook cull, `cli.py`
1736->1453, ADR-0001, maturity control-plane entry), corpus refreshed live, `repo_health`
checker built + tested, this standard + REPO-MAP.

- [x] P1: `docs-sync` corpus auto-refresh - DONE 2026-07-09. `~/.claude/bin/docs-sync.sh` rebuilds local-only (offline) when any `~/docs` file is newer than the index, wired into SessionStart, non-blocking.
- [~] P1: split `cli.py` - PARTIAL 2026-07-09. Extracted `text_index.py` (retrieval/scoring, now unit-tested) + `util.py` (timestamps/ids/redaction); `cli.py` 1449 -> 1344. Remaining: split the ~40 command handlers + `build_parser` into a `commands/` package (still over the 500 hard cap).
- [ ] P2: migrate the remaining ~10 python-heredoc hooks to tested shims; add a blocking local `ruff/mypy/pytest` gate before harness edits.
- [ ] P2: decide the vector/DB layer: retire the orphaned `~/.claude/cache/lancedb` (dormant since 2026-05-08) or adopt it; leave the intent JSON-cosine until semantic recall is real.
- [ ] P2: consolidate the ~6 overlapping structure docs (AI-native, maturity ladder, architecture SOTA, file-plan, code-reuse, this) so there is one standard, not scattered prose.
- [ ] P2: regenerate `~/docs/INDEX.md` from the tree instead of hand-maintaining it.
- [ ] P3: TUI decision - finish the stalled custom TUI (rainfall loader, meme integration) or cut it; the standard has no place for a half-built component.
- [ ] P3: `$HOME`-as-repo hygiene - gitignore + artifact policy for the harness clutter (handover-*.md, loose docx/pdf, tmp scripts) so the CS-agents working tree is not polluted. High blast radius; needs care.
- [ ] P3: promptfoo push-gate fix (deployed prompt + sturdier Foundry judge). Separate.
- [ ] P3: changelog / version discipline for the setup itself.

Recommended order: P1 items first (cheap, unblock), then the `cli.py` split (the checker
demands it), then the hook migration behind a gate.
