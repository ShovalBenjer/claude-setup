---
name: pii-scrubber
description: Scan outputs, deliverables, and staged diffs for PII (names, emails, phone numbers, national-IDs, CRM fields) before they are written or committed. Pseudonymizes or blocks on detection. Triggers on "/pii-scrub", "mask the PII", "scrub before commit", "any PII in this?", pre-write/pre-commit hooks. Companion PreToolUse hook documented below — not auto-wired.
model: sonnet
allowed-tools: ["Bash", "Read", "Write", "Grep"]
---

# PII Scrubber — output/commit gate

## When to invoke

- User says `/pii-scrub`, "mask the PII", "scrub before commit", "any PII in this?"
- Before writing a file that came from CRM export, eval harness row, Chatwoot dump, training dataset, or any Azure Blob containing customer data
- Before `/commit-push-pr` when the staged diff touches `*.csv`, `*.json`, `*.parquet`, `*.xlsx`, `eval/`, `data/`, `fixtures/`, `exports/`, `chatwoot*`
- PreToolUse hook fires (see below) on `Write(*)` and `Bash(git commit*)` — the hook calls this skill if PII signals are present

## SKIP conditions

- Target is a pure code file with no data rows: `*.py`, `*.ts`, `*.tsx`, `*.js`, `*.md`, `*.toml`, `*.yaml`, `*.bicep`, `*.tf` — unless the file embeds a string literal that looks like a real email or phone
- File is under `tests/fixtures/` and uses clearly synthetic names (e.g. `John Doe`, `example@test.com`, `050-000-0000`)
- User provides explicit `[pii-ok: <reason>]` annotation in the commit message or task context
- Target is a schema definition, migration, or type declaration (no data values)

---

## Detection taxonomy

### Tier 1 — High-confidence patterns (always block or pseudonymize)

| Signal | Regex / heuristic |
|---|---|
| Israeli national ID (teudat zehut) | `\b[0-9]{9}\b` near column name `id_number`, `tz`, `teudat` |
| Email | `[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}` |
| Israeli phone | `\b(05[0-9][-\s]?\d{7}|\+972[-\s]?5[0-9][-\s]?\d{7})\b` |
| International phone | `\+?[1-9]\d{6,14}` near column name `phone`, `mobile`, `tel` |
| Credit card (PAN) | Luhn-valid 13–19 digit sequence |

### Tier 2 — Context-dependent (flag, ask before blocking)

| Signal | Heuristic |
|---|---|
| Full name | Column header is `name`, `full_name`, `customer_name`, `contact_name` + value has 2+ capitalized words |
| Free-text with email or phone embedded | Long string field value matching Tier 1 inside it |
| CRM lead fields | Keys: `lead_id`, `crm_id`, `customer_id` paired with any Tier 1 value in the same row |
| Passport / driver licence | Columns named `passport`, `license`, `dl_number` |

### Tier 3 — Low-signal / report only

- Columns named `ip`, `device_id`, `session_id` — flag presence, don't block
- Base64 blobs > 200 chars inside JSON fields — flag as potentially encoded PII

---

## Scan procedure

### For a file path target

```
1. Determine file type (CSV / JSON / Parquet / plain text / diff hunk)
2. For CSV/TSV: inspect headers only first → report Tier 1/2 column hits
   Use: mise exec -- mlr --ocsv head -n 5 <file>   # NEVER dump full table
3. For JSON: jq -r '[keys[]]' to list top-level keys; sample 3 values per key
4. For Parquet: DuckDB schema + DESCRIBE; sample 3 rows with LIMIT 3
5. Match each sampled value against Tier 1 patterns
6. Report: {file, column/key, tier, sample_count_hit, action}
   Report PRESENCE only — never echo the actual PII value
7. If Tier 1 hits: BLOCK write/commit; propose pseudonymization map
8. If Tier 2 hits: surface to user for explicit OK before proceeding
9. If Tier 3 only: annotate output with warning, allow proceed
```

### For a git diff target

```
1. git diff --cached (staged) or git diff HEAD (working tree)
2. Extract only added lines (prefix "+") from diff hunks
3. Run Tier 1 regex against added lines
4. Any hit → block commit, report line number + column name, never echo the value
5. User must either: pseudonymize the data, or add [pii-ok: <reason>] to commit msg
```

---

## Pseudonymization map

When scrubbing is requested (not just detection), replace values deterministically:

| Type | Replacement |
|---|---|
| Email | `user_<sha256[:6]>@example.invalid` |
| Phone | `+972-50-000-NNNN` where NNNN = sha256[:4] of original |
| National ID | `000000000` + preserve check-digit position |
| Full name | `Contact_<sha256[:6]>` |
| Free-text with embedded PII | Replace matched span inline, preserve surrounding text |

Pseudonymization is applied in-place via `sd` (PCRE2):
```bash
mise exec -- sd '<pattern>' '<replacement>' <file>
```

Always produce a `pii-scrub-map.json` alongside the target with before-sha → after-sha pairs so the mapping is reversible if needed. Never write the original values into the map — only the sha256 of the original.

---

## Output format

```
PII SCAN RESULT
  Target: <path or "staged diff">
  Scanned: <N rows sampled / N added lines>
  Tier 1 hits: <count>  → BLOCKED
  Tier 2 hits: <count>  → NEEDS APPROVAL
  Tier 3 hits: <count>  → WARNING

  Findings:
    [TIER1] <file>:<column/line>  type=email  hits=3   (values not shown)
    [TIER2] <file>:<column/line>  type=full_name  hits=12
    ...

  Action required:
    a) Run /pii-scrub --fix <file> to pseudonymize in place
    b) Add [pii-ok: <reason>] to commit message if data is already synthetic
    c) Remove the file from the staged set
```

---

## CLI gate — `pii-scrub.py`

A stdlib-only Python scanner lives at `~/.claude/bin/pii-scrub.py`.
Run it **before writing any deliverable** and after any agent/workflow output is generated.

```bash
# Check a file — prints file:line <PATTERN-TYPE> per hit, no secret values, exits 1 on hit
~/.claude/bin/pii-scrub.py --check <file>

# Redact in place — replaces matches with <REDACTED>
~/.claude/bin/pii-scrub.py --redact <file>

# Pipe mode (stdin → stdout redacted)
cat report.txt | ~/.claude/bin/pii-scrub.py --redact
```

Patterns covered: `email`, `israeli-phone`, `international-phone`, `national-id-shaped`,
`tabular-pii-header` (`first_name` / `last_name` / `email` / `phone` / `full_name`),
`password-assignment`, `api-key`, `secret-assignment`, `bearer-token`, `aws-access-key`,
`connection-string` (`Account=` / `Pwd=` / `Password=`), `pem-private-key`.

**Gate protocol:**
1. Agent produces output text or writes a file.
2. Run `pii-scrub.py --check <file>`. If exit 1 → do NOT deliver; run `--redact` or abort.
3. If exit 0 → proceed with write / commit / send.

**Never print matched values** — the tool enforces this; `--check` outputs type + line number only.

---

## Companion PreToolUse/Stop hook (not wired — document only)

A hook that fires this skill automatically requires wiring in `.claude/settings.json` under `hooks.PreToolUse`. The hook logic is:

**File:** `~/.claude/hooks/pii-scrubber-hook.sh`

```bash
#!/usr/bin/env bash
# PreToolUse hook — fires before Write(*) and Bash(git commit*)
# Claude Code passes: TOOL_NAME, TOOL_INPUT_JSON via env or stdin
# Exit 2 to block the tool call; exit 0 to allow.

set -euo pipefail
TOOL="${TOOL_NAME:-}"
INPUT="${TOOL_INPUT_JSON:-}"

# Only intercept Write and git commit
if [[ "$TOOL" == "Write" ]]; then
  FILE=$(echo "$INPUT" | jq -r '.file_path // empty')
  # Skip pure-code files
  if [[ "$FILE" =~ \.(py|ts|tsx|js|md|toml|yaml|bicep|tf)$ ]]; then exit 0; fi
  # Delegate to Claude skill for data files
  echo "PII_SCRUBBER: data file detected — invoking /pii-scrub on $FILE"
  exit 2   # block; Claude should invoke the skill and re-evaluate
fi

if [[ "$TOOL" == "Bash" ]]; then
  CMD=$(echo "$INPUT" | jq -r '.command // empty')
  if [[ "$CMD" =~ "git commit" ]]; then
    STAGED=$(git diff --cached --name-only 2>/dev/null || true)
    DATA_FILES=$(echo "$STAGED" | grep -E '\.(csv|json|parquet|xlsx)$' || true)
    if [[ -n "$DATA_FILES" ]]; then
      echo "PII_SCRUBBER: data files staged — run /pii-scrub before committing"
      exit 2
    fi
  fi
fi

exit 0
```

**To wire it** (human-gated — add to needs-you queue):
```json
// .claude/settings.json  →  hooks section
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Bash",
        "hooks": [{ "type": "command", "command": "~/.claude/hooks/pii-scrubber-hook.sh" }]
      }
    ]
  }
}
```

Wiring this hook requires editing `.claude/settings.json` — use `/update-config` when ready.

---

## Integration with forge loop

- **SPEC axis**: this skill itself is the spec; no separate doc needed unless a project adds custom PII column lists
- **PREMORTEM**: five failure modes
  1. Regex false-negative on obfuscated email (`user[at]domain[dot]com`) — accept risk, flag free-text fields
  2. Parquet/Avro binary formats bypassing text scan — always use DuckDB DESCRIBE + sample, never skip
  3. `[pii-ok]` token abused as a blanket bypass — treat as a one-commit escape, not a file-level exemption
  4. Hook exit-2 loop if Claude re-invokes Write without fixing — cap retry at 2, then escalate to user
  5. Pseudonymization map written to a committed file — `pii-scrub-map.json` must be in `.gitignore`

## Notes

- Never read, echo, or log actual PII values — report column names, hit counts, and type only
- `pii-scrub-map.json` must be listed in `.gitignore`; add it if missing before first use
- For Chatwoot conversation exports: Tier 2 applies to `contact.name`, `contact.email`, `phone_number` fields — these are real customer data
- For eval harness rows: `ground_truth` and `expected_output` fields may contain customer names extracted from call transcripts — scan those fields explicitly
