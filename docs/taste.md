# Taste ledger

Design picks the operator made, with the reason in one line. `/diverge` writes here
after every non-mechanical decision, and future creative work reads it before
sampling candidates. The research position is that no automated taste model works
yet, so a human-curated corpus is the state of the art. This is that corpus.

Append only. One row per decision. Never rewrite a row: if a pick is reversed, add a
new row that supersedes it by date and say what changed.

| Date | Decision | Pick | `p_conventional` | Reason |
|---|---|---|---|---|
| 2026-07-29 | Tamper-evidence for `state/prompt-tickets.jsonl`, given that `bus.py::canonical()` hashes a fixed `CHAIN_FIELDS` tuple that covers none of a ticket's content fields | Self-describing rows: each row carries `chain_fields`, and `canonical()` hashes the named fields plus the list itself | 0.10 | A row becomes verifiable by a reader that knows no schema, and shrinking a row's coverage changes its hash instead of hiding. The rejected default put coverage in a constant far from the data, which is what let the original defect exist. |

## Notes on the 2026-07-29 pick

The defect being fixed is worth stating, because it is a category this repo keeps
finding rather than a one-off. `CHAIN_FIELDS` names `id`, `ts`, `from_lane`,
`origin_lane`, `from_session`, `to`, `kind`, `subject`, `body`, `refs`, `prev`. A
prompt-ticket row carries `id`, `ts`, `session`, `repo`, `branch`, `text_sha`,
`state`, `prev`. The intersection is three keys. Had the spec's instruction to import
`canonical` been followed literally, every ticket row would have shipped with a hash
committing to its id, its time, and its predecessor, and to nothing about the ticket.
`row_altered()` would have returned False after an edit to `state` or `text_sha`.

That is the same class as the waiver whose reason is never checked (L-2026-07-29-c)
and the confidence gate with no stored outcomes (L-2026-07-27-d): an accountability
mechanism that is present, runs, reports success, and is structurally incapable of
failing. The pick was made on which option makes that class detectable, not on which
option was smallest.

Constraint killed during defixation: "a hash payload should be a fixed schema
constant." That was inherited from fixed-header chain designs and from how `bus.py`
happens to be written. The real requirement is only that a verifier can recompute the
bytes, and a declared list satisfies it strictly better than a constant the verifier
must already possess. Cost is about sixty bytes per row.

## 2026-07-29 — Naming the split writing site: case-ledgers

Decision: the writing site (formerly daily-deep-learning.pages.dev/writing/) deploys
to Cloudflare Pages project `case-ledgers`. Candidates carried conventionality
estimates per the out-of-distribution rule: the-bench (p 0.25, publication named for
its flagship essay), case-ledgers (p 0.35, names the genre; the site's own subtitle
is "Case ledgers and working notes"), ktav-yad (p 0.15, Hebrew anchor), shoval-writing
(p 0.9, the mode, rejected). The operator was asked twice and did not pick; the-bench
ranked first and was attempted, and failed on a fact, not a preference:
the-bench.pages.dev is a third party's Access-walled project, discovered when the
deploy returned "Project not found" [8000007]. case-ledgers was the next candidate
that survives both the taste ordering and the global namespace. The anchor is the
site's own subtitle, so the grounding is auditable in the artifact itself.
Renaming later is one variable in deploy.yml plus _redirects plus canonicals.
