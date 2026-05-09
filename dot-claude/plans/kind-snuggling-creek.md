# Plan: apply email-state-machine migration to the real prod Postgres

## Context

**Problem.** `email_drip_sender` (timer function, every 5 min) has been crashing on every invocation for at least a day with `UndefinedColumn: column "arabic_email_status" does not exist`. Health endpoint reports `stuck_sessions: 965` (status=warning, demoting overall to `degraded`). The chronic backlog grows because `_expire_stale_sessions()` (which would auto-cancel >48h sessions) lives inside `email_drip_sender` and never runs to completion before the unrelated query crashes the function.

**Why the fix didn't land yesterday.** Two production Postgres flexible servers exist in `AZAI_group`:

| Server | FQDN | Function-app uses it? | Admin login | Public access |
|---|---|---|---|---|
| `postgres-seekapatraining-prod` | `postgres-seekapatraining-prod...` | **No** (443 stuck sessions, separate data) | `seekapaadmin` | Enabled |
| `aiprojects-company-postsql` | `aiprojects-company-postsql...` | **Yes** (965 stuck sessions, real prod) | `postuser` (Azure-level) | **Disabled (VNET-only)** |

The runbook `docs/runbooks/2026-04-06-migrations-014-017.md` claimed `aiprojects-company-postsql` was a stale CLAUDE.md typo. That was wrong. Migrations 014/017 were applied to `postgres-seekapatraining-prod` (not the live prod). The fix never reached the actual data.

**Wiki source-of-truth (page `/Training Platform/Database`).** Confirms:
- Live prod: `aiprojects-company-postsql.postgres.database.azure.com` / db `seekapa_training`
- Runtime user: `training_app_user` (no DDL rights — proved last run with `must be owner of table training_sessions`)
- DDL user: `seekapaadmin` (this is a Postgres role, not the Azure-flexible-server admin login `postuser`)
- Network: VNET-only — use Bastion / jump host / VNET-integrated worker

## Approach

Run migrations from inside the VNET via the function app's Kudu console — no public-access flip on the DB, no new VM, no new firewall holes. Steps below run end-to-end via `az webapp ssh`/Kudu REST.

### Step 1 — Test that `PostgreSQL-Admin-Password` (KV) authenticates `seekapaadmin` on the live prod server

Why this is the question: we have one admin password in KV. It authenticated `seekapaadmin@postgres-seekapatraining-prod` yesterday. The wiki says `seekapaadmin` is also the DDL role on `aiprojects-company-postsql`. Need to confirm same password works there. If it does — straightforward. If not — escalate to find the right credential.

Test command (runs on the function host via Kudu, never public-network):

```bash
# from dev machine
az webapp ssh -g AZAI_group -n func-training-prod
# inside the function host (VNET-attached):
python3 -c "
import os, psycopg2, urllib.parse
# Read pwd from env or fetch from KV via managed identity
import requests
md = 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net'
tok = requests.get(md, headers={'Metadata':'true'}).json()['access_token']
sec = requests.get(
    'https://kv-seekapa-apps.vault.azure.net/secrets/PostgreSQL-Admin-Password?api-version=7.4',
    headers={'Authorization': f'Bearer {tok}'}).json()['value']
conn = psycopg2.connect(
    host='aiprojects-company-postsql.postgres.database.azure.com',
    user='seekapaadmin', password=sec, dbname='seekapa_training', sslmode='require')
cur = conn.cursor()
cur.execute('SELECT current_user, tableowner FROM pg_tables WHERE tablename=%s', ('training_sessions',))
print(cur.fetchone())
"
```

Expected: `('seekapaadmin', 'seekapaadmin')`. If we get a `password authentication failed` error, the same KV password isn't valid here and we ask the user.

### Step 2 — Apply migrations 014, 015 (with column-name fix), 017 + add 'EXPIRED' enum value

Same channel — `az webapp ssh` into function host, run a Python script that reads each migration file from a temp upload, then applies. Files to use:

- `database/migrations/014_email_queue.sql` — boolean tracking columns + indexes
- `database/migrations/015_scoring_source.sql` — **needs inline fix**: `elevenlabs_conversation_id` → `conversation_id` (the table has only `conversation_id`)
- `database/migrations/017_email_state_machine.sql` — adds `email_status`, `arabic_email_status`, `email_next_retry_at`; drops old booleans
- one-line `ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'EXPIRED';` (run with `autocommit=True`)

All four are idempotent (`IF NOT EXISTS`). 016 is **not** re-run — it already succeeded yesterday on the wrong server, but on this server it would cancel pre-2026-03-18 stuck sessions and is needed. Adding 016 to the list (the runbook's pattern; it just `UPDATE`s rows, no DDL).

Final list: 014, 015 (patched), 016, 017, plus the enum add.

### Step 3 — Restart function app to flush stale connection-pool schema cache

The function host's `psycopg2.pool.ThreadedConnectionPool` (singleton in `shared/database.py`) caches schema across invocations. After ALTER, existing connections still see the old schema. Restart forces fresh pool init.

```bash
az functionapp restart -g AZAI_group -n func-training-prod
```

### Step 4 — Verify

- Health: `curl https://func-training-prod.azurewebsites.net/api/system/health` — `stuck_sessions.count` should drop within ~30 min as `_expire_stale_sessions()` runs each cycle and marks >48h sessions `EXPIRED`. Overall status should flip from `degraded` to `healthy` once `stuck_sessions` is below threshold.
- App Insights: 0 `email_drip_sender` exceptions in the 30 min following the restart.
- App Insights: at least one `email_drip_sender` request with `success=True`.

## Critical files

- `database/migrations/014_email_queue.sql` (apply as-is)
- `database/migrations/015_scoring_source.sql` (one-char fix: `elevenlabs_conversation_id` → `conversation_id`; commit the fix to repo)
- `database/migrations/016_cleanup_stale_sessions.sql` (apply as-is)
- `database/migrations/017_email_state_machine.sql` (apply as-is)
- `backend/email_drip_sender/__init__.py:122` — uses `'EXPIRED'` enum value (must exist in DB before this runs)
- `backend/shared/database.py` — connection pool singleton; restart needed to refresh schema cache after ALTER
- `docs/runbooks/2026-04-06-migrations-014-017.md` — needs an addendum: hostname is **not** stale; runbook misled the agent. Fix that note.
- Wiki page `/Training Platform/Database` — already correct; cite as source of truth.

## Existing reusable helpers

- `/tmp/migrate-fix.sh` and `/tmp/migrate-fix2.sh` from yesterday — adapt to use Kudu/SSH transport instead of public-firewall transport. Same Python connection logic; only the network path changes.
- `_expire_stale_sessions()` already in `email_drip_sender/__init__.py:116` — once the column + enum land, it self-heals the backlog. No new code.

## Risks

- **One-shot SQL execution on prod via Kudu is auditable but powerful.** Each command runs as the function-app's identity. Recorded in Kudu's deployment log. We're touching the prod DB schema — there is no fully-safe approach.
- **DROP COLUMN in 017 step 6** (drops `email_sent`, `email_sent_at`, etc.) is irreversible; backfilled data would be the recovery basis. Not new risk vs. yesterday's run.
- **If `PostgreSQL-Admin-Password` doesn't authenticate `seekapaadmin@aiprojects-company-postsql`**, plan stalls and we ask the user where the right secret is.

## Verification (end-to-end)

1. Pre-check (from dev): `curl -s .../system/health | jq '.components.stuck_sessions'` — record baseline.
2. Run the migration via Kudu/SSH (Step 2).
3. Restart function app (Step 3).
4. Wait 5 min (one drip cycle).
5. App Insights query for `email_drip_sender` exceptions in last 5 min — expect 0.
6. App Insights query for `email_drip_sender` requests, last `success=True` field — expect at least one.
7. Re-hit `/system/health` — expect `stuck_sessions.count` declining; check again after 30 min for full backlog drain.
