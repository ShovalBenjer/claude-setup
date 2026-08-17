//! DASH-1 slice 2: read-only ledger readers for `state/*.jsonl`.
//!
//! Design source: docs/specs/2026-08-17-session-dashboard-program-design.md
//! section 1. These ledgers are append-only, hand-evolved logs with no
//! enforced schema (AGENTS.md calls them ledgers, not a database), so every
//! reader here is tolerant by construction: a malformed or short-shaped line
//! is skipped and counted, never a panic, never a silent drop.
//!
//! Slice 2 scope: only `ledger::gate_runs` is implemented end to end (the
//! `GateRun` type, its reader, and `latest_gate_verdict`). The other five
//! ledger types named in the program design (claims, agent_spawns,
//! skill_use, routing, bus) are declared as empty stub modules per the
//! program design's slice 2 scope ("other five readers stub to `todo!()`-free
//! empty reports"); they return an empty `LedgerReadReport` rather than
//! panicking, so a caller that wires them early gets an honest empty result,
//! not a crash.

pub mod ledger;

use serde::Serialize;

/// Uniform result of reading one ledger file. `skipped` is a count, not a
/// silent drop: the UI is expected to surface `skipped > 0` as a visible
/// badge so an unknown-schema line is never invisible to the operator.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct LedgerReadReport<T> {
    pub rows: Vec<T>,
    pub skipped: usize,
    pub total_lines: usize,
    /// First parse/shape error seen, truncated to 200 chars, for the one
    /// diagnostic line the UI shows on hover. Never the full offending line:
    /// it may carry a prompt fragment or a path with PII.
    pub first_error: Option<String>,
}

impl<T> LedgerReadReport<T> {
    pub fn empty() -> Self {
        LedgerReadReport {
            rows: Vec::new(),
            skipped: 0,
            total_lines: 0,
            first_error: None,
        }
    }
}

/// IPC-boundary error type (program design section 2.2). Never carries a raw
/// filesystem path outside the configured project root, so a typo in a
/// project name cannot leak a host path across the IPC boundary.
#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(tag = "kind", content = "message", rename_all = "snake_case")]
pub enum IpcError {
    NotFound(String),
    Io(String),
    InvalidProject(String),
}
