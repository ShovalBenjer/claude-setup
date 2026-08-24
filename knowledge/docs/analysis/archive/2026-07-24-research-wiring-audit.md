# Research-wiring audit + AUTO-17 pipeline design — 2026-07-24

Point-in-time scan (docs-control-plane: analysis/, input to TODO). Answers the
operator question "what about the research — is it wired?" Claims tagged
VERIFIED (command/file read this session), STAGED (exists but unproven end-to-end),
ASSUMED (inference, not independently checked).

Bottom line: the corpus is large (~443 files, ~386 MB, git-tracked) and mostly
SHELF-WARE. Three papers of the §2b citation list are genuinely wired into
enforcement (Antislop → slop_lint.py, Verbalized Sampling → /diverge, MAST →
ADR-0009 + two specs). Everything else — the July harness docs, the Perplexity
deep-research file, research-papers/ wholesale — is consumed by zero rules, zero
tools, zero hooks. AUTO-17 (`research_sweep.py`) is TODO in the PRD and unbuilt
(VERIFIED: prd/autonomy-ecosystem.md row 17, `tools/selfimprove/` contains only
`scan.py` + `proposals.jsonl`). The §2b pointer "sources in docs/research
appendix" is dangling: `docs/research/` does not exist (VERIFIED).

---

## 1. Inventory

### 1a. `perplexity_research-11.5.26` — a FILE, not a directory

VERIFIED: single UTF-8 file at repo root, 33,521 bytes, 338 lines, mtime
2026-07-23. Three Perplexity deep-research answers pasted together:

1. **Neurosymbolic Gastown** — Beads/Refinery/Witness as symbolic gates; concrete
   build order: formal verifier at merge gate (Z3/Lean/Alloy), domain constraints
   as grammars, knowledge graph as symbolic memory, solver-verification replacing
   prompt-verification.
2. **Architecture-level model work** — activation steering + SAE correctness
   probes on open models (mid-depth layers), RLEF (log every test-pass/fail as a
   trajectory), Code World Models / latent planning, PRM verifiers, test-time
   compute scaling.
3. **Math/CS-theory substrate** — MDL/Kolmogorov as correctness proxy at merge
   gates, PAC-Bayes bounds for fine-tunes, wavelet decomposition of agent
   session event streams, category-theoretic typed agent composition,
   information geometry for training.

NOTE (VERIFIED): `docs/specs/2026-07-24-autonomy-implementation.md:117` cites it
as `perplexity_research-11.5.26/` with a trailing slash — the spec believes it is
a directory. Wrong reference; any future `research_sweep.py` that globs it as a
dir finds nothing.

### 1b. `research-papers/` — 180 files, 375 MB (VERIFIED counts via find/du)

| Subdir | Files | Size | What it is |
|---|---|---|---|
| `home-md/` | 24 | 561K | May-2026 HOME-dir plans + deep dives: CLAUDE-CODE-MASTER-PLAN-2026-05-03, claude-setup master plan/tasks/skills-triage, "Autonomous Agentic Coding Systems with Semantic Self-Awareness 2025-2030" (x2 copies), "From 2028: Looking Back on 2026 Agentic Coding", Q-Learning/DeepRL audit, bwrap-WSL fix docs, RTK.md |
| `Documents/` | 31 | 722K | Work deep-research folders, Apr-May 2026: Executive_MCP_Research_20260507, CDP_Kick_Research, CRM_Call_Analyser_Tool_Selection, CS_Agent_Eval_Research + SOTA_Audit, ElevenLabs_Scribe (x2), Foundry_Workflows, Football_Analytics_ML, SIU_InHouse_Video, SOTA_DS_Methods, azure_costs pptx |
| `Prompts/` | 6 | 109K | Anti-AI Writing Style Guide, Q-Learning/DeepRL audit (dup of home-md), SOTA Frontend Audit prompt, data-scientist-xlsx SKILL, data_personas |
| `docs-shoval/` | 47 | 712K | Work docs snapshot (subset of work-docs/): ARCHITECTURE, KNOWLEDGE-BASE, COMPLIANCE-AUDIT, FOUNDRY-EVAL-CI-PLAN, MODEL-MIGRATION-PLAN, audits/, eval-results/, reflections/, wiki/ |
| `el-vadt/` | 71 | **373M** | Sales-agent corpus: persuasion books (Challenger Sale PDF, Psychology of Persuasion PDF, SPIN Selling, Purple Cow, VITO), ElevenLabs emotion research, dark-patterns mining scripts + CSVs, sales-agents-summary, specify-memory. The 373M is `docs/` (PDFs). |
| `knowledge/` | 1 | 8K | Near-empty scaffold: `devops/` EMPTY, `perplexity/` EMPTY, `marketplace/analysis` EMPTY — a taxonomy that was never filled (VERIFIED) |

Duplication (VERIFIED): `docs-shoval/` overlaps `work-docs/` heavily
(ARCHITECTURE.md, KNOWLEDGE-BASE.md, COMPLIANCE-AUDIT.md, SHOVAL-BENJER-5MO-CONTEXT
appear in both); Q-Learning audit appears in both `home-md/` and `Prompts/`;
"Autonomous Agentic Coding Systems" exists twice in `home-md/` ("(1).md" copy).

### 1c. `work-docs/` — 263 files, 11 MB (VERIFIED)

The July-2026 research layer (the part the operator is asking about):

- `work-docs/research/` (6 files): 2026-05-07 AI-bot security best practices,
  **2026-07-07 claude-setup gap analysis**, **2026-07-08 global+per-project
  suggestions**, **2026-07-08 trending-agent-repos**, README (declares itself
  "the research lane"), prompts/.
- July harness docs at work-docs root: **`sol5.6-harness.txt`** (the "AI Runtime /
  maturity ladder" essay — intelligence moves from model to harness to OS),
  **`Next-Gen AI Coding Intelligence 2026 — Model Failures, Harness Engineering,
  Startups & Open Source Frontiers.md`** (July-2026 SWE-bench table, context-rot,
  April regression post-mortem, harness-engineering literature),
  **`code-quality-standard-2026-07.md`** (Q1-Q7 control doc: docstrings, types,
  boundaries, complexity, testing, A-F rubric, uv/ruff/mypy),
  `harness-structure-standard-2026-07-09.md`, `coding-effort-craft-completion-2026-07.md`,
  `implementation-fixes-playbook-2026-07.md`,
  **`Reducing Fix-Commit Rate & Building a Self-Improving Code Quality Flywheel.md`**.
- The ~20-report SOTA series: Production AI June 2026, Principal Engineer
  Curriculum, API Design SOTA, Data & Persistence SOTA, System Architecture SOTA,
  Excellent SQL, SOTA Testing Criteria, SOTA Video/Voice Testing, Text2SQL,
  Next-Gen UI/UX, Next-Gen AI-Native Repo Structure, Code Reuse/DRY, Code
  Maturity Ladder, GD Coverage Metric 2030, Dilum Sanjaya repo analysis, etc.
- Plus operational history: repo-standards-2026-07-09, project-scorecard,
  specs/, audits/, wiki/, pipelines/, eval-results/.

### 1d. CLAUDE-OS.md §2b citation list (VERIFIED, lines 181-191)

Nine citations ground the Deep Work Protocol: METR time-horizons; arXiv
2509.09677 (self-conditioning); ACL 2026 "Illusion of Insight";
debate-martingale results; LLM homogenization studies; Verbalized Sampling
(arXiv 2510.01171); Antislop (ICLR 2026); MAST (NeurIPS 2025); Anthropic
long-running-harness + context-engineering posts. The text says "sources in
docs/research appendix" — **`docs/research/` does not exist** (VERIFIED:
`test -d docs/research` → NO). The citations live nowhere as files; the
appendix pointer is dangling.

---

## 2. Consumption map — wired vs shelf

Method (VERIFIED): grepped every corpus-area name and every §2b citation across
`CLAUDE-OS.md`, `TODO.md`, `README.md`, `docs/`, `tools/`, `dot-claude/`,
`github/`, `state/`.

### WIRED (research that reached an enforcement or design artifact)

| Research item | Consumed by | Evidence |
|---|---|---|
| Antislop (ICLR 2026) | `tools/slop_lint.py` (gate, verified exit-1 per TODO), `dot-claude/commands/slop.md`, `dot-claude/rules/calibrated-claims.md` | grep hits, VERIFIED |
| Verbalized Sampling (2510.01171) | `dot-claude/commands/diverge.md` (the /diverge protocol) | grep hit, VERIFIED |
| MAST (NeurIPS 2025) | `docs/adr/0009-slm-swarm...md`, `docs/specs/2026-07-23-persona-review-economy.md`, `docs/specs/2026-07-23-slm-swarm.md` | grep hits, VERIFIED |
| Executive MCP research (Documents/) | CLAUDE-OS L4 "Push-beats-pull (Executive MCP research)" — one design sentence | grep hit, VERIFIED |
| 2026-07-07 gap analysis + 2026-07-08 suggestions | CLAUDE-OS supersession table row "Absorbed (G1→L5... G4→L5)"; EXECUTION-PLAN references gap-analysis | VERIFIED |
| May master plans (home-md/) | CLAUDE-OS supersession table: formally superseded, "history/reference only" | VERIFIED |
| §2b findings 1-4 as a bloc | The 12-rule Deep Work Protocol table itself + kernel-anchor.sh hook (deep-work discipline injected every prompt, per TODO) | STAGED — the protocol encodes the findings, but 9 citations have no on-disk source and several rules are still TODO (P1) |

### SHELF-WARE (zero consumers found)

| Corpus area | Grep result | Status |
|---|---|---|
| `perplexity_research-11.5.26` (all 3 answers: NeSy gates, SAE/RLEF, MDL/wavelets) | referenced ONCE, as a *future seed shelf* in the AUTO-17 spec paragraph (with wrong trailing-slash path) | SHELF. Zero practices extracted. |
| `sol5.6-harness.txt` | only the import-inventory names it | SHELF |
| `Next-Gen AI Coding Intelligence 2026...md` | zero references | SHELF — despite being the single most §2b-relevant doc in the corpus |
| `code-quality-standard-2026-07.md` | only the import-inventory names it | SHELF — Q1-Q7 rubric enforced nowhere |
| `Reducing Fix-Commit Rate...flywheel.md` | zero references | SHELF — literally a design for the §2d medium loop, unread by it |
| SOTA report series (~20 docs) | zero references from OS spine (work-docs/research/README says they "inform future implementation") | SHELF |
| `research-papers/home-md` deep dives (Semantic Self-Awareness 2025-2030, From-2028 retrospective) | zero references | SHELF |
| `research-papers/Documents/` (except Executive MCP) | zero references | SHELF — mostly work-context (Seekapa/CRM/video), low OS relevance |
| `research-papers/el-vadt/` (373 MB) | zero references | SHELF + a repo-weight problem; sales-domain, wake-trigger material at best |
| `research-papers/knowledge/` | empty scaffold | DEFECT — a taxonomy with no content |
| §2b citations: METR, 2509.09677, ACL "Illusion of Insight", debate-martingale, homogenization, Anthropic posts | cited in prose only; no file, no appendix, no fetchable record | HALF-WIRED — they shaped §2b once, but nothing can re-verify or extend them (dangling `docs/research` pointer) |

### Verdict

Wired: 3 papers + 2 absorbed analyses + 1 sentence. Shelf: ~430 files.
The system's own INDEX admits it: "Research digests... papers in CLAUDE-OS §2b"
points at prose, not artifacts. The research loop exists as PRD row AUTO-17
(TODO), a spec paragraph (§P5), and a TODO line — no code, no cron, no schema
(VERIFIED: `ls tools/selfimprove/` → `proposals.jsonl`, `scan.py` only).

---

## 3. Pipeline design — AUTO-17: `tools/selfimprove/research_sweep.py`

Design goal: a paper (local or web) becomes a **practice-diff proposal row**
against CLAUDE-OS §2b/§2c, entering the SAME approval queue the medium loop
already uses (`proposals.jsonl` → operator approves → PR, per ADR-0005/0012).
Research that cannot name the practice row it would change is filed as
reference, not proposed.

### 3.1 Sources

**Local shelf (backfill, then watch for new/changed files by mtime against a
seen-index):**

| Priority | Path | Why |
|---|---|---|
| 1 | `perplexity_research-11.5.26` (FILE — fix the spec's trailing slash) | named seed shelf; 3 dense answers |
| 1 | `work-docs/Next-Gen AI Coding Intelligence 2026*.md` | direct §2b subject matter |
| 1 | `work-docs/sol5.6-harness.txt`, `harness-structure-standard-2026-07-09.md` | harness-engineering practices |
| 1 | `work-docs/code-quality-standard-2026-07.md`, `Reducing Fix-Commit Rate*.md`, `implementation-fixes-playbook-2026-07.md`, `coding-effort-craft-completion-2026-07.md` | quality gates → L5 fabric |
| 2 | `work-docs/research/*.md` | the declared research lane |
| 2 | `work-docs/` SOTA series (20 docs) | per-domain practice mining, lower cadence |
| 3 | `research-papers/home-md/` frontier essays | 2027-2030 horizon items |
| 4 | `research-papers/Documents/`, `Prompts/` | work-context; mine on demand only |
| EXCLUDE | `research-papers/el-vadt/`, `docs-shoval/` dups, `knowledge/` empties | sales-domain / duplicates / empty; candidates for archive-out |

**Web (weekly, cloud rail so it survives laptop sleep):**

- arXiv API (`http://export.arxiv.org/api/query`), categories `cs.AI+cs.SE+cs.CL`,
  submittedDate last 7 days, fixed query set (versioned in the tool):
  `"agent harness" OR "harness engineering"`; `"long-horizon" AND "LLM agent"`;
  `"code agent" AND (verification OR "world model")`; `"context engineering"`;
  `"multi-agent" AND failure`; `"self-improving" AND agent`;
  `(homogenization OR slop) AND "language model"`; `"process reward model" AND code`.
  Cap: top 10/week after screening.
- Anthropic engineering blog + release notes (WebFetch of the index page, diff
  against seen-index) — §2b already leans on two posts.
- Re-verification lane: the 9 §2b citations get fetched ONCE into
  `docs/research/` (abstract + link + date + one-line finding each), closing the
  dangling appendix pointer.

### 3.2 Stages (one run = one pass, bounded)

```
harvest  -> screen -> extract -> practice-diff -> emit -> (operator gate) -> PR
```

1. **harvest** — list new/changed local files (mtime > seen-index) + web results.
   Write raw hits to `state/research/seen-index.jsonl` (id = sha1 of path|url).
2. **screen** — keep only items that plausibly touch a named surface: one of
   §2b rules 1-12, a §2c native-feature row, an L0-L8 layer, or an active spec.
   Everything else → `status:"reference"` row (kept, never proposed).
3. **extract** — per kept item, ONE claim: `finding` (one sentence), `evidence`
   (quote/section), `class` (measured-result | vendor-doc | essay | speculation).
   Speculation never becomes a proposal (calibrated-claims).
4. **practice-diff** — the core move. Compare the finding against the CURRENT
   practice table (parse the §2b markdown table at run time — no hardcoded copy):
   - CONFIRMS a row → strengthen citation only (append to docs/research/ card).
   - EXTENDS a row → proposal: amend rule text + name the new stick.
   - CONTRADICTS a row → proposal (risk ≥ med, never auto).
   - NEW practice, no row → proposal to ADD a row — must name mechanism + stick,
     else it stays reference (a rule with no stick is a defect, ADR-0005).
5. **emit** — append rows to `tools/selfimprove/proposals.jsonl` (schema below),
   print top-5, add a "research" section to the daily/weekly digest. Migrates to
   `ecosystem.db.proposals` when AUTO-06 lands (source="research_sweep").
6. **gate** — unchanged: operator approves → the session (or nightly workflow)
   turns the practice_diff into a PR editing CLAUDE-OS.md / a rule / a hook.
   Auto-apply: NEVER for §2b changes (they are constitution-class).

### 3.3 Output schema (proposal row, superset of scan.py's `proposal()`)

```json
{
  "id": "sha1[:10] of title",
  "title": "Practice-diff: <short imperative>",
  "why": "<finding, one sentence>",
  "risk": "low|med|high",
  "auto_actionable": false,
  "evidence": "work-docs/... | arXiv:2509.09677",
  "kind": "research",
  "score": 0,
  "citation": {
    "source": "local|arxiv|blog",
    "ref": "path-or-arxiv-id-or-url",
    "date": "2026-07-24",
    "class": "measured-result|vendor-doc|essay|speculation",
    "claim": "<one-line finding>"
  },
  "practice_diff": {
    "target": "CLAUDE-OS.md#2b rule 3 | dot-claude/rules/x.md | new-row",
    "relation": "extends|contradicts|new",
    "current": "<quoted current practice text or 'absent'>",
    "proposed": "<exact replacement/addition text>",
    "stick": "<the enforcement mechanism: hook|gate|cron|CI — required>"
  },
  "status": "open"
}
```

Required code changes in `scan.py` ecosystem (small): add `"research": 3` to the
kind→score map (currently `{"gap":3,"hygiene":2,"growth":3,"health":4}`, would
KeyError on a research row — VERIFIED from source); scan.py and research_sweep.py
must append/merge on id, not blind-overwrite proposals.jsonl (today scan.py
`write_text`s the whole file — a research row would be erased on the next scan;
VERIFIED scan.py:113).

### 3.4 Cadence + rails

- **Weekly** (Sunday night), as the research stage of the weekly self-improve
  loop (§2d medium loop; TODO line "Research stage in weekly self-improve cron").
- **Primary rail: GitHub Actions** `schedule:` on claude-setup (same pattern as
  AUTO-07 nightly) — the corpus is git-tracked (VERIFIED: 173 + 260 + 1 files in
  git), so the cloud runner can read it; local cron is session-bound and AUTO-18
  is operator-blocked, so cloud-first is the only rail that runs this week.
- Budget: ≤10 web items + ≤5 local files per run, ≤5 proposals per run (spam cap
  mirrors the autonomy-PR premortem).
- One-time **backfill mode** (`--backfill`): walk priority-1/2 local shelf, cap 5
  proposals per run until drained (~4-6 weekly runs to clear the July docs).

### 3.5 How a paper becomes practice (lifecycle, end to end)

paper → harvest row → screened (targets §2b rule N) → claim extracted →
practice_diff row in proposals.jsonl → surfaces in digest → operator approves →
PR: CLAUDE-OS §2b row edited + enforcement artifact (hook/gate/cron) in the same
PR (ADR-0005: no prose-only rule) → review fabric reviews it → merge → citation
card written to `docs/research/` → lesson row if the paper invalidated prior
practice. The §2b table stays the single practice registry; `docs/research/`
becomes the (currently missing) appendix of citation cards.

---

## 4. Worked example — one real shelf doc → the proposal it would emit

Input: `work-docs/Reducing Fix-Commit Rate & Building a Self-Improving Code
Quality Flywheel.md` (VERIFIED read: ~22% fix-commit rate on cs-agents = 26/120;
DORA 2024 rework-rate benchmarks 10-25% avg, 5-10% best; fix commits =
intent-level failure crossing the merge gate; agentic repos churn because gates
are optional; prescription = four pre-merge gates + wire fix-commit rate into an
automated reflect-and-propose loop).

Screen: targets §2d medium loop (self-improvement scanner) + §2b rule 3
(external verifiers at boundaries). Class: measured-result (cited DORA + repo
data). → proposal:

```json
{
  "id": "a3f1c9d02e",
  "title": "Practice-diff: add fix-commit-rate as a scanner signal + digest metric",
  "why": "Fix-commit rate (fix/hotfix/revert commits over total) is an intent-level defect-escape metric; 22% measured on cs-agents vs 5-10% best-practice; the OS medium loop currently reads TODO/git/hooks/flywheel but no quality-outcome signal",
  "risk": "low",
  "auto_actionable": false,
  "evidence": "work-docs/Reducing Fix-Commit Rate & Building a Self-Improving Code Quality Flywheel.md",
  "kind": "research",
  "score": 6,
  "citation": {
    "source": "local",
    "ref": "work-docs/Reducing Fix-Commit Rate & Building a Self-Improving Code Quality Flywheel.md",
    "date": "2026-07-24",
    "class": "measured-result",
    "claim": "rework/fix-commit rate is a first-class instability metric (DORA 2024); in agentic repos it directly measures what escaped the merge gates"
  },
  "practice_diff": {
    "target": "tools/selfimprove/scan.py + CLAUDE-OS.md#2d medium loop",
    "relation": "extends",
    "current": "scan.py signals: open TODOs, git drift, hook health, flywheel volume, tools-without-tests. No signal measures whether shipped work was CORRECT (defect escapes).",
    "proposed": "scan.py signal #6: for each active repo, fix_rate = commits matching ^(fix|hotfix|revert|correct) / total over trailing 90d (git log --oneline); >15% emits a 'health' proposal naming the repo and its top fixed files; rate lands in the daily digest. §2d medium-loop text gains: 'quality outcomes (fix-commit rate) feed the weekly diff-proposal pass.'",
    "stick": "cron (weekly self-improve run) + digest surfacing; escalation: repo >20% for 2 weeks -> proposal to add a pre-merge gate from code-quality-standard-2026-07.md Q5"
  },
  "status": "open"
}
```

This is the template motion for the whole shelf: the Next-Gen 2026 doc emits
diffs against §2b rule 2 (context-rot numbers → tighten the fresh-context
threshold) and §2c (tool lazy loading row); the Perplexity file emits an
"extends" diff on §2b rule 3 (solver-verification/PRM as a future verifier
class, filed at horizon-2027 unless a stick exists today);
`code-quality-standard-2026-07.md` emits a NEW-row proposal binding its Q1-Q7
rubric to the review fabric as an aspect verifier (§2b rule 12).

---

## 5. Top 6 moves

1. **Build `tools/selfimprove/research_sweep.py` (AUTO-17)** to §3 spec —
   harvest/screen/extract/practice-diff/emit, `kind:"research"` rows into
   proposals.jsonl. Fix the two scan.py landmines first: kind-score KeyError +
   whole-file overwrite (merge-on-id instead).
2. **Create `docs/research/` and backfill 9 citation cards** for the §2b list
   (METR, 2509.09677, Illusion of Insight, debate-martingale, homogenization,
   2510.01171, Antislop, MAST, Anthropic posts) — closes the dangling "docs/
   research appendix" pointer and gives the sweep its diff baseline.
3. **Wire the weekly cloud rail**: `.github/workflows/research-sweep.yml`
   (schedule, Sunday), same guardrails as the AUTO-07 nightly (branch-scoped
   `auto/*`, ≤5 proposals, PR-gated) — corpus is git-tracked so the runner can
   read it; local cron stays blocked on AUTO-18.
4. **Run backfill on the priority-1 shelf** (perplexity file + 7 July harness/
   quality docs) — expect ~10-15 practice-diff proposals; the worked example
   (§4) is the first.
5. **Fix the spec's corpus reference**: `perplexity_research-11.5.26/` →
   `perplexity_research-11.5.26` (file) in
   `docs/specs/2026-07-24-autonomy-implementation.md:117`.
6. **De-shelf the dead weight**: propose (destructive-op gate: operator OK)
   moving `research-papers/el-vadt/` (373 MB sales-domain PDFs) out of the OS
   repo to the work-archive, deleting the empty `research-papers/knowledge/`
   scaffold, and deduping `docs-shoval/` vs `work-docs/` — the corpus the sweep
   watches should be the corpus that can change practice.
