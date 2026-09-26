# fleetview

Observability tooling for supervising several Claude Code sessions at once, per
`docs/analysis/2026-09-02-interaction-viz-and-agent-harness-research.md`. First
component: `catchup.py`, which reads the session JSONL Claude Code writes under
`~/.claude/projects/` and produces a catch-up digest, structural facts always
(prompts, tools, files touched, commands, tokens), plus an optional headless
`claude -p` narrative on top. It replaces pasting whole transcripts into
another model and asking for a summary.

```bash
python tools/fleetview/catchup.py list                 # sessions, newest first
python tools/fleetview/catchup.py digest --no-llm      # newest session, offline
python tools/fleetview/catchup.py digest --he          # narrative digest in Hebrew
python tools/fleetview/catchup.py digest --project myrepo --session 0cc9
python tools/fleetview/catchup.py selftest
```

Changes nothing about a live Claude Code setup: it only reads transcript files
that already exist, wires no hooks, and needs no settings.json entry. The
transcript schema is Claude Code's own and unversioned, so parsing is
defensive and unrecognized row types are reported, not fatal.
`CLAUDE_PROJECTS_DIR` overrides the transcript root for tests.
