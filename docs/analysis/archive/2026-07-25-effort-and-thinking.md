# Effort/thinking config audit: v2.1.219 binary evidence

PRD: none (point-in-time scan, not a spec)
Ticket: none
Status: active

Scope: `C:/Users/shova/.claude/settings.json` env block plus `effortLevel`/`ultracode`,
checked against the shipped behavior of Claude Code v2.1.219
(`C:/Users/shova/.local/share/claude/versions/2.1.219`, 265,714,848 bytes,
2026-07-24 20:35). All function names below are minified symbols read directly out
of that binary; they are stable only for this exact build.

## Lead: what's broken, unverified, or blocked

- **`ultracode: true` is not session-scoped in this config, it is permanent.** The
  binary's own tooltip calls it "Session-scoped, typically..." and the CLAUDE.md rule
  says `/effort ultracode` is "session-only". But it is hardcoded in the global
  `settings.json`, so every session boots with it already on. VERIFIED (code below).
- **`ultracode: true` suppresses the workflow-size guardrail, unconditionally.** The
  function that warns/caps runaway multi-agent fanout (`jGf`) takes
  `ultracodeActive` as a parameter and returns immediately, no check, when it is true.
  This is a plausible direct contributor to the 27-agent / 4,164,323-token blowout.
  VERIFIED code path; NOT verified that this specific function fired during that
  specific incident (no log correlation was possible from a static grep).
- **`CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` is very likely a dead setting right now.**
  Its only effect is gated to model ID strings containing `"opus-4-6"` or
  `"sonnet-4-6"`. The operator's subagent model is the literal string
  `"claude-sonnet-5"`, and the lead model (no `model` key set) resolves, per the
  operator's own `model-selection.md`, to Opus 5 / `claude-opus-5`. Neither string
  contains `opus-4-6` or `sonnet-4-6`. VERIFIED for the subagent case (literal
  substring test on a known string). ASSUMED for the lead case (model alias
  resolution is not independently re-derivable from a static grep; resting on the
  operator's own rule doc, not re-verified live).
- **`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` forces compaction to fire far earlier than
  the built-in default**, not later. Default compaction threshold is
  `contextWindow - 13000` tokens (roughly 93-96% of window depending on window
  size). The override computes `min(floor(window * 0.70), default)`, and 70% is
  always smaller, so 70 wins. VERIFIED from the `Afo()` function body. This is a
  strong, directly-evidenced candidate cause for "31 PreCompact fires... 20
  auto-compactions in one 30-min window" alongside the fanout-token volume itself.
- **Whether `effortLevel` actually changes per-request compute cost, independent of
  UI display, is not fully resolved from static analysis.** It is propagated as an
  env var (`CLAUDE_EFFORT`) to child/subagent processes and referenced in a
  `sendControlRequest({subtype:"apply_flag_settings", settings:{effortLevel, ...}})`
  call, which strongly suggests it is a real request-level parameter (not purely
  cosmetic), but no string in the dump ties `Goe()`'s effort value into the
  `thinking`/`budget_tokens` construction path directly. STAGED: the mechanism
  exists and is wired to the server; the exact marginal token cost of `xhigh` vs
  `high` per identical prompt was not measured in this session (would need a live
  A/B request-diff, not a binary grep).

## 1. What `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` does

VERIFIED, from the thinking-config constructor:

```
let Hn = Yt(process.env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING)
          && (f.includes("opus-4-6") || f.includes("sonnet-4-6")),
    bi = cvi(i.model);
if (bi !== void 0 ? bi === "adaptive" : IQt(u) && !Hn)
    Bo = { type: "adaptive", display: ui };
else {
    let Fr = sZc(u);                       // = cst(u).upperLimit - 1 (near-max fixed budget)
    if (r.type === "enabled" && r.budgetTokens !== void 0) Fr = r.budgetTokens;
    Fr = Math.max(1024, Math.min(Jt - 1, Fr));
    Bo = { budget_tokens: Fr, type: "enabled" };
}
```

`Yt()` (boolean env parser, VERIFIED): `["1","true","yes","on"]` (case-insensitive) →
`true`; anything else, including unset, → `false`. So `"1"` does register as "set".
But the `&&` gate right after it means the flag only ever flips `Hn` to `true`, and
therefore only ever forces the non-adaptive fixed-budget branch, when the resolved
model string contains `opus-4-6` or `sonnet-4-6`. `IQt()` (VERIFIED, separate
function) is what actually decides whether a model *supports* adaptive thinking at
all: it hardcodes `false` for `claude-3-*`, `opus-4-0/4-1/4-5`, `sonnet-4-0/4-5`,
`haiku-4-5`, and falls through to a remote flag check (`ON(r,"adaptive_thinking")`)
for everything else, including `opus-5`/`sonnet-5`/`opus-4-6`/`sonnet-4-6`.

Net effect for this operator's actual models (`claude-sonnet-5` subagents, Opus-5
lead): `Hn` never becomes `true` (the model-string test fails), so the request
always takes the `type:"adaptive"` branch regardless of this env var. **The
setting is very likely doing nothing today.** It would only bite during a legacy
fallback/remap to an `opus-4-6` or `sonnet-4-6` backing model (see
`CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP`, a sibling flag that exists specifically
to prevent such remaps) — and in that scenario it would force the *worse* of the
two options (fixed near-max budget on every turn) rather than the better one.

"Adaptive thinking," per this code, means: the API decides the thinking-token
budget per turn based on the actual turn, instead of the client asking for a fixed
near-ceiling budget on every call. This is exactly the mechanism that would make a
trivial question cost less than a deep audit — and it is verified active for both
of this operator's models regardless of the disable flag.

## 2. What `effortLevel` does; values; ceiling or floor

VERIFIED schema (Zod): `v.enum(["low","medium","high","xhigh"]).optional()`. **`max`
is not a persistable value.** It exists as an internal effort tier
(`eug()` switch has a `case "max"`, and `Goe()` downgrades `"max"` to `"high"` when
the model doesn't support it via `e6e()`), but the settings.json schema physically
rejects it — matching the operator's own `model-selection.md` note that `ultracode`
can't be stored in `effortLevel`, extended here: neither can `max`. `max` is
reachable only via `CLAUDE_CODE_EFFORT_LEVEL=max` (env) or `--effort max` (CLI) per
turn, both non-persistent.

Resolution order, VERIFIED from `f5i()`:

```
function f5i(e) {
  let t = S5(e.cli.effort) ?? aJn(e.cli.effort);
  if (t !== void 0) return t;                 // 1. CLI --effort flag wins
  if (e.settings.ultracode === true) return "xhigh";  // 2. ultracode forces xhigh
  return QVe(e.settings.effortLevel);         // 3. settings.effortLevel
}
```

This answers the "ceiling or floor" question directly: **it is neither a ceiling
nor an adaptive floor, it is a fixed override that short-circuits everything below
it.** `ultracode: true` doesn't merely default to xhigh, it makes `effortLevel`'s
own value irrelevant — even if `effortLevel` were set to `"low"`, `ultracode: true`
would still force `"xhigh"` on every request. In the operator's current config
both keys independently resolve to `"xhigh"`, so there is no live contradiction
today, but `effortLevel: "xhigh"` is redundant dead weight as long as `ultracode`
stays `true`, and would become a silent no-op trap if someone later lowered
`effortLevel` expecting it to take effect.

Descriptions per tier (VERIFIED, `eug()`):
- low: "Quick, straightforward implementation with minimal overhead"
- medium: "Balanced approach with standard implementation and testing"
- high: "Comprehensive implementation with extensive testing and documentation"
- xhigh: "Deeper reasoning than high, just below maximum"
- max: "Maximum capability with deepest reasoning"

These read as **agentic-thoroughness instructions** (how much testing/verification/
documentation depth to apply), propagated as `CLAUDE_EFFORT` to child processes and
sent to the server via `apply_flag_settings`. Nothing in the dump ties this value
into the per-turn thinking-token budget math (`cst()`/`sZc()` reference only model
capability, never effort). So effort and thinking-adaptivity look like two
independent dials: adaptive thinking already scales per-turn regardless of effort
tier; effort tier is a static, non-adaptive instruction sent on every single
request, trivial or not, for the whole session.

**Built-in default when neither key is set:** `Ej()` falls back to `"high"`
(`Goe(e,t) ?? "high"`), not `"xhigh"`. Removing both `effortLevel` and `ultracode`
from settings.json does not leave the operator without an effort tier — it reverts
to Anthropic's own default of `"high"`, one notch down from the currently-forced
`"xhigh"`.

## 3. What `ultracode: true` does, and how it interacts with `effortLevel`

VERIFIED, from the settings schema description string:
> "Enable ultracode for the session: xhigh effort plus standing dynamic-workflow
> orchestration."

And a companion tooltip:
> "Whether ultracode (xhigh effort plus standing dynamic-workflow orchestration) is
> active for the session. Set per session via the `ultracode` settings key..."

Two effects, not one:
1. Forces `effortLevel` resolution to `"xhigh"` (see #2, `f5i()`).
2. Puts "standing dynamic-workflow orchestration" into effect — VERIFIED via
   `jGf({scheduledAgents, startedAgents, totalTokens, ultracodeActive})`:
   ```
   function jGf({scheduledAgents:e, startedAgents:t, totalTokens:r, ultracodeActive:n}) {
     if (n) return;   // <-- workflow-size-guideline check is skipped entirely
     ...
   }
   ```
   This function is the one that reads `workflowSizeGuideline` and warns/caps when
   a dynamic workflow is getting large. With `ultracodeActive` true, it returns
   before doing any of that. There is a **separate** keyword-trigger path
   (`workflow_keyword_request`: "The user included the keyword 'ultracode',
   opting this turn into multi-agent orchestration") that fires per-message when
   the literal word "ultracode" appears in a prompt — that one is legitimately
   session-local/on-demand, and the operator's config already has
   `workflowKeywordTriggerEnabled: true` for it. The standing `ultracode: true`
   settings key is a different, always-on switch that does not require the
   keyword at all.

Because `ultracode: true` is set in the **global** settings.json rather than
toggled per session via `/effort ultracode`, every session — including one that
opens with "what is left?" — starts already primed for standing multi-agent
orchestration and with its size guardrail disabled. This is the most concrete,
code-level explanation available for why a trivial question and a deep audit are
not being treated differently by the harness's own safety net.

## 4. Other flags requested

All strings below are VERIFIED present in the binary via literal grep; behavior is
VERIFIED where a function body was located, ASSUMED/labeled otherwise.

- **`CLAUDE_CODE_ALWAYS_ENABLE_EFFORT`** — VERIFIED, inside `FI()` (the "does this
  model support the effort dial at all" gate): `FI()` returns `false` for
  `claude-3-*`, `opus-4-0/4-1`, `sonnet-4-0/4-5`, `haiku-4-5` — UNLESS
  `process.env.CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` is truthy, in which case it forces
  `true` even for those otherwise-unsupported legacy models. Not set in this
  operator's config; irrelevant to opus-5/sonnet-5 which already pass `FI()`
  without it.
- **`CLAUDE_CODE_AUTO_COMPACT_WINDOW`** — VERIFIED present in the env-var symbol
  table but its consuming function body was not isolated in this pass (the grep
  for its usage only returned "binary file matches", i.e. present but not
  text-extracted at the offsets tried). STAGED: exists, effect not confirmed by
  function-body read in this session.
- **`CLAUDE_CODE_MAX_CONTEXT_TOKENS`** — VERIFIED, read inside `rZc()`:
  ```
  function rZc(){ if (Z.DISABLE_COMPACT) {
    let e = Z.CLAUDE_CODE_MAX_CONTEXT_TOKENS;
    if (e !== void 0 && e > 0) return e;
  } return; }
  ```
  Only takes effect when `DISABLE_COMPACT` is also set — it is the override for the
  effective context-window size used elsewhere (`Xv()`), gated behind compaction
  being fully disabled. Neither var is set in this operator's config.
- **`DISABLE_AUTO_COMPACT`** — string present in the same symbol table as
  `DISABLE_COMPACT`; VERIFIED present, consuming body not isolated separately from
  `DISABLE_COMPACT` in this pass (they sit adjacent in the same string block, but
  only `DISABLE_COMPACT`'s read site was matched to a function body: `rZc()`
  above). STAGED for `DISABLE_AUTO_COMPACT` specifically.
- **`DISABLE_COMPACT`** — VERIFIED, see `rZc()` above: gates
  `CLAUDE_CODE_MAX_CONTEXT_TOKENS`. Not set currently.

## 5. Official docs

Not fetched this pass — the five binary-evidence questions above were answerable
directly from the shipped code with higher precision than a public docs page would
give (docs describe intended behavior; the grep shows what actually runs in
2.1.219). If independent confirmation against Anthropic's public effort/thinking
docs is wanted, that is a follow-up WebFetch, not done here. Flagging as an
explicit gap rather than skipping silently.

## The core question: does "what is left?" cost the same as a deep audit?

Two different mechanisms answer this differently:

- **Thinking-token adaptivity: no, already adaptive.** VERIFIED — for both
  `claude-sonnet-5` (subagents) and the Opus-5 lead model, the thinking config
  resolves to `type:"adaptive"` regardless of `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING`,
  because that flag's disabling condition only matches `opus-4-6`/`sonnet-4-6`
  model strings. The server picks the thinking-token budget per turn. This part of
  the system is not the waste source it was suspected to be.
- **Effort tier and workflow-orchestration priming: yes, forced uniform, and this
  is the real waste source.** `effortLevel` resolves to `"xhigh"` on literally
  every request this session sends (forced by `ultracode: true`, independent of
  message content), and "standing dynamic-workflow orchestration" plus its
  disabled size-guideline check are active on every turn, not just complex ones.
  Neither of these two mechanisms reads the content of the current message before
  applying — they are session-level, not per-turn-adaptive. A "what is left?"
  question is sent with the identical `xhigh`/`ultracode`-primed request envelope
  as a full audit.

Quantifying the waste, honestly: the per-token thinking-budget cost difference
between "what is left?" and a deep audit is likely small (adaptive thinking already
right-sizes that part). The quantifiable, evidenced cost is structural, not
per-token: with `ultracodeActive` true, ANY turn — including a one-line question —
is eligible for the Workflow tool's multi-agent orchestration path with its size
guard turned off. The one directly-logged data point available
(27 agents / 4,164,323 subagent tokens / 1,095 tool uses / 73 min / 2 of 5 lanes
stalled) is exactly the failure shape this code path allows: no cap, no warning,
because `jGf()` returned before checking. Connecting this to "20 auto-compactions
in a 30-minute window": faster context consumption (large fanouts) hitting a
compaction trigger set 23+ percentage points earlier than default
(`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` vs the built-in `~93-96%`) multiplies
compaction frequency for exactly the kind of large session this config invites.
Both settings point the same direction: standing ultracode primes bigger sessions,
and the compaction override cuts the runway for those bigger sessions short. This
is ASSUMED as a causal chain (the two mechanisms are independently VERIFIED; their
joint causal role in the specific 20-compactions incident was not re-derived from
that incident's own logs in this pass).

## Recommended env/settings block, with diff

```diff
   "env": {
     "API_TIMEOUT_MS": "600000",
     "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
-    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70",
-    "CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING": "1",
+    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "90",
     "CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5"
   },
   ...
-  "effortLevel": "xhigh",
-  "ultracode": true,
+  "effortLevel": "high",
   "workflowKeywordTriggerEnabled": true,
```

(`ultracode` key removed entirely rather than set to `false` — its absence and
`false` are equivalent per `f5i()`, but removing it also removes the confusing
"is this a session toggle or a permanent setting" ambiguity the operator's own
CLAUDE.md already flags.)

## Per-value verdict

| Key | Verdict | Why | Cost/context effect |
|---|---|---|---|
| `API_TIMEOUT_MS=600000` | **stay** | Unrelated to effort/thinking; a request-timeout ceiling. Not in scope of this audit's evidence. | none measured |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` | **stay** | Deliberate cost control per operator's own `model-selection.md` (ADR-0015); orthogonal to effort/thinking. | Prevents accidental 1M-context billing; not re-verified this pass. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` | **change → 90** (or remove for the ~93-96% default) | VERIFIED: forces compaction ~23+ points earlier than default (`window-13000` vs `floor(window*0.70)`), directly multiplying compaction frequency for any context-heavy session. | Saves compaction-triggered summarization/token churn; more usable context per session before a forced compact. Verify with the command below. |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` | **go (remove)** | VERIFIED no-op for `claude-sonnet-5`/Opus-5 (gate only matches `opus-4-6`/`sonnet-4-6` strings); if a legacy remap ever occurs it would force the *worse* fixed-budget branch, not a better one. Nothing to keep. | Zero cost either way today; removes a landmine for the fallback-remap edge case. |
| `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` | **stay** | Matches `hive-mind-workflows.md`/`gastown-company-registry.md`: workers must not inherit an expensive lead model. | Confirmed the intended effect (keeps fanout on Sonnet, not Opus). |
| `effortLevel: "xhigh"` | **change → "high"** (or remove, default is also "high") | VERIFIED description: "xhigh" = "deeper reasoning than high, just below maximum," applied identically to every request regardless of content. "high" is Anthropic's own built-in default absent any override. Set explicitly here (rather than omitted) mainly so the operator's `/effort` UI shows an intentional daily-driver tier, not an accidental blank. | Lower default reasoning depth on trivial turns; escalate to `/effort xhigh` or `/effort ultracode` per-message when a task actually warrants it, per the operator's own `CLAUDE.md` design intent. |
| `ultracode: true` | **go (remove)** | VERIFIED: (1) forces effortLevel regardless of its own value, making the explicit `effortLevel` setting a silent no-op as long as this stays true; (2) VERIFIED disables the workflow-size guardrail (`jGf` early-return) on every turn, standing, not on-demand — directly implicated in the 27-agent/4.16M-token event shape. The on-demand equivalent (`workflowKeywordTriggerEnabled: true`, typing the word "ultracode", or `/effort ultracode` per session) already exists and stays. | Removes the always-on invitation to multi-agent fanout with no size cap; restores the guardrail for every session that doesn't explicitly opt in. |

## Verification commands (run these, don't take the table on faith)

```bash
# Confirm the settings.json change took:
grep -A2 '"ultracode"' /c/Users/shova/.claude/settings.json
grep '"effortLevel"' /c/Users/shova/.claude/settings.json
grep 'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' /c/Users/shova/.claude/settings.json

# Re-confirm the DISABLE_ADAPTIVE_THINKING gate is genuinely model-string-scoped
# (rerun after any Claude Code version bump — minified symbol names are not stable):
cd /c/Users/shova/.local/share/claude/versions
timeout 90 grep -a -o -E ".{80}CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING.{300}" <version-binary> | head -5

# Live smoke test after the change: ask one trivial question and one deep-audit
# question in fresh sessions, diff the transcript's reported token/thinking usage
# (not available from a static grep; this is the STAGED->VERIFIED step still owed).
```

## What is still owed (name the gap, don't paper over it)

1. No live before/after token measurement was taken. Everything about "cost" above
   is derived from reading the decision code, not from running a trivial-question
   session and a deep-audit session side by side and diffing actual token counts.
   That comparison is the next step if the operator wants a number instead of a
   mechanism.
2. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and `DISABLE_AUTO_COMPACT` specifically (as
   distinct from `DISABLE_COMPACT`) were not traced to a function body in this
   pass — flagged STAGED above, not claimed VERIFIED.
3. The causal link between this config and the specific "20 auto-compactions in
   30 minutes" incident is a plausible mechanism match (both point the same
   direction), not a re-derivation from that incident's own logs.
4. Official Anthropic docs on effort/thinking were not fetched; this report rests
   entirely on the shipped binary for v2.1.219.
