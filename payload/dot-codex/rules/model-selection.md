# Model Selection

**Workflow:** Opus (planning) → Haiku (implementation) → Compact (100-120k tokens)

## Rules

**Opus:** Architecture, critical decisions, plan mode
**Haiku:** Implementation after plan approved, cost-efficient
**Sonnet:** Default balance

**Context target:** 100-120k tokens. Auto-compaction at ~95% capacity.
**Compaction:** Decision log + thematic grouping, 50%+ reduction. Task state persists in session history.

## Per-Project

**SIU:** Haiku default (budget ~$536/mo)
**figma-4-all:** Haiku (fast iteration)
**seekapa-video:** Haiku (rendering workflows)

**Override:** Use Opus for architecture only
