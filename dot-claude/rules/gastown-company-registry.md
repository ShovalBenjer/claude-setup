---
paths:
  - "**/.claude/agents/**"
  - "**/*gastown*"
  - "**/*agent-registry*"
---

# Agent registry

Each agent entry must declare a narrow purpose, inputs, allowed tools, write scope,
required evidence, and stop condition. Do not name unavailable skills or hard-code
stale model IDs. Registry metadata routes work; it does not grant extra authority.
