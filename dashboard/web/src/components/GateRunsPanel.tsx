import { useEffect, useState } from "react";
import type { GateRun, LedgerReadReport } from "../types";
import { verdictLabel } from "../types";
import { readGateRuns } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ok"; report: LedgerReadReport<GateRun> };

// Nav-routing fix: this is the panel the "Gate runs" sidebar item pointed
// at nothing before. `read_gate_runs` was already a fully implemented,
// tested Rust reader (dashboard/core/src/ledger/gate_runs.rs) with no
// frontend caller; this consumes it via ipc.ts's new `readGateRuns`.
export function GateRunsPanel({ project }: { project: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    readGateRuns(project, 50)
      .then((report) => {
        if (!cancelled) setState({ status: "ok", report });
      })
      .catch((err: unknown) => {
        if (!cancelled) setState({ status: "error", message: String(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [project]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Gate runs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {state.status === "loading" && (
          <p className="text-sm text-muted-foreground">Loading...</p>
        )}
        {state.status === "error" && (
          <>
            <Badge variant="destructive">UNAVAILABLE</Badge>
            <p className="mt-2 text-xs text-muted-foreground">{state.message}</p>
          </>
        )}
        {state.status === "ok" && state.report.rows.length === 0 && (
          <Badge variant="secondary">NO RUNS YET</Badge>
        )}
        {state.status === "ok" && state.report.rows.length > 0 && (
          <>
            {state.report.skipped > 0 && (
              <p className="text-xs text-status-warn">
                {state.report.skipped} malformed line(s) skipped
                {state.report.first_error ? `: ${state.report.first_error}` : ""}
              </p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="pb-2 pr-4">Timestamp</th>
                    <th className="pb-2 pr-4">Project</th>
                    <th className="pb-2 pr-4">Verdict</th>
                    <th className="pb-2 pr-4">Commit</th>
                    <th className="pb-2">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {[...state.report.rows].reverse().map((run, i) => (
                    <tr key={`${run.ts}-${i}`} className="border-t border-border/50">
                      <td className="py-1.5 pr-4 text-xs text-muted-foreground">{run.ts}</td>
                      <td className="py-1.5 pr-4">{run.project}</td>
                      <td className="py-1.5 pr-4">{verdictLabel(run.verdict)}</td>
                      <td className="py-1.5 pr-4 font-mono text-xs">
                        {run.commit ? run.commit.slice(0, 8) : "n/a"}
                      </td>
                      <td className="py-1.5">
                        {run.duration_seconds !== null ? `${run.duration_seconds.toFixed(1)}s` : "n/a"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
