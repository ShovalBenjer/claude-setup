// Mirrors dashboard/core/src/ledger/gate_runs.rs and dashboard/core/src/lib.rs.
// Kept hand-in-sync for slice 2; a generated-bindings step (e.g. ts-rs) is
// deferred, not rejected, since only one reader (GateRun) exists yet and a
// codegen step for a single type is not worth the build-graph addition.

export type Verdict =
  | "pass"
  | "fail"
  | "partial"
  | { unknown: string };

export interface GateRun {
  ts: string;
  project: string;
  project_path: string;
  commit: string;
  dirty: boolean;
  fingerprint: string;
  partial: boolean;
  verdict: Verdict;
  domains: Record<string, string>;
  blocking: string[];
  waivers_unconfirmed: string[];
  unmeasured: string[];
  duration_seconds: number | null;
  domain_seconds: Record<string, number> | null;
}

export interface LedgerReadReport<T> {
  rows: T[];
  skipped: number;
  total_lines: number;
  first_error: string | null;
}

export type IpcError =
  | { kind: "not_found"; message: string }
  | { kind: "io"; message: string }
  | { kind: "invalid_project"; message: string };

export function verdictLabel(v: Verdict): string {
  if (typeof v === "string") return v.toUpperCase();
  return v.unknown;
}

// Mirrors dashboard/core/src/modules.rs (DASH-1 slice 3).
export interface ModuleDescriptor {
  id: string;
  name: string;
  enabled: boolean;
}

// Mirrors dashboard/core/src/meme.rs. Named divergence from the program
// design's `MemeResult { path, source }`: see that file's module doc for
// why (operator's slice-3 direction: subprocess `list`/`find`, not the
// `claude-memes mcp` stdio surface).
export interface MemeEvent {
  id: string;
  query: string;
  trigger: string;
}

export interface FindHit {
  hub: string;
  score: number;
  queries: string[];
}

// DASH-1 nav-routing fix: the four sidebar destinations. Lifted to App.tsx
// so AppShell (sidebar + topbar) and the content area share one source of
// truth for which panel is active.
// DASH-1 v2: "meme" added as a fifth view -- direction doc item 4 folds
// the meme module's entry point into the rail rather than keeping it as a
// full-width section nested under Overview's ModuleRegistry card. The
// toggle itself (enable/disable) still lives in ModuleRegistry on the
// Overview view; this view only renders MemeModule's content when the
// module is enabled and the rail entry is selected.
export type View = "overview" | "gate-runs" | "prompt-tickets" | "agent-spawns" | "meme";

// Mirrors dashboard/core/src/lib.rs LedgerReadReport<T>, generic over the
// row type. `skipped > 0` must be surfaced (lib.rs doc comment: "the UI is
// expected to surface `skipped > 0` as a visible badge so an unknown-schema
// line is never invisible to the operator").
export interface LedgerReadReport<T> {
  rows: T[];
  skipped: number;
  total_lines: number;
  first_error: string | null;
}

// Mirrors dashboard/core/src/ledger/agent_spawns.rs AgentSpawn. Fields taken
// from the real shape observed in state/agent-spawns.jsonl, 2026-09-01: see
// that file's module doc for why model/isolation are plain strings (an
// empty string is a real "no override" value, not an absent field).
export interface AgentSpawnRow {
  ts: string;
  subagent_type: string;
  description: string;
  model: string;
  background: boolean;
  isolation: string;
  prompt_chars: number;
  session: string;
  cwd: string;
  router_named: string[];
  router_skills: string[];
  router_named_at: string;
}
