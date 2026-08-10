# Pipeline Docs

This lane holds CI/CD, deploy-gate, and notification references. It is for reusable pipeline knowledge, not project-specific generated pipeline logs.

Key references:

- `../FOUNDRY-EVAL-CI-PLAN.md`
- `../MODEL-MIGRATION-PLAN.md`
- `../wiki/Deployment.md`
- `notifications/notify.sh`
- `notifications/tlg_notification_legacy.sh`

Rules:

- Prefer no-secret, env-driven scripts.
- Production notifications should use `NOTIFY_BOT` and `NOTIFY_CHAT_ID`.
- New notification scripts should avoid emoji and use `[OK]` / `[FAIL]` markers.
- Project-specific pipeline YAML belongs in the project repo; only reusable templates or docs belong here.
