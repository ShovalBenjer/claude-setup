---
name: jira-read
description: Read-only Jira access for qboservices.atlassian.net — fetch a single issue (description + comments + attachments, ADF flattened to plain text), list/download attachments, or run a JQL search. Auth via Azure Key Vault 'Shoval'/JIRA-API-KEY at call time (same pattern as jira-reminder-refresh.py), never written to disk. GET-only by construction — no create/update/transition/comment-post capability exists in this skill. Triggers on "/jira-read", "pull ticket <KEY>", "what's in DEV-XXXX", "fetch this jira issue", "search jira for", "what does the ticket say", "list attachments on <KEY>". SKIP for drafting new tickets locally (use jira-task-draft), posting a comment (draft first per jira-comment-drafting rule, human approves, then post), or if an `mcp__atlassian__jira_*` tool is connected this session — check ToolSearch first and prefer that over this REST fallback.
model: sonnet
---

# Jira Read (read-only)

**Invocation:** `/jira-read`, or any request to pull/inspect a specific Jira issue or run a JQL search.

## Before using this skill

Run `ToolSearch({query: "select:mcp__atlassian"})` (or similarly named). If an Atlassian/Jira MCP tool is connected this session, prefer it — it's a proper typed integration. This skill exists because that MCP is **not** connected in a plain Claude Code session as of 2026-07; it's the REST fallback for exactly that gap.

## Auth — no keys handled directly

Token comes from Key Vault `Shoval` / secret `JIRA-API-KEY`, fetched by `az keyvault secret show` inside `jira_read.py` at call time. It is never printed, never written to a file, never logged. Requires an active `az login` session (`DefaultAzureCredential`-adjacent — this script shells out to `az` directly rather than using the Python SDK, matching `jira-reminder-refresh.py`).

Verify before running anything:
```bash
az account show --query "{user:user.name}" -o tsv
```
Empty output → `az login` first.

## Operations

All of these are GET requests. Nothing in this script can create, update, transition, or comment on a ticket.

```bash
# One issue, human-readable (description + comments + attachments, ADF flattened to text)
~/.claude/skills/jira-read/jira_read.py issue DEV-5062

# Same issue, full raw JSON (for scripting / piping to jq)
~/.claude/skills/jira-read/jira_read.py issue DEV-5062 --raw

# Just the comments (e.g. to check who last replied)
~/.claude/skills/jira-read/jira_read.py comments DEV-5062

# List attachments (id, filename, size, date) — useful to confirm a local file
# actually matches what someone attached, by filename + byte size
~/.claude/skills/jira-read/jira_read.py attachments DEV-5076

# Download one attachment by its id (from the attachments listing above)
~/.claude/skills/jira-read/jira_read.py download 90405 /tmp/market_overview_handoff.zip

# JQL search — enumerate a ticket set before an audit/checklist pass
~/.claude/skills/jira-read/jira_read.py search 'project = DEV AND text ~ "Widgora" ORDER BY created ASC'
~/.claude/skills/jira-read/jira_read.py search 'assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC' --max 50
```

## When to reach for this vs. the reminder digest

`~/.claude/jira/reminders.json` (built by `jira-reminder-refresh.py`, refreshed on a schedule) already has a cheap digest of *flagged* tickets — assignee = you, stale or has an unanswered comment. Read that file directly for "what needs my attention right now." Reach for this skill instead when you need:
- The full content of a **specific** ticket (description, all comments, attachments) — the digest only carries the summary + flag reason.
- A ticket **not currently flagged** (closed, backlog, someone else's, or just not stale enough to surface).
- A **JQL search** across a ticket set, e.g. "every Widgora ticket" for a checklist/reconciliation pass.

## Boundaries

- **Never writes.** Creating, commenting, transitioning, or assigning stays human-in-the-loop: draft locally with `jira-task-draft`, or for a comment reply, draft per the `jira-comment-drafting` rule and post only after Shoval gives explicit per-comment OK.
- **Not a bulk export tool.** This is for targeted reads (one issue, one search, one attachment), not scraping the whole project. If a task wants "every ticket ever," pause and confirm scope first.
- **PII/secrets stay out of the token path.** The Jira token itself is never surfaced in output; issue content (summaries, descriptions, comments) may legitimately contain customer/business detail — treat that content per the normal `pii-handling` rule if it flows into any other artifact.

## Reconciling ticket content against the repo (checklist audits)

This skill answers "what does the ticket say," not "is it done." For a ticket-by-ticket implementation audit:
1. Pull the issue (`jira_read.py issue KEY`) and break the description + each comment into discrete tasks.
2. Ground each task against the repo per the PRD Control Plane rule: grep/read for the files named in the ticket, check git log for a matching commit, and where the ticket describes user-visible behavior, verify live (Playwright against a public route, or a local dev server for anything behind auth) rather than inferring from code alone.
3. Report done / partial / not-started / unclear per task, citing the evidence (file:line, commit sha, or a live observation) — not a blanket "ticket is done."

## Verification

```bash
az account show --query name -o tsv
[ -x ~/.claude/skills/jira-read/jira_read.py ] && echo "runner ok"
~/.claude/skills/jira-read/jira_read.py issue DEV-5062 | head -5
```
