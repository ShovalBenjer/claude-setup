import type { FindHit, GateRun, MemeEvent, ModuleDescriptor } from "./types";

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
