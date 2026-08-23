import type { ReactNode } from "react";

import type { RailEntry } from "./Rail";
import { Rail } from "./Rail";
import type { View } from "../types";

// DASH-1 v2: AppShell's Sidebar/Topbar pair is replaced by Rail (compact
// cmux-style vertical tabs, see Rail.tsx) plus a slimmer Topbar that no
// longer duplicates the rail's own label -- the rail button's title
// attribute and the topbar heading would otherwise say the same thing
// twice in a narrower shell. Topbar keeps the project path and a live
// pulse per the pre-v2 shell; nav state (`view`/`onSelectView`) still
// lives in App.tsx per the nav-routing fix, AppShell only renders it.
const VIEW_TITLE: Record<View, string> = {
  overview: "Overview",
  "gate-runs": "Gate runs",
  "prompt-tickets": "Prompt tickets",
  "agent-spawns": "Agent spawns",
  meme: "Meme events",
};

function Topbar({ project, view }: { project: string; view: View }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/70 px-6">
      <div>
        <h1 className="text-sm font-semibold text-foreground">{VIEW_TITLE[view]}</h1>
        <p className="text-xs text-muted-foreground">{project}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 rounded-full bg-primary" />
        <span className="text-xs text-muted-foreground">live</span>
      </div>
    </header>
  );
}

export function AppShell({
  project,
  view,
  onSelectView,
  railEntries,
  children,
}: {
  project: string;
  view: View;
  onSelectView: (v: View) => void;
  railEntries: RailEntry[];
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Rail entries={railEntries} view={view} onSelect={onSelectView} />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar project={project} view={view} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
