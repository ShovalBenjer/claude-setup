import { GateVerdictTile } from "./components/GateVerdictTile";
import { AppShell } from "./components/AppShell";

// Slice 2 scope: one live tile (GateVerdictTile), a hardcoded project path
// (`list_projects` is stubbed server-side per the program design, so there
// is no picker yet). Sidebar/LiveView/ModuleRegistry/TaskBoard/
// CommunicationSurface from the program design's component tree land in
// later slices; AppShell below is the sidebar+topbar frame for that
// eventual layout, not the full component tree itself.
const PROJECT_PATH = ".";

export default function App() {
  return (
    <AppShell project={PROJECT_PATH}>
      <div className="flex flex-wrap gap-4">
        <GateVerdictTile project={PROJECT_PATH} />
      </div>
    </AppShell>
  );
}
