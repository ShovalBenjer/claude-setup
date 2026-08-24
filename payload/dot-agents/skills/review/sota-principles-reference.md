# SOTA Engineering Principles — Quick Reference for /review

## Severity Classification
- **BLOCK**: Security, broken tests, secrets, SQL injection, missing auth, scaffold in production
- **WARN**: Complexity >10, missing tests, perf concerns, a11y gaps, outdated deps
- **INFO**: Style, stack recommendations, minor improvements

## Hard Limits (All Projects)
- Cyclomatic complexity <10 per function (warn at 7)
- Cognitive complexity <15 per function
- Function <50 LOC, File <500 LOC
- Type coverage >90%
- No `any` (TS), no untyped functions (Python strict mypy)
- Zero dead code (ruff F401/F811/F841, knip)
- Zero secrets in code (gitleaks patterns)
- All SQL parameterized (zero interpolation)

## Stack Preferences (Best-in-Class)
| Prefer | Over | Domain |
|--------|------|--------|
| polars | pandas | Data (>100K rows) |
| httpx | requests | Async HTTP |
| pydantic v2 | dataclasses | Validation boundaries |
| ruff | flake8/isort/black | Python lint |
| uv | pip/poetry | Python packaging |
| bun | npm/yarn | JS runtime |
| esbuild/vite | webpack | JS bundling |
| vitest | jest | JS testing |
| pytest | unittest | Python testing |
| date-fns | moment.js | Date handling |
| fetch/ky | axios | Simple HTTP (JS) |

## Tool Matrix (CI Integration)
| Category | Python | JS/TS |
|----------|--------|-------|
| Lint | ruff | eslint + prettier |
| Type | mypy strict | tsc strict |
| Dead code | vulture, ruff F | knip |
| Security | bandit, semgrep, pip-audit | npm audit, semgrep |
| Secrets | gitleaks | gitleaks |
| Complexity | radon, ruff C901 | eslint-plugin-sonarjs |
| Test | pytest, hypothesis, mutmut | vitest, fast-check, stryker |
| A11y | -- | axe-core, eslint-plugin-jsx-a11y |
| Perf | py-spy, import-time | lighthouse CI, bundlewatch |
| Deps | pip-audit, deptry, pip-licenses | npm audit, knip, license-checker |
| Container | hadolint, trivy, dive | hadolint, trivy, dive |

## Per-Category Top Flags

### Architecture
- `import` from infra/ in domain/ code = layer violation
- Class hierarchy >2 levels deep = use composition
- if/elif >5 branches on same var = extract to lookup table
- Circular module dependencies

### Performance
- Loop containing DB/HTTP call = N+1 (BLOCK)
- `requests.get()` in async context (use httpx)
- `SELECT *` without LIMIT
- Frontend bundle >250KB gzipped initial
- `import pandas` at module level in Azure Functions (cold start)

### Accessibility (WCAG 2.2)
- `<div onClick>` without role="button" + tabIndex
- Color contrast <4.5:1
- `<img>` without alt
- Missing `<label>` for inputs
- No prefers-reduced-motion check on animations

### UI/UX
- Async operation without loading+error+success states
- Empty list renders blank (needs empty state)
- Form >7 fields without sections
- Button onClick without visual feedback
- `<img>` without width/height (CLS)

### Security (OWASP)
- f-string SQL (BLOCK)
- `dangerouslySetInnerHTML` (BLOCK)
- `allow_origins=["*"]` in CORS (BLOCK)
- Endpoint without auth check (BLOCK)
- Secret pattern in source (BLOCK)

### Data Engineering
- Pipeline without schema validation at ingestion
- INSERT without ON CONFLICT/upsert
- No row count logging (lineage)
- `requests.get()` without retry/backoff
- PII in log statements

### API Design
- Inconsistent error response shapes
- List endpoint without pagination
- POST without idempotency key support
- No /health endpoint
- No X-Request-ID propagation
