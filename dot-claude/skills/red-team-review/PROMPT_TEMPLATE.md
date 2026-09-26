# Red Team Review Execution Template

Use this prompt to launch a comprehensive red team review:

---

## Full Review Prompt

```
Create an agent team for a comprehensive red team security and quality review of this project.

Spawn 8 expert reviewers with the following personas:

1. **@ux-reviewer** - UI/UX Expert
   Focus: Accessibility (WCAG), responsive design, user flows, design consistency,
   interaction patterns, error states, performance perception

2. **@backend-reviewer** - Backend Architect
   Focus: API design, database schema, scalability, error handling, caching,
   service architecture, rate limiting, dependency management

3. **@data-reviewer** - Data Engineer
   Focus: Data integrity, validation, migrations, privacy compliance (GDPR/CCPA),
   query performance, backup/recovery, data pipelines

4. **@security-reviewer** - Security Expert
   Focus: Auth/AuthZ, injection attacks (SQL/XSS/CSRF), secrets management,
   API security, dependency vulnerabilities, encryption, threat modeling

5. **@performance-reviewer** - Performance Engineer
   Focus: Bundle size, N+1 queries, caching effectiveness, indexing, memory leaks,
   payload optimization, concurrency, load capacity

6. **@devops-reviewer** - DevOps/SRE
   Focus: CI/CD safety, IaC practices, deployment strategies, monitoring/alerting,
   incident response, disaster recovery, cost optimization

7. **@testing-reviewer** - Testing Specialist
   Focus: Unit/integration/e2e test coverage, test quality, flaky tests,
   performance testing, security testing, contract testing

8. **@quality-reviewer** - Code Quality Reviewer
   Focus: Maintainability, SOLID principles, code smells, documentation,
   technical debt, error patterns, modularity

**Review Process:**

1. Each expert should independently:
   - Use Glob to find all files in their domain
   - Read relevant source files, configs, and tests
   - Document findings with severity: CRITICAL, HIGH, MEDIUM, LOW
   - Include: file path, line numbers, code snippets, specific recommendations

2. Experts should communicate to:
   - Challenge each other's findings
   - Identify cross-cutting concerns that span multiple domains
   - Validate assumptions and proposed solutions

3. Produce structured output per expert:
   ```markdown
   ## [@expert-handle] Domain Review

   ### Critical Issues (Immediate Action Required)
   - **Issue**: [description]
     - **File**: [path:line]
     - **Risk**: [what could go wrong]
     - **Fix**: [specific recommendation]
     - **Effort**: [Low/Medium/High]

   ### High Priority
   [same structure]

   ### Medium Priority
   [same structure]

   ### Positive Findings
   [what this domain does well]
   ```

4. After all experts finish, synthesize into:
   - Executive summary with top 10 critical findings
   - Priority matrix sorted by severity and impact
   - Cross-domain concerns section
   - Recommended action plan with timelines

**Output Location**: Create a comprehensive report at `./RED_TEAM_REVIEW.md`

**Quality Standards:**
- Be adversarial - assume the worst and challenge assumptions
- Provide specific, actionable recommendations with examples
- Include positive findings to reinforce good patterns
- Prioritize findings by business impact, not just technical severity
- Every critical/high issue MUST include a file path and specific fix

Begin the review.
```

---

## Focused Review Variants

### Security-Focused Review
```
Create an agent team for a security-focused review. Spawn:
- @security-reviewer (Security Expert)
- @backend-reviewer (Backend Architect) - focus on API security
- @data-reviewer (Data Engineer) - focus on data privacy
- @devops-reviewer (DevOps) - focus on infrastructure security

Review for: authentication vulnerabilities, injection attacks, secrets exposure,
dependency vulnerabilities, compliance gaps (GDPR/CCPA), and security monitoring.
```

### Performance Review
```
Create an agent team for a performance review. Spawn:
- @performance-reviewer (Performance Engineer)
- @backend-reviewer (Backend Architect) - focus on query optimization
- @ux-reviewer (UI/UX) - focus on perceived performance
- @devops-reviewer (DevOps) - focus on infrastructure efficiency

Review for: slow queries, N+1 problems, bundle size, caching gaps, memory leaks,
and auto-scaling configuration.
```

### Pre-Production Readiness Review
```
Create an agent team for production readiness assessment. Spawn:
- @devops-reviewer (DevOps/SRE)
- @security-reviewer (Security Expert)
- @testing-reviewer (Testing Specialist)
- @performance-reviewer (Performance Engineer)

Review for: deployment safety, monitoring coverage, disaster recovery plans,
load capacity, security hardening, and test coverage.
```

### Code Quality & Maintainability Review
```
Create an agent team for code quality review. Spawn:
- @quality-reviewer (Code Quality)
- @testing-reviewer (Testing Specialist)
- @backend-reviewer (Backend Architect) - focus on architecture

Review for: technical debt, code smells, test quality, documentation gaps,
SOLID violations, and maintainability risks.
```

---

## Advanced Options

### With Plan Approval
Add this to any prompt above:
```
Require plan approval before reviewers begin. Each reviewer should:
1. Plan their review approach (which files, what tools, what criteria)
2. Send plan to team lead for approval
3. Wait for approval before executing
4. Revise plan if rejected
```

### With Specific Model Selection
```
Use Sonnet for all reviewers except:
- Use Opus for @security-reviewer and @backend-reviewer (depth needed)
- Use Haiku for @quality-reviewer (fast pattern matching)
```

### With Selective Scope
```
Limit the review to:
- Backend: src/api/, src/services/, src/models/
- Frontend: src/components/, src/pages/
- Infrastructure: .github/, docker/, terraform/
```

### Incremental Review (Post-Fixes)
```
Re-run security and performance reviews only on the files modified since
the last review. Compare findings to ./RED_TEAM_REVIEW.md and produce
a delta report showing:
- Issues resolved
- New issues introduced
- Issues still open
```

---

## Integration Examples

### Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-push

if git diff --name-only origin/main | grep -E "src/(api|models|auth)/"; then
  echo "Critical path changes detected. Running security review..."
  claude --non-interactive "Run security-focused red team review on changed files"
fi
```

### CI/CD Pipeline
```yaml
# .github/workflows/review.yml
name: Red Team Review
on:
  pull_request:
    branches: [main]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Red Team Review
        run: |
          claude /red-team-review --output review.md
          cat review.md >> $GITHUB_STEP_SUMMARY
```

---

## Tips for Best Results

1. **Provide Context**: Ensure CLAUDE.md or README explains:
   - Tech stack and architecture
   - Known limitations or deliberate design choices
   - Areas of active development vs stable code

2. **Start Broad, Then Focus**:
   - First: Full 8-expert review for comprehensive baseline
   - Then: Targeted reviews (security-only, perf-only) for deep dives

3. **Review at the Right Time**:
   - Feature complete: Full review
   - Pre-release: Production readiness review
   - Post-incident: Security + DevOps focused review
   - Refactor planning: Code quality review

4. **Act on Findings**:
   - Address all CRITICAL issues before shipping
   - Schedule HIGH issues for next sprint
   - Track MEDIUM issues as technical debt
   - Use positive findings to document best practices

5. **Iterative Reviews**:
   - After fixing critical issues, re-run the affected domain reviews
   - Track review history to measure improvement over time
   - Use delta reviews to ensure fixes don't introduce new issues

6. **Cost Management**:
   - Use Haiku for exploratory reviews
   - Use Sonnet for standard reviews
   - Use Opus only for critical deep dives (security audits, major refactors)
