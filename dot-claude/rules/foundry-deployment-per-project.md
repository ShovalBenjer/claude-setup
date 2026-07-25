---
paths:
  - "**/azure/**"
  - "**/infra/**"
  - "**/*foundry*"
  - "**/*deploy*"
---

# Cloud and Foundry deployment

Keep project, environment, identity, data, and resource boundaries explicit.
Use least privilege, pinned versions, secret injection, and a reversible plan.
Read-only inspection and dry runs do not authorize production mutation. After an
approved deployment, verify the deployed revision and a real service signal.
