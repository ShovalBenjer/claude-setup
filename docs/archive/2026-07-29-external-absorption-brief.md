# External brief: absorb the saved-link corpus

Written 2026-07-29, lane B, to be pasted into a Claude Desktop conversation as a
standing brief. It is self-contained on purpose: it carries the measured facts so
the external session does not need this repository to start.

Attach `C:\Users\shova\wa-export-archive\self-chat-links-2026-07-29.csv` to the
conversation. That file is links and first-seen dates only, extracted from a chat
export marked SENSITIVE. No message text was copied and none may be requested.

---

## The prompt

You are working on an absorption audit for a single operator's engineering estate.
Your output is a decision table, not an essay. Read the whole brief before starting.

### The standing rule you are enforcing

Every external resource this operator has saved must end in exactly one of four
states. There is no fifth state, and "interesting, worth exploring" is not an
outcome:

1. **ADOPTED**: it becomes a real dependency. Name the package, the install
   command, and the file that will import it.
2. **ABSORBED**: the idea is taken into existing code. Name the specific mechanism
   taken, in one sentence, and the file it should land in.
3. **USED AS-IS**: run or read directly, no integration. Name the command or the
   artifact to save.
4. **REJECTED**: with a reason that would survive a challenge. "Not needed" is not
   a reason. "Duplicates X which we already run, and its only distinct feature is Y
   which does not apply because Z" is a reason.

An item that cannot be placed in one of the four is not finished, and you say so
rather than inventing a placement.

### Why this brief exists (measured, not asserted)

The estate has a strong verification harness and near-zero absorption. Numbers from
2026-07-29, each reproducible from a command:

- 51 commits in four weeks: `+221,943 / -9,336`. Exactly one commit was net
  negative, and it removed a feature rather than debt.
- 28 prior-art records exist. 17 say `split` (part of our code should go), 1 says
  `delete-ours`, 2 say `wrap`. Twenty of twenty-eight are instructions to remove
  code. Lines removed in response: zero until today.
- The `tools/` tree is 30,330 lines of Python with **two** genuine third-party
  imports. Roughly 70 alternatives were formally evaluated. Zero were adopted.
- **Root cause**: the prior-art record schema has 14 fields (`verdict`, `why`,
  `strongest_counterargument`, `migration_loc`, ...) and not one of them names what
  was taken from the alternative. Absorption is unrepresentable in the schema,
  therefore unchecked, therefore it never happens.

So the failure is not laziness or ignorance. It is that every loop in the system
terminates in a written artifact and none terminates in a deletion or a dependency.
Your output must not repeat that. A beautiful analysis of these links is a failure.

### The input

The attached CSV has three columns: `first_seen`, `url`, `host`. 806 unique URLs
saved across roughly 14 months, of which:

| host | count |
|---|---|
| github.com | 80 |
| youtube (all forms) | 166 |
| linkedin.com | 41 |
| facebook.com | 31 |
| learn.microsoft.com | 14 |
| arxiv.org | 12 |

Save rate rose five to ten times in July 2026, so recency is a signal of current
intent, not just of when the link appeared.

### Scope, in priority order

**Tier 1, do this first and completely: the 80 GitHub URLs.** For each repo, fetch
enough to answer the table below. Do not guess from the name. A repo you cannot
reach gets a row saying so.

**Tier 2: the 12 arXiv papers and 14 Microsoft Learn pages.** Same table, where
"adopt" means a technique enters a named file and "absorb" means a claim enters a
rule or a test.

**Tier 3: YouTube, LinkedIn, Facebook, and the ~300 remaining hosts.** These are
mostly not engineering artifacts. Classify at the host level, name the handful that
are, and say plainly that the rest are out of scope. Do not pad.

### The table you produce, one row per resource

| field | content |
|---|---|
| `url` | verbatim from the CSV |
| `what_it_is` | one sentence, from the actual README or paper, not the name |
| `license` | exact license id. **This is a gate, not a footnote.** |
| `status` | ADOPTED / ABSORBED / USED-AS-IS / REJECTED |
| `mechanism` | for absorb: the one mechanism taken. For adopt: the package and install line. For use-as-is: the command. For reject: the surviving reason. |
| `lands_in` | the file or directory it changes. "TBD" is not allowed on a non-rejected row. |
| `effort` | S (under an hour) / M (a day) / L (more) |
| `conflicts_with` | anything in the constraints below that it violates |

Sort the final table by value over effort, highest first. Then give me the top ten
as a numbered action list where each entry is a command or a diff, not a plan.

### Hard constraints of the target estate

Violating one of these makes a recommendation useless, so check each row against them:

- **Windows 11 native.** Not WSL. PowerShell and Git Bash are both present. A
  tool that only ships a Linux binary or needs a Unix-only syscall is REJECTED
  unless it runs under `uvx` or `npx`.
- **License is a hard gate for anything commercial.** The operator has commercial
  ventures. PolyForm Noncommercial, SSPL, BUSL, "source available", and custom
  non-OSI licenses mean the CODE cannot be vendored, though the IDEAS remain
  absorbable and the repo remains binding prior art. This is not hypothetical:
  `github.com/Sdraugel/albert` was evaluated today and is PolyForm Noncommercial
  1.0.0, so it went to ABSORBED (two mechanisms, rebuilt) rather than ADOPTED.
- **Python is preferred stdlib, `uv` for anything else. JavaScript uses `bun`.**
  A new dependency needs a reason stronger than convenience, but "we hand-wrote
  700 lines that this package does better" IS that reason and has already been
  found true several times.
- **No new long-running server process without a named owner.** Dashboards that
  require an always-on daemon have failed here before.
- **Data with real names or contact details stays local.** Several candidate
  targets touch a recruiting ledger. Anything that ships data to a hosted service
  is REJECTED on that ground alone unless self-hostable.
- **Prefer first-party.** Claude Code ships native agent teams, `/code-review`,
  worktree isolation, hooks, and scheduling. A third-party tool duplicating one of
  those must beat it on a named axis or it is REJECTED.

### Things already decided, so do not re-derive them

- `amirfish1/claude-command-center`: ADOPT-PARTIAL, specced 2026-07-24, never
  built. One idea taken (jsonl-on-disk as source of truth). Do not re-evaluate; if
  it appears in the CSV, mark it and move on.
- `Master0fFate/just-my-skills`: REJECTED as an install, USED-AS-IS as one page.
  Already saved today.
- `Sdraugel/albert`: license-blocked as above.
- DoltHub: three of five features already absorbed into git-tracked append-only
  JSONL. The unabsorbed piece is point-in-time reconstruction for gitignored
  sqlite ledgers.

### Anti-patterns that will make the output worthless

- Producing a long analysis with a recommendations section at the end. That is
  exactly the failure mode being corrected.
- Writing "consider adopting X" without naming the file it changes.
- Grouping thirty repos into a paragraph of themes instead of thirty rows.
- Rating things you did not fetch. An unreachable URL gets a row saying
  UNREACHABLE, which is a real and useful result.
- Softening a REJECTED verdict into "maybe later". Later is not one of the four
  states.

### What good looks like

A table where every non-rejected row names a file, and a top-ten list where item
one can be executed in under an hour by someone who reads only that line.

---

## After the external session returns

Bring the table back and file it against `TODO.md` section `ABSORB`. Each ADOPTED
or ABSORBED row becomes a ticket. Each REJECTED row becomes a line in the relevant
`docs/prior-art/*.json` record once `ABSORB-01` adds the `absorbed` and
`absorption_status` fields, which is the schema change that makes any of this
checkable.
