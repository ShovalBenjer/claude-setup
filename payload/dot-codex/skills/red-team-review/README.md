# Red Team Review - Quick Start

A comprehensive multi-persona adversarial review system using Claude Code agent teams.

## Quick Start

### 1. Enable Agent Teams (Already Done ✓)

The experimental feature is enabled in your `~/.codex/settings.json`.

### 2. Run a Full Review

In any project directory:

```bash
claude
```

Then say:
```
Use the red team to review this project
```

Or use the full prompt from `PROMPT_TEMPLATE.md`.

### 3. View Results

The review report will be generated at `./RED_TEAM_REVIEW.md`

## What Gets Reviewed

**8 Expert Personas:**
- 🎨 **UI/UX**: Accessibility, design consistency, user flows
- 🏗️ **Backend**: API design, scalability, database architecture
- 📊 **Data**: Data integrity, privacy, migrations, pipelines
- 🔒 **Security**: Auth, vulnerabilities, compliance, threat modeling
- ⚡ **Performance**: Speed, efficiency, resource optimization
- 🚀 **DevOps**: CI/CD, monitoring, deployment, reliability
- ✅ **Testing**: Coverage, quality, automation strategies
- 🧹 **Code Quality**: Maintainability, best practices, tech debt

## Review Types

### Full Review (All 8 Experts)
```
Create the full red team to review this project
```

### Security Focus (4 Experts)
```
Create a red team for security review: spawn security, backend, data, and devops reviewers
```

### Performance Focus (4 Experts)
```
Create a red team for performance review: spawn performance, backend, ux, and devops reviewers
```

### Pre-Production (4 Experts)
```
Create a red team for production readiness: spawn devops, security, testing, and performance reviewers
```

## Output Format

```markdown
# Red Team Review Report

## Executive Summary
[Top 10 critical findings]

## Priority Matrix
| Severity | Domain | Issue | File | Recommendation | Effort |

## Domain Reviews

### [@ux-reviewer] UI/UX
#### Critical Issues
- **Issue**: Insufficient color contrast
  - **File**: src/components/Button.tsx:45
  - **Risk**: WCAG AAA failure, accessibility lawsuit risk
  - **Fix**: Change color from #777 to #595959 (contrast ratio 4.5:1)
  - **Effort**: Low

[... all 8 domains ...]

## Cross-Cutting Concerns
## Positive Findings
## Next Steps
```

## File Structure

```
~/.codex/skills/red-team-review/
├── README.md              # This file
├── SKILL.md              # Full skill documentation
├── PROMPT_TEMPLATE.md    # Ready-to-use prompts
└── PROJECT_TEMPLATE.md   # Example CLAUDE.md for projects
```

## Best Practices

✅ **DO:**
- Run on stable, feature-complete code
- Provide project context via CLAUDE.md
- Address CRITICAL findings before shipping
- Use focused reviews for deep dives
- Re-review after major fixes

❌ **DON'T:**
- Run on actively changing code (wait for stable state)
- Ignore context setup (reviewers need architecture knowledge)
- Try to fix everything at once (prioritize by severity)
- Run full reviews in CI (too expensive, use focused reviews)
- Skip re-reviews (verify fixes don't introduce new issues)

## Cost Considerations

**Token Usage** (approximate):
- Full 8-expert review: **High** (8 concurrent sessions)
- Focused 4-expert review: **Medium** (4 concurrent sessions)
- Single domain deep dive: **Low** (1 session)

**Model Selection:**
- **Haiku**: Fast, cheap, good for initial scans
- **Sonnet**: Balanced, recommended for most reviews
- **Opus**: Deep analysis, use for critical security/architecture reviews

**Optimization:**
```
# Fast initial scan
Review with red team using Haiku for all reviewers

# Then deep dive on critical areas
Spawn only @security-reviewer and @backend-reviewer using Opus
```

## Display Modes

### In-Process (Default)
All reviewers run in your main terminal. Use `Shift+Up/Down` to switch between them.

### Split Panes (tmux/iTerm2)
Each reviewer gets its own pane. Requires tmux or iTerm2 with `it2` CLI.

Change in `~/.codex/settings.json`:
```json
{
  "teammateMode": "in-process"  // or "tmux" for split panes
}
```

## Interacting with Reviewers

### View a Specific Reviewer
```
# In-process mode
Shift+Up/Down to cycle through reviewers
Enter to view their session
Escape to return to lead

# Split pane mode
Click into their pane
```

### Message a Reviewer Directly
```
# In in-process mode
Shift+Up/Down to select reviewer, then type your message

# Or tell the lead
"Ask @security-reviewer to focus on the authentication module"
```

### Check Progress
```
Show me the task list
```

or press `Ctrl+T` in in-process mode.

## Troubleshooting

### Reviewers Not Spawning
- Verify agent teams are enabled: check `~/.codex/settings.json`
- Ensure tmux is installed if using split panes: `which tmux`
- Task might be too simple (teams are for complex parallelizable work)

### Too Many Permission Prompts
Pre-approve read operations in your [permission settings](https://code.claude.com/docs/en/permissions).

### Review Taking Too Long
- Use Haiku for faster reviews
- Run focused reviews (4 experts instead of 8)
- Limit scope: "Review only the src/api/ directory"

### Reviewers Stopping Early
Check their output (Shift+Up/Down or click their pane) and provide additional instructions.

## Examples

### Review Before Deploying
```bash
cd ~/my-app
claude

# In Claude:
"Create the full red team to review this project before production deployment.
Use Sonnet for all reviewers. Output the report to PRE_DEPLOY_REVIEW.md"
```

### Security Audit
```bash
claude

# In Claude:
"Create a security-focused red team with 4 reviewers:
- @security-reviewer (using Opus)
- @backend-reviewer (focus on API security)
- @data-reviewer (focus on data privacy and GDPR compliance)
- @devops-reviewer (focus on infrastructure security)

Be extremely thorough. Output to SECURITY_AUDIT.md"
```

### Review Changed Files Only
```bash
# After making changes
claude

# In Claude:
"Create the red team to review only the files I changed in this branch
compared to main. Focus on: security, performance, and testing."
```

## Next Steps

1. **Try it now**: Run a quick review on any project
2. **Customize**: Add project-specific context to CLAUDE.md (see `PROJECT_TEMPLATE.md`)
3. **Integrate**: Add to your workflow (pre-commit, pre-deploy, weekly audits)
4. **Iterate**: Run focused re-reviews after addressing findings

## Resources

- [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams)
- [Subagents vs Teams](https://code.claude.com/docs/en/features-overview#compare-similar-features)
- [Permission Settings](https://code.claude.com/docs/en/permissions)
- [Git Worktrees for Parallel Sessions](https://code.claude.com/docs/en/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees)

## Feedback & Improvements

This is a living skill. Improve it by:
1. Adding new expert personas for your domain
2. Refining review criteria based on findings
3. Creating domain-specific prompt variants
4. Sharing successful review patterns

---

**Ready to start?** Run: `claude` and say "Use the red team to review this project"
