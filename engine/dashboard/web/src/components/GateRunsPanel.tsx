import { useEffect, useState } from "react";
import { GitCommitHorizontal } from "lucide-react";
import type { GateRun, LedgerReadReport } from "../types";
import { verdictLabel } from "../types";
import { readGateRuns } from "../ipc";
import { verdictTone } from "../lib/status";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { FeedList, FeedRow } from "./FeedRow";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ok"; report: LedgerReadReport<GateRun> };

// DASH-1 v2 restyle: was a <table> with five plain columns. Rebuilt as a
// buzz-style compact feed (direction doc item 2): one FeedRow per gate
// run, timestamp + a git-commit glyph as the source icon, one-line
// content ("VERDICT on project"), and an inline reference chip carrying
// the commit sha -- the "inline reference chip for anything with an
// id/sha" the direction doc calls for. Each row's status dot reuses the
// same verdictTone GateVerdictTile already computes, so a FAIL run reads
// as a red dot in both the tile and the feed, not two different scales.
// Data is real: read_gate_runs is the same fully implemented Rust reader
// PR #85 wired; only the presentation changed here.
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
    <Card className="w-full" data-panel="gate-runs">
      <CardHeader>
        <CardTitle>Gate runs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
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
              <p className="pb-2 text-xs text-status-warn">
                {state.report.skipped} malformed line(s) skipped
                {state.report.first_error ? `: ${state.report.first_error}` : ""}
              </p>
            )}
            <FeedList>
              {[...state.report.rows].reverse().map((run, i) => (
                <FeedRow
                  key={`${run.ts}-${i}`}
                  icon={GitCommitHorizontal}
                  timestamp={run.ts}
                  tone={verdictTone(run.verdict)}
                  reference={
                    run.commit
                      ? { label: "commit", value: run.commit.slice(0, 8) }
                      : undefined
                  }
                >
                  {verdictLabel(run.verdict)} on {run.project}
                  {run.duration_seconds !== null ? ` · ${run.duration_seconds.toFixed(1)}s` : ""}
                </FeedRow>
              ))}
            </FeedList>
          </>
        )}
      </CardContent>
    </Card>
  );
}
