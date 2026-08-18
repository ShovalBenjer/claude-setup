import { GateVerdictTile } from "./components/GateVerdictTile";
import { AppShell } from "./components/AppShell";
import { ModuleRegistry } from "./components/ModuleRegistry";

// Slice 2 scope carried a hardcoded project path (`list_projects` is
// stubbed server-side per the program design, so there is no picker yet).
// Slice 3 adds ModuleRegistry (acceptance row 3: capability modules with a
// per-module toggle, first real module is meme). TaskBoard/
// CommunicationSurface from the program design's component tree land in
// later slices; AppShell below is the sidebar+topbar frame for that
// eventual layout, not the full component tree itself.
const PROJECT_PATH = ".";

export default function App() {
  return (
    <AppShell project={PROJECT_PATH}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap gap-4">
          <GateVerdictTile project={PROJECT_PATH} />
        </div>
        <ModuleRegistry />
      </div>
    </AppShell>
  );
}
