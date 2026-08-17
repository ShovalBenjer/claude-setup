import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, CircleX, Loader2 } from "lucide-react";
import type { GateRun } from "../types";
import { verdictLabel } from "../types";
import { latestGateVerdict } from "../ipc";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { cn } from "../lib/cn";

interface Props {
  project: string;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ok"; run: GateRun };

// Design anchor: block/buzz (https://github.com/block/buzz), shallow-cloned
// and read 2026-08-17 — dark Catppuccin-derived palette, Card/Badge
// primitives at web/src/shared/ui/*.tsx. Tokens and component shells now
// live in src/index.css and src/components/ui/*; this tile consumes them
// instead of the bespoke GateVerdictTile.css it used before.
function verdictTone(v: GateRun["verdict"]): "pass" | "fail" | "partial" | "unknown" {
  if (typeof v === "string") {
    if (v === "pass") return "pass";
    if (v === "fail") return "fail";
    if (v === "partial") return "partial";
  }
  return "unknown";
}

const TONE_META = {
  pass: {
    badge: "default" as const,
    icon: CheckCircle2,
    text: "text-primary",
    ring: "ring-primary/40",
  },
  fail: {
    badge: "destructive" as const,
    icon: CircleX,
    text: "text-destructive",
    ring: "ring-destructive/40",
  },
  partial: {
    badge: "warning" as const,
    icon: CircleAlert,
    text: "text-warning",
    ring: "ring-warning/40",
  },
  unknown: {
    badge: "secondary" as const,
    icon: CircleAlert,
    text: "text-muted-foreground",
    ring: "ring-border",
  },
};

export function GateVerdictTile({ project }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    latestGateVerdict(project)
      .then((run) => {
        if (cancelled) return;
        setState(run ? { status: "ok", run } : { status: "empty" });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState({ status: "error", message: String(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [project]);

  if (state.status === "loading") {
    return (
      <Card className="w-72">
        <CardHeader>
          <CardTitle>Gate</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Loading...</span>
        </CardContent>
      </Card>
    );
  }

  if (state.status === "error") {
    return (
      <Card className="w-72 ring-1 ring-destructive/40">
        <CardHeader>
          <CardTitle>Gate</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="destructive">UNAVAILABLE</Badge>
          <p className="mt-2 text-xs text-muted-foreground">{state.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (state.status === "empty") {
    return (
      <Card className="w-72">
        <CardHeader>
          <CardTitle>Gate</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="secondary">NO RUNS YET</Badge>
        </CardContent>
      </Card>
    );
  }

  const { run } = state;
  const tone = verdictTone(run.verdict);
  const meta = TONE_META[tone];
  const Icon = meta.icon;
  const duration = run.duration_seconds !== null ? `${run.duration_seconds.toFixed(1)}s` : "n/a";

  return (
    <Card className={cn("w-72 ring-1", meta.ring)}>
      <CardHeader>
        <CardTitle>Gate</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <Icon className={cn("h-5 w-5", meta.text)} />
          <span className={cn("text-lg font-bold", meta.text)}>{verdictLabel(run.verdict)}</span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {duration} &middot; {run.project} &middot; {run.ts}
        </p>
      </CardContent>
    </Card>
  );
}
