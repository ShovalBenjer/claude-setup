# Foundry and Chatwoot Alignment Plan

Date: 2026-04-16

## 1. Foundry Cleanup Plan

Problem:
- Chatwoot currently calls the project Responses API with `agent_reference.name = "seekapa"`.
- The live direct agent resolves to `seekapa:97`, which still contains the old first-turn identity flow.
- The published application `seekapa` is a different surface and is pinned to deployment `seekapa-82`.
- Repo prompt files and wiki notes do not reliably describe what Chatwoot is actually using.

Required cleanup:
1. Pick one live surface per channel and document it.
2. Treat the published application as the supported Chatwoot surface.
3. Keep the direct agent path only for channels that still depend on Foundry conversation state.
4. Add a parity check between:
   - runtime route
   - published application version
   - live direct agent version
   - prompt/tool names referenced in docs
5. Stop calling newer prompt files "active" until they exist in Foundry.

## 2. Prompt Diff Summary

Observed direct-agent behavior (`seekapa:97`):
- Time-aware greeting.
- Mandatory first-turn collection of full name and account email.
- Framed as a Chatwoot FAQ bot with no CRM access.

Desired Chatwoot behavior:
- First turn should greet and wait.
- No immediate identity collection in the same message bubble.
- Identity should be requested only when account-specific verification is actually needed.
- Any identity ask must explain why it is needed.

Guardrails implemented in code:
- Chatwoot still injects time/profile context.
- First-turn identity asks are stripped when Chatwoot already has sender profile data.
- Published application routing is preferred for Chatwoot when explicit history is supplied.

## 3. Runtime Recommendation

Recommendation:
- For Chatwoot, use the published application endpoint and send recent Chatwoot turns as explicit stateless history.
- For other channels, keep the existing project Responses API path until those channels have an equivalent history source.

Reasoning:
- The published application is the operational Foundry surface that can be versioned independently.
- The application endpoint is stateless by contract, so Chatwoot must provide prior turns itself.
- Chatwoot already has access to message history through the Chatwoot API.
- This avoids relying on stale direct-agent prompt state while preserving multi-turn behavior.

Implementation in this branch:
- `channel_router._call_agent()` now supports two modes:
  - stateful direct-agent mode
  - stateless published-application mode when explicit `message_history` is provided
- `chatwoot_handler` now serializes recent Chatwoot messages into `message_history`
- `chatwoot_handler` keeps the first-turn sanitizer as a second guard against stale prompt drift
