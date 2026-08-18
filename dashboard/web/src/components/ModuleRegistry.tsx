import { useEffect, useState } from "react";
import type { ModuleDescriptor } from "../types";
import { listModules, setModuleEnabled } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Switch } from "./ui/switch";
import { MemeModule } from "./MemeModule";

// Program design section 3, acceptance row 3: capability modules with a
// per-module toggle. Single source of truth for toggle state lives here
// (a `Map<moduleId, boolean>` derived from `list_modules`, mutated only
// through `set_module_enabled`), matching the ModuleRegistryContext note
// in the program design rather than each module owning its own flag.
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
    // optimistic update, reverted on IPC failure
    const prev = modules;
    setModules(modules.map((m) => (m.id === id ? { ...m, enabled: next } : m)));
    setModuleEnabled(id, next).catch((err: unknown) => {
      setModules(prev);
      setError(String(err));
    });
  }

  const memeEnabled = modules?.find((m) => m.id === "meme")?.enabled ?? false;

  return (
    <div className="space-y-4">
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
        </CardContent>
      </Card>

      {memeEnabled && <MemeModule />}
    </div>
  );
}
