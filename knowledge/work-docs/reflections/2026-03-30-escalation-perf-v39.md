# Reflection: Signal-Driven Escalation + Prompt v39 + CI Overhaul
**Date:** 2026-03-30
**PR:** #101 (merged to stage), #102 (merged to master)
**Builds:** #11112, #11113, #11117 -- all succeeded

---

## Part 1: Test Evidence

```
$ python3 tests/live_bot_test.py
RESULTS: 15/15 passed
ALL TESTS PASSED
```

Unit tests: 82 passed (0.17s)
Live tests: 15/15 against deployed webhook

## Part 2: Honest Completion

```
HONEST COMPLETION: 85%

WORKING (85%):
- Signal-driven escalation deployed (status gate, customer phrases, disconnect)
- Prompt v39 deployed to Foundry (Nisreen, exact keywords, no concept matching)
- Sender context enrichment (name/email from Chatwoot payload)
- Pipeline rewritten with service principal deploy (no more username/password)
- Pipeline triggers on feature/* branches
- Post-deploy smoke tests
- CI variable group configured with real Foundry API key
- Wiki updated: main page, Architecture, Deployment
- Live test suite: 15/15 passing
- Test skill created: .claude/skills/test-bot-telegram/skill.md
- All branches synced (master + stage), merged branches cleaned up

SCAFFOLDED (10%):
- Codex CI reviewer: API key configured but codexAgentId empty (uses fallback)
- Telegram channel plugin: not configured yet (can't auto-test via Telegram)
- Wiki subpages: Getting-Started and Compliance not updated yet

MISSING (5%):
- API documentation (Scalar/OpenAPI style) for Azure Functions endpoints
- Interactive architecture diagram update (system-arch-interactive.html)
- Conversation logic flow documentation per doc-design.md standard
- urllib3 connection pooling for channel_router (deferred)
```

## Part 3: Key Revelations

1. **Prompt v39 works independently of code deploy.** Tests 1,2 passed even before code deploy because the Foundry agent prompt was updated. The prompt is the primary control surface.

2. **Status gate is the most impactful code change.** Conversation 44 was stuck in "open" status -- the new gate correctly prevented the bot from responding, which is the "bot stops after transfer" behavior Nes requested.

3. **Pipeline credentials were the real blocker.** Build #11101 failed not due to code issues but because `funcDeployUser`/`funcDeployPassword` were "placeholder". Yasha's pipeline YAML with `AzureCLI@2` + service principal was the correct fix.

4. **The circular escalation loop was real and measurable.** Old code: bot says "human agent" in response → code detects keyword → sends SECOND escalation message. Fixed by checking customer message instead of bot response.

## Part 4: Concealment

1. **We never verified the bot's actual response TEXT in live tests.** The 404 errors (fake conversation IDs) mean Chatwoot can't deliver the reply. We verified the webhook processed correctly, but didn't read the agent's actual response content. Need Telegram channel testing for that.

2. **The Foundry agent inference time wasn't measured.** We estimated 80% token reduction (11K→2K) would speed things up, but have no before/after latency data.

3. **`_should_escalate` still scans bot response.** If prompt v39 ever uses "human agent" in a response, the code will toggle to open. This coupling remains.
