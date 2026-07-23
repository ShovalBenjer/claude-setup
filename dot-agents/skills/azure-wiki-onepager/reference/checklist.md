# Interactions, Accessibility, Anti-Patterns, Quality Gate

## UI/UX Interaction Patterns

### Accordions

Native `<details>`/`<summary>`. No JS, no libraries.
- Keyboard: `Space`/`Enter` toggles, `Tab` moves focus.

### Copy Buttons

Every code block gets one:

```javascript
onclick="
  const code = this.closest('.code-block').querySelector('pre').innerText;
  navigator.clipboard.writeText(code);
  this.textContent = 'Copied';
  setTimeout(() => this.textContent = 'Copy', 2000);
"
```

### Tabs (if needed)

Radio-button CSS, no JS:

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

Every interactive element needs one:
```css
summary:hover { background: var(--wiki-surface-offset); }
tr:hover td   { background: var(--wiki-surface-2); }
button:hover  { background: var(--wiki-primary-hover); }
```

### Reading Progress Bar (optional)

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

## Accessibility Checklist (WCAG 2.1 AA)

- [ ] All `<img>` have `alt`. Decorative: `alt=""`.
- [ ] Color is never the only signal — add text label or icon.
- [ ] Body text contrast >= 4.5:1 on all surfaces.
- [ ] Large text (24px+) contrast >= 3:1.
- [ ] All interactive reachable via keyboard (Tab, Enter, Space, Escape).
- [ ] `:focus-visible` outline never suppressed (no `outline: none` without custom ring).
- [ ] Heading hierarchy sequential: H1 → H2 → H3. Never skip.
- [ ] Tables use `<th>`, not `<td>` with bold.
- [ ] Accordions use `<details>`/`<summary>`, not JS-toggled `display:none`.
- [ ] Font size never below 12px.

## Performance Checklist

- [ ] No external fonts via `@import` unless tested in the tenant.
- [ ] Images WebP or SVG.
- [ ] Inline SVG icons, no icon-font CDN.
- [ ] `<script>` deferred or inline — no external CDN scripts.
- [ ] `<style>` block at top of file.
- [ ] Large tables: `content-visibility: auto` on `<tbody>`.

## Anti-Patterns — Never Do These

### Content

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| Open with architecture or code | No context | Lead with Overview |
| Q&A as paragraphs | Unnavigable | `<details>` accordion |
| Raw prompt as Markdown | No formatting | Dark code block |
| Multiple H1 | Breaks SR nav | One H1 per page |
| Skipping heading levels | Breaks a11y | Sequential hierarchy |
| Unlabeled Mermaid branches | Ambiguous | Label every decision arrow |
| No version badges | No freshness signal | Always include version + date |

### Design

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| Colored left-border on regular cards | Material Design 1.0 look | Surface elevation or neutral border |
| Rainbow badge row (6+ colors) | Visual noise | Max 2 non-neutral hues per viewport |
| Flat gray `#cccccc` border | Breaks dark mode | `oklch(... / 0.15)` alpha |
| Pure black/white text `#000`/`#fff` | Harsh contrast | Use `--wiki-text` / `--wiki-bg` |
| Gradient buttons | Cheap, AI-slop | Solid `--wiki-primary` |
| Icons in colored circles | SaaS template cliché | Bare icons + typography hierarchy |
| Centered body text | Hard to read | Left-align prose |
| Uniform radius everywhere | Toy-like | Radius hierarchy per element |
| Identical padding everywhere | Monotonous rhythm | Vary `padding-block` by density |

### Technical

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| `localStorage` in `<script>` | Blocked in sandbox | In-memory JS |
| External `<script src>` | CDN blocked by Azure | Inline JS |
| `!important` | Specificity hack, fragile | Fix selector |
| Hardcoded hex colors | Breaks dark mode | CSS custom properties |
| `onclick="eval(...)"` | Security policy violation | Named fn or simple inline expr |
| `<iframe>` | Blocked by Azure | Mermaid or HTML |

## Pre-Publish Quality Gate

Verify every item before merging a wiki PR.

### Content
- [ ] Opens with header band — no raw H1 first.
- [ ] Overview ≤ 4 sentences + KPI cards.
- [ ] UI Design Flow diagram present (Mermaid or HTML).
- [ ] System prompt in dark code block with copy button.
- [ ] Q&A uses `<details>` with category badges.
- [ ] Architecture table with status badges.
- [ ] Changelog in reverse chronological order.

### Design
- [ ] `<style>` token block at top of file.
- [ ] No hardcoded hex — only `var(--wiki-*)`.
- [ ] Radius hierarchy observed (pills, md, lg).
- [ ] Max 2 non-neutral accent colors per section.
- [ ] Callout semantic colors match content type.

### Accessibility
- [ ] Single `<h1>`.
- [ ] All images have `alt`.
- [ ] No text below 12px.
- [ ] All interactive elements keyboard-accessible.

### Technical
- [ ] No `localStorage`, `sessionStorage`, `eval()`.
- [ ] No external `<script src>`.
- [ ] Dark mode tested via `prefers-color-scheme: dark` in DevTools.
- [ ] Mermaid renders correctly (escape special chars like `<`, `>`, `&`).
- [ ] No horizontal overflow at 375px viewport.
