import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import type { FindHit, MemeEvent } from "../types";
import { memeFind, memeListEvents } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

// First real module in ModuleRegistry (program design section 3:
// `ModuleRegistry > MemeModule`). Renders the 22 events from `claude-memes
// list` and a concept search box driving `find`. No GIF preview: network
// fetch of the Giphy query would need a CSP allowance this slice does not
// add (per the task's stated scope, "skip network fetches if it complicates
// CSP" — it does, since `default.json`'s capability is read-only/no-fs, and
// widening it for one image preview is out of scope here).
export function MemeModule() {
  const [events, setEvents] = useState<MemeEvent[] | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<FindHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    memeListEvents()
      .then((rows) => {
        if (!cancelled) setEvents(rows);
      })
      .catch((err: unknown) => {
        if (!cancelled) setEventsError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function runSearch(concept: string) {
    if (!concept.trim()) return;
    setSearching(true);
    setSearchError(null);
    memeFind(concept)
      .then((results) => setHits(results))
      .catch((err: unknown) => setSearchError(String(err)))
      .finally(() => setSearching(false));
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Meme events</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            runSearch(query);
          }}
        >
          <div className="flex flex-1 items-center gap-2 rounded-md border border-input bg-transparent px-3 py-1.5">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              placeholder="concept, e.g. tests failed"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {searching ? "..." : "Find"}
          </button>
        </form>

        {searchError && (
          <p className="text-xs text-destructive">{searchError}</p>
        )}

        {hits && (
          <ul className="space-y-1.5">
            {hits.length === 0 && (
              <li className="text-xs text-muted-foreground">No hubs matched.</li>
            )}
            {hits.map((hit) => (
              <li
                key={hit.hub}
                className="flex items-center justify-between gap-2 rounded-md bg-muted/50 px-2.5 py-1.5 text-xs"
              >
                <span className="font-medium text-foreground">{hit.hub}</span>
                <span className="truncate text-muted-foreground">
                  {hit.queries.join(" | ")}
                </span>
                <Badge variant="secondary">{hit.score.toFixed(3)}</Badge>
              </li>
            ))}
          </ul>
        )}

        <div className="border-t border-border/70 pt-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Registered events {events ? `(${events.length})` : ""}
          </p>
          {eventsError && <p className="text-xs text-destructive">{eventsError}</p>}
          {!events && !eventsError && (
            <p className="text-xs text-muted-foreground">Loading...</p>
          )}
          {events && (
            <ul className="grid max-h-56 grid-cols-1 gap-1 overflow-auto sm:grid-cols-2">
              {events.map((ev) => (
                <li key={ev.id} className="truncate text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{ev.id}</span>
                  {" "}&middot;{" "}{ev.trigger}
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
