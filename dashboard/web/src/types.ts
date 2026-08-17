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
