# Component Library

Each component is a self-contained HTML snippet using tokens from `tokens.md`. Copy and adapt.

## Header Band

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
    Azure OpenAI-powered agent handling tier-1 support tickets, live chat deflection,
    and automated escalation routing.
  </p>
  <div style="display:flex; flex-wrap:wrap; gap:var(--wiki-space-2);">
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">v2.4</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Azure OpenAI GPT-4o</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Production</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Updated: Apr 2026</span>
  </div>
</div>
```

Rules: solid-to-darker-blue gradient only (no rainbow/neon). Badges white/translucent on the colored background, never colored on colored. Title includes context-appropriate Lucide SVG icon. Always include version + model + environment + last-updated badges.

## KPI Metric Card

```html
<div style="
  background: var(--wiki-surface);
  border: 1px solid var(--wiki-border);
  border-radius: var(--wiki-radius-lg);
  padding: var(--wiki-space-5) var(--wiki-space-6);
  box-shadow: var(--wiki-shadow-sm);
  display: flex; flex-direction: column; gap: var(--wiki-space-2);
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
    +3.2% vs last month
  </span>
</div>
```

Rules: exactly 3 lines — label (uppercase, muted), value (large, bold), delta (colored). Green for improvement, red for regression, muted for neutral. Max 4 per row. Values use `tabular-nums`.

## Callout / Alert Block

```html
<div style="
  border-left: 3px solid var(--wiki-primary);
  background: var(--wiki-info-tint);
  border-radius: 0 var(--wiki-radius-md) var(--wiki-radius-md) 0;
  padding: var(--wiki-space-4) var(--wiki-space-5);
  margin: var(--wiki-space-6) 0;
  display: flex; gap: var(--wiki-space-3); align-items: flex-start;
">
  <span style="font-size:16px; flex-shrink:0; margin-top:2px;">i</span>
  <div>
    <strong style="font-size:var(--wiki-text-sm); color:var(--wiki-primary);">Note</strong>
    <p style="margin:4px 0 0; font-size:var(--wiki-text-sm); color:var(--wiki-text); line-height:1.6;">
      Callout body — 1-3 sentences max.
    </p>
  </div>
</div>
```

Variants: swap `border-color` and `background` per callout semantics in `tokens.md`. Never colored left-border on a regular card — callouts only.

## Accordion Q&A Item

Native HTML `<details>` — no JS.

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
    font-size: var(--wiki-text-base); font-weight: 500;
    cursor: pointer; list-style: none;
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--wiki-space-3); color: var(--wiki-text); user-select: none;
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
    font-size: var(--wiki-text-base); line-height: 1.65;
    color: var(--wiki-text-muted);
  ">
    <p>When confidence drops below 0.72, or the user explicitly requests a human,
    the conversation is transferred to the live-agent queue in Dynamics 365.
    The full transcript is passed along with a 3-sentence summary.</p>
  </div>
</details>
```

Rules: category badge (top-right of summary) is mandatory — enables scanning. Answer lives in `--wiki-surface-2` to visually separate from question. Never nest accordions. Group related Q&As under a `### Category Heading`.

## System Prompt Code Block

```html
<div style="
  background: #0d1117; border-radius: var(--wiki-radius-lg);
  overflow: hidden; margin: var(--wiki-space-6) 0;
  box-shadow: var(--wiki-shadow-md);
">
  <div style="
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--wiki-space-3) var(--wiki-space-5);
    background: #161b22; border-bottom: 1px solid #30363d;
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
      this.textContent = 'Copied';
      setTimeout(()=>this.textContent='Copy',2000);
    " style="
      font-size:var(--wiki-text-xs); color:#8b949e; background:#21262d;
      border:1px solid #30363d; border-radius:4px; padding:4px 10px; cursor:pointer;
    ">Copy</button>
  </div>
  <pre style="
    margin:0; padding:var(--wiki-space-6); overflow-x:auto;
    font-family:var(--wiki-font-mono); font-size:13px; line-height:1.65;
    color:#c9d1d9; background:#0d1117; white-space:pre-wrap; word-break:break-word;
  "><code>You are a customer support agent for [Company]. Your role is to help
customers resolve issues with accounts, orders, and products.

## Identity
- Name: Aria
- Tone: Professional, empathetic, solution-focused
- Language: Match the user's language automatically

## Capabilities
- Answer questions about account management, billing, orders
- Look up order status via `get_order_status` tool
- Create support tickets via `create_ticket` tool
- Escalate to a human when confidence &lt; 0.72

## Constraints
- Never disclose internal pricing agreements
- Never commit outside standard policy
- Always confirm PII before sharing account data

## Escalation Triggers
- User requests human agent
- Confidence score &lt; 0.72
- Legal, compliance, or safety queries
- 3+ failed resolution attempts</code></pre>
</div>
```

Rules: dark terminal theme (`#0d1117`) for all system prompts/config. Always include copy button. Traffic-light dots are the only accepted terminal decoration. Escape HTML: `<` → `&lt;`, `>` → `&gt;`.

## Architecture Component Table

```html
<div style="overflow-x:auto; margin:var(--wiki-space-6) 0;">
  <table style="width:100%; border-collapse:collapse;
    font-size:var(--wiki-text-sm); font-family:var(--wiki-font-body);">
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
            Operational
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

Rules: headers uppercase, letter-spaced, muted. Status badges are pills with semantic color. Alternate row backgrounds (`var(--wiki-surface-2)` for even rows). Always wrap in `overflow-x:auto`. Numeric columns: `font-family: var(--wiki-font-mono)`, `text-align: right`.

## Step / Decision Pipeline

```html
<div style="margin:var(--wiki-space-6) 0;">
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
        Model classifies user messages into 14 intent categories via zero-shot
        classification prompt. Confidence threshold: 0.65.
      </p>
    </div>
  </div>
  <div style="width:2px; height:24px; background:var(--wiki-divider); margin-left:15px; margin-bottom:var(--wiki-space-1);"></div>
</div>
```

Rules: numbered circles are `--wiki-primary` / white text. Connector line 2px `--wiki-divider`, centered under the circle. Title `font-weight:500`, body size. Description muted + smaller.

## Changelog Table

```markdown
| Version | Date | Author | Change |
|---|---|---|---|
| v2.4 | Apr 2026 | @eng-team | Added sentiment-aware escalation routing |
| v2.3 | Mar 2026 | @ai-team | Upgraded to GPT-4o from GPT-4-turbo |
| v2.2 | Feb 2026 | @eng-team | Added Redis caching; P50 latency -40% |
| v2.1 | Jan 2026 | @pm-team | Extended Q&A bank from 45 to 120 entries |
| v2.0 | Dec 2025 | @eng-team | Initial production deployment |
```

Rules: reverse chronological (newest first). `@handle` format, not full names. Change description: active voice, past tense, under 12 words.
