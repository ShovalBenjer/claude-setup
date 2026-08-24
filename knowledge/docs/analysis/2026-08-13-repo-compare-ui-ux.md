# Repo-compare: UI/UX layer over Claude Code (operator's saved list, category 1)

Date: 2026-08-13. Source list: `docs/תזכורת לעצמי- github repos + urls.md` (91 repos,
operator's chat-history audit). This run: the 8 strongest UI/UX candidates from
category 1, per the repo-compare cap. Cut (16, named so the cap is visible):
anthropics/claude-code (compared 2026-08-12), claude-code-router, claude-code-mcp-guide,
just-my-skills, mattpocock/skills, AI-Builder-Club/skills, ui-ux-pro-max-skill
(installed here), no-ai-slop (slop_lint covers it), agent-client-protocol,
open-code-review, get-shit-done, reposwarm, dogwood, rtk (deployed here),
Threejs-Awesome-Graphics-Agent-Skills, personal profiles (dilums, Dex4D).

Evidence class: README-only scan via `gh repo view` + `gh api .../readme` (first 200
lines), 2026-08-13, no clones, no execution. Verification of the mechanisms themselves
has not run.

## Verdicts

| repo | stars | verdict | one-line reason |
|---|---|---|---|
| amirfish1/claude-command-center | 117 | ADOPT (pattern only) | session dashboard reading `~/.claude` transcripts as source of truth; license is non-commercial so the pattern is adoptable, the code is not |
| breaking-brake/cc-wf-studio | 5,351 | WATCH | visual workflow AUTHORING canvas (React Flow), not a session monitor; relevant only if we want a skill-builder UI |
| pbakaus/impeccable | 58,567 | WATCH | 59 deterministic design-slop detector rules; a runnable oracle for out-of-distribution.md rule 3 if we build visual layers |
| ofekron/better-agent | 54 | WATCH | CCC-shaped multi-provider workspace, but README says Linux bootstrap unsupported and Windows unvalidated |
| affaan-m/everything-claude-code | 239,748 | IGNORE | skill/agent pack, competitor to Gastown registry, no UI layer |
| AgriciDaniel/claude-obsidian | 10,803 | IGNORE | knowledge-vault visualization, not session UI |
| aaif-goose/goose | 52,729 | IGNORE | competing agent runtime, not an observability layer |
| renenel/agent-brain | 7 | IGNORE | memory skill, no UI surface, no license stated |

## The ADOPT: claude-command-center's architecture, not its code

Its "Why this exists" section describes the exact shape our gap needs: the dashboard
owns nothing, it is a LENS over Claude Code's on-disk state (`~/.claude/projects/
*.jsonl` transcripts, `~/.claude/sessions/<pid>.json` live registry, hook-written
sidecars), deriving a "which session needs you" signal from the transcript. That maps
one-to-one onto what this harness already has: append-only `state/*.jsonl` ledgers,
Stop/Notification hooks, and (fixed 2026-08-13) a Windows-toast path. A local
dashboard that READS our ledgers and transcripts, without owning execution, closes the
operator's session-monitor gap while leaving the gate, bus, and skills untouched.
License blocks vendoring (non-commercial "other"), so this is a build-the-pattern
adoption, a separate claimed implementation session per the skill's hard limits.

## The negative finding that matters: nobody ships the buzz

The operator named "buzz" as the example. Across all 8 repos, none ships a Slack-style
notification bridge. CCC's nearest equivalents are a macOS `say` TTS button and a
delivery-health banner. So the buzz is not waiting in a repo to be adopted: our own
Notification-hook to Windows-toast path (fixed this session, pending the operator's
visual confirmation) IS the state of the art for this machine, and extending it
(per-event routing, quiet hours, a needs-input vs finished distinction) is homegrown
work, not absorption.

## What "more to edit" actually means, answered

The terminal config was never the lever. Running Claude Code full-screen, the visible
UX is (a) the TUI itself (Anthropic's, not editable), (b) toasts (ours, fixed, needs
eyeball), and (c) a dashboard beside the terminal (the ADOPT above, not yet built).
The concrete next implementation, if the operator claims it: a single-page local
dashboard reading `state/*.jsonl` + `~/.claude/projects/*.jsonl`, surfacing per-session
status and needs-you, pushing toasts through the existing hook. CCC's SSE-stream
row (`/api/sessions/events`, their v5.4.0) is the reference mechanism.
