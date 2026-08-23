import { invoke } from "@tauri-apps/api/core";
import type {
  AgentSpawnRow,
  FindHit,
  GateRun,
  LedgerReadReport,
  MemeEvent,
  ModuleDescriptor,
} from "./types";

// Thin IPC wrapper around Tauri's `invoke`, re-exported from
// `@tauri-apps/api/core` (the idiomatic Tauri 2 pattern for a bundled
// frontend: this app has a Vite/TypeScript build step, so it imports the
// real package rather than relying on `withGlobalTauri` window-namespace
// injection, which Tauri's own docs frame as the no-bundler convenience
// path). `@tauri-apps/api/core`'s `invoke` reads `window.__TAURI_INTERNALS__`,
// which the Tauri runtime injects into every webview regardless of the
// `withGlobalTauri` config value; `window.__TAURI__` (the old check this
// module used) is a separate, opt-in global bundle this app does not enable.
// Outside a real Tauri webview (e.g. `vite dev` in a browser tab) the
// import still resolves, but any call rejects because
// `window.__TAURI_INTERNALS__` is absent -- callers already handle a
// rejected promise via LedgerReadReport error paths and empty states.

export function latestGateVerdict(project: string): Promise<GateRun | null> {
  return invoke<GateRun | null>("latest_gate_verdict", { project });
}

// Nav-routing fix: `read_gate_runs` was already a real, tested Rust reader
// and IPC command (dashboard/src-tauri/src/commands.rs) with nothing in
// this file calling it. The Gate runs tab had no data path at all.
export function readGateRuns(
  project: string,
  limit?: number,
): Promise<LedgerReadReport<GateRun>> {
  return invoke<LedgerReadReport<GateRun>>("read_gate_runs", { project, limit });
}

// `read_agent_spawns_cmd` is wired end to end at the IPC boundary, but its
// reader (dashboard/core/src/ledger/stubs.rs) is an honest stub: it always
// returns an empty report regardless of `state/agent-spawns.jsonl`
// contents. Calling it here is correct (it is the real command); rendering
// its result must say "not implemented yet", not imply real rows.
export function readAgentSpawns(
  project: string,
  limit?: number,
): Promise<LedgerReadReport<AgentSpawnRow>> {
  return invoke<LedgerReadReport<AgentSpawnRow>>("read_agent_spawns_cmd", { project, limit });
}

// DASH-1 slice 3: module registry + meme module.
export function listModules(): Promise<ModuleDescriptor[]> {
  return invoke<ModuleDescriptor[]>("list_modules");
}

export function setModuleEnabled(id: string, enabled: boolean): Promise<void> {
  return invoke<void>("set_module_enabled", { id, enabled });
}

export function memeListEvents(): Promise<MemeEvent[]> {
  return invoke<MemeEvent[]>("meme_list_events");
}

export function memeFind(query: string): Promise<FindHit[]> {
  return invoke<FindHit[]>("meme_find", { query });
}
