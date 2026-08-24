---
name: wizard
description: Generate an interactive bash wizard that walks a human through steps only they can perform. Use for credentials, OAuth connects, third-party dashboards, billing fixes, one-off migrations. Not for steps the agent can do itself.
---

# Wizard

A wizard is a bash script that walks a human, step by step, through a manual procedure
that is tedious to do by hand and tedious to re-explain every time. It opens each URL,
says exactly what to click and copy, captures the values, writes them where they belong
(`.env`, GitHub secrets), confirms at every stage, and shows how many stages remain.

The estate-specific case: NEEDS OPERATOR moments. 2026-08-23 alone produced three
(the sudoers drop-in, the Todoist OAuth connect, the GitHub Actions billing fix), each
delivered as a paragraph the operator had to parse. Each should have been one generated
`wizard.sh` run. When a turn ends with more than one operator-only step, generate the
wizard instead of the prose.

The UX is already solved by [template.sh](template.sh): stage progress, confirmation
gates, cross-platform URL opening (including WSL, which is this machine), hidden secret
entry, idempotent `.env` upserts, `gh secret`/`gh variable` writes, closing summary.
Your job is only to scope the procedure and author the stages. Never hand-edit the
library above the `STAGES` marker.

A wizard is ephemeral by default: written to the job's tmp dir or `scripts/`, deleted
when done. Commit it only when it is a repeatable setup path.

## Process

1. **Scope.** Read the repo first (`.env*`, README, workflows: every `secrets.*`
   reference is a value the wizard must produce). List the stages in order and what
   each captures; the human confirms, reorders, drops.
2. **Map each stage's journey.** The exact path: which URL, what to click, where the
   value appears, which variable it fills. Where the current UI is unknown, say so and
   check the docs; never invent steps.
3. **Author.** Copy template.sh, one `stage` per step in dependency order, set
   `TOTAL_STAGES`. Open the URL before asking for its value; `ask_secret` for secrets;
   `write_env` every persisted value; `confirm` before anything irreversible. Secrets
   captured this way stay out of the transcript, which is the same boundary the
   pii-handling rule draws: the agent never sees the value, only that a stage passed.
4. **Verify statically.** `bash -n`, shellcheck if present, `chmod +x`. Never run it
   end-to-end yourself: it opens browsers and blocks on the human. Check every captured
   value lands where step 1 said. Tell the human how to run it.

Adapted 2026-08-23 from mattpocock/skills `engineering/wizard` (MIT); template.sh
vendored verbatim from the same commit. Delta record:
docs/analysis/2026-08-23-pocock-skills-delta.md.
