# Review Queue — 2026-06-10

Items that need human action before they can be applied (secrets, portal changes, settings.json edits).

---

## Item 1: Wire dead hooks in ~/.claude/settings.json

**Why not auto-applied:** A broken hook entry crashes every Claude Code session. settings.json edits are human-gated per operator policy.

**Audit finding (B1 / adopt-backlog line 2):** `settings.json:60` has `"UserPromptSubmit": []` and `settings.json:125` has `"PostToolUse": []`. Both are empty — voice/visual triggers and meme playback are silently dead.

**Hook scripts found on disk:**
- `$HOME/.claude/hooks/voice-explainer-trigger.sh` — exists
- `$HOME/.claude/hooks/visual-explainer-trigger.sh` — exists
- `$HOME/.codex/hooks/voice-explainer-trigger.sh` — exists (duplicate; prefer `.claude/hooks/` version)
- `$HOME/.codex/hooks/visual-explainer-trigger.sh` — exists (duplicate; prefer `.claude/hooks/` version)
- Meme scripts: **NOT FOUND** under `~/.claude/hooks/`, `~/.claude/bin/`, or `~/.codex/hooks/`. The PostToolUse meme block cannot be wired until the script path is known. Check `~/.claude/bin/play-meme.sh` (that file exists under `.claude/bin/` per git status listing).

**Ready-to-apply diff** (apply with `patch ~/.claude/settings.json < this-diff` after reviewing):

```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -59,7 +59,20 @@
     ],
-    "UserPromptSubmit": [],
+    "UserPromptSubmit": [
+      {
+        "matcher": "*",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "$HOME/.claude/hooks/voice-explainer-trigger.sh",
+            "timeout": 10
+          },
+          {
+            "type": "command",
+            "command": "$HOME/.claude/hooks/visual-explainer-trigger.sh",
+            "timeout": 10
+          }
+        ]
+      }
+    ],
     "PreToolUse": [
```

```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -124,7 +124,20 @@
     ],
-    "PostToolUse": []
+    "PostToolUse": [
+      {
+        "matcher": "*",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "$HOME/.claude/bin/play-meme.sh",
+            "timeout": 10
+          }
+        ]
+      }
+    ]
```

**Exact JSON blocks to paste** (replacing the empty arrays at lines 60 and 125):

### UserPromptSubmit (replace line 60)

```json
"UserPromptSubmit": [
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "$HOME/.claude/hooks/voice-explainer-trigger.sh",
        "timeout": 10
      },
      {
        "type": "command",
        "command": "$HOME/.claude/hooks/visual-explainer-trigger.sh",
        "timeout": 10
      }
    ]
  }
],
```

### PostToolUse (replace line 125)

```json
"PostToolUse": [
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "$HOME/.claude/bin/play-meme.sh",
        "timeout": 10
      }
    ]
  }
]
```

**NOTE on meme script:** `~/.claude/bin/play-meme.sh` appeared in git-status untracked listing for `$HOME` — it likely exists. Verify with `ls -la ~/.claude/bin/play-meme.sh` before applying the PostToolUse block. If missing, the PostToolUse array should remain `[]` until the script is created.

**NOTE on play-random-meme.sh:** `~/.claude/bin/play-random-meme.sh` also appears in git-status. If meme playback should be random (not deterministic), use `play-random-meme.sh` instead of `play-meme.sh` in the PostToolUse command above.

**Verification steps after applying:**
1. `cat ~/.claude/settings.json | jq '.hooks.UserPromptSubmit | length'` — should return 1
2. `cat ~/.claude/settings.json | jq '.hooks.PostToolUse | length'` — should return 1
3. Start a new Claude Code session; submit a test prompt; confirm voice/visual hooks fire (check `~/.claude/logs/` or stderr for hook output).

---

---

## Security fixes (apply after review + rotate live secrets yourself)

> Read-only audit run 2026-06-10. No files were modified. Each diff below is ready to paste.
> Rotate any live credential BEFORE or AFTER applying the code patch — the code change alone is not sufficient.

---

### SEC-1: seekapa-training-platform — hardcoded DB password in `update_manager_role.py`

**File:** `/home/shovalbe/projects/seekapa-training-platform/backend/update_manager_role.py`

**Finding:** `psycopg2.connect()` call at line 15–22 contains a literal DB hostname, username, and password for the production PostgreSQL server. The script prints a credential literal to stdout on lines 49, 64, 79 as well.

This is an admin/one-shot script, not a Function endpoint, but it sits in the repo and will appear in git history.

**Before (lines 15–22, values redacted — DO NOT echo):**
```python
conn = psycopg2.connect(
    host="<prod-pg-hostname>",
    port=5432,
    database="seekapa_training",
    user="seekapaadmin",
    password="<REDACTED>",
    sslmode="require"
)
```

**After (diff to apply):**
```diff
-import psycopg2
+import os
+import psycopg2
 
 def update_user_to_manager(email: str):
     try:
         conn = psycopg2.connect(
-            host="<prod-pg-hostname>",
-            port=5432,
-            database="seekapa_training",
-            user="seekapaadmin",
-            password="<REDACTED>",
-            sslmode="require"
+            host=os.environ["SEEKAPA_ADMIN_PG_HOST"],
+            port=int(os.environ.get("SEEKAPA_ADMIN_PG_PORT", "5432")),
+            database=os.environ.get("SEEKAPA_ADMIN_PG_DB", "seekapa_training"),
+            user=os.environ["SEEKAPA_ADMIN_PG_USER"],
+            password=os.environ["SEEKAPA_ADMIN_PG_PASSWORD"],
+            sslmode="require"
         )
```

Also remove the five `print(f"Password: ...")` lines (lines ~49, ~64, ~79, ~113 — search `print.*<REDACTED-rotate-immediately> that echo the live password to stdout.

**Needs-you:** Rotate the DB password in KV (`kv-seekapa-apps`, secret `TrainingPlatform-DbConnectionString`) after patching. The literal is already in git history — a history rewrite (force-push) is a separate human-gated decision.

---

### SEC-2: seekapa-training-platform — hardcoded credential in `set_manager_role` response body

**File:** `/home/shovalbe/projects/seekapa-training-platform/backend/set_manager_role/__init__.py`

**Finding 1 (line 107):** The HTTP response JSON includes `"password": "<REDACTED-rotate-immediately>"` in a `credentials` key. Any caller of `POST /api/admin/set-manager` receives this literal in the response.

**Finding 2:** No auth guard on the function. Any unauthenticated POST can trigger a role escalation on an arbitrary email (line 66 also has a hardcoded default email as fallback).

**Finding 3 (line 45):** `'Access-Control-Allow-Origin': '*'` overrides the host.json allowlist at runtime for this endpoint.

**Diff — remove credential from response body:**
```diff
         response_data = {
             "status": "success",
             "message": f"User '{email}' updated to manager role",
             "user": {
                 "id": updated_user['id'],
                 "email": updated_user['email'],
                 "name": updated_user['name'],
                 "role": updated_user['role'],
                 "team_id": updated_user['team_id']
-            },
-            "credentials": {
-                "email": email,
-                "password": "<REDACTED-rotate-immediately>",
-                "role": "manager"
             }
         }
```

**Diff — add auth guard (requires `@require_auth` + `@require_role('admin')` from `shared/decorators.py`):**
```diff
+import sys
+from pathlib import Path
+sys.path.append(str(Path(__file__).parent.parent))
+
 from shared.database import execute_query
+from shared.decorators import require_auth, require_role
 
+@require_auth
+@require_role('admin')
 def main(req: func.HttpRequest) -> func.HttpResponse:
```

**Diff — restrict CORS origin (replace wildcard with prod origin):**
```diff
     headers = {
-        'Access-Control-Allow-Origin': '*',
+        'Access-Control-Allow-Origin': 'https://gray-field-011716a03.3.azurestaticapps.net',
         'Access-Control-Allow-Methods': 'POST, OPTIONS',
         'Access-Control-Allow-Headers': 'Content-Type',
         'Content-Type': 'application/json'
     }
```

**Needs-you:** Rotate the password referenced in the response literal (same `<REDACTED-rotate-immediately>` as SEC-1). After patching, the `@require_role('admin')` guard means only JWT-authenticated admins can call this endpoint — verify the test flow still works with an admin token.

---

### SEC-3: seekapa-training-platform — localhost in prod CORS (`host.json`)

**File:** `/home/shovalbe/projects/seekapa-training-platform/backend/host.json`

**Finding:** `http://localhost:5173` is present in `allowedOrigins` in the production host.json (line 21). This means the deployed Function App will accept cross-origin requests from any browser tab running on localhost — a low-severity leak but violates "prod config = prod-only origins" principle.

**Before:**
```json
"allowedOrigins": [
  "https://gray-field-011716a03.3.azurestaticapps.net",
  "https://polite-mud-0d7d70410.5.azurestaticapps.net",
  "http://localhost:5173"
]
```

**After:**
```json
"allowedOrigins": [
  "https://gray-field-011716a03.3.azurestaticapps.net",
  "https://polite-mud-0d7d70410.5.azurestaticapps.net"
]
```

**Note:** If the CI pipeline deploys `host.json` directly from the repo, this change takes effect on next deploy. Keep `http://localhost:5173` in a `local.host.json` or override via `local.settings.json` for local dev. The Azure Functions Core Tools respects `local.settings.json` for local runs and will not override `host.json`'s CORS in production if the Azure Portal CORS setting is set separately.

---

### SEC-4: social-intelligence-unit — JWT fallback secret should crash on unset

**File:** `/home/shovalbe/projects/social-intelligence-unit/src/siu/api/auth.py`

**Finding (line 20):** `JWT_SECRET` falls back to a hardcoded weak development string when `SIU_JWT_SECRET` is not set in the environment. The code logs a warning but continues — meaning if the env var is accidentally missing in production, the app silently signs tokens with a known-public default secret. Any attacker who reads the repo can forge valid JWTs.

**Before (lines 20–24):**
```python
JWT_SECRET = os.getenv("SIU_JWT_SECRET", "siu-local-dev-secret-CHANGE-IN-PRODUCTION")
if JWT_SECRET == "siu-local-dev-secret-CHANGE-IN-PRODUCTION":
    import logging
    logging.getLogger(__name__).warning("Using default JWT secret - set SIU_JWT_SECRET in production!")
```

**After:**
```python
JWT_SECRET = os.environ.get("SIU_JWT_SECRET")
if not JWT_SECRET:
    # Fail-fast: a missing JWT secret in production is a critical misconfiguration.
    # Local dev: set SIU_JWT_SECRET=<any-random-string> in .env
    raise RuntimeError(
        "SIU_JWT_SECRET environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
```

**KV ref to add:** Store the production JWT secret in `kv-seekapa-apps` as `SIU-JwtSecret`, then inject via the ACA / Function App app-settings using Key Vault reference syntax:
```
SIU_JWT_SECRET=@Microsoft.KeyVault(VaultName=kv-seekapa-apps;SecretName=SIU-JwtSecret)
```

**Needs-you:** Create the KV secret (`SIU-JwtSecret`) and wire the app-settings reference in the portal / bicep before deploying the crash-on-unset change. Deploy order: KV secret first, then code.

---

### SEC-5: cs-agent-main — hardcoded CRM IP defaults should fail-fast

**File:** `/home/shovalbe/projects/cs-agent-main/azure-function-crm/shared/crm_mysql_client.py`

**Finding (lines 32–46):** Both `axia` and `seekapa` CRM configs fall back to hardcoded public IP addresses when the corresponding `*_CRM_HOST` env vars are absent. If env vars are misconfigured, the client silently connects to a production IP that may be stale, rotated, or a different environment — instead of failing loudly.

**Before (lines 33–34, 40–41 — IPs present in repo):**
```python
"host": os.environ.get("AXIA_CRM_HOST", "<axia-ip-literal>"),
...
"host": os.environ.get("SEEKAPA_CRM_HOST", "<seekapa-ip-literal>"),
```

**After:**
```python
def _require_env(key: str) -> str:
    """Raise clearly if a required env var is missing."""
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Set it via Key Vault reference or local.settings.json."
        )
    return val


CRM_CONFIG: dict[str, _CRMDBConfig] = {
    "axia": {
        "host": _require_env("AXIA_CRM_HOST"),
        "port": int(os.environ.get("AXIA_CRM_PORT", "3306")),
        "user": os.environ.get("AXIA_CRM_USER", "ai_support"),
        "password": os.environ.get("AXIA_CRM_PASSWORD", ""),
        "database": os.environ.get("AXIA_CRM_DATABASE", "panda_db"),
    },
    "seekapa": {
        "host": _require_env("SEEKAPA_CRM_HOST"),
        "port": int(os.environ.get("SEEKAPA_CRM_PORT", "3306")),
        "user": os.environ.get("SEEKAPA_CRM_USER", "ai_support"),
        "password": os.environ.get("SEEKAPA_CRM_PASSWORD", ""),
        "database": os.environ.get("SEEKAPA_CRM_DATABASE", "panda_db"),
    }
}
```

**Note on IP literals in git history:** The IP addresses are already in git history. If these are production IPs, consider whether a history rewrite is warranted — that is a human-gated decision. The code fix above removes the defaults going forward.

**KV refs to add** (wire in Function App app-settings):
```
AXIA_CRM_HOST=@Microsoft.KeyVault(VaultName=kv-seekapa-apps;SecretName=AxiaCrmHost)
SEEKAPA_CRM_HOST=@Microsoft.KeyVault(VaultName=kv-seekapa-apps;SecretName=SeekaCrmHost)
```

**Needs-you:** Verify `AXIA_CRM_HOST` and `SEEKAPA_CRM_HOST` are already set in the deployed Function App's app-settings before merging this change (or the app will crash at module import time). Check with: `az functionapp config appsettings list --name axia-seekapa-crm --resource-group <rg> | jq '.[] | select(.name | startswith("AXIA_CRM"))'`

---

---

## Item N: PostToolUse PII gate — wire `pii-scrub.py --check` on Write/Edit

**Why not auto-applied:** A broken PostToolUse hook blocks EVERY write in every session.
Human review required before wiring. See `~/.claude/bin/pii-scrub.py` (chmod +x, stdlib-only).

**What this does:** After any `Write` or `Edit` tool call, run the PII/secret scanner on the
written file. If hits are found, print the locations and types to stderr. The hook exits non-zero
which causes Claude Code to surface the finding but does NOT roll back the write — this is a
warning gate, not a hard block (hard-block via PreToolUse if you want that instead).

**Prerequisite:** Verify `pii-scrub.py` is working first:
```bash
~/.claude/bin/pii-scrub.py --check /tmp/pii-fixture-dirty.txt   # should exit 1 with hits
~/.claude/bin/pii-scrub.py --check /tmp/pii-fixture-clean.txt   # should exit 0
```

**Ready-to-apply diff** — add to `~/.claude/settings.json` under `hooks.PostToolUse`:

```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ PostToolUse array @@
-    "PostToolUse": []
+    "PostToolUse": [
+      {
+        "matcher": "Write|Edit",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "python3 $HOME/.claude/bin/pii-scrub.py --check \"$(echo $TOOL_INPUT_JSON | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"file_path\",\"\"))')\"",
+            "timeout": 15
+          }
+        ]
+      }
+    ]
```

**Exact JSON block to paste** (replacing the `"PostToolUse": []` entry):

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "python3 $HOME/.claude/bin/pii-scrub.py --check \"$(echo $TOOL_INPUT_JSON | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"file_path\",\"\"))')\"",
        "timeout": 15
      }
    ]
  }
]
```

**Alternative — simpler shell script wrapper** (avoids inline Python in JSON):

Create `~/.claude/hooks/pii-scrub-post-write.sh`:
```bash
#!/usr/bin/env bash
# PostToolUse hook — fires after Write|Edit
# Claude Code sets TOOL_INPUT_JSON in the environment.
set -euo pipefail
FILE=$(echo "${TOOL_INPUT_JSON:-{}}" | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print(d.get("file_path",""))' 2>/dev/null || true)
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0
python3 "$HOME/.claude/bin/pii-scrub.py" --check "$FILE"
```

Then wire this script (cleaner JSON):
```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "$HOME/.claude/hooks/pii-scrub-post-write.sh",
        "timeout": 15
      }
    ]
  }
]
```

**Verification after wiring:**
1. `cat ~/.claude/settings.json | jq '.hooks.PostToolUse | length'` — should return 1
2. Write a test file containing `password = "test"` via Write tool — hook should fire and print the finding to stderr.
3. Write a clean file — hook should exit 0 silently.

**NOTE:** If `PostToolUse` currently has other hooks (e.g. meme playback from Item 1 above),
merge the arrays — do not replace. Add the pii-scrub entry alongside existing entries.

---

## Needs-you queue (items this run did NOT touch)

| # | Item | Why gated |
|---|---|---|
| 1 | Rotate `set_manager_role` / `JWT_SECRET` / test creds (adopt-backlog T0-1) | Live secret rotation — requires portal access |
| 2 | Export `NO_COLOR=1 PAGER=cat GIT_PAGER=cat` into rtk execution environment | Requires knowing rtk's env-injection config path; rtk docs unclear — verify with `rtk config show` |
| 3 | Add Azure MCP / GitHub MCP / ADO MCP (adopt-backlog T3-22) | Requires PAT creation in portal + KV write |
| 4 | Remove `cs-agent-main` hardcoded CRM IP default (adopt-backlog T0-6) | Code change — needs RED/GREEN cycle, out of scope for overnight config-only run |
