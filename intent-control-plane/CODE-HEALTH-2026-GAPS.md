# Code health 2026: gaps and open tasks

> Generated 2026-06-29 against src/intent_control_plane/. Agent-pickup-ready.
> Companion doc: TESTING-SOTA-2026-GAPS.md owns the test/CI gaps. This doc does
> NOT re-audit testing. Evidence is cited as file:line. Scope is proportionate:
> zero-dependency alpha CLI, local-only, no money / CRM-write / PII-to-model / prod.

## 1. Summary

Verdict: structurally healthy code wearing one bad shape. The "minimal zero-dependency
CLI" is in fact a single-file 1458-line monolith (src/intent_control_plane/cli.py:1458;
the only other source file is a 6-line __init__.py). Correctness hygiene is good: zero
`except Exception`, zero bare `except`, zero `eval`/`exec`, zero `# noqa`, zero
`subprocess`, and only two read-only `os.environ.get` calls. The portfolio-wide
bad-practice counts (broad except 802, print 5780, os.environ 680, noqa 813) do NOT
manifest in this project. The one real defect is the god-file: 52 top-level functions,
14 subcommands, the ledger/store layer, the retrieval/vector math, context-pack building,
evidence handling, and all rendering are jammed into one module. The headline task is to
split cli.py into a thin dispatcher plus focused modules. Everything else is a small
follow-up.

## 2. Monolithic files (the headline finding)

### cli.py: 1458 lines, one module, 52 top-level functions

Verified: `wc -l` = 1458 (cli.py:1458); 52 top-level `def`s
(`rg '^(def |class )' cli.py`). It is the entire codebase. What is crammed in, by zone:

- argparse setup: `build_parser` is a single 128-line function with 25 `add_parser`
  blocks (cli.py:1312 through cli.py:1440).
- store / ledger / schema: `base_paths`, `connect`, `initialize`, `apply_schema`
  (a 120-line embedded DDL string), `ledger_append` (cli.py:44 through cli.py:240).
- every subcommand handler: `init_command`, `capture`, `extract_intent`, `context_pack`,
  `attach_evidence`, `eval_smoke`, `hive_bind`, `hive_sync`, `jira_assess`,
  `session_brief`, `foundry_status`, `retention_sweep`, `doctor`, `list_records`,
  `show_record`, `rebuild_index`, `vector_search` (scattered cli.py:243 through cli.py:1302).
- intent extraction heuristics: `extract_goal`, `infer_constraints`, `infer_proof`
  (cli.py:305 through cli.py:332).
- retrieval / vector math: `terms`, `term_vector`, `cosine`, `text_hash`,
  `upsert_vector`, `event_score`, `cwd_terms`, `recent_session_terms`,
  `STOP_WORDS` (cli.py:573 through cli.py:730).
- context-pack building: `build_context_pack` (cli.py:1080).
- row serializers: eight `*_row_to_dict` helpers (cli.py:406 through cli.py:477).
- rendering: `render_session_brief`, `render_context_pack_markdown`, `output`
  (cli.py:890, cli.py:1138, cli.py:1305).

Assessment: this is a genuine god-file. The verb handlers, the persistence layer, the
math, and the rendering have no reason to share a module; they share it only because the
file was never split. It is still readable (functions are small and typed), so this is a
maintainability/onboarding cost, not a correctness bug. Proportionate fix for an alpha:
split along the seams that already exist in the function names, do not rewrite logic.

### Proposed split (concrete module names)

```
src/intent_control_plane/
  __init__.py
  cli.py            # THIN: build_parser() + main() + output() dispatch ONLY (~150 lines)
  paths.py          # base_paths, DEFAULT_BASE_DIR, SCHEMA_VERSION
  store.py          # connect, initialize, apply_schema (the DDL), ledger_append
  rows.py           # the 8 *_row_to_dict serializers
  redact.py         # redact + SECRET_PATTERNS (security-relevant, isolate it; see sec 4)
  retrieval.py      # terms, STOP_WORDS, term_vector, cosine, text_hash, upsert_vector,
                    #   event_score, cwd_terms, recent_session_terms
  pack.py           # build_context_pack, render_context_pack_markdown
  commands/
    __init__.py
    capture.py      # capture, extract_intent + extract_goal/infer_constraints/infer_proof
    records.py      # list_records, show_record, init_command
    evidence.py     # attach_evidence
    evals.py        # eval_smoke
    index.py        # rebuild_index, vector_search
    session.py      # session_brief, render_session_brief
    foundry.py      # foundry_status
    hive.py         # hive_bind, hive_sync
    jira.py         # jira_assess, ticket_text, assess_ticket_relation
    retention.py    # retention_sweep
    doctor.py       # doctor
```

cli.py keeps only `build_parser`, `main`, `output`, and the `set_defaults(func=...)`
wiring, importing each handler from `commands/`. No behavior change; the console-script
entry stays `intent_control_plane.cli:main` (pyproject.toml unchanged).

## 3. Bad practices (quantified, this project only)

The portfolio context counts do not reproduce here. Verified in src/:

- broad `except Exception`: 0 (`rg 'except Exception' src/` -> no hits).
- bare `except:`: 0 (none). The only `try` block catches `sqlite3.Error` specifically
  (cli.py:1289 through cli.py:1296), which is correct narrow handling.
- `eval(` / `exec(`: 0 (none). No dynamic code execution anywhere.
- `# noqa` / `type: ignore`: 0 (none). Nothing is suppressed.
- `subprocess` / `os.system` / `shell=True`: 0 in this project (the test file shells out,
  but that is out of scope per the testing-doc split).
- `os.environ`: 2 reads, both read-only and legitimate (cli.py:933 reads five
  AZURE_* presence flags; cli.py:950 reads AZURE_OPENAI_DEPLOYMENT for a hash). No writes,
  no secrets logged. Acceptable as-is.
- `print(`: 3 occurrences, classified as required. cli.py:1307 and cli.py:1309 are the
  single `output()` sink (the legitimate stdout of a CLI: human string or JSON).
  cli.py:1450 is the error path in `main()`, correctly routed to `sys.stderr`. There are
  zero debug/log-style prints scattered in handlers. Conclusion: print usage is correct;
  no stdout pollution, nothing to clean.

Net: nothing in this section needs a remediation task. It is recorded so the next agent
does not chase the portfolio numbers into a project that does not have the problem.

## 4. Duplication and dead code

Real, small, and worth folding when the split happens (do not over-engineer it):

- Eight near-identical row serializers, `*_row_to_dict` (cli.py:406, 421, 440, 444, 457,
  468), referenced 22 times. Each is the same shape: read sqlite3.Row, json.loads the
  `*_json` columns, return a dict. They belong together in rows.py (sec 2); a tiny
  helper for the json-column unpacking would remove most of the repetition.
- `show_record` is eight copy-pasted not-found branches (cli.py:530 through cli.py:570),
  each: run a single-row query, `if row is None: raise SystemExit(...)`, return a
  serializer. Collapsible to one table mapping kind -> (table, id_column, serializer).
- `list_records` is a six-arm if/elif on `args.kind` (cli.py:484 through cli.py:523),
  the dual of `show_record`. Same kind->table/serializer table removes the chain.
- `initialize(args.base_dir)` is called at the top of 16 command handlers
  (`rg -c` = 16). Harmless (it is idempotent) but repetitive; a one-line decorator or a
  single call in the dispatcher would centralize it.
- `connect(args.base_dir)` appears at 20 sites; expected for a store layer, not a defect,
  but it confirms store.py should own the connection helper.

Dead code: none found. Every top-level function is reachable from a `set_defaults(func=)`
wiring or is a helper called by one. No unused imports observed (`from __future__`,
argparse, hashlib, json, math, os, re, sqlite3, sys, uuid, datetime, pathlib, typing are
all used). No commented-out blocks.

## 5. Structural issues

- The one-file-CLI smell is the whole story (sec 2). The fix is the split, not a rewrite.
- Security-relevant function worth isolating: yes, `redact` + `SECRET_PATTERNS`
  (cli.py:21 through cli.py:41). This is the project's only data-protection control: it is
  what makes captured prompts safe for a model-facing copy (it is the function the
  testing doc and the `doctor` smoke check both lean on, cli.py:1286). It is currently
  buried near the top of a 1458-line file next to id helpers. Pull it into its own
  redact.py so the security boundary is one named, separately-testable module, and so the
  regex set has an obvious home for review. Behavior unchanged.
- `apply_schema` embeds ~120 lines of SQL DDL as a Python string literal
  (cli.py:104 through cli.py:224). Fine for an alpha, but it is the bulk of the store
  layer; keeping it in store.py (not the dispatcher) is the point of the split.
- Error handling via `raise SystemExit(...)` for not-found / bad-kind (10 sites,
  cli.py:301 through cli.py:972) is a reasonable pattern for a small CLI and `main()`
  already maps string exit codes to stderr + exit 2 (cli.py:1448). No change needed; noted
  so it is not mistaken for swallowed errors.

## 6. Open tasks

### P1: Split cli.py into a thin dispatcher plus modules (the headline)

- Why: a 1458-line single file holding argparse, the store/ledger, retrieval math,
  context-pack building, and rendering is the project's one structural defect and the main
  onboarding cost.
- Acceptance: cli.py contains only `build_parser`, `main`, `output`, and func-wiring
  (target under ~160 lines); handlers live under commands/; store/paths/rows/redact/
  retrieval/pack are their own modules per the sec 2 layout; the console-script entry
  still resolves to `intent_control_plane.cli:main`; the existing unittest suite passes
  unchanged (no behavior change). Move code, do not rewrite logic.
- Target files: src/intent_control_plane/cli.py -> the module layout in section 2.
- Size: medium (mechanical move of 52 functions into ~20 files; a few hours, low risk
  because it is pure relocation gated by the existing tests).

### P1: Isolate the redact security boundary

- Why: `redact` + `SECRET_PATTERNS` (cli.py:21 through cli.py:41) is the only
  data-protection control and is currently buried in the monolith.
- Acceptance: redact lives in src/intent_control_plane/redact.py; cli.py, doctor, and
  capture import it; the redaction smoke in `doctor` (cli.py:1286) still passes.
- Target files: cli.py:21 through cli.py:41 -> src/intent_control_plane/redact.py.
- Size: small (can land as the first slice of the P1 split).

### P2: Collapse show/list/serializer duplication

- Why: `show_record` (eight copy-paste branches, cli.py:530 through cli.py:570) and
  `list_records` (six-arm if/elif, cli.py:484 through cli.py:523) duplicate a
  kind -> (table, serializer) mapping; the eight `*_row_to_dict` helpers repeat the same
  json-column unpacking.
- Acceptance: one declarative kind->table/id/serializer table drives both show and list;
  the eight serializers live in rows.py with a shared json-unpack helper; outputs are
  byte-identical to today (verify with the existing list/show tests).
- Target files: cli.py:406 through cli.py:570 -> rows.py + commands/records.py.
- Size: small (best done as a follow-up to the P1 split, not before it).

### P2: Centralize the per-command initialize call

- Why: `initialize(args.base_dir)` is repeated at the top of 16 handlers
  (cli.py, `rg -c initialize(args.base_dir)` = 16).
- Acceptance: initialize runs once in the dispatch path (or via one small decorator);
  individual handlers no longer each call it; tempdir-based tests still pass.
- Target files: cli.py:main / commands/ handlers.
- Size: small.
