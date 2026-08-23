import { useEffect, useState } from "react";
import { Smile } from "lucide-react";
import type { ModuleDescriptor } from "../types";
import { listModules, setModuleEnabled } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Switch } from "./ui/switch";

// Program design section 3, acceptance row 3: capability modules with a
// per-module toggle. Single source of truth for toggle state lives here
// (a `Map<moduleId, boolean>` derived from `list_modules`, mutated only
// through `set_module_enabled`), matching the ModuleRegistryContext note
// in the program design rather than each module owning its own flag.
//
// DASH-1 v2: this card used to render the full MemeModule inline right
// below the toggle list -- a second full-width section stacked under
// Overview. Direction doc item 4: "Meme module becomes one channel-level
// action, not a separate sidebar tab" was resolved (per the advisor's
// read of the task text, which is narrower than the direction doc's
// aspirational session-per-tab framing) as its own compact rail entry
// (App.tsx's useRailEntries adds a "Memes" tab only when this toggle is
// on). ModuleRegistry keeps owning the toggle -- that's still the single
// source of truth for enabled state -- but no longer duplicates the
// module's content inline; a one-line pointer to the rail replaces it.
export function ModuleRegistry() {
  const [modules, setModules] = useState<ModuleDescriptor[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listModules()
      .then((rows) => {
        if (!cancelled) setModules(rows);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function toggle(id: string, next: boolean) {
    if (!modules) return;
    const prev = modules;
    setModules(modules.map((m) => (m.id === id ? { ...m, enabled: next } : m)));
    setModuleEnabled(id, next).catch((err: unknown) => {
      setModules(prev);
      setError(String(err));
    });
  }

  const memeEnabled = modules?.find((m) => m.id === "meme")?.enabled ?? false;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Modules</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {error && <p className="text-xs text-destructive">{error}</p>}
        {!modules && !error && (
          <p className="text-xs text-muted-foreground">Loading...</p>
        )}
        {modules?.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between rounded-md px-2 py-1.5"
          >
            <span className="text-sm text-foreground">{m.name}</span>
            <Switch
              checked={m.enabled}
              onCheckedChange={(checked) => toggle(m.id, checked)}
            />
          </div>
        ))}
        {memeEnabled && (
          <p className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground">
            <Smile className="h-3.5 w-3.5" />
            Open the Memes tab in the rail to search and browse events.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
