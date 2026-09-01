import { useEffect, useState } from "react";
import { GateVerdictTile } from "./components/GateVerdictTile";
import { AppShell } from "./components/AppShell";
import { ModuleRegistry } from "./components/ModuleRegistry";
import { GateRunsPanel } from "./components/GateRunsPanel";
import { PromptTicketsPanel } from "./components/PromptTicketsPanel";
import { AgentSpawnsPanel } from "./components/AgentSpawnsPanel";
import { MemeModule } from "./components/MemeModule";
import { RAIL_ICONS, type RailEntry } from "./components/Rail";
import type { View } from "./types";
import { latestGateVerdict, listModules } from "./ipc";
import { verdictTone } from "./lib/status";

// Slice 2 scope carried a hardcoded project path (`list_projects` is
// stubbed server-side per the program design, so there is no picker yet).
const PROJECT_PATH = ".";

// DASH-1 v2: rail entries are built here (not inside Rail.tsx) because
// they need two pieces of app-level state Rail itself has no access to:
// the latest gate verdict (tone for gate-runs/overview) and whether the
// meme module is enabled (whether its rail entry appears at all --
// direction doc item 4, "fold its entry point into the left rail").
// gate-runs/overview share one tone (both surface the same latest run);
// prompt-tickets/agent-spawns get "unknown" because neither has a
// verdict of its own to derive a tone from: prompt-tickets still has no
// reader at all, and agent-spawns' reader is real (2026-09-01) but a
// spawn row carries no pass/fail signal -- rendering anything but
// "unknown" there would be a fabricated status, not a derived one.
function useRailEntries(project: string): RailEntry[] {
  const [tone, setTone] = useState<ReturnType<typeof verdictTone>>("unknown");
  const [memeEnabled, setMemeEnabled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    latestGateVerdict(project)
      .then((run) => {
        if (!cancelled && run) setTone(verdictTone(run.verdict));
      })
      .catch((err: unknown) => {
        // rail falls back to "unknown"; GateVerdictTile/GateRunsPanel
        // surface the real UNAVAILABLE error to the operator, so this is
        // not a silent-pass swallow -- it is logged for diagnosis and the
        // rail dot just stays neutral rather than duplicating that error
        // text at icon size.
        console.warn("rail: latestGateVerdict failed, dot stays unknown", err);
      });
    listModules()
      .then((modules) => {
        if (!cancelled) setMemeEnabled(modules.some((m) => m.id === "meme" && m.enabled));
      })
      .catch((err: unknown) => {
        console.warn("rail: listModules failed, meme entry stays hidden", err);
      });
    return () => {
      cancelled = true;
    };
  }, [project]);

  const entries: RailEntry[] = [
    { view: "overview", label: "Overview", detail: "modules + gate tile", icon: RAIL_ICONS.overview, tone },
    { view: "gate-runs", label: "Gate runs", detail: "state/gate-runs.jsonl", icon: RAIL_ICONS["gate-runs"], tone },
    {
      view: "prompt-tickets",
      label: "Tickets",
      detail: "no reader wired",
      icon: RAIL_ICONS["prompt-tickets"],
      tone: "unknown",
    },
    {
      view: "agent-spawns",
      label: "Spawns",
      detail: "state/agent-spawns.jsonl",
      icon: RAIL_ICONS["agent-spawns"],
      tone: "unknown",
    },
  ];
  if (memeEnabled) {
    entries.push({ view: "meme", label: "Memes", detail: "module enabled", icon: RAIL_ICONS.meme, tone: "unknown" });
  }
  return entries;
}

export default function App() {
  const [view, setView] = useState<View>("overview");
  const railEntries = useRailEntries(PROJECT_PATH);

  return (
    <AppShell project={PROJECT_PATH} view={view} onSelectView={setView} railEntries={railEntries}>
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
      {view === "meme" && <MemeModule />}
    </AppShell>
  );
}
