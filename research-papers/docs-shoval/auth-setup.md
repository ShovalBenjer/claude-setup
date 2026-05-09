# CS Agent Authentication Setup Guide

This document describes how to set up the signed token authentication system for CS Agents.

## Overview

The authentication system uses HMAC-SHA256 signed tokens to:
- Prevent login ID guessing attacks
- Ensure only authenticated users can access their CRM data
- Support multiple channels (web widget, mobile app, Telegram, WhatsApp)

## Architecture

```
Parent App (Web/Mobile) ──────┐
                              │
                              ▼
                   /api/generate-signed-link
                              │
                              ▼
                       Signed Token
                   (login_timestamp_signature)
                              │
    ┌─────────────────────────┼─────────────────────────┐
    ▼                         ▼                         ▼
Web Widget              Telegram Bot             WhatsApp Bot
(postMessage)           (/start token)           (deep link)
    │                         │                         │
    └─────────────────────────┼─────────────────────────┘
                              │
                              ▼
                     /api/validate-token
                              │
                              ▼
                   CS Agent (session-locked)
                              │
                              ▼
                       CRM Data Access
```

## Prerequisites

- Azure CLI installed and logged in
- Access to Azure Key Vault `kv-seekapa-apps`
- Access to Azure Function App `azure-function-crm`

## Step 1: Generate the Signing Key

Generate a cryptographically secure 256-bit (32-byte) key:

```bash
# Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Or using OpenSSL
openssl rand -hex 32
```

**Example output:** `a1b2c3d4e5f6...` (64 hexadecimal characters)

**IMPORTANT:**
- Save this key securely - you'll need it for Key Vault
- Do NOT commit this key to source control
- Do NOT share this key in plain text

## Step 2: Add Secret to Azure Key Vault

```bash
# Set the secret in Key Vault
az keyvault secret set \
  --vault-name kv-seekapa-apps \
  --name CS-AGENTS-LINK-SIGNING-KEY \
  --value "YOUR_GENERATED_KEY_HERE"

# Verify the secret was created
az keyvault secret show \
  --vault-name kv-seekapa-apps \
  --name CS-AGENTS-LINK-SIGNING-KEY \
  --query "id" -o tsv
```

## Step 3: Configure Azure Function App

Add the Key Vault reference to the Function App configuration:

```bash
# Get the Key Vault secret URI
SECRET_URI=$(az keyvault secret show \
  --vault-name kv-seekapa-apps \
  --name CS-AGENTS-LINK-SIGNING-KEY \
  --query "id" -o tsv)

# Add as app setting with Key Vault reference
az functionapp config appsettings set \
  --name azure-function-crm \
  --resource-group AZAI_group \
  --settings "CS_AGENTS_LINK_SIGNING_KEY=@Microsoft.KeyVault(SecretUri=${SECRET_URI})"
```

**Alternative (Azure Portal):**

1. Go to Azure Portal → Function App → Configuration
2. Add new application setting:
   - Name: `CS_AGENTS_LINK_SIGNING_KEY`
   - Value: `@Microsoft.KeyVault(SecretUri=https://kv-seekapa-apps.vault.azure.net/secrets/CS-AGENTS-LINK-SIGNING-KEY/)`
3. Save and restart the Function App

## Step 4: Grant Function App Access to Key Vault

Ensure the Function App has permission to read secrets:

```bash
# Get the Function App's managed identity principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --name azure-function-crm \
  --resource-group AZAI_group \
  --query principalId -o tsv)

# Grant secret read access
az keyvault set-policy \
  --name kv-seekapa-apps \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get
```

## Step 5: Deploy Updated Functions

After the above setup, deploy the updated Azure Functions:

```bash
cd azure-function-crm
func azure functionapp publish azure-function-crm
```

## Step 6: Verify Deployment

Test the generate-signed-link endpoint:

```bash
# Get the function key
FUNCTION_KEY=$(az functionapp keys list \
  --name azure-function-crm \
  --resource-group AZAI_group \
  --query "functionKeys.default" -o tsv)

# Test generate signed link
curl -X POST "https://azure-function-crm.azurewebsites.net/api/generate-signed-link?code=${FUNCTION_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"login": 5844134, "brand": "seekapa"}'
```

Expected response:
```json
{
  "success": true,
  "signed_token": "5844134_1737190920_abc123def456",
  "login": 5844134,
  "brand": "seekapa",
  "expires_at": "2026-01-19T09:22:00+00:00",
  "links": {
    "telegram": "https://t.me/SeekApaBot?start=5844134_1737190920_abc123def456",
    "whatsapp": "https://wa.me/123456?text=start_5844134_1737190920_abc123def456",
    "web_widget": "5844134_1737190920_abc123def456"
  }
}
```

Test the validate-token endpoint:

```bash
curl -X POST "https://azure-function-crm.azurewebsites.net/api/validate-token?code=${FUNCTION_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"signed_token": "5844134_1737190920_abc123def456", "brand": "seekapa"}'
```

## Web Widget Integration

To integrate with a web chat widget, use postMessage to pass the token:

```javascript
// In the parent app (after user login)
async function openChatWidget(userLogin) {
  // 1. Generate signed link from your backend
  const response = await fetch('/api/chat/generate-link', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login: userLogin, brand: 'seekapa' })
  });
  const { signed_token } = await response.json();

  // 2. Open chat widget
  const chatFrame = document.getElementById('chat-widget');
  chatFrame.src = 'https://chat.seekapa.com/widget';

  // 3. Pass token via postMessage when iframe loads
  chatFrame.onload = () => {
    chatFrame.contentWindow.postMessage({
      type: 'SESSION_INIT',
      signed_token: signed_token,
      brand: 'seekapa'
    }, 'https://chat.seekapa.com');
  };
}
```

## Telegram Bot Integration

Configure the bot to handle start parameters:

```python
# In your Telegram bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    # Extract token from /start command
    # Format: /start 5844134_1737190920_abc123def456
    args = message.text.split(' ', 1)
    if len(args) > 1:
        signed_token = args[1]
        # Pass to CS Agent session context
        session_context = {
            'signed_token': signed_token,
            'brand': 'seekapa'  # or 'axia'
        }
        start_agent_session(message.chat.id, session_context)
```

## Security Considerations

### Token Expiration
- Default TTL: 24 hours
- Maximum TTL: 7 days
- Expired tokens are rejected with clear error message

### Link Sharing Risk
- Telegram/WhatsApp links can be shared
- Tokens expire, limiting exposure window
- For highly sensitive operations, escalate to human support

### Key Rotation
To rotate the signing key:
1. Generate new key
2. Update Key Vault secret
3. Restart Function App
4. Old tokens become invalid immediately

### Monitoring
Monitor for:
- High rate of invalid signature errors (potential attack)
- High rate of expired token errors (links being shared)
- Token generation without subsequent validation (potential link harvesting)

## Troubleshooting

### "Service not configured" Error
- Check that `CS_AGENTS_LINK_SIGNING_KEY` is set in Function App settings
- Verify Key Vault reference syntax
- Check Function App has Key Vault access

### "Invalid signature" Error
- Verify the same key is used for generation and validation
- Check brand parameter matches
- Ensure token hasn't been modified

### "Token expired" Error
- Generate a fresh token
- Check TTL settings (default 24h)
- Verify server clocks are synchronized

## Files Modified

| File | Purpose |
|------|---------|
| `azure-function-crm/shared/link_signing.py` | HMAC signing/validation |
| `azure-function-crm/generate_signed_link/__init__.py` | Token generation endpoint |
| `azure-function-crm/generate_signed_link/function.json` | Function config |
| `azure-function-crm/validate_token/__init__.py` | Token validation (updated) |
| `agent-prompts/seekapa-system-prompt-v34.md` | Seekapa prompt with session lock |
| `agent-prompts/axia-cs-system-prompt-v27.md` | Axia prompt with session lock |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-18 | Initial implementation |
