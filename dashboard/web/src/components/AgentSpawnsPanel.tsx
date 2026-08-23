import { useEffect, useState } from "react";
import { GitBranch } from "lucide-react";
import { readAgentSpawns } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

type LoadState = { status: "loading" } | { status: "error"; message: string } | { status: "ok" };

// DASH-1 v2 restyle: still no fabricated rows. The Rust reader for
// state/agent-spawns.jsonl (dashboard/core/src/ledger/stubs.rs) remains a
// zero-field stub, so this panel cannot render a feed of real spawn
// events -- doing so would be exactly the "do not fabricate data to make
// the redesign look fuller" the task rules out. What changed is only the
// shell (feed-card frame matching GateRunsPanel's new look) and the icon
// (GitBranch, matching this entry's rail glyph); the honest empty-state
// copy is unchanged from PR #85.
export function AgentSpawnsPanel({ project }: { project: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    readAgentSpawns(project, 50)
      .then(() => {
        if (!cancelled) setState({ status: "ok" });
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
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <GitBranch className="h-4 w-4 text-muted-foreground" />
        <CardTitle>Agent spawns</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {state.status === "loading" && (
          <p className="text-sm text-muted-foreground">Loading...</p>
        )}
        {state.status === "error" && (
          <>
            <Badge variant="destructive">UNAVAILABLE</Badge>
            <p className="mt-2 text-xs text-muted-foreground">{state.message}</p>
          </>
        )}
        {state.status === "ok" && (
          <>
            <Badge variant="secondary">READER NOT IMPLEMENTED</Badge>
            <p className="text-xs text-muted-foreground">
              The IPC command is wired, but the Rust reader for
              state/agent-spawns.jsonl (dashboard/core/src/ledger/stubs.rs)
              is a stub that always returns zero rows. No fabricated data is
              shown here; this ledger has real rows on disk waiting on a
              real reader (tracked separately, not this restyle).
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
