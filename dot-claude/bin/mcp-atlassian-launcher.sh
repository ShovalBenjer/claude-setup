#!/usr/bin/env bash
set -euo pipefail

# Pulls the Jira API token from Azure Key Vault at start time so the secret
# never lands in .mcp.json (which lives inside the seekapa worktree at $HOME).
# Requires: az login session active, uvx on PATH.

VAULT="Shoval"
# SECRET_NAME, not SECRET: the vault entry name, never the token. See the
# elevenlabs launcher for the full note. "JIRA-API-KEY" is 12 characters and
# slipped under the scanner's 16-character threshold, so this file was one
# rename of a vault entry away from the same false positive, not free of it.
SECRET_NAME="JIRA-API-KEY"

if ! command -v az >/dev/null 2>&1; then
  echo "mcp-atlassian-launcher: az CLI not found on PATH" >&2
  exit 1
fi
if ! command -v uvx >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
fi

TOKEN="$(az keyvault secret show --vault-name "$VAULT" --name "$SECRET_NAME" --query value -o tsv 2>/dev/null)"
if [ -z "${TOKEN:-}" ]; then
  echo "mcp-atlassian-launcher: failed to read $SECRET_NAME from vault $VAULT (az login expired?)" >&2
  exit 1
fi

export JIRA_URL="https://qboservices.atlassian.net"
export JIRA_USERNAME="shoval.be@i-sdd.com"
export JIRA_API_TOKEN="$TOKEN"

exec uvx mcp-atlassian "$@"
