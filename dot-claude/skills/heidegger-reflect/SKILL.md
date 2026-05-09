---
name: heidegger-reflect
description: End-of-task self-reflection protocol combining test evidence, completion honesty, and Heideggerian model-aware introspection.
---

# Heidegger Self-Reflection Skill

**Purpose:** End-of-task self-inspection using Heideggerian unconcealment + model-aware introspection

## Usage

```
/heidegger-reflect <task-name>
```

## Protocol

This skill executes the **full self-review protocol** defined in `docs/prompts/Heidegar_self_reflect_oded.md` (the prompt document -- DO NOT append to it).

The prompt document defines the framework. Read it before reflecting.

For the deep introspective protocol (sections 1.2-1.4, 2.3, 3.1-3.3, 4.1-4.3), also reference `docs/prompts/self_review.md` if it exists, or the archived version at `archive/cleanup-2026-02-19/docs-legacy/prompts/self_review.md` (retrievable via `git show HEAD:...`).

## Output Location

Reflections are written to: `docs/reflections/YYYY-MM-DD-<task-slug>.md`

Each reflection is a **standalone file**, not appended to the prompt doc.

## Required Sections

### Part 1: Test Evidence (Mandatory)
Before any reflection, run and capture actual test output. No claims without evidence.

### Part 2: Honest Completion (Mandatory)
```
HONEST COMPLETION: X%
WORKING (X%): [what actually runs]
SCAFFOLDED, NOT WIRED (X%): [what exists but is not functional]
MISSING (X%): [what does not exist yet]
```

### Part 3: Heideggerian 4-Lens Analysis
1. **Revelation** -- what became unconcealed (ground truth, validated/contradicted assumptions)
2. **Concealment** -- what was obscured or unaddressed (data gaps, postponed decisions)
3. **Internal Mechanisms** -- how AI patterns shaped the outcome (biases, implicit assumptions)
4. **Implications** -- how this enables/limits user's action-space

### Part 4: Deep Model-Aware Introspection
From the self_review.md protocol:

1.2 **Internal concept activations** -- name dominant roles/concepts with confidence levels
1.3 **Information preserved but not decoded** -- details present in context but not expressed, and why
1.4 **Behavioral reachable set** -- alternative answer-styles that could have been produced, and why they weren't

2.3 **Shadow answer** -- construct a plausible answer from a differently-aligned model; compare

3.1 **Training-time patterns** -- regularities that shaped the answer, with specific evidence
3.2 **Safety/alignment influence** -- where claims were softened or branches avoided
3.3 **Narrative smoothing** -- where competing frames were suppressed for coherence

4.1 **User option-space** -- how revealing/concealing narrows or widens user's interpretations
4.2 **Plausible vs executable** -- which parts sound good but may not work in practice
4.3 **Perceived authority vs reliability** -- where tone may cause over-estimation of epistemic authority

### Part 5: Stubborn Issues (if any)
Track persistent issues per the stubborn-issue policy in the prompt doc.

### Part 6: Revision Offer
Ask user if they want a revised version integrating uncovered tensions.

## Key Rules

- The prompt doc (`docs/prompts/Heidegar_self_reflect_oded.md`) is the FRAMEWORK. Never append reflections to it.
- Each reflection is a separate file in `docs/reflections/`.
- A reflection is NOT a status report. It requires genuine introspection on internal mechanisms.
- Identify at least 3 concealed gaps (per project rule `.Codex/rules/heidegger_reflection.md`).
- Cite specific files, line numbers, error counts.
