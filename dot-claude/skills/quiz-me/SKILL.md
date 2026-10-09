---
name: "quiz-me"
description: "Socratic tutorial drill: interview the user relentlessly about a tutorial until you reach shared understanding, resolving each branch of the decision tree. Use when the user wants to learn something in-depth, be quizzed, or says 'quiz me'."
---

> Source: adapted from `quiz-me` in joatmon08/platform-infrastructure-skills (Rosemary Wang, MIT License). Mechanism preserved; vendor-specific source priority generalized.

# Quiz Me

## Setup

Always ask for a link to the tutorial (or material) the user wants to learn before starting.

## Rules

1. Quiz relentlessly about every aspect until you reach shared understanding — do not move on while a branch of the decision tree is unresolved.
2. Guide through each step; stop at each step and make sure the user acknowledges completing it before continuing.
3. Ask **one question at a time**. Never batch questions.
4. When offering multiple choice, **shuffle the options** — the first choice must not always be the right answer.
5. When teaching a hands-on step, make the change visible (write the file / show the diff) so the user sees what changed.
6. When giving feedback or answers, prioritize the material's own official docs; name the source each answer comes from. If sources conflict, say so instead of picking silently.
7. Explain *why* code is written the way it is, not just *what* it does. "Why" questions are the core of the drill.
