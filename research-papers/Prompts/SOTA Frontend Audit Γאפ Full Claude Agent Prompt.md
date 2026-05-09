# SOTA Frontend Audit — Full Claude Agent Prompt (Local Dev)

> **How to use this document:** Paste the contents of **Section 2 (The Prompt)** verbatim into Claude (Claude Code / Claude.ai with Projects). Claude will self-orchestrate using Playwright MCP, Codex CLI, and its own shell access to perform a full-stack, fully automated frontend audit of your locally running website. No human intervention is required once the prompt is running.

***

## 1. Prerequisites & Environment Setup

Before running the prompt, ensure the following tools are installed and accessible in Claude's environment.

### 1.1 Required Tooling

| Tool | Install Command | Purpose |
|------|----------------|---------|
| **Playwright MCP** | `npx playwright install --with-deps` + MCP config | Browser automation, screenshots, ARIA tree, visual regression[^1][^2] |
| **Lighthouse 13 CLI** | `npm install -g lighthouse` | Performance, CWV, A11y, SEO, Best Practices audits[^3][^4] |
| **axe-core/playwright** | `npm install @axe-core/playwright` | WCAG 2.1 AA automated accessibility scanning[^5][^6] |
| **Codex CLI** | `npm install -g @openai/codex` | Read-only code review of the codebase[^7][^8] |
| **vite-bundle-visualizer** | `npm install -D vite-bundle-visualizer` | JS bundle size and tree-shaking analysis[^9] |
| **Microsoft Clarity script** | Inject snippet into `<head>` | Session heatmaps & rage-click detection[^10] |

### 1.2 MCP Config (`.claude.json` — user scope)

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": { "PLAYWRIGHT_HEADLESS": "true" }
    }
  }
}
```

### 1.3 SOTA Minimal Stack Enforced by This Audit[^11][^12][^13]

The audit validates that the codebase conforms to the **2026 minimal SOTA stack**:

| Layer | Enforced Tool | Why Minimal & SOTA |
|-------|-------------|-------------------|
| Framework | Next.js 15+ (App Router) | RSC, SSR/SSG hybrid, file-based routing[^11][^12] |
| Language | TypeScript (strict) | Type safety, zero `any`[^11] |
| Styling | Tailwind CSS v4 | Utility-first, zero runtime CSS, small bundle[^12][^13] |
| UI Components | shadcn/ui + Radix UI | Copy-owned, accessible headless primitives[^11][^13] |
| Bundler | Vite 7 / Rolldown | 16× faster builds vs Webpack, minimal config[^14] |
| State | React 19 + URL params | Server state via RSC; TanStack Query for async[^12] |
| Analytics | Microsoft Clarity (free) | Unlimited heatmaps + session recordings[^10] |

### 1.4 Core Web Vitals Budgets (2026 Thresholds)

| Metric | Good (Required) | Stretch Goal |
|--------|----------------|--------------|
| LCP | ≤ 2.5s | ≤ 1.8s |
| INP | ≤ 200ms | ≤ 100ms |
| CLS | ≤ 0.1 | ≤ 0.05 |

These are the official Google 2026 thresholds and represent the performance gate the audit enforces.[^15][^16][^17]

***

## 2. The Full Claude Agent Prompt

> **Copy everything between the triple-backtick fences below and send it to Claude Code.**

```
# ROLE
You are a SOTA Frontend Audit Agent. You have access to:
  - Playwright MCP (browser automation, screenshots, ARIA tree, network interception)
  - Lighthouse 13 CLI (performance/a11y/SEO/best-practices audits)
  - axe-core via @axe-core/playwright (WCAG 2.1 AA scanning)
  - Codex CLI (read-only code review — never modifies files)
  - vite-bundle-visualizer / webpack-bundle-analyzer (bundle inspection)
  - Your shell (run any Node.js, bash, or npx command)

Your mission: perform a comprehensive, fully automated SOTA frontend audit of the
local dev website running at http://localhost:3000 (adjust if needed).
Produce a single structured Markdown audit report at ./audit-report.md.
Use the Codex CLI to cross-validate every finding you make in the code.

---

# STEP 0 — ENVIRONMENT PREFLIGHT

Before any audit steps, run the following checks and abort with a clear error
if any tool is missing:

```bash
# 1. Confirm local dev server is reachable
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# 2. Confirm Lighthouse is installed
lighthouse --version

# 3. Confirm Playwright can launch
npx playwright --version

# 4. Confirm Codex CLI is available (read-only)
codex --version

# 5. Confirm axe-core package is present
node -e "require('@axe-core/playwright'); console.log('axe-core OK')"
```

If all checks pass, print "✅ PREFLIGHT PASSED — Starting audit" and proceed.

---

# STEP 1 — LIGHTHOUSE 13 FULL AUDIT

Run Lighthouse 13 against localhost:3000 in both desktop and mobile modes.
Use the new insight-based audit format (--legacy-navigation=false flag in LH 13).

```bash
lighthouse http://localhost:3000 \
  --output=json,html \
  --output-path=./audit-results/lighthouse-desktop \
  --preset=desktop \
  --chrome-flags="--headless=new" \
  --only-categories=performance,accessibility,best-practices,seo

lighthouse http://localhost:3000 \
  --output=json,html \
  --output-path=./audit-results/lighthouse-mobile \
  --chrome-flags="--headless=new" \
  --only-categories=performance,accessibility,best-practices,seo
```

Parse both JSON outputs. For each of the 4 categories × 2 modes, extract:
- Score (0–100)
- All RED and YELLOW flagged audits with their description and impact
- Core Web Vitals: LCP, INP, CLS actual values vs. Good thresholds
  - LCP Good = ≤ 2.5s | INP Good = ≤ 200ms | CLS Good = ≤ 0.1

For every audit failure (red/yellow), note: audit ID, title, description,
score, and the specific element or resource that caused the failure.

**CODEX CROSS-VALIDATE (after Lighthouse):**
```
codex exec -m gpt-4o-codex -s read-only \
  "Review the source code at ./src. For each Lighthouse failure listed in
   /tmp/lh-failures.txt, identify the exact file and line number responsible.
   Quote the problematic code. Suggest the minimal SOTA fix.
   End with VERDICT: APPROVED or VERDICT: REVISE."
```
Write Lighthouse failures to /tmp/lh-failures.txt before running Codex.

---

# STEP 2 — PLAYWRIGHT MCP: VISUAL & INTERACTION AUDIT

Use the Playwright MCP server to perform a live visual and interaction audit.
For each of the following page types present on the site, navigate and execute:

  a) Homepage / landing page
  b) Any form page (contact, login, signup, checkout)
  c) Any list/grid page (products, blog, dashboard)
  d) Any detail/single-entity page (product detail, blog post)
  e) Any modal or drawer that opens on interaction

For EACH page/state, perform ALL of the following sub-checks:

### 2a. Screenshot Baseline
  - Take a full-page screenshot: desktop (1440×900) and mobile (375×812)
  - Save to ./audit-results/screenshots/<page>-desktop.png and <page>-mobile.png
  - Visually describe what you observe: layout quality, whitespace, hierarchy,
    contrast, font legibility, image quality, CLS-prone elements

### 2b. Semantic HTML & Agent Readability Audit
  - Capture the accessibility tree from Playwright MCP
  - Check for:
    □ Presence of exactly one <h1> per page
    □ Logical heading hierarchy (h1 → h2 → h3, no skips)
    □ All images have meaningful alt attributes (not empty, not "image")
    □ All form inputs have associated abel> elements
    □ Interactive elements use semantic tags (<button>, <a>, <input>)
    □ No divs used as buttons (role="button" on div is acceptable only
      if aria-label and keyboard events are also present)
    □ Landmark regions: <main>, <header>, <nav>, <footer> present
    □ Skip navigation link present for keyboard users

### 2c. Keyboard Navigation Audit
  - Use Playwright keyboard API to Tab through interactive elements
  - Verify: every focusable element receives a visible focus ring
  - Verify: no keyboard traps (Tab cycles correctly)
  - Verify: modals trap focus when open and restore on close

### 2d. Responsive Layout Audit
  - Test at 5 breakpoints: 375, 768, 1024, 1280, 1440 (px width)
  - At each breakpoint take a screenshot and check:
    □ No horizontal overflow (scrollWidth === clientWidth)
    □ Text is not truncated in unexpected ways
    □ Touch targets on mobile ≥ 44×44px (WCAG 2.5.5)
    □ Navigation is usable (hamburger menu opens/closes correctly)

### 2e. Form Interaction & Validation Audit
  - On any form found: fill all fields with valid data, submit, observe response
  - Then fill with invalid data (empty required field, invalid email), check:
    □ Error messages appear inline next to the field (not just alert())
    □ Errors are announced to screen readers (aria-live or role="alert")
    □ No form submission of invalid data possible
    □ Success state is clearly communicated

### 2f. Network & Performance Observation
  - Intercept all network requests during full page load
  - Flag: any uncompressed response > 100KB
  - Flag: any image > 200KB (should be WebP/AVIF)
  - Flag: any third-party script from an external domain
  - Flag: any render-blocking <script> without async/defer
  - Flag: any CSS loaded via @import (blocking)
  - Measure: Time to First Byte (TTFB), note if > 600ms on localhost

---

# STEP 3 — WCAG 2.1 AA ACCESSIBILITY DEEP SCAN (axe-core)

Write and execute the following Playwright + axe-core test script:

```javascript
// ./audit-scripts/axe-scan.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const PAGES = [
  { name: 'home', url: 'http://localhost:3000' },
  { name: 'form', url: 'http://localhost:3000/contact' }, // adjust URL
  // Add any discovered pages here
];

for (const { name, url } of PAGES) {
  test(`axe WCAG 2.1 AA — ${name}`, async ({ page }) => {
    await page.goto(url);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'best-practice'])
      .analyze();

    // Write results JSON for Codex cross-validation
    const fs = require('fs');
    fs.writeFileSync(
      `./audit-results/axe-${name}.json`,
      JSON.stringify(results, null, 2)
    );

    // Group violations by impact
    const critical = results.violations.filter(v => v.impact === 'critical');
    const serious  = results.violations.filter(v => v.impact === 'serious');

    console.log(`[${name}] critical: ${critical.length}, serious: ${serious.length}`);
    // Do NOT assert — collect all, let the report decide severity
  });
}
```

Run with: `npx playwright test ./audit-scripts/axe-scan.spec.ts --reporter=json`

Parse the output. For each violation, record:
  - Rule ID, description, impact level (critical/serious/moderate/minor)
  - Affected HTML element (outerHTML snippet)
  - WCAG criterion violated
  - Recommended fix

**CODEX CROSS-VALIDATE (axe results):**
```
codex exec -m gpt-4o-codex -s read-only \
  "Review the axe violation list in ./audit-results/axe-*.json.
   For each critical or serious violation, find the responsible component
   in ./src. Confirm the violation is real (not a false positive).
   Suggest the minimal code fix with ARIA or semantic HTML.
   End with VERDICT: APPROVED or VERDICT: REVISE."
```

---

# STEP 4 — SOTA STACK CONFORMANCE AUDIT (Codex CLI)

Run a full read-only Codex review of the entire codebase to enforce the
SOTA minimal stack requirements.

**Write the following audit checklist to /tmp/stack-checklist.md:**

```markdown
## SOTA Stack Conformance Checklist

### Framework & Language
- [ ] Using Next.js 15+ with App Router (not Pages Router)
- [ ] TypeScript strict mode enabled (tsconfig "strict": true)
- [ ] No `any` types in production code paths
- [ ] Server Components used by default; Client Components only where needed

### Styling
- [ ] Tailwind CSS v4+ with no global CSS bloat
- [ ] No inline style= attributes except for truly dynamic values
- [ ] No CSS-in-JS runtime (styled-components, emotion) — only Tailwind
- [ ] Dark mode supported via Tailwind dark: variant or CSS variables

### UI Components
- [ ] shadcn/ui components present in /components/ui
- [ ] Radix UI used as headless primitive layer
- [ ] No Bootstrap, Chakra, MUI, or Ant Design installed

### Bundler & Build
- [ ] Vite 7 / Rolldown OR Next.js with Turbopack — not plain Webpack
- [ ] Tree-shaking verified: no full lodash import, use lodash-es
- [ ] Dynamic imports used for heavy components (React.lazy / next/dynamic)
- [ ] Image optimization: only next/image or equivalent (no raw <img> for LCP)
- [ ] No unused dependencies in package.json

### Performance
- [ ] No render-blocking scripts in <head> without defer/async
- [ ] LCP image has fetchpriority="high" and preload link
- [ ] Font loading: font-display: swap or optional
- [ ] No layout shift from ads, embeds, or late-loading images (CLS < 0.1)

### Accessibility (Code Level)
- [ ] All interactive components keyboard accessible
- [ ] Color contrast ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- [ ] No ARIA roles that override native semantics without need
- [ ] Focus management on modals, drawers, and route changes

### Analytics
- [ ] Microsoft Clarity snippet present in layout (or <head>)
- [ ] No Hotjar AND Clarity simultaneously (avoid INP penalty from dual tracking)
- [ ] No blocking analytics scripts (use async tag injection)
```

Then run Codex:
```
codex exec -m gpt-4o-codex -s read-only \
  "You are a strict SOTA frontend code auditor. Review the full codebase at ./
   against every checklist item in /tmp/stack-checklist.md.
   For each FAILED item:
     1. State the item
     2. Quote the exact file:line evidence
     3. Explain the performance or quality impact
     4. Provide the minimal SOTA fix (code snippet)
   For each PASSED item: one-line confirmation only.
   Final summary: X passed, Y failed.
   End with: AUDIT: PASS (0 critical failures) or AUDIT: CONCERNS (list them)."
```

---

# STEP 5 — BUNDLE SIZE AUDIT

If using Vite:
```bash
npx vite-bundle-visualizer --open=false --outDir=./audit-results/bundle
```

If using Next.js:
```bash
ANALYZE=true npx next build
# Requires @next/bundle-analyzer configured in next.config.js
```

Parse the bundle stats. Report:
  - Total JS bundle size (gzipped)
  - Largest 5 chunks by size
  - Any single chunk > 100KB gzipped (flag as "needs code splitting")
  - Detected duplicate dependencies (same package, multiple versions)
  - Any moment.js, lodash (non-es), or other known bundle-bloat packages

**CODEX CROSS-VALIDATE:**
```
codex exec -m gpt-4o-codex -s read-only \
  "Review ./audit-results/bundle for large chunks. For each chunk > 100KB,
   find the import chain in ./src that caused it.
   Suggest dynamic import() or tree-shaking fixes.
   End with VERDICT: APPROVED or VERDICT: REVISE."
```

---

# STEP 6 — BEHAVIOR ANALYTICS READINESS CHECK

Verify Microsoft Clarity (or Hotjar fallback) is properly installed:

```javascript
// Playwright MCP: check for Clarity script presence
const clarityPresent = await page.evaluate(() =>
  typeof window.clarity !== 'undefined'
);
const hotjarPresent = await page.evaluate(() =>
  typeof window.hj !== 'undefined'
);

// Flag if BOTH are present (INP penalty risk)
if (clarityPresent && hotjarPresent) {
  flag("WARN: Both Clarity and Hotjar loaded. Dual tracking hurts INP.");
}

// Flag if NEITHER is present
if (!clarityPresent && !hotjarPresent) {
  flag("WARN: No behavior analytics detected. Add Microsoft Clarity (free, unlimited).");
}
```

Check that the analytics script:
  - Loads with async attribute (not blocking)
  - Does not fire before user consent if GDPR is required
  - Does not capture passwords or payment fields (check clarity privacy settings)

---

# STEP 7 — FINAL CODEX HOLISTIC AUDIT (FRESH SESSION)

After all steps complete, run one final FRESH Codex session for a holistic view:

```
codex exec -m gpt-4o-codex -s read-only \
  "You are performing a FINAL HOLISTIC AUDIT. Read:
   - ./audit-results/lighthouse-desktop.json
   - ./audit-results/lighthouse-mobile.json
   - ./audit-results/axe-*.json
   - ./audit-results/bundle/ (stats summary)
   - ./audit-scripts/ (all audit scripts written)
   - ./src (full source codebase)

   Your job is NOT to repeat prior findings. Check for:
   1. Systemic patterns that incremental checks may have missed
      (e.g., all forms lack ARIA live regions, all pages miss OG meta tags)
   2. Consistency issues: naming conventions, error handling patterns,
      loading state patterns — are they uniform across components?
   3. Security surface: any dangerouslySetInnerHTML, eval(), or
      unsanitized user input rendered to DOM?
   4. Anything that only becomes visible reading the codebase as a whole.

   End with: AUDIT: PASS or AUDIT: CONCERNS (with specific, actionable items).
   This session result is for human review — do not loop."
```

---

# STEP 8 — GENERATE AUDIT REPORT

Compile ALL findings from Steps 1–7 into ./audit-report.md using this structure:

```markdown
# Frontend Audit Report
**URL:** http://localhost:3000
**Date:** <today's date>
**Auditor:** Claude Agent + Codex CLI + Playwright MCP + Lighthouse 13

***

## Executive Summary
<2–4 sentence overview: overall health, most critical issues, top wins>

## Scores Overview

| Category | Desktop | Mobile | Status |
|----------|---------|--------|--------|
| Performance | X/100 | X/100 | 🟢/🟡/🔴 |
| Accessibility | X/100 | X/100 | 🟢/🟡/🔴 |
| Best Practices | X/100 | X/100 | 🟢/🟡/🔴 |
| SEO | X/100 | X/100 | 🟢/🟡/🔴 |
| WCAG 2.1 AA Violations | - | Critical: N / Serious: N | 🟢/🟡/🔴 |
| Stack Conformance | X passed / Y failed | - | 🟢/🟡/🔴 |
| Bundle Health | Xkb gzip | - | 🟢/🟡/🔴 |

## Core Web Vitals

| Metric | Measured | Threshold | Pass? |
|--------|----------|-----------|-------|
| LCP | Xs | ≤ 2.5s | ✅/❌ |
| INP | Xms | ≤ 200ms | ✅/❌ |
| CLS | X | ≤ 0.1 | ✅/❌ |

## Critical Issues (Fix immediately)
<Each issue with: title, evidence, file:line if applicable, fix>

## Serious Issues (Fix before launch)

## Moderate Issues (Fix in next sprint)

## SOTA Stack Violations
<Each with: checklist item, evidence, recommended fix>

## Bundle Analysis
<Largest chunks, dependencies to replace, estimated savings>

## Accessibility Findings
<Grouped by impact: critical → serious → moderate>

## Visual & Interaction Findings
<Screenshots at each breakpoint, layout issues, responsive gaps>

## Analytics & Observability
<Clarity/Hotjar status, async loading, privacy concerns>

## Codex Final Verdict
<Paste the AUDIT: PASS / AUDIT: CONCERNS output from Step 7>

## Recommended Action Plan
| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| P0 | ... | XS/S/M/L | High/Med/Low |
...
```

After writing audit-report.md, print:
"✅ AUDIT COMPLETE — Report saved to ./audit-report.md"
Then print a 3-line plain-English summary of the top 3 most critical findings.
```

***

## 3. Codex CLI Review Loop Architecture

The prompt above implements a **hybrid review strategy** based on current best practice for Claude + Codex co-agent pipelines:[^7]

- **Fix-loop Codex sessions** use `codex exec resume <session-id>` to verify fixes are applied, maintaining traceability across iterations.[^7]
- **Final audit Codex session** (Step 7) uses a **fresh session** to eliminate the "this is acceptable" bias that accumulates during incremental fixes.[^7]
- All Codex runs use **`-s read-only`** sandbox — the reviewer never touches implementation.[^8][^7]

```
Claude Agent (orchestrator)
  │
  ├── Step 1: Lighthouse CLI ──── JSON ──→ Codex fix-loop
  ├── Step 2: Playwright MCP (browser) ──→ screenshots, ARIA tree
  ├── Step 3: axe-core/Playwright ─────→ JSON ──→ Codex fix-loop
  ├── Step 4: Codex stack review ──────→ checklist verdict
  ├── Step 5: Bundle analyzer ─────────→ JSON ──→ Codex fix-loop
  ├── Step 6: Clarity/Hotjar check ────→ inline finding
  └── Step 7: Codex FRESH session ─────→ AUDIT: PASS/CONCERNS
                                              ↓
                                     audit-report.md
```

***

## 4. Tool Capability Matrix

| Audit Dimension | Lighthouse 13 | Playwright MCP | axe-core | Codex CLI |
|----------------|---------------|---------------|----------|-----------|
| Core Web Vitals (LCP/INP/CLS) | ✅ Primary | ⚠️ Observed | ❌ | ✅ Code root cause |
| WCAG 2.1 AA | ✅ ~30% coverage[^18] | ✅ ARIA tree | ✅ ~50% coverage[^19] | ✅ Code fix |
| Visual regression | ❌ | ✅ Screenshots[^20] | ❌ | ❌ |
| Keyboard navigation | ❌ | ✅ Tab simulation[^2] | ⚠️ Partial | ✅ Code |
| Bundle size | ❌ | ❌ | ❌ | ✅ Primary[^9] |
| SOTA stack conformance | ❌ | ❌ | ❌ | ✅ Primary[^7] |
| Semantic HTML / agent readability | ⚠️ Partial | ✅ ARIA tree[^1] | ✅ | ✅ |
| Analytics tag audit | ❌ | ✅ JS eval[^2] | ❌ | ✅ |
| Network waterfall | ✅ | ✅ Intercept | ❌ | ❌ |
| Responsive layout | ✅ Mobile preset | ✅ Viewport resize | ❌ | ❌ |

***

## 5. Behavior Analytics — Local Dev Strategy

For local dev, **Microsoft Clarity** is the recommended free default over Hotjar for the following reasons:[^21][^10]

- **Unlimited sessions** with no daily cap (Hotjar free tier is capped at 35 sessions/day)[^10]
- **Rage clicks + JavaScript error detection** built-in[^10]
- **Page speed monitoring** included in dashboard[^22]
- Single `<script async>` tag with no complex setup — audit-friendly[^23]

The audit prompt explicitly checks that behavior analytics scripts load **async** to avoid INP penalties from third-party tracking threads competing on the main thread.[^16]

***

## 6. Expected Output

Running the prompt end-to-end produces the following artifacts in `./audit-results/`:

```
audit-results/
├── lighthouse-desktop.report.html    ← Human-readable LH report
├── lighthouse-desktop.report.json    ← Machine-readable for Codex
├── lighthouse-mobile.report.html
├── lighthouse-mobile.report.json
├── screenshots/
│   ├── home-desktop.png
│   ├── home-mobile.png
│   └── ...
├── axe-home.json                     ← WCAG violations per page
├── axe-form.json
├── bundle/                           ← Bundle visualizer output
└── audit-report.md                   ← ✅ THE FINAL DELIVERABLE
```

The `audit-report.md` is a standalone, shareable document that a developer or design team can act on immediately, with every issue traced to a specific file, line, and recommended fix.

---

## References

1. [Playwright MCP: AI-Powered Browser Automation Guide](https://aiagentskit.com/blog/playwright-mcp/) - Learn how Playwright MCP connects AI agents to real browsers using the Model Context Protocol. Setup...

2. [Testing with Playwright and Claude Code - nikiforovall.blog](https://nikiforovall.github.io/ai/2025/09/06/playwright-claude-code-testing.html) - Learn how to use Playwright MCP servers with Claude Code slash commands to perform manual and explor...

3. [Google Lighthouse 13: Insight-Based Audits for 2025](https://searchsavvy.in/google-lighthouse-13-launches-with-insight-based-audits-a-game-changer-for-web-performance-in-2025/) - Boost performance with Google Lighthouse 13. Explore new insight-based audits designed to enhance sp...

4. [Automating Browser-Based Performance Testing](https://dev.to/leading-edje/automating-browser-based-performance-testing-1n6) - Open your site in Chrome → Right‑click Inspect → Lighthouse tab → Set your analysis options → Analyz...

5. [Playwright Accessibility Testing: Fast CI Automation Guide](https://testdino.com/blog/playwright-accessibility/) - This guide covers how to add axe-core to your Playwright test suite in under 20 lines of code, enfor...

6. [How We Automate Accessibility Testing with Playwright ...](https://dev.to/subito/how-we-automate-accessibility-testing-with-playwright-and-axe-3ok5) - In this article, we'll show you how we use Playwright combined with Axe ( @axe-core/playwright ) to ...

7. [Automating the Claude Code × Codex Review Loop](https://smartscope.blog/en/blog/claude-code-codex-review-loop-automation-2026/) - Level 1: Start with a Single SKILL.md File. The /codex-review command triggers an automated Codex re...

8. [Codex CLI](https://developers.openai.com/codex/cli/) - Codex CLI is OpenAI's coding agent that you can run locally from your terminal. It can read, change,...

9. [How to Reduce JavaScript Bundle Size in 2025 🚀](https://dev.to/frontendtoolstech/how-to-reduce-javascript-bundle-size-in-2025-2n77) - Modern bundlers like Vite and Webpack eliminate unused code automatically. Ensure you're using ES6 i...

10. [Free analytics for HR firms: Clarity vs Hotjar tested - Luniq](https://www.luniq.io/en/resources/blog/microsoft-clarity-vs-hotjar-best-free-analytics-for-hr-firms-in-2026) - This comparison of Microsoft Clarity vs Hotjar helps you pick the right free analytics tool to stop ...

11. [I Tested 10 Shadcn Templates for Next.js Projects (Here ...](https://dev.to/vaibhavg/i-tested-shadcn-templates-for-nextjs-projects-32p6) - When building modern React apps, many developers now use Shadcn UI with Next.js and Tailwind instead...

12. [React Developers Favor Next.js, Tailwind CSS, and ...](https://www.linkedin.com/posts/vibha-verma-45133722_reactjs-frontenddevelopment-webdevelopment-activity-7437055399859539970-wYkC) - The React Stack Developers Are Choosing in 2026 Frontend development is evolving rapidly, and the to...

13. [Which is the go-to React UI / Next JS library in 2026?](https://www.reddit.com/r/reactjs/comments/1rfenu5/which_is_the_goto_react_ui_next_js_library_in_2026/) - Shadcn + Tailwind is basically the default stack right now and honestly it deserves it. The copy-pas...

14. [Rspack vs Vite: Which Bundler to Choose in 2025?](https://www.linkedin.com/posts/andrey-burov_webdevelopment-javascript-react-activity-7384551106271690752-m-iP) - Rspack vs Vite: Which Bundler to Choose in 2025? If you're tired of slow Webpack builds or choosing ...

15. [What Are Core Web Vitals? A Practical Guide for 2026](https://apogeewatcher.com/blog/what-are-core-web-vitals-a-practical-guide-for-2026) - Google confirmed that Core Web Vitals are a ranking signal. Pages that meet the "Good" thresholds ge...

16. [Core Web Vitals in 2026: What's Changed and How to Pass](https://www.rivuletiq.com/core-web-vitals-2026-whats-changed-and-how-to-pass/) - The 2026 metrics and Good thresholds · LCP (Largest Contentful Paint): Good is 2.5s (developers.goog...

17. [Understanding Core Web Vitals and Google search results](https://developers.google.com/search/docs/appearance/core-web-vitals) - Core Web Vitals is a set of metrics that measure real-world user experience for loading performance,...

18. [Lighthouse Accessibility: Simple Setup and Audit Guide](https://codoid.com/accessibility-testing/lighthouse-accessibility-simple-setup-and-audit-guide/) - Lighthouse accessibility helps quick find and fix issues. Learn setup steps, run audits in any brows...

19. [A You-Oriented Guide to Axe-Core Playwright Accessibility ...](https://www.qamadness.com/a-you-oriented-guide-to-axe-core-playwright-accessibility-testing/) - This automation duo lets you catch up to 50% of WCAG issues quickly, shrink feedback loops, and turn...

20. [Visual comparisons](https://playwright.dev/docs/test-snapshots) - Playwright Test includes the ability to produce and visually compare screenshots using await expect(...

21. [Microsoft Clarity vs. Hotjar: Each Tool's True Strengths](https://www.crazyegg.com/blog/microsoft-clarity-vs-hotjar/) - Microsoft Clarity is better if you're on a budget and need basic insights to grow. Hotjar is ideal i...

22. [Hotjar vs Microsoft Clarity: An Honest Comparison](https://www.hotjar.com/blog/hotjar-vs-microsoft-clarity/) - Both Hotjar and Microsoft Clarity help you understand what's happening on your website by collecting...

23. [How to Set Up Heatmaps on Your Website with Hotjar](https://www.supermonitoring.com/blog/how-to-set-up-heatmaps-with-hotjar/) - See how to install Hotjar heatmaps, track user behavior, and use click and scroll data to improve yo...

