# el-vadt - Development Rules

**Project:** el-vadt
**Type:** AI/Sales Agents + Conversation Analysis
**Last Updated:** 2026-02-18

---

## Development Standards

### Code Quality
- **Language:** [Python | TypeScript | JavaScript | Mixed]
- **Linter:** [ruff | eslint | both]
- **Formatter:** [black | prettier]
- **Type Checking:** [mypy | tsc | both]
- **Target:** [Coverage threshold]%

### Testing
- **Framework:** [pytest | vitest | playwright | other]
- **Coverage Minimum:** [X]%
- **Test Structure:** [unit | integration | e2e]
- **CI/CD:** [GitHub Actions | other]

### Tooling Standards
- **Package Manager:** [uv for Python | bun for Node | both]
- **Build Tool:** [esbuild | webpack | other]
- **Runtime:** [Python 3.x | Node 18.x | other]

### Pre-Commit Hooks
- ✅ Clutter prevention (no root images, .env, caches)
- ✅ [Project-specific hook 1]
- ✅ [Project-specific hook 2]

---

## Git Workflow

### Commit Messages
**Format:** Conventional Commits
```
<type>(<scope>): <subject>

<body (optional)>

<footer (optional)>
```

**Types:** feat, fix, docs, style, refactor, perf, test, chore, ci

**Example:**
```
feat(auth): add JWT token validation

Implement JWT token validation in auth middleware.
Add token refresh endpoint and error handling.

Fixes #123
```

### Branch Naming
- Feature: `feature/[description]`
- Bug fix: `fix/[description]`
- Refactor: `refactor/[description]`
- Docs: `docs/[description]`

### PR Requirements
- [ ] Title describes change (feat/fix/docs)
- [ ] Description explains why (not just what)
- [ ] Tests added or updated
- [ ] Coverage >90% (or project target)
- [ ] Linter passes (no warnings)
- [ ] Type checking passes
- [ ] Pre-commit hook passes

---

## Quality Gates

### Before Merging

1. **Code Quality**
   - [ ] Linter: 0 errors
   - [ ] Type check: 0 errors
   - [ ] Format: Consistent with standard

2. **Testing**
   - [ ] Unit tests: >90% coverage (or [X]%)
   - [ ] All tests passing
   - [ ] New tests added for changes

3. **Documentation**
   - [ ] README updated (if applicable)
   - [ ] Code comments added (if complex)
   - [ ] CLAUDE.md updated (if architectural)

4. **Performance**
   - [ ] [Project-specific metric] meets SLA
   - [ ] No regressions detected
   - [ ] Load test passed (if applicable)

5. **Security**
   - [ ] No secrets in code
   - [ ] Input validation added
   - [ ] Security scan passed

---

## Development Workflow (TDD)

### 1. RED Phase
Write failing test first:
```bash
npm run test   # Should FAIL
# or
pytest         # Should FAIL
```

### 2. GREEN Phase
Write minimal code to pass:
```bash
npm run test   # Should PASS
# or
pytest         # Should PASS
```

### 3. REFACTOR Phase
Improve code quality:
```bash
npm run lint     # Fix any issues
npm run format   # Apply formatting
npm run test     # Should still PASS
```

### 4. Commit
```bash
git add [files]
git commit -m "feat(scope): description"
git push
```

---

## Performance Targets

| Metric | Target | SLA |
|--------|--------|-----|
| [Metric 1] | [Value] | [SLA] |
| [Metric 2] | [Value] | [SLA] |
| API Response | <[X]ms P95 | Production |
| Test Suite | <[X]min full | CI/CD |
| Build Time | <[X]min | CI/CD |

---

## Deployment Standards

### Prerequisites
- [ ] All tests passing (>90% coverage)
- [ ] Linter passing (0 warnings)
- [ ] Type checking passing
- [ ] Security scan passing
- [ ] Manual QA signed off

### Deployment Checklist
- [ ] Environment prepared
- [ ] Database migrations tested
- [ ] Configuration validated
- [ ] Secrets rotated (if needed)
- [ ] Rollback plan documented

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Check metrics dashboards
- [ ] Verify SLAs are met
- [ ] User communication sent

---

## Architecture Decisions

### Technology Stack
- **Backend:** [Framework | Runtime]
- **Frontend:** [Framework | Runtime]
- **Database:** [Database system]
- **API:** [REST | GraphQL | Other]
- **Auth:** [Method]
- **Hosting:** [Platform]

### Design Patterns
- **Codebase:** [Architecture: Clean | Layered | Other]
- **Testing:** [Approach: Unit | Integration | E2E | All]
- **State Management:** [Method]
- **Error Handling:** [Strategy]

### Known Constraints
- [Constraint 1]: [Details]
- [Constraint 2]: [Details]

---

## Tooling Commands

### Development
```bash
# Setup
[setup-command]

# Run in dev mode
[dev-command]

# Run specific component
[component-specific-command]
```

### Testing
```bash
# Run all tests
[test-all-command]

# Run unit tests only
[test-unit-command]

# Run with coverage
[test-coverage-command]

# Run specific test
[test-specific-command]
```

### Code Quality
```bash
# Lint
[lint-command]

# Format
[format-command]

# Type check
[type-check-command]

# All checks
[all-checks-command]
```

### Building
```bash
# Build
[build-command]

# Build for production
[build-prod-command]

# Clean build
[clean-build-command]
```

---

## Debugging Tips

### Debug Mode
```bash
[project-specific-debug-instructions]
```

### Common Issues
1. **[Issue 1]**
   - Symptom: [Description]
   - Root cause: [Why]
   - Fix: [Steps to fix]

2. **[Issue 2]**
   - Symptom: [Description]
   - Root cause: [Why]
   - Fix: [Steps to fix]

---

## Documentation Standards

### README.md
- Project purpose
- Quick start (3 min)
- Architecture diagram (optional)
- Setup instructions
- Running the project
- Testing
- Contributing guidelines
- License

### Code Comments
- Complex logic: Explain WHY not WHAT
- Public APIs: Document parameters & returns
- Gotchas: Note edge cases
- References: Link to specs/issues

### Commit Messages
- 50 char title max
- Blank line after title
- Explain WHY, not WHAT
- Reference issues/PRs
- Use present tense ("add" not "added")

---

## Team Guidelines

### Code Review
- [ ] Review within 24 hours
- [ ] Be constructive and kind
- [ ] Ask questions, don't demand
- [ ] Approve when satisfied

### Communication
- [ ] Update MEMORY.md after each session
- [ ] Notify team of major changes
- [ ] Ask for help when stuck
- [ ] Share learnings and patterns

### Collaboration
- [ ] No force pushes to main
- [ ] Rebase before merging (or merge commits if preferred)
- [ ] Keep branches short-lived (< 1 week)
- [ ] Run full test suite before pushing

---

## Security Guidelines

### Secrets Management
- ✅ Use `.env` files (local only, in .gitignore)
- ✅ Use environment variables in CI/CD
- ❌ Never commit secrets
- ❌ Never log secrets
- ❌ Never share in commits

### Input Validation
- ✅ Validate all user input
- ✅ Use strict type checking
- ✅ Sanitize HTML/URLs
- ❌ Trust user data
- ❌ Skip validation for "internal" APIs

### Data Protection
- ✅ Hash passwords (bcrypt, argon2, etc.)
- ✅ Encrypt sensitive data
- ✅ Log security events
- ❌ Store plaintext secrets
- ❌ Log sensitive data

---

## FAQ

**Q: What should I do if I'm blocked?**
A: Update MEMORY.md with blocker details and ask team

**Q: When should I write tests?**
A: Before implementation (TDD workflow)

**Q: What coverage is required?**
A: >90% unit + integration coverage

**Q: How do I review a PR?**
A: Check code quality, tests, docs, security

**Q: What if my test fails?**
A: Don't commit. Fix the test or code first.

**Q: Can I use external libraries?**
A: Yes, but add to dependencies and get approval

---

## Continuous Improvement

### Metrics to Track
- Test coverage trend
- Build times trend
- Bug fix time to resolution
- Feature delivery timeline

### Regular Reviews
- Monthly: Code quality metrics
- Quarterly: Architecture assessment
- Yearly: Technology stack evaluation

### Feedback Loop
- Collect feedback from team
- Adjust rules as needed
- Document decisions in MEMORY.md

---

**Version:** 1.0
**Last Updated:** 2026-02-18
**Status:** Ready to use
**Review Frequency:** Quarterly
