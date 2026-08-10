#!/usr/bin/env bash
set -euo pipefail

# Pulls the Jira API token from Azure Key Vault at start time so the secret
# never lands in .mcp.json (which lives inside the seekapa worktree at $HOME).
# Requires: az login session active, uvx on PATH.

VAULT="Shoval"
SECRET="JIRA-API-KEY"

if ! command -v az >/dev/null 2>&1; then
  echo "mcp-atlassian-launcher: az CLI not found on PATH" >&2
  exit 1
fi
if ! command -v uvx >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
fi

TOKEN="$(az keyvault secret show --vault-name "$VAULT" --name "$SECRET" --query value -o tsv 2>/dev/null)"
if [ -z "${TOKEN:-}" ]; then
  echo "mcp-atlassian-launcher: failed to read $SECRET from vault $VAULT (az login expired?)" >&2
  exit 1
fi

export JIRA_URL="https://qboservices.atlassian.net"
export JIRA_USERNAME="shoval.be@i-sdd.com"
export JIRA_API_TOKEN="$TOKEN"

exec uvx mcp-atlassian "$@"
