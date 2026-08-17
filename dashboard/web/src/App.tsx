import { GateVerdictTile } from "./components/GateVerdictTile";
import "./App.css";

// Slice 2 scope: one live tile (GateVerdictTile), a hardcoded project path
// (`list_projects` is stubbed server-side per the program design, so there
// is no picker yet). Sidebar/LiveView/ModuleRegistry/TaskBoard/
// CommunicationSurface from the program design's component tree land in
// later slices.
const PROJECT_PATH = ".";

export default function App() {
  return (
    <main className="app">
      <h1 className="app__title">Session Dashboard</h1>
      <GateVerdictTile project={PROJECT_PATH} />
    </main>
  );
}
