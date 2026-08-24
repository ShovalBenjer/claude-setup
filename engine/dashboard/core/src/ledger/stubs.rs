//! Stub types and readers for the five ledgers out of scope for slice 2
//! (`state/claims.jsonl`, `state/agent-spawns.jsonl`, `state/skill-use.jsonl`,
//! `state/routing.jsonl`, `state/bus.jsonl`). Program design section 4,
//! slice 2 row: "other five readers stub to `todo!()`-free empty reports."
//!
//! Each stub reader always returns `LedgerReadReport::empty()` regardless of
//! the path argument: a wired-but-unimplemented IPC command must never panic
//! or read state it does not yet parse. Full types (ClaimRow, AgentSpawn,
//! SkillUse, RoutingEvent, BusMessage) are specified in the program design
//! sections 1.3-1.6 and land in a later slice.

use crate::LedgerReadReport;
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ClaimRow;
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct AgentSpawn;
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SkillUse;
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RoutingEvent;
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BusMessage;

pub fn read_claims(_path: &Path) -> LedgerReadReport<ClaimRow> {
    LedgerReadReport::empty()
}
pub fn read_agent_spawns(_path: &Path) -> LedgerReadReport<AgentSpawn> {
    LedgerReadReport::empty()
}
pub fn read_skill_use(_path: &Path) -> LedgerReadReport<SkillUse> {
    LedgerReadReport::empty()
}
pub fn read_routing(_path: &Path) -> LedgerReadReport<RoutingEvent> {
    LedgerReadReport::empty()
}
pub fn read_bus(_path: &Path) -> LedgerReadReport<BusMessage> {
    LedgerReadReport::empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stub_readers_never_panic_and_return_empty() {
        let p = Path::new("/does/not/matter");
        assert_eq!(read_claims(p), LedgerReadReport::empty());
        assert_eq!(read_agent_spawns(p), LedgerReadReport::empty());
        assert_eq!(read_skill_use(p), LedgerReadReport::empty());
        assert_eq!(read_routing(p), LedgerReadReport::empty());
        assert_eq!(read_bus(p), LedgerReadReport::empty());
    }
}
