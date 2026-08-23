import type {
  AgentSpawnRow,
  FindHit,
  GateRun,
  LedgerReadReport,
  MemeEvent,
  ModuleDescriptor,
} from "./types";

// Thin IPC wrapper around Tauri's `invoke`. `@tauri-apps/api` is not a
// declared dependency in this slice (the src-tauri crate itself is not
// buildable in this sandbox; see dashboard/src-tauri/Cargo.toml), so this
// module resolves `invoke` off `window.__TAURI__` at call time rather than
// importing the package, and falls back to a rejected promise outside a
// Tauri webview. This keeps `bun run build` / `npm run build` green without
// the package installed, while leaving a real call site for slice 3+ to
// swap in `@tauri-apps/api/core`'s `invoke` directly.
function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const tauri = (window as unknown as { __TAURI__?: { core?: { invoke: <U>(c: string, a?: Record<string, unknown>) => Promise<U> } } }).__TAURI__;
  if (!tauri?.core?.invoke) {
    return Promise.reject(new Error("not running inside a Tauri webview"));
  }
  return tauri.core.invoke<T>(cmd, args);
}

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
