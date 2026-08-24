---
name: azure-devops
description: Use Azure DevOps CLI workflows for branch/commit/PR automation with explicit approval gates.
allowed-tools: ["Bash", "Read", "Edit", "Grep", "Glob"]
---

## When to use
- The task is to commit, push, or create PRs in Azure DevOps repos.
- You need a scripted branch-to-PR workflow with manual approval requirements.

## Entry points
- Script: `~/.codex/skills/azure-devops/azure-devops.sh`
- Docs: `~/.codex/skills/azure-devops/README.md`
- Security notes: `~/.codex/skills/azure-devops/PERMISSIONS.md`

## Typical Commands
- Full workflow: `~/.codex/skills/azure-devops/azure-devops.sh full-workflow <branch> <commit-msg> <pr-title> [target]`
- Create PR only: `~/.codex/skills/azure-devops/azure-devops.sh create-pr <source> <target> <title> [desc]`
- Status: `~/.codex/skills/azure-devops/azure-devops.sh status`

## Notes
- Requires `DEVOPS_PAT` in env or project `.env`.
- PR merge remains manual by policy.
