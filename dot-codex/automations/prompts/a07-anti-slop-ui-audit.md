# A7. Anti-Slop UI Audit

Schedule: Wednesdays 6:00 PM
Repo root: active frontend code under `/home/shovalbe/projects/` ONLY (skip anything under `.archive/`):
- `seekapa-training-platform/frontend` (React + Vite + Tailwind) — PRIMARY: known dark-on-dark issues
- `campaign-analysis/funnel-ui` (Next.js)
- `ORM-AGENT/**` and `video-understanding/**` web surfaces if present
(Do NOT scan `figma-4-all` or `social-intelligence-unit` — both archived 2026-06-10.)
Mode: read + propose

Walk every `.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, and `.html` file in the configured roots. Per file, scan for:

1. AI-slop palette: `bg-white`, `#fff`, `#ffffff`, `from-purple-*`, `to-purple-*`, and `gradient-to-r` where the target is purple or blue.
2. Inter-only font declarations.
3. `text-gray-500` low-contrast usage.
4. Emoji in JSX/HTML, per `no-emojis.md`.
5. More than 3 distinct `rounded-*` values in one component.
6. `!important` in non-reset CSS.
7. `z-index` greater than 9999.
8. DARK-ON-DARK / WCAG-fail contrast (PRIORITY — the human-obvious "lazy AI" tell): any text whose
   foreground colour sits on a same-tone background so the WCAG contrast ratio is < 4.5:1 (normal
   text) or < 3:1 (large/bold). Resolve Tailwind tokens to hex (e.g. `text-zinc-700`/`text-slate-800`
   on `bg-zinc-900`/`bg-black`/a dark gradient, `text-white` on `bg-gray-100`, dark text on a dark
   `dark:` variant). Compute the ratio; report fg token, bg token, ratio, and the element. Also flag
   hardcoded near-equal fg/bg hex pairs and `opacity` on text that drops effective contrast below 4.5.
9. Invisible/placeholder states: unstyled `:focus`/`:disabled`, `color: transparent` text, or a
   `loading`/empty state with no visible affordance.

Output `~/.claude/docs/ANTI_SLOP_AUDIT_<DATE>.md` as a per-project table with:

- File path, line, violation.
- A 1-line fix suggestion using Catppuccin Mocha tokens.

If any file has more than 5 violations, file an ADO work item via:

```bash
~/.claude/bin/work-item.sh create --type Bug --title "Anti-slop violations: <file>" --tags "ui-debt"
```
