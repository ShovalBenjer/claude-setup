#!/usr/bin/env bash
set -euo pipefail

# Pulls the ElevenLabs API key from Azure Key Vault at start time so the secret
# never lands in .mcp.json. Mirrors mcp-atlassian-launcher.sh's pattern.
# Requires: az login session active, uvx on PATH.

VAULT="kv-seekapa-apps"
# SECRET_NAME, not SECRET: this holds the vault ENTRY NAME. The key itself is
# fetched below and never stored in this file. Under the old name it matched
# this repo's own secret scanner, because `SECRET=` followed by 16 or more
# quoted characters is exactly what a real leak looks like, and it cost a
# session chasing a credential that does not exist. The scanner was right and
# the variable was misnamed, so the name moved rather than the pattern.
SECRET_NAME="ELEVENLABS-API-KEY"

if ! command -v az >/dev/null 2>&1; then
  echo "elevenlabs-mcp-launcher: az CLI not found on PATH" >&2
  exit 1
fi
if ! command -v uvx >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
fi

KEY="$(az keyvault secret show --vault-name "$VAULT" --name "$SECRET_NAME" --query value -o tsv 2>/dev/null)"
if [ -z "${KEY:-}" ]; then
  echo "elevenlabs-mcp-launcher: failed to read $SECRET_NAME from vault $VAULT (az login expired?)" >&2
  exit 1
fi

export ELEVENLABS_API_KEY="$KEY"

exec uvx elevenlabs-mcp "$@"
