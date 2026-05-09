# Plan: KB Replacement & Test Optimization

**Created**: 2025-12-14
**Status**: Ready for execution
**Priority**: High

---

## Executive Summary

Multi-LLM consensus (GPT-5 Pro, Gemini Pro, GPT-5): **Stick with GPT-5.1** for now while focusing on KB replacement and test updates. GPT-5.2 over-escalates and requires prompt tuning AFTER the new KB is in place.

### Current Test Results (GPT-5.1 vs GPT-5.2)
| Suite | GPT-5.1 | GPT-5.2 |
|-------|---------|---------|
| E2E | 156/166 (94.0%) | 137/166 (82.5%) |
| Escalation | 13/15 (86.7%) | 13/15 (86.7%) |
| Advanced | 48/62 (77.4%) | 45/62 (72.6%) |
| **TOTAL** | **217/243 (89.3%)** | **195/243 (80.2%)** |

**Decision**: Use GPT-5.1 for production. Tune GPT-5.2 later after KB is updated.

---

## Phase 1: Revert Agents to GPT-5.1 (Immediate)

### Task 1.1: Update Agent Models
Both agents are currently on GPT-5.2. Revert to GPT-5.1:

```bash
# Use Azure AI Foundry Portal or SDK to update:
# - seekapa: gpt-5.2 -> gpt-5.1
# - AxiaCS: gpt-5.2 -> gpt-5.1
```

**Azure AI Foundry Portal**:
1. Go to https://ai.azure.com
2. Navigate to Project: `seekapa_ai`
3. Go to Agents section
4. Edit each agent (seekapa, AxiaCS)
5. Change model from `gpt-5.2` to `gpt-5.1`
6. Save and deploy new version

---

## Phase 2: Replace Knowledge Base

### Task 2.1: Upload New KB to Vector Store

**New KB File**: `/home/odedbe/projects/axia-seekapa-cs-agents/Seekapa_FAQ_KB.pdf`
- 24 questions covering: Withdrawals, Deposits, KYC/AML, Fees, Trading Conditions, Bonuses, Complaints, Regulation, Privacy
- Source: `Seekapa_FAQ_KB.docx` (converted to PDF)

**Steps**:
1. Go to Azure AI Foundry Portal
2. Navigate to Project: `seekapa_ai`
3. Go to Vector Stores / File Search
4. Current vector stores:
   - `vs_BhDnWqMdIsxjgv1f0sQOuwX6` (seekapa)
   - `vs_IBlcKLyVYgTK2axc8fzTnAb8` (AxiaCS)
5. Upload `Seekapa_FAQ_KB.pdf` to BOTH vector stores (same KB for both agents)
6. Delete old KB files from vector stores

### Task 2.2: Verify KB Integration
```bash
cd /home/odedbe/projects/axia-seekapa-cs-agents/tests
# Test a few KB questions manually
python3 -c "
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

client = AIProjectClient(
    endpoint='https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai',
    credential=DefaultAzureCredential(),
)
agent = client.agents.get(agent_name='seekapa')
openai = client.get_openai_client()

# Test KB retrieval
response = openai.responses.create(
    input=[{'role': 'user', 'content': 'What is the withdrawal processing time?'}],
    extra_body={'agent': {'name': agent.name, 'type': 'agent_reference'}}
)
print(response.output_text)
"
```

---

## Phase 3: Update Test Cases

### Task 3.1: Map Old Tests to New KB
The new KB has 24 questions (Q1-Q24). Update tests to match:

| New KB Section | Old Test IDs to Update |
|----------------|----------------------|
| Withdrawals (Q1-Q3) | SEEK-KB-DEP-*, WDR-* |
| KYC/AML (Q4-Q5) | SEEK-KB-ACCT-*, ACC-* |
| Fees (Q6-Q7) | SEEK-KB-Q*, fee-related |
| Trading (Q8-Q10) | TRD-*, leverage/margin tests |
| Bonuses (Q11-Q13) | bonus-related tests |
| Alerts/Social (Q14-Q15) | social trading tests |
| Complaints (Q16) | REG-*, escalation tests |
| Regulation (Q17) | REG-*, compliance tests |
| Privacy (Q18) | GDPR tests |
| Additional (Q19-Q24) | misc tests |

### Task 3.2: Update Test Data Files
Files to update:
- `tests/test_data/multilingual_tests.json`
- `tests/test_data/kb_tests.json`
- `tests/test_data/scenario_tests.json`
- `tests/test_data/escalation_tests.json`
- `tests/test_data/advanced_scenario_tests.json`

### Task 3.3: Clean Up Obsolete Tests
Remove tests that reference old KB content no longer present.

---

## Phase 4: Re-run Full Test Suite

### Task 4.1: Run All Tests
```bash
cd /home/odedbe/projects/axia-seekapa-cs-agents/tests

# E2E Tests (166 tests)
python3 e2e_test_runner.py --phase all

# Escalation Tests (15 tests)
python3 escalation_test_runner.py --level all --skip-ticket-validation

# Advanced Scenarios (62 tests)
python3 advanced_scenario_test_runner.py --phase all
```

### Task 4.2: Target Pass Rates
After KB update and test alignment:
- E2E: Target 95%+
- Escalation: Target 90%+
- Advanced: Target 85%+
- Overall: Target 90%+

---

## Phase 5 (Future): GPT-5.2 Prompt Tuning

**Only after Phases 1-4 are complete**, tune prompts for GPT-5.2:

### Techniques to Reduce Over-Escalation (from multi-LLM brainstorm):

1. **Evidence-gated escalation rubric**: Force model to only escalate when specific hard conditions are met (R1-R5: investment advice, KYC bypass, fraud, system outage, human authority needed)

2. **Must-cite KB policy**: Require KB citations in responses; absence of evidence triggers clarifying questions, not escalation

3. **Clarify-first micro-loop**: Before escalation, ask 1-2 targeted clarifying questions and attempt partial resolution

4. **Template-first responses**: Use pre-approved templates for top 20 scenarios to prevent unnecessary escalation

5. **Disposition classification gating**: Classify as S1-S6 categories; only allow escalation for S4-S6 (Compliance/Security, System Incident, Authority-Required)

---

## Files Reference

### New KB Files
- `/home/odedbe/projects/axia-seekapa-cs-agents/Seekapa_FAQ_KB.docx` (source)
- `/home/odedbe/projects/axia-seekapa-cs-agents/Seekapa_FAQ_KB.pdf` (for upload)
- `/home/odedbe/projects/axia-seekapa-cs-agents/Seekapa_FAQ_KB.txt` (text reference)

### Test Runners (already updated to use new SDK)
- `tests/e2e_test_runner.py` - E2E tests
- `tests/escalation_test_runner.py` - Escalation tests
- `tests/advanced_scenario_test_runner.py` - Advanced scenarios

### Agent Configuration
- Endpoint: `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai`
- Agents: `seekapa`, `AxiaCS`
- Current model: `gpt-5.2` (needs revert to `gpt-5.1`)

---

## Quick Start for Next Session

Say: **"Continue with the plan"** and Claude will:

1. Check this plan file
2. Revert agents to GPT-5.1
3. Guide you through KB upload in Azure Portal
4. Update test data files to match new KB
5. Run full test suite
6. Report results

---

## Checklist

- [ ] Revert seekapa agent to gpt-5.1
- [ ] Revert AxiaCS agent to gpt-5.1
- [ ] Upload Seekapa_FAQ_KB.pdf to seekapa vector store
- [ ] Upload Seekapa_FAQ_KB.pdf to AxiaCS vector store
- [ ] Delete old KB files from vector stores
- [ ] Update multilingual_tests.json for new KB
- [ ] Update kb_tests.json for new KB
- [ ] Update scenario_tests.json for new KB
- [ ] Update escalation_tests.json for new KB
- [ ] Update advanced_scenario_tests.json for new KB
- [ ] Run E2E tests and verify pass rate
- [ ] Run Escalation tests and verify pass rate
- [ ] Run Advanced tests and verify pass rate
- [ ] Document final results
