---
PRD: prd/session-dashboard.md
Ticket: DASH-1
Status: active
---

# Session dashboard: program design (slice 1)

DASH-1 acceptance row 7 asks for this document before any application code:
Rust types for the ledger rows the UI reads, the Tauri IPC contract, the React
component tree, the vertical slice list, and named rejected alternatives. This
is that document. It supersedes nothing in
`docs/specs/2026-08-17-session-dashboard-direction.md` (stack lock, Buzz mode
catalogue) or `docs/prd/session-dashboard.md` (the acceptance table); both
currently exist only on `worktree-rules-sync-repo-stack-reasoning` (PR #78),
not on this branch. This document does not restate or edit that acceptance
table, to avoid a cross-branch merge conflict with #78; it only cites row
numbers by reference. **Writing this document is not the review row 7 asks
for**: row 7 closes when the PR carrying it is reviewed and merged, not when
the file exists.

## 0. Empirical grounding: the ledgers are not one schema each

Before drafting a single struct, every row of the six ledgers in scope was
key-set-scanned (`python3` json.loads + `Counter` of `sorted(d.keys())`, run
2026-08-17 against this worktree's `state/`):

| file | rows | distinct key-sets | worst case |
| --- | --- | --- | --- |
| `state/gate-runs.jsonl` | 14,924 | 4 | `domain_seconds`, `unmeasured`, `waivers_unconfirmed` each independently optional |
| `state/claims.jsonl` | 43 | 6 | one row uses `date`+`claim`+`evidence`, no `ts`; another uses `ts`+`claim`+`who`, no `evidence` |
| `state/agent-spawns.jsonl` | 37 | 2 | one legacy row (`agreed`, `is_builtin`, `route_match`, ...) shares zero keys with the other 36 |
| `state/skill-use.jsonl` | 73 | 1 | stable today; still not guaranteed by a schema anywhere |
| `state/routing.jsonl` | 339 | 1 | stable today; same caveat |
| `state/bus.jsonl` | 32 | 2 | 12 legacy rows predate `hash`/`origin_lane` (added when the chain got hash-linked) |

Conclusion: these are append-only, hand-evolved logs with no enforced schema
(`AGENTS.md` calls them ledgers, not a database). A reader that assumes a
fixed shape will panic or silently misread on real data within the first few
hundred rows for four of six files. Every reader in this design is therefore
tolerant by construction, not by exception handling bolted on later.

## 1. Rust-side types

Crate layout: `src-tauri/src/ledger/{gate_runs,claims,agent_spawns,skill_use,routing,bus,mod}.rs`.
Each module owns one `TryFrom<&serde_json::Value>` (not `Deserialize` on the
raw line directly: see rejected alternative 1.6) producing its row type, and
a `read(path: &Path) -> LedgerReadReport<T>` function.

### 1.1 Shared read report (every reader returns this, never a bare `Vec<T>`)

```rust
/// Uniform result of reading one ledger file. `skipped` is a count, not a
/// silent drop: the UI surfaces `skipped > 0` as a visible badge so an
/// unknown-schema line is never invisible to the operator.
pub struct LedgerReadReport<T> {
    pub rows: Vec<T>,
    pub skipped: usize,
    pub total_lines: usize,
    /// First parse/shape error seen, truncated to 200 chars, for the one
    /// diagnostic line the UI shows on hover. Never the full offending line
    /// (it may carry a prompt fragment or path with PII).
    pub first_error: Option<String>,
}
```

Read algorithm, identical across all six readers: open file, iterate lines,
`skip empty/whitespace-only lines without counting them as skipped`, for each
non-empty line: `serde_json::from_str::<serde_json::Value>` (malformed JSON
-> increment `skipped`, record `first_error` if unset, continue) then
`RowType::try_from(&value)` (missing/wrong-typed required field -> same
skip-and-count path, continue). **No `unwrap`, no `expect`, no `panic!` in
any ledger reader.** A missing file is not an error: return an empty report
(`rows: vec![]`, `total_lines: 0`): the dashboard runs before a ledger has
its first row.

### 1.2 `state/gate-runs.jsonl` -> `GateRun`

```rust
pub struct GateRun {
    pub ts: String,                          // ISO-ish, kept as String; UI formats
    pub project: String,
    pub project_path: String,
    pub commit: String,
    pub dirty: bool,
    pub fingerprint: String,
    pub partial: bool,
    pub verdict: Verdict,                    // enum, see below
    pub domains: HashMap<String, String>,     // domain name -> PASS/FAIL/... ; not a fixed struct, keys vary by which domains ran
    pub blocking: Vec<String>,
    pub waivers_unconfirmed: Vec<String>,     // absent in oldest key-set -> default empty
    pub unmeasured: Vec<String>,              // absent in two of four key-sets -> default empty
    pub duration_seconds: Option<f64>,        // absent in oldest key-set
    pub domain_seconds: Option<HashMap<String, f64>>, // absent in oldest key-set
}

pub enum Verdict { Pass, Fail, Partial, Unknown(String) }
```

`Verdict::Unknown(String)` exists because a future gate run may emit a verdict
string this build has never seen; the UI must render it, not crash on it.

### 1.3 `state/claims.jsonl` -> `ClaimRow` (union type, forced by 1.0's scan)

```rust
pub struct ClaimRow {
    pub ts: Option<String>,          // absent in the `date`-keyed variant
    pub date: Option<String>,        // present only in that variant
    pub lane: Option<String>,
    pub who: Option<String>,
    pub scope: Option<String>,
    pub claim: Option<String>,
    pub evidence: Option<String>,
    pub falsifier: Option<String>,
    pub note: Option<String>,
    pub proposal_id: Option<String>,
    pub cwd: Option<String>,
    pub id: Option<String>,
    pub claimed_at: Option<String>,
}
impl ClaimRow {
    /// ts if present, else date, else None. The UI's single sort key.
    pub fn effective_time(&self) -> Option<&str> { self.ts.as_deref().or(self.date.as_deref()) }
}
```

Every field is `Option` on purpose: 1.0 showed no field is common to all six
key-sets except `lane`. `try_from` requires only `lane` to be present and of
type string; everything else is best-effort.

### 1.4 `state/agent-spawns.jsonl` -> `AgentSpawn`

```rust
pub struct AgentSpawn {
    pub ts: String,
    pub subagent_type: String,
    pub description: Option<String>,
    pub model: Option<String>,
    pub background: Option<bool>,
    pub session: Option<String>,
    pub cwd: Option<String>,
    pub router_named: Option<Vec<String>>,
    pub router_skills: Option<Vec<String>>,
    // legacy 2026-era shape carries `outcome`, `routed_persona`, `agreed`;
    // captured as passthrough rather than named fields, since it is one row
    // in 37 and adding named fields for a single historical shape is not
    // worth the surface area (see rejected alternative 1.6).
    pub legacy_extra: Option<serde_json::Value>,
}
```

### 1.5 `state/skill-use.jsonl` -> `SkillUse`, `state/routing.jsonl` -> `RoutingEvent` (both single-shape today, still built tolerant)

```rust
pub struct SkillUse { pub ts: String, pub skill: String, pub args: Option<String>, pub session: Option<String>, pub project: Option<String>, pub cwd: Option<String>, pub outcome: Option<String> }
pub struct RoutingEvent { pub ts: String, pub personas: Vec<String>, pub skills: Vec<String>, pub matched: bool, pub prompt_chars: Option<u64>, pub session: Option<String> }
```

Only `ts` (and `skill`/`personas`+`matched` respectively) are required for a
row to count as parsed; everything else defaults on absence. One key-set
today is evidence of current stability, not a schema guarantee: the reader
does not special-case "exactly one shape."

### 1.6 `state/bus.jsonl` -> `BusMessage`

```rust
pub struct BusMessage {
    pub id: String,
    pub ts: String,
    pub from_lane: String,
    pub to: String,
    pub kind: String,          // "claim" | "answer" | "question" | ... ; kept as String, not enum (see rejected alt below)
    pub subject: String,
    pub body: String,
    pub refs: Vec<String>,
    pub from_session: Option<String>,
    pub origin_lane: Option<String>,  // absent in 12 legacy rows
    pub prev: Option<String>,         // absent in legacy rows (predates hash-chaining)
    pub hash: Option<String>,         // absent in legacy rows
}
```

`kind` stays `String` rather than a closed enum: `bus.py verify` is the
authority on chain integrity, not this reader, and a closed enum would panic
or silently drop on a `kind` value this build predates. The dashboard is
read-only display, not a bus participant; it never calls `bus.py send`.

### 1.7 Rejected alternatives (one per point, named)

- **1.0**: assume one `struct` per file with `#[derive(Deserialize)]` and let
  serde reject malformed rows. Rejected: serde's default behavior is
  fail-the-whole-line on the first missing required field, which is exactly
  the crash-on-real-data outcome 1.0 measured against `claims.jsonl` and
  `gate-runs.jsonl`. Every optional field would still need `Option<T>` by
  hand, so the manual `TryFrom` buys skip-and-count for free at the same
  cost.
- **1.6 (agent-spawns legacy row, and bus `kind`)**: enumerate every observed
  legacy shape as its own named struct variant in a `enum AgentSpawnRow {
  Current(AgentSpawn), Legacy(...) }`. Rejected for this slice: one legacy row
  in 37 does not justify a second full struct and a match arm the UI has to
  handle everywhere; `Option<serde_json::Value>` passthrough is cheaper and
  strictly more forward-compatible (an unseen third shape still parses as
  passthrough instead of failing `try_from` entirely). Revisit if legacy
  volume grows.

## 2. Tauri IPC contract

**Read-only by construction, scoped explicitly**: the Tauri `fs` capability
allowlist grants read-only access to `state/*.jsonl` under configured project
roots and nothing else; no command in this contract accepts a write path, a
delete path, or a ledger-mutating argument. This scope covers slices 1-3.
Slice 4 (Chrome kickstart) is an *acting* command, not a ledger write, and is
listed separately in 2.4 with its own boundary citation: "read-only by
construction" describes the ledger layer, not the whole app.

### 2.1 Commands (slice 2 scope)

| command | args | return | error |
| --- | --- | --- | --- |
| `list_projects` | `()` | `Vec<ProjectRef { name: String, path: String, has_state: bool }>` | `IpcError::Io(String)` |
| `read_gate_runs` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<GateRun>` | `IpcError::NotFound(String) \| IpcError::Io(String)` |
| `read_claims` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<ClaimRow>` | same |
| `read_agent_spawns` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<AgentSpawn>` | same |
| `read_skill_use` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<SkillUse>` | same |
| `read_routing` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<RoutingEvent>` | same |
| `read_bus` | `{ project: String, limit: Option<u32> }` | `LedgerReadReport<BusMessage>` | same |
| `latest_gate_verdict` | `{ project: String }` | `Option<GateRun>` (last row by `ts`) | same |

`limit` truncates from the tail (most recent N) server-side, since
`gate-runs.jsonl` alone is 14,924 rows and the React side must never load a
full ledger into a table component.

### 2.2 Error type

```rust
pub enum IpcError { NotFound(String), Io(String), InvalidProject(String) }
```

Serialized to `{"kind": "not_found" | "io" | "invalid_project", "message": String}`
across the IPC boundary (Tauri commands returning `Result<T, E>` need `E:
Serialize`). No error variant carries a raw filesystem path outside the
configured project roots, to avoid leaking host paths from an
`InvalidProject` typo.

### 2.3 Module registry / meme MCP commands (slice 3 scope, listed here for contract completeness, not implemented in slice 1)

| command | args | return | error |
| --- | --- | --- | --- |
| `list_modules` | `()` | `Vec<ModuleDescriptor { id: String, name: String, enabled: bool }>` | `IpcError::Io` |
| `set_module_enabled` | `{ id: String, enabled: bool }` | `()` | `IpcError::InvalidProject` (reused for "unknown module id") |
| `meme_find` | `{ query: String }` | `MemeResult { path: String, source: String }` | `IpcError::Io` |
| `meme_play` | `{ path: String }` | `()` | `IpcError::Io` |

`meme_find`/`meme_play` proxy to `claude-memes mcp`'s `find_meme`/`play_meme`
stdio tools per the direction spec's integration seam; the dashboard does not
reimplement selection. `set_module_enabled` writes to app-local config
(Tauri's own store), never to `state/`, so it does not violate the ledger
read-only scope.

### 2.4 Acting commands (slice 4 scope, outward action, separately boundaried)

| command | args | return | error |
| --- | --- | --- | --- |
| `kickstart_cloud_session` | `{ project: String, task_summary: String }` | `KickstartResult { opened: bool }` | `IpcError::Io` |

Opens the operator's default browser at `claude.ai/code` with the project
context prefilled where the site supports a URL parameter; does not submit,
merge, or post anything. This is the one command in the whole contract that
performs a side effect outside the process, and it is allowed under
`~/.claude/rules/the-loop-may-act.md` ("kicking a session is allowed, merging
and posting stay with the operator"): cited explicitly here because
"read-only by construction" (this section's opening claim) would otherwise
read as contradicted by its existence.

## 3. React component tree

Routing axis is the **four-register communication policy** from
`~/.claude/rules/output-channel-routing.md` (high-signal/low-noise,
social, deep-engineering, urgent-escalation): acceptance row 5 names
"four-register," not the five-row channel table. Channels (TTS, meme, HTML
artifact, diagram, plain text) are what a register *selects*, not the axis
itself; conflating the two was flagged as the likely-checked wording risk for
this doc and is deliberately kept apart below.

```
App
├── Sidebar                          [project picker; list_projects]
├── LiveView                         [acceptance row 2: sessions, agents, last gate verdict per tree]
│   ├── SessionList                  [reads agent-spawns via read_agent_spawns]
│   ├── GateVerdictTile              [reads latest_gate_verdict; renders Verdict enum incl. Unknown(_)]
│   └── SkippedRowsBadge             [renders LedgerReadReport.skipped > 0 for whichever reader fed the tile; never silent]
├── ModuleRegistry                   [acceptance row 3: capability modules, per-module toggle]
│   ├── ModuleToggle (repeated)      [list_modules / set_module_enabled]
│   └── MemeModule                   [first named module; meme_find / meme_play]
├── TaskBoard                        [acceptance row 4: open tasks per module]
│   └── KickstartButton              [kickstart_cloud_session; confirms before opening browser]
└── CommunicationSurface             [acceptance row 5]
    ├── RegisterRouter               [classifies an incoming event into one of the four registers]
    ├── HighSignalLane   -> renders  [reaction/ack chips, silent status updates]
    ├── SocialLane       -> renders  [meme/sticker channel, via ModuleRegistry's MemeModule]
    ├── DeepEngineeringLane -> renders [threaded markdown, HTML-artifact channel, diagram channel, cited diffs]
    └── UrgentLane       -> renders  [direct-mention style banner + TTS channel]
```

Per-module toggle state lives in a single `Map<moduleId, boolean>` in a React
context (`ModuleRegistryContext`), backed by `list_modules`/`set_module_enabled`;
no module component owns its own enabled flag, so toggling is one source of
truth instead of N components each guessing the current state.

Acceptance-row landing: row 1 (read-only) -> the fs capability scope in
section 2, not a component; row 2 -> `LiveView`; row 3 -> `ModuleRegistry`;
row 4 -> `TaskBoard`; row 5 -> `CommunicationSurface`; row 6 (WSL2/WSLg
tolerance) -> no component, a runtime/rendering constraint carried in the
Tauri window config, not UI logic; row 7 -> this document plus its PR review.

## 4. Vertical slice list

Each slice's acceptance check names a command or artifact per
`calibrated-claims`; none is satisfied by "looks right in the UI."

- **Slice 1 (this document).** Acceptance: this file exists at
  `docs/specs/2026-08-17-session-dashboard-program-design.md`, passes
  `python tools/slop_lint.py`, passes `python tools/docmap/strand.py check`,
  and is reachable per R2 (linked from `TODO.md`). No Rust or React code
  ships in this slice.
- **Slice 2: ledger reader + one live gate-verdict tile.** Scope: implement
  `src-tauri/src/ledger/gate_runs.rs` (section 1.2/1.1) and wire
  `latest_gate_verdict` + `GateVerdictTile` only; other five readers stub to
  `todo!()`-free empty reports. Acceptance: (a) a Rust unit test asserts a
  hand-crafted malformed line (missing `verdict`, and a line that is not
  valid JSON) increments `skipped` and does not panic, run via `cargo test`;
  (b) `GateVerdictTile` renders the real `verdict` string equal to the last
  `verdict` field from `python tools/gate/gate.py status` for the same
  project, checked by hand once and screenshotted per the CLAUDE.md
  user-facing-change rule; (c) any component over 300 lines has
  `docs/prior-art/<name>.json` before the gate passes (constraint from the
  direction spec, restated here so slice 2 doesn't ambush on it).
- **Slice 3: module registry with meme module via claude-memes MCP.**
  Acceptance: `list_modules`/`set_module_enabled` round-trip through a
  restarted app (toggle state persists); `meme_find`/`meme_play` invoked
  end-to-end against a running `claude-memes mcp` process (no mock of the
  MCP boundary, per the no-mocks rule) and produce an observable play event
  (stdout line or file write from the real binary, pasted as evidence).
- **Slice 4: cloud-session kickstart.** Acceptance: `kickstart_cloud_session`
  opens the operator's actual default browser at the expected URL (observed,
  not asserted: a screenshot or OS-level process check that a browser
  process launched with the right URL argument); the command performs no
  HTTP POST and no file write outside app-local config, verified by a test
  that asserts the Tauri capability manifest grants this command no `fs`
  write scope.
- **Slice 5: communication surface.** Acceptance: for each of the four
  registers, one synthetic event routes to the lane the
  `output-channel-routing.md` table specifies (a table-driven test:
  event class -> expected lane), plus one manual check that a TTS-tagged
  urgent event actually speaks via the same `System.Speech`/`say.sh`
  mechanism named in that rule (not a new one invented here).

## 5. Rejected alternatives (design-point level, beyond 1.7)

- **Single `AnyLedgerRow` sum-type for all six files** instead of six named
  structs. Rejected: a sum type forces every reader and every UI component to
  match on a variant it does not care about, and the six ledgers have no
  shared consumer: nothing in the UI ever needs "the next row from any
  ledger" as a stream. Six small types are less code at every call site than
  one large enum plus six `if let` unwraps.
- **Polling the ledgers on a timer from React** instead of a Tauri
  file-watcher event. Deferred, not rejected outright, but the default for
  slice 2 is polling (`setInterval` calling `read_gate_runs` on a few-second
  cadence) because `state/gate-runs.jsonl` is appended by processes outside
  this app's control and a watcher adds inotify/WSLg-specific failure modes
  (WSL2 filesystem watch support across the Windows/Linux boundary is not
  verified) for a surface that updates on human timescales, not
  sub-second ones. Revisit only if polling proves visibly laggy.
