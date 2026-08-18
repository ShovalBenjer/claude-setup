import { Activity, GitBranch, LayoutDashboard, ListTodo, Smile } from "lucide-react";

import { cn } from "../lib/cn";
import type { View } from "../types";
import { TONE_DOT_CLASS, type StatusTone } from "../lib/status";

// Left rail redesign (DASH-1 v2, direction doc "Target shape"): replaces
// the prior w-56 labeled sidebar (4 wide buttons, text + icon) with a
// compact icon-width vertical tab strip modeled on cmux.com (read via the
// direction doc's live-inspected transcription, not re-fetched this
// session -- no browser/web-fetch tool was available here; see the PR
// description for that gap named plainly). cmux's rail is one narrow
// tab per session (branch, cwd, a status/notification indicator), not a
// wide labeled menu. This rail keeps that shape: fixed 64px width, one
// entry per wired data-source (not per invented "session", since no
// session-scoped reader exists in dashboard/core -- agent-spawns' own
// reader is a zero-field stub), icon plus a truncated label (not the
// prior sidebar's full-width text row), a title attribute carrying the
// full label + detail for hover, and a small status dot per entry sourced from
// real gate-verdict data via RailEntry.tone (never a decorative color:
// entries with no verdict data render the "unknown" muted tone, not a
// fabricated pass).
export interface RailEntry {
  view: View;
  label: string;
  detail: string;
  icon: typeof LayoutDashboard;
  tone: StatusTone;
}

export const RAIL_ICONS: Record<View, typeof LayoutDashboard> = {
  overview: LayoutDashboard,
  "gate-runs": Activity,
  "prompt-tickets": ListTodo,
  "agent-spawns": GitBranch,
  meme: Smile,
};

function RailButton({
  entry,
  active,
  onSelect,
}: {
  entry: RailEntry;
  active: boolean;
  onSelect: (v: View) => void;
}) {
  const Icon = entry.icon;
  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      aria-label={`${entry.label}: ${entry.detail}`}
      title={`${entry.label} -- ${entry.detail}`}
      data-rail-entry={entry.view}
      onClick={() => onSelect(entry.view)}
      className={cn(
        "group relative flex w-full flex-col items-center gap-1 rounded-lg px-1.5 py-2.5 text-[10px] font-medium transition-colors",
        active
          ? "bg-primary/15 text-primary"
          : "text-sidebar-foreground/60 hover:bg-accent/50 hover:text-sidebar-foreground",
      )}
    >
      <span className="relative flex h-5 w-5 items-center justify-center">
        <Icon className="h-4 w-4" />
        <span
          data-status-dot={entry.tone}
          className={cn(
            "absolute -right-1 -top-1 h-2 w-2 rounded-full ring-2 ring-sidebar",
            TONE_DOT_CLASS[entry.tone],
          )}
        />
      </span>
      <span className="w-full truncate text-center leading-tight">{entry.label}</span>
    </button>
  );
}

// cmux keeps its rail narrow (icon/compact width) rather than the wide
// labeled sidebar this dashboard had; w-16 (64px) here is that same
// compact-width call, not a wide menu with room for a settings row and a
// brand lockup. Each entry still carries a short truncated label under
// the icon (not a strictly icon-only rail); the full label plus detail is
// in the buttons title attribute for hover.
export function Rail({
  entries,
  view,
  onSelect,
}: {
  entries: RailEntry[];
  view: View;
  onSelect: (v: View) => void;
}) {
  return (
    <aside
      aria-label="Sessions and data sources"
      className="hidden w-16 shrink-0 flex-col items-center gap-1 border-r border-sidebar-border bg-sidebar py-3 md:flex"
    >
      <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
        S
      </div>
      <nav className="flex w-full flex-1 flex-col gap-1 px-1.5">
        {entries.map((entry) => (
          <RailButton key={entry.view} entry={entry} active={view === entry.view} onSelect={onSelect} />
        ))}
      </nav>
    </aside>
  );
}
