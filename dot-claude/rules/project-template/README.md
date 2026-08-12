# Per-project rules (the project half of the unified rule setup)

The rule set is split into two layers, mirroring how Claude Code's settings chain
already works (global `~/.claude/`, per-project `.claude/` in the repo):

- **Global** (`dot-claude/rules/*.md`, deployed to `~/.claude/rules/`): rules true in
  EVERY repo. Read into every session. Keep this tree lean, because every rule here is
  a per-session token cost paid in all projects, relevant or not.
- **Per-project** (this `project-template/` folder): rules bound to ONE external system
  or product. They only ever fire in a repo that touches that system, so carrying them
  in the global tree taxes every unrelated session. A consuming repo adopts one by
  copying it into that repo's own `.claude/rules/`.

## Why the split exists

Measured 2026-08-12: the global rules tree was ~11,300 words read every session. Two
files in it were bound to single external systems and fired nowhere else:

- `jira-comment-drafting.md` (632 words): comment tone for `qboservices.atlassian.net`.
- `foundry-deployment-per-project.md` (657 words): deployment naming for the `brn-azai`
  Azure Foundry account.

Every session in every repo (including this harness, which touches neither Jira nor
Foundry) paid 1,289 words for context that could not apply. Moving them here removes
that tax from the global layer without losing the rule: the repos that DO touch Jira or
Foundry copy the file into their own `.claude/rules/`.

## How to adopt one in a consuming repo

```bash
mkdir -p <repo>/.claude/rules
cp dot-claude/rules/project-template/jira-comment-drafting.md <repo>/.claude/rules/
```

A rule declaring itself "Global rule" in its own header but binding to one named
external system (a Jira host, a cloud account, a single product) belongs here, not in
the global tree. "Applies to every session" in the header means every session THAT
TOUCHES THAT SYSTEM, not every session on the machine.
