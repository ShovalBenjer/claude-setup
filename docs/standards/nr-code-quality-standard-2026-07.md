# Python Code Implementation Quality Standard — July 2026
**Control document for zero-runtime-dep Python package**
**Stack: uv · ruff · mypy --strict · pytest · tree-sitter (only external dep)**
**Last updated: 2026-07-12 | Agent-legible, primary-sourced**

---

## Table of Contents
1. [Q1 — Docstring Standard](#q1--docstring-standard)
2. [Q2 — Type + Interface Standard](#q2--type--interface-standard)
3. [Q3 — Error-Handling + Boundary Standard](#q3--error-handling--boundary-standard)
4. [Q4 — Simplicity / Complexity Standard](#q4--simplicity--complexity-standard)
5. [Q5 — Testing Standard](#q5--testing-standard)
6. [Q6 — Unified A-F Grading Rubric](#q6--unified-af-grading-rubric)
7. [Q7 — Stack-Specific Config + Tooling](#q7--stack-specific-config--tooling)

---

## Q1 — Docstring Standard

### Primary Sources
- **PEP 257** (Active, last revised 2024-04-16): https://peps.python.org/pep-0257/
- **Google Python Style Guide** (continuously updated, accessed 2026-07): https://google.github.io/styleguide/pyguide.html §3.8
- **NumPy docstring guide**: https://numpydoc.readthedocs.io/en/latest/format.html
- **pydoclint** (2026-05): https://jsh9.github.io/pydoclint/

**Chosen style for this stack: Google style** (single-indent sections, less verbose than NumPy, preferred for tighter code). Configure `pydoclint --style=google` and ruff `D` rules.

---

### Per-MODULE docstring

**Rule:** Every module file (`*.py`) MUST have a module-level docstring as its first statement.

**Required content (all four bullets non-negotiable):**

```python
"""<One-line imperative summary ending in a period.>

Purpose: WHY this module exists in the package (not just what it does).
Contracts: Key invariants the rest of the package may rely on.
Agent-context: Which tree-sitter node types or grammar contracts this
    module owns; which public symbols an agent should call vs avoid.

Typical usage::

    from mypackage.parser import NodeVisitor
    visitor = NodeVisitor(source=src)
    result = visitor.visit(tree.root_node)
"""
```

**PEP 257 rule:** "The docstring for a module should generally list the classes, exceptions and functions (and any other objects) that are exported by the module, with a one-line summary of each." (PEP 257, §Multi-line Docstrings)

**Google rule:** "Every file should contain license boilerplate. [...] Files used by other modules should be importable." The module docstring is the primary machine-readable description.

**AI-native convention (2025–2026):**
Write the `Agent-context` section so an LLM agent reading only the module docstring knows:
1. What this module does (purpose)
2. What it depends on (wiring: imports, tree-sitter grammars)
3. What invariants the caller can trust (contracts)
4. What NOT to call from outside (private boundaries)

Pattern from llms.txt/AGENTS.md community norms (2025–2026): keep it structured and parseable — agents respond better to labeled sections than prose paragraphs. Reference: Addy Osmani "My LLM coding workflow going into 2026" (2026-01-03) and IBM "Standardize AI code generation" (2026-05-21).

**⚠ Flag:** No formal PEP or official standard yet mandates the `Agent-context` section. This is an emerging convention drawn from practitioner sources, not a standards body.

---

### Per-CLASS docstring

**Rule:** Every public class REQUIRES a docstring. Private classes (`_Foo`) require one if they have public methods.

**Required content:**

```python
class NodeVisitor:
    """Visit tree-sitter nodes and extract structured data.

    Walks the CST produced by tree-sitter and yields typed records.
    Invariant: the input `Tree` must be from the same grammar version
    as the `Language` passed at construction.

    Attributes:
        language: The tree-sitter Language used for this visitor.
        errors: List of ParseError encountered during traversal.
    """
```

**Google rule (§3.8.4):** "Classes should have a docstring below the class definition describing the class. If your class has public attributes, they should be documented here in an Attributes section."

**When `Attributes:` section is MANDATORY:** whenever the class exposes any public instance attribute not obvious from `__init__` signature alone.

**When `Methods:` section is recommended:** complex classes with > 5 public methods that are not self-evident from names alone.

---

### Per-FUNCTION/METHOD docstring

**Conditional docstring rule (Google §3.8.3):**

> A function MUST have a docstring unless it meets **all three** of:
> 1. Not externally visible (prefixed `_`)
> 2. Very short (≤ 10 lines)
> 3. Obvious from name and signature alone

**Section mandate table:**

| Section | Mandatory when |
|---------|---------------|
| `Args:` | ≥ 1 non-obvious parameter, OR any parameter whose type annotation doesn't fully convey meaning |
| `Returns:` | Returns anything non-`None`; OMIT if function name starts with "Returns"/"Yields" and one-liner suffices |
| `Raises:` | ≥ 1 exception the CALLER must handle (do NOT document internal programming-error exceptions per Google rule) |
| `Examples:` | Public API functions, complex invariants, or any function an agent might call autonomously |
| `Side Effects:` | Function mutates non-local state, writes files, calls network, or modifies tree-sitter state |

**Full example (Google style):**

```python
def parse_function_def(node: Node, source: bytes) -> FunctionRecord:
    """Extract a typed function record from a tree-sitter function_definition node.

    Validates that `node.type == "function_definition"` before extracting.
    Side effect: none (pure function).

    Args:
        node: A tree-sitter Node with type "function_definition".
            Must belong to the Python grammar version ≥ 0.21.
        source: The raw UTF-8 source bytes the tree was parsed from.

    Returns:
        A FunctionRecord with name, args, return_annotation, and byte_range
        populated. `return_annotation` is None when unannotated.

    Raises:
        ValueError: If node.type is not "function_definition".
        UnicodeDecodeError: If source contains non-UTF-8 sequences.

    Examples:
        >>> node = parser.parse(b"def foo(x: int) -> str: ...").root_node
        >>> rec = parse_function_def(node.children[0], b"def foo(x: int) -> str: ...")
        >>> rec.name
        'foo'
    """
```

---

### Per-LINE inline comment

**The "why not what" rule (Google §3.8.5, PEP 8):**

✅ **Warranted:** Explains a non-obvious decision, a gotcha, a workaround, a known limitation, or intent that the code CANNOT convey.

```python
# tree-sitter byte offsets are inclusive on both ends (unlike Python slices)
text = source[node.start_byte : node.end_byte + 1]

# Walk parent chain instead of children: avoids O(n²) on deeply nested CSTs
while current := current.parent:
```

❌ **Comment-as-code-smell:**
```python
# Increment i  ← describes WHAT, not WHY
i += 1

# Check if list is empty  ← obvious from code
if not items:
```

**Rule:** Never write a comment that restates what the next line already says. An inline comment is justified only when a competent Python developer, reading the line cold, might make the WRONG assumption about why it was written that way.

---

### Tooling: Measure Docstring Coverage + Style

#### 1. ruff D rules (pydocstyle, built-in, primary enforcement)

Enable in `[tool.ruff.lint]`:

```toml
# Minimum viable D-rule set for this stack
select = [
  # ... other rules ...
  "D",        # pydocstyle — full suite
]
ignore = [
  "D100",     # DISABLE: missing docstring in public MODULE → enforce via interrogate instead
  "D104",     # DISABLE: missing docstring in public PACKAGE → same
  "D203",     # Conflicts with D211 (blank line before class docstring) — pick D211
  "D212",     # Conflicts with D213 (multi-line summary first line) — pick D213
  "D401",     # "First line should be in imperative mood" — overly pedantic for agents
]
```

**D-codes non-negotiable for this stack:**

| Code | Rule |
|------|------|
| D101 | Missing docstring in public class |
| D102 | Missing docstring in public method |
| D103 | Missing docstring in public function |
| D107 | Missing docstring in `__init__` |
| D200 | No whitespaces allowed surrounding docstring text |
| D205 | 1 blank line required between summary and description |
| D206 | Docstring should be indented with spaces |
| D300 | Use `"""triple double quotes"""` |
| D400 | First line should end with a period |
| D417 | Missing argument descriptions in the docstring |

#### 2. interrogate (coverage threshold enforcement)

```bash
# Install (dev only)
uv add --dev interrogate

# Run: enforce 100% public-symbol coverage
interrogate -v --fail-under 100 --ignore-init-module --ignore-magic src/

# In CI (non-zero exit on failure):
interrogate --fail-under 100 --quiet src/
```

`pyproject.toml` config:
```toml
[tool.interrogate]
ignore-init-method = false
ignore-init-module = true      # __init__.py modules covered by package docstring
ignore-magic = false
ignore-semiprivate = true      # _name methods
ignore-private = true          # __name methods (not __init__)
ignore-module = false
ignore-nested-functions = false
fail-under = 100
verbose = 0
quiet = false
whitelist-regex = []
color = true
generate-badge = "."
badge-format = "svg"
```

#### 3. pydoclint (Args/Returns/Raises match verification — replaces darglint)

**Note:** darglint is unmaintained as of 2023. Use `pydoclint` instead (actively maintained, 2026-05 release).

```bash
uv add --dev pydoclint

# Run
pydoclint --style=google --arg-type-hints-in-docstring=false src/

# As ruff plugin (via flake8 compat — optional for ruff-only stacks)
# pydoclint integrates natively via its CLI; run separately in CI
```

**A vs C vs F distinction (docstrings):**

| Grade | Observable criteria |
|-------|-------------------|
| A | 100% public symbols documented; all Args/Returns/Raises present and matching; module has Purpose + Contracts + Agent-context; no "what" comments |
| C | ≥ 80% symbols documented; Args present but Returns sometimes missing; no agent-context section; some "what" comments |
| F | < 60% coverage; bare `pass` docstrings; Args/Returns absent or wrong; inline comments restate code |

---

## Q2 — Type + Interface Standard

### Primary Sources
- **mypy strict docs**: https://mypy.readthedocs.io/en/stable/ (v2.2.0, 2026)
- **PEP 544** (Accepted 2022-03-21): https://peps.python.org/pep-0544/
- **mypy protocols**: https://mypy.readthedocs.io/en/stable/protocols.html
- **pydevtools mypy strict guide** (2026-06-23): https://pydevtools.com/handbook/how-to/how-to-configure-mypy-strict-mode/

---

### Full-annotation bar under mypy --strict

`mypy --strict` enables these flags (all non-negotiable for this stack):

```
--disallow-any-generics        No List, Dict without type params
--disallow-subclassing-any     No subclassing Any-typed classes
--disallow-untyped-calls       All called functions must be typed
--disallow-untyped-defs        All function defs must be annotated
--disallow-incomplete-defs     All params AND return must be annotated
--check-untyped-defs           Type-check even unannotated functions
--disallow-untyped-decorators  All decorators must be typed
--warn-redundant-casts         No redundant cast()
--warn-unused-ignores          No stale # type: ignore
--warn-return-any              Return type Any is explicit
--no-implicit-reexport         Symbols not in __all__ are not re-exported
--strict-equality              No trivially false comparisons
```

**The `Any` rule:** Never use `Any` as a lazy escape hatch. Permitted uses:
- Interoperating with tree-sitter C bindings (add `# type: ignore[import-untyped]` with a justification comment)
- Truly dynamic dispatch patterns where the type is unknowable at analysis time

**Banned patterns:**
```python
# BANNED: lazy DTO
def process(data: dict[str, Any]) -> None: ...

# BANNED: unannotated internal
def _helper(x):
    return x + 1

# BANNED: cast without reason
value = cast(int, node.start_byte)  # only if start_byte is already int
```

---

### Protocol vs ABC — the decision rule

| Use `Protocol` when | Use `ABC` when |
|--------------------|----------------|
| Structural typing is sufficient (duck typing) | You need shared implementation / template method |
| External types must satisfy the interface without modifying them | All implementors are in your own codebase |
| Agent calls require minimal coupling | You need `super()` calls or mixin behaviour |
| tree-sitter nodes or stdlib types must satisfy the interface | You want `isinstance()` checks at runtime without `@runtime_checkable` |

**PEP 544 guidance:** "Protocol classes can be used with structural subtyping. A class is compatible with a protocol if it has all the attributes and methods defined in the protocol with compatible types." No inheritance required.

```python
# PREFERRED for this stack (Protocol — structural, loose coupling)
from typing import Protocol

class NodeExtractor(Protocol):
    """Extract typed data from a tree-sitter node."""
    def extract(self, node: Node, source: bytes) -> dict[str, object]: ...

# Use ABC only when sharing implementation:
from abc import ABC, abstractmethod

class BaseVisitor(ABC):
    """Shared walk logic for all tree-sitter visitors."""
    def walk(self, node: Node) -> None:
        self._visit(node)
        for child in node.children:
            self.walk(child)

    @abstractmethod
    def _visit(self, node: Node) -> None: ...
```

---

### Typed DTO at boundaries rule

**Rule:** Promote `dict[str, Any]` to a typed struct at ANY system boundary:
- Function accepting external / parsed input
- Function returning data to a caller outside this module
- Any inter-module data record that travels > 1 call frame

**Decision tree:**
1. Pure internal, single call-site, ≤ 3 fields → `@dataclass(frozen=True)` (stdlib, zero deps)
2. Validation + coercion needed at boundary → `pydantic.BaseModel` (runtime dep — excluded from this stack; use only in tests or harness layer)
3. High-throughput serialisation + zero alloc → `msgspec.Struct` (runtime dep — excluded from this stack)
4. **For this zero-dep stack:** use `@dataclass(frozen=True)` + mypy strict for ALL inter-module records

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FunctionRecord:
    """Typed record extracted from a function_definition node."""
    name: str
    start_byte: int
    end_byte: int
    return_annotation: str | None
    is_async: bool
```

**A vs C vs F distinction (types):**

| Grade | Observable criteria |
|-------|-------------------|
| A | Zero mypy errors under `--strict`; no `Any` without comment; all inter-module records are typed dataclasses; Protocols for all structural interfaces |
| C | mypy errors ≤ 5 (in `# type: ignore` without justification); `dict[str, Any]` crossing ≥ 1 module boundary; some unannotated internal helpers |
| F | mypy fails under `--check-untyped-defs`; bare `dict` or `Any` as public API return types; no annotations on public functions |

---

## Q3 — Error-Handling + Boundary Standard

### Primary Sources
- **Google Python Style Guide §2.4** (Exceptions): https://google.github.io/styleguide/pyguide.html
- **Real Python exception best practices**: https://realpython.com/ref/best-practices/exception-handling/ (accessed 2026)
- **Miguel Grinberg "Ultimate Guide to Error Handling"** (2024-10-06): https://blog.miguelgrinberg.com/post/the-ultimate-guide-to-error-handling-in-python
- **PEP 8 §Error Handling**: https://peps.python.org/pep-0008/

---

### The five canonical boundary tests

Every function that touches an external resource (file, tree-sitter grammar, subprocess, config) MUST be testable against:

| Test # | Scenario | Expected behaviour |
|--------|----------|-------------------|
| 1 | Valid input | Returns correct typed result |
| 2 | Invalid input (wrong type / value) | Raises `ValueError` with message naming the bad field |
| 3 | Missing config / env var | Raises `RuntimeError` or domain-specific `ConfigError` at startup, NOT at first use |
| 4 | Missing resource (file, grammar, node type) | Raises specific `FileNotFoundError` / `LookupError` with path/name |
| 5 | Timeout / resource exhaustion | Either raises `TimeoutError` or fails-closed (logs + re-raises) |

---

### Fail-closed rule

**Rule:** At every boundary, fail loudly and explicitly. "Best-effort" is only permitted when:
1. The caller has explicitly opted into degraded mode
2. The failure is logged at `WARNING` level or above with full context
3. The fallback behaviour is documented in the function docstring

```python
# CORRECT: fail-closed
def load_grammar(path: Path) -> Language:
    """Load a tree-sitter grammar from a compiled .so/.dylib file.

    Raises:
        FileNotFoundError: If path does not exist.
        RuntimeError: If the grammar cannot be loaded (wrong arch, corrupt file).
    """
    if not path.exists():
        raise FileNotFoundError(f"Grammar not found: {path}")
    try:
        return Language(str(path), "python")
    except Exception as exc:
        raise RuntimeError(f"Failed to load grammar at {path}: {exc}") from exc

# WRONG: silent failure
def load_grammar(path: Path) -> Language | None:
    try:
        return Language(str(path), "python")
    except Exception:
        return None  # BANNED: caller cannot know if this is a real absence
```

---

### No-bare-except rule

**Google §2.4.4:** "Never use catch-all `except:` statements, or catch `Exception` or `StandardError`, unless you are re-raising the exception, or creating an isolation point."

**Per-line checklist for reviewers:**

```
□ No bare `except:` (ruff E722 catches this)
□ No `except Exception:` without (a) re-raise or (b) explicit log + documented isolation point
□ No `pass` inside except block (ruff S110)
□ Every caught exception uses `as exc` and either re-raises or logs with exc info
□ `finally` block used for cleanup (never for flow control)
□ Custom exception classes inherit from `Exception`, named `*Error`
□ Error message names the CALLER's abstraction ("grammar path" not "path variable")
□ Exception chains preserved: `raise FooError("msg") from original_exc`
□ try-block is as narrow as possible (minimum lines inside try)
```

**Typed error hierarchy for this stack:**

```python
class HarnessError(Exception):
    """Base for all harness-layer errors."""

class GrammarError(HarnessError):
    """Tree-sitter grammar load or parse failure."""

class AnalysisError(HarnessError):
    """Code analysis logic failure (not a grammar issue)."""

class ConfigError(HarnessError):
    """Missing or invalid configuration."""
```

**A vs C vs F distinction (error handling):**

| Grade | Observable criteria |
|-------|-------------------|
| A | No bare except; all exceptions typed and chained; boundary tests 1-5 present; custom error hierarchy; no silently-swallowed exceptions |
| C | Specific exceptions caught but not chained (`from exc` missing); ≤ 2 `except Exception` with log but no re-raise; missing 1–2 boundary tests |
| F | Bare `except:` present; `except Exception: pass` present; errors silently return `None`; no custom error types; no boundary tests |

---

## Q4 — Simplicity / Complexity Standard

### Primary Sources
- **Radon docs** (cyclomatic complexity): https://radon.readthedocs.io/en/latest/intro.html
- **ruff C901 rule** (McCabe complexity): https://docs.astral.sh/ruff/rules/complex-structure/
- **Sourcegraph "Cyclomatic complexity"** (2025-11-11)
- **DX "Cognitive complexity"** (2025-11-25): https://getdx.com/blog/cognitive-complexity/
- **codeant.ai "7 Axes of Code Quality"** (2024-10-07)
- **Google Style Guide §functions** (function length limit)

---

### Numeric thresholds

| Metric | Green (no action) | Yellow (review) | Red (refactor) |
|--------|------------------|-----------------|---------------|
| Cyclomatic complexity (radon CC / ruff C901) | 1–5 | 6–10 | > 10 |
| Cognitive complexity | < 10 | 10–15 | > 15 |
| Function length (lines) | ≤ 20 | 21–40 | > 40 |
| Parameter count | ≤ 4 | 5–6 | > 6 |
| Nesting depth | ≤ 3 | 4 | > 4 |
| Module lines (excl. docstrings) | ≤ 300 | 301–500 | > 500 |

**Radon CC grades (canonical):** A(1-5), B(6-10), C(11-15), D(16-20), E(21-25), F(>25). **Target: median A, no function below B.**

**Google Style Guide §functions:** "Prefer functions ≤ 40 lines. Recognize no hard limit, but long functions are a signal to extract." In practice, for agent-legible code, 20 lines is the practical target.

---

### Tool commands

```bash
# McCabe complexity via radon
uv add --dev radon
radon cc src/ -s -a -n B    # show all functions grade B and below (≥ complexity 6)
radon mi src/ -s            # maintainability index

# ruff C901 (built-in, use in CI)
# In pyproject.toml: [tool.ruff.lint.mccabe] max-complexity = 10
ruff check --select C901 src/

# Cognitive complexity via complexipy
uv add --dev complexipy
complexipy src/ --max-complexity 15

# Dead code via vulture
uv add --dev vulture
vulture src/ --min-confidence 80

# Vulture whitelist for intentional public API
# Create whitelist.py: contains items that look unused but are exported
vulture src/ whitelist.py --min-confidence 80
```

---

### Dead code and speculative abstraction

**vulture** flags:
- Unused imports
- Unused functions / methods
- Unused variables / parameters
- Unreachable code

**Speculative abstraction smells (manual review):**
- A class with exactly one concrete subclass (→ likely YAGNI)
- A `BaseXxx` with no shared implementation (→ use Protocol instead)
- A factory function with one code path (→ just call the constructor)
- A parameter that is always passed the same value at every call site

**A vs C vs F distinction (simplicity):**

| Grade | Observable criteria |
|-------|-------------------|
| A | Radon median A; no function > complexity 10; no nesting > 3; no dead code (vulture clean); 0 speculative abstractions; all params ≤ 4 |
| C | Radon median B; ≤ 2 functions > complexity 10; some nested ifs > 3 levels; vulture finds ≤ 3 unused symbols; 1–2 single-impl base classes |
| F | Any function > complexity 15; nesting > 4; modules > 500 lines; vulture finds > 5 unused symbols; `dict[str, Any]` god-objects |

---

## Q5 — Testing Standard

### Primary Sources
- **pytest docs**: https://docs.pytest.org/
- **Hypothesis (property-based testing)**: https://hypothesis.readthedocs.io/ — "In Praise of Property-Based Testing" (Increment, 2021-11-18); empirical study (OOPSLA 2025)
- **mutmut docs**: https://mutmut.readthedocs.io/
- **CircleCI "What is mutation testing?"** (2026-06-24): https://circleci.com/blog/what-is-mutation-testing/
- **QASkills mutmut guide** (2026-07-09): https://qaskills.sh/blog/mutmut-python-mutation-testing-guide
- **NSF/Diallo "Analysis of Mutation Testing Tools for Python"** (2024, cited ×3)

---

### No-mocks-for-business-logic

**Rule:** Mock only I/O and time-based operations. Never mock the function under test's immediate collaborators in the same module.

```python
# CORRECT: test tree-sitter parsing with real bytes
def test_parse_function_def_extracts_name() -> None:
    src = b"def hello(x: int) -> str: ..."
    parser = get_python_parser()
    tree = parser.parse(src)
    record = parse_function_def(tree.root_node.children[0], src)
    assert record.name == "hello"

# WRONG: mocking the parser defeats the test
def test_parse_function_def_bad() -> None:
    mock_node = MagicMock()
    mock_node.type = "function_definition"
    # This test proves nothing about real tree-sitter integration
```

**Recorded fixtures for external resources:** if a tree-sitter grammar version changes, fixtures capture the known-good AST snapshot. Use `pytest-recording` or simple JSON/pickle fixtures.

---

### Property-based testing with Hypothesis

**Mandatory when invariants exist:**
- Round-trip encode/decode (serialize → deserialize → original)
- Sorting/ordering invariants (length preserved, elements same)
- Idempotency (applying twice = applying once)
- Range invariants (byte offsets always within source length)

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(st.binary(min_size=1, max_size=4096))
@settings(max_examples=500)
def test_parser_never_crashes_on_arbitrary_bytes(source: bytes) -> None:
    """Parser must not raise on any byte input — at worst return error nodes."""
    parser = get_python_parser()
    tree = parser.parse(source)
    # tree-sitter guarantees a tree is always returned; root_node must exist
    assert tree.root_node is not None
```

---

### Mutation testing (mutmut)

**Threshold targets (per CircleCI 2026 and IBM 2025 guidance):**
- New modules: **≥ 80% mutation score** before merge
- Existing core modules: **≥ 70% mutation score** in CI gate
- "Don't chase 100%": equivalent mutants and trivial mutations inflate the denominator

```bash
uv add --dev mutmut

# Run mutation testing scoped to changed files (fast CI mode)
mutmut run --paths-to-mutate src/ --runner "python -m pytest"

# View surviving mutants
mutmut results

# HTML report
mutmut html

# CI gate: exit non-zero if score < threshold
mutmut run --CI  # exits 1 if any mutants survived
```

`pyproject.toml`:
```toml
[tool.mutmut]
paths_to_mutate = "src/"
backup = false
runner = "python -m pytest -x -q"
tests_dir = "tests/"
```

---

### Coverage thresholds

- **Whole-repo line coverage:** ≥ 90% (enforced via `--cov-fail-under=90`)
- **Diff coverage (per PR):** ≥ 80% of changed lines covered (enforced via `pytest-cov` + diff-cover)
- **Mutation score:** ≥ 70% on core modules

```bash
# Coverage
uv add --dev pytest-cov
pytest --cov=src --cov-report=xml --cov-fail-under=90

# Diff coverage (changed lines only)
uv add --dev diff-cover
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

---

### TDD discipline (RED before GREEN)

**Rule:** Each behaviour gets a failing test before implementation code is written.

**Per-behaviour TDD, NOT all-tests-then-all-code:**
```
RED:   write test for exactly one behaviour → confirm it fails
GREEN: write minimum code to pass → confirm only this test passes
REFACTOR: simplify without breaking any test
COMMIT: one behaviour per commit
```

**A vs C vs F distinction (testing):**

| Grade | Observable criteria |
|-------|-------------------|
| A | ≥ 90% line coverage; ≥ 70% mutation score; Hypothesis for all invariants; 0 business-logic mocks; five boundary tests present; RED-GREEN-REFACTOR commits |
| C | 70–89% coverage; mutation testing not run; ≥ 1 Hypothesis test for main invariants; some mocks of collaborators; boundary tests incomplete |
| F | < 70% coverage; no mutation testing; no property tests; mocks everywhere including business logic; tests written after code; no boundary tests |

---

## Q6 — Unified A-F Grading Rubric

### How to apply this rubric

Apply per source file. For each dimension, select the grade band by checking OBSERVABLE criteria only — no subjective judgement. Tool commands are listed under each dimension. Two reviewers applying this rubric to the same file should arrive at the same grade within ±1 band.

---

### Rubric table

| Dimension | A | B | C | D | F | Measuring tool |
|-----------|---|---|---|---|---|----------------|
| **Docstrings** | 100% public symbols; all sections present/matching; module has Purpose+Contracts+Agent-context | 95%+ coverage; minor missing Examples | 80%+ coverage; Args present, Returns sometimes absent | 60–79%; bare docstrings ("TODO") | <60% or wrong Args/Returns | `interrogate --fail-under 100` + `pydoclint` |
| **Types** | Zero mypy --strict errors; no `Any` w/o comment; all boundaries use typed DTOs | ≤2 `# type: ignore` with justification | ≤5 type errors; no `Any` as return type; `dict[str,Any]` only internally | Mypy passes only without strict; `Any` at boundaries | Mypy fails on basic checks; unannotated public API | `mypy --strict src/` |
| **Error handling** | No bare except; typed errors; all 5 boundary tests; exception chains; fail-closed | ≤1 `except Exception` with re-raise | ≤2 `except Exception` with log; some chains missing | Bare `except` present; some silent None returns | Bare `except: pass`; exceptions swallowed; no custom types | `ruff --select E722,S110`; manual boundary test audit |
| **Correctness** | All boundary tests pass; Hypothesis finds no violations; mutation score ≥80% | Mutation score 70–79%; all example tests pass | Mutation score 60–69%; some edge cases uncovered | Mutation score 50–59%; known edge-case failures | Mutation score <50% OR failing tests | `mutmut run` + `pytest` |
| **Simplicity** | Radon CC all A/B; no function>10 CC; no nesting>3; vulture clean; params≤4 | ≤1 CC-B function; vulture ≤1 unused | Radon CC median B; ≤2 functions>10 CC; ≤3 vulture hits | ≥3 functions>10 CC; nesting>4 in places; 4–6 vulture hits | Any CC>15; nesting>5; >6 vulture hits; god-objects | `radon cc -n B src/`; `vulture src/`; `ruff --select C901` |
| **Testing** | ≥90% coverage; ≥70% mutation; Hypothesis for invariants; 0 biz-logic mocks | 85–89% coverage; 65–70% mutation | 70–84% coverage; no mutation run; some Hypothesis | 60–69% coverage; no property tests; many mocks | <60% coverage; no mutation; pure mock-based | `pytest --cov-fail-under=90`; `mutmut run` |

---

### Per-function checklist (human or agent applies mechanically)

```
FUNCTION: ______________________

Docstring
□ First line: one-sentence imperative, ends with period
□ Args: section present for all non-obvious params
□ Returns: section present (or function returns None)
□ Raises: section present for all caller-visible exceptions
□ Side Effects: noted if function mutates non-local state

Types
□ All parameters annotated (no bare names)
□ Return type annotated
□ No `Any` without # type: ignore[...] comment
□ No `dict[str, Any]` as parameter type

Error handling
□ No bare `except:` (use specific exception types)
□ Every `except` either re-raises or logs with exc_info=True
□ No `pass` in except block
□ Exceptions chained with `from exc`
□ Error messages identify the failing CALLER abstraction

Complexity
□ CC ≤ 10 (run: radon cc -s <file>)
□ Nesting depth ≤ 3
□ Parameter count ≤ 4 (or documented justification)
□ Lines ≤ 40

Testing
□ At least 1 happy-path test exists
□ At least 1 invalid-input test exists
□ Hypothesis test if function has invariants
□ No mocks of direct collaborators in same module
```

---

### Per-line checklist (reviewer applies to every non-trivial line)

```
LINE: ______________________

□ Is there an inline comment?
  → If yes: does it explain WHY (not what)? If it restates code → DELETE
  → If code is non-obvious without comment → ADD one

□ Does the line use `except` without a type?
  → Flag: bare except (E722)

□ Does the line assign a variable of type `Any` or `dict[str, Any]`?
  → Flag: promote to typed struct

□ Is there a magic number literal?
  → Extract to named constant with comment explaining its origin

□ Does the line swallow an exception (empty except body or bare return None after except)?
  → Flag: fail-closed violation

□ Is there a TODO/FIXME/HACK comment?
  → Must have: owner, ticket reference, deadline. Undated TODOs are F-grade.
```

---

## Q7 — Stack-Specific Config + Tooling

### Non-negotiable vs nice-to-have

| Item | Verdict | Reason |
|------|---------|--------|
| mypy --strict | **Non-negotiable** | Zero-dep stdlib package; type errors are CI failures |
| ruff D (docstring) | **Non-negotiable** | Agent-legible code requires 100% coverage |
| ruff C901 (complexity) | **Non-negotiable** | CC > 10 is unacceptable for agent traversal |
| ruff E/F/B/I | **Non-negotiable** | Basic correctness + import hygiene |
| interrogate | **Non-negotiable** | Coverage threshold enforcement (ruff D does not count; only checks format) |
| pydoclint | **Non-negotiable** | Args/Returns match verification (darglint unmaintained) |
| pytest + pytest-cov | **Non-negotiable** | Coverage gate |
| hypothesis | **Non-negotiable** | tree-sitter parsing has round-trip + crash invariants |
| vulture | **Strongly recommended** | Dead code in a single-operator harness is a liability |
| radon | **Nice-to-have** | C901 duplicates much of it; radon adds MI and Halstead |
| mutmut | **Nice-to-have for v1; non-negotiable for v2** | Expensive to run; add once coverage baseline is ≥ 90% |
| diff-cover | **Nice-to-have** | Per-PR coverage is a nicer DX than whole-repo gate |

**Zero-runtime-dep rule compliance:** All tools above are dev dependencies only (`uv add --dev`). None are imported at runtime. tree-sitter remains the sole runtime external dep.

---

### Complete `pyproject.toml` config block

```toml
# ──────────────────────────────────────────────────────────────
# pyproject.toml — dev tooling + quality enforcement
# Stack: uv · ruff · mypy --strict · pytest · tree-sitter only
# Standard version: 2026-07-12
# ──────────────────────────────────────────────────────────────

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-harness"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "tree-sitter>=0.23",
]

[project.optional-dependencies]
dev = [
    "mypy>=1.11",
    "ruff>=0.5",
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "hypothesis>=6.112",
    "interrogate>=1.7",
    "pydoclint>=0.5",
    "vulture>=2.11",
    "radon>=6.0",
    "mutmut>=3.0",
    "diff-cover>=9.0",
]

# ── ruff ──────────────────────────────────────────────────────
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",        # pycodestyle errors
    "W",        # pycodestyle warnings
    "F",        # pyflakes
    "I",        # isort
    "B",        # flake8-bugbear
    "C4",       # flake8-comprehensions
    "C9",       # mccabe complexity (C901)
    "UP",       # pyupgrade
    "D",        # pydocstyle (docstrings)
    "ANN",      # flake8-annotations (type hints)
    "S",        # flake8-bandit (security)
    "SIM",      # flake8-simplify
    "RUF",      # ruff-specific rules
    "ERA",      # eradicate (commented-out code)
    "PT",       # flake8-pytest-style
    "T20",      # flake8-print (no stray print statements)
    "N",        # pep8-naming
    "PERF",     # perflint
]
ignore = [
    # Docstring style conflicts — pick one convention
    "D203",     # no-blank-line-before-class  (conflicts with D211)
    "D212",     # multi-line-summary-first-line (conflicts with D213)
    # Agent-legible code: imperative mood is enforced selectively
    "D401",     # first-line-imperative-mood — can conflict with descriptive modules
    # ANN rules: mypy --strict already handles these more precisely
    "ANN101",   # missing-type-self
    "ANN102",   # missing-type-cls
    "ANN401",   # any-type — allow Any at tree-sitter interop points with justification
]

[tool.ruff.lint.mccabe]
max-complexity = 10      # C901 threshold: complexity > 10 is an error

[tool.ruff.lint.pydocstyle]
convention = "google"    # Enforce Google-style docstrings

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "D",        # Tests don't require full docstring coverage
    "S101",     # assert is fine in tests
    "ANN",      # Test functions don't require full annotation
]
"src/**/__init__.py" = [
    "D104",     # Missing docstring in public package — covered by interrogate separately
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

# ── mypy ──────────────────────────────────────────────────────
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
show_error_codes = true
pretty = true
# tree-sitter: C extension, no type stubs available
[[tool.mypy.overrides]]
module = ["tree_sitter", "tree_sitter.*"]
ignore_missing_imports = true

# ── pytest ─────────────────────────────────────────────────────
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--cov=src",
    "--cov-report=xml",
    "--cov-report=term-missing",
    "--cov-fail-under=90",
]
markers = [
    "integration: tests requiring real tree-sitter grammar",
    "slow: tests running > 1s",
]

# ── interrogate ────────────────────────────────────────────────
[tool.interrogate]
ignore-init-method = false
ignore-init-module = true
ignore-magic = false
ignore-semiprivate = true
ignore-private = true
ignore-module = false
ignore-nested-functions = false
fail-under = 100
verbose = 0
color = true

# ── vulture ────────────────────────────────────────────────────
[tool.vulture]
min_confidence = 80
paths = ["src", "whitelist.py"]

# ── mutmut ─────────────────────────────────────────────────────
[tool.mutmut]
paths_to_mutate = "src/"
backup = false
runner = "python -m pytest -x -q"
tests_dir = "tests/"
```

---

### CI command sequence

```bash
# ── Format check (no writes in CI)
uv run ruff format --check src/ tests/

# ── Lint
uv run ruff check src/ tests/

# ── Type check
uv run mypy --strict src/

# ── Docstring coverage (100% public symbols)
uv run interrogate --fail-under 100 --quiet src/

# ── Docstring section validation (Args/Returns match)
uv run pydoclint --style=google src/

# ── Dead code
uv run vulture src/ whitelist.py --min-confidence 80

# ── Complexity report (informational; C901 is CI-blocking via ruff)
uv run radon cc src/ -s -a -n B

# ── Tests + coverage
uv run pytest

# ── Diff coverage (PR gate; requires coverage.xml from above)
uv run diff-cover coverage.xml --compare-branch=main --fail-under=80

# ── Mutation testing (run weekly or before releases, not on every commit)
uv run mutmut run --paths-to-mutate src/
uv run mutmut results
```

---

## Appendix: Source Verification Status

| Claim | Source | Status |
|-------|--------|--------|
| PEP 257 module/function docstring requirements | peps.python.org/pep-0257/ (Active) | ✅ Primary |
| Google Style Guide §3.8 (docstrings) | google.github.io/styleguide/pyguide.html | ✅ Primary |
| NumPy docstring sections | numpydoc.readthedocs.io | ✅ Primary |
| mypy --strict flags | mypy.readthedocs.io v2.2.0 | ✅ Primary |
| PEP 544 (Protocol) | peps.python.org/pep-0544/ | ✅ Primary |
| ruff D/C901/ANN rules | docs.astral.sh/ruff/rules/ | ✅ Primary |
| Radon CC grades (A–F) | radon.readthedocs.io | ✅ Primary |
| cognitive complexity thresholds (< 15 good) | getdx.com (2025), sourcegraph.com (2025) | ✅ Practitioner |
| mutation score target 70–80% | circleci.com (2026), IBM issue #280 (2025) | ✅ Practitioner |
| AI-native "Agent-context" docstring convention | Addy Osmani (2026), IBM (2026) | ⚠️ Emerging — no PEP/standard body |
| darglint deprecated → use pydoclint | linuxlinks.com (2026), pypi pydoclint (2026) | ✅ Verified |
| Google function length ≤ 40 lines | google.github.io/styleguide/pyguide.html | ✅ Primary |
| Parameter count ≤ 4–6 | codeant.ai axes (2024), DX cognitive (2025) | ✅ Practitioner consensus |
| interrogate --fail-under 100 | interrogate.readthedocs.io | ✅ Primary |
