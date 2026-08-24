# Sales Agents Project - Claude Code Configuration

**Project**: Arabic Voice Agents for Sales/Retention Calls
**Platform**: ElevenLabs Conversational AI
**Last Updated**: 2026-01-19

---

## Quick Start

```bash
# Test current agents (v6.8)
python3 scripts/test_v6.8_a2a.py

# Create new agents
python3 scripts/create_v6.8_agents.py
```

### v6.8 Key Changes
- **Gender Fix**: Plural/formal forms (cultural respect)
- **Latency**: 70% smaller prompts, streaming level 4, eager turn-taking
- See `docs/v6.8-status-and-results.md` for full details

---

## Current State (v6.8)

### Active Agents (v6.8 - Cultural Fix + Latency Optimization)
| Agent | ID | LLM | Latency |
|-------|-----|-----|---------|
| **Maryam-Claude** | `agent_9901kfae5g8he788z86ve0p4bp2g` | Claude Sonnet 4.5 | 1798ms avg |
| Maryam-Gemini | `agent_5701kfae5dh6fgw9ezvsqvvnrqdz` | Gemini 3 Flash | 3237ms avg |
| Nouf-Claude | `agent_6201kfae5hgze9ws5f4sj5jkrdym` | Claude Sonnet 4.5 | - |
| Nouf-Gemini | `agent_4501kfae5ewmegmavr7rbk7ak3ar` | Gemini 3 Flash | - |

**Recommended**: Maryam-Claude (best Arabic, lowest latency)

### v6.8 Fixes Applied
- **Gender**: Plural/formal addressing (كيف الحال؟, الله يسعدكم)
- **Latency**: Prompt reduced 70%, streaming level 4, eager mode
- **Status**: Gender PASS, Latency IMPROVED (1798ms, target <1500ms)

---

## Project Structure

```
sales-agents/
├── config/                    # Agent configurations
│   ├── v6.8-gemini-agents.json  # ✅ Current (v6.8)
│   ├── v6.8-claude-agents.json  # ✅ Current (v6.8)
│   ├── v6.7-gemini-agents.json  # Archive
│   └── v6.7-claude-agents.json  # Archive
├── prompts/                   # System prompts
│   ├── maryam-v6.8-DEPLOYED.md  # ✅ Current - with plural forms
│   ├── nouf-v6.8-DEPLOYED.md    # ✅ Current - latency optimized
│   ├── maryam-v6.7-DEPLOYED.md  # Archive
│   └── nouf-v6.7-DEPLOYED.md    # Archive
├── scripts/                   # Automation scripts
│   ├── create_v6.8_agents.py    # ✅ Current
│   ├── test_v6.8_a2a.py         # ✅ Current
│   └── realtime_audio_processor.py
├── tests/
│   └── qa_scripts/           # QA test cases
│       └── karim_onboarding.json
├── test-results/             # Test output
│   ├── v6.8/                 # ✅ Current results
│   └── v6.7/                 # Archive
└── docs/                     # Documentation
    ├── v6.8-status-and-results.md  # ✅ Current status
    └── v6.7-status-and-next-steps.md
```

### v6.8 Prompts

**Maryam v6.8**: 4023 chars (down from 17651) with plural addressing
**Nouf v6.8**: 2696 chars (down from 8429) latency optimized

---

## Key Technical Details

### ElevenLabs API
- Base URL: `https://api.elevenlabs.io/v1`
- WebSocket: `wss://api.elevenlabs.io/v1/convai/conversation`
- Auth: `xi-api-key` header
- API Key: In `.env` as `ELEVENLABS_API_KEY`

### Voice IDs
- Nouf: `4wf10lgibMnboGJGCLrP` (Custom)
- Maryam: `a1KZUXKFVFDOb33I1uqr` (Salma Dubai)

### Safety Blocking
New agents may be auto-blocked if prompt contains sensitive content.
**Workaround**: Use v6.5.3 prompt structure as base.
See `docs/v6.7-status-and-next-steps.md` for details.

---

## Critical Rules

### DO NOT
- Create new prompts from scratch (use v6.5.3 base to avoid blocking)
- Change core persona elements without testing
- Push to GitHub (use Azure DevOps only)

### ALWAYS
- Run `test_v6.7_a2a.py` after agent changes
- Check `is_blocked_ivc` status after creation
- Document changes in relevant markdown files

---

## API Examples

### List Agents
```python
import requests
headers = {'xi-api-key': API_KEY}
resp = requests.get('https://api.elevenlabs.io/v1/convai/agents', headers=headers)
```

### Get Agent Details
```python
resp = requests.get(f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}', headers=headers)
```

### Update Agent
```python
resp = requests.patch(f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
    headers={**headers, 'Content-Type': 'application/json'},
    json={'conversation_config': {...}}
)
```

---

## Testing

### A2A Test
```bash
python3 scripts/test_v6.8_a2a.py
```

Tests:
- Latency per turn (target: <1500ms)
- Gender addressing (plural forms)
- Persona timeline ("اليوم" vs "الأسبوع اللي فات")
- App knowledge (should not ask how to open)

### Manual Test URLs (v6.8)
- [Maryam-Claude](https://elevenlabs.io/app/talk-to?agent_id=agent_9901kfae5g8he788z86ve0p4bp2g) **RECOMMENDED**
- [Maryam-Gemini](https://elevenlabs.io/app/talk-to?agent_id=agent_5701kfae5dh6fgw9ezvsqvvnrqdz)
- [Nouf-Claude](https://elevenlabs.io/app/talk-to?agent_id=agent_6201kfae5hgze9ws5f4sj5jkrdym)
- [Nouf-Gemini](https://elevenlabs.io/app/talk-to?agent_id=agent_4501kfae5ewmegmavr7rbk7ak3ar)

---

## Related Memory Entities

Query memory for:
- `sales-agents-v6.8` - Current project status
- `gender-addressing-fix` - Cultural validation research
- `latency-optimization-research` - Optimization options
- `elevenlabs-safety-blocking` - Blocking workarounds
- `qa-test-karim-script` - QA test case details
