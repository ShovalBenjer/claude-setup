# Prompt triage: 354 claude-setup tickets, 18 checklist issues, 2026-08-23

Point-in-time scan. The operator's ask, in his own words on this date: "ensure every prompt
request is turned into a checklist task on todoist + github issue connected ticket to it",
with the note "i think its requested many times already". It was: PT-b44c264535ea (07-29),
PT-953b874d9b8a (07-30), PT-8eb53ff760e0 (07-30), PT-073ef92993c9 (08-10),
PT-b93a3be202a3 (08-10), PT-a66b82775130 (08-12), PT-706a81097829 (08-17), and this one.
Eight times in 26 days. Issue #91 holds all of them as boxes.

## What was true before this session

- `render_todo.py list` for this repo: 348 awaiting triage, 0 workable, 6 rule-classified,
  354 total. `state_transitions` in `~/.intent/intent.db` held 350 rows, every one of them
  `'' -> CAPTURED`. Nothing had ever moved a ticket past capture.
- 282 of the 426 unique prompts had no transition row at all; `render_todo.py` reads a
  missing row as CAPTURED, so they counted as inbox without being in the ledger's lifecycle.
- `state/prompt-tickets.jsonl` (the git mirror) already had 25 chain breaks from parallel
  sessions appending at the same tip. `tickets.verify` runs only on test fixtures.
- Todoist: no API token on the machine, no Zapier connection. The CSV import is the path
  that needs nothing but a click from the operator.

## Method

1. Dumped every event with `repo_path like '%claude-setup%'` joined to the mirror by
   `text_sha`: 480 events, 426 unique prompts, 424 with a `PT-` id.
2. Read all 426 (the dump is 134 KB; two Read calls). Hand-clustered into 17 work themes
   plus one other-lane bucket. Multi-request prompts went to their dominant theme; the box
   carries the whole prompt, so the minor requests are not lost, only filed under the
   neighbour.
3. One GitHub issue per theme, title `Txx <theme>`, body marker `<!-- prompt-triage:Txx -->`
   for idempotent re-runs, one `- [ ]` per prompt with its `PT-` id, date, and the first
   170 characters verbatim.
4. Transitions written twice, as the design requires: `state_transitions` in the intent
   store (actor `lane-A session 3b140585`, reason names the issue) and a chained row in
   `state/prompt-tickets.jsonl` via `tickets.append_chained`. 424 in the first pass, 53
   duplicate captures (same text, different id per session) in the second, 2 by hand.
5. `render_todo.py` learned to group TRIAGED tickets by the issue named in the reason. Before
   that change, a fully triaged inbox rendered as "0 workable, 0 awaiting" and nothing else.
   Test added: `test_triaged_tickets_render_as_issue_pointers_not_a_blank_inbox`.

## Result

| | count |
|---|---|
| TRIAGED into issues | 219 (render_todo count; 263 + 53 + 2 transitions, minus worktree-path rows the renderer files elsewhere) |
| NOT_WORK | 135 rendered, 161 + duplicates transitioned |
| awaiting triage after | 0 |
| issues created | #91 to #108 |
| Todoist import | `~/.intent/exports/todoist-import-2026-08-23.csv`, 283 rows, 18 parents with the issue URL as description and the prompts as indented subtasks |

Themes by prompt count: #94 launcher/WSL/kitty 32, #108 other-lane 29, #93 external repos
20, #99 self-hosting and models 18, #101 enforcement and standards 17, #92 docs
consolidation 16, #97 personas 18, #91 traceability 17, #100 research program 16, #95 buzz
TUI 14, #98 providers 14, #102 operator communication 12, #106 WSL leftovers 8, #103 skills
7, #107 memory and RAG 6, #96 GitHub PM 5, #104 books 5, #105 usage and cost 4.

## What the clustering says

- The single most repeated request cluster is the launcher and terminal (#94, 32 prompts
  across 07-30 to 08-23). The `.lnk` chooser was reported broken or stale on 07-30, 07-31,
  08-05, 08-12 (four times that day), and 08-23. Issue #9 existed for it the whole time.
- The second is "where did my requests go" (#91) and "we are drowning in .md files" (#92),
  which are the two halves of this session.
- 135 of 354 prompts are acks, status checks, notifications, or cross-session messages.
  That is the operator spending 38% of his turns asking whether work happened, which is
  the cost calibrated-claims.md was written about.

## Not done here

- No ticket moved past TRIAGED. OPEN requires someone to pick the box up; that is the
  next session's work, per theme, and `render_todo.py` will show OPEN rows as workable.
- Todoist is not written to. The CSV is on disk; the operator either imports it or connects
  Todoist through Zapier once (URL in the session report), after which a session can write
  tasks directly.
- The 25 pre-existing chain breaks in the mirror, and the new fork this branch creates at
  merge, are not repaired. Same class as L-2026-08-23-a.
