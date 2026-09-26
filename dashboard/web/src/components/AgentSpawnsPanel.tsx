import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import type { AgentSpawnRow, LedgerReadReport } from "../types";
import { readAgentSpawns } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { FeedList, FeedRow } from "./FeedRow";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ok"; report: LedgerReadReport<AgentSpawnRow> };

// Real reader wired 2026-09-01 (dashboard/core/src/ledger/agent_spawns.rs),
// replacing the zero-field stub PR #85/v2 restyle explicitly deferred ("this
// ledger has real rows on disk waiting on a real reader, tracked separately").
// Follows GateRunsPanel's proven feed shape: FeedList/FeedRow, a skipped-count
// warning, one row per spawn. No status dot: a spawn has no pass/fail verdict
// of its own (gate runs do), so forcing a tone here would be a fabricated
// signal, not a derived one -- the same discipline App.tsx's rail already
// applies to this same ledger ("rendering anything but unknown would be a
// fabricated status").
export function AgentSpawnsPanel({ project }: { project: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    readAgentSpawns(project, 50)
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
    <Card className="w-full" data-panel="agent-spawns">
      <CardHeader>
        <CardTitle>Agent spawns</CardTitle>
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
          <Badge variant="secondary">NO SPAWNS YET</Badge>
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
              {[...state.report.rows].reverse().map((row, i) => (
                <FeedRow
                  key={`${row.ts}-${i}`}
                  icon={Bot}
                  timestamp={row.ts}
                  reference={
                    row.isolation
                      ? { label: "isolation", value: row.isolation }
                      : row.background
                        ? { label: "mode", value: "background" }
                        : undefined
                  }
                >
                  {row.subagent_type}
                  {row.description ? `: ${row.description}` : ""}
                  {row.router_named.length > 0
                    ? ` · routed ${row.router_named.join(", ")}`
                    : ""}
                </FeedRow>
              ))}
            </FeedList>
          </>
        )}
      </CardContent>
    </Card>
  );
}
