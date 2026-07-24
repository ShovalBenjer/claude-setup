---
name: azure-wiki-onepager
version: 1.0
description: >
  Standard guidelines skill for building best-looking, production-grade, one-page
  Azure DevOps Wiki pages. Covers content architecture, design system, CSS styling,
  UI/UX patterns, interactive features, and Google-grade design standards.
  Use-case anchored to AI-powered customer support agent projects.
tags: [azure, wiki, design, css, ui, customer-support, ai-agent]
---

# Azure Wiki One-Pager — Design & Content Skill

> **Skill Purpose:** This document is a reusable, opinionated set of guidelines — a "skill" — for
> producing the best-looking, most informative, and most navigable one-page Azure DevOps Wiki
> articles. It blends Google-grade design thinking with Azure's native Markdown/HTML rendering
> capabilities. Every rule here is prescriptive and actionable. Read it before authoring or
> reviewing any Wiki page.

---

## Table of Contents

1. [Skill Activation Criteria](#1-skill-activation-criteria)
2. [Mental Model — What a Great Wiki Page Is](#2-mental-model--what-a-great-wiki-page-is)
3. [Content Architecture](#3-content-architecture)
4. [Design System — Tokens & Variables](#4-design-system--tokens--variables)
5. [Typography](#5-typography)
6. [Color & Surface Layering](#6-color--surface-layering)
7. [Spacing System](#7-spacing-system)
8. [Layout Patterns](#8-layout-patterns)
9. [Component Library](#9-component-library)
10. [CSS Styling Standards](#10-css-styling-standards)
11. [UI/UX Interaction Patterns](#11-uiux-interaction-patterns)
12. [Customer Support Agent — Content Template](#12-customer-support-agent--content-template)
13. [System Prompt — Authoring Standard](#13-system-prompt--authoring-standard)
14. [Q&A Section — Structure & Format](#14-qa-section--structure--format)
15. [UI Design Flow — Diagram Standard](#15-ui-design-flow--diagram-standard)
16. [Accessibility & Performance Checklist](#16-accessibility--performance-checklist)
17. [Anti-Patterns — Never Do These](#17-anti-patterns--never-do-these)
18. [Quality Gate Checklist](#18-quality-gate-checklist)

---

## 1. Skill Activation Criteria

**Activate this skill when:**

- You are authoring or reviewing an Azure DevOps Wiki page.
- The output is a single, long-form `.md` or embedded-HTML wiki document.
- The content involves an AI agent, customer support system, LLM pipeline, or technical product.
- The goal is a visually polished, navigable, information-dense page — not a raw spec dump.

**Do NOT activate this skill for:**
- Multi-page wikis with separate navigation (use a separate `azure-wiki-multipage` skill).
- Pure Markdown-only wikis with no embedded HTML/CSS (use the basic `azure-wiki-markdown` skill).
- README files or repo documentation (use the `readme` skill).

---

## 2. Mental Model — What a Great Wiki Page Is

A great Azure Wiki one-pager has **three jobs**, in priority order:

1. **Orientate** — The reader knows within 5 seconds what this page covers and why it matters.
2. **Inform** — Every section answers a real question a stakeholder, developer, or support operator would actually ask.
3. **Delight** — The visual design respects the reader's time and intelligence. It does not look like a Confluence dump or a Word document pasted into Markdown.

### The Google-Grade Standard

Google-grade design means:
- **Information density without clutter.** Every pixel earns its place.
- **Hierarchy that guides the eye.** The reader never has to work to find structure.
- **Restraint.** One accent color. Two font weights. No gradients on interactive elements.
- **Consistency.** Every card, table, and callout follows the same visual grammar.
- **Motion only where it adds meaning.** A subtle expand on accordion items. Nothing more.

### Azure Wiki Constraints (Know Before You Build)

Azure DevOps Wiki renders a **subset of GitHub-Flavored Markdown (GFM)** plus allows
**raw HTML blocks** embedded in `.md` files. This means:

| Feature | Supported | Notes |
|---|---|---|
| Headings `# H1` – `###### H6` | ✅ | Use heading hierarchy strictly |
| Tables | ✅ | GFM pipe syntax |
| Fenced code blocks | ✅ | Syntax highlighting via Prism-like renderer |
| Raw `<style>` blocks | ✅ | Scoped to the page; loaded inline |
| Raw `<script>` blocks | ⚠️ | Limited; no `localStorage`, no `fetch()` to external URLs |
| `<details>` / `<summary>` | ✅ | Native accordion without JS |
| Mermaid diagrams | ✅ | Use `::: mermaid` fenced block |
| MathJax | ✅ | Use `$inline$` or `$$block$$` |
| iframes | ❌ | Blocked by Azure security policy |
| External fonts via `@import` | ⚠️ | Works in some tenants; test before relying on it |
| CSS custom properties (variables) | ✅ | Fully supported in modern browsers |
| `prefers-color-scheme` media query | ✅ | Use for automatic dark mode |

---

## 3. Content Architecture

### The One-Pager Spine

Every one-pager follows this spine. Sections marked **[REQUIRED]** must always be present.
Optional sections are included based on project type.

```
┌─────────────────────────────────────────────────────┐
│  HEADER BAND                          [REQUIRED]     │
│  Title · Badge row · Last-updated · Owner            │
├─────────────────────────────────────────────────────┤
│  OVERVIEW                             [REQUIRED]     │
│  1-paragraph purpose + KPI metric cards              │
├─────────────────────────────────────────────────────┤
│  UI DESIGN FLOW                       [REQUIRED]     │
│  End-to-end interaction diagram                      │
├─────────────────────────────────────────────────────┤
│  SYSTEM PROMPT                        [REQUIRED]     │
│  Full prompt in a styled code block                  │
├─────────────────────────────────────────────────────┤
│  AGENT BEHAVIOR / DECISION PIPELINE   [RECOMMENDED]  │
│  Step-by-step numbered flow                          │
├─────────────────────────────────────────────────────┤
│  Q&A REFERENCE                        [REQUIRED]     │
│  Categorized accordion Q&A pairs                     │
├─────────────────────────────────────────────────────┤
│  ARCHITECTURE                         [RECOMMENDED]  │
│  Component table with SLA / owners                   │
├─────────────────────────────────────────────────────┤
│  KPI DASHBOARD                        [OPTIONAL]     │
│  Live metrics cards                                  │
├─────────────────────────────────────────────────────┤
│  CHANGELOG                            [RECOMMENDED]  │
│  Version history table                               │
└─────────────────────────────────────────────────────┘
```

### Section Ordering Rules

- **Always lead with Overview.** Context before detail. Never open with architecture or code.
- **UI Design Flow before System Prompt.** Readers need the "what" before the "how".
- **Q&A near the bottom.** It's reference material, not narrative. Readers scroll to it, not through it.
- **Changelog always last.** It's an audit trail, not content.

### Heading Hierarchy

```markdown
# Page Title                          ← One per page, H1
## Section Name                       ← Major sections
### Subsection Name                   ← Within a section
#### Detail Heading                   ← Use sparingly
```

**Never skip levels.** An `####` must always live inside a `###`, which lives inside a `##`.

---

## 4. Design System — Tokens & Variables

Embed a `<style>` block at the very top of the Wiki page (before any Markdown content).
This block defines all design tokens as CSS custom properties.

```html
<style>
/* ============================================================
   AZURE WIKI DESIGN SYSTEM — Customer Support Agent
   Art direction: Azure cloud-native · professional · clean
   Palette: Azure blue + cool neutral surfaces
   Typography: Inter (body) — system fallback chain
   Density: balanced
   ============================================================ */

:root {
  /* --- Surfaces --- */
  --wiki-bg:              #f6f8fa;
  --wiki-surface:         #ffffff;
  --wiki-surface-2:       #f0f3f7;
  --wiki-surface-offset:  #e8ecf2;
  --wiki-divider:         #d0d7e0;
  --wiki-border:          oklch(0.55 0.04 240 / 0.15);

  /* --- Text --- */
  --wiki-text:            #1a1f2e;
  --wiki-text-muted:      #5a6478;
  --wiki-text-faint:      #9aa3b2;
  --wiki-text-inverse:    #ffffff;

  /* --- Primary Accent: Azure Blue --- */
  --wiki-primary:         #0078d4;
  --wiki-primary-hover:   #005a9e;
  --wiki-primary-active:  #004578;
  --wiki-primary-tint:    #cce4f6;

  /* --- Semantic Colors --- */
  --wiki-success:         #107c10;
  --wiki-success-tint:    #dff6dd;
  --wiki-warning:         #c35f0a;
  --wiki-warning-tint:    #fde7d4;
  --wiki-error:           #a4262c;
  --wiki-error-tint:      #fde7e9;
  --wiki-info:            #0078d4;
  --wiki-info-tint:       #cce4f6;

  /* --- Radius --- */
  --wiki-radius-sm:       4px;
  --wiki-radius-md:       8px;
  --wiki-radius-lg:       12px;
  --wiki-radius-xl:       16px;
  --wiki-radius-pill:     9999px;

  /* --- Shadows --- */
  --wiki-shadow-sm:       0 1px 3px oklch(0.2 0.05 240 / 0.08);
  --wiki-shadow-md:       0 4px 12px oklch(0.2 0.05 240 / 0.10);
  --wiki-shadow-lg:       0 8px 24px oklch(0.2 0.05 240 / 0.14);

  /* --- Spacing (4px base) --- */
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

  /* --- Typography --- */
  --wiki-font-body:    'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
  --wiki-font-mono:    'Cascadia Code', 'Consolas', 'SF Mono', monospace;

  --wiki-text-xs:   12px;
  --wiki-text-sm:   13px;
  --wiki-text-base: 15px;
  --wiki-text-lg:   17px;
  --wiki-text-xl:   20px;
  --wiki-text-2xl:  24px;
  --wiki-text-3xl:  30px;

  /* --- Transitions --- */
  --wiki-transition: 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* Dark mode — automatic via prefers-color-scheme */
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

> **Rule:** All colors, radii, and spacing values in component HTML must reference these tokens.
> **Never** hardcode `#0078d4` directly in a component — always use `var(--wiki-primary)`.

---

## 5. Typography

### Font Stack

Azure Wiki renders in the user's browser. Rely on the system font stack supplemented by
**Segoe UI** (Windows/Azure-native) with **Inter** as a web-safe fallback.

```css
font-family: var(--wiki-font-body);
/* resolves to: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif */
```

For monospace (code blocks, system prompts, JSON):
```css
font-family: var(--wiki-font-mono);
/* resolves to: 'Cascadia Code', 'Consolas', 'SF Mono', monospace */
```

### Size Scale Usage

| Use case | Size token | Value | Weight |
|---|---|---|---|
| Page title (H1) | `--wiki-text-3xl` | 30px | 700 |
| Section heading (H2) | `--wiki-text-2xl` | 24px | 600 |
| Subsection heading (H3) | `--wiki-text-xl` | 20px | 600 |
| Detail heading (H4) | `--wiki-text-lg` | 17px | 600 |
| Body text | `--wiki-text-base` | 15px | 400 |
| Table cells, labels | `--wiki-text-sm` | 13px | 400 |
| Badges, metadata, tiny labels | `--wiki-text-xs` | 12px | 500 |

### Line Height Rules

- Body text: `1.65` — comfortable for documentation reading.
- Headings: `1.2` — tight, authoritative.
- Code blocks: `1.5` — readable without feeling like a wall of text.
- Table cells: `1.4` — dense but scannable.

### Reading Width

Wrap prose paragraphs at **70–75 characters** max:
```css
.wiki-prose p { max-width: 72ch; }
```

This is the single most impactful readability rule. Long lines cause reader fatigue.

---

## 6. Color & Surface Layering

### The Three-Layer Surface Model

Every wiki page uses a three-level surface stack to create depth without shadows:

```
Background  (--wiki-bg)           ← Page body
  └─ Card    (--wiki-surface)     ← Content cards, panels
       └─ Inner (--wiki-surface-2) ← Code blocks, nested tables, callouts
            └─ Offset (--wiki-surface-offset) ← Hover states, selected rows
```

**Visual rule:** Each level must be visually distinct. If two adjacent surfaces look identical,
add 3–5% lightness difference. Test in both light and dark mode.

### Color Usage Rules

| Role | Token | Usage |
|---|---|---|
| Links, primary CTAs | `--wiki-primary` | Buttons, hyperlinks, active nav |
| Hover states | `--wiki-primary-hover` | On hover of primary elements |
| Success states | `--wiki-success` | ✅ badges, "online" indicators |
| Warning states | `--wiki-warning` | ⚠️ deprecation notices, caution callouts |
| Error / critical | `--wiki-error` | ❌ failure states, critical alerts |
| Info / neutral | `--wiki-info` | ℹ️ informational callouts |
| Tinted backgrounds | `*-tint` variants | Callout backgrounds, tag fills |

**Restraint Rule:** In any single viewport, no more than **2 non-neutral accent colors** should
appear simultaneously. Charts and status indicators may use more colors, but UI chrome must stay
monochromatic.

### Callout Color Semantics

```
ℹ️  Info callout    → border: --wiki-primary,    bg: --wiki-info-tint
✅  Success callout → border: --wiki-success,    bg: --wiki-success-tint
⚠️  Warning callout → border: --wiki-warning,    bg: --wiki-warning-tint
❌  Error callout   → border: --wiki-error,      bg: --wiki-error-tint
🔒  Security note   → border: --wiki-warning,    bg: --wiki-warning-tint
```

---

## 7. Spacing System

All spacing is derived from a **4px base unit**. Never use arbitrary pixel values.

```
4px   (--wiki-space-1)  → icon gaps, inline padding
8px   (--wiki-space-2)  → badge/chip padding, tight row gaps
12px  (--wiki-space-3)  → input field padding, compact list items
16px  (--wiki-space-4)  → card padding (minimum), standard gap
20px  (--wiki-space-5)  → comfortable row spacing
24px  (--wiki-space-6)  → section sub-heading gap, card inner gap
32px  (--wiki-space-8)  → card-to-card gap, section content gap
40px  (--wiki-space-10) → section top margin
48px  (--wiki-space-12) → major section break
64px  (--wiki-space-16) → page-level section separation
```

**Application:**
- Card padding: `var(--wiki-space-6)` (24px) on desktop, `var(--wiki-space-4)` (16px) on mobile.
- Gap between cards in a grid: `var(--wiki-space-4)` to `var(--wiki-space-6)`.
- Section-to-section spacing: `var(--wiki-space-12)` (48px).
- Inline element gaps (icon + label): `var(--wiki-space-2)` (8px).

---

## 8. Layout Patterns

### The Wiki Page Layout

A best-in-class Azure Wiki one-pager uses a **reading-lane layout**:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Wiki-rendered navigation rail — Azure-native, not ours]       │
├─────────────────────────────────────────────────────────────────┤
│  HEADER BAND (full-width strip)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  CONTENT LANE  (max-width: 1000px, centered)         │        │
│  │                                                      │        │
│  │  Section 1: Overview                                 │        │
│  │  Section 2: UI Flow                                  │        │
│  │  Section 3: System Prompt                            │        │
│  │  ...                                                 │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

Apply the content lane:
```html
<div style="max-width:1000px; margin:0 auto; padding:0 16px; font-family:var(--wiki-font-body);">
  <!-- all page content -->
</div>
```

### Grid Patterns

**KPI Metric Cards — 4-column auto-fill:**
```css
display: grid;
grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
gap: var(--wiki-space-4);
```

**Two-column layout (text + code):**
```css
display: grid;
grid-template-columns: 1fr 1fr;
gap: var(--wiki-space-6);
align-items: start;
```
Always collapse to single column on screens narrower than 640px:
```css
@media (max-width: 640px) { grid-template-columns: 1fr; }
```

**Architecture component table — full width, horizontal scroll on mobile:**
```css
overflow-x: auto;
-webkit-overflow-scrolling: touch;
```

### Reading Rhythm

Vary visual weight between sections to prevent monotony:

| Section Type | Visual Treatment |
|---|---|
| Overview | Light card, KPI metrics, subtle surface |
| Diagram / Flow | Full-width bordered panel, white bg |
| System Prompt | Dark code block, monospace, copy button |
| Q&A | Accordion list, left-indented answers |
| Architecture Table | Striped table, status badges |
| Changelog | Compact timeline-style table |

---

## 9. Component Library

Each component below is written as a self-contained HTML snippet using the design tokens
from Section 4. Copy and adapt directly into your Wiki `.md` file.

---

### 9.1 Header Band

```html
<div style="
  background: linear-gradient(135deg, var(--wiki-primary) 0%, #005a9e 100%);
  border-radius: var(--wiki-radius-lg);
  padding: var(--wiki-space-8) var(--wiki-space-10);
  margin-bottom: var(--wiki-space-8);
  color: var(--wiki-text-inverse);
">
  <div style="display:flex; align-items:center; gap:var(--wiki-space-3); margin-bottom:var(--wiki-space-4);">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
    <h1 style="font-size:var(--wiki-text-3xl); font-weight:700; margin:0; line-height:1.2;">
      Customer Support Agent
    </h1>
  </div>
  <p style="font-size:var(--wiki-text-base); opacity:0.9; max-width:65ch; margin:0 0 var(--wiki-space-4) 0; line-height:1.6;">
    Azure OpenAI–powered agent handling tier-1 support tickets, live chat deflection,
    and automated escalation routing for the product support team.
  </p>
  <div style="display:flex; flex-wrap:wrap; gap:var(--wiki-space-2);">
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">v2.4</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Azure OpenAI GPT-4o</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Production</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Updated: Apr 2026</span>
  </div>
</div>
```

**Rules:**
- Use a solid-to-darker-blue gradient, never rainbow or neon.
- Badges must be white/translucent — never colored on a colored background.
- Title must include a context-appropriate icon (Lucide SVG inline).
- Always include: version badge, model badge, environment badge, last-updated badge.

---

### 9.2 KPI Metric Card

```html
<div style="
  background: var(--wiki-surface);
  border: 1px solid var(--wiki-border);
  border-radius: var(--wiki-radius-lg);
  padding: var(--wiki-space-5) var(--wiki-space-6);
  box-shadow: var(--wiki-shadow-sm);
  display: flex;
  flex-direction: column;
  gap: var(--wiki-space-2);
">
  <span style="font-size:var(--wiki-text-xs); font-weight:500; text-transform:uppercase;
    letter-spacing:0.06em; color:var(--wiki-text-muted);">
    Deflection Rate
  </span>
  <span style="font-size:var(--wiki-text-3xl); font-weight:700; color:var(--wiki-text);
    letter-spacing:-0.02em; line-height:1;">
    74%
  </span>
  <span style="font-size:var(--wiki-text-sm); color:var(--wiki-success);">
    ↑ +3.2% vs last month
  </span>
</div>
```

**Rules:**
- Exactly 3 lines: label (uppercase, muted), value (large, bold), delta (colored).
- Delta: green (`--wiki-success`) for improvement, red (`--wiki-error`) for regression, muted for neutral.
- Never more than 4 KPI cards in a single row — use `auto-fill minmax(200px, 1fr)`.
- Values must use `tabular-nums` font feature for alignment in grids.

---

### 9.3 Callout / Alert Block

```html
<!-- Info callout -->
<div style="
  border-left: 3px solid var(--wiki-primary);
  background: var(--wiki-info-tint);
  border-radius: 0 var(--wiki-radius-md) var(--wiki-radius-md) 0;
  padding: var(--wiki-space-4) var(--wiki-space-5);
  margin: var(--wiki-space-6) 0;
  display: flex;
  gap: var(--wiki-space-3);
  align-items: flex-start;
">
  <span style="font-size:16px; flex-shrink:0; margin-top:2px;">ℹ️</span>
  <div>
    <strong style="font-size:var(--wiki-text-sm); color:var(--wiki-primary);">Note</strong>
    <p style="margin:4px 0 0; font-size:var(--wiki-text-sm); color:var(--wiki-text); line-height:1.6;">
      Replace this text with the callout content. Keep callouts to 1–3 sentences max.
    </p>
  </div>
</div>
```

**Variants:** Swap `border-color` and `background` per Section 6 callout semantics.
**Rule:** Never use a colored left-border on a card. Callouts only.

---

### 9.4 Accordion Q&A Item

Use native HTML `<details>` — no JavaScript required, works in all browsers including Azure Wiki.

```html
<details style="
  border: 1px solid var(--wiki-border);
  border-radius: var(--wiki-radius-md);
  margin-bottom: var(--wiki-space-2);
  background: var(--wiki-surface);
  overflow: hidden;
">
  <summary style="
    padding: var(--wiki-space-4) var(--wiki-space-5);
    font-size: var(--wiki-text-base);
    font-weight: 500;
    cursor: pointer;
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--wiki-space-3);
    color: var(--wiki-text);
    user-select: none;
  ">
    <span>How does the agent handle escalations?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-primary-tint);
      color:var(--wiki-primary); padding:2px 8px; border-radius:var(--wiki-radius-pill);
      white-space:nowrap;">Routing</span>
  </summary>
  <div style="
    padding: var(--wiki-space-4) var(--wiki-space-5) var(--wiki-space-5);
    border-top: 1px solid var(--wiki-border);
    background: var(--wiki-surface-2);
    font-size: var(--wiki-text-base);
    line-height: 1.65;
    color: var(--wiki-text-muted);
  ">
    <p>When the agent's confidence score drops below 0.72, or the user explicitly
    requests a human, the conversation is transferred to the live-agent queue in
    Dynamics 365. The full conversation transcript is passed along with a 3-sentence
    summary generated by the model.</p>
  </div>
</details>
```

**Rules:**
- Category badge (top-right of summary) is mandatory — it enables visual scanning.
- Answer lives in `--wiki-surface-2` to visually separate it from the question.
- Never nest accordions. Flat list only.
- Group related Q&As under a `### Category Heading` before the accordion list.

---

### 9.5 System Prompt Code Block

```html
<div style="
  background: #0d1117;
  border-radius: var(--wiki-radius-lg);
  overflow: hidden;
  margin: var(--wiki-space-6) 0;
  box-shadow: var(--wiki-shadow-md);
">
  <!-- Toolbar -->
  <div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--wiki-space-3) var(--wiki-space-5);
    background: #161b22;
    border-bottom: 1px solid #30363d;
  ">
    <div style="display:flex; align-items:center; gap:var(--wiki-space-2);">
      <span style="width:12px;height:12px;border-radius:50%;background:#ff5f56;display:inline-block;"></span>
      <span style="width:12px;height:12px;border-radius:50%;background:#ffbd2e;display:inline-block;"></span>
      <span style="width:12px;height:12px;border-radius:50%;background:#27c93f;display:inline-block;"></span>
      <span style="font-size:var(--wiki-text-xs); color:#8b949e; margin-left:8px; font-family:var(--wiki-font-mono);">
        SYSTEM_PROMPT.txt
      </span>
    </div>
    <button onclick="
      const el = this.parentElement.nextElementSibling;
      navigator.clipboard.writeText(el.innerText);
      this.textContent = '✓ Copied';
      setTimeout(()=>this.textContent='Copy',2000);
    " style="
      font-size:var(--wiki-text-xs); color:#8b949e; background:#21262d;
      border:1px solid #30363d; border-radius:4px; padding:4px 10px; cursor:pointer;
    ">Copy</button>
  </div>
  <!-- Prompt Content -->
  <pre style="
    margin:0; padding:var(--wiki-space-6); overflow-x:auto;
    font-family:var(--wiki-font-mono); font-size:13px; line-height:1.65;
    color:#c9d1d9; background:#0d1117; white-space:pre-wrap; word-break:break-word;
  "><code>You are a customer support agent for [Company Name]. Your role is to help
customers resolve issues with their accounts, orders, and products.

## Identity
- Name: Aria
- Tone: Professional, empathetic, solution-focused
- Language: Match the user's language automatically

## Capabilities
- Answer questions about account management, billing, and orders
- Look up order status via the `get_order_status` tool
- Create support tickets via the `create_ticket` tool
- Escalate to a human agent when confidence &lt; 0.72

## Constraints
- Never disclose internal pricing agreements
- Never make commitments outside standard policy
- Always confirm PII before sharing account data

## Escalation Triggers
- User requests human agent
- Confidence score &lt; 0.72
- Legal, compliance, or safety-related queries
- 3+ failed resolution attempts</code></pre>
</div>
```

**Rules:**
- Always use the dark terminal theme (`#0d1117` background) for system prompts and config.
- Always include a copy button. Copy should write `el.innerText` to clipboard.
- Traffic-light dots (red/yellow/green) are the accepted terminal decoration — nothing else.
- Escape HTML entities in prompt content: `<` → `&lt;`, `>` → `&gt;`.

---

### 9.6 Architecture Component Table

```html
<div style="overflow-x:auto; margin:var(--wiki-space-6) 0;">
  <table style="
    width:100%; border-collapse:collapse;
    font-size:var(--wiki-text-sm); font-family:var(--wiki-font-body);
  ">
    <thead>
      <tr style="background:var(--wiki-surface-2); border-bottom:2px solid var(--wiki-divider);">
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left;
          font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs);
          text-transform:uppercase; letter-spacing:0.05em;">Component</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left;
          font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs);
          text-transform:uppercase; letter-spacing:0.05em;">Azure Service</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left;
          font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs);
          text-transform:uppercase; letter-spacing:0.05em;">SLA</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left;
          font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs);
          text-transform:uppercase; letter-spacing:0.05em;">Status</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid var(--wiki-border);">
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:500; color:var(--wiki-text);">LLM Inference</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">Azure OpenAI GPT-4o</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted); font-family:var(--wiki-font-mono);">99.9%</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4);">
          <span style="background:var(--wiki-success-tint); color:var(--wiki-success);
            border-radius:var(--wiki-radius-pill); padding:2px 8px; font-size:var(--wiki-text-xs); font-weight:500;">
            ● Operational
          </span>
        </td>
      </tr>
      <!-- Repeat rows; alternate with background: var(--wiki-surface-2) for even rows -->
    </tbody>
  </table>
</div>
```

**Rules:**
- Table headers: uppercase, letter-spaced, muted color.
- Status badges: pill shape, semantic color, dot prefix (●).
- Alternating row backgrounds: even rows get `var(--wiki-surface-2)`.
- Always wrap in `overflow-x:auto` container for mobile.
- Numeric columns: `font-family: var(--wiki-font-mono)`, `text-align: right`.

---

### 9.7 Step / Decision Pipeline

```html
<div style="margin:var(--wiki-space-6) 0;">
  <!-- Step item -->
  <div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-5);">
    <div style="
      width:32px; height:32px; border-radius:50%;
      background:var(--wiki-primary); color:var(--wiki-text-inverse);
      display:flex; align-items:center; justify-content:center;
      font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;
    ">1</div>
    <div>
      <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">
        Intent Classification
      </strong>
      <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">
        The model classifies the user message into one of 14 intent categories using
        a zero-shot classification prompt. Confidence threshold: 0.65.
      </p>
    </div>
  </div>
  <!-- Connector line between steps -->
  <div style="width:2px; height:24px; background:var(--wiki-divider); margin-left:15px; margin-bottom:var(--wiki-space-1);"></div>
  <!-- Next step ... -->
</div>
```

**Rules:**
- Numbered circles: `--wiki-primary` background, white text.
- Connector line: `2px` wide, `--wiki-divider` color, centered under the circle.
- Step title: `font-weight:500`, body text size.
- Step description: muted color, smaller size.

---

### 9.8 Changelog Table

```html
| Version | Date | Author | Change |
|---|---|---|---|
| v2.4 | Apr 2026 | @eng-team | Added sentiment-aware escalation routing |
| v2.3 | Mar 2026 | @ai-team | Upgraded to GPT-4o from GPT-4-turbo |
| v2.2 | Feb 2026 | @eng-team | Added Redis caching layer; P50 latency −40% |
| v2.1 | Jan 2026 | @pm-team | Extended Q&A bank from 45 to 120 entries |
| v2.0 | Dec 2025 | @eng-team | Initial production deployment |
```

**Rules:**
- Always in reverse chronological order (newest first).
- Author column: use `@handle` format, not full names.
- Change description: active voice, past tense, under 12 words.

---

## 10. CSS Styling Standards

### Rule 1: All styles inline or in `<style>` block

Azure Wiki does not support external stylesheets. All CSS must be either:
1. **Inline `style="..."` attributes** on individual HTML elements (preferred for components).
2. **A `<style>` block** at the top of the `.md` file (required for token definitions and global rules).

### Rule 2: Use tokens everywhere

```html
<!-- ❌ WRONG — hardcoded color -->
<div style="background:#ffffff; border:1px solid #ddd;">

<!-- ✅ RIGHT — token references -->
<div style="background:var(--wiki-surface); border:1px solid var(--wiki-border);">
```

### Rule 3: Never use !important

`!important` is a code smell. If you need it, your specificity is broken. Fix the selector.

### Rule 4: Transition all interactive elements

```html
<button style="transition: background var(--wiki-transition), transform var(--wiki-transition);">
```

Apply transitions to: `background`, `color`, `border-color`, `box-shadow`, `transform`.
Never apply transitions to: `width`, `height`, `display`, `position`.

### Rule 5: Border radius consistency

| Element type | Radius |
|---|---|
| Badges, pills, tags | `--wiki-radius-pill` (9999px) |
| Buttons, inputs | `--wiki-radius-md` (8px) |
| Cards, panels | `--wiki-radius-lg` (12px) |
| Full-width banners | `--wiki-radius-lg` (12px) |
| Table cells | `0` — no radius on cells |
| Code blocks | `--wiki-radius-lg` (12px) on wrapper |

### Rule 6: Box shadow for elevation only

- `--wiki-shadow-sm`: cards at rest.
- `--wiki-shadow-md`: cards on hover, floating panels.
- `--wiki-shadow-lg`: modals, popovers.
- No shadows on flat, non-elevated elements (table rows, list items, badges).

---

## 11. UI/UX Interaction Patterns

### Accordions (Q&A)

Use native `<details>`/`<summary>`. No JavaScript. No third-party libraries.

Keyboard behavior (browser-native):
- `Space` / `Enter` → toggles open/closed.
- `Tab` → moves focus to next `<summary>`.

### Copy Buttons

Every code block (system prompt, API examples, JSON config) gets a copy button:

```javascript
// Inline onclick — safe for Azure Wiki's limited JS scope
onclick="
  const code = this.closest('.code-block').querySelector('pre').innerText;
  navigator.clipboard.writeText(code);
  this.textContent = '✓ Copied';
  setTimeout(() => this.textContent = 'Copy', 2000);
"
```

### Tabs (If Needed)

Use radio-button CSS tabs — no JavaScript required:

```html
<style>
  .wiki-tabs input[type=radio] { display:none; }
  .wiki-tabs label { cursor:pointer; padding:8px 16px; border-bottom:2px solid transparent; }
  .wiki-tabs input:checked + label { border-bottom-color: var(--wiki-primary); color:var(--wiki-primary); font-weight:500; }
  .wiki-tab-content { display:none; }
  #tab1:checked ~ .wiki-tab-content:nth-of-type(1) { display:block; }
  #tab2:checked ~ .wiki-tab-content:nth-of-type(2) { display:block; }
</style>
```

### Hover States

Every interactive element (button, accordion summary, table row) needs a hover state:
```css
summary:hover { background: var(--wiki-surface-offset); }
tr:hover td   { background: var(--wiki-surface-2); }
button:hover  { background: var(--wiki-primary-hover); }
```

### Reading Progress (Optional)

```html
<div id="wiki-progress" style="
  position:fixed; top:0; left:0; height:3px;
  background:var(--wiki-primary); width:0%; z-index:9999;
  transition:width 0.1s linear;
"></div>
<script>
  window.addEventListener('scroll', () => {
    const el = document.getElementById('wiki-progress');
    const pct = window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100;
    if (el) el.style.width = pct + '%';
  });
</script>
```

---

## 12. Customer Support Agent — Content Template

This is the canonical content structure for a customer support AI agent wiki page.
Fill in the bracketed placeholders for your specific agent.

```markdown
# [Agent Name] — Customer Support Agent

<!-- PASTE HEADER BAND HTML (Section 9.1) here -->

---

## Overview

[Agent Name] is an Azure OpenAI–powered conversational agent deployed on [Channel(s): Web Chat / Teams / Email].
It handles tier-1 support for [Product/Team] by resolving [X]% of inbound tickets without human intervention,
routing escalations to [CRM System] with full conversation context.

<!-- PASTE KPI CARDS HTML (4× Section 9.2 in a grid) here -->

---

## UI Design Flow

[Description of the user journey through the support interface — 2–3 sentences.]

<!-- PASTE FLOW DIAGRAM (Section 15) here -->

---

## System Prompt

The following prompt governs the agent's identity, tone, capabilities, and safety boundaries.

<!-- PASTE SYSTEM PROMPT CODE BLOCK (Section 9.5) here -->

---

## Agent Behavior Pipeline

When a message arrives, the agent executes the following decision pipeline:

<!-- PASTE STEP PIPELINE HTML (Section 9.7) here — 5 steps minimum -->

---

## Q&A Reference Bank

Quick-reference answers to the most common customer queries. Expand each item for the full answer.

### Account & Authentication
<!-- PASTE ACCORDIONS (Section 9.4) -->

### Billing & Payments
<!-- PASTE ACCORDIONS (Section 9.4) -->

### Orders & Fulfillment
<!-- PASTE ACCORDIONS (Section 9.4) -->

### Technical Issues
<!-- PASTE ACCORDIONS (Section 9.4) -->

---

## Architecture

<!-- PASTE ARCHITECTURE TABLE (Section 9.6) -->

---

## KPIs & Monitoring

<!-- PASTE 6× KPI CARDS in a grid -->

---

## Changelog

<!-- PASTE CHANGELOG TABLE (Section 9.8) -->
```

---

## 13. System Prompt — Authoring Standard

A well-authored system prompt in a wiki page serves two purposes:
1. **Documentation** — It tells any reader exactly how the agent behaves.
2. **Operational reference** — It's the source of truth for deployments.

### Prompt Structure (Mandatory Sections)

```
## Identity
  - Agent name and role description
  - Tone and persona guidelines
  - Language handling rules

## Capabilities
  - List of things the agent CAN do
  - Available tools / function calls (with parameter hints)
  - Knowledge domains covered

## Constraints
  - List of things the agent MUST NOT do
  - Data handling and PII rules
  - Policy boundaries (what it cannot commit to)

## Escalation Triggers
  - Conditions that force handoff to a human
  - Confidence threshold value
  - Maximum retry count before escalation

## Response Format
  - Length guidance (short/medium/long per query type)
  - Markdown vs plain text
  - Citation format if referencing knowledge base articles
```

### Prompt Quality Rules

- **Be specific, not verbose.** "Respond in 2–3 sentences for simple factual queries" is better than "Keep responses concise."
- **Make constraints absolute.** "Never disclose" not "try to avoid disclosing."
- **Specify the escalation threshold numerically.** "Confidence < 0.72" not "when unsure."
- **Version the prompt.** Include `# Prompt Version: 2.4 | Last modified: Apr 2026` as the first line of the prompt.
- **Use Markdown inside the prompt.** `##` sections and `-` bullets are rendered by GPT-4o as structure.

---

## 14. Q&A Section — Structure & Format

### Authoring Rules

| Rule | Correct | Wrong |
|---|---|---|
| Question format | User-voice, natural language | "FAQ Item 7" |
| Answer length | 2–4 sentences | 10+ lines or single word |
| Answer tone | Helpful, direct, no jargon | "Per policy §4.2…" |
| Category badge | Always present | Missing or inconsistent |
| Order within category | Most-asked first | Alphabetical |

### Category System

Define categories before authoring Q&A entries:

| Category | Badge Color | Typical Volume |
|---|---|---|
| Account & Auth | Blue | 30% |
| Billing & Payments | Green | 25% |
| Orders & Fulfillment | Orange | 20% |
| Technical Issues | Red | 15% |
| Product Information | Purple | 10% |

### Example Q&A Entry (Well-Formed)

```
Q: Why was I charged twice for my last order?
Category: Billing
A: Duplicate charges are usually caused by a payment retry after a
   network timeout. The extra charge is typically reversed within
   3–5 business days. If it persists beyond 5 days, reply here
   with your order number and we'll escalate to the payments team.
```

### Example Q&A Entry (Poorly Formed — Do Not Use)

```
Q: Billing issue?              ← Too vague, not user-voice
A: Please contact billing.    ← Not an answer, not helpful
```

---

## 15. UI Design Flow — Diagram Standard

Use **Mermaid flowchart diagrams** for all UI flow documentation. Azure Wiki renders Mermaid
natively via the `::: mermaid` fenced block.

### Standard Customer Support Agent Flow

```
::: mermaid
flowchart TD
    A([👤 User]) --> B[Chat Widget Opens]
    B --> C{Authentication\nCheck}
    C -- Not logged in --> D[Show Login Prompt]
    C -- Logged in --> E[Load Conversation Context\nfrom Redis]
    D --> E
    E --> F[User Sends Message]
    F --> G[Azure Functions\nPreprocessor]
    G --> H{Content Safety\nFilter}
    H -- Flagged --> I[Return Safety\nDecline Message]
    H -- Clean --> J[Azure OpenAI\nGPT-4o Inference]
    J --> K{Confidence\nScore Check}
    K -- Score < 0.72 --> L[Escalate to\nHuman Agent Queue]
    K -- Score ≥ 0.72 --> M[Tool Call Required?]
    M -- Yes --> N[Execute Tool\nget_order / create_ticket]
    N --> O[Inject Tool Result\ninto Context]
    O --> P[Final Response\nGeneration]
    M -- No --> P
    P --> Q[Send Response\nto User]
    Q --> R{Resolved?}
    R -- Yes --> S([✅ Close Ticket])
    R -- No --> F
:::
```

### Mermaid Diagram Rules

- **Direction:** Use `TD` (top-down) for linear flows, `LR` (left-right) for state machines.
- **Decisions:** Use `{}` diamond nodes. Always label both branches.
- **Start/End:** Use `([...])` stadium shapes for user/system endpoints.
- **Maximum width:** Keep diagrams to 8–10 nodes per row. Split complex flows into sub-diagrams.
- **Color:** Do not use Mermaid theme styling beyond the default — it renders inconsistently across Azure Wiki tenants.
- **Labels:** All arrows that represent a decision must have a label (`-- Label -->`).

### When to Use HTML Diagrams vs Mermaid

| Use case | Recommendation |
|---|---|
| End-to-end flow (7+ nodes) | Mermaid flowchart |
| Architecture block diagram | HTML flex/grid boxes |
| State machine | Mermaid stateDiagram-v2 |
| Sequence diagram | Mermaid sequenceDiagram |
| Simple 3–4 step pipeline | HTML step component (Section 9.7) |

---

## 16. Accessibility & Performance Checklist

### Accessibility (WCAG 2.1 AA)

- [ ] All `<img>` elements have `alt` text. Decorative images: `alt=""`.
- [ ] Color is never the **only** means of conveying information (add text label or icon).
- [ ] Body text contrast ratio ≥ 4.5:1 on all surface backgrounds.
- [ ] Large text (24px+) contrast ratio ≥ 3:1.
- [ ] All interactive elements reachable and operable via keyboard (Tab, Enter, Space, Escape).
- [ ] `:focus-visible` outline is never suppressed (`outline: none` is forbidden without a custom focus ring).
- [ ] Heading hierarchy is sequential: H1 → H2 → H3. Never skip levels.
- [ ] Tables have `<th>` headers, not just `<td>` with bold text.
- [ ] `<details>`/`<summary>` accordions are used instead of JS-toggled `display:none` divs.
- [ ] Font size is never below 12px.

### Performance

- [ ] No external fonts loaded via `@import` unless tested in the tenant.
- [ ] Images are WebP or SVG where possible.
- [ ] Inline SVG icons instead of external icon font CDNs.
- [ ] `<script>` tags are deferred or inline-only (no external scripts from CDN).
- [ ] `<style>` block is placed in the `<head>` equivalent (top of the `.md` file, before content).
- [ ] Large tables use `content-visibility: auto` on `<tbody>` for paint performance.

---

## 17. Anti-Patterns — Never Do These

### Content Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| Opening with architecture or code | Reader has no context | Always start with Overview |
| Writing Q&A as plain paragraphs | Unnavigable wall of text | Use `<details>` accordion |
| Pasting raw system prompt as Markdown | Loses code formatting | Use dark code block component |
| Using H1 more than once per page | Breaks screen reader nav | One H1 per page |
| Skipping heading levels (H2 → H4) | Breaks accessibility | Follow sequential hierarchy |
| Unlabeled decision branches in Mermaid | Ambiguous flow | Label every arrow at a decision |
| No version badges on the header | Reader can't assess freshness | Always include version + date |

### Design Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| Colored left-border on regular cards | Looks like Material Design 1.0 | Use surface elevation or neutral border |
| Rainbow badge row (6+ colors) | Visual noise, no hierarchy | Max 2 non-neutral hues per viewport |
| `border: 1px solid #cccccc` solid gray | Doesn't adapt to dark mode | Use `oklch(... / 0.15)` alpha border |
| Pure black text on white (`#000`/`#fff`) | Harsh contrast, no warmth | Use `--wiki-text` / `--wiki-bg` tokens |
| Gradient buttons | Looks cheap and AI-generated | Solid `--wiki-primary` fill only |
| Icons in colored circles | SaaS template cliché | Use bare icons + typography hierarchy |
| Centered body text | Hard to read, AI aesthetic | Left-align all body text |
| Uniform large border-radius everywhere | Bubbly, toy-like feel | Use radius hierarchy per element size |
| Every section with identical padding | Monotonous rhythm | Vary `padding-block` by content density |

### Technical Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| `localStorage` in `<script>` | Blocked in sandboxed iframes | Use in-memory JS variables |
| External `<script src="...">` tags | CDN may be blocked by Azure policy | Inline all JS |
| `!important` in styles | Specificity hack, fragile | Fix the selector |
| Hardcoded hex colors | Breaks dark mode | Use CSS custom properties |
| `onclick="eval(...)"` | Security policy violation | Use named functions or simple inline expressions |
| `<iframe>` embeds | Blocked by Azure security policy | Use Mermaid or HTML components |

---

## 18. Quality Gate Checklist

Before publishing or merging a wiki page, verify every item:

### Content
- [ ] Page opens with the header band (Section 9.1) — no raw title as the first element.
- [ ] Overview section present and under 4 sentences + KPI cards.
- [ ] UI Design Flow diagram present (Mermaid or HTML).
- [ ] System prompt present in dark code block with copy button.
- [ ] Q&A section uses `<details>` accordion with category badges.
- [ ] Architecture table present with status badges.
- [ ] Changelog table present in reverse chronological order.

### Design
- [ ] `<style>` token block at the top of the file.
- [ ] No hardcoded hex values in any component — only `var(--wiki-*)` tokens.
- [ ] Radius hierarchy observed (pills for badges, `--wiki-radius-lg` for cards).
- [ ] No more than 2 non-neutral accent colors visible in any section.
- [ ] Callout semantic colors match content type (info/success/warning/error).

### Accessibility
- [ ] Single `<h1>` on the page.
- [ ] All images have `alt` text.
- [ ] No text smaller than 12px.
- [ ] All interactive elements (accordion summaries, copy buttons) are keyboard-accessible.

### Technical
- [ ] No `localStorage`, `sessionStorage`, or `eval()` in scripts.
- [ ] No external `<script src>` references.
- [ ] Dark mode tested via `prefers-color-scheme: dark` simulation in browser DevTools.
- [ ] Mermaid diagrams render correctly (check for unescaped special characters).
- [ ] Page scrolls without horizontal overflow on 375px viewport.

---

*This skill document is maintained by the Platform Engineering team.*
*Last updated: April 2026 · Version 1.0*
*To propose changes, open a PR against `docs/skills/azure-wiki-onepager-skill.md`.*
