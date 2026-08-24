---
name: eval-runner
description: Run the Foundry-only 4-phase eval pipeline (deterministic gate → smoke 10-row → expanded 40-80 → nightly 80-150) using grok-4-1-fast-reasoning-2-eval primary + DeepSeek-V3.2 audit. Cost-bounded (≤1500 input / ≤120 output per row). Triggers on "/eval", "/eval-runner", "run smoke", "run nightly eval".
model: claude-opus-4-7
---

# Eval Runner — Test & Eval Integration Skill

**Invocation:** `/eval` or when user requests test/eval execution

## Purpose

Run project-specific test suites, eval pipelines, and quality checks.
Present results as structured summaries that Claude can reason about
without needing to parse raw terminal output (saving tokens).

## When to Activate

- Before merging or completing a feature
- After editing critical paths (scoring, ingestion, layout engine)
- When user asks "does this pass?" or "run tests"
- As part of Stop hook verification

## Project-Specific Commands

### social-intelligence-unit

```bash
# Unit tests (fast)
cd ~/projects/social-intelligence-unit && uv run pytest tests/ -x --tb=short -q

# Type checking
cd ~/projects/social-intelligence-unit && uv run mypy src/ --ignore-missing-imports

# Linting
cd ~/projects/social-intelligence-unit && uv run ruff check src/

# Security scan
cd ~/projects/social-intelligence-unit && uv run bandit -r src/ -ll

# Full quality gate
cd ~/projects/social-intelligence-unit && uv run pytest && uv run mypy src/ && uv run ruff check src/
```

### figma-4-all

```bash
# P0 (pre-commit)
cd ~/projects/figma-4-all && bun run test:p0

# Staged (PR-level)
cd ~/projects/figma-4-all && bun run test:staged

# QA (VABB metrics on 232 hard cases)
cd ~/projects/figma-4-all && bun run qa

# Syntax validation (ES2017)
cd ~/projects/figma-4-all && bun run validate:syntax

# Full quality gate
cd ~/projects/figma-4-all && bun run validate:syntax && bun run test:p0 && bunx eslint . --fix
```

### seekapa-video

```bash
# TypeScript validation
cd ~/projects/seekapa-video && bun run typecheck

# Linting (ESLint 9 flat config)
cd ~/projects/seekapa-video && bun run lint

# Unit & integration tests
cd ~/projects/seekapa-video && bun run test

# Full quality gate
cd ~/projects/seekapa-video && bun run typecheck && bun run lint && bun run test
```

## How to Report Results

After running tests, provide:

1. **Pass/Fail count** (e.g., "47 passed, 2 failed")
2. **Failed test names** (if any)
3. **Coverage delta** (if measurable)
4. **Recommendation** (proceed / fix required / investigate)

Keep reports under 10 lines. No raw terminal dumps.

## Integration with Hooks

The Stop hook (`~/.codex/hooks/stop-checklist.sh`) checks if tests were run.
This skill provides the actual test execution. Together they form a feedback loop:

```
Edit code → Stop hook detects changes → Prompts for test run → /eval executes → Report
```

## Future: Braintrust / DeepEval Integration

When configured, this skill will also:

- Run Braintrust experiment suites for agent evaluation
- Run DeepEval assertions for reasoning quality
- Compare results against golden baselines
- Post deltas to configured notification channel

Add these commands to the project-specific sections above once
the eval infrastructure is deployed.
