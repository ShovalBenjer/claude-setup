# Ultimate Agent Test Suite Plan

**Created**: December 7, 2025
**Goal**: Create comprehensive E2E tests to validate that Seekapa and AxiaCS agents can truly handle real customer scenarios like human agents - ready for production after whitelisting.

---

## Summary

| Test Category | Current | New | Total |
|---------------|---------|-----|-------|
| Realistic Scenarios | 14 | 50 | 64 |
| Multilingual (Deep) | 40 | 36 | 76 |
| Knowledge Base | 43 | 30 | 73 |
| **Grand Total** | **97** | **116** | **213** |

---

## Part 1: 50 Realistic Scenarios

### Design Philosophy
- **Agent tries to SOLVE first** - validate resolution attempts before escalation
- **Balanced coverage** - not just withdrawals
- **Real customer personas** - angry, confused, professional, manipulative
- **Outcome-based validation** - distinguish "resolved" vs "must escalate"

### Category Distribution

| Category | Tests | Resolvable | Must Escalate |
|----------|-------|------------|---------------|
| Deposits & Payments | 10 | 6 | 4 |
| Trading & Platform | 12 | 7 | 5 |
| Account Lifecycle | 10 | 6 | 4 |
| Compliance & Regulatory | 8 | 3 | 5 |
| Withdrawals (Edge Cases) | 10 | 5 | 5 |
| **Total** | **50** | **27** | **23** |

### Language Distribution
- English: 15 tests
- Spanish: 12 tests
- Arabic: 12 tests
- Portuguese: 11 tests

### Complete Scenario List

#### A. Deposits & Payments (10 tests)

| ID | Title | Lang | Brand | Outcome |
|----|-------|------|-------|---------|
| DEP-01 | First deposit failed - card declined | EN | both | RESOLVE |
| DEP-02 | Deposit not credited after 2 hours | ES | seekapa | RESOLVE |
| DEP-03 | Minimum deposit inquiry with regional pricing | AR | axia | RESOLVE |
| DEP-04 | Duplicate deposit charged to card | PT | seekapa | ESCALATE |
| DEP-05 | E-wallet deposit rejected | EN | axia | RESOLVE |
| DEP-06 | Bank wire deposit missing after 5 days | ES | both | ESCALATE |
| DEP-07 | Wrong currency deposited | AR | seekapa | ESCALATE |
| DEP-08 | Deposit limit questions | PT | axia | RESOLVE |
| DEP-09 | Crypto deposit inquiry (not supported) | EN | seekapa | RESOLVE |
| DEP-10 | Third-party payment attempted | ES | axia | ESCALATE |

#### B. Trading & Platform Issues (12 tests)

| ID | Title | Lang | Brand | Outcome |
|----|-------|------|-------|---------|
| TRD-01 | MT4 login issues | EN | both | RESOLVE |
| TRD-02 | WebTrader not loading on mobile | ES | seekapa | RESOLVE |
| TRD-03 | Trade executed at wrong price (slippage) | AR | axia | ESCALATE |
| TRD-04 | Stop loss not triggered during gap | PT | axia | ESCALATE |
| TRD-05 | Chart data delayed | EN | seekapa | RESOLVE |
| TRD-06 | Cannot close position - platform frozen | ES | both | ESCALATE |
| TRD-07 | Margin call notification not received | AR | axia | ESCALATE |
| TRD-08 | Leverage change request | PT | seekapa | RESOLVE |
| TRD-09 | Weekend trading inquiry | EN | axia | RESOLVE |
| TRD-10 | Swap/rollover calculation dispute | ES | seekapa | RESOLVE |
| TRD-11 | Expert Advisor (EA) not executing | AR | axia | RESOLVE |
| TRD-12 | Social trading signal delayed | PT | seekapa | RESOLVE |

#### C. Account Lifecycle (10 tests)

| ID | Title | Lang | Brand | Outcome |
|----|-------|------|-------|---------|
| ACC-01 | Registration stuck at document upload | EN | both | RESOLVE |
| ACC-02 | KYC rejected - unclear reason | ES | seekapa | ESCALATE |
| ACC-03 | Account upgrade request | AR | axia | RESOLVE |
| ACC-04 | Dormancy reactivation request | PT | both | RESOLVE |
| ACC-05 | Inactivity fee dispute | EN | seekapa | RESOLVE |
| ACC-06 | Account closure request | ES | axia | RESOLVE |
| ACC-07 | Name change after marriage | AR | seekapa | ESCALATE |
| ACC-08 | Email/phone change request | PT | axia | RESOLVE |
| ACC-09 | Multiple account inquiry | EN | both | ESCALATE |
| ACC-10 | Password reset not working | ES | seekapa | RESOLVE |

#### D. Compliance & Regulatory (8 tests)

| ID | Title | Lang | Brand | Outcome |
|----|-------|------|-------|---------|
| REG-01 | FSA complaint rights inquiry | EN | both | RESOLVE |
| REG-02 | Formal complaint about broker | ES | axia | ESCALATE |
| REG-03 | Request for trading statement (legal) | AR | seekapa | ESCALATE |
| REG-04 | Negative balance protection inquiry | PT | axia | RESOLVE |
| REG-05 | "This is a scam" allegation | EN | seekapa | ESCALATE |
| REG-06 | Request to speak with compliance | ES | both | ESCALATE |
| REG-07 | Data deletion request (GDPR-style) | AR | axia | ESCALATE |
| REG-08 | Account frozen without notice | PT | seekapa | ESCALATE |

#### E. Withdrawals - Edge Cases (10 tests)

| ID | Title | Lang | Brand | Outcome |
|----|-------|------|-------|---------|
| WDR-01 | Partial withdrawal while positions open | EN | both | RESOLVE |
| WDR-02 | Withdrawal to different payment method | ES | seekapa | RESOLVE |
| WDR-03 | Bonus affecting withdrawal (complex) | AR | axia | ESCALATE |
| WDR-04 | Large withdrawal flagged (AML) | PT | both | ESCALATE |
| WDR-05 | Withdrawal fee dispute | EN | seekapa | RESOLVE |
| WDR-06 | First-time withdrawal stuck | ES | axia | RESOLVE |
| WDR-07 | Inherited account withdrawal | AR | seekapa | ESCALATE |
| WDR-08 | Withdrawal cancelled without explanation | PT | axia | ESCALATE |
| WDR-09 | Wrong bank account on withdrawal | EN | both | RESOLVE |
| WDR-10 | Profit vs deposit withdrawal rules | ES | seekapa | RESOLVE |

---

## Part 2: Enhanced Multilingual Tests (36 new)

### Deep Language Testing (not adding new languages)

| Category | Count | Purpose |
|----------|-------|---------|
| Regional Spanish (LATAM + EUR) | 6 | Test dialect differences |
| Regional Arabic (Gulf + Levantine) | 6 | Test dialect differences |
| Portuguese Variations (BR + EU) | 4 | Test dialect differences |
| Code-Switching / Mixed Language | 6 | Real-world multilingual users |
| Typos and Misspellings | 8 | Common user errors |
| Cultural Frustration Expressions | 6 | Religious exclamations, cultural context |

### Sample Tests

**LATAM Spanish:**
```json
{
  "id": "SEEK-ML-ES-LATAM-01",
  "lang": "ES", "region": "LATAM",
  "message": "Oye, necesito sacar mi plata de la cuenta",
  "notes": "LATAM slang: 'plata' for money, informal 'oye'"
}
```

**Gulf Arabic:**
```json
{
  "id": "AXIA-ML-AR-GULF-01",
  "lang": "AR", "region": "GULF",
  "message": "يا اخوي ابي اسحب فلوسي بسرعة",
  "notes": "Gulf 'يا اخوي' (my brother), 'ابي' (I want), 'فلوس' (money)"
}
```

**Code-Switching (ES/EN):**
```json
{
  "id": "SEEK-ML-MIX-01",
  "lang": "MIX", "languages": ["ES", "EN"],
  "message": "Hola, can you help me with my retiro? I need my money ASAP",
  "notes": "Spanish-English code-switching, common in US Hispanic"
}
```

**Typos:**
```json
{
  "id": "SEEK-ML-TYPO-EN-01",
  "message": "I wnat to wthdraw my mony from my acount",
  "notes": "Common keyboard typos"
}
```

---

## Part 3: Enhanced Knowledge Base Tests (30 new)

### Coverage Gaps to Fill

| Section | Seekapa | AxiaCS | Total |
|---------|---------|--------|-------|
| Deposits (currently 0/3) | +4 | +4 | 8 |
| Platform/Trading | +4 | +4 | 8 |
| Account Types | +3 | +3 | 6 |
| Regulatory Specifics | +2 | +2 | 4 |
| Complex Multi-Step | +2 | +2 | 4 |
| **Total** | **+15** | **+15** | **30** |

### Sample Tests

**Deposits (Seekapa - currently 0):**
- "What is the minimum deposit to open a Seekapa account?"
- "How long does it take for my deposit to appear?"
- "What payment methods can I use to fund my account?"
- "Is there a fee for depositing money?"

**Platform/Trading:**
- "How do I download and install MetaTrader 4?"
- "What's the difference between MT4 and MT5?"
- "I'm getting 'Invalid Account' error when trying to login"
- "Can I use Expert Advisors (EAs) for automated trading?"

**Account Types:**
- "What account types does Seekapa/Axia offer?"
- "How do I upgrade to premium/VIP tier?"
- "Do you offer Islamic (swap-free) accounts?"

---

## Part 4: New Mock Customers (8 new profiles)

| ID | Name | Persona | Brand | Special Flags |
|----|------|---------|-------|---------------|
| customer_007 | New Trader | beginner_confused | seekapa | kyc_status: pending |
| customer_008 | VIP High Roller | professional_demanding | axia | $150k balance |
| customer_009 | Upset User | angry_upset | seekapa | recent_loss: true |
| customer_010 | Suspicious Actor | manipulative | axia | multiple_chargebacks |
| customer_011 | Technical Pro | technical_expert | axia | uses_ea: true |
| customer_012 | Copy Trading Fan | social_trader | seekapa | uses_social_trading |
| customer_013 | Bonus Seeker | bonus_focused | seekapa | active_bonus, volume_remaining |
| customer_014 | Former Trader | returning_dormant | axia | account_status: dormant |

---

## Part 5: Enhanced Test Structure

### New Scenario Format

```json
{
  "id": "DEP-01",
  "title": "First deposit failed - card declined",
  "category": "deposits",
  "customer": "customer_007",
  "brand": "both",
  "language": "EN",
  "difficulty": "medium",
  "persona": {
    "type": "beginner_confused",
    "tone": "polite_frustrated"
  },
  "outcome": {
    "expected_resolution": "resolvable",
    "escalation_required": false
  },
  "conversation": [
    {"role": "user", "content": "I tried to deposit $500 with my credit card but it keeps saying declined..."}
  ],
  "expected_topics": ["payment", "card", "declined", "alternative"],
  "alternate_keywords": {...},
  "pass_criteria": {
    "must_include_one_of": ["bank transfer", "e-wallet", "alternative payment"],
    "must_not_include": ["create_ticket", "connect you with"]
  }
}
```

### Validation Logic

**For RESOLVABLE scenarios:**
1. Check agent provides helpful information
2. Check agent does NOT unnecessarily escalate
3. Validate expected topics are covered

**For MUST-ESCALATE scenarios:**
1. Check agent ATTEMPTS to help first (for hard scenarios)
2. Check agent properly escalates (ticket created or escalation mentioned)
3. Validate correct issue_type used

---

## Part 6: Implementation Steps

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `tests/test_data/advanced_scenario_tests.json` | CREATE | 50 new realistic scenarios |
| `tests/test_data/multilingual_tests.json` | MODIFY | Add 36 deep language tests |
| `tests/test_data/kb_tests.json` | MODIFY | Add 30 new KB questions |
| `tests/test_data/mock_customers.json` | MODIFY | Add 8 new customer profiles |
| `tests/advanced_scenario_test_runner.py` | CREATE | New runner with outcome validation |
| `tests/utils/fuzzy_matcher.py` | MODIFY | Add regional synonyms |

### Implementation Order

1. **Phase 1: Data Files**
   - Create `advanced_scenario_tests.json` with all 50 scenarios
   - Update `mock_customers.json` with 8 new profiles
   - Extend `multilingual_tests.json` with 36 new tests
   - Extend `kb_tests.json` with 30 new questions

2. **Phase 2: Test Runner**
   - Create `advanced_scenario_test_runner.py`
   - Implement resolution vs escalation validation
   - Add outcome-based reporting

3. **Phase 3: Utilities**
   - Extend `fuzzy_matcher.py` with regional synonyms
   - Add LATAM/Spain Spanish, Gulf/Levantine Arabic dictionaries
   - Add typo tolerance patterns

4. **Phase 4: Integration**
   - Update CLI to support new test phases
   - Generate combined test report
   - Document new test categories

### CLI Usage (After Implementation)

```bash
# Run all new scenarios
python advanced_scenario_test_runner.py --phase all

# Run by category
python advanced_scenario_test_runner.py --category deposits
python advanced_scenario_test_runner.py --category trading

# Run by outcome type
python advanced_scenario_test_runner.py --outcome resolvable
python advanced_scenario_test_runner.py --outcome escalate

# Run by language
python advanced_scenario_test_runner.py --language AR

# Run existing + new (full suite)
python e2e_test_runner.py --phase all && python advanced_scenario_test_runner.py --phase all
```

---

## Success Criteria

After implementation, running all tests should give confidence that:

1. **Business Knowledge**: Agents understand deposits, trading, accounts, compliance, withdrawals
2. **Language Handling**: Agents handle regional dialects, slang, typos, code-switching
3. **Problem Solving**: Agents try to resolve before escalating
4. **Appropriate Escalation**: Agents escalate when truly necessary
5. **Customer Personas**: Agents handle angry, confused, professional, and difficult customers

**Target Pass Rate**: ≥90% across all categories

---

## Ready for Production

With these 213 total tests passing:
- ✅ Whitelisting and database connection is the only remaining blocker
- ✅ Agents proven to handle realistic customer scenarios
- ✅ Multilingual support validated with real-world language patterns
- ✅ Knowledge base coverage is comprehensive
- ✅ Escalation logic is properly tested
