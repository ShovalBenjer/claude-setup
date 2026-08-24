# Mutation Testing Runner

**Purpose:** Measure test suite strength by introducing code mutations and checking if tests catch them.

**When to Use:**
- Before releasing new versions
- After major refactoring
- To find weak test coverage areas

**Commands:**

## JavaScript/TypeScript (Stryker)
```bash
# Install Stryker (one-time)
bun add -D @stryker-mutator/core @stryker-mutator/vitest-runner

# Run mutation testing
bunx stryker run

# Check mutation score (target: >80%)
cat reports/mutation/mutation.html
```

## Python (mutmut)
```bash
# Install mutmut (one-time)
uv pip install mutmut

# Run mutation testing
uv run mutmut run

# Show results
uv run mutmut results
```

**Interpreting Results:**
- **Mutation Score >80%**: Strong test suite ✅
- **Mutation Score <80%**: Weak tests, add more test cases ❌
- **Survived mutants**: Code mutations that didn't break tests (need more tests)

**Safety:**
- Only runs on test files, never modifies source permanently
- Creates temporary mutated versions to test
- Original code unchanged after run

**Official Reference:** [Stryker Mutator Docs](https://stryker-mutator.io/)
