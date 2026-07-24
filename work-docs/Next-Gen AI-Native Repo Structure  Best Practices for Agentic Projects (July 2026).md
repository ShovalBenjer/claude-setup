# Next-Gen AI-Native Repo Structure: Best Practices for Agentic Projects (July 2026)

## Executive Summary

Professional Python repository structure in mid-2026 has bifurcated into two camps: classic `src`-layout projects (well-suited for libraries and APIs) and an emerging **AI-native / agentic layout** tailored to LLM-based systems that wire together agents, tools, prompts, memory, and orchestration. Over 97% of companies now incorporate AI into their development workflows, and the majority of new agentic projects require a deliberate directory contract between human developers and the AI coding agents that increasingly read, modify, and generate their code. This report codifies the consensus on directory structure, docstring philosophy, file/function LOC budgets, tree-navigation patterns, and a concrete next-gen template for agentic setups like "Gastown."[^1][^2][^3]

***

## 1. The State of Professional Repo Structure in 2026

### 1.1 Why Structure Matters More in the AI Era

Modern AI coding agents (Claude Code, Cursor, Windsurf, SWE-agents) navigate repositories by traversing directory trees, reading `__init__.py`, grepping symbols, and building internal code graphs. A clean, predictable layout is no longer just a human-readability concern — it is a **machine-readability prerequisite**. RepoGraph and similar tools that parse repo-level structure for AI context require that modules and sub-agents be locatable via consistent naming conventions. RepoReviewer (March 2026), a multi-agent system for repository-level code review, explicitly decomposes work by *repository structure zones* (context synthesis, file-level analysis, prioritization).[^4][^5][^6]

The YC Spring 2025 batch — where 70+ of 144 companies build agentic AI — reinforces this: startups like Delty work on "system design and architecture based on deep codebase understanding", and the CB Insights AI Software Development Market Map (2026) shows that **code documentation & knowledge management** and **end-to-end agentic SDLC** are now distinct market categories.[^2][^7]

### 1.2 The src Layout vs. Flat Layout

The Python Packaging Authority (PyPA) recommends the **`src` layout** for packages distributed via PyPI:[^8]

- **Flat layout**: `awesome_package/` at the repo root alongside `pyproject.toml`. Simple, but risks accidental import of the in-development copy.
- **`src` layout**: `src/awesome_package/` isolated from root config files. Prevents editable-install shadowing and enforces that only intended-importable modules are on the path.[^8]

For agentic projects that are *not* distributed as packages but run as applications, a **hybrid application layout** is optimal: `src/` holds the importable business-logic core while top-level directories hold agents, tools, prompts, config, and data separately.

***

## 2. The AI-Native / Agentic Directory Layout

### 2.1 Core Principles

Effective agentic repo structure follows three principles validated by modular multi-agent research:[^9][^10]

1. **Separation of concerns by agent role** — each sub-agent type (orchestrator, planner, executor, reviewer) lives in its own module with a clear `Input → Strategy → Output` spec.[^9]
2. **Prompt-code co-location** — prompts are versioned assets, not hardcoded strings. They belong in a `prompts/` directory structured to mirror their corresponding agent.
3. **State/memory isolation** — short-term (in-context), mid-term (vector store), and long-term (persistent) memory are distinct infrastructure layers, each deserving its own directory or module.[^11]

### 2.2 Canonical Agentic Project Tree (2026)

```
my-agent-project/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── release.yml
│   └── CODEOWNERS
│
├── src/
│   └── my_agent/                  # importable core package
│       ├── __init__.py
│       ├── agents/                # one module per agent role
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   ├── planner.py
│       │   ├── executor.py
│       │   └── reviewer.py
│       ├── tools/                 # tool wrappers (function-calling / MCP)
│       │   ├── __init__.py
│       │   ├── web_search.py
│       │   ├── code_runner.py
│       │   ├── file_ops.py
│       │   └── registry.py        # tool registration / discovery
│       ├── memory/                # memory subsystems
│       │   ├── __init__.py
│       │   ├── short_term.py      # context window management
│       │   ├── vector_store.py    # embeddings / RAG
│       │   └── persistent.py      # DB-backed long-term memory
│       ├── state/                 # LangGraph-style StateGraph types
│       │   ├── __init__.py
│       │   └── schemas.py         # Pydantic state models
│       ├── workflows/             # orchestration graphs / pipelines
│       │   ├── __init__.py
│       │   ├── main_graph.py
│       │   └── sub_graphs/
│       ├── models/                # LLM client wrappers / adapters
│       │   ├── __init__.py
│       │   └── client.py
│       ├── config/                # settings, env management
│       │   ├── __init__.py
│       │   └── settings.py        # Pydantic BaseSettings
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── retry.py
│
├── prompts/                       # versioned prompt templates
│   ├── orchestrator/
│   │   └── system_v2.md
│   ├── planner/
│   │   └── chain_of_thought.md
│   └── reviewer/
│       └── code_review.md
│
├── tests/
│   ├── unit/
│   │   ├── test_agents.py
│   │   ├── test_tools.py
│   │   └── test_memory.py
│   ├── integration/
│   │   └── test_workflows.py
│   ├── e2e/
│   │   └── test_full_pipeline.py
│   └── conftest.py
│
├── data/
│   ├── fixtures/                  # test / seeding data
│   └── outputs/                   # agent run artifacts (gitignored)
│
├── docs/
│   ├── architecture.md
│   ├── agent-contracts.md         # agent I/O specs
│   └── prompts-guide.md
│
├── scripts/                       # dev / ops one-off scripts
│   ├── seed_memory.py
│   └── eval_agents.py
│
├── .env.example
├── .gitignore
├── pyproject.toml                 # uv / ruff / mypy / pytest config
├── Makefile                       # dev commands: make test, make lint
├── README.md
└── CHANGELOG.md
```

### 2.3 Key Directory Contracts

| Directory | What Goes There | Anti-patterns to Avoid |
|-----------|----------------|----------------------|
| `agents/` | One file per agent role; LangGraph node definitions | Mixing tool logic with agent logic |
| `tools/` | Tool handler functions + `registry.py` for MCP/function-call discovery | Hardcoding tool lists in agent files |
| `prompts/` | Markdown or Jinja2 templates, versioned (v1/v2 suffixes) | f-strings inlined in agent code |
| `memory/` | Vector store clients, context compressors, DB schemas | Storing embeddings inside agent state dicts |
| `state/` | Pydantic `TypedDict` / `BaseModel` for graph state | Passing raw dicts between agents[^12] |
| `workflows/` | LangGraph `StateGraph` definitions, not business logic | Monolithic 600-line graph files |
| `config/` | `pydantic-settings` `BaseSettings`; `.env` loading | `os.getenv()` scattered across modules |

***

## 3. Toolchain: The 2026 Standard Stack

The Python ecosystem has largely converged on a **`uv` + `ruff` + `pyproject.toml`** stack for new projects:[^13][^1]

```toml
# pyproject.toml (abbreviated)
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=0.3",
    "langchain-core>=0.3",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "httpx>=0.27",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "ANN", "D"]
pydocstyle.convention = "google"   # enforces docstring style

[tool.mypy]
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- **`uv`**: replaces pip + virtualenv + pip-tools; workspace support for monorepos.[^13]
- **`ruff`**: linting + formatting in one tool, ~100x faster than flake8/black combo; includes `pydocstyle` enforcement.
- **`pyproject.toml`**: single source of truth — no more `setup.py`, `setup.cfg`, `tox.ini`, `.flake8`.
- **`mypy` (strict)**: type annotations are non-negotiable in AI-native code where LLM agents read type stubs for context.[^1]

***

## 4. Docstrings in 2026: What to Doc and What Not To

### 4.1 The Docstring Debate in the AI Era

The empirical software engineering community and AI tooling have reached a nuanced consensus: **docstrings remain essential, but their form has evolved**. Three forces shape this:[^14][^1]

1. **AI agents use docstrings as structured signals.** RepoAgent (2024) explicitly relies on docstring extraction to build repository-level documentation graphs. LLM context windows are finite — a well-written `Args:` block is more token-efficient than the agent reading the full function body.[^15]
2. **Self-documenting code is not enough.** The Hitchhiker's Guide principle — "if you use docstrings in internal modules, your whole-module documentation should give a holistic view" — applies more strongly when automated agents generate code that lacks tribal knowledge.[^16]
3. **Docstring-everything is wasteful and breaks with AI-generated code.** Studies on 75%+ AI code adoption show that auto-generated boilerplate docstrings add noise without value.[^1]

### 4.2 The 2026 Docstring Decision Framework

**Always docstring:**
- Public functions and classes (`def`, not `_private`)
- Any function longer than ~20 lines
- Agent entrypoints and tool handlers — these are read by LLM context builders
- Pydantic models and `TypedDict` state schemas — describe the *semantics*, not just field names
- Module-level docstrings for every module file (one paragraph, what this module does)

**Conditional docstring (docstring if non-obvious):**
- Private helper functions (`_helper()`) — docstring only if the logic is subtle
- Simple property accessors or pass-through wrappers

**Skip docstring:**
- `__init__` when the class docstring already describes parameters
- One-liner utility functions with self-explanatory names (`def get_timestamp(): return datetime.now()`)
- Generated stub code or migration files

### 4.3 Recommended Style: Google over NumPy

Google-style docstrings are the dominant choice for agentic projects because they are:[^17][^15]
- More readable in raw text form (important for prompt injection)
- Better supported by ruff's `pydocstyle` enforcement
- Compatible with MkDocs + mkdocstrings (the 2026 standard for auto-docs)

```python
def invoke_tool(tool_name: str, args: dict[str, Any]) -> ToolResult:
    """Execute a registered tool by name with the provided arguments.

    Dispatches to the tool registry and handles retries on transient errors.
    Raises ToolNotFoundError if the tool is not registered.

    Args:
        tool_name: The registry key of the tool to invoke.
        args: Keyword arguments forwarded to the tool handler.

    Returns:
        ToolResult containing output, status code, and execution metadata.

    Raises:
        ToolNotFoundError: If tool_name is not in the registry.
        ToolExecutionError: If the tool fails after max retries.

    Example:
        result = invoke_tool("web_search", {"query": "LangGraph 2026"})
    """
```

***

## 5. Lines of Code (LOC) — Recommended Budgets

### 5.1 The Empirical Baseline

PEP 8 and the Hitchhiker's Guide do not specify hard LOC limits, but the MASAI multi-agent architecture research (Microsoft, 2024-2025) found that **unnecessarily long trajectories inflate costs and add extraneous context**. The same principle applies to source files: long files reduce AI agent localization accuracy. MASAI's `Edit Localizer` achieved a 75% file-level localization rate specifically because the repo structure was modular and files were scoped tightly.[^9]

The large-scale ML Python project study (2024) found that poorly structured ML repos tend toward monolithic files that make automated analysis harder. The eye-tracking readability study confirms function length affects cognitive load directly.[^18][^17]

### 5.2 Practical LOC Guidelines for Agentic Projects

| Scope | Recommended Budget | Hard Limit | Notes |
|-------|-------------------|------------|-------|
| **Function / method** | ≤ 30 LOC | 50 LOC | Exceeding 30 is a refactor signal |
| **Class** | ≤ 150 LOC | 300 LOC | Large classes should be split by responsibility |
| **Module file** | ≤ 300 LOC | 500 LOC | Files >300 LOC lose AI context coherence |
| **Agent file** | ≤ 200 LOC | 350 LOC | Agent node logic should be narrow |
| **Workflow / graph file** | ≤ 250 LOC | 400 LOC | Use sub-graphs for complex flows |
| **Test file** | ≤ 400 LOC | 600 LOC | Split by feature boundary |

These budgets align with the "divide and conquer" principle of MASAI and the "ravioli over spaghetti" preference from the Hitchhiker's Guide (hundreds of small, well-scoped pieces rather than large monolithic units).[^16][^9]

**The AI-native corollary**: Keep each file to a *single conceptual concern*. An AI agent reading `tools/web_search.py` should be able to understand it in full within one context pass. Files that exceed ~500 LOC typically require the agent to paginate reads, degrading tool use accuracy.[^6]

***

## 6. Tree Navigation & Quick Search Patterns

### 6.1 Bash Tree Commands for Repo Exploration

For rapid human and agent inspection, these commands cover 95% of navigation needs:

```bash
# Full tree excluding noise (gitignored, caches, venvs)
tree -I '__pycache__|*.pyc|.git|.venv|node_modules|*.egg-info' --dirsfirst

# Just directory structure (no files) — great for architecture overview
tree -d -I '.git|.venv|__pycache__|*.egg-info'

# Show up to 3 levels deep (good for large repos)
tree -L 3 -I '.git|.venv|__pycache__'

# Show only Python files
find . -name "*.py" | grep -v '__pycache__' | sort

# Find all agent entrypoints
grep -rl "class.*Agent\|def invoke\|@tool" src/ --include="*.py"

# Quickly locate prompt templates
find prompts/ -name "*.md" -o -name "*.j2" | sort

# Count LOC per file (sorted, largest first)
find src/ -name "*.py" | xargs wc -l | sort -rn | head -20

# Find all public functions/classes in a module
grep -n "^def \|^class \|^    def " src/my_agent/agents/orchestrator.py

# Search for TODO / FIXME markers
grep -rn "TODO\|FIXME\|HACK" src/ --include="*.py"

# Inspect all tool registrations
grep -rn "@tool\|registry.register\|tool_name" src/tools/ --include="*.py"
```

### 6.2 AI Agent Navigation Patterns

Modern AI software agents (SWE-agent, RepoReviewer, MASAI) use a canonical read pattern:[^4][^9]

1. `LIST(/)` → understand top-level structure
2. `LIST(src/)` → find the importable package
3. `READ(src/my_agent/__init__.py)` → understand public API
4. `READ(src/my_agent/agents/orchestrator.py, class=OrchestratorAgent)` → agent signature
5. `grep` for symbol usage across repo

A repo that cleanly separates `agents/`, `tools/`, `prompts/`, and `workflows/` lets the agent localize changes **without reading the entire codebase**, directly improving resolution rates in automated tasks.[^6][^9]

***

## 7. Gastown-Specific Next-Gen Recommendations

Based on your Gastown agentic setup, below is a concrete upgrade path:

### 7.1 Adopt the Three-Layer Agent Architecture

Structure agents in three tiers inspired by MASAI and LangGraph patterns:[^19][^9]

```
agents/
├── orchestrator.py    # top-level: receives task, delegates, tracks state
├── planner.py         # mid-level: breaks tasks into sub-tasks (CoT)
├── executor.py        # low-level: calls tools, handles retries
└── reviewer.py        # post-execution: validates output, triggers re-runs
```

Each file owns *one role*, imports only from `tools/`, `memory/`, and `state/`, never from sibling agents directly — communication flows through `state/schemas.py`.

### 7.2 Version Your Prompts

Store all prompts as Markdown or Jinja2 files in `prompts/`. This enables:
- **Diff tracking** — prompt changes show up in git history
- **A/B testing** — swap `system_v1.md` ↔ `system_v2.md` without code changes
- **AI agent access** — agents can self-read their own prompt file for meta-reasoning

```
prompts/
├── orchestrator/
│   ├── system_v3.md        # current
│   └── system_v2.md        # archived
└── executor/
    └── tool_use.md
```

### 7.3 Enforce State via Pydantic

All inter-agent communication should pass through typed Pydantic schemas:[^12]

```python
# state/schemas.py
from pydantic import BaseModel, Field
from typing import Annotated
from langgraph.graph.message import add_messages

class AgentState(BaseModel):
    task: str
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    current_agent: str = "orchestrator"
    iteration: int = 0
    done: bool = False
```

This gives you: free serialization to JSON, schema validation at every node boundary, and automatic documentation generation.

### 7.4 Tool Registry Pattern

Avoid scattered tool definitions. Use a central `registry.py`:

```python
# tools/registry.py
from typing import Callable
from dataclasses import dataclass

@dataclass
class ToolSpec:
    name: str
    description: str  # this gets injected into LLM system prompt
    fn: Callable
    schema: dict      # JSON schema for function calling

_REGISTRY: dict[str, ToolSpec] = {}

def register(name: str, description: str, schema: dict):
    def decorator(fn: Callable):
        _REGISTRY[name] = ToolSpec(name, description, fn, schema)
        return fn
    return decorator

def get_tool_schemas() -> list[dict]:
    return [{"name": t.name, "description": t.description, "parameters": t.schema}
            for t in _REGISTRY.values()]
```

This pattern makes tool discovery transparent to both humans and AI agents via `grep`.[^19][^9]

### 7.5 Makefile for Dev Ergonomics

```makefile
.PHONY: install test lint type-check run clean

install:
    uv sync --all-extras

test:
    uv run pytest tests/ -v --tb=short

lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

type-check:
    uv run mypy src/

run:
    uv run python -m my_agent.main

clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -name "*.pyc" -delete
```

***

## 8. Docstring Quick Reference for Agentic Code

| Code Element | Docstring? | Style | Must Include |
|--------------|-----------|-------|-------------|
| Agent class | ✅ Always | Google | Role, inputs, outputs, tools used |
| Tool handler function | ✅ Always | Google | Args, Returns, side effects, Example |
| Pydantic state schema | ✅ Always | Google | Semantics of each field |
| Module `__init__.py` | ✅ Always | One-line + paragraph | What the module does |
| `_private` helper | If subtle | Inline `#` comment ok | Purpose, non-obvious logic |
| `__init__` with class docstring | ❌ Skip | — | Already in class docstring |
| Simple property | ❌ Skip | — | Name is self-documenting |
| Test function | ❌ Optional | Inline only | Test name should describe the case |

***

## 9. Repo Navigation Quick Search Cheat Sheet

```bash
# === STRUCTURE ===
tree -L 3 -I '.git|.venv|__pycache__|*.egg-info' --dirsfirst
find src/ -name "*.py" | xargs wc -l | sort -rn | head -20  # largest files

# === AGENTS & TOOLS ===
grep -rn "class.*Agent\|def invoke\|@register\|@tool" src/agents/ src/tools/
grep -rn "def " src/tools/ --include="*.py" | grep -v "_"   # public tool functions

# === PROMPTS ===
find prompts/ -type f | sort
grep -rn "load_prompt\|PromptTemplate\|system_v" src/ --include="*.py"

# === STATE / SCHEMAS ===
grep -rn "class.*Model\|class.*State\|TypedDict" src/state/ src/models/

# === MEMORY ===
grep -rn "embed\|vector\|retrieve\|similarity" src/memory/ --include="*.py"

# === CONFIG ===
cat pyproject.toml | grep -A5 "\[tool\."
cat .env.example

# === TESTS ===
pytest tests/ --collect-only -q   # list all tests
pytest tests/unit/ -k "tool"      # run tool-related tests only

# === QUALITY ===
ruff check src/ --statistics       # lint summary
mypy src/ --no-error-summary        # type errors only
```

***

## 10. Summary: What Separates Next-Gen from Legacy Repos

| Dimension | Legacy (pre-2024) | Next-Gen (2026) |
|-----------|------------------|-----------------|
| **Package management** | `pip` + `requirements.txt` + `setup.py` | `uv` + `pyproject.toml` only |
| **Linting/formatting** | `flake8` + `black` + `isort` separately | `ruff` handles all three |
| **Type safety** | Optional hints | `mypy --strict`, Pydantic everywhere |
| **Agent organization** | Monolithic `agent.py` | Role-split `agents/` directory |
| **Prompt management** | Hardcoded f-strings | Versioned `prompts/` Markdown files |
| **State passing** | Raw `dict` between functions | `Pydantic BaseModel` state schemas |
| **Tool discovery** | Hardcoded lists in agent | Central `tools/registry.py` |
| **Memory** | In-memory list | Tiered `memory/` (short/vector/persistent) |
| **Docstrings** | All-or-nothing | Selective Google-style on public API |
| **File LOC** | Unlimited | Soft cap ~300, hard cap ~500 per file |
| **Test organization** | Single `tests.py` | `unit/`, `integration/`, `e2e/` split |
| **CI/CD** | Manual or Jenkins | GitHub Actions in `.github/workflows/` |

---

## References

1. [Software Engineering Practices: In the era of AI / LLMs](https://al-kindipublisher.com/index.php/jcsts/article/view/11814) - The software development landscape is going through a major shift as generative artificial intellige...

2. [Y Combinator’s 2025 Spring batch reveals the future of agentic AI](https://cashmere.io/v/4415VEw0Y) - by CB Insights We analyze Y Combinator's Spring 2025 batch to uncover the top trends in agentic AI, ...

3. [Y Combinator’s 2025 Summer Batch reveals focus on production-ready AI](https://cashmere.io/v/vLQyCJHFx) - by CB Insights We analyze Y Combinator's Summer 2025 batch to uncover the top trends in agent infras...

4. [RepoReviewer: A Local-First Multi-Agent Architecture for Repository-Level Code Review](https://arxiv.org/abs/2603.16107) - Repository-level code review requires reasoning over project structure, repository context, and file...

5. [RepoGraph: Enhancing AI Software Engineering with Repository-level Code
  Graph](https://arxiv.org/html/2410.14684v1) - ...and developing effective solutions. On this basis, we
present RepoGraph, a plug-in module that ma...

6. [Alibaba LingmaAgent: Improving Automated Issue Resolution via
  Comprehensive Repository Exploration](http://arxiv.org/pdf/2406.01422.pdf) - ...comprehensively understand and utilize whole
software repositories for issue resolution. Deployed...

7. [The AI software development market map](https://cashmere.io/v/cfTm4fDal) - by CB Insights From coding agents to testing automation, we mapped 90+ AI startups redefining how so...

8. [Design and Implementation of an Online Python Teaching Case Library for the Training of Application-Oriented Talents](https://online-journals.org/index.php/i-jet/article/download/18191/8175) - ...paper develops and implements a complete online Python teaching case library. The teaching conten...

9. [MASAI: Modular Architecture for Software-engineering AI Agents](http://arxiv.org/pdf/2406.11638v1.pdf) - A common method to solve complex problems in software engineering, is to
divide the problem into mul...

10. [A Taxonomy of Architecture Options for Foundation Model-based Agents:
  Analysis and Decision Model](https://arxiv.org/pdf/2408.02920.pdf) - The rapid advancement of AI technology has led to widespread applications of
agent systems across va...

11. [TaskGen: A Task-Based, Memory-Infused Agentic Framework using StrictJSON](http://arxiv.org/pdf/2407.15734.pdf) - ...solve an
arbitrary task by breaking them down into subtasks. Each subtask is mapped to
an Equippe...

12. [ChatSpatial: Schema-Enforced Agentic Orchestration for Reproducible and Cross-Platform Spatial Transcriptomics](http://biorxiv.org/lookup/doi/10.64898/2026.02.26.708361) - Spatial transcriptomics analyses often require coordinating specialized Python and R methods. When a...

13. [PyPackIT: Automated Research Software Engineering for Scientific Python
  Applications on GitHub](http://arxiv.org/pdf/2503.04921.pdf) - ..., and
Reusable) and Open Science principles. PyPackIT is a user-friendly,
ready-to-use software t...

14. [PyGen: A Collaborative Human-AI Approach to Python Package Creation](http://arxiv.org/pdf/2411.08932.pdf) - ...documented our
results, analyzed the limitations, and suggested strategies to alleviate them.
Pyg...

15. [RepoAgent: An LLM-Powered Open-Source Framework for Repository-level
  Code Documentation Generation](https://arxiv.org/pdf/2402.16667.pdf) - ... code documentation. Through both qualitative and
quantitative evaluations, we have validated the...

16. [RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation](https://aclanthology.org/2023.emnlp-main.151.pdf) - ...settings and consistently outperforms the vanilla retrieval-augmented code completion approach. F...

17. [Assessing Python Style Guides: An Eye-Tracking Study with Novice
  Developers](https://arxiv.org/html/2408.14566) - ...style guides play an essential role in
software development, influencing code formatting, naming ...

18. [A Large-Scale Study of ML-Related Python Projects](https://dl.acm.org/doi/pdf/10.1145/3605098.3636056) - The rise of machine learning (ML) for solving current and future problems increased the production o...

19. [AI-Powered Software Engineering Automation System Using Multi-Agent Collaboration](https://ieeexplore.ieee.org/document/11582907/) - The rapid growth of Artificial Intelligence (AI) and Large Language Models (LLMs) has changed softwa...

