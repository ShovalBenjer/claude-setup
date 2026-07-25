---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.java"
  - "**/*.cs"
---

# Boundary contracts

Parse and validate data at external, persistence, network, model, and tool
boundaries. Prefer explicit types or schemas over raw passthrough. Define missing,
extra, malformed, timeout, and partial-failure behavior. Test representative valid
and invalid payloads; never weaken a boundary oracle to fit an implementation.
