import { ListTodo } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

// DASH-1 v2 restyle: still no backing IPC command or Rust reader for
// state/prompt-tickets.jsonl (dashboard/core/src/ledger has readers for
// gate_runs and stubs for claims/agent_spawns/skill_use/routing/bus --
// none of those is state/prompt-tickets.jsonl). Only the shell changed to
// match the other panels' feed-card frame; still no fabricated content
// and still no reuse of a different ledger's reader.
export function PromptTicketsPanel() {
  return (
    <Card className="w-full" data-panel="prompt-tickets">
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <ListTodo className="h-4 w-4 text-muted-foreground" />
        <CardTitle>Prompt tickets</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Badge variant="secondary">NO READER WIRED</Badge>
        <p className="text-xs text-muted-foreground">
          No IPC command or Rust reader exists yet for
          state/prompt-tickets.jsonl. This panel intentionally shows no data
          rather than reusing a different ledger's reader or fabricating
          content.
        </p>
      </CardContent>
    </Card>
  );
}
