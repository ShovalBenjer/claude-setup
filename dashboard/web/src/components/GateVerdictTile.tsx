import { useEffect, useState } from "react";
import type { GateRun } from "../types";
import { verdictLabel } from "../types";
import { latestGateVerdict } from "../ipc";
import "./GateVerdictTile.css";

interface Props {
  project: string;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ok"; run: GateRun };

// Design anchor: the buzz UI clone (dark background, bold oversized type,
// high-contrast status color as the single accent) per the direction spec
// (docs/specs/2026-08-17-session-dashboard-direction.md) and the
// out-of-distribution rule's requirement to name the anchor in the artifact.
// The task named a live clone path (/home/shov/.claude/jobs/b771656c/tmp/buzz)
// that does not exist on this machine as of 2026-08-17 (checked before
// writing this file); the anchor is applied from the direction spec's
// written description (dark, bold, buzz-style) rather than from pixels, and
// that gap is recorded here rather than silently ignored.
function verdictColor(v: GateRun["verdict"]): string {
  if (typeof v === "string") {
    if (v === "pass") return "#3ddc84";
    if (v === "fail") return "#ff5c5c";
    if (v === "partial") return "#ffb454";
  }
  return "#8a8fa3";
}

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
      <div className="gate-tile gate-tile--loading">
        <span className="gate-tile__label">GATE</span>
        <span className="gate-tile__verdict">…</span>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="gate-tile gate-tile--error">
        <span className="gate-tile__label">GATE</span>
        <span className="gate-tile__verdict">UNAVAILABLE</span>
        <span className="gate-tile__meta">{state.message}</span>
      </div>
    );
  }

  if (state.status === "empty") {
    return (
      <div className="gate-tile gate-tile--empty">
        <span className="gate-tile__label">GATE</span>
        <span className="gate-tile__verdict">NO RUNS YET</span>
      </div>
    );
  }

  const { run } = state;
  const duration =
    run.duration_seconds !== null ? `${run.duration_seconds.toFixed(1)}s` : "n/a";

  return (
    <div className="gate-tile" style={{ borderColor: verdictColor(run.verdict) }}>
      <span className="gate-tile__label">GATE</span>
      <span className="gate-tile__verdict" style={{ color: verdictColor(run.verdict) }}>
        {verdictLabel(run.verdict)}
      </span>
      <span className="gate-tile__meta">
        {duration} · {run.project} · {run.ts}
      </span>
    </div>
  );
}
