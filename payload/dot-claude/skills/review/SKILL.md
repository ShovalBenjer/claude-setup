---
name: review
description: PR precheck review — composites codex-call code review + testing-pyramid gap plan + heidegger-reflect into a single structured thread posted to Azure DevOps via the azure-devops Python SDK or `az devops invoke`. Triggers on "/review", "before merge", "PR precheck", "review this PR", "review PR #<n>".
skip-if: >
  No PR context is present (no PR number, no ADO remote, and no active branch with an
  open PR). Also skip if the diff is empty. Do NOT skip just because CI is green — the
  skill adds human-oriented signal CI cannot produce.
model: sonnet
---

# /review — PR precheck

Composite skill: Codex review + test-gap plan + reflection → single structured ADO PR thread.

## Two execution paths

| Path | When | Entrypoint | Posts via |
|---|---|---|---|
| **Interactive** | Developer runs `/review` in Claude Code | This SKILL.md (steps 1–7 below) | `work-item.sh` or azure-devops SDK |
| **CI** | `Build.Reason == PullRequest` in ADO pipeline | `scripts/codex_pr_review.py` | one resolvable thread per finding, direct via ADO REST (`pullRequestThreads`) |

Interactive posts one composed thread; CI posts one resolvable thread per finding (dedup on
re-run). See the CI path section for the live comment-handling flow.

---

## ONE HUMAN PREREQUISITE — STOP IF MISSING

The Build Service identity for the ADO project must have **"Contribute to pull requests"**
on the repository. Without this the posting step returns HTTP 403.

**Check / grant:**
```
ADO Portal → Project Settings → Repos → axia-seekapa-cs-agents
           → Security → "<Corp-AI> Build Service (<org>)"
           → Contribute to pull requests → Allow
```

If this permission is absent:
- Interactive path: write the review body to `/tmp/review-pr-<N>-<ts>.md`, print manual-paste instructions, stop.
- CI path: `codex_pr_review.py --soft-post-fail` exits 0 (build stays green); the Foundry review is logged in the pipeline output.

Add to the `needs-you` queue and do NOT retry posting until permission is confirmed.

---

## When to use

- Before merging any branch to master/main
- User types `/review`, "review PR #N", "precheck before merge"
- Automated overnight precheck (Gastown job)

## When NOT to use

- Diff is empty
- No ADO remote (GitHub-only repo — use `gh pr review` directly instead)
- Already posted a review thread this session for the same PR SHA (idempotency guard)

---

## Interactive path (steps 1–7)

### Step 1 — Resolve PR context

```bash
PR_NUMBER="${ARGS:-}"
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
```

Parse the ADO org + project + repo from the remote URL:

```
https://i-sdd@dev.azure.com/<ORG>/<PROJECT>/_git/<REPO>
git@ssh.dev.azure.com:v3/<ORG>/<PROJECT>/<REPO>
```

If `PR_NUMBER` is empty, look it up:

```bash
az devops configure --defaults organization=https://dev.azure.com/<ORG> project=<PROJECT>
az repos pr list --repository <REPO> --source-branch "$BRANCH" --status active --query "[0].pullRequestId" -o tsv
```

If still empty, stop and ask the user for the PR number.

#### projects.json

Per-project overrides live at `.claude/projects.json` in the repo root. The review skill
reads this file if present; all keys are optional (fallback to git-remote parsing):

```jsonc
{
  "ado": {
    "org": "i-sdd",
    "project": "Corp-AI",
    "repo": "axia-seekapa-cs-agents"
  },
  "review": {
    "base_branch": "master",
    "codex_effort": "high",
    "post_thread": true      // false → dry-run (print only, no post)
  }
}
```

---

### Step 2 — Gather diff

```bash
BASE=$(jq -r '.review.base_branch // "master"' .claude/projects.json 2>/dev/null || echo "master")
git fetch origin "$BASE" --quiet
DIFF=$(git diff "origin/$BASE"...HEAD -- '*.py' '*.ts' '*.tsx' '*.js')
FILES=$(git diff --name-only "origin/$BASE"...HEAD)
```

If `DIFF` is empty, log "no diff vs $BASE" and stop cleanly.

---

### Step 3 — Codex review (Part A)

Effort from `projects.json` → `review.codex_effort` (default `high`).

Invoke the codex-call skill (or inline if unavailable) with this prompt structure:

```
## PART A — Code Review

Findings in three sections:

### BLOCKING
Correctness bugs, security issues, broken contracts.
Format: **[BLOCKING]** `file:line` — description — suggested fix

### SUGGESTION
Non-blocking improvements: readability, performance, observability.

### NITPICK
Style, naming. Max 5 items.
```

Pipe `$DIFF` as context. Write output to `/tmp/review-codex-$PR_NUMBER.md`.

---

### Step 4 — Testing-pyramid gap plan (Part B)

Invoke the testing-pyramid skill scoped to the changed files, or produce inline:

- For each changed public function/class: note missing unit / integration / contract / e2e coverage
- Output as markdown checklist under `### TEST GAPS`
- If a path is already well-covered, mark `[covered]`

---

### Step 5 — Heidegger reflection (Part C)

Compressed to 4 bullets under `### REFLECTION`:

1. **Revealed** — what the diff actually changes vs what the PR description claims
2. **Concealed** — what the diff does NOT address (scope gaps, deferred TODOs)
3. **Mechanism** — dominant pattern in the code (e.g. "defensive null-checks throughout")
4. **Action space** — what the reviewer must decide before merging

---

### Step 6 — Compose thread body

```
## PR Precheck — <PR_TITLE> (#<PR_NUMBER>)
_Generated by /review skill — <ISO8601 timestamp> — diff base: origin/<BASE>_

### Code Review
<Part A — trimmed to ≤ 4000 chars if longer>

### Test Gaps
<Part B checklist>

### Reflection
<Part C 4 bullets>

---
_BLOCKING findings require resolution before merge.
SUGGESTION / NITPICK are advisory._
```

---

### Step 7 — Post to ADO PR

#### Auth

- **CI** (`$SYSTEM_ACCESSTOKEN` set): pass to `work-item.sh` via env — never echo.
- **Local** (`az login` active): `work-item.sh` uses ambient session automatically.

Presence check only: `[ -n "${SYSTEM_ACCESSTOKEN:-}" ] || echo "using ambient az login"`.

#### Primary — work-item.sh (az devops invoke)

```bash
# Build the body file first
cat > /tmp/review-thread-body.md << 'EOF'
<composed thread body>
EOF

bash ~/.claude/bin/work-item.sh comment "$PR_NUMBER" /tmp/review-thread-body.md
```

`work-item.sh` constructs and executes:
```
az devops invoke
  --area git
  --resource pullRequestThreads
  --route-parameters project=<P> repositoryId=<R> pullRequestId=<id>
  --http-method POST
  --api-version 7.1
  --in-file <json>
  --org https://dev.azure.com/<ORG>
```

The JSON payload is built via `jq` (safe escaping — no raw heredoc injection):
```json
{
  "comments": [{"parentCommentId": 0, "content": "<body>", "commentType": 1}],
  "status": 1
}
```

#### Fallback — azure-devops Python SDK

Use only if `work-item.sh` is unavailable or `az` CLI is not installed:

```bash
uv venv /tmp/review-venv --quiet
uv pip install azure-devops msrest --quiet --python /tmp/review-venv/bin/python
/tmp/review-venv/bin/python - <<'PY'
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import os, pathlib

token   = os.environ["AZURE_DEVOPS_TOKEN"]   # injected; never echoed
org_url = f"https://dev.azure.com/{ORG}"
body    = pathlib.Path("/tmp/review-thread-body.md").read_text()

creds  = BasicAuthentication("", token)
conn   = Connection(base_url=org_url, creds=creds)
git    = conn.clients.get_git_client()

thread = {"comments": [{"content": body, "commentType": 1}], "status": 1}
result = git.create_thread(thread, REPO, int(PR_NUMBER), project=PROJECT)
print(f"thread_id={result.id}")
PY
```

#### Dry-run mode

If `projects.json` has `"post_thread": false`, or pass `--dry-run` to `work-item.sh`:
prints the constructed az command + payload (no secret values), exits 0.

---

## CI path — THE FLEET FLOW (comment handling, live 2026-07-08)

Every active project's pipeline runs a `CodexReview` stage on `Build.Reason == PullRequest`
that reviews the diff and posts findings as PR comment threads. This is the pre-PR flow: the
reviewer talks to the PR in comments, not a wall-of-text.

### Components

| File | Role |
|---|---|
| `scripts/codex_pr_review.py` | CI reviewer. Diffs `origin/<base>...HEAD`, calls the Foundry codex deployment, parses the review into findings, posts one thread per finding, dedups prior runs. Portable: drop it into any repo unchanged. |
| `azure-pipelines.yml` stage `CodexReview` | `dependsOn: []`, `continueOnError: true` (advisory, never blocks merge), `condition: eq(variables['Build.Reason'], 'PullRequest')`. Fetches the key + runs the script. |

### Auth — KEY, not the SP's AAD token

The pipeline service principal has Contributor (control-plane) but NOT the Foundry-User DATA
role, so `DefaultAzureCredential` → `responses.create` returns **403**. Fix that is live:
the stage fetches the AIServices key in-stage (Contributor can `listKeys`) and the script
prefers it:

```bash
export AZURE_AI_FOUNDRY_KEY="$(az cognitiveservices account keys list -n brn-azai -g AZAI_group --query key1 -o tsv)"
python scripts/codex_pr_review.py
```

The script builds an `OpenAI(base_url=<project>/openai/v1, api_key=..., default_headers={"api-key":...})`
client when `AZURE_AI_FOUNDRY_KEY` is set (key mode passes the backing model explicitly),
else falls back to `AIProjectClient` + `DefaultAzureCredential` for a local operator run.

### Model — SOTA Foundry codex

`AGENT_DEPLOYMENT = gpt-5.3-codex-CI-Reviewer` (model `gpt-5.3-codex`, the newest codex in the
brn-azai catalog; `gpt-5.4`/`gpt-5.5` are general/chat, NOT codex). Use the codex family for
code review, not the higher general version number.

### Comment handling (the point of this skill)

- `parse_findings(review)` splits the review on `[SEVERITY]` markers into
  `{severity, file, line, text}`.
- `post_findings(...)` posts **one Active (resolvable) thread per finding**, anchored inline to
  `file:line` (`threadContext.rightFileStart/End`); if the anchor is rejected it retries as a
  general thread. Each finding is resolved independently in the PR UI.
- `close_prior_codex_threads(...)` runs FIRST every re-review: it closes still-open threads from
  a prior run (matched by the `## Codex AI` content marker) so a re-run REPLACES rather than
  STACKS. `is_prior_codex_thread()` is the pure predicate (unit-tested).
- Empty-review guard: one retry on an empty completion (reasoning models occasionally return
  empty on a large diff).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Review posted; no CRITICAL finding (advisory, stage never blocks merge) |
| `1` | CRITICAL finding present (stage still advisory via `continueOnError`) |

### Rollout to a new project's pipeline

1. Copy `scripts/codex_pr_review.py` into the repo unchanged.
2. Add the `CodexReview` stage (dependsOn `[]`, PR-only condition, `continueOnError: true`)
   with an `AzureCLI@2` step that fetches the key and runs the script.
3. One human prereq per repo: the Build Service needs **"Contribute to pull requests"** on that
   repo (see above) or the POST returns 403 and no thread lands.
4. No RBAC/Foundry-User grant needed (key auth handles it).

---

## Output

On success:
```
Posted review thread to PR #<N> (thread_id=<ID>)
BLOCKING: <count>  SUGGESTION: <count>  NITPICK: <count>  TEST GAPS: <count>
```

On 403 (permission missing): write body to `/tmp/review-pr-<N>-<ts>.md`, print
manual-paste instructions, add to `needs-you` queue. Do NOT retry.

On any other error: print error, write partial output to `/tmp/review-pr-<N>-<ts>.md`.

---

## Safety

- Never read, echo, or log token values — presence check only.
- Never commit anything (this skill is read + post only).
- Never push branches.
- `$HOME` is a git worktree; never `git add` here.
- Codex `--full-auto` runs against `$PWD`, not `$HOME` — confirm CWD before invoking.
- Ephemeral venv at `/tmp/review-venv` — does not touch project dependencies.
- `work-item.sh` builds the JSON payload via `jq`, not string interpolation — no injection risk from review text containing quotes/backslashes.
