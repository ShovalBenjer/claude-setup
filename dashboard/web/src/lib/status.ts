import type { GateRun } from "../types";

export type StatusTone = "pass" | "fail" | "partial" | "unknown";

export function verdictTone(v: GateRun["verdict"]): StatusTone {
  if (typeof v === "string") {
    if (v === "pass") return "pass";
    if (v === "fail") return "fail";
    if (v === "partial") return "partial";
  }
  return "unknown";
}

export const TONE_DOT_CLASS: Record<StatusTone, string> = {
  pass: "bg-status-pass",
  fail: "bg-status-fail",
  partial: "bg-status-warn",
  unknown: "bg-muted-foreground/40",
};

export const TONE_TEXT_CLASS: Record<StatusTone, string> = {
  pass: "text-status-pass",
  fail: "text-status-fail",
  partial: "text-status-warn",
  unknown: "text-muted-foreground",
};

export const TONE_RING_CLASS: Record<StatusTone, string> = {
  pass: "ring-status-pass/40",
  fail: "ring-status-fail/40",
  partial: "ring-status-warn/40",
  unknown: "ring-border",
};
