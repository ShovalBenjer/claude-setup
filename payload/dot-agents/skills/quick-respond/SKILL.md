---
name: quick-respond
description: One-shot answer from knowledge. No file reads, no verification, no forge loop.
effort: low
---

## Purpose

Quick syntax lookup, API signature, pattern example, or conceptual answer.
No tools needed -- answer from training knowledge.

## Rules

- No file reads, no search, no verification
- No forge loop, no TDD, no /reflect
- Keep answer concise (under 20 lines)
- If the question requires codebase-specific context, say: "This needs project context. Use `/answer-question` instead."
- If the question requires implementation, say: "This requires code changes. Exiting quick-respond mode."
