#!/bin/bash
# Setup script for MCP server environment variables
# This script helps you configure authentication for all MCP servers

set -e

CLAUDE_CONFIG="$HOME/.claude.json"
BACKUP_CONFIG="$HOME/.claude.json.backup"

echo "======================================"
echo "MCP Server Environment Setup"
echo "======================================"
echo ""
echo "This script will help you add environment variables"
echo "to your MCP server configurations in ~/.claude.json"
echo ""

# Create backup
echo "Creating backup of ~/.claude.json..."
cp "$CLAUDE_CONFIG" "$BACKUP_CONFIG"
echo "Backup created: $BACKUP_CONFIG"
echo ""

# Helper function to add env vars using jq
add_env_vars() {
    local server_name=$1
    shift
    local env_vars=("$@")

    echo "Configuring $server_name..."

    for env_var in "${env_vars[@]}"; do
        IFS='=' read -r key value <<< "$env_var"
        if [ -n "$value" ] && [ "$value" != "your-"*"-here" ]; then
            echo "  Adding $key"
            jq --arg server "$server_name" --arg key "$key" --arg val "$value" \
                '.mcpServers[$server].env[$key] = $val' \
                "$CLAUDE_CONFIG" > "${CLAUDE_CONFIG}.tmp" && mv "${CLAUDE_CONFIG}.tmp" "$CLAUDE_CONFIG"
        fi
    done
}

# Azure configuration
if [ -f "$HOME/.claude/.env.azure" ]; then
    echo "Found .env.azure file"
    source "$HOME/.claude/.env.azure"

    if [ -n "$AZURE_SUBSCRIPTION_ID" ] && [ "$AZURE_SUBSCRIPTION_ID" != "your-subscription-id-here" ]; then
        add_env_vars "azure" \
            "AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID" \
            "AZURE_TENANT_ID=$AZURE_TENANT_ID" \
            "AZURE_CLIENT_ID=$AZURE_CLIENT_ID" \
            "AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET"
        echo "✓ Azure configured"
    else
        echo "⚠ Azure credentials not set in .env.azure"
    fi
    echo ""
fi

# Azure DevOps configuration
if [ -f "$HOME/.claude/.env.azdo" ]; then
    echo "Found .env.azdo file"
    source "$HOME/.claude/.env.azdo"

    if [ -n "$AZDO_PAT" ] && [ "$AZDO_PAT" != "your-pat-token-here" ]; then
        add_env_vars "azure-devops" \
            "AZURE_DEVOPS_ORG=$AZURE_DEVOPS_ORG" \
            "AZURE_DEVOPS_PROJECT=$AZURE_DEVOPS_PROJECT" \
            "AZDO_PAT=$AZDO_PAT"
        echo "✓ Azure DevOps configured"
    else
        echo "⚠ Azure DevOps credentials not set in .env.azdo"
    fi
    echo ""
fi

# ElevenLabs configuration
if [ -f "$HOME/.claude/.env.elevenlabs" ]; then
    echo "Found .env.elevenlabs file"
    source "$HOME/.claude/.env.elevenlabs"

    if [ -n "$ELEVENLABS_API_KEY" ] && [ "$ELEVENLABS_API_KEY" != "your-api-key-here" ]; then
        add_env_vars "elevenlabs" \
            "ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY"
        echo "✓ ElevenLabs configured"
    else
        echo "⚠ ElevenLabs API key not set in .env.elevenlabs"
    fi
    echo ""
fi

# Trello configuration
if [ -f "$HOME/.claude/.env.trello" ]; then
    echo "Found .env.trello file"
    source "$HOME/.claude/.env.trello"

    if [ -n "$TRELLO_API_KEY" ] && [ "$TRELLO_API_KEY" != "your-api-key-here" ]; then
        trello_vars=(
            "TRELLO_API_KEY=$TRELLO_API_KEY"
            "TRELLO_TOKEN=$TRELLO_TOKEN"
        )

        # Add optional vars if set
        if [ -n "$TRELLO_BOARD_ID" ] && [ "$TRELLO_BOARD_ID" != "your-board-id-here" ]; then
            trello_vars+=("TRELLO_BOARD_ID=$TRELLO_BOARD_ID")
        fi
        if [ -n "$TRELLO_WORKSPACE_ID" ] && [ "$TRELLO_WORKSPACE_ID" != "your-workspace-id-here" ]; then
            trello_vars+=("TRELLO_WORKSPACE_ID=$TRELLO_WORKSPACE_ID")
        fi

        add_env_vars "trello" "${trello_vars[@]}"
        echo "✓ Trello configured"
    else
        echo "⚠ Trello credentials not set in .env.trello"
    fi
    echo ""
fi

echo "======================================"
echo "Configuration complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit the .env.* files in ~/.claude/ with your actual credentials"
echo "2. Run this script again to apply the configuration"
echo "3. Verify with: claude mcp list"
echo ""
echo "Environment files:"
echo "  - ~/.claude/.env.azure (Azure)"
echo "  - ~/.claude/.env.azdo (Azure DevOps)"
echo "  - ~/.claude/.env.elevenlabs (ElevenLabs)"
echo "  - ~/.claude/.env.trello (Trello)"
echo ""
