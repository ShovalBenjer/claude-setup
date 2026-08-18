import { useState } from "react";
import { GateVerdictTile } from "./components/GateVerdictTile";
import { AppShell } from "./components/AppShell";
import { ModuleRegistry } from "./components/ModuleRegistry";
import { GateRunsPanel } from "./components/GateRunsPanel";
import { PromptTicketsPanel } from "./components/PromptTicketsPanel";
import { AgentSpawnsPanel } from "./components/AgentSpawnsPanel";
import type { View } from "./types";

// Slice 2 scope carried a hardcoded project path (`list_projects` is
// stubbed server-side per the program design, so there is no picker yet).
// Slice 3 adds ModuleRegistry (acceptance row 3: capability modules with a
// per-module toggle, first real module is meme). TaskBoard/
// CommunicationSurface from the program design's component tree land in
// later slices; AppShell below is the sidebar+topbar frame for that
// eventual layout, not the full component tree itself.
const PROJECT_PATH = ".";

// Nav-routing fix: the sidebar's four buttons previously had no onClick and
// `active` was a hardcoded literal in AppShell's NAV_ITEMS, so clicking
// anything but the (permanently "active") Overview button did nothing —
// App.tsx always rendered the same fixed children regardless of the
// sidebar. View state now lives here, the one place both AppShell (which
// button is highlighted, what the topbar title says) and the content area
// (which panel renders) can read it from.
export default function App() {
  const [view, setView] = useState<View>("overview");

  return (
    <AppShell project={PROJECT_PATH} view={view} onSelectView={setView}>
      {view === "overview" && (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-4">
            <GateVerdictTile project={PROJECT_PATH} />
          </div>
          <ModuleRegistry />
        </div>
      )}
      {view === "gate-runs" && <GateRunsPanel project={PROJECT_PATH} />}
      {view === "prompt-tickets" && <PromptTicketsPanel />}
      {view === "agent-spawns" && <AgentSpawnsPanel project={PROJECT_PATH} />}
    </AppShell>
  );
}
