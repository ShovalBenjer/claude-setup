import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/cn";

// pattern inspired by shadcn/ui's Badge primitive; buzz ships the same
// shape at web/src/shared/ui/badge.tsx (cloned + read 2026-08-17), where
// "default" is reserved for the brand accent (bg-primary/text-primary-
// foreground) and "destructive" is its own semantic variant
// (bg-destructive/text-destructive-foreground) — buzz never colors a
// status with its brand accent. status-pass/status-fail/status-warn
// mirror that split for this dashboard's gate-verdict states, so a PASS
// verdict does not render in the same violet as buttons and active nav.
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        warning: "border-transparent bg-warning text-warning-foreground",
        "status-pass": "border-transparent bg-status-pass text-status-pass-foreground",
        "status-fail": "border-transparent bg-status-fail text-status-fail-foreground",
        "status-warn": "border-transparent bg-status-warn text-status-warn-foreground",
        outline: "border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
