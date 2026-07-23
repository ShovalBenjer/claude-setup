---
name: azure-devops
description: Azure DevOps CLI workflow automation with explicit manual approval gates.
---

## Purpose
Use Azure DevOps automation safely for branch, commit, push, and PR creation.

## Entry Points
- Script: `~/.Codex/skills/azure-devops/azure-devops.sh`
- Docs: `~/.Codex/skills/azure-devops/README.md`

## Commands
- Full workflow: `~/.Codex/skills/azure-devops/azure-devops.sh full-workflow <branch> <commit-msg> <pr-title> [target]`
- Create PR only: `~/.Codex/skills/azure-devops/azure-devops.sh create-pr <source> <target> <title> [desc]`
- Status: `~/.Codex/skills/azure-devops/azure-devops.sh status`

## Notes
- Requires `DEVOPS_PAT` in runtime env or `.env`.
- Merge remains manual by policy.
