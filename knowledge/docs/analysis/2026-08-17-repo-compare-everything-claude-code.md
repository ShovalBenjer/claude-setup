# Repo compare: affaan-m/everything-claude-code (ECC) vs claude-setup

VERIFIED via shallow clone `git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git`
into `/home/shov/.claude/jobs/b771656c/tmp/everything-claude-code`, HEAD `06c5e118`, 2026-08-16.
Cloning succeeded (network reachable, repo public), not a not-found/blocked case.

## (a) What it is

ECC ("ecc.tools", plugin name `ecc`, v2.2.0, MIT, single maintainer). A large
multi-harness prompt/skill/hook distribution: 68 agents, 285 skills, 94 legacy
command shims, plus hooks, rules, "memory," continuous learning, and an
"AgentShield" security-scan product line. Ships parity surfaces for Claude Code,
Cursor, Codex, OpenCode, Kiro, Gemini, Zed, Copilot, Antigravity, Qwen, most content
is prose skill/rule files duplicated per-harness (`.cursor/rules/*.md`,
`.kiro/hooks/*.kiro.hook`, `rules/<lang>/hooks.md` x20 languages). Has a paid tier
("ECC Pro", GitHub App, $19/seat/mo) layered on the free OSS core. Read only the
Claude-relevant subset (`.claude/`, `skills/`, `hooks/`, `commands/`).

## (b) Overlap with our harness

| Mechanism | Ours | ECC |
|---|---|---|
| Gate before "done" | `tools/gate/gate.py` (12-domain contract, exit-code oracle) | `delivery-gate` Stop hook: deterministic regex/mtime/disk checks, exit 2 blocks |
| Verification loop | gate + oracle selftests + mutation (`tools/audit/mutate.py`) | `verification-loop` SKILL.md, prose checklist (build/type/lint/test), no enforcing code, agent must choose to run it |
| Learned-pattern capture | `state/lessons.jsonl`, memory files, rules under `~/.claude/rules/` (human-curated) | `continuous-learning-v2`: PreToolUse/PostToolUse hook (`observe.sh`) writes `observations.jsonl` 100% of the time; background Haiku agent clusters into confidence-scored "instinct" YAML files |
| Ledgers | `state/*.jsonl` append-only, hash-chained bus (`tools/bus/bus.py verify`) | `observations.jsonl` per project, no hash chain found |
| Skills sync (drift check) | `tools/audit/skills_sync.py check` | none found, no live-vs-repo drift oracle |
| Review panel | `tools/review/panel.py` writes `state/reviews/<sha>.json` | none found as code; "review" is prose-only in skills |
| Prior-art / novelty gate | `tools/map/codemap.py prior-art` | none found |
| Security | `boundary-contracts.md` (rule, prose) + PII rules | `everything-claude-code-guardrails.md` (prose, explicitly labeled "Review before treating it as a hard policy file") + AgentShield (separate npm package, not inspected, out of clone scope, road-mapped per `docs/architecture/agentshield-enterprise-research-roadmap.md`, i.e. more roadmap than shipped enforcement in this repo) |

## (c) Ours, not theirs (VERIFIED absent in the clone)

- A falsifier layer: nothing in ECC pairs a check with a mutation that must turn it
  red (our `tools/audit/mutate.py --spec all`). `verification-loop` and
  `delivery-gate` are single-direction checks with no adversarial self-test found.
- Hash-chained, append-only bus with a verify command (`tools/bus/bus.py verify`).
  ECC's `observations.jsonl` is plain JSONL, no chain/tamper-evidence found.
- A skills-sync oracle comparing live deployed state against repo payload
  (`skills_sync.py check`), ECC has no equivalent; drift between its 7 harness
  mirrors is handled by a prose instinct ("cross-platform-sync": "mirror shipped
  changes... root repo as source of truth") not by a checker.
- Quality-contract-as-data (`quality-contract.json` + `docs/QUALITY-CONTRACT.md`)
  declaring UNCOVERED-fails-by-default per domain. ECC's guardrails file explicitly
  says "review before treating it as a hard policy file", the opposite posture.
- Prior-art-gate tied to component size (300+ line components owe a record with
  named alternatives). Nothing analogous found in ECC.

## (d) Theirs, not ours, adopt/watch/ignore

1. **`delivery-gate` Stop hook (deterministic, exit-2 blocking)**, ADOPT (watch
   first). Mechanism: mtime-check on "learning library" files + disk-space
   threshold + regex rationalization scan on transcript tail, block only on disk
   critical or >=3 stale learning libs. This is a *cheap* mechanical companion to
   our gate, not a replacement, it would land as a new Stop-hook check in
   `dot-claude/hooks/`, gated by `settings.json`, checking whether `state/*.jsonl`
   or `docs/analysis/` were touched on a complex-edit-count session. Watch first
   because our existing Stop-hook already has a completion_gate.py (per
   `long-checks-background.md`); a second Stop hook risks double-gating without a
   measured gap. **Verdict: WATCH**, write the gap analysis before adding.
2. **Project-scoped "instincts" (continuous-learning-v2)**, this is the item
   flagged for special attention. See section (e) below for the full comparison.
   **Verdict: IGNORE the mechanism as designed (background-agent-authored,
   confidence-scored auto-instincts), WATCH the project-scoping idea** (their
   git-remote-hash-based project isolation is a real gap: our
   `~/.claude/rules/*.md` are global-only, with no built-in isolation between
   e.g. a Seekapa rule and a personal-repo rule beyond manual file placement,
   which the `project-template/` split already partially answers, see (e)).
3. **`verification-loop` SKILL.md multi-phase checklist (build/type/lint/test,
   80% coverage target)**, IGNORE. Pure prose, no enforcing code, strictly weaker
   than our gate.py contract (exit-code oracle, UNCOVERED-fails). Nothing to import.
4. **Cross-harness rule mirrors (`rules/<lang>/hooks.md` x20 languages,
   `.cursor/`, `.kiro/`, `.opencode/` parity)**, IGNORE for us; we are Claude-Code
   only by design (repo-topology / gastown registry assume one harness). Would be
   pure surface-area cost with no current multi-harness need.
5. **AgentShield security scanning (`ecc-agentshield` npm package)**, WATCH,
   unverified. Not present in this clone as inspectable code (only a research
   roadmap doc and one example policy-exception file). Cannot verify enforcement
   quality; do not adopt sight-unseen. If revisited, pull the actual npm package
   separately and check for a real oracle, not roadmap prose.
6. **`hooks/hooks.json` consolidated dispatcher pattern (single Bash/Write/Edit
   matcher routing to `run-with-flags.js` sub-dispatchers)**, WATCH. Interesting
   for reducing hook count/overhead (we have 29 files in `dot-claude/hooks`, 23 of
   29 unwired per AGENTS.md), but their dispatcher is Node-based with a plugin-root
   resolution shim of real complexity (visible in the inlined `node -e` blob) ,
   not a clean lift. Worth studying the *pattern* (one registered hook, internal
   routing) next time hook sprawl is cleaned up, not worth porting the code.

No single skill in ECC's 285-skill tree is being named ADOPT-wholesale: the ones
inspected (`continuous-learning-v2`, `delivery-gate`, `verification-loop`) are each
either weaker than or orthogonal to an existing enforced mechanism here, and the
rest of the tree (285 skills spanning `x-api`, `investor-materials`,
`frontend-slides`, `crosspost`, etc.) is generic prose-skill content of the same
shape as our own `dot-claude/skills`, not inspected line-by-line (ASSUMED
representative from the 42 skill names read, not exhaustive).

## (e) Instincts vs our rules/memory split, the special-attention item

**ECC's "instinct" model** (v2.1, `continuous-learning-v2`):
- Source: PreToolUse/PostToolUse hooks fire on every tool call (claimed "100%
  reliable" vs skill-based v1 at "50-80%"), writing to `observations.jsonl`.
- Authoring: a *background Haiku agent* (not the operator) reads observations and
  writes atomic instinct YAML files with a numeric confidence score (0.3-0.9),
  auto-updated by repeated observation / lack of correction.
- Scope: project-hashed by git remote URL, isolated by default; promoted to global
  only after appearing in 2+ projects at avg confidence >= 0.8.
- Storage: deliberately moved OUT of `~/.claude` to `~/.local/share/ecc-homunculus`
  because "Claude Code's sensitive-path guard" blocks background writes under
  `~/.claude`, i.e. the design routes around a safety boundary rather than
  respecting it. VERIFIED from SKILL.md's own "Data Directory" section.
- Windows: VERIFIED-in-their-docs non-functional ("no-op... see issue #2489") ,
  the background observer process is killed when its spawning hook exits.

**Our rules/memory split**, per the loaded global CLAUDE.md and
`gastown-company-registry.md`:
- Rules (`~/.claude/rules/*.md`) are operator-authored, dated, named-incident
  provenance (e.g. `boundary-contracts.md` cites the exact PR and reviewer that
  motivated it). No confidence score; a rule is either adopted (in the file) or
  not.
- Memory (`~/.claude/projects/.../memory/MEMORY.md`) is auto-appended one-liners
  with links to dated detail files, but every entry ties to a session artifact,
  not an unsupervised confidence-weighted inference.
- `project-template/` (this session's loaded context) already implements ECC's
  "project-scoped vs global" distinction, but by explicit human curation+ADOPTION
  (a rule is copied into a consuming repo's `.claude/rules/` on purpose), not by
  git-remote-hash auto-detection and auto-promotion.

**Comparison verdict**: ECC's instinct engine automates exactly the step this
harness's rules discipline keeps human-owned on purpose (`accepting-architectures.md`,
`calibrated-claims.md`, no auto-authored confidence claim should silently become
policy). A background agent auto-writing "near-certain (0.9)" behavioral rules from
raw tool-call observation, with promotion to global scope on repetition alone, is
the opposite of "architectures are accepted block by block" and of
"calibrated-claims" (ASSUMED masquerading as a numeric score is still ASSUMED).
The project-scoping *idea* (auto-detect which repo a rule applies to) is a real
capability gap worth watching, but the mechanism that produces the rule content is
exactly the failure mode our rule set was built to prevent. **Verdict: IGNORE the
instinct-authoring engine; WATCH only the project-scope-detection idea, and only
as a manually-gated tool** (e.g. "flag this rule as project-scoped," never
"auto-write and auto-promote this rule").

## Evidence class summary

- VERIFIED: repo cloned and readable (not blocked); file contents of
  `everything-claude-code-instincts.yaml`, `everything-claude-code-guardrails.md`,
  `continuous-learning-v2/SKILL.md`, `delivery-gate/SKILL.md`,
  `delivery-gate/hooks/quality-gate.py`, `verification-loop/SKILL.md` (partial),
  `hooks/hooks.json` (head), `plugin.json`, README head, all read directly, quoted
  above.
- ASSUMED: the 285-skill and 68-agent claims are ECC's own README count, not
  independently tallied here; the "42 skill names read" in (d) is a directory
  listing, not content review, so representativeness of the untouched ~250 skills
  is unverified. AgentShield's actual enforcement quality is unverified (no code
  in this clone, only roadmap doc + one example file).
- Not reached: `.opencode/`, `.cursor/`, `.kiro/`, `.codex/` mirror trees; the 12
  language-specific `rules/<lang>/hooks.md` files; `scripts/hooks/` full dispatcher
  chain beyond the head of `hooks.json`; AgentShield npm package (separate repo,
  not cloned).
