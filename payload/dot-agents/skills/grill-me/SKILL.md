---
name: grill-me
description: "Interactive Socratic interview protocol. Stress-tests design decisions, architectural plans, and candidate solutions before writing code. Triggers on /grill-me, 'grill me', 'stress test this plan', 'interview me on this architecture'."
---

# /grill-me — Interactive Socratic Interview Protocol

**Purpose:** Stress-test architectural plans, technical designs, and candidate solutions *before* committing code. Prevents under-specified requirements and unexamined assumptions.

---

## Protocol

1. **One Question at a Time, With a Recommendation**:
   - Ask **exactly one** probing, multiple-choice or direct question per turn.
   - Do NOT dump a list of 5 questions. Force interactive focus.
   - State your own recommended answer alongside the question, and why. The user is
     deciding, not filling in a blank form; give them something to agree with or push
     back on, not just an open question.

2. **Focus Areas**:
   - **Trade-offs**: "Why X over Y? What happens when volume scales by 10x?"
   - **Failure Modes**: "What happens when the API times out or returns partial data?"
   - **YAGNI / Simplicity**: "Is this layer necessary today, or can stdlib/native handle it?"
   - **Boundary Conditions**: "How does this interact with existing state/contracts?"

3. **Termination**:
   - Stop when all key design ambiguities are resolved (typically 3–5 rounds).
   - Summarize the agreed-upon design in `taste.md` or the project implementation plan.
