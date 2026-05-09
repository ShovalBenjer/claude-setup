# Debug Handover: Agent Not Calling CRM Tools

**Date**: 2026-01-12
**Issue**: CS agents in Teams not calling CRM data lookup tools despite API working

## Problem Summary

When user provides account number in ACC format (e.g., "ACC20761122"), the agent:
- Does NOT call `get_client_by_account_no` tool
- Instead asks for login ID or email
- Says "I don't have your personal account data"

## What Was Verified Working

### CRM API Endpoints (100% confirmed working)
```bash
# Test command - returns full client data
curl -X POST "https://axia-seekapa-crm.azurewebsites.net/api/get-client-by-account-no" \
  -H "Content-Type: application/json" \
  -H "x-functions-key: <FUNC_KEY>" \
  -d '{"brand": "axia", "account_no": "ACC20761122"}'

# Result: SUCCESS - Returns Amitush cohen, amit.co@zonlineltd.com
```

### All Test Accounts Found
| Account | Brand | Name | API Status |
|---------|-------|------|------------|
| ACC20761122 | **axia** | Amitush cohen | ✓ Works |
| ACC30176418 | seekapa | Yousef E M A Alazmi | ✓ Works |
| ACC30105937 | seekapa | Kais F Al Kotamy | ✓ Works |
| ACC30108247 | seekapa | Abdullah Ali M Khurayzi | ✓ Works |

### Fix Applied
Removed `test_user` filter from `shared/crm_mysql_client.py` queries. This was excluding accounts with high accountids.

## Possible Root Causes (To Investigate)

### 1. Agent Prompt Not Deployed to Azure AI Foundry
- Updated prompts are at:
  - `agent-prompts/seekapa-system-prompt-v33-testing.md`
  - `agent-prompts/axia-cs-system-prompt-v26-testing.md`
- **Check**: Was the updated prompt actually uploaded to Azure AI Foundry agent configuration?

### 2. OpenAPI Spec Not Linked to Agent
- Updated specs are at:
  - `azure-function-crm/openapi-spec-seekapa-final.json`
  - `azure-function-crm/openapi-spec-axia-final.json`
- **Check**: Is the OpenAPI spec properly linked as the agent's tool definitions?
- **Check**: Does the agent have `get_client_by_account_no` as an available tool?

### 3. Brand Mismatch in Testing
- User tested Seekapa agent with ACC20761122
- ACC20761122 is an **AXIA** account
- Seekapa agent is hardcoded to use `brand: "seekapa"`
- **Action**: Test Seekapa agent with Seekapa accounts (ACC30176418, ACC30105937)
- **Action**: Test Axia agent with Axia account (ACC20761122)

### 4. Tool Invocation Instructions Not Clear Enough
The prompt Phase B says:
```
**Option 1 - Account Number (ACC format like ACC30176418):**
1. **Immediately** call `get_client_by_account_no(brand="seekapa", account_no="ACC30176418")`
```
- **Check**: Is the agent actually seeing this instruction?
- **Check**: Is there conflicting guidance elsewhere in the prompt?

## Debug Steps

### Step 1: Verify Agent Configuration in Azure AI Foundry
1. Go to Azure AI Foundry portal
2. Open the Seekapa agent configuration
3. Check:
   - System prompt content - does it match v33-testing?
   - Tools/Actions - is `get_client_by_account_no` listed?
   - OpenAPI spec - is it the latest version?

### Step 2: Test with Correct Brand Matching
- Seekapa agent + Seekapa account: ACC30176418
- Axia agent + Axia account: ACC20761122

### Step 3: Check Agent Logs
- Azure AI Foundry should have conversation logs
- Look for:
  - Was a tool call attempted?
  - What error occurred if so?
  - What was the agent's reasoning?

### Step 4: Verify OpenAPI Spec Upload
The spec should include:
```json
"/api/get-client-by-account-no": {
  "post": {
    "operationId": "get_client_by_account_no",
    "summary": "Get client data by account number (ACC format)",
    ...
  }
}
```

## Files Changed Today

1. `shared/crm_mysql_client.py` - Removed test_user filters
2. `test_crm_connection/__init__.py` - Cleaned up debug code
3. `openapi-spec-seekapa-final.json` - Added get_client_by_account_no
4. `openapi-spec-axia-final.json` - Added get_client_by_account_no
5. `agent-prompts/seekapa-system-prompt-v33-testing.md` - Updated Phase B
6. `agent-prompts/axia-cs-system-prompt-v26-testing.md` - Updated Phase B + fixed URL

## Quick Test Commands

```bash
# Get function key
FUNC_KEY=$(az functionapp keys list --name axia-seekapa-crm --resource-group AZAI_group --query 'functionKeys.default' -o tsv)

# Test Seekapa account
curl -s -X POST "https://axia-seekapa-crm.azurewebsites.net/api/get-client-by-account-no" \
  -H "Content-Type: application/json" -H "x-functions-key: $FUNC_KEY" \
  -d '{"brand": "seekapa", "account_no": "ACC30176418"}'

# Test Axia account
curl -s -X POST "https://axia-seekapa-crm.azurewebsites.net/api/get-client-by-account-no" \
  -H "Content-Type: application/json" -H "x-functions-key: $FUNC_KEY" \
  -d '{"brand": "axia", "account_no": "ACC20761122"}'
```

## Key Question to Answer

**Is the updated agent prompt and OpenAPI spec actually deployed to Azure AI Foundry?**

The API backend works. The issue is likely in the agent configuration layer.
