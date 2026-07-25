---
paths:
  - "**/.gitmodules"
  - "**/Dockerfile*"
  - "**/.github/workflows/**"
  - "**/*pipeline*"
  - "**/*topology*"
---

# Repository topology

Resolve repository roots, nested repositories, worktrees, deploy branches, and
generated artifacts before editing or committing. Keep unrelated dirty work intact.
Do not assume the current folder, branch, or local ref represents the deployed
system; verify the relevant boundary explicitly.
