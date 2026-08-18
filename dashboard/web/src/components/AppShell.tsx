import type { ReactNode } from "react";
import { Activity, GitBranch, LayoutDashboard, ListTodo, Settings } from "lucide-react";

import { cn } from "../lib/cn";

interface NavItem {
  label: string;
  icon: typeof LayoutDashboard;
  active?: boolean;
}

// pattern inspired by shadcn/ui's "dashboard-01" block layout
// (https://ui.shadcn.com/blocks, fixed left icon+label sidebar over a
// header/content column) and buzz's own left-rail app shell
// (web/src/app/App.tsx + shared/theme, cloned + read 2026-08-17). Nav items
// below are named for this dashboard's own domains (Gate, Agents, Runs),
// not copied from either source.
const NAV_ITEMS: NavItem[] = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Gate runs", icon: Activity },
  { label: "Prompt tickets", icon: ListTodo },
  { label: "Agent spawns", icon: GitBranch },
];

function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-3 py-4 md:flex">
      <div className="mb-6 flex items-center gap-2 px-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
          S
        </div>
        <span className="text-sm font-semibold tracking-wide text-sidebar-foreground">
          Session Dashboard
        </span>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            type="button"
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
              item.active
                ? "bg-primary/15 text-primary"
                : "text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground",
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </nav>
      <button
        type="button"
        className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium text-sidebar-foreground/60 hover:bg-accent/50 hover:text-sidebar-foreground"
      >
        <Settings className="h-4 w-4" />
        Settings
      </button>
    </aside>
  );
}

function Topbar({ project }: { project: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/70 px-6">
      <div>
        <h1 className="text-sm font-semibold text-foreground">Overview</h1>
        <p className="text-xs text-muted-foreground">{project}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 rounded-full bg-primary" />
        <span className="text-xs text-muted-foreground">live</span>
      </div>
    </header>
  );
}

export function AppShell({ project, children }: { project: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar project={project} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
