# A5. PST/Email -> Action Mining

Schedule: Mondays 7:30 AM
Repo root: latest PST ingestion output
Mode: read + ADO work items + summary file

Read the latest PST-extracted index, assumed at one of:

- `~/.claude/cache/pst/latest.jsonl`
- `~/.claude-ink-tui/data/pst-index.jsonl`
- the configured path if another one exists locally

For each message in the last 7 days where:

- `shoval` is on To/Cc, or
- subject mentions one of: `cs-agent`, `hr-agent`, `campaign-analysis`, `call-analyzer`, `Chatwoot`, `Foundry`, `SIU`, `figma-4-all`, `Onesignal`, `Copilot Studio`, `RTK`, or
- body contains an action verb addressed to `you` within 3 lines of `shoval`

Extract:

- `ACTION ITEM`: one sentence, infinitive form, for example `investigate X` or `decide on Y`.
- `DEADLINE`: if mentioned.
- `BLOCKER`: what is needed to act.
- `THREAD LINK`: Outlook URI if available.

Output `~/.claude/docs/EMAIL_ACTIONS_<DATE>.md` ranked by deadline proximity.

For any item with a deadline within 5 days and no existing matching ADO work item, file via:

```bash
~/.claude/bin/work-item.sh create --type Task --tags "email-derived"
```

Do not include email body content in the work item description. Only include the extracted action sentence. Privacy: never log full email bodies to disk outside the input path.
