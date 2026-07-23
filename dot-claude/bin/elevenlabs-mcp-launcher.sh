#!/usr/bin/env bash
set -euo pipefail

# Pulls the ElevenLabs API key from Azure Key Vault at start time so the secret
# never lands in .mcp.json. Mirrors mcp-atlassian-launcher.sh's pattern.
# Requires: az login session active, uvx on PATH.

VAULT="kv-seekapa-apps"
SECRET="ELEVENLABS-API-KEY"

if ! command -v az >/dev/null 2>&1; then
  echo "elevenlabs-mcp-launcher: az CLI not found on PATH" >&2
  exit 1
fi
if ! command -v uvx >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
fi

KEY="$(az keyvault secret show --vault-name "$VAULT" --name "$SECRET" --query value -o tsv 2>/dev/null)"
if [ -z "${KEY:-}" ]; then
  echo "elevenlabs-mcp-launcher: failed to read $SECRET from vault $VAULT (az login expired?)" >&2
  exit 1
fi

export ELEVENLABS_API_KEY="$KEY"

exec uvx elevenlabs-mcp "$@"
