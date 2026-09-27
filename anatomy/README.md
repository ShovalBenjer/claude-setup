# anatomy/

Enforced standards for this repository. A book mechanism, an ADR, or a
review lesson becomes a standard here only when a running hook enforces
it: every row in `E-ROWS.md` names the exact check, test, or code path
that runs, and a row without a hook does not ship. Prose is not
enforcement.

- `E-ROWS.md`: the registry. Id, title, source issue, enforcement pointer, status.
- `e-rows/E-NNNN-<slug>.md`: one structured record per row (source,
  mechanism, enforcement pointer, how to run the check, status, non-goals).

Built by the `book-to-standard` pipeline: mined issue → E-row → hook →
tests → anatomy PR → review + green bar → merge.
