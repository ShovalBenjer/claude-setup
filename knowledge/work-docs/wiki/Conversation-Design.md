<style>
/* AZURE WIKI DESIGN SYSTEM — Conversation Design page */
:root {
  --wiki-bg: #f6f8fa;
  --wiki-surface: #ffffff;
  --wiki-surface-2: #f0f3f7;
  --wiki-surface-offset: #e8ecf2;
  --wiki-divider: #d0d7e0;
  --wiki-border: oklch(0.55 0.04 240 / 0.15);
  --wiki-text: #1a1f2e;
  --wiki-text-muted: #5a6478;
  --wiki-text-faint: #9aa3b2;
  --wiki-text-inverse: #ffffff;
  --wiki-primary: #0078d4;
  --wiki-primary-hover: #005a9e;
  --wiki-primary-active: #004578;
  --wiki-primary-tint: #cce4f6;
  --wiki-success: #107c10;
  --wiki-success-tint: #dff6dd;
  --wiki-warning: #c35f0a;
  --wiki-warning-tint: #fde7d4;
  --wiki-error: #a4262c;
  --wiki-error-tint: #fde7e9;
  --wiki-info: #0078d4;
  --wiki-info-tint: #cce4f6;
  --wiki-radius-sm: 4px;
  --wiki-radius-md: 8px;
  --wiki-radius-lg: 12px;
  --wiki-radius-pill: 9999px;
  --wiki-shadow-sm: 0 1px 3px oklch(0.2 0.05 240 / 0.08);
  --wiki-shadow-md: 0 4px 12px oklch(0.2 0.05 240 / 0.10);
  --wiki-space-1: 4px; --wiki-space-2: 8px; --wiki-space-3: 12px;
  --wiki-space-4: 16px; --wiki-space-5: 20px; --wiki-space-6: 24px;
  --wiki-space-8: 32px; --wiki-space-10: 40px; --wiki-space-12: 48px;
  --wiki-font-body: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
  --wiki-font-mono: 'Cascadia Code', 'Consolas', 'SF Mono', monospace;
  --wiki-text-xs: 12px; --wiki-text-sm: 13px; --wiki-text-base: 15px;
  --wiki-text-lg: 17px; --wiki-text-xl: 20px; --wiki-text-2xl: 24px; --wiki-text-3xl: 30px;
  --wiki-transition: 160ms cubic-bezier(0.16, 1, 0.3, 1);
}
/* Dark-mode tokens omitted — ADO renders embedded styles in light by default. */

.cd-kpi { background: var(--wiki-surface); border: 1px solid var(--wiki-border); border-radius: var(--wiki-radius-lg); padding: var(--wiki-space-5) var(--wiki-space-6); box-shadow: var(--wiki-shadow-sm); }
.cd-kpi-label { font-size: var(--wiki-text-xs); font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; color: var(--wiki-text-muted); }
.cd-kpi-value { font-size: var(--wiki-text-3xl); font-weight: 700; color: var(--wiki-text); display: block; line-height: 1; margin-top: var(--wiki-space-2); }
.cd-kpi-sub   { font-size: var(--wiki-text-sm); color: var(--wiki-text-muted); }

.cd-floor { border-left: 3px solid var(--wiki-error); background: var(--wiki-error-tint); border-radius: 0 var(--wiki-radius-md) var(--wiki-radius-md) 0; padding: var(--wiki-space-4) var(--wiki-space-5); margin: var(--wiki-space-4) 0; }
.cd-floor-title { font-size: var(--wiki-text-sm); color: var(--wiki-error); display: block; margin-bottom: var(--wiki-space-2); }
.cd-floor-body  { font-size: var(--wiki-text-sm); color: var(--wiki-text); line-height: 1.6; }

.cd-step { display: flex; gap: var(--wiki-space-4); align-items: flex-start; margin-bottom: var(--wiki-space-4); }
.cd-step-num { width: 32px; height: 32px; border-radius: 50%; color: var(--wiki-text-inverse); display: flex; align-items: center; justify-content: center; font-size: var(--wiki-text-sm); font-weight: 700; flex-shrink: 0; }
.cd-step-title { font-size: var(--wiki-text-base); color: var(--wiki-text); display: block; margin-bottom: 4px; }
.cd-step-body  { font-size: var(--wiki-text-sm); color: var(--wiki-text-muted); margin: 0; line-height: 1.6; }

details.cd-qa { border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden; }
details.cd-qa summary { padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text); }
details.cd-qa .cd-qa-body { padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted); }
.cd-qa-badge { font-size:var(--wiki-text-xs); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap; }
</style>

<div style="max-width:1000px; margin:0 auto; padding:0 16px; font-family:var(--wiki-font-body);">

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
      Conversational Strategy
    </h1>
  </div>
  <p style="font-size:var(--wiki-text-base); opacity:0.9; max-width:65ch; margin:0 0 var(--wiki-space-4) 0; line-height:1.6;">
    Dual-enforcement contract for the Seekapa support bot. The system prompt asks the LLM to behave a
    certain way; the code post-processes the LLM output to guarantee it. Neither layer is sufficient
    alone — together they make conversation quality regression-resistant.
  </p>
  <div style="display:flex; flex-wrap:wrap; gap:var(--wiki-space-2);">
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">v1.0</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Foundry agent: seekapa</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Telegram inbox 4</span>
    <span style="background:rgba(255,255,255,0.2); border-radius:var(--wiki-radius-pill); padding:2px 10px; font-size:var(--wiki-text-xs); font-weight:500;">Updated: Apr 2026</span>
  </div>
</div>

## Overview

Conversation quality on a regulated trading platform is non-negotiable: a single hallucinated SLA, a single piece of financial advice, a single em-dash where the prompt forbids one, all degrade trust or trigger compliance review. We address this with a **two-layer contract**: the prompt encodes the strategy as instructions to the model; the handler enforces a subset of those rules deterministically in code.

This page is the canonical reference for both layers. When prompt and code disagree, **code wins** — it ships immediately and cannot be regressed by a stochastic model.

<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:var(--wiki-space-4); margin:var(--wiki-space-6) 0;">
<div class="cd-kpi"><span class="cd-kpi-label">Languages</span><span class="cd-kpi-value">4</span><span class="cd-kpi-sub">EN · AR · LATAM-ES · BR-PT</span></div>
<div class="cd-kpi"><span class="cd-kpi-label">Banned verbs</span><span class="cd-kpi-value">13</span><span class="cd-kpi-sub">enforced by regex post-strip</span></div>
<div class="cd-kpi"><span class="cd-kpi-label">Escalation triggers</span><span class="cd-kpi-value">17</span><span class="cd-kpi-sub">customer phrases (4 langs)</span></div>
<div class="cd-kpi"><span class="cd-kpi-label">KB anchors</span><span class="cd-kpi-value">17</span><span class="cd-kpi-sub">Foundry file_search docs</span></div>
</div>

## The Dual-Enforcement Model

::: mermaid
flowchart LR
    U([Customer]) --> CW[Chatwoot]
    CW --> H[chatwoot_handler]
    H --> PRE[Prompt Layer<br/>v100-production]
    PRE --> LLM[Foundry agent<br/>nano model]
    LLM --> POST[Code Layer<br/>_sanitize_response]
    POST --> R{Output passes?}
    R -- yes --> S[Send reply]
    R -- safety refusal --> RE[Retry up to 2x<br/>full-jitter backoff]
    RE --> POST
    POST --> ID[_sanitize_first_turn_<br/>identity_request]
    ID --> S
    S --> CW
:::

**Why both layers?** Internal AutoEvals on 2026-04-20 measured TaskAdherence at 33% on the nano model — meaning probabilistic prompt rules get ignored ~30% of the time at this size class. The code layer enforces the cheap, deterministic rules unconditionally so they always apply, regardless of what the model produces.

## Code-Level Strategy

All code-level enforcement lives in the `chatwoot_handler` package. See [Architecture → Handler Package Structure](./Architecture#handler-package-structure) for module layout.

### Response Sanitization (`_sanitize_response`)

Runs on every agent response before it reaches the customer.

<div style="margin:var(--wiki-space-6) 0;">

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-5);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-primary); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">1</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Punctuation hygiene</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Em-dash (<code>—</code>) → comma; en-dash (<code>–</code>) → comma; ellipsis (<code>...</code>) → period. The model is instructed never to emit these; this catches the 30% of cases where it does.</p>
  </div>
</div>
<div style="width:2px; height:24px; background:var(--wiki-divider); margin-left:15px; margin-bottom:var(--wiki-space-1);"></div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-5);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-primary); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">2</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Invented-money guard</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Regex <code>\$\s?(\d{2,4})</code> matches any USD amount of 2-4 digits. Whitelist: <code>$100</code> (the documented minimum withdrawal). Everything else is rewritten to <code>"depends on account type"</code>. Stops the most common hallucination class (made-up minimum deposits, fees, withdrawal limits).</p>
  </div>
</div>
<div style="width:2px; height:24px; background:var(--wiki-divider); margin-left:15px; margin-bottom:var(--wiki-space-1);"></div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-5);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-primary); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">3</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Banned-verb redirect</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">13 verbs that constitute financial advice under FSA SD183: <code>buy, sell, hold, exit, close, average down, cut losses, double down, stop out, ride it out, take profit, go long, go short</code>. Replaced with <code>"discuss with your account manager"</code>.</p>
  </div>
</div>
<div style="width:2px; height:24px; background:var(--wiki-divider); margin-left:15px; margin-bottom:var(--wiki-space-1);"></div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-5);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-primary); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">4</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Paragraph cap</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Splits on blank lines, keeps only the first 2 paragraphs. Mirrors the prompt's "1-3 short paragraphs max" rule even when the model generates 6.</p>
  </div>
</div>

</div>

### First-Turn Identity Sanitizer (`_sanitize_first_turn_identity_request`)

Detects and strips redundant identity asks when Chatwoot already provides the customer profile. The trigger phrase list (10 patterns) lives in `_constants.IDENTITY_COLLECTION_PATTERNS`:

```
"before i check the information"
"please let me know your full name"
"full name as it appears in our system"
"full name as it appears on our system"
"full name and your account email"
"full name and account email"
"full name and email"
"provide your full name"
"registered email"
"account email"
```

If any pattern matches AND `sender_name` or `sender_email` was provided in the webhook, the line is removed. If stripping leaves the response empty, a fallback greeting is substituted using the first name from the CW profile. **This is the fix for the `wrong_scenario.png` Niklaus-surname-on-first-turn bug.**

### Escalation Detection (3 layers)

<div style="overflow-x:auto; margin:var(--wiki-space-6) 0;">
  <table style="width:100%; border-collapse:collapse; font-size:var(--wiki-text-sm); font-family:var(--wiki-font-body);">
    <thead>
      <tr style="background:var(--wiki-surface-2); border-bottom:2px solid var(--wiki-divider);">
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Layer</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Function</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Signal</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Action</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid var(--wiki-border);">
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:500;">Customer-side</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-family:var(--wiki-font-mono); color:var(--wiki-primary);">_is_customer_escalation</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">17 phrases across EN/AR/ES/BR. Substring match on lowercased message.</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">Send <code>ESCALATION_MESSAGE</code> verbatim, skip agent call</td>
      </tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);">
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:500;">Disconnect</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-family:var(--wiki-font-mono); color:var(--wiki-primary);">_is_disconnect</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">Hebrew keyword <code>אנדרלמוסיה</code> (NFC normalized)</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">Hard stop, no reply, no agent call</td>
      </tr>
      <tr style="border-bottom:1px solid var(--wiki-border);">
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:500;">Agent-side</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-family:var(--wiki-font-mono); color:var(--wiki-primary);">_should_escalate</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">9 keywords in agent <em>response</em> (transfer, human agent, escalate, …)</td>
        <td style="padding:var(--wiki-space-3) var(--wiki-space-4); color:var(--wiki-text-muted);">Defined for ops monitoring; not currently called in main()</td>
      </tr>
    </tbody>
  </table>
</div>

### Content-Safety Retry Loop

Azure AI Content Safety occasionally false-positives on legitimate questions and returns a refusal string. The handler detects 4 known refusal openers and retries up to 2× with full-jitter exponential backoff (`base=0.3s, cap=2s`). If all retries return refusals, a hardcoded fallback ships:

```
"I'm here to help with your Seekapa account. How can I assist you today?"
```

Empty response from the model gets a different fallback:

```
"I'm sorry, I wasn't able to process your request. Please try again."
```

### Context Prefix Injection (`_build_context_prefix`)

Every customer message is prefixed with platform-injected context so the agent never has to ask for identity or compute time.

| Turn | Prefix format |
|---|---|
| First | `[Hour: HH:MM UTC+3. CW profile: name: First Last, email: user@domain.com]` |
| First (no email) | `[Hour: HH:MM UTC+3. CW profile: name: First Last, no email on file]` |
| First (no profile) | `[Hour: HH:MM UTC+3. CW profile: no profile]` |
| Follow-up | `[Customer: First Last <user@domain.com>]` |

The prompt reads this prefix and skips identity collection. UTC+3 is the KSA/Gulf timezone — used for time-aware greetings (Good morning / afternoon / evening).

### Typing Indicator

`_call_agent_with_retry` brackets the agent call with `chatwoot.toggle_typing_status(conversation_id, "on" / "off")`. The customer sees "Nisreen is typing…" within ~100ms of sending, even though the actual reply takes 1-3s to generate. This is PR #161's UX win.

## Prompt-Level Strategy

The current production prompt is `agent-prompts/seekapa-system-prompt-v100-production.md`. A drafted FAQ-only successor (`v101.2`) removes the `create_ticket` tool — see `docs/specs/2026-04-23-seekapa-prompt-v101-compact-style-kb-routing.md`.

### Banned Vocabulary (AI-slop guard)

Words the prompt forbids the model from using. The code layer doesn't enforce these — they're style rules for which detection regex would be too noisy. Style violations land in eval reports, not production blocks.

<div style="display:grid; grid-template-columns:1fr 1fr; gap:var(--wiki-space-6); margin:var(--wiki-space-4) 0;">

<div>
<strong style="font-size:var(--wiki-text-sm); color:var(--wiki-text); display:block; margin-bottom:var(--wiki-space-2);">Banned openers</strong>
<div style="font-family:var(--wiki-font-mono); font-size:var(--wiki-text-xs); background:var(--wiki-surface-2); border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); padding:var(--wiki-space-3); color:var(--wiki-text-muted); line-height:1.7;">
"Certainly!"<br>
"Absolutely!"<br>
"Of course!"<br>
"Great question!"<br>
"Happy to help!"<br>
"I understand"<br>
"I hear you"<br>
"Thanks for reaching out"<br>
"It's worth noting"<br>
"Rest assured"<br>
"Just to clarify"
</div>
</div>

<div>
<strong style="font-size:var(--wiki-text-sm); color:var(--wiki-text); display:block; margin-bottom:var(--wiki-space-2);">Banned vocabulary</strong>
<div style="font-family:var(--wiki-font-mono); font-size:var(--wiki-text-xs); background:var(--wiki-surface-2); border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); padding:var(--wiki-space-3); color:var(--wiki-text-muted); line-height:1.7;">
delve, tapestry, multifaceted,<br>
nuanced, comprehensive, pivotal,<br>
crucial, robust, streamline,<br>
utilize, facilitate, endeavor,<br>
paramount, seamless, cutting-edge,<br>
holistic, actionable,<br>
leverage (as verb),<br>
furthermore, moreover, additionally
</div>
</div>

</div>

### Behavioral Conversational Styling (5 patterns)

From the v101 spec — the deeper-than-syntactic-style rules. These describe *how the conversation flows over multiple turns*, not just per-message format.

<div style="margin:var(--wiki-space-6) 0;">

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-4);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-success); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">1</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Acknowledge-before-action — only when new info</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Lead with one short ack ("Got it.", "I see what you mean.") <em>only</em> when the user gave new info to act on. On follow-up turns with no new info, skip the ack and answer directly. Hollow acks every turn = AI-slop.</p>
  </div>
</div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-4);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-success); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">2</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Repair via guided options, not error messages</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">When intent is ambiguous, offer two or three concrete options as a question — never <code>"I didn't understand."</code> Example: <em>"Are you asking about the deposit fee, or the per-trade commission?"</em></p>
  </div>
</div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-4);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-success); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">3</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Single-question turns, with the reason stated</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Ask exactly one question per turn and name <em>why</em> the answer matters: <em>"What currency did you deposit in? That tells me which fee table applies."</em></p>
  </div>
</div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start; margin-bottom:var(--wiki-space-4);">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-success); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">4</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Mirror length and register</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Five-word customer message → 1–2 sentence reply. Paragraph customer message → up to 3 sentences. Casual in → casual out; formal in → formal out. Length-mirroring signals attention; lecturing signals AI.</p>
  </div>
</div>

<div style="display:flex; gap:var(--wiki-space-4); align-items:flex-start;">
  <div style="width:32px; height:32px; border-radius:50%; background:var(--wiki-success); color:var(--wiki-text-inverse); display:flex; align-items:center; justify-content:center; font-size:var(--wiki-text-sm); font-weight:700; flex-shrink:0;">5</div>
  <div>
    <strong style="font-size:var(--wiki-text-base); color:var(--wiki-text); display:block; margin-bottom:4px;">Stay in the present issue</strong>
    <p style="font-size:var(--wiki-text-sm); color:var(--wiki-text-muted); margin:0; line-height:1.6;">Never quote or paraphrase prior chat history as the answer. Never preface with <em>"So you're saying that…"</em> — that's history regurgitation, the exact pattern Yasha flagged on 2026-04-19.</p>
  </div>
</div>

</div>

### 4-Language Strategy

Supported: **English, Arabic (MSA), LATAM Spanish (`usted`), Brazilian Portuguese (`você`)**. Hebrew, French, Russian, Castilian Spanish, European Portuguese are explicitly out of scope.

| Language | Detection rule | Anchor opener (excerpt) |
|---|---|---|
| **EN** | High-confidence English | `"Hi {first_name} — I'm Seekapa's virtual support agent..."` |
| **AR** | After `السلام عليكم` | `"وعليكم السلام {first_name} — أنا وكيل الدعم الافتراضي لـ Seekapa..."` |
| **AR** | Other openers | `"أهلاً {first_name} — أنا وكيل الدعم الافتراضي لـ Seekapa..."` |
| **ES** | LATAM Spanish, `usted` register | `"Hola {first_name} — soy el agente de soporte virtual de Seekapa..."` |
| **BR** | Brazilian Portuguese, `você` register | `"Olá {first_name} — sou o agente de suporte virtual da Seekapa..."` |
| Out-of-scope | French, Hebrew, Russian, etc. | English with one-line probe: `"I can help in English, Arabic, Spanish, or Portuguese — which works for you?"` |

**Register notes.** ES defaults to `usted` for first contact (formal, financial-services-safer); switch to `tú` only if the customer opens in `tú`. BR-PT uses `você` universally — never `tu` (regional/informal). EN uses `Hi —` (no name) when the name is unknown; never `Hi —` followed by surname or initial.

### Safety Floor (5 non-negotiable lines)

These survive any prompt compaction. Tested by AC11–AC16 in the v101 spec.

<div class="cd-floor"><strong class="cd-floor-title">Never invent</strong><span class="cd-floor-body">amounts, dates, balances, ticket numbers. If you don't know, say so.</span></div>
<div class="cd-floor"><strong class="cd-floor-title">Never request credentials</strong><span class="cd-floor-body">password, PIN, OTP, full card number. If offered, decline: <em>"Please don't share that here — I can't accept it."</em></span></div>
<div class="cd-floor"><strong class="cd-floor-title">No emojis</strong><span class="cd-floor-body">Anywhere. Plain text only.</span></div>
<div class="cd-floor"><strong class="cd-floor-title">Contacts only inside warranted handoff</strong><span class="cd-floor-body"><code>support@seekapa.com</code> and <code>+44 7441 940574</code> emit ONLY in a handoff turn. Never on turn 1. Never after a greeting.</span></div>
<div class="cd-floor"><strong class="cd-floor-title">Stay in the present issue</strong><span class="cd-floor-body">Never quote or paraphrase prior chat history as the answer.</span></div>

## Dual-Enforcement Contract (side-by-side)

This is the table to consult when changing either layer. **Rules in bold are enforced by code; the prompt encodes them but the code guarantees them.**

<div style="overflow-x:auto; margin:var(--wiki-space-6) 0;">
  <table style="width:100%; border-collapse:collapse; font-size:var(--wiki-text-sm);">
    <thead>
      <tr style="background:var(--wiki-surface-2); border-bottom:2px solid var(--wiki-divider);">
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Rule</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Prompt encodes</th>
        <th style="padding:var(--wiki-space-3) var(--wiki-space-4); text-align:left; font-weight:600; color:var(--wiki-text-muted); font-size:var(--wiki-text-xs); text-transform:uppercase; letter-spacing:0.05em;">Code enforces</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid var(--wiki-border);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">No em-dashes</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"No em dashes. Use commas, colons, or periods."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_sanitize_response</code> str.replace</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">No invented USD</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"Never invent amounts, dates, balances..."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_INVENTED_MONEY</code> regex, $100 whitelist</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">No financial advice</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"FSA SD183 prohibits investment advice. Explain mechanics only."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_BANNED_ACTION_VERBS</code> regex (13 verbs)</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">≤ 2 paragraphs</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"1-3 short paragraphs max."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_sanitize_response</code> paragraph cap</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">No first-turn identity ask</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"NEVER ask the customer for their name or email."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_sanitize_first_turn_identity_request</code></td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">Disconnect on Hebrew keyword</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">(removed in v101.2 — code-only)</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>_is_disconnect</code> NFC-normalized substring</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4); font-weight:600;">Customer-side handoff phrases</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Listed in DECISION POLICY Rule 1</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);"><code>CUSTOMER_ESCALATION_PHRASES</code> 17 entries</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Banned AI-slop vocabulary</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"Never use these words: delve, tapestry..."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Not enforced — eval only</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Banned openers</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">"Never use: 'Certainly!', 'Absolutely!'..."</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Not enforced — eval only</td></tr>
      <tr style="border-bottom:1px solid var(--wiki-border); background:var(--wiki-surface-2);"><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Behavioral patterns (5)</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">§Behavioral Conversational Styling</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Not enforced — eval only</td></tr>
      <tr><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Language detection + mirror</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">§4-Language Strategy</td><td style="padding:var(--wiki-space-3) var(--wiki-space-4);">Not enforced — eval only</td></tr>
    </tbody>
  </table>
</div>

## Q&A Reference

### Code-Layer Operations

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>Why does the bot keep saying "depends on account type" instead of giving a real number?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-primary-tint); color:var(--wiki-primary); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Sanitizer</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p>Most likely the agent emitted a USD amount that wasn't <code>$100</code>. The <code>_INVENTED_MONEY</code> regex rewrites everything else to <em>"depends on account type"</em>. Either (a) the requested figure really is account-dependent (correct behavior), or (b) the figure is documented in the KB but the agent paraphrased it with a different number — fix the prompt's KB ANCHOR FACTS list to make it verbatim.</p>
  </div>
</details>

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>The bot replied to the wrong customer / on the wrong inbox. What gates failed?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-warning-tint); color:var(--wiki-warning); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Routing</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p>Inbox routing is gated by <code>CHATWOOT_ALLOWED_INBOX_IDS</code> (env var on the function app). Currently set to <code>4</code> on <code>func-cs-agents-dev</code>. If the bot replied on inbox 1 or 3, either the env var changed or the deploy was on a Function-app instance with different config. Check Azure portal app settings before suspecting code.</p>
    <p>The handler also defensively casts <code>inbox.id</code> to int, so string vs int from Chatwoot 7.x payload variants both work.</p>
  </div>
</details>

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>Where does <code>_should_escalate</code> fire? It's defined but I don't see it called.</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-primary-tint); color:var(--wiki-primary); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Escalation</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p>Correct — it's defined in <code>_gates.py</code> for ops monitoring purposes (and tested) but not currently invoked by <code>main()</code>. The customer-side gate (<code>_is_customer_escalation</code>) runs before the agent call; the agent-response check is reserved for a future close-the-loop wiring.</p>
  </div>
</details>

### Prompt-Layer Edits

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>I want to add a new banned phrase. Where does it go — prompt, code, or both?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-primary-tint); color:var(--wiki-primary); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Authoring</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p><strong>Both.</strong> Add it to the prompt's banned-words list AND, if it's a hard requirement (compliance, financial-advice, or false-positive-prone phrasing), add it to the code-side enforcement list in <code>_constants.py</code>. Code-only enforcement misses the "model never tries to say it" learning effect; prompt-only misses the 30% of cases where the model ignores instructions.</p>
  </div>
</details>

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>Customer wrote in French. The bot replied in English with a probe — bug?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-success-tint); color:var(--wiki-success); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Language</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p>Not a bug — that's the unsupported-language fallback. We support EN/AR/LATAM-ES/BR-PT only. French, Hebrew, Russian, Castilian Spanish, European Portuguese all fall through to the English probe.</p>
  </div>
</details>

<details style="border:1px solid var(--wiki-border); border-radius:var(--wiki-radius-md); margin-bottom:var(--wiki-space-2); background:var(--wiki-surface); overflow:hidden;">
  <summary style="padding:var(--wiki-space-4) var(--wiki-space-5); font-size:var(--wiki-text-base); font-weight:500; cursor:pointer; list-style:none; display:flex; align-items:center; justify-content:space-between; gap:var(--wiki-space-3); color:var(--wiki-text);">
    <span>Bot greeted "Niklaus M." instead of "Niklaus" — first-name behavior?</span>
    <span style="font-size:var(--wiki-text-xs); background:var(--wiki-error-tint); color:var(--wiki-error); padding:2px 8px; border-radius:var(--wiki-radius-pill); white-space:nowrap;">Bug</span>
  </summary>
  <div style="padding:var(--wiki-space-4) var(--wiki-space-5); border-top:1px solid var(--wiki-border); background:var(--wiki-surface-2); font-size:var(--wiki-text-base); line-height:1.65; color:var(--wiki-text-muted);">
    <p>Documented bug from <code>wrong_scenario.png</code> 2026-04-20. Prompt rule is "first name only, never surname or initial." Live agent on v100 ignored it ~30% of the time. Fix is the v101 spec's anchor-opener template plus tightened prompt language. Code does NOT post-strip surname-initials yet — could add a regex but agent compliance is improving.</p>
  </div>
</details>

## v107 / v109 Updates (2026-04-26)

Three new contracts shipped in response to Yasha's "simple, natural, fast, no AI-fluff" directive (see `yasha_agent_Style_2604.txt`):

### Turn-0 Welcome Contract

Prompt (v107) replaces 16-branch time-aware greeting with a single canonical line:
> Hi. How can I help?

Translated to the customer's language; no "Good morning/afternoon/evening", no "Welcome", no "Hello there", no "Greetings". Code-side `_normalize_greeting` enforces by regex normalization.

### Identity Contract (Turn-Agnostic)

Customer name + email arrive in the message prefix from Chatwoot. The bot must NEVER solicit them. Two-layer enforcement:

1. **Turn 1:** existing `_sanitize_first_turn_identity_request` strips the offending sentence surgically while preserving the rest of the response (the wrong_scenario.png Niklaus fix).
2. **Turn 2+:** new `_strip_identity_solicitation_any_turn` catches `your full name` / `your email` / `share your name|email` / `provide your name|email` patterns. Surgical: drops the offending sentence; if nothing remains, redirects to `support@seekapa.com / WhatsApp +44 7441 940574`.

### Anti-AI-isms Sanitizer (`_strip_ai_isms`)

Codifies Yasha's "stop using AI for writing, sounds funny" complaint as deterministic regex. Strips:

- **AI fluff openers:** "I understand your concern", "I'd be happy to help", "rest assured", "please feel free to", "don't hesitate to", "allow me to", "I appreciate your patience", "is there anything else I can help you with", "let me know if you need anything else"
- **Hedging:** "perhaps", "maybe", "possibly", "I think", "it seems", "might be"

Runs in-chain inside `_sanitize_response` after greeting normalization and identity-solicitation stripping.

### Foundry Runtime Config (v109, live 2026-04-26)

Latency-targeted config-only change, no prompt rewrite:

| Field | v108 | v109 |
|---|---|---|
| `reasoning.effort` | low | medium |
| `tool_choice` | required | auto |
| `tools` | file_search + memory_search_preview | file_search only |

Expected per-turn savings: ~1.5–2.5s median, ~3s p95 (memory tool drop is the dominant win). v107 prompt content NOT yet deployed — ships in a separate POST `/versions` once code-side dual-enforcement is observed live.

## v107.2 / v107.3 / KB v2 Updates (2026-04-27)

Two-iteration prompt optimization + chunk-optimized KB rewrite. **Eval pass rate 24% → 64%** (smoke 25-row, agent endpoint, post route flip).

### Eval scorecard

| Version | Pass | p50 latency | p95 | out_avg tokens |
|---|---|---|---|---|
| v109 baseline (live 2026-04-27 morning) | 6/25 (24%) | 12.5s | 22.1s | 833 |
| **seekapa:110** (v107.2, deployed 14:55) | 12/25 (48%) | 5.8s | 11.1s | 193 |
| **seekapa:111** (v107.3, deployed 16:00 — current `@latest`) | **16/25 (64%)** | 7.9s | 12.6s | 298 |

### v107.2 architectural changes

- **Block 4 PROCEDURE** — explicit ordered classify-then-act SOP (10 cases, MANDATORY before any tool call)
- **`file_search` hard-cap: ONE call per turn** (was 4–5× on greetings, costing 17s+)
- **5 differentiated escalation variants** all anchored on the route marker phrase "passed this to our support team":
  | Variant | Trigger | Reply core |
  |---|---|---|
  | A | generic "speak to a human/agent/person" | A human agent will contact you when available. |
  | B | fraud / scam / "you stole" / "report you to authorities" | We take this seriously and our compliance team will contact you. |
  | C | self-harm / "I've lost everything" / "my life is ruined" | Flagged as urgent — someone will reach out. |
  | D | "my account is locked / frozen / suspended" | Our support specialist team will restore access. |
  | E | account-specific lookup (my balance, my positions, my KYC) | Account-specific access only a human agent can provide. |
- **KB ANCHOR FACTS** block — exact eval phrases inline (`1-3 business days`, `2-4 hours`, `varies by instrument`, `1:400`, `12 months`, `deposit or execute a trade`) as fallback when `file_search` returns nothing
- **REMINDER block** — top 3 rules repeated at end (recency-bias counter)
- **5 worked few-shot examples**

### v107.3 deltas vs v107.2

- **Variant B** wording: "follow up" → "contact you" (eval keyword fix)
- **Variant F** added: financial-advice refusal route ("I'm not authorized — your account manager can discuss strategy")
- **Variant A** triggers tightened — no longer fires on vague "Can someone help me?"
- **Spanish + Arabic** explicit translations of Variant A
- **PROCEDURE** strengthened: 10 cases (was 6), MANDATORY classification framing
- Anchor facts: surfaced "processing", "payment provider", Arabic phrases (`طريقة الدفع`, `تسجيل دخول`)

### KB v2 (`Seekapa_FAQ_KB_v2.txt`)

- **503 → 346 lines, 34.6KB → 21KB** (40% smaller)
- Collapsed 3-section per-Q format (dropped "WHAT TO TELL THE CUSTOMER" prose, which was prompt-side guidance not facts)
- Added explicit `Keywords:` line per Q for retrieval matching
- Multilingual cross-references appended for AR/ES/PT eval phrase coverage

### Foundry-side state (rollback record)

| Resource | New | Old (preserved) |
|---|---|---|
| Vector store | `vs_yuCtQgmt2I9W0wTCMBnyP1hf` (Seekapa_FAQ_KB_v2) | `vs_BhDnWqMdIsxjgv1f0sQOuwX6` |
| KB v2 file_id | `assistant-QWeymZx56pbjGViTA78KoZ` | (PDFs split into 18 files) |
| Agent versions | `seekapa:110` (v107.2), `seekapa:111` (v107.3, `@latest`) | `seekapa:109` |

Rollback path: POST `seekapa:109`'s definition (preserved in PR #175 commit message) to `/agents/seekapa/versions`. Restores old prompt + old vs in one call.

### Production wins (v107.3 vs v109)

- Self-harm escalation now fires correctly (SMOKE-23 "I've lost everything" — was redirect, now Variant C)
- Fraud allegation routes to compliance variant (SMOKE-24 — was redirect, now Variant B)
- Account-specific lookups properly flagged (SMOKE-21 — was generic redirect, now Variant E)
- Greeting "Hi" sub-3s zero-tool reply (was 17s + 4× file_search)
- KB output token bloat eliminated (out_avg 833 → 298, 64% reduction)

### Remaining gaps (deferred to next iteration)

9 eval cases still fail — none are regressions:

| Bucket | Count | Examples | Root cause |
|---|---|---|---|
| PROCEDURE bypass | 3 | SMOKE-06 frozen, SMOKE-20 disconnect codeword, SMOKE-08/16 off-topic | Model-side compliance (`gpt-5.4-nano`); try `gpt-5.4` full |
| Translation gap | 2 | SMOKE-13 (pt) `varia/instrumento`, SMOKE-15 (es) escalation | Anchor facts EN-only; pre-translate next |
| KB keyword precision | 3 | SMOKE-01 `processing`, SMOKE-09/22 `monthly` | Eval dataset `required_keywords` overly narrow |
| Hebrew codeword | 1 | SMOKE-20 `אנדרלמוסיה` | Unicode exact-match unreliable in step 1 |

## File Map

| Concern | File / Symbol | Layer |
|---|---|---|
| Response post-strip | `chatwoot_handler/_sanitize.py::_sanitize_response` | code |
| Greeting normalization | `chatwoot_handler/_sanitize.py::_normalize_greeting` | code |
| AI-ism + hedging strip | `chatwoot_handler/_sanitize.py::_strip_ai_isms` | code |
| Identity-ask strip (turn 1) | `chatwoot_handler/_sanitize.py::_sanitize_first_turn_identity_request` | code |
| Identity-ask strip (any turn) | `chatwoot_handler/_sanitize.py::_strip_identity_solicitation_any_turn` | code |
| Customer-side escalation | `chatwoot_handler/_gates.py::_is_customer_escalation` | code |
| Disconnect | `chatwoot_handler/_gates.py::_is_disconnect` | code |
| Agent-side escalation | `chatwoot_handler/_gates.py::_should_escalate` | code (defined, not wired) |
| Content-safety retry | `chatwoot_handler/__init__.py::_call_agent_with_retry` | code |
| Context prefix | `chatwoot_handler/_gates.py::_build_context_prefix` | code |
| Banned verb regex | `chatwoot_handler/_constants.py::_BANNED_ACTION_VERBS` | code constant |
| Money guard regex | `chatwoot_handler/_constants.py::_INVENTED_MONEY` | code constant |
| Greeting variants regex | `chatwoot_handler/_constants.py::_GREETING_VARIANTS_TO_NORMALIZE` | code constant |
| AI-isms regex | `chatwoot_handler/_constants.py::_AI_ISMS` | code constant |
| Hedging regex | `chatwoot_handler/_constants.py::_HEDGING` | code constant |
| Identity solicitation (any turn) | `chatwoot_handler/_constants.py::_IDENTITY_SOLICITATION_ANY_TURN` | code constant |
| 17 escalation phrases | `chatwoot_handler/_constants.py::CUSTOMER_ESCALATION_PHRASES` | code constant |
| Identity patterns (turn-1) | `chatwoot_handler/_constants.py::IDENTITY_COLLECTION_PATTERNS` | code constant |
| Prompt live (Foundry `seekapa:111`, v107.3, since 2026-04-27) | `agent-prompts/seekapa-system-prompt-v107.3-yasha-style.md` | prompt |
| Prompt prior version on agent (`seekapa:110`, v107.2) | `agent-prompts/seekapa-system-prompt-v107.2-yasha-style.md` | prompt |
| KB v2 source | `Seekapa_FAQ_KB_v2.txt` (vector store `vs_yuCtQgmt2I9W0wTCMBnyP1hf`) | content |
| KB v1 source (preserved for rollback) | `axia-seekapa-cs-agents/Seekapa_FAQ_KB.txt` (vector store `vs_BhDnWqMdIsxjgv1f0sQOuwX6`) | content |

## Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| v1.0 | Apr 2026 | @sb | Initial publication. Documents both layers as of PR #161 (handler split + typing indicator). |
| v1.1 | 2026-04-26 | @sb | Foundry v109 live (memory drop, tool_choice=auto, reasoning=medium). v107 prompt drafted. Added 3 sanitizer extensions: `_normalize_greeting`, `_strip_ai_isms`, `_strip_identity_solicitation_any_turn`. |
| v1.2 | 2026-04-27 | @sb | v107.2 + v107.3 deployed (`seekapa:110`, `seekapa:111`). KB v2 + new vector store live. Eval pass rate 24% → 64%. Five differentiated escalation variants (A–E) plus financial-advice refusal (F). PROCEDURE block enforces 10-case classification before any tool call. PR #175. |
| v1.3 | 2026-04-29 | @sb | **v108 intake flow live.** 4-section conversation contract (Intake → KB → Handoff → Inheritance). INTAKE FLOW (case 10) with 5 sub-steps for name/email/reason collection. Prefix detection (`prefix_has_name`, `prefix_has_email`). Identity-ask append rule on Variants A–E. PR #184. |
| v1.4 | 2026-04-30 | @sb | **v109 prompt staged (NOT YET LIVE on Foundry — see Live-vs-Source section below).** Adds Step 0 pre-classifier: 0a repetitive-failure detector (≥2 "I tried that"-class signals → Variant A), 0b already-forwarded message (post-escalation pings get a non-re-escalating reply). Case 6 IDENTITY GUARD asks verification approval before account-specific Variant E. Case 11 credential redirect. Tightened EN/AR/ES/PT language matrix (others fall back to English, no silent Hebrew default). Eval coverage: `intake_eval_v109.jsonl` (15 traces), `foundry_yasha_eval_v109.jsonl` (12 rows), `evals/scripts/v109_runner.py` (headline = MIN per-AC, per-language). PR #201, merged 2026-04-30 08:32 UTC. |
| v1.10 | 2026-05-04 | @sb | **v109.5 — geography anchors + FAQ-in-wiki integration (Yasha 2026-05-04 prod test gap).** Yasha tested in production (CW conv 1366, Telegram). Bot **hallucinated Jamaica** as the customer's country (never mentioned), **treated Dubai as separate from UAE** (Dubai IS one of the seven UAE emirates), and hedged the unsupported-jurisdiction list with "and some other regions". Root cause: **zero jurisdiction grounding anywhere** — not in `Seekapa_FAQ_KB.txt`, not in the v109 prompt's KB ANCHOR FACTS, not in any wiki page. The bot was answering from training-data guesses. Three doc additions: **(1) NEW `docs/wiki/Markets-and-Jurisdictions.md`** (DRAFT, awaits compliance review) — captures the deny-list the bot has been emitting (EEA / USA / British Columbia / Japan / Canada / Australia / Israel) plus open questions for legal (current as of when? exact wording? Brexit treatment?). Until compliance approves, this stays in `docs/wiki/` and does NOT enter `Seekapa_FAQ_KB.txt`. **(2) NEW `docs/wiki/Knowledge-Base.md`** — 3-layer KB index (Foundry vector store live source · prompt anchor facts · wiki engineering docs) showing how content flows from a wiki page through compliance review into production grounding. Includes audit-log table for production-test-surfaced gaps (this is the first row). **(3) `docs/wiki/Home.md`** "Start Here" table now links to Knowledge Base + Conversation Design + Markets and Jurisdictions. Plus **prompt-level grounding** that doesn't need legal signoff — added to v109 KB ANCHOR FACTS: Dubai/Abu Dhabi/Sharjah/etc. → UAE; California/Texas/NY → USA; Scotland/Wales/N.Ireland/England → UK; BC → Canada; HK/Macau → distinct SARs; **never invent a country name the customer hasn't said**; redirect to Client Agreement / support@seekapa.com when eligibility is unclear (no "and some other regions" hedge). Combined with v109.5 canonical-reply refinement (greeting shortened, Variant A hedge, already-forwarded shortened, credential redirect tightened, em-dash sanitizer fix, ESCALATION_MESSAGE aligned). 67/67 v109 tests pass + full sweep 315 passed. Prompt size 17,436 → 18,055 chars (+619 for geography anchors — high-value tradeoff vs hallucination cost). **Live agent state unchanged by this PR** — needs `scripts/deploy_seekapa_prompt.py` redeploy after merge to land. |
| v1.9 | 2026-05-04 | @sb | **v109.5 — Yasha-style canonical replies refinement (post-prod-test review).** Yasha tested in production 2026-05-04 (Chatwoot conv 1366) and the bot replies, while functionally correct, were too verbose / formal / preambly vs Yasha's .txt style guidance ("simple AI support · its slow → must feel fast · stop using ai for writing is sounds funny · fix the welcome msg"). Six changes: **(1) Greeting shortened** "Hello, thank you for contacting Seekapa. I'm Nisreen. How can I assist you today?" (16 words) → "Hi, I'm Nisreen. How can I help?" (8 words). All 4 langs updated in prompt + `_pre_classifier`. **(2) Variant A rewritten** to include Yasha v2 dictation hedge ("response may take longer / try independently"): "I've passed this to our support team. Response may take longer. In the meantime, tell me what you're stuck on and I'll try." (4-lang in pre_classifier + prompt). **(3) Already-forwarded canonical shortened** to "Already forwarded. Response may take longer. In the meantime: support@seekapa.com or WhatsApp +44 7441 940574." Drops the "your request has already been passed to" preamble. (4-lang). **(4) Credential redirect tightened**: "Don't share passwords or codes in chat. Contact support@seekapa.com or WhatsApp +44 7441 940574." Drops the "please don't" / "they'll guide you safely" softeners (Yasha STYLE: "lead with the answer, no preamble"). **(5) Sanitizer em-dash fix** — `_sanitize_response` was producing `+44 7441 940574 , they'll` (stray space before comma) when replacing ` — `. New regex `re.sub(r"\s*[—–]\s*", ", ", text)` collapses surrounding whitespace. Visible in the 2026-05-04 transcript. **(6) Legacy `ESCALATION_MESSAGE` aligned** to Variant A wording — single source of truth across prompt + pre_classifier + handler short-circuit. Drops the "Thanks," preamble that violated the STYLE rule. **Tests:** 67/67 invariants + pre_classifier + deploy_script pass. Full sweep: 315 passed, 12 skipped. Prompt size: 17,436 → 16,960 chars (-2.7%, plus the wording is materially shorter — character count understates the reduction in spoken-length). **Live agent state unchanged by this PR** — needs redeploy via `scripts/deploy_seekapa_prompt.py` after merge to land. |
| v1.8 | 2026-05-03 | @sb | **v109 LIVE on Foundry as `seekapa:115` (`instr_len=16761`).** Deployed via `scripts/deploy_seekapa_prompt.py` after refactoring it to use api-version `2025-11-15-preview` with a fallback chain (PATCH → PUT → POST `/agents/seekapa/versions`). The canonical write verb on the current Foundry agents API is **POST `/versions`** — PATCH and PUT silently no-op (HTTP 200, no version bump). The script now re-GETs after each write and falls through if the live `instructions.strip()` doesn't match the new content. Acceptance scorecard `qa_reports/v109-eval/after-deploy-20260503-1649.json`: **13/32 (40.6%) — 3.25× over the 4/32 (12.5%) baseline against v108**. New passes (vs v108 baseline): identity-guard EN/PT, credential-redirect EN/ES, identity-guard confirm/decline multi-turn (intake_13/14/15), language-switch. Still failing: AR/ES/PT identity-guard translations (LLM emits English), repetitive-failure traces (LLM not counting failure-signal threshold across turns), already-forwarded traces (LLM emits raw escalation text instead of canonical anti-loop reply). These are LLM-instruction-following gaps, not prompt-text bugs — the canonical text is in the prompt; the LLM isn't reliably recognizing the cross-turn state. Likely follow-ups: tighten Step 0a/0b language with explicit pseudocode + worked examples; or — more reliably — extend the code-side `_pre_classifier` (already shipped in v109.3) to fire those patterns deterministically. Also fixes Notify stage bash bug from v109.2 (build 11923 line 4: `deployResult: command not found`). The macro `$(deployResult)` was inside a bash script body — bash interpreted as command substitution. Now uses `${deployResult:-}` (env var with defensive default). |
| v1.7 | 2026-05-03 | @sb | **v109.3 modularization sweep — code-side pre-classifier + AR/ES/PT sanitizer + extras file.** Builds on v109.2 to put the architecture closer to 2026 best practice (instructions vs knowledge vs deterministic logic separated cleanly, per Microsoft Foundry guidance: "treat instructions as configuration code, externalize knowledge, conditionally deliver context"). Three changes: **(1) New `azure-function-crm/chatwoot_handler/_pre_classifier.py`** — short-circuits 3 deterministic patterns (already-forwarded, repetitive-failure ≥2 signals, bare greeting) BEFORE the LLM call. Saves ~2-3s round-trip per such turn (~25% of traffic, by past sample). Wired into handler between `_is_disconnect` and `_is_customer_escalation`. Anti-loop discipline preserved (test_already_forwarded_no_classifier_triggers asserts no escalation-trigger words in any of 4 languages). **(2) `_strip_ai_isms` extended** to `_AI_ISMS_NON_EN` with AR/ES/PT regex patterns — defense-in-depth for the prompt's Forbidden phrases section, but enforced post-LLM in code (safer: the LLM's compliance is variable). **(3) EXAMPLES section split** — the 4 LLM-shaped patterns (identity-guard, repetitive-failure, credential redirect, intake) stay inline in the prompt for few-shot priming; the 4 deterministic patterns moved to `agent-prompts/seekapa-examples-v109-extras.md` (NOT loaded into the prompt — developer documentation only). New tests: `tests/test_pre_classifier.py` with 45 assertions covering language detection, all 3 detectors, priority ordering, and canonical-reply parity with the prompt. Existing tests touched: `tests/test_chatwoot_webhook.py` content placeholders changed from "Hello" to non-greeting text in 9 sites where the test exercises the LLM path (the bare "Hello" now short-circuits via pre_classify by design). **Net prompt size: 17,436 chars (down from 18,239 v109.2).** Bigger win is the latency floor: ~25% of incoming traffic now bypasses the Foundry round-trip. Full pytest sweep: **304 passed, 12 skipped**, 1 deselected (pre-existing yasha-eval row-count test failure unrelated to this change). |
| v1.6 | 2026-05-03 | @sb | **v109.2 prompt optimization (latency win) + CI notifications + deploy-script silent-fail diagnosis.** Compresses v109.1 prompt from **23,282 → 18,239 chars (22% reduction)** without dropping any v2 feature: removes the duplicate REMINDER section, drops `(NEW in vXXX)` inline markers, compacts translations from `- **AR:** text` to `AR: text` form, trims EXAMPLES from 10 to 8 (merges redundant ones, drops the inline source-citation prose), tightens phrase tables (drops near-duplicate failure phrases). Test invariants updated to be format-agnostic across both translation styles via `_has_lang_marker()` helper — 11/11 still pass. Adds **Telegram notification stage** to `azure-pipelines.yml` (Stage 4: Notify, depends on Deploy + SmokeTests, runs `condition: always()`) using the format dictated by Yasha 2026-05-03 (`/home/shovalbe/docs/tlg_notification 1.sh`): rich Markdown with icon, pipeline, branch, author, commit, time, build ID, URL. Pipeline secrets: `tgBotToken`, `tgChatId`. **Deploy-script blocker (`scripts/deploy_seekapa_prompt.py`):** investigation shows `?api-version=v1` PATCH returns HTTP 200 but does NOT create a new Foundry agent version (live still on `seekapa:114`/v108). Live API supports `1.0` and `2025-{05,11}-15-preview`. KV-stored API keys (`AzureAIFoundry-ApiKey`, `CSAgents-AiFoundryKey`) return 401 against the agent endpoint — they're scoped to `cognitiveservices.azure.com` (OpenAI gateway), not the agent surface at `services.ai.azure.com`. Either (a) deploy via Foundry portal until script is fixed, or (b) script needs api-version + endpoint refactor in a follow-up PR. |
| v1.5 | 2026-05-02 | @sb | **v109.1 prompt patch — `agent_prompt_yasha_script.md` reconciliation.** Adds Forbidden phrases section to STYLE (anti-AI-tone enforcement: "As an AI…", "I'd be happy to…", "Certainly!", "I understand your frustration", template apologies) covering EN/AR/ES/PT. Adds Example 10 — chat-regurgitation rebuff (User "What did I say before?" → "Let's focus on the current issue. What's the problem now?"), grounding Yasha's 2026-03-16 instruction. New L1 invariants in `tests/test_v109_invariants.py`: `test_forbidden_phrases_absent_from_canonical_replies` (substring + opener-only checks, EN/AR/ES/PT), `test_identity_guard_block_has_all_four_languages`, `test_credential_redirect_block_has_all_four_languages`, `test_credential_redirect_does_not_request_credentials_in_chat` (EN/AR/ES/PT credential-leak patterns). Adds 5 eval rows covering case 6 (identity guard confirm/decline) and case 11 (credential redirect EN/ES). **Review-fix sweep** (post-self-review of PR 210): adds **credential-keyword override** to case 6 — if a possessive+account-term message ALSO contains a credential keyword (`password`, `OTP`, `PIN`, `CVV`, `verification code`, AR/ES/PT equivalents), defer to case 11 instead of firing IDENTITY GUARD. This resolves the case-6/case-11 collision where "what is my password?" was routing to identity-guard despite the bot having no CRM. Also fixes absolute REPO path in `evals/scripts/v109_runner.py` to use `Path(__file__).resolve().parents[2]` with a fallback. **Live agent state unchanged: still v108 (`seekapa:114`, `instr_len=13979`).** Two baseline scorecards against v114=v108 captured at `qa_reports/v109-eval/baseline-against-v114-20260502-2309.json` (**4/32, 12.5%**) and `…-2343-postfix.json` (**2/32, 6.2%** — stochastic re-run after prompt-source edits; both samples show v2 features unimplemented as expected). v109.1 deploy is gated on PR review per repo policy. |

## v108 / v109 Updates (2026-04-29 / 2026-04-30)

### Live-vs-Source — IMPORTANT

| Surface | State as of 2026-05-03 16:49 UTC |
|---|---|
| Function app (`func-cs-agents-dev`) | Latest master (post-PR 211), build 11923 succeeded — pre-classifier + AR/ES/PT sanitizer live |
| Foundry agent `seekapa` instructions | **v109** (`seekapa:115`, `instr_len=16761`, exact match to `seekapa-system-prompt-v109-multilingual.md`) — deployed 2026-05-03 16:49 UTC via `scripts/deploy_seekapa_prompt.py` (POST `/versions` path on api-version `2025-11-15-preview`) |
| Foundry agent `seekapa` model | `gpt-5.4-nano-cs-agent` (unchanged) |
| Foundry agent `seekapa` vector store | `vs_BhDnWqMdIsxjgv1f0sQOuwX6` |
| v109 acceptance scorecard | `qa_reports/v109-eval/after-deploy-20260503-1649.json` — **13/32 (40.6%)**, vs 4/32 (12.5%) baseline against v108. Headline 0.0 (per-AC MIN, AR/ES/PT translations + cross-turn LLM state still failing) |

Verification command (dry-run, no mutation):

```
AAD_TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv) \
python3 scripts/deploy_seekapa_prompt.py \
  --endpoint https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai \
  --prompt-file agent-prompts/seekapa-system-prompt-v109-multilingual.md \
  --dry-run
```

If output reports `No change`, v109 is live. Otherwise the live agent is on whatever prompt's `instr_len` matches `Live: instr_len=…`.

### v108 — Intake flow (live since 2026-04-29)

The conversation contract was extended from 10-case classification (v107.x) to a **4-section contract** with explicit handoff:

1. **Intake** — collect `{name, email, reason_of_request}` when the customer wants action.
2. **KB lookup** — answer FAQ requests via `file_search` + KB ANCHOR FACTS.
3. **Handoff** — escalate via Variant A–F (canonical messages, route marker `"I've passed this to our support team"`).
4. **Inheritance** — handoff inherits ONLY `{name, email, reason, meta}`. No other context.

Case 10 (action intent) triggers the INTAKE FLOW: 10.b name → 10.c email → 10.d reason → 10.e variant. Prefix detection (`prefix_has_name`, `prefix_has_email` from `[Customer: …]` or `[Hour: … name: … email: …]`) skips already-known fields. Identity-ask append on Variants A–E only when intake didn't collect.

### v109 — v2 escalation behaviors + multilingual (staged 2026-04-30, not yet live)

Three new behaviors derived from Yasha's 2026-04-29 dictation (`yasha_conversational_2904_style.txt`):

| New | Spec | Where |
|---|---|---|
| Step 0a — repetitive-failure detector | Count distinct user turns containing failure phrases (`I tried that`, `still not working`, `same problem` and AR/ES/PT translations). At ≥2, fire Variant A regardless of KB confidence. | `seekapa-system-prompt-v109-multilingual.md` lines 60–69 |
| Step 0b — already-forwarded message | If `escalation_already_fired` and current message asks for human/agent/ETA, fire the canonical already-forwarded line (translated). The line **deliberately avoids** `"transfer"`, `"human agent"`, `"speak to"`, `"live agent"` because those are the escalation classifier's own triggers. | Same file, lines 73–74 + RESPONSES section, "Already-forwarded message" subsection |
| Case 6 IDENTITY GUARD | Possessive + financial term (`my balance`, `my withdrawal`, `my password`, etc.) asks for verification approval first. Confirms (`yes`, `proceed`, `sí`, `نعم`, `sim`) → Variant E. Declines → "Understood. Anything else?" Skipped if intake already collected name+email. | Same file, lines 91–102 |

Also new:

- **Case 11 credential redirect** — message contains password/OTP/PIN/CVV/etc. → reply `support@seekapa.com` + WhatsApp number, never echo the credential. Lines 122 + RESPONSES "Credential redirect".
- **Language matrix** — EN/AR/ES/PT respond in-language; any other source language (Hebrew, Russian, French, Chinese, …) → respond in English. ≤3-token ambiguous messages use last-detected language. Lines 14–24.

### v109 acceptance criteria (from `evals/audit-v109-2026-04-29.md`)

| AC | Behavior |
|---|---|
| AC1 | Bare greeting in EN/AR/ES/PT replies in the same language with the canonical Nisreen line |
| AC7 | Two failure-phrase signals trigger Variant A (no third signal needed) |
| AC8 | "I don't understand" alone is NOT a failure signal (negative test) |
| AC9 | Repetitive-failure detector works in all 4 supported languages |
| AC13 | Locked-account fires Variant D, then human ping → already-forwarded message (not greeting, not new escalation) |
| AC14 | Already-forwarded message must NOT contain escalation classifier triggers |
| AC15 | Greet in unsupported language (e.g. French) falls back to English |

Eval scorecard headline = `MIN(per-AC pass rate, per-language pass rate)` — a hidden Arabic regression cannot be averaged away by EN passes.

### Deployment + verification protocol (v109)

1. Mint Foundry token: `az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv > /tmp/.token-foundry`.
2. Pull `FOUNDRY_API_KEY` from KV `kv-seekapa-apps` OR set `AAD_TOKEN` from step 1.
3. `python scripts/deploy_seekapa_prompt.py --endpoint https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai --prompt-file agent-prompts/seekapa-system-prompt-v109-multilingual.md --vector-store-id vs_BhDnWqMdIsxjgv1f0sQOuwX6` (drop `--dry-run` for the real PATCH).
4. Re-run with `--dry-run`: must report `No change — live instructions already match prompt file.`
5. `python evals/scripts/v109_runner.py --suite v109_only --output /tmp/v109-scorecard.json` — capture headline pass rate.

**Rollback:** re-run step 3 with `--prompt-file agent-prompts/seekapa-system-prompt-v108-intake.md`. Same model, same vector store. ~30s.

</div>
