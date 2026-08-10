# CS Agents - Architecture (LIGHT)

## 1. Quick Overview

**Purpose**: Email OTP authentication and CRM data access for Seekapa and Axia customer service AI agents hosted on Azure AI Foundry.

**Tech Stack**:
- Backend: Python, Azure Functions v1
- CRM Database: SQL Server (`azvmsqlpowerbi.database.windows.net` / `AZDBSQLPowerBI`)
- Email: Azure Communication Services (OTP delivery)
- AI Platform: Azure AI Foundry (conversational agents)
- Agent Prompts: Seekapa v27+, AxiaCS v20+ (stored in `agent-prompts/`)

**Key Features**:
- 6-digit OTP authentication with 5-minute expiration
- CRM customer data retrieval post-authentication
- Test framework for agent evaluation (`tests/`)
- Knowledge base testing (`tests/test_data/`)

**Production URL**: https://axia-seekapa-crm.azurewebsites.net

## 2. API & Integration

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/send-otp` | POST | Function Key | Generate and send 6-digit OTP to customer email |
| `/api/verify-otp` | POST | Function Key | Validate OTP and return customer data from CRM |
| `/api/get-customer-data` | POST | Function Key | Legacy auth method (login + email, kept for reference) |

### Authentication Flow

```
Customer -> "I need help with my account"
  -> Agent collects email + login ID
  -> send_otp() generates code -> sends to email
  -> Customer provides OTP code
  -> verify_otp() validates -> returns CRM customer data
  -> Agent helps with account-specific questions
```

### External Services

| Service | Purpose | Auth |
|---------|---------|------|
| Azure AI Foundry | Hosts Seekapa + Axia conversational agents | Foundry configuration |
| Azure Communication Services | Sends OTP emails | Connection string in Key Vault |
| CRM SQL Server | Customer data (`[XPORT].[Customer_Support1]`) | SQL connection string |

### Tool Definitions

The file `azure-function-crm/tool-definitions.json` defines the function calling interface used by Azure AI Foundry agents to invoke the OTP and customer data functions.

## 3. Infrastructure

### Azure Resources

| Resource | Name | Type |
|----------|------|------|
| Function App | `axia-seekapa-crm` | Azure Functions (Consumption) |
| CRM Database | `azvmsqlpowerbi.database.windows.net` | SQL Server |
| Key Vault | `kv-seekapa-apps` | Secrets management |

### Deployment

```bash
# Deploy Azure Functions
cd azure-function-crm
func azure functionapp publish axia-seekapa-crm --python

# Get function key
az functionapp keys list \
  --resource-group AZAI_group \
  --name axia-seekapa-crm \
  --query "functionKeys.default" -o tsv
```

### Key Vault Secrets

| Secret | Purpose |
|--------|---------|
| `Chatbot-DbConnectionString` | CRM SQL Server connection |
| Azure Communication Services connection string | OTP email delivery |

### Repository

Azure DevOps: https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents
