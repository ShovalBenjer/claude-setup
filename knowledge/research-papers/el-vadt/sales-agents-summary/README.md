# Sales Agents - Maryam Al-Rashid Voice Agent

## Overview

Production-ready Arabic voice agent for relationship restoration with former trading platform clients. Built on ElevenLabs Conversational AI.

## Current Version: v2.3 - Agent A (GPT-5.1) Selected ★

| Metric | Value |
|--------|-------|
| **Human-Likeness Score** | 63/70 (90%) |
| **Production Agent** | Agent A (GPT-5.1) |
| **Backup Agent** | Agent B (Claude Haiku) |
| **Next Goal** | 90/100 per dimension |

### Agent IDs
| Agent | ID | LLM | Status |
|-------|----|----|--------|
| **A** | `agent_6101kepwsqdyefw81dfdwn1g44a7` | gpt-5.1 | ★ PRODUCTION |
| B | `agent_2501kepwtp39e5jtjksamgvpb8dg` | claude-haiku-4-5 | Backup |
| C | `agent_3101kepwsszmezgazvxpb1qyqp7z` | gemini-2.0-flash | Eliminated |
| D | `agent_1701kepwstw5e2z9m9xng5xzrdat` | claude-sonnet-4 | Eliminated |

### Test Links
- **Agent A (Winner)**: https://elevenlabs.io/app/talk-to-agent/agent_6101kepwsqdyefw81dfdwn1g44a7
- **Agent B (Backup)**: https://elevenlabs.io/app/talk-to-agent/agent_2501kepwtp39e5jtjksamgvpb8dg

---

## Key Features

### Behavioral Constraints (Section 0)
- Maximum 2 sentences per response
- ONE idea per response - never list options
- Natural fillers: "إيه..."، "يعني..."، "شوف..."
- Anti-repetition enforcement

### Identity
- Maryam Al-Rashid, 38 years old, from Abu Dhabi
- Client Relationship Consultant at Seekapa
- Licensed trading platform representative

### Ethical Framework
- Permission gates before advancing conversation
- Time-boxed rapport (3-5 minutes max)
- Crisis response protocol (mental health support line: 920033360)
- 72-hour no-sell vulnerability firewall
- Transparent purpose (never claim "not a sales call")

### 7-Pillar Evaluation Framework
1. **Trust Building** - Rapport before business
2. **Shame Awareness** - Avoid shame about past losses
3. **Permission Seeking** - Consent before advancing
4. **No Pressure** - Zero FOMO/urgency tactics
5. **Empathy** - Genuine emotional connection with pauses
6. **Human Feeling** - Natural, non-robotic speech
7. **Outcome** - Positive next step or preserved relationship

---

## Project Structure

```
sales-agents/
├── config/
│   ├── created_agents.json      # Agent IDs, test results, winner
│   ├── agent-variants.json      # All 4 agent configurations
│   ├── agent-info.json          # Current active agent settings
│   └── elevenlabs-settings.json # API reference settings
├── prompts/
│   ├── system-prompt.md         # Full Maryam persona (English)
│   └── system-prompt-arabic.md  # Arabic version
├── scripts/
│   ├── create_elevenlabs_agents.py  # Create agents via API
│   └── run_agent_tests.py           # Run 16 test simulations
├── test-results/
│   ├── test_results_*.json      # Raw test data
│   └── analysis_summary.md      # 7-pillar scoring analysis
├── docs/
│   └── SESSION_HANDOVER_*.md    # Session handover documents
├── data-inputs/
│   ├── qc-success-calls.json    # 102 QC-analyzed calls
│   └── grade-b-call-*.txt       # Sample successful calls
├── exports/
│   ├── maryam_positive.jsonl    # Training pairs (positive)
│   └── maryam_full.json         # Full training data
└── src/
    └── training/
        └── extractor.py         # Training pair extraction
```

---

## ElevenLabs Configuration (Agent A)

### LLM
- Model: `gpt-5.1`
- Temperature: 0.35
- Max Tokens: unlimited

### TTS (Voice)
- Model: `eleven_turbo_v2_5`
- Voice: Salma (`a1KZUXKFVFDOb33I1uqr`) - Dubai Female
- Stability: 0.42
- Similarity Boost: 0.80
- Speed: 0.90

### ASR (Recognition)
- Provider: ElevenLabs
- Quality: High
- Keywords: 43 Arabic phrases including crisis detection

### Turn Settings
- Timeout: 12 seconds
- Mode: Turn-based
- Eagerness: Patient (no interruptions)
- Max Duration: 60 minutes

---

## Test Results Summary (2026-01-11)

### 7-Pillar Scores
| Pillar | Agent A | Agent B | Agent C |
|--------|---------|---------|---------|
| Trust Building | 9/10 | 9/10 | 3/10 |
| Shame Awareness | 8/10 | 10/10 | 2/10 |
| Permission Seeking | 10/10 | 8/10 | 4/10 |
| No Pressure | 8/10 | 10/10 | 5/10 |
| Empathy | 9/10 | 10/10 | 2/10 |
| Human Feeling | 9/10 | 10/10 | 3/10 |
| Outcome | 10/10 | 7/10 | 1/10 |
| **TOTAL** | **63/70** | **64/70** | **20/70** |

### Why Agent A Won
1. **Cultural Dua Response**: Immediate "الله يعوضك" on hearing loss
2. **Empathy + Competence Balance**: Validates then offers handrail
3. **Outcome Focus**: Booked consultation vs. therapy loop

### Why Agent C Failed
- Asked for Kunya BEFORE acknowledging client's pain
- "Slot-filling" behavior destroyed rapport instantly

---

## Quick Start

### Run Automated Tests
```bash
export ELEVENLABS_API_KEY="your-key-here"
python3 scripts/run_agent_tests.py
```

### Create New Agents
```bash
python3 scripts/create_elevenlabs_agents.py
```

### Update Agent Settings
```bash
curl -X PATCH "https://api.elevenlabs.io/v1/convai/agents/{agent_id}" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"conversation_config": {...}}'
```

---

## Regulatory Compliance

| Requirement | Implementation |
|-------------|----------------|
| DFSA/SCA Clear & Fair | Section 0 anti-manipulation rules |
| SAMA Explainable AI | Permission gates, suitability checks |
| GFIN Vulnerable Clients | Crisis protocol, 72-hour firewall |
| Risk Disclosure | Mandatory before trading discussion |

---

## Session History

| Date | Goal | Result |
|------|------|--------|
| 2026-01-11 | Create & test 4 variants | Agent A selected (63/70) |

---

## Next Steps

1. Improve Agent A to 90/100 per dimension
2. Add more empathy pauses (learn from Agent B)
3. Test with native Khaleeji speakers
4. Consider Professional Voice Clone
5. Set up production webhooks

---

## Related Projects

- **QC Call Analyzer**: Quality analysis of sales calls
- **Seekapa Training Platform**: Agent training system
- **Retention Agents**: Doctor persona (reference for good patterns)

## License

Proprietary - Seekapa/Corp-domain

---

*Maryam Al-Rashid: شغلك مو تبيعين. شغلك تعطينهم طريق كريم يرجعون منه.*
*(Your job is not to sell. Your job is to give them an honorable path back.)*
