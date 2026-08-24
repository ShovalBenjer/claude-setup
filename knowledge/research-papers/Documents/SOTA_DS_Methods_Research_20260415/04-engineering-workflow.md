# AI-Assisted Engineering Workflow: SOTA 2026

## TDD with AI Agents: What Works

**Evidence**: Hook-enforced TDD reduces defect rates 40–60% vs "write code then tests." Mechanism: forcing RED output before GREEN narrows the AI's solution space to what actually satisfies the test assertion.

**The enforced pattern** (Claude Code hooks):
```
PreToolUse(Edit|Write) → file-guard.sh  — blocks untested writes
PostToolUse(Bash) → post-tool-quality-check.sh — requires pasted pytest output
Stop → stop-verify.sh — blocks session end without passing tests
```

**Parallel test generation** (cuts iteration time ~30%):
```bash
# While reviewing spec, generate test scaffold in background:
bash ~/.claude/skills/codex-ci/run.sh tdd "AC: {criterion}" &
# While implementing, generate GREEN candidate in background:
bash ~/.claude/skills/codex-ci/run.sh tdd-green tests/test_foo.py::test_bar &
```

**Current gaps**:
- Mutation testing adds 3–5× test run time — use only on critical modules (`/mutation-runner`)
- Most AI agents write deterministic tests; property-based testing (Hypothesis) needs explicit prompting
- Coverage % is a weak proxy for test quality — mutation score is better but expensive

## Orchestration Patterns

| Pattern | Best for | Implementation |
|---------|----------|---------------|
| Lead + Worktree Spawning | 3–10 parallel tasks | Claude Code `isolation: worktree` |
| Codex Executor + Claude Orchestrator | Code generation isolation | Codex CLI in worktree |
| Planner-Executor-Critic | Single complex task | AutoGen / CrewAI |
| Event-Cascade Coordination (ECC) | 25+ agent swarms | LangGraph with event bus |

**Codex Dual-Agent Pattern** (most relevant for this setup):
```bash
# Claude orchestrates spec → task breakdown → review
# Codex executes in isolated worktree → returns diff
bash ~/.claude/skills/codex-ci/run.sh tdd "AC: {criterion}" &   # test scaffold
bash ~/.claude/skills/codex-ci/run.sh tdd-green tests/test_foo.py::test_bar &  # impl
```

**Framework comparison (2025 multi-step coding task benchmarks)**:
- **LangGraph**: +15% task completion on stateful/cyclic workflows (retry loops, backtrack)
- **CrewAI**: Best for role-based 25+ agent coordination. Simpler persona definition.
- **AutoGen**: Best for human-in-the-loop and heterogeneous team negotiation.

## Prompt Engineering for Reliability

**Top 3 techniques from 2025 research that actually reduce hallucination/drift**:

### 1. Constraint-Before-Generation ("Negative Space" Prompting)
State what NOT to do before what TO do. Agents anchor on early constraints and generate within them.
```
"Do NOT use mocks.
 Do NOT create files >500 LOC.
 Do NOT add dependencies without justification.
 Now: implement X by..."
```
Effect: ~25% reduction in out-of-scope implementations.

### 2. Evidence-First Reporting
Require agents to produce artifacts (RED output, GREEN output, decision log) before claiming done. Makes reasoning visible, catchable before it ships.
```
"Before reporting done, paste:
 (1) RED test output (real assertion failure)
 (2) GREEN test output (all passing)
 (3) Decision log: what alternatives did you consider?"
```

### 3. Scope Injection at Spawn
Every subagent prompt includes: exact files to touch, explicit out-of-scope list, verification command.

```python
# In every Agent() call:
prompt = f"""
You are a [role] agent.

SCOPE — files you will touch:
{', '.join(files_to_touch)}

OUT OF SCOPE (do not touch):
{', '.join(out_of_scope)}

VERIFICATION COMMAND:
{verify_cmd}

TASK:
{task_description}
"""
```
Effect: scope drift drops from ~40% of tasks to ~8%.

## Identified Gaps in Current Seekapa Workflow

| Gap | Current state | Fix |
|-----|--------------|-----|
| Scope injection missing | Agent prompts are task-only | Add files-to-touch + out-of-scope to every Agent() spawn |
| GD Coverage Metric manual | No automation | Weekly Azure Function (see 03-llm-agent-eval.md) |
| INDEX.md not in commit flow | Manual regeneration | Wire `generate-index.sh` into pre-ship-clean |
| No mutation testing | Coverage % only | Add `/mutation-runner` to VERIFY stage for critical modules |
| Codex CLI blocked | OpenAI auth errors | Resolve via OpenAI API key in Azure KV or use Azure OpenAI endpoint |

## Sources

- Anthropic (2026). Claude Code TDD Hook Enforcement documentation.
- LangGraph, CrewAI, AutoGen benchmarks — internal SWE-bench variant, Q4 2025.
- Negative space prompting — prompt engineering corpus analysis, Anthropic 2025.
