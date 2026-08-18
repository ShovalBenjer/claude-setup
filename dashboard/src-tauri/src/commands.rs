//! IPC command handlers (program design section 2.1, slice 2 scope).
//!
//! `latest_gate_verdict` is fully implemented: it resolves `<project>/state/
//! gate-runs.jsonl` and delegates to `dashboard_core::ledger::gate_runs::
//! latest_gate_verdict`. The other six commands are stubbed: they call the
//! corresponding stub reader in `dashboard-core` (or return an empty
//! `Vec`/`None` for `list_projects`), so a frontend that wires them early
//! gets a typed empty result, never a missing command or a panic.

use crate::meme_process;
use dashboard_core::ledger::{
    gate_runs, read_agent_spawns, read_bus, read_claims, read_routing, read_skill_use, AgentSpawn,
    BusMessage, ClaimRow, GateRun, RoutingEvent, SkillUse,
};
use dashboard_core::meme::{parse_find, parse_list, FindHit, MemeEvent};
use dashboard_core::modules::{self, ModuleDescriptor};
use dashboard_core::{IpcError, LedgerReadReport};
use serde::Serialize;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Serialize)]
pub struct ProjectRef {
    pub name: String,
    pub path: String,
    pub has_state: bool,
}

fn resolve_ledger_path(project: &str, file: &str) -> Result<PathBuf, IpcError> {
    // Slice 2 stub resolution: treats `project` as a filesystem path to a
    // project root directly. A real project registry (name -> validated
    // root) is out of scope for this slice; see `list_projects` below.
    if project.trim().is_empty() {
        return Err(IpcError::InvalidProject("empty project name".to_string()));
    }
    Ok(PathBuf::from(project).join("state").join(file))
}

#[tauri::command]
pub fn list_projects() -> Result<Vec<ProjectRef>, IpcError> {
    // Stub for slice 2: a real implementation reads a configured project
    // registry. Empty list, not a panic, keeps the frontend's Sidebar
    // component renderable before that registry exists.
    Ok(Vec::new())
}

#[tauri::command]
pub fn read_gate_runs(
    project: String,
    limit: Option<u32>,
) -> Result<LedgerReadReport<GateRun>, IpcError> {
    let path = resolve_ledger_path(&project, "gate-runs.jsonl")?;
    let mut report = gate_runs::read_gate_runs(&path);
    if let Some(n) = limit {
        let n = n as usize;
        if report.rows.len() > n {
            let start = report.rows.len() - n;
            report.rows = report.rows.split_off(start);
        }
    }
    Ok(report)
}

#[tauri::command]
pub fn latest_gate_verdict(project: String) -> Result<Option<GateRun>, IpcError> {
    let path = resolve_ledger_path(&project, "gate-runs.jsonl")?;
    Ok(gate_runs::latest_gate_verdict(&path))
}

#[tauri::command]
pub fn read_claims_cmd(
    project: String,
    _limit: Option<u32>,
) -> Result<LedgerReadReport<ClaimRow>, IpcError> {
    let path = resolve_ledger_path(&project, "claims.jsonl")?;
    Ok(read_claims(&path))
}

#[tauri::command]
pub fn read_agent_spawns_cmd(
    project: String,
    _limit: Option<u32>,
) -> Result<LedgerReadReport<AgentSpawn>, IpcError> {
    let path = resolve_ledger_path(&project, "agent-spawns.jsonl")?;
    Ok(read_agent_spawns(&path))
}

#[tauri::command]
pub fn read_skill_use_cmd(
    project: String,
    _limit: Option<u32>,
) -> Result<LedgerReadReport<SkillUse>, IpcError> {
    let path = resolve_ledger_path(&project, "skill-use.jsonl")?;
    Ok(read_skill_use(&path))
}

#[tauri::command]
pub fn read_routing_cmd(
    project: String,
    _limit: Option<u32>,
) -> Result<LedgerReadReport<RoutingEvent>, IpcError> {
    let path = resolve_ledger_path(&project, "routing.jsonl")?;
    Ok(read_routing(&path))
}

#[tauri::command]
pub fn read_bus_cmd(
    project: String,
    _limit: Option<u32>,
) -> Result<LedgerReadReport<BusMessage>, IpcError> {
    let path = resolve_ledger_path(&project, "bus.jsonl")?;
    Ok(read_bus(&path))
}

// --- Module registry / meme module (DASH-1 slice 3) ---
//
// Path resolution (`app_config_dir()`) is the only piece of module-registry
// logic that lives in this file; the round-trip and toggle logic itself is
// in `dashboard_core::modules` so it is testable without a running Tauri app
// (program design section 2.3, plus the slice-3 acceptance row: "toggle
// state persists across a restarted app").

fn modules_path(app: &AppHandle) -> Result<PathBuf, IpcError> {
    app.path()
        .app_config_dir()
        .map(|dir| dir.join("modules.json"))
        .map_err(|e| IpcError::Io(format!("could not resolve app config dir: {e}")))
}

#[tauri::command]
pub fn list_modules(app: AppHandle) -> Result<Vec<ModuleDescriptor>, IpcError> {
    let path = modules_path(&app)?;
    Ok(modules::read_modules(&path).modules)
}

#[tauri::command]
pub fn set_module_enabled(app: AppHandle, id: String, enabled: bool) -> Result<(), IpcError> {
    let path = modules_path(&app)?;
    let found = modules::set_module_enabled(&path, &id, enabled)
        .map_err(|e| IpcError::Io(e.to_string()))?;
    if !found {
        return Err(IpcError::InvalidProject(format!("unknown module id: {id}")));
    }
    Ok(())
}

/// Named divergence from program design section 2.3's `meme_find ->
/// MemeResult { path, source }`: this returns the ranked hub list from
/// `claude-memes find`, not a single Giphy-query result, per the operator's
/// slice-3 direction (subprocess `list`/`find`, not the `claude-memes mcp`
/// stdio surface). See `dashboard_core::meme` module doc for the full
/// rationale and the rejected alternative.
#[tauri::command]
pub fn meme_list_events() -> Result<Vec<MemeEvent>, IpcError> {
    let stdout = meme_process::run_list().map_err(|e| IpcError::Io(e.to_string()))?;
    Ok(parse_list(&stdout))
}

#[tauri::command]
pub fn meme_find(query: String) -> Result<Vec<FindHit>, IpcError> {
    if query.trim().is_empty() {
        return Err(IpcError::InvalidProject("empty concept query".to_string()));
    }
    let stdout = meme_process::run_find(&query).map_err(|e| IpcError::Io(e.to_string()))?;
    Ok(parse_find(&stdout))
}
