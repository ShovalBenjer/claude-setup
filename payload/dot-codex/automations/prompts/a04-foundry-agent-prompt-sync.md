# A4. Foundry Agent Prompt Sync Diff

Schedule: Weekdays 7:30 AM
Repo root: `/home/shovalbe/projects/cs-agent/`, `/home/shovalbe/projects/hr-agent/`, `/home/shovalbe/projects/campaign-analysis/`
Mode: read + ADO bug if drift exceeds threshold

For each Foundry agent repo (`cs-agent`, `hr-agent`, `campaign-analysis`):

1. Read the prompt files committed to git, typically `prompt.md`, `agent_prompts/*.md`, or `agent.yaml`.
2. Pull the live prompt from Foundry via the Foundry SDK. Project: `seekapa_ai`; resource group: `seekapa_ai`. Use the agent IDs from `~/.claude/projects/-home-shovalbe/memory/project_foundry_agent_repos.md`.
3. Diff line-by-line. Compute:
   - Lines in git not in Foundry: un-deployed.
   - Lines in Foundry not in git: deployed but un-versioned; this is the biggest risk.
4. Output `~/.claude/docs/FOUNDRY_PROMPT_DIFF_<DATE>.md`.

If `in Foundry not in git` exceeds 10 lines for any agent, file an ADO bug via:

```bash
~/.claude/bin/work-item.sh create --type Bug --title "Foundry prompt drift: <agent>" --tags "foundry-drift"
```

Attach or include the diff.

Auth: `az login` plus `AZURE_CLIENT_ID` from Key Vault. If a 401 occurs, do not retry. Note `auth-needs-refresh` in the output and stop.
