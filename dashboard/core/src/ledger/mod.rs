//! One module per `state/*.jsonl` ledger. `gate_runs` is the only reader
//! implemented in slice 2 (program design section 4, "Slice 2" scope); the
//! rest are stub modules returning an empty `LedgerReadReport` so callers
//! that wire them early get an honest empty result rather than a missing
//! symbol or a panic.

pub mod gate_runs;
pub mod stubs;

pub use gate_runs::{read_gate_runs, GateRun, Verdict};
pub use stubs::{
    read_agent_spawns, read_bus, read_claims, read_routing, read_skill_use, AgentSpawn,
    BusMessage, ClaimRow, RoutingEvent, SkillUse,
};
