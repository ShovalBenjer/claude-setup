# WhatsApp self-notes links versus planned work, 2026-08-23

Point-in-time scan. Source: the operator's own WhatsApp group `972528034567-1603902193@g.us`
(438 messages, 2025-08-23 to 2026-08-23 00:53), decrypted locally with the whatsapp-query
skill on 2026-08-23 and read from 2026-07-15 onward (87 lines). Nothing from the store is
quoted beyond link titles. The Gemini-extracted 91-entry list the operator pasted is imported
beside this file as `2026-08-23-whatsapp-repo-reminder-list.md`.

## What was not updated

- 10 repos the operator saved were in no ledger at all: gossip and Agent-Reach (saved
  2026-08-23 00:51), firstmate, the-open-engine/zeroshot, dogwood, gsd-build/get-shit-done,
  junfanz1/Awesome-AI-Review, NOVA_claude-code-mcp-guide, molson194/AI-CS188,
  omernesh/bookmark-everything, renenel/agent-brain (agent-brain had a resource-ledger row but
  no external-repos row). All 10 now have `external-repo.v1` rows with `gh api` metadata and
  verdict `untriaged`. Three were missed by earlier diffs only because the upstream repo was
  renamed after the link was saved.
- 9 non-GitHub links were never recorded: arxiv 2601.10700 (2026-07-25), canonmail.com,
  the Modal Kimi K3 post, ecc.tools/skills, two awesomeclaude.ai pages (2026-07-29),
  detectionskills.io (2026-08-06), hamel.dev/talks (2026-08-18), arxiv 2310.01405 and
  janwehner.com (2026-08-19, representation engineering). All 9 now have `see` rows.
- `state/external-repos.jsonl`: 103 of 115 rows were `untriaged` before this session, now
  113 of 125. The saved-link pipeline captures and does not decide. That is the actual
  "weren't updated": not missing rows, missing verdicts.
- `tools/intent/resources.py coverage` reports 0.7% of seen resources ever reasoned about.
- `resources.py verify` breaks at row 3893 (`RES-eb4c44ca6df9` names a prev that is not the
  previous row). The break predates this session's appends (the file had 3897 rows on main)
  and nothing in the gate runs `verify`, so a hash-chained ledger has been unverified since at
  least the last clone-to-clone merge. Lesson row appended.

## Saved repos against the plan (dated by the WhatsApp message)

| saved | repo | ledger verdict | where the plan already names it |
|---|---|---|---|
| 07-20 | mattpocock/skills | untriaged | 76 doc refs, issues #6 #11 #12 #13 #19 #27 #38 #50 #56 |
| 07-24 | just-my-skills | untriaged | TODO.md, issues #11 #56 |
| 07-25 | impeccable | adopt-patterns | repo-compare-ui-ux, no issue |
| 07-25 | dolt | untriaged | 17 doc refs (estate audit, where-we-stand), no issue |
| 07-26 | HyperAgents | concepts-only | absorption batch 07-30 |
| 07-26 | MemRL | untriaged | absorption batch 07-30 only |
| 07-30 | agent-client-protocol | adopt-candidate | issue #13 (ACP bridge EPIC) |
| 07-30 | no-ai-slop | adopt-patterns | issues #10 #19 |
| 08-05 | reposwarm | adopt-patterns | TODO.md, repo-compare-ui-ux, no issue |
| 08-07 | dogwood | untriaged (new row) | repo-compare-ui-ux mention only |
| 08-11 | agent-brain | untriaged (new row) | repo-compare-ui-ux mention only |
| 08-20 | equity-research-skill | untriaged | ledger only |
| 08-23 | gossip | untriaged (new row) | nothing |
| 08-23 | firstmate | untriaged (new row) | nothing |
| 08-23 | Agent-Reach | untriaged (new row) | nothing |

Reading: the July saves were absorbed into issues within days (ACP became #13, no-ai-slop
fed #10 and #19). From 2026-08-05 on, nothing saved reached an issue. The absorption loop
stopped when the repo-compare sessions stopped, and the ledger kept filling.

## What this session did with it

- A single GitHub issue carries the 15-row table above as a checklist, one box per repo, so
  the next repo-compare session has a list rather than a ledger to grep.
- The three 2026-08-23 saves (gossip, firstmate, Agent-Reach) are the ones with the closest
  fit to open work: gossip is a cross-session correspondence fabric, which is the bus
  (`tools/bus`) and the proposal rows in charters.md; firstmate is a crew orchestrator, which
  is the Gastown map; Agent-Reach is a multi-platform read CLI, which overlaps the Exa and
  alphaXiv connectors. Each is a repo-compare candidate, not an adopt.

## Not done here

- No verdicts were written beyond `untriaged`. A verdict needs a source read, and this
  session's scope was the sync, not the triage.
- The resource-ledger chain break is recorded, not repaired. Repairing a hash chain means
  rewriting history in an append-only file; that is the operator's call.
