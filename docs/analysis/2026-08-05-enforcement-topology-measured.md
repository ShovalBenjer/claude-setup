# Enforcement topology: what is global, what is per-project, and what is only a document

Status: measurement, 2026-08-05. Every number below names the command that produced it.
Written because four questions were asked at once and three of them turn on the same fact:
**a document being governed is not the same as a rule being enforced**, and this repo
currently conflates them.

## 1. The notification path between sessions

There is exactly one, and it is not GitHub.

```mermaid
flowchart LR
  S1["session A-1"] -->|bus.py send| L[("state/bus.jsonl<br/>hash-chained")]
  S2["session A-2"] -->|bus.py send| L
  L -->|UserPromptSubmit hook| D["delivered at the TOP of<br/>the next operator prompt"]
  D --> S3["session A-3 reads it<br/>before doing anything"]
  L -.->|bus.py log<br/>does NOT consume| R["read without<br/>advancing the cursor"]
  L -.->|bus.py verify| V["chain integrity"]

  PR["GitHub PR comments"] -.->|NO watcher| X["read only if a session<br/>happens to run gh pr view"]

  style L fill:#2d4a3e,color:#c5c9c5
  style X fill:#5a3030,color:#e8d8d8
```

`bus.py inbox` **advances a cursor**, so reading consumes. `bus.py log` does not.
`state/bus.jsonl` is hash-chained and `bus.py verify` checks it, so a rewrite of history
is visible.

**GitHub PR comments have no watcher.** kilo-code-bot and the Claude review action post
findings that reach a session only if that session runs `gh pr view` on purpose.

## 2. Global versus per-project, measured

```mermaid
flowchart TB
  subgraph G["GLOBAL, loads in every session in every repo"]
    R["~/.claude/rules/*.md<br/>22 files"]
    H["~/.claude/settings.json hooks<br/>7 events: SessionStart, PreToolUse,<br/>PostToolUse, PreCompact, Stop,<br/>Notification, UserPromptSubmit"]
    K["~/.claude/CLAUDE.md<br/>the global contract"]
  end

  subgraph P["PER-PROJECT, only where a contract is wired AND run"]
    C1["claude-setup<br/>16 domains, 292+ gate runs"]
    C2["new-recruit<br/>10 domains, ZERO gate runs"]
    C3["daily-deep-learning<br/>10 domains, ZERO gate runs"]
  end

  subgraph D["DOCUMENTS ONLY, governed but not enforced"]
    S["docs/standards/ 7 files<br/>incl. the 3 imported nr-* standards"]
    A["docs/adr/ 21 ADRs<br/>13 with zero executable reference"]
  end

  G --> C1
  G --> C2
  G --> C3
  D -.->|docmap: must have a status<br/>strand: must be reachable| C1
  D -.->|NO oracle reads their CONTENT| N["nothing checks<br/>compliance with them"]

  style C1 fill:#2d4a3e,color:#c5c9c5
  style C2 fill:#5a3030,color:#e8d8d8
  style C3 fill:#5a3030,color:#e8d8d8
  style N fill:#5a3030,color:#e8d8d8
```

The measurements behind that:

| question | command | answer |
|---|---|---|
| global rules live? | `ls ~/.claude/rules/*.md \| wc -l` | **22** |
| global hook events? | read `~/.claude/settings.json` | **7** |
| repos with a contract? | `ls */quality-contract.json` | **3 of 3** |
| repos that ever ran it? | `wc -l */state/gate-runs.jsonl` | **1 of 3** |
| standards referenced by an executable? | `grep -rl` over `tools/`, workflows, contract | `code-quality-standard` **0**, `harness-structure` **0**, `repo-standards` **0** |
| ADRs referenced by an executable? | same | **8 of 21**; 13 have zero |

## 3. The gap this exposes

`docs/standards/` IS referenced three times, and none of the three is enforcement:

- `docmap.py:60` classifies the directory so its files must declare a status
- `strand.py:47` puts it in `GOVERNED` so its files must be reachable from a read surface
- `repo_project.py:4` mentions one in a comment

So a standard in this repo must **have a status** and **be linked**. Nothing reads what it
says. The imported `nr-code-quality-standard-2026-07.md` sets a module hard limit of 500
lines and a function hard limit of 50, and `quality-contract.json` has no size or
complexity domain at all. Measured against `tools/**/*.py` by AST: **14 modules over 500,
71 functions over 50 of 678**, and nine of the ten longest functions are `cmd_selftest`,
headed by `tools/bus/bus.py:589` at **614 lines**.

That is the difference between a governed document and an enforced rule, and it is the
single largest gap in the topology.

## 4. What choosing a lane actually changes

A lane is a **charter**, not a mechanism. Nothing technical keys off it except the
SessionStart banner and the bus's `--to`. Concretely:

```mermaid
flowchart LR
  OP["operator picks a lane"] --> CL["claim row in<br/>claude-setup/state/claims.jsonl"]
  CL --> SC["scope: which repo you may edit"]
  SC --> L1["A harness -> ~/work/repos/claude-setup<br/>16-domain gate RUNS, CI runs it"]
  SC --> L2["B resume -> ~/work/repos/new-recruit<br/>10-domain contract declared, NEVER run"]
  SC --> L3["C learning -> daily-deep-learning<br/>10-domain contract declared, NEVER run"]
  SC --> L4["D content -> publishing surfaces"]
  G2["the 22 global rules and 7 hooks<br/>apply identically in all four"] --> L1
  G2 --> L2
  G2 --> L3
  G2 --> L4

  style L1 fill:#2d4a3e,color:#c5c9c5
  style L2 fill:#5a3030,color:#e8d8d8
  style L3 fill:#5a3030,color:#e8d8d8
```

So the honest answer to "what changes if I pick the resume engine instead of the harness":
the global rules and hooks are identical, the claim ledger is the same file, and the only
real difference is that **lane A is gated and lanes B and C are not**. Work in
`new-recruit` is governed by 22 global rules and by nothing else that executes.

## 5. The complete intended workflow

```mermaid
flowchart TB
  A1["SessionStart hook<br/>recall + bus inbox"] --> A2["name the lane<br/>docs/charters.md"]
  A2 --> A3["claim row<br/>state/claims.jsonl"]
  A3 --> A4{"design decision?"}
  A4 -->|yes| A5["/diverge, 5 candidates<br/>with p_conventional<br/>log the pick in docs/taste.md"]
  A4 -->|no| A6
  A5 --> A6["write the failing test FIRST"]
  A6 --> A7["implement"]
  A7 --> A8["prove the test can go RED<br/>revert the fix, watch it fail"]
  A8 --> A9["regenerate codemap + docmap"]
  A9 --> A10["gate.py run, LAST"]
  A10 -->|red| A11{"clear it or waive it"}
  A11 -->|waive| A12["dated waiver naming the count<br/>and the confirming command"]
  A11 -->|clear| A9
  A10 -->|green| A13["commit to a branch"]
  A12 --> A13
  A13 --> A14["push, open PR<br/>ADR-0012: never push to main"]
  A14 --> A15["CI: 14 domains + panel + supply-chain"]
  A15 --> A16["bus.py send: tell the other lanes"]
  A16 --> A17["merge, --merge not --squash<br/>the commit messages hold the findings"]

  style A6 fill:#2d4a3e,color:#c5c9c5
  style A8 fill:#2d4a3e,color:#c5c9c5
  style A10 fill:#2d4a3e,color:#c5c9c5
  style A12 fill:#5a3030,color:#e8d8d8
```

The two steps that get skipped and cost the most, both observed today: **A8**, proving the
test can fail, without which you ship a test that passes for the wrong reason; and **A16**,
telling the other lanes, without which two sessions push to one branch in the same minutes
and each regenerates a map the other invalidates.

## 6. Coverage

Every number here is from a command run on 2026-08-05 against the tree at `aa4811a`.
Not measured: whether the 13 unreferenced ADRs are unenforced or merely unnamed in the
oracles that implement them, which needs reading each ADR rather than grepping its number.
The `enforced_by` counts are substring matches on `ADR-NNNN` and will miss an oracle that
implements a decision without citing it.
