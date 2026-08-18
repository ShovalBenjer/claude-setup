import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

// Nav-routing fix: "Prompt tickets" has no backing IPC command or Rust
// reader at all (dashboard/core/src/ledger has readers for gate_runs and
// stubs for claims/agent_spawns/skill_use/routing/bus — none of those is
// state/prompt-tickets.jsonl). Mapping this tab onto `read_claims_cmd`
// would silently show the wrong ledger's data, so instead this panel
// renders an honest empty state naming the gap rather than fabricating or
// mis-sourcing data.
export function PromptTicketsPanel() {
  return (
    <Card className="w-full">
      <CardHeader>
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
