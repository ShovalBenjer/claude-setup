# AI Foundry Connection Update Report

**Date**: 2026-02-03
**Task**: Update CustomKeys connections for CRM APIs in Azure AI Foundry

## Summary

Successfully updated both CRM API connections with proper credentials using Azure REST API.

## What Worked ✅

### 1. Connection Creation with PUT
```bash
az rest --method PUT \
  --url "https://management.azure.com/.../connections/{name}?api-version=2025-06-01" \
  --body '{
    "properties": {
      "authType": "CustomKeys",
      "category": "CustomKeys",
      "target": "https://axia-seekapa-crm.azurewebsites.net",
      "credentials": {
        "keys": {
          "x-functions-key": "<REDACTED>"
        }
      },
      "metadata": {
        "type": "openapi"
      }
    }
  }'
```

### 2. Credential Verification via listSecrets
```bash
az rest --method POST \
  --url "https://management.azure.com/.../connections/{name}/listSecrets?api-version=2025-06-01"
```
This endpoint returns the actual credentials (unlike GET which returns `credentials: null` for security).

### 3. Delete and Recreate Strategy
When updating existing connections with missing credentials:
1. DELETE the old connection
2. PUT a new connection with credentials in one call
3. Verify with listSecrets

### 4. API Version
**2025-06-01** works correctly for all operations (GET, PUT, DELETE, listSecrets).

## What Didn't Work ❌

### 1. PATCH for Credential Updates
PATCH operations accepted the payload but credentials remained null. PATCH only updated `target` but not `credentials`.

### 2. Alternative Credential Structures
These formats were rejected:
```json
// Flat structure (rejected with ValidationError)
"credentials": {
  "x-functions-key": "value"
}

// Nested with explicit key property (deserialization error)
"credentials": {
  "keys": {
    "x-functions-key": {
      "key": "value"
    }
  }
}
```

### 3. Connection Names with Underscores
`axia_crm_api` failed with:
```
Error Code: BadParameter
Error Message: The request URI contains an invalid name: axia_crm_api
Target: keyvault
```

**Reason**: AI Foundry stores credentials in Key Vault, which only allows alphanumerics and hyphens.

### 4. Other API Versions Tested
- **2025-07-01-preview**: Same behavior as 2025-06-01 (credentials accepted but shown as null in GET)
- **2025-09-01**: Not tested after finding 2025-06-01 works
- **2025-10-01-preview**: Not tested after finding 2025-06-01 works

## Final Configuration

### seekapa_crm_api
- **Name**: `seekapa_crm_api`
- **Target**: `https://axia-seekapa-crm.azurewebsites.net`
- **Auth Type**: CustomKeys
- **Credential Key**: `x-functions-key`
- **Credential Value**: `<REDACTED>`
- **Status**: ✅ Verified via listSecrets

### axia-crm-api (renamed from axia_crm_api)
- **Name**: `axia-crm-api` (changed from `axia_crm_api` due to underscore restriction)
- **Target**: `https://axia-seekapa-crm.azurewebsites.net`
- **Auth Type**: CustomKeys
- **Credential Key**: `x-functions-key`
- **Credential Value**: `<REDACTED>`
- **Status**: ✅ Verified via listSecrets

## Key Learnings

1. **Security by Design**: GET operations intentionally return `credentials: null`. Use `listSecrets` POST endpoint to verify.

2. **Credential Format**: The correct structure is:
   ```json
   "credentials": {
     "keys": {
       "header-name": "value"
     }
   }
   ```

3. **Naming Constraints**: Connection names must be Key Vault compatible (alphanumerics and hyphens only).

4. **Update Strategy**: For connections with missing credentials, DELETE + PUT is more reliable than PATCH.

5. **Verification**: Always verify with `listSecrets` after creating/updating connections.

## Session 2026-02-04 Updates

### Connection Name Fix
- AxiaCS agent referenced `axia_crm_api` (underscore) but session 2026-02-03 created `axia-crm-api` (hyphen)
- Created new `axia_crm_api` connection matching agent expectation — **fixed 400 missing_required_parameter error**
- Note: underscores DO work in connection names (contrary to earlier report about Key Vault restrictions)

### Three connections now exist:
| Name | Created | Status |
|------|---------|--------|
| `seekapa_crm_api` | 2026-02-03 | ✅ Active, used by Seekapa agent |
| `axia_crm_api` | 2026-02-04 | ✅ Active, used by AxiaCS agent |
| `axia-crm-api` | 2026-02-03 | ⚠️ Orphan (not referenced by any agent) |

### Model Change
- Both agents switched from `gpt-5.1-23` → `gpt-5` in portal
- gpt-5.1 has known openapi tool calling regression (never calls openapi tools)
- gpt-5 IS in the function calling support table
- Portal settings: Text format, Let model choose, Medium reasoning

### OpenAPI Spec Update
- Added `"security": [{"apiKey": []}]` at global level to both specs
- Updated specs uploaded to portal for both agents

### Fallback Plan Verified
- Raw Responses API (brn-azai.openai.azure.com/openai/v1/responses) works with `type: function` tools
- Full round-trip proven: model→function call→CRM HTTP→feed result→model presents data
- Token scope for raw API: `https://cognitiveservices.azure.com/.default`

## Commands Reference

```bash
# List all connections
az rest --method GET \
  --url "https://management.azure.com/subscriptions/08b0ac81-a17e-421c-8c1b-41b59ee758a3/resourceGroups/AZAI_group/providers/Microsoft.CognitiveServices/accounts/brn-azai/projects/seekapa_ai/connections?api-version=2025-06-01"

# Get specific connection
az rest --method GET \
  --url "https://management.azure.com/.../connections/{name}?api-version=2025-06-01"

# Verify credentials
az rest --method POST \
  --url "https://management.azure.com/.../connections/{name}/listSecrets?api-version=2025-06-01"

# Delete connection
az rest --method DELETE \
  --url "https://management.azure.com/.../connections/{name}?api-version=2025-06-01"

# Create/Update connection
az rest --method PUT \
  --url "https://management.azure.com/.../connections/{name}?api-version=2025-06-01" \
  --body @connection-payload.json
```
