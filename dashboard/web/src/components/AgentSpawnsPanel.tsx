import { useEffect, useState } from "react";
import { readAgentSpawns } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

type LoadState = { status: "loading" } | { status: "error"; message: string } | { status: "ok" };

// Nav-routing fix: the "Agent spawns" IPC command (`read_agent_spawns_cmd`)
// is wired end to end, but its reader (dashboard/core/src/ledger/stubs.rs)
// is an honest stub — `AgentSpawn` is a zero-field struct and the reader
// always returns an empty report regardless of `state/agent-spawns.jsonl`.
// This panel calls the real command and states that plainly rather than
// fabricating rows the backend does not parse yet.
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
    <Card className="w-full">
      <CardHeader>
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
              shown here; this ledger has 71+ real rows on disk waiting on a
              real reader (tracked separately, not this nav-routing fix).
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
