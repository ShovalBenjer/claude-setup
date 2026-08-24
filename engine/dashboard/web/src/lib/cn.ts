import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Pattern: shadcn/ui's standard `cn` helper (clsx + tailwind-merge), also
// used verbatim in block/buzz at web/src/shared/lib/cn.ts (checked
// 2026-08-17). This is the de-facto standard utility across the current
// shadcn ecosystem, not a buzz-specific invention.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
