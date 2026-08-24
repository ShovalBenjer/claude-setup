# Claude Setup Tasks — Weekend Research Roundup

> **APPENDIX NOTE (2026-05-04):** This was the first-pass weekend task list. A1-A4 are now tracked in the canonical master plan §14.6. **Use `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md` as the live source of truth.**

**Date:** 2026-05-02
**Context:** Mapping 5 weekend reads to concrete setup work + career-path notes.
**Current state of `~/.claude/`:** 2 MCPs (telegram, playwright), 2 hooks (voice/visual triggers), 1 slash command (`commit-push-pr`), plugin marketplace wired but only telegram installed. `AGENTS.md` at `$HOME` is Codex-only; Claude has no equivalent global rule file.

---

## A. IMPLEMENT — Setup Changes Worth Doing

### A1. Install `claude-obsidian` (Daniel Agrici)
**Source:** https://github.com/AgriciDaniel/claude-obsidian
**Why it fits:** You already write research markdown at `$HOME` root (4 files from this weekend alone). claude-obsidian turns Claude into a vault organizer with citation-backed Q&A, autoresearch, and lint. Solves the "where did I put that note" problem.

- [ ] Install Obsidian on WSL host (or Windows side, then point at WSL path)
- [ ] Pick an install path: try plugin route first
  ```
  claude plugin marketplace add AgriciDaniel/claude-obsidian
  claude plugin install claude-obsidian@claude-obsidian-marketplace
  ```
- [ ] Run `bash bin/setup-vault.sh` if going clone route
- [ ] Add Local REST API Obsidian plugin so MCP can hit the vault directly
- [ ] Pre-load vault by `ingest`-ing the existing `$HOME/*.md` research files (Q-Learning, Claude Code bwrap, compass artifact, etc.)
- [ ] Try `/autoresearch` on a Seekapa multilingual topic to gauge value
- [ ] Add an `init` skill memory pointer if you keep it

**Risk:** This is a heavy plugin (11 skills). Try in a side worktree first before committing to it as a daily driver.

---

### A2. Install `Understand-Anything` (Lum1104) for Seekapa
**Source:** https://github.com/Lum1104/Understand-Anything (via LinkedIn post by sumanth077)
**Why it fits:** Seekapa is now ~v109 with multilingual flow on top of intake on top of OTP — architecture is getting dense. 5-agent parallel scan + React Flow dashboard + semantic search + diff impact = exactly the tour-guide layer that's missing for new contributors and for you when you context-switch back.

- [ ] Add to plugin marketplace (likely `claude plugin marketplace add Lum1104/Understand-Anything`, verify on the repo README)
- [ ] Run scan on `axia-seekapa-cs-agents` worktree (HOME-as-repo — be careful with output paths)
- [ ] Validate the diff-impact view against a recent Seekapa PR (e.g. PR 184 v108 yasha intake) to see if it correctly traces blast radius
- [ ] Decide: keep as on-demand only, or wire into commit-push-pr pre-flight

---

### A3. Wire up the Meta Ads CLI (only if you actually run ads)
**Sources:**
- https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli
- https://www.facebook.com/business/help/1456422242197840 (Ads AI Connectors help)
**Why it fits (or doesn't):** You don't currently have a Meta marketing workflow surfaced in `~/.claude/`. This is only worth installing if you are running ads for i-sdd or a side project. Otherwise it's a curiosity bookmark.

- [ ] Decision gate: do you have an active Meta ad account + Marketing API access?
- [ ] If yes:
  - [ ] `uv tool install` (or `pipx install`) the Ads CLI — needs Python 3.12+
  - [ ] Stash the Marketing API token in Azure Key Vault, not `.env` (use your existing `azure-keyvault-secrets` skill pattern)
  - [ ] Note: resources default to PAUSED — keep that default, don't `--no-pause`
- [ ] If no: drop the link in your "tools-to-revisit" note and move on

---

### A4. Setup hygiene fixes uncovered during research
- [ ] **`gh` CLI missing** — `gh repo view` failed during this research. Install via `apt` or `bun`/`brew`. Affects `commit-push-pr` skill on GitHub repos (Azure DevOps unaffected).
- [ ] **No global `CLAUDE.md` at `$HOME`** — `AGENTS.md` is Codex-only. Either: (a) symlink `CLAUDE.md` → `AGENTS.md` to share the rule set, or (b) write a Claude-specific `CLAUDE.md` that references the same rules. Currently Claude only reads `~/.claude/projects/-home-shovalbe/memory/MEMORY.md`.
- [ ] **Single slash command** — `commit-push-pr.md` is the only entry in `~/.claude/commands/`. Consider porting your most-used Codex skills (`eval-runner`, `red-team-review`, `web-inspect`) to Claude commands so the Codex-vs-Claude split (per memory) doesn't leave Claude underpowered for orchestration.
- [ ] **MCP coverage gap** — only `telegram` + `playwright` in `.mcp.json`. Worth adding (when needed): Context7 (for SDK lookups during Seekapa work — already auto-listed in this session, just not in your local config), Perplexity (you have it as a Codex skill, no Claude equivalent).

---

## B. CAREER REFERENCE — Navan Senior ML Engineer (Tel Aviv)

**Source:** https://navan.com/careers/openings/7783027 — *Senior ML Engineer, LLMs & Self-Hosted AI*

This role's must-haves map *closely* to what you already do at Seekapa, with two clear gaps. Treat this as a calibration target, not necessarily an apply-now.

### Already aligned (your Seekapa work covers these)
- Python + Bash daily driver
- Claude Code native terminal use
- Agentic systems: ReAct, function/tool calling, RAG (Seekapa intake/multilingual flow)
- LLM eval frameworks (you've shipped 64% eval pass rate per recent commit)
- Hugging Face ecosystem familiarity

### Gaps to close (if this is a target role)
1. **Self-hosted inference at scale** — vLLM or TGI deployment. You're on Azure Foundry / managed APIs today. **Action:** stand up a vLLM container on a side GPU box (or RunPod), serve a quantized 7B model, measure tokens/sec.
2. **Fine-tuning depth** — SFT / DPO / LoRA hands-on. **Action:** fine-tune a small model on a Seekapa transcript subset using PEFT/LoRA, push to HF, document the run.
3. **Statistical evaluation rigor** — t-tests, Mann-Whitney U, bootstrapping for A/B. You have eval pass rates but not significance testing. **Action:** add a `scipy.stats` layer to your eval pipeline; report CIs not just point estimates.
4. **MLOps stack** — DVC + W&B/MLflow. **Action:** instrument one Seekapa training/eval run end-to-end with W&B.

### Nice-to-have stretch goals
- Ray for multi-GPU orchestration
- Quantization: AWQ / GPTQ / GGUF
- FastAPI async microservices (you're on Azure Functions today — different pattern)

**Decision needed:** Is this a "apply within 6 months" target, or a "use as study syllabus" reference? The gaps above are 3–6 months of weekend work to close credibly.

---

## C. NOT WORTH IMPLEMENTING (filed for awareness)

- **Meta Ads CLI** as a Claude tool — unless your day job adds an ads workflow, it's noise. The PAUSED-default and uv-installable design are nice patterns to crib for your own CLIs though.

---

## Suggested order of attack

1. **This week:** A4 setup hygiene (`gh` install, `CLAUDE.md` symlink, port 2-3 Codex skills) — small, compounding wins.
2. **Next weekend:** A2 Understand-Anything on Seekapa — biggest leverage for current work.
3. **Within 2 weeks:** A1 claude-obsidian — bigger commitment, do after A2 proves the plugin model works for you.
4. **Ongoing:** B Navan gap-closing — pick one gap, do it, ship it publicly. Don't try to cover all four.
5. **Skip unless triggered:** A3 Meta Ads CLI.

---

## Source links (for re-fetching if needed)

- claude-obsidian — https://github.com/AgriciDaniel/claude-obsidian
- Meta Ads CLI announcement — https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli
- Meta Ads AI Connectors help — https://www.facebook.com/business/help/1456422242197840
- Understand-Anything (via LinkedIn) — https://github.com/Lum1104/Understand-Anything
- Navan ML Engineer role — https://navan.com/careers/openings/7783027
