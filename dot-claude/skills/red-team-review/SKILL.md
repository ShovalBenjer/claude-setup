---
name: red-team-review
description: Multi-persona project review using parallel agent teams (security, architecture, performance, UX, eval). Spawns subagents in worktrees, aggregates findings into a unified report. Triggers on "/red-team-review", "comprehensive review", "second opinion on this PR", "audit this codebase".
model: claude-opus-4-7
disable-model-invocation: true
---

# Red Team Review Skill

A comprehensive multi-persona project review using agent teams.

## Overview

This skill spawns a team of expert reviewers, each with a distinct perspective, to conduct a thorough adversarial review of your project. Each expert operates independently and challenges assumptions, identifies risks, and provides actionable recommendations.

## Expert Personas

### 1. UI/UX Expert (@ux-reviewer)
**Focus**: User experience, accessibility, design consistency
- Visual hierarchy and information architecture
- Accessibility (WCAG compliance, keyboard navigation, screen readers)
- Responsive design and cross-device compatibility
- User flows and interaction patterns
- Design system consistency
- Performance perception (loading states, animations, transitions)
- Error states and edge case handling in UI
- Localization and internationalization readiness

### 2. Backend Architect (@backend-reviewer)
**Focus**: Server architecture, scalability, reliability
- API design and RESTful/GraphQL patterns
- Database schema design and normalization
- Transaction handling and data consistency
- Caching strategies and invalidation
- Error handling and logging
- Background job processing and queue management
- Service boundaries and microservice architecture
- Rate limiting and throttling
- Dependency management and third-party integrations

### 3. Data Engineer (@data-reviewer)
**Focus**: Data integrity, pipelines, analytics
- Data models and relationships
- Data validation and sanitization
- Migration strategies and rollback plans
- Data retention and archival policies
- ETL/ELT pipeline design
- Data warehouse schema (if applicable)
- Query performance and indexing strategies
- Data privacy compliance (GDPR, CCPA)
- Backup and disaster recovery
- Data lineage and observability

### 4. Security Expert (@security-reviewer)
**Focus**: Vulnerabilities, threat modeling, compliance
- Authentication and authorization (OAuth, JWT, session management)
- Input validation and injection attacks (SQL, XSS, CSRF)
- Secrets management and key rotation
- API security (rate limiting, authentication, CORS)
- Dependency vulnerabilities (supply chain security)
- Encryption at rest and in transit
- Security headers and CSP policies
- Threat modeling and attack surface analysis
- Compliance requirements (SOC2, HIPAA, PCI-DSS if applicable)
- Logging sensitive operations (without logging sensitive data)

### 5. Performance Engineer (@performance-reviewer)
**Focus**: Speed, efficiency, resource utilization
- Frontend performance (bundle size, lazy loading, code splitting)
- Backend performance (N+1 queries, query optimization)
- Caching effectiveness (CDN, browser cache, server cache)
- Database indexing and query plans
- Memory usage and leak detection
- Network payload size and compression
- Critical rendering path optimization
- Concurrency and parallelization opportunities
- Resource pooling (connections, threads)
- Load testing and capacity planning

### 6. DevOps/SRE (@devops-reviewer)
**Focus**: Operations, monitoring, deployment reliability
- CI/CD pipeline design and safety
- Infrastructure as Code (IaC) practices
- Deployment strategies (blue/green, canary, rolling)
- Monitoring and alerting coverage
- Log aggregation and searchability
- Incident response procedures
- Disaster recovery and business continuity
- Cost optimization (cloud resources, compute)
- Auto-scaling configuration
- Health checks and readiness probes

### 7. Testing Specialist (@testing-reviewer)
**Focus**: Test coverage, quality assurance strategy
- Unit test coverage and quality
- Integration test strategy
- End-to-end test coverage for critical paths
- Test data management and fixtures
- Flaky test detection and remediation
- Performance testing and benchmarks
- Security testing (SAST, DAST, penetration testing)
- Contract testing for APIs
- Accessibility testing automation
- Visual regression testing

### 8. Code Quality Reviewer (@quality-reviewer)
**Focus**: Maintainability, technical debt, best practices
- Code organization and modularity
- Naming conventions and readability
- DRY violations and code duplication
- SOLID principles adherence
- Error handling patterns
- Documentation quality (inline comments, README, API docs)
- Technical debt identification and prioritization
- Code smell detection (long functions, god objects, feature envy)
- Dependency injection and testability
- Configuration management

## Review Process

When you invoke this skill, the team lead will:

1. **Spawn Expert Teammates**: Create 8 specialized reviewers, each with their persona and focus area
2. **Distribute Tasks**: Assign each expert to review the project from their perspective
3. **Parallel Investigation**: Experts work independently, reading code, running analyses, and documenting findings
4. **Cross-Challenge**: Experts communicate to challenge each other's assumptions and validate findings
5. **Synthesize Report**: Lead consolidates all findings into a comprehensive review document

## Usage

```bash
/red-team-review [path-to-project]
```

Or simply:
```
Review this project with the full red team
```

## Expected Deliverables

Each expert produces:
- **Risk Assessment**: Critical, High, Medium, Low severity issues
- **Specific Findings**: File paths, line numbers, code snippets
- **Recommendations**: Actionable fixes with priority levels
- **Best Practice Gaps**: Missing patterns or tools

The team lead synthesizes:
- **Executive Summary**: Top 10 critical findings across all domains
- **Priority Matrix**: What to fix first based on impact and effort
- **Domain-Specific Reports**: Detailed findings per expert area
- **Architectural Recommendations**: High-level improvements

## Output Format

```markdown
# Red Team Review Report
Project: [name]
Date: [date]
Reviewers: 8 expert personas

## Executive Summary
[Top 10 critical cross-cutting concerns]

## Priority Matrix
| Severity | Domain | Issue | File | Recommendation | Effort |
|----------|--------|-------|------|----------------|--------|
| ...      | ...    | ...   | ...  | ...            | ...    |

## Domain Reviews

### UI/UX (@ux-reviewer)
#### Critical Issues
- [issue with file:line]

#### High Priority
- [issue with file:line]

#### Recommendations
- [actionable items]

[... repeat for all 8 domains ...]

## Cross-Cutting Concerns
[Issues that span multiple domains]

## Positive Findings
[What the project does well - patterns to maintain]

## Next Steps
[Prioritized action plan]
```

## Configuration

### Model Selection
By default, reviewers use Sonnet for balanced speed and depth. For faster reviews:
```
Review with the red team using Haiku for each reviewer
```

For maximum depth on complex projects:
```
Review with the red team using Opus for security and backend reviewers
```

### Selective Reviews
Focus on specific domains:
```
Spawn only the UI/UX, Performance, and Accessibility reviewers
```

### Plan Approval Mode
For high-risk reviews where you want to approve approaches first:
```
Create the red team with plan approval required for all reviewers
```

## Notes

- Each reviewer is an independent Claude Code session with full project context
- Reviewers have read access to all files and can run analysis tools
- The review is adversarial by design - experts are instructed to be critical
- Cross-domain communication helps identify issues that span multiple areas
- Estimated time: 10-30 minutes depending on project size and depth
- Token cost: Significant (8 concurrent sessions) - best used for important reviews

## Best Practices

1. **Run on stable codebases**: Red team reviews work best on feature-complete or pre-release code
2. **Provide context**: Include a README or CLAUDE.md with architecture overview
3. **Start broad, then focus**: First run a full review, then spawn specific experts for deep dives
4. **Address critical findings first**: Use the priority matrix to guide fixes
5. **Re-review after fixes**: Run targeted re-reviews after addressing high-severity issues

## Integration with CI/CD

This skill can be adapted for automated reviews:
```bash
# In your CI pipeline
claude /red-team-review --output review-report.md --fail-on critical
```

## Limitations

- Reviews are read-only (experts don't make changes, only recommend)
- Best for projects with clear file structure and documentation
- Token-intensive for very large codebases (>100k lines)
- Requires agent teams experimental feature enabled
