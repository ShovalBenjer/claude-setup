# Tokens, Typography, Color, Spacing, Layout, CSS Standards

## Design System — Tokens

Embed this `<style>` block at the very top of the Wiki page, before any Markdown.

```html
<style>
/* AZURE WIKI DESIGN SYSTEM
   Art direction: Azure cloud-native · professional · clean
   Palette: Azure blue + cool neutral surfaces
   Typography: Segoe UI (body) — Inter fallback — system chain */

:root {
  /* Surfaces */
  --wiki-bg:              #f6f8fa;
  --wiki-surface:         #ffffff;
  --wiki-surface-2:       #f0f3f7;
  --wiki-surface-offset:  #e8ecf2;
  --wiki-divider:         #d0d7e0;
  --wiki-border:          oklch(0.55 0.04 240 / 0.15);

  /* Text */
  --wiki-text:            #1a1f2e;
  --wiki-text-muted:      #5a6478;
  --wiki-text-faint:      #9aa3b2;
  --wiki-text-inverse:    #ffffff;

  /* Primary Accent: Azure Blue */
  --wiki-primary:         #0078d4;
  --wiki-primary-hover:   #005a9e;
  --wiki-primary-active:  #004578;
  --wiki-primary-tint:    #cce4f6;

  /* Semantic */
  --wiki-success:         #107c10;
  --wiki-success-tint:    #dff6dd;
  --wiki-warning:         #c35f0a;
  --wiki-warning-tint:    #fde7d4;
  --wiki-error:           #a4262c;
  --wiki-error-tint:      #fde7e9;
  --wiki-info:            #0078d4;
  --wiki-info-tint:       #cce4f6;

  /* Radius */
  --wiki-radius-sm:       4px;
  --wiki-radius-md:       8px;
  --wiki-radius-lg:       12px;
  --wiki-radius-xl:       16px;
  --wiki-radius-pill:     9999px;

  /* Shadow */
  --wiki-shadow-sm:       0 1px 3px oklch(0.2 0.05 240 / 0.08);
  --wiki-shadow-md:       0 4px 12px oklch(0.2 0.05 240 / 0.10);
  --wiki-shadow-lg:       0 8px 24px oklch(0.2 0.05 240 / 0.14);

  /* Spacing (4px base) */
  --wiki-space-1:  4px;
  --wiki-space-2:  8px;
  --wiki-space-3:  12px;
  --wiki-space-4:  16px;
  --wiki-space-5:  20px;
  --wiki-space-6:  24px;
  --wiki-space-8:  32px;
  --wiki-space-10: 40px;
  --wiki-space-12: 48px;
  --wiki-space-16: 64px;

  /* Type */
  --wiki-font-body: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
  --wiki-font-mono: 'Cascadia Code', 'Consolas', 'SF Mono', monospace;

  --wiki-text-xs:   12px;
  --wiki-text-sm:   13px;
  --wiki-text-base: 15px;
  --wiki-text-lg:   17px;
  --wiki-text-xl:   20px;
  --wiki-text-2xl:  24px;
  --wiki-text-3xl:  30px;

  /* Motion */
  --wiki-transition: 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --wiki-bg:              #0d1117;
    --wiki-surface:         #161b22;
    --wiki-surface-2:       #1c2128;
    --wiki-surface-offset:  #21262d;
    --wiki-divider:         #30363d;
    --wiki-border:          oklch(0.8 0.02 240 / 0.12);
    --wiki-text:            #c9d1d9;
    --wiki-text-muted:      #8b949e;
    --wiki-text-faint:      #484f58;
    --wiki-text-inverse:    #0d1117;
    --wiki-primary:         #58a6ff;
    --wiki-primary-hover:   #79b8ff;
    --wiki-primary-active:  #a5cdff;
    --wiki-primary-tint:    #1f3a5f;
    --wiki-success:         #3fb950;
    --wiki-success-tint:    #1a3a1e;
    --wiki-warning:         #d29922;
    --wiki-warning-tint:    #3a2e0e;
    --wiki-error:           #f85149;
    --wiki-error-tint:      #3a1a1a;
    --wiki-shadow-sm:       0 1px 3px oklch(0 0 0 / 0.3);
    --wiki-shadow-md:       0 4px 12px oklch(0 0 0 / 0.4);
    --wiki-shadow-lg:       0 8px 24px oklch(0 0 0 / 0.5);
  }
}
</style>
```

**Rule:** All colors, radii, and spacing in components must use these tokens. Never hardcode `#0078d4` — always `var(--wiki-primary)`.

## Typography

Body:
```css
font-family: var(--wiki-font-body);
/* 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif */
```

Mono (code blocks, system prompts, JSON):
```css
font-family: var(--wiki-font-mono);
/* 'Cascadia Code', 'Consolas', 'SF Mono', monospace */
```

### Size Scale

| Use case | Token | Value | Weight |
|---|---|---|---|
| Page title (H1) | `--wiki-text-3xl` | 30px | 700 |
| Section heading (H2) | `--wiki-text-2xl` | 24px | 600 |
| Subsection (H3) | `--wiki-text-xl` | 20px | 600 |
| Detail (H4) | `--wiki-text-lg` | 17px | 600 |
| Body | `--wiki-text-base` | 15px | 400 |
| Table cells, labels | `--wiki-text-sm` | 13px | 400 |
| Badges, metadata | `--wiki-text-xs` | 12px | 500 |

### Line Height

- Body `1.65`, headings `1.2`, code `1.5`, table cells `1.4`.

### Reading Width

Wrap prose at **70–75 characters** max:
```css
.wiki-prose p { max-width: 72ch; }
```

Single most impactful readability rule. Long lines cause fatigue.

## Color & Surface Layering

### Three-Layer Surface Model

```
Background  (--wiki-bg)            ← Page body
  └─ Card    (--wiki-surface)      ← Content cards, panels
       └─ Inner (--wiki-surface-2) ← Code blocks, nested tables, callouts
            └─ Offset (--wiki-surface-offset) ← Hover states, selected rows
```

Each level must be visually distinct (3–5% lightness difference minimum). Test in both light and dark mode.

### Color Usage

| Role | Token | Usage |
|---|---|---|
| Links, primary CTAs | `--wiki-primary` | Buttons, hyperlinks, active nav |
| Hover | `--wiki-primary-hover` | On hover of primary elements |
| Success | `--wiki-success` | pass badges, "online" indicators |
| Warning | `--wiki-warning` | deprecation, caution callouts |
| Error | `--wiki-error` | failure, critical alerts |
| Info | `--wiki-info` | informational callouts |
| Tinted backgrounds | `*-tint` variants | Callout bg, tag fills |

**Restraint Rule:** Max **2 non-neutral accent colors** simultaneously per viewport. Charts may use more; UI chrome stays monochromatic.

### Callout Semantics

```
Info     → border: --wiki-primary,  bg: --wiki-info-tint
Success  → border: --wiki-success,  bg: --wiki-success-tint
Warning  → border: --wiki-warning,  bg: --wiki-warning-tint
Error    → border: --wiki-error,    bg: --wiki-error-tint
Security → border: --wiki-warning,  bg: --wiki-warning-tint
```

## Spacing System

All spacing derives from a **4px base unit**. Never arbitrary values.

```
4px   (--wiki-space-1)  → icon gaps, inline padding
8px   (--wiki-space-2)  → badge/chip padding, tight row gaps
12px  (--wiki-space-3)  → input field padding, compact list items
16px  (--wiki-space-4)  → card padding (min), standard gap
20px  (--wiki-space-5)  → comfortable row spacing
24px  (--wiki-space-6)  → section sub-heading gap, card inner gap
32px  (--wiki-space-8)  → card-to-card gap, section content gap
40px  (--wiki-space-10) → section top margin
48px  (--wiki-space-12) → major section break
64px  (--wiki-space-16) → page-level section separation
```

Application:
- Card padding: `--wiki-space-6` desktop, `--wiki-space-4` mobile.
- Grid gap: `--wiki-space-4` to `--wiki-space-6`.
- Section-to-section: `--wiki-space-12`.
- Inline icon + label: `--wiki-space-2`.

## Layout Patterns

### Reading Lane

Content centered at max 1000px:

```html
<div style="max-width:1000px; margin:0 auto; padding:0 16px; font-family:var(--wiki-font-body);">
  <!-- all page content -->
</div>
```

### KPI Grid (4-column auto-fill)

```css
display: grid;
grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
gap: var(--wiki-space-4);
```

### Two-Column (text + code)

```css
display: grid;
grid-template-columns: 1fr 1fr;
gap: var(--wiki-space-6);
align-items: start;
@media (max-width: 640px) { grid-template-columns: 1fr; }
```

### Mobile-Safe Table Wrapper

```css
overflow-x: auto;
-webkit-overflow-scrolling: touch;
```

### Reading Rhythm

Vary visual weight per section to prevent monotony:

| Section | Treatment |
|---|---|
| Overview | Light card, KPI metrics |
| Diagram / Flow | Full-width bordered panel, white bg |
| System Prompt | Dark code block, monospace, copy button |
| Q&A | Accordion list, indented answers |
| Architecture | Striped table, status pills |
| Changelog | Compact timeline-style table |

## CSS Styling Standards

### Rule 1: Inline or `<style>` only

Azure Wiki does not support external stylesheets. Use either:
1. Inline `style="..."` on elements (preferred for components).
2. A `<style>` block at the top of the `.md` (required for tokens + global rules).

### Rule 2: Tokens everywhere

```html
<!-- WRONG -->
<div style="background:#ffffff; border:1px solid #ddd;">

<!-- RIGHT -->
<div style="background:var(--wiki-surface); border:1px solid var(--wiki-border);">
```

### Rule 3: Never `!important`

If you need it, your specificity is broken. Fix the selector.

### Rule 4: Transition interactive elements

```html
<button style="transition: background var(--wiki-transition), transform var(--wiki-transition);">
```

Apply to: `background`, `color`, `border-color`, `box-shadow`, `transform`.
Never to: `width`, `height`, `display`, `position`.

### Rule 5: Radius hierarchy

| Element | Radius |
|---|---|
| Badges, pills, tags | `--wiki-radius-pill` |
| Buttons, inputs | `--wiki-radius-md` |
| Cards, panels | `--wiki-radius-lg` |
| Full-width banners | `--wiki-radius-lg` |
| Table cells | `0` |
| Code blocks | `--wiki-radius-lg` on wrapper |

### Rule 6: Shadow for elevation only

- `--wiki-shadow-sm` — cards at rest.
- `--wiki-shadow-md` — cards on hover, floating panels.
- `--wiki-shadow-lg` — modals, popovers.
- No shadows on flat, non-elevated elements (rows, badges, list items).
