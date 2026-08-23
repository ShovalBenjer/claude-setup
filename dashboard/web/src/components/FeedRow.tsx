import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "../lib/cn";
import { TONE_DOT_CLASS, type StatusTone } from "../lib/status";

// buzz message-row grammar (docs/assets/screenshots/channel-agents.png,
// viewed directly from a shallow clone at /tmp/buzz-check this session):
// each row is source-glyph + name + timestamp on one line, one-line
// message body below, and an inline reference chip ("Buzz - PR" /
// "GitHub - PR": small icon-in-box, a two-line label) for anything
// carrying a PR/commit/link. Adopted here as a compact feed row for
// ledger data instead of buzz's literal avatar+name (these are session
// events, not people -- direction doc: "a source icon (not a person
// avatar -- sessions aren't people)"). Explicitly not adopted: buzz's
// emoji reaction strip (operator flagged emoji-as-primary-signal to move
// past, not copy) and its avatar images.
export interface FeedRowRef {
  label: string;
  value: string;
}

export function FeedRow({
  icon: Icon,
  timestamp,
  children,
  tone,
  reference,
}: {
  icon: LucideIcon;
  timestamp: string;
  children: ReactNode;
  tone?: StatusTone;
  reference?: FeedRowRef;
}) {
  return (
    <div className="flex items-start gap-3 border-b border-border/40 px-1 py-2.5 last:border-b-0">
      <span className="relative mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {tone && (
          <span
            data-status-dot={tone}
            className={cn("absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full ring-1 ring-card", TONE_DOT_CLASS[tone])}
          />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[10px] text-muted-foreground">{timestamp}</span>
        </div>
        <p className="truncate text-sm text-foreground">{children}</p>
        {reference && (
          <div className="mt-1.5 inline-flex items-center gap-2 rounded-md border border-border/70 bg-muted/40 px-2 py-1 text-xs">
            <span className="font-medium text-muted-foreground">{reference.label}</span>
            <span className="font-mono text-foreground">{reference.value}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function FeedList({ children }: { children: ReactNode }) {
  return <div className="flex flex-col">{children}</div>;
}
