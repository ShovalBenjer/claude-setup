# Project CLAUDE.md Template for Red Team Reviews

Copy this template to your project's `CLAUDE.md` to provide red team reviewers with essential context.

---

```markdown
# Project Context for Red Team Reviews

## Project Overview

**Name**: [Your Project Name]
**Type**: [Web App / API / Mobile App / CLI Tool / Library / etc.]
**Tech Stack**: [e.g., React + TypeScript, Node.js + PostgreSQL, Python + FastAPI]
**Primary Language(s)**: [JavaScript, TypeScript, Python, etc.]

**Description**:
[2-3 sentence description of what this project does and who uses it]

**Critical User Flows**:
1. [e.g., User registration and login]
2. [e.g., Payment processing]
3. [e.g., Data export]

## Architecture

**Architecture Pattern**: [e.g., Monolith, Microservices, Serverless, JAMstack]

**Key Components**:
- **Frontend**: [location, framework, state management]
- **Backend**: [location, framework, API style (REST/GraphQL)]
- **Database**: [type, ORM, migration tool]
- **Cache**: [Redis, in-memory, CDN]
- **Queue/Jobs**: [if applicable: Sidekiq, Bull, SQS]
- **Infrastructure**: [AWS, GCP, Azure, self-hosted]

**Directory Structure**:
```
src/
├── api/           # Backend API endpoints
├── components/    # React components
├── models/        # Database models
├── services/      # Business logic
├── utils/         # Shared utilities
├── config/        # Configuration files
└── tests/         # Test files
```

## Dependencies

**Critical Dependencies**:
- [Dependency name]: [Why it's critical, version constraints]
- [e.g., express: Core API framework, pinned to 4.x for stability]

**Known Vulnerabilities**:
- [List any known security issues you're tracking or have accepted]
- [Or state: "None known as of [date]"]

## Security & Compliance

**Authentication**: [OAuth 2.0, JWT, Session cookies, etc.]
**Authorization**: [RBAC, ABAC, attribute-based, etc.]

**Compliance Requirements**:
- [ ] GDPR (EU data privacy)
- [ ] CCPA (California data privacy)
- [ ] HIPAA (Healthcare data)
- [ ] PCI-DSS (Payment card data)
- [ ] SOC 2
- [ ] Other: [specify]

**Secrets Management**: [AWS Secrets Manager, HashiCorp Vault, .env files, etc.]

**Data Sensitivity**:
- **PII stored**: [Yes/No - what types: names, emails, addresses, etc.]
- **Financial data**: [Yes/No - credit cards, bank accounts, etc.]
- **Health data**: [Yes/No]

## Performance Requirements

**Target Metrics**:
- **Page Load**: [e.g., < 2s for initial paint]
- **API Response**: [e.g., p95 < 200ms]
- **Database Queries**: [e.g., < 100ms for simple queries]

**Expected Scale**:
- **Users**: [Daily active users, concurrent users]
- **Requests**: [Requests per second, peak load]
- **Data Volume**: [Database size, growth rate]

## Testing Strategy

**Current Coverage**:
- Unit tests: [% coverage or location]
- Integration tests: [Yes/No, location]
- E2E tests: [Yes/No, tool used]
- Performance tests: [Yes/No, tool used]

**Test Commands**:
```bash
npm test              # Run all tests
npm run test:unit     # Unit tests only
npm run test:e2e      # E2E tests
npm run test:coverage # Coverage report
```

**CI/CD**: [GitHub Actions, CircleCI, Jenkins, etc.]
**Deployment Strategy**: [Blue/green, Rolling, Canary]

## Known Issues & Technical Debt

**Known Bugs**:
- [Issue description, tracking link, severity]

**Technical Debt**:
- [Debt item, why it exists, plan to address]
- [e.g., "Legacy auth system uses sessions instead of JWT - migrating in Q2"]

**Deliberate Design Choices** (Don't Flag These):
- [Choice that might look like a problem but is intentional]
- [e.g., "No server-side rendering - this is a dashboard app for authenticated users only"]

## Development Constraints

**Browser Support**: [e.g., Modern browsers only (Chrome, Firefox, Safari, Edge - last 2 versions)]
**Mobile Support**: [Responsive web, Native apps, Not supported]
**Accessibility Target**: [WCAG 2.1 Level AA, Level AAA, Best effort]

**Performance Budget**:
- Bundle size: [e.g., < 500KB gzipped]
- First Contentful Paint: [e.g., < 1.5s]
- Time to Interactive: [e.g., < 3.5s]

## Areas of Active Development

**Currently Working On**:
- [Feature or refactor in progress - expect instability here]

**Stable Areas** (Safe to Review):
- [Modules that are feature-complete and ready for review]

**Off-Limits** (Don't Review These):
- [Experimental code, prototypes, scheduled for deletion]

## Review Guidance for Red Team

**High Priority Areas**:
1. [e.g., Payment processing module - security critical]
2. [e.g., User data export - privacy/compliance critical]
3. [e.g., Admin dashboard - privilege escalation risk]

**Low Priority Areas**:
- [e.g., Marketing pages - low risk, low criticality]

**Specific Concerns**:
- [Any specific things you want the reviewers to focus on]
- [e.g., "We migrated from MySQL to PostgreSQL - check for query incompatibilities"]

## Deployment & Operations

**Environments**:
- **Production**: [URL, deployment frequency]
- **Staging**: [URL, what it's used for]
- **Development**: [Local setup instructions]

**Monitoring**:
- **APM**: [Datadog, New Relic, etc.]
- **Logs**: [CloudWatch, Splunk, etc.]
- **Errors**: [Sentry, Rollbar, etc.]
- **Uptime**: [Pingdom, UptimeRobot, etc.]

**Incident Response**:
- **On-call rotation**: [Yes/No]
- **Runbooks**: [Location of incident playbooks]
- **SLA/SLO**: [If applicable]

## Contact & Resources

**Documentation**:
- API Docs: [URL or location]
- Architecture Diagrams: [URL or location]
- Runbooks: [URL or location]

**Key Contacts**:
- Tech Lead: [Name/Email]
- Security: [Name/Email]
- DevOps: [Name/Email]

---

## Red Team Review Instructions

When performing a red team review of this project:

1. **Start Here**:
   - Read this CLAUDE.md fully
   - Review README.md for setup instructions
   - Check package.json / requirements.txt for dependencies

2. **Focus Areas** (based on above context):
   - [Specific modules or features to prioritize]

3. **Context to Keep in Mind**:
   - [Any nuances reviewers should know]
   - [e.g., "This is a prototype - prioritize architecture over polish"]

4. **Review Standards**:
   - **Critical**: Security vulnerabilities, data loss risks, compliance violations
   - **High**: Performance issues affecting users, major bugs, accessibility failures
   - **Medium**: Code quality issues, maintainability concerns, minor bugs
   - **Low**: Style inconsistencies, minor optimizations, documentation gaps

5. **Output Format**:
   - File: `./RED_TEAM_REVIEW.md`
   - Include: Severity, Domain, Issue, File:Line, Risk, Fix, Effort
   - Prioritize: Issues by business impact, not just technical severity
```

---

## Usage

1. **Copy this template** to your project root as `CLAUDE.md`
2. **Fill in all sections** with your project's specifics
3. **Update regularly** as the project evolves
4. **Run red team review** - reviewers will automatically read this file

This gives reviewers the context they need to:
- Focus on what matters
- Avoid false positives (flagging deliberate choices)
- Understand your architecture and constraints
- Prioritize findings based on your business needs
- Provide actionable, relevant recommendations

## Minimal Version

If you want a quicker start, here's a minimal CLAUDE.md:

```markdown
# [Project Name]

**Type**: [Web App / API / etc.]
**Stack**: [Tech stack]

## Architecture
[Brief description of how components fit together]

## Critical Paths
1. [Most important user flow]
2. [Second most important]

## Security
- **Auth**: [How authentication works]
- **PII**: [Yes/No and what types]

## Known Issues
- [Major known bugs or tech debt]

## Focus Areas for Review
1. [What you most want reviewed]
2. [Second priority]

## Don't Flag These
- [Deliberate choices that might look wrong]
```
