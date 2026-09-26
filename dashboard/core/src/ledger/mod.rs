//! One module per `state/*.jsonl` ledger. `gate_runs` and `agent_spawns`
//! are real readers; the rest are stub modules returning an empty
//! `LedgerReadReport` so callers that wire them early get an honest empty
//! result rather than a missing symbol or a panic.

pub mod agent_spawns;
pub mod gate_runs;
pub mod stubs;

pub use agent_spawns::{read_agent_spawns, AgentSpawn};
pub use gate_runs::{read_gate_runs, GateRun, Verdict};
pub use stubs::{read_bus, read_claims, read_routing, read_skill_use, BusMessage, ClaimRow, RoutingEvent, SkillUse};
