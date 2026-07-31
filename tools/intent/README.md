# tools/intent

Turns an operator prompt into a tracked work item, and keeps a tamper-evident record
of that in git without putting the prompt text there.

`tickets.py` is the pure layer: ticket identity, the lifecycle allow-list, and the
hash-chained mirror at `state/prompt-tickets.jsonl`. It imports nothing from
`intent-control-plane`, deliberately, because that package is only importable from its
own venv and the root test suite runs under the system interpreter. Keeping the logic
here is what makes it testable at all.

`capture_turn.py` is the `UserPromptSubmit` hook entrypoint. It has both dependencies
and is the only file that does.

`resources.py` is the same idea applied to what gets handed to a session rather than
typed into it. It keys on a normalized URL or repository, so one resource spelled six
ways is one row set, and it separates a `seen` row from a `note` row on purpose: a bare
list of links records exposure, and calling that coverage is how 73 of 110 resources in
one week left no trace while the list looked healthy. `coverage` reports that ratio
rather than hiding it. A note points at the artifact holding the reasoning and never
carries the reasoning itself.

Two properties worth stating, because both were defects found while building this:

- A ticket id is derived from `{session_id, text_sha, occurrence_index}` and carries no
  clock and no randomness, so replaying the ledger reproduces it, and the historical
  prompt corpus can be given ids without inventing provenance.
- Rows declare the fields their hash covers, and the declaration is itself covered.
  `bus.py`'s `CHAIN_FIELDS` is a message-passing vocabulary; a ticket row hashed against
  it would commit to its id, its timestamp and its predecessor, and to nothing about the
  ticket. See `docs/taste.md` for the decision and what was rejected.

The lifecycle is an allow-list, not a deny-list. A deny-list answers "is this edge
forbidden", which permits every edge nobody thought to forbid.
