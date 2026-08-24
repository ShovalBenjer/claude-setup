# Example Red Team Review Session

This document shows exactly what a red team review session looks like.

## Example 1: Full Review

### Start Claude in Your Project
```bash
cd ~/my-project
claude
```

### Launch the Red Team
```
Create an agent team for a comprehensive red team review of this project.

Spawn 8 expert reviewers with the following personas:

1. @ux-reviewer - UI/UX Expert focusing on accessibility, responsive design,
   user flows, design consistency, interaction patterns, and error states

2. @backend-reviewer - Backend Architect focusing on API design, database schema,
   scalability, error handling, caching, and service architecture

3. @data-reviewer - Data Engineer focusing on data integrity, validation,
   migrations, privacy compliance, query performance, and backup/recovery

4. @security-reviewer - Security Expert focusing on auth/authz, injection attacks,
   secrets management, API security, dependency vulnerabilities, and threat modeling

5. @performance-reviewer - Performance Engineer focusing on bundle size, query
   optimization, caching effectiveness, indexing, memory leaks, and concurrency

6. @devops-reviewer - DevOps/SRE focusing on CI/CD safety, deployment strategies,
   monitoring/alerting, incident response, and disaster recovery

7. @testing-reviewer - Testing Specialist focusing on test coverage, test quality,
   flaky tests, performance testing, and security testing

8. @quality-reviewer - Code Quality Reviewer focusing on maintainability, SOLID
   principles, code smells, documentation, and technical debt

Each expert should:
- Use Glob to find all relevant files in their domain
- Read source files, configs, and tests thoroughly
- Document findings with severity: CRITICAL, HIGH, MEDIUM, LOW
- Include: file path, line numbers, code snippets, specific recommendations
- Challenge assumptions and communicate with other reviewers
- Note positive findings (what the project does well)

After all experts finish, synthesize findings into RED_TEAM_REVIEW.md with:
- Executive summary (top 10 critical findings)
- Priority matrix (severity, domain, issue, file, recommendation, effort)
- Detailed findings per domain
- Cross-cutting concerns
- Positive findings
- Prioritized action plan

Begin the review.
```

### What Happens Next

1. **Team Lead spawns 8 reviewers** (you'll see them listed)
2. **Reviewers work in parallel** - each reads files in their domain
3. **Progress updates** - you can check task status with `Ctrl+T` or "show task list"
4. **Reviewers communicate** - they message each other to validate findings
5. **Lead synthesizes** - after all reviewers finish, creates the final report
6. **Output**: `RED_TEAM_REVIEW.md` in your project directory

### Interacting During Review

While the review runs, you can:

**Check progress:**
```
Show me the current task list
```

**View a specific reviewer's work:**
```
# In-process mode: Shift+Up/Down to select, Enter to view
# Split pane mode: Click into their pane
```

**Give specific instructions:**
```
Ask @security-reviewer to pay special attention to the authentication module
```

**Speed up if needed:**
```
Focus only on CRITICAL and HIGH severity issues
```

### Expected Output

`RED_TEAM_REVIEW.md`:
```markdown
# Red Team Review Report
Project: my-project
Date: 2024-02-14
Reviewers: 8 expert personas

## Executive Summary

Top 10 Critical Findings:

1. **SQL Injection vulnerability in user search** (@security-reviewer)
   - File: src/api/users.js:45
   - Risk: Attackers can extract entire database
   - Fix: Use parameterized queries
   - Effort: Low (2 hours)

2. **No rate limiting on password reset** (@security-reviewer)
   - File: src/api/auth.js:89
   - Risk: Brute force attacks, account takeover
   - Fix: Implement express-rate-limit
   - Effort: Medium (4 hours)

[... 8 more critical findings ...]

## Priority Matrix

| Severity | Domain | Issue | File | Recommendation | Effort |
|----------|--------|-------|------|----------------|--------|
| CRITICAL | Security | SQL Injection | src/api/users.js:45 | Use parameterized queries | Low |
| CRITICAL | Security | No rate limiting | src/api/auth.js:89 | Add express-rate-limit | Medium |
| HIGH | Performance | N+1 query in dashboard | src/api/dashboard.js:23 | Use JOIN or dataloader | Medium |
| HIGH | Accessibility | Missing ARIA labels | src/components/Modal.tsx:12 | Add aria-label and role | Low |
[... more findings ...]

## Domain Reviews

### [@security-reviewer] Security Expert

#### Critical Issues

**SQL Injection in User Search**
- **File**: src/api/users.js:45
- **Code**:
  ```javascript
  db.query(`SELECT * FROM users WHERE name LIKE '%${req.query.search}%'`)
  ```
- **Risk**: Attacker can inject SQL to extract data, modify data, or escalate privileges
- **Fix**:
  ```javascript
  db.query('SELECT * FROM users WHERE name LIKE ?', [`%${req.query.search}%`])
  ```
- **Effort**: Low (30 minutes to fix, 1 hour to test)

**No Rate Limiting on Password Reset**
- **File**: src/api/auth.js:89
- **Risk**: Brute force password reset tokens, account takeover
- **Fix**: Add rate limiting middleware
  ```javascript
  const rateLimit = require('express-rate-limit');
  const resetLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5
  });
  app.post('/reset-password', resetLimiter, resetHandler);
  ```
- **Effort**: Medium (2 hours to implement, 2 hours to test)

#### High Priority

[... more findings ...]

#### Positive Findings
- ✅ Excellent use of bcrypt for password hashing (12 rounds)
- ✅ JWT tokens have appropriate expiry (15 minutes)
- ✅ HTTPS enforced in production

---

### [@performance-reviewer] Performance Engineer

#### Critical Issues

**N+1 Query in Dashboard Loading**
- **File**: src/api/dashboard.js:23
- **Code**:
  ```javascript
  const users = await User.findAll();
  for (const user of users) {
    user.posts = await Post.findByUserId(user.id); // N+1!
  }
  ```
- **Risk**: Dashboard takes 5+ seconds with 1000 users
- **Fix**: Use JOIN or eager loading
  ```javascript
  const users = await User.findAll({
    include: [{ model: Post }]
  });
  ```
- **Effort**: Low (1 hour)

[... continues for all 8 domains ...]

## Cross-Cutting Concerns

1. **Logging of Sensitive Data**
   - Multiple reviewers flagged: logs contain user emails and tokens
   - Files: src/middleware/logger.js, src/api/auth.js
   - Fix: Sanitize logs before output

2. **Inconsistent Error Handling**
   - Flagged by: @backend-reviewer, @quality-reviewer
   - Some endpoints return errors as strings, others as objects
   - Fix: Standardize error response format

## Positive Findings

What this project does well:
- ✅ Comprehensive test coverage (87% overall, 95% on critical paths)
- ✅ Clear separation of concerns (models, services, controllers)
- ✅ Excellent API documentation using OpenAPI
- ✅ Proper use of transactions for data integrity
- ✅ Strong monitoring setup (APM, logs, alerts)

## Next Steps

### Immediate (Ship Blockers)
1. Fix SQL injection vulnerability (src/api/users.js:45) - **2 hours**
2. Add rate limiting to auth endpoints - **4 hours**
3. Remove sensitive data from logs - **3 hours**

**Total**: 9 hours | **Must complete before next deploy**

### This Sprint (High Priority)
1. Fix N+1 queries (3 instances found) - **4 hours**
2. Add missing ARIA labels to all modals - **6 hours**
3. Implement missing database indexes - **3 hours**
4. Add integration tests for payment flow - **8 hours**

**Total**: 21 hours

### Next Sprint (Medium Priority)
- Address code duplication in validators (8 files)
- Improve error messages for better UX
- Add performance monitoring to slow endpoints
- Document deployment runbooks

### Technical Debt Tracking
- Create tickets for all 47 findings
- Prioritize CRITICAL and HIGH for next 2 sprints
- Schedule monthly re-reviews of fixed areas
```

---

## Example 2: Security-Focused Review

### Quick Security Audit
```
Create a red team for a security audit. Spawn 4 reviewers:

1. @security-reviewer - Main security expert using Opus for deep analysis
2. @backend-reviewer - Focus on API security and server-side vulnerabilities
3. @data-reviewer - Focus on data privacy, GDPR compliance, and PII handling
4. @devops-reviewer - Focus on infrastructure security and secrets management

Review for:
- Authentication and authorization vulnerabilities
- Injection attacks (SQL, XSS, CSRF, command injection)
- Secrets exposure in code or logs
- Dependency vulnerabilities
- API security (CORS, rate limiting, authentication)
- Data privacy compliance (GDPR, CCPA)
- Infrastructure security (container configs, permissions)

Be extremely thorough. Every CRITICAL finding must include proof-of-concept
exploit steps. Output to SECURITY_AUDIT.md
```

---

## Example 3: Performance Review

### Performance Optimization Review
```
Create a red team for performance optimization. Spawn 4 reviewers:

1. @performance-reviewer - Main performance expert
2. @backend-reviewer - Focus on database queries and server performance
3. @ux-reviewer - Focus on perceived performance and user experience
4. @devops-reviewer - Focus on infrastructure efficiency and auto-scaling

Review for:
- Slow database queries (N+1, missing indexes, full table scans)
- Large bundle sizes and unoptimized assets
- Missing caching opportunities
- Memory leaks and resource exhaustion
- Inefficient algorithms (O(n²) where O(n) is possible)
- Blocking operations in critical paths
- Over-fetching data in APIs

For each issue found, include:
- Benchmark showing current performance
- Specific optimization recommendation
- Expected performance improvement

Output to PERFORMANCE_REVIEW.md
```

---

## Example 4: Pre-Production Checklist

### Production Readiness Assessment
```
Create a red team for production readiness assessment. Spawn 4 reviewers:

1. @devops-reviewer - Main production readiness expert
2. @security-reviewer - Security hardening checklist
3. @testing-reviewer - Test coverage and QA readiness
4. @performance-reviewer - Load capacity and performance benchmarks

Create a go/no-go checklist covering:
- Deployment automation (rollback plan, health checks, zero-downtime)
- Monitoring (APM, logs, errors, uptime, alerts)
- Security hardening (secrets rotation, least privilege, audit logs)
- Performance benchmarks (load tested to 2x expected traffic)
- Test coverage (>80% on critical paths, E2E for main flows)
- Disaster recovery (backups tested, runbooks documented)
- Documentation (API docs, deployment guide, incident playbooks)

Output a checklist to PRODUCTION_READINESS.md with:
- ✅ Items that pass
- ❌ Items that fail (with specific fixes needed)
- ⚠️  Items that are partial (with gaps to address)

Include a final GO / NO-GO recommendation with blockers listed.
```

---

## Example 5: Incremental Review (After Fixes)

### Re-Review After Addressing Findings
```
Load the previous review from RED_TEAM_REVIEW.md.

Spawn only @security-reviewer and @performance-reviewer.

Re-review the files that were flagged in the previous report for:
- Security CRITICAL and HIGH issues (12 files)
- Performance CRITICAL and HIGH issues (8 files)

For each previously flagged issue, determine:
- ✅ RESOLVED: Issue is fixed and no longer present
- ⚠️  PARTIALLY RESOLVED: Some improvement but issue remains
- ❌ NOT RESOLVED: Issue still present
- 🆕 NEW ISSUE: Fix introduced a new problem

Output a delta report to REVIEW_DELTA.md showing:
- Issues resolved (with verification)
- Issues still open
- New issues introduced by fixes
- Overall progress score (% of issues resolved)

If any CRITICAL issues remain or were introduced, mark the report with
**DEPLOYMENT BLOCKED** at the top.
```

---

## Tips for Best Results

### Before Running Review
1. ✅ Ensure CLAUDE.md exists with project context
2. ✅ Code is in a stable state (feature complete, tests passing)
3. ✅ Dependencies are up to date
4. ✅ You have 15-30 minutes to let the review run

### During Review
1. ✅ Let reviewers finish before interrupting
2. ✅ Check task progress occasionally (Ctrl+T)
3. ✅ Provide clarifications if reviewers ask questions
4. ❌ Don't try to fix issues while review is running

### After Review
1. ✅ Read the full report before taking action
2. ✅ Address all CRITICAL issues immediately
3. ✅ Create tickets for HIGH and MEDIUM issues
4. ✅ Re-review after fixes using incremental review
5. ✅ Update CLAUDE.md with any deliberate choices reviewers flagged

---

## Cost Optimization

### Use the Right Model for the Job

**Fast Initial Scan** (Lowest Cost):
```
Review with red team using Haiku for all reviewers
```

**Standard Review** (Balanced):
```
Review with red team using Sonnet for all reviewers
```

**Deep Critical Review** (Highest Quality):
```
Review with red team using Opus for security and backend reviewers,
Sonnet for the rest
```

### Focused Reviews Cost Less

Instead of running all 8 reviewers:
- Security audit: 4 reviewers (Security, Backend, Data, DevOps)
- Performance: 4 reviewers (Performance, Backend, UX, DevOps)
- Code quality: 3 reviewers (Quality, Testing, Backend)

This cuts token usage by 50-60% while still getting thorough coverage.

---

Ready to try it? `cd` into your project and run `claude`, then use one of the prompts above!
