# Dynamic setup decisions: workflows, effort, thinking, cross-model, resources

Status: decision document, not a spec. Answers the operator's verbatim question set.
Written 2026-07-25 local / re-verified live at 2026-07-24 23:42 UTC (`date -u`, pasted
below). Scope: the five 2026-07-25 lane files under `docs/analysis/`
(`effort-and-thinking`, `cloudflare-fit`, `other-resources`, `free-tier-exploitables`,
`claude-mastery-audit`), all read whole, plus a fresh live re-verification pass done
while writing this document, plus the refutation packet (1 survived, 5 named killed,
only 3 delivered in full). `claude-mastery-research-prompt.md` is the prompt that
produced the mastery audit, not a sixth lane.

## Lead with what is broken: settings.json is a moving target, not one file

Three genuinely different versions of `dot-claude/settings.json` exist right now, and
the OPERATOR CONTEXT this task shipped with is neither the newest nor the committed one:

1. **Committed HEAD** (`git show HEAD:dot-claude/settings.json`, commit `9a4f7bc`,
   2026-07-24 20:10:42+03:00): `ultracode: true`, `permissions.defaultMode:
   "bypassPermissions"`, `skipDangerousModePermissionPrompt: true`, env has
   `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` and `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING:
   "1"`, no `API_TIMEOUT_MS`, no `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. Its `_meta` block
   reads `"project": "Axia Seekapa CS Agents"`, `"description": "OTP authentication for
   Seekapa and AxiaCS AI agents"`: an employer-project snapshot pulled in by commit
   `8d2277b` ("work-setup import from work-archive-2026-07-12"), not this machine's own
   baseline. **VERIFIED**: checked all 9 hook scripts HEAD's `hooks` block references
   (`session-context.sh`, `post-compact-reinject.sh`, `hive-review-bridge.sh`,
   `coverage-enforcer.sh`, `eval-gate.sh`, `codex-review-on-push.sh`,
   `watchdog-verify.sh`, `protect-infra.sh`, `stop-checklist.sh`) against
   `~/.claude/hooks/`: **all 9 are MISSING**. A revert to HEAD would not just re-enable
   `ultracode`/bypass, it would install a hook block that silently fails to fire for
   9 of its entries.
2. **The OPERATOR CONTEXT snapshot** this task was given ("verified this session"):
   env has `API_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`,
   `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`, `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`,
   `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5`; `ultracode: true`;
   `permissions.defaultMode: bypassPermissions`; claims no `model` key. This matches
   neither HEAD nor the file on disk now: it is a real intermediate state from earlier
   in this session, not a fabrication, just stale by the time this task runs.
3. **The live file on disk right now** (`cat /c/Users/shova/.claude/settings.json`, run
   fresh for this document): env has only `API_TIMEOUT_MS`. No `ultracode` key. No
   `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, no `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING`, no
   `CLAUDE_CODE_SUBAGENT_MODEL`, no `CLAUDE_CODE_DISABLE_1M_CONTEXT`.
   `permissions.defaultMode: "acceptEdits"` with `disableBypassPermissionsMode:
   "disable"`. `"model": "opus"` **is** present (contrary to OPERATOR CONTEXT).
   `effortLevel: "xhigh"` still set. Byte-identical to the working-tree copy of
   `dot-claude/settings.json` (VERIFIED, `git status --short` shows only ` M`, meaning
   working tree and live `~/.claude/settings.json` already match; the diff is entirely
   against HEAD).

Everything below is evaluated against **state 3, the live file, re-read for this
document**, never against 1 or 2. Where a lane's own snapshot (state 2) differs from
current disk, that is named explicitly rather than silently carried forward. This
three-way drift, on the one file that gates every session's permissions and effort
tier, uncommitted, is itself the single largest "don't want to be disappointed" risk
in this setup: see question 5 and row 2 of section 3.

## 1. Direct answers, in your order

**So do we want to use workflows or agent teams?** Workflows, opted into per task,
never standing. Agent teams is not a real lever today regardless of preference:
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` appears in the binary and in HEAD's env block,
but the gate (`isAgentSwarmsEnabled`) also requires a remote flag, `tengu_amber_flint`,
which cannot be read from a static grep and is carried ASSUMED off per your own prior
check. The live file has it absent: keep it absent, adding it back buys nothing and
implies a false "one flag away" story. The thing that actually caused the 27-agent /
4,164,323-token blowout is `ultracode: true` as a *standing* settings key: it forces
`effortLevel` to `xhigh` and, VERIFIED from `jGf()`, returns before checking the
workflow-size guardrail on every single turn, not just complex ones. The live file has
already removed that key. `workflowKeywordTriggerEnabled: true` (VERIFIED present,
live) is the correct on-demand equivalent: type "ultracode" or run `/effort ultracode`
per task when you actually want multi-agent fanout.

**What is the effort level dynamically we want to use?** There is no per-turn dynamic
effort dial in the shipped code: `f5i()` resolves a single static value sent
identically on every request for the whole session. "Dynamic" can only mean
operator-driven escalation. Decision: persisted default `"high"` (Anthropic's own
built-in default when the key is absent, per `Ej()`), escalate per task with
`/effort xhigh` or `/effort ultracode` when a task's risk actually warrants it. Live
state is still `"xhigh"` (VERIFIED, re-read for this document) and has not been
changed yet: that is row 3 of the config diff below.

**Is adaptive thinking what we want to do?** Yes, and it is already the active
mechanism for both models you run, independent of any flag. The disable path in
`CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` only triggers when the resolved model string
contains `opus-4-6` or `sonnet-4-6`; `claude-sonnet-5` (your subagent pin) and the
Opus-5 lead alias contain neither, so every request takes the `type:"adaptive"` branch
regardless of the flag. The flag is currently absent from the live env block
(VERIFIED): correct, leave it absent. If it were ever set again it would do nothing
today and would only ever hurt in a legacy `opus-4-6`/`sonnet-4-6` remap edge case, by
forcing the worse fixed-near-max-budget branch instead of the adaptive one.

**What about more dynamic stuff across the model, other providers?** No gateway, no
proxy, no standing router to a second provider, and none is recommended. Keep
first-party Claude.ai/Max OAuth routing as the only thing touching real work here, per
your own `model-selection.md`. Kimi K3 and DeepSeek V4 are real external candidates per
the mastery-audit lane, but their architecture numbers are vendor-reported, not
independently reproducible at this cutoff (Kimi's full weights/report were scheduled
for July 27, still after today). If either is ever evaluated, it happens in an isolated
harness against the same task/tools/oracle and never receives private work,
credentials, or proprietary prompts merely to get "model diversity." This is a policy
call, nothing to install or toggle.

**What is my setup missing? I don't want to be disappointed.** Four things, led by the
worst: (1) the three-way settings.json drift above: the file that governs every
session's permissions and effort tier is uncommitted, and its committed fallback (HEAD)
is an employer-flavored snapshot whose hooks reference 9 scripts VERIFIED missing on
this machine. (2) `claude-code-review.yml` is deployed, looks live in the workflow
list, and silently is not working: re-checked fresh this pass
(`gh run list --workflow=claude-code-review.yml --limit 5`), both of its last 2 runs
still show `conclusion: failure` (`2026-07-23T02:28:22Z`, `2026-07-23T11:44:57Z`),
`error_max_turns`, unchanged since the lane found it, no run since. This is exactly the
false-negative class your own calibrated-claims rule flags as worst. (3)
`permissions.defaultMode` is `acceptEdits` with bypass locked out
(`disableBypassPermissionsMode: "disable"`) on the live file: a real behavior change
from both HEAD and the OPERATOR CONTEXT snapshot, and nothing read for this document
shows you explicitly asked for this specific change; it needs your call, not mine (see
section 5). (4) AUTO-18's nightly cron is deployed and correctly configured but still
has 0 runs (re-checked fresh, see question 6's cloudflare answer is separate: this is
the GitHub-side cron, see section 3 row 4); it is not due to fire for about another 1h35m
from this check, not broken.

**Beside Cloudflare, do we want to use it on our setup?** Yes, narrowly, gated on one
prerequisite still unmet: re-checked fresh this pass, `bunx wrangler whoami` still
returns "You are not authenticated," `~/.wrangler/config` still does not exist, no
`CLOUDFLARE_*`/`CF_*` env var is set anywhere in this shell. Adopt two of the four
shortlisted items after auth: R2 for the transcript archive, Pages for FleetView.
Reject two regardless of auth: Cron Triggers for AUTO-18 (cannot wake the laptop or
invoke local Claude Code), Browser Rendering for the CDP loop (no path to `localhost`
or the Windows Edge SSO session it depends on). Defer Vectorize (premature at ~130 MB
across ~287-295 files; try D1 FTS5 first). Durable Objects (SQLite-backed) has a real
free tier on Workers Free and is architecturally correct for ordered, multi-writer-safe
messaging between local sessions if that ever becomes a named priority: it is not one
of your currently named weak points, so it is flagged here, not in the ranked 8.

**Same for other resources you think can upgrade our weak points.** The two
highest-value items are already on this machine, not cloud. Native `msedge.exe` /
`chrome.exe` (VERIFIED present) replace the WSL-shaped CDP bridge documented in
`.claude/commands/cdp.md`, which cannot work on a native Windows box (it references
`/home/shovalbe/...` and `obscura-cdp` paths that do not exist here). The PreCompact
hook (`precompact-handoff.sh`) already fires and is wired in the live `settings.json`
(VERIFIED) but only logs `git status`/`git log`, it does not copy the transcript: the
"raw gold" archive gap is a small edit to an existing hook, not new infrastructure.
Outside Cloudflare, `ntfy.sh` (free, pushes to an already-installed phone app, zero
app-store work) is the strongest fit for getting a verified result onto your phone,
closer to AUTO-05's spirit than building a receiver before a telephony provider is
chosen. Full ranked list is section 3.

## 2. The config diff

Against the live file re-read for this document, `C:\Users\shova\.claude\settings.json`
(state 3 above), not against OPERATOR CONTEXT and not against HEAD: see the lead
section for why those three differ. This is a Claude Max flat-rate subscription
(per your own `model-selection.md`, "Paid API spend is avoided," ADR-0002), so no line
below has a direct per-token dollar cost. Where a line has a real cost it is indirect:
faster consumption of the subscription's own usage quota, or context/compaction churn.

```diff
   "env": {
-    "API_TIMEOUT_MS": "600000"
+    "API_TIMEOUT_MS": "600000",
+    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
+    "CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5"
   },
   ...
-  "effortLevel": "xhigh",
+  "effortLevel": "high",
   "workflowKeywordTriggerEnabled": true,
```

| Line | Verdict | Cost, stated |
|---|---|---|
| `API_TIMEOUT_MS=600000` | keep, unchanged | $0. Request-timeout ceiling, unrelated to effort/thinking/agent teams. No lane raised a concern. |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` | add back | $0 direct (flat subscription). Indirect: your own `model-selection.md` says select 1M context only when measured retrieval and deliberate compaction are inadequate, i.e. opt-in, not standing-on. Whether an unset key defaults to 1M-available or 1M-unavailable was not established by any lane or independently re-derived from the binary this pass: the recommendation rests on your written policy, not a verified technical default (open item, section 5). If unset does default to available, the indirect cost is a session silently pulling a far larger context window and burning Max usage quota for no requested benefit, the same shape as the 27-agent event. |
| `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` | add back | $0 direct. Indirect: your `model-selection.md` says use `claude-sonnet-5` for bounded implementation and parallel workers. A bounded grep for the unset-fallback behavior this pass only hit string-table entries, not the resolving function body: ASSUMED, not VERIFIED, that an unset value means subagents inherit the Opus-5 lead model. If it does, every worker in a fanout burns quota at the lead-model rate, directly relevant to the 4,164,323-subagent-token event already on record. The policy match alone justifies restoring the pin regardless of that unresolved detail. |
| `effortLevel: "xhigh"` to `"high"` | change | $0 direct. Indirect: VERIFIED from `f5i()`/`eug()` that effort tier is a static instruction sent identically on every request regardless of content; `xhigh` on a one-line question requests the same "deeper reasoning, more testing" instruction as a full audit, contributing to faster context growth and more frequent compaction. `high` is Anthropic's own built-in default when the key is absent. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | do not add | $0, non-change. OPERATOR CONTEXT's "=70" description does not match the live file or HEAD (both absent): correcting the record, not a live setting. If it were set to 70, VERIFIED it forces compaction ~23+ points earlier than the harness default (`window-13000`, ~93-96% of window); absent is already the better state. |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | do not add | $0. VERIFIED no-op for `claude-sonnet-5`/Opus-5 (gate only matches `opus-4-6`/`sonnet-4-6` strings); would only ever force the worse fixed-budget branch in a legacy remap. Already absent, live: leave it that way. |
| `ultracode` (top-level key) | do not add | $0 direct. Indirect: the single highest-leverage line for preventing a repeat of the 27-agent / 4.16M-token / 2-of-5-stalled event (VERIFIED mechanism, section 1). Already absent, live: leave it that way; use the keyword trigger per task instead. |

Verify after applying:

```bash
grep -E 'CLAUDE_CODE_DISABLE_1M_CONTEXT|CLAUDE_CODE_SUBAGENT_MODEL|"effortLevel"' /c/Users/shova/.claude/settings.json
```

Not in this diff because it is a decision, not a config line: `permissions.defaultMode`
(live: `acceptEdits`; HEAD and OPERATOR CONTEXT: `bypassPermissions`) and
`disableBypassPermissionsMode: "disable"`. Real, defensible security posture; also a
real behavior change against a documented pattern of wanting long, uninterrupted
autonomous loops. Nothing read for this document shows you explicitly asked for this
exact change: confirm before treating it as settled (section 5).

## 3. What to adopt, ranked

None of these were executed as part of writing this document beyond the read-only
verification commands whose output is quoted above and below.

| # | What | Weak point closed | First command | Verify command | Effort |
|---|---|---|---|---|---|
| 1 | Fix `claude-code-review.yml` (`error_max_turns` on both of its last 2 runs, re-checked this pass, unchanged since 2026-07-23) | Already-deployed AUTO-10 reviewer silently not working: the worst calibrated-claims failure class | Raise `--max-turns` (e.g. 20) or narrow the review prompt scope in the workflow file, then `gh run rerun <last-failed-run-id> --repo ShovalBenjer/claude-setup` | `gh run view <id> --repo ShovalBenjer/claude-setup --json conclusion` returns `success` | 15-30 min |
| 2 | Commit or explicitly reject the pending `dot-claude/settings.json` rewrite (still ` M`, re-checked this pass): do not `git checkout`/`reset` this file until you decide, its HEAD fallback references 9 hook scripts VERIFIED missing on disk and carries an unrelated employer `_meta` block | Governance/loss risk on the one file that gates every session's permissions, effort tier, and hooks | `git -C /c/Users/shova/claude-setup diff -- dot-claude/settings.json` (review the full diff yourself; it includes the `acceptEdits`/bypass-lock decision) | `git status --short -- dot-claude/settings.json` returns empty after commit | 15-20 min review, your decision on the permissions question first |
| 3 | Apply the section 2 diff | Cost-quota regression risk (subagent model pin, 1M-context opt-in, effort tier) in the current live config | Edit `C:\Users\shova\.claude\settings.json` per section 2 | `grep -E 'SUBAGENT_MODEL|DISABLE_1M_CONTEXT|"effortLevel"' /c/Users/shova/.claude/settings.json` | 2 min |
| 4 | Confirm AUTO-18's nightly cron actually fires (SURVIVED adversarial refutation, corrected framing) | Turns "deployed" into "smoked" for the always-on-schedule weak point. Re-verified fresh this pass: `gh run list --workflow=claude-nightly.yml` still returns `[]`, current time 2026-07-24 23:42 UTC, scheduled fire `17 1 * * *` UTC is about 1h35m out: not broken, just not due yet. Do not report AUTO-18 solved off the workflow's existence | Nothing to build; wait | `gh run list --repo ShovalBenjer/claude-setup --workflow=claude-nightly.yml --limit 3 --json conclusion,createdAt` after ~01:17 UTC | 5 min, after the fire time passes |
| 5 | Transcript archive, local first, cloud second | The "raw gold" gap: PreCompact hook already fires but only logs `git status`/`git log`, does not copy the transcript (VERIFIED). ~130-152 MB across ~287-295 `.jsonl` files against a 10 GB R2 free tier once auth exists | Local: edit `precompact-handoff.sh` to copy the hook's `transcript_path` (from stdin JSON) into a local archive dir before compaction. Cloud, only after `bunx wrangler login` succeeds: `bunx wrangler r2 bucket create claude-transcripts-archive` | Local: trigger a manual `/compact`, confirm a new file lands with a timestamp matching the hook-fire log. Cloud: `bunx wrangler r2 bucket list` shows the bucket | Local copy: 45 min-1 hr. Cloud auth: 5-10 min. Bucket: 2 min. Keep separate: an empty bucket with no writer is not progress (see section 4) |
| 6 | Native Windows CDP loop, replacing the WSL-shaped `cdp.md` | The currently broken local browser-verification loop; `msedge.exe`/`chrome.exe` already installed locally | `Start-Process msedge.exe -ArgumentList "--remote-debugging-port=9222","--user-data-dir=$env:LOCALAPPDATA\Edge-CDP-Profile"` | `curl -fsS http://127.0.0.1:9222/json/version` returns JSON with `webSocketDebuggerUrl` | 20-30 min, including rewriting `cdp.md` to drop the WSL-only steps |
| 7 | `ntfy.sh` for phone delivery | Closest free fit to "a verified result reaches the phone," relevant to AUTO-05's spirit without committing to a telephony provider. Rate ceiling is UNVERIFIED: generic self-hosted defaults, conflicts with a secondary source's ~250/day/IP claim | `curl -d "test" ntfy.sh/<long-random-topic-name>` | Phone shows the notification (manual check). Before trusting it for anything time-critical, send a deliberate 20-30 message burst in under a minute and watch for 429s | Under 5 min to try; load-test before relying on it |
| 8 | Pages project for FleetView | AUTO-19 dashboard, cheapest/lowest-risk of the four Cloudflare items: but NOT a literal copy of `daily-deep-learning`'s deploy pattern; "verbatim" did not survive adversarial review, exact gap unknown (section 4) | After wrangler auth: `bunx wrangler pages project list` to confirm the account and the existing `daily-deep-learning` project first | `curl -I https://<fleetview-project>.pages.dev` returns a response after the first deploy | 45-60 min, above the original "verbatim" estimate because that claim was refuted |

Dropped to respect the 8-row cap, still real, later: D1 as a transcript search index
(pair with row 5, defer Vectorize per both Cloudflare lanes' sequencing); Durable
Objects for multi-session messaging (not a named weak point today); `ecosystem.db`
bootstrap (`sqlite3` already available, this is schema design, not a resource gap); the
AUTO-05 Cloudflare Tunnel skeleton (blocked on an unmade telephony-provider decision,
not a tooling gap); a GitHub Actions scheduled workflow for an arXiv/ECCC-style watcher
(a real fit per `free-tier-exploitables` problem 4, but no concrete ingestion target is
named in this task).

## 4. What not to adopt, and why

This section is not empty. It carries everything the refutation packet killed, and
everything the lanes' own analysis rejected without adversarial review.

**Checked and dismissed by adversarial refutation.** The packet supplied to this task
named 5 killed claims but delivered complete text for only 3, the 3rd cut off
mid-sentence, the 4th and 5th never delivered. Listing only what was actually received:

- *Wrangler-not-authenticated "blocks all four shortlist items."* The auth gap itself
  is real, re-confirmed fresh this pass (`whoami` fails, `~/.wrangler/config` absent, no
  `CF_*`/`CLOUDFLARE_*` env var set). The "blocks all four" framing does not survive:
  `wrangler`'s own output states a no-login path exists (`wrangler deploy --temporary`),
  and the refutation's own repo check was run against a different repo than where these
  Cloudflare weak points actually live. Use: the auth gap is real and listed as a
  prerequisite in rows 5 and 8 above; do not repeat the absolute "blocks everything"
  framing.
- *R2 free tier "comfortably covers" the archive, therefore create the bucket now.* The
  capacity math holds (~130-152 MB against 10 GB free). The sequencing does not:
  creating a bucket with no writer wired to it yet is unused infrastructure reported as
  progress, the exact pattern already flagged twice this year (23 persona files, 35 dead
  skill stubs). Row 5 above keeps bucket creation but sequences it after the local copy
  is proven.
- *Pages "verbatim" reuse of the `daily-deep-learning` deploy pattern.* Ruled
  overstated; the refutation text was cut off before stating exactly what differs. The
  specific gap is unknown, not fabricated here (section 5). Row 8 budgets extra review
  time instead of treating this as a drop-in copy.
- *Items 4 and 5 of the "killed by refutation" set*: not delivered to this task in any
  form, despite the header claiming 5. Not invented here. If they exist, they need to be
  re-supplied before this document can speak to them.

**Rejected on the lanes' own analysis, not adversarially killed, just does not fit.**

- *Cron Triggers for AUTO-18.* Fires reliably on Cloudflare's edge regardless of laptop
  power state, but there is nothing local for it to call when the laptop is asleep, and
  it cannot invoke Claude Code either way. Adopting it would create a schedule that
  looks solved and fires into nothing. Use Windows Task Scheduler's own wake-flag on the
  four already-registered Sadna tasks, or the already-available `schedule`/`CronCreate`
  capability for anything genuinely cloud-portable.
- *Browser Rendering for the CDP verification loop.* Runs a serverless browser on
  Cloudflare's own network with no path to `localhost` and no access to the Windows Edge
  SSO/Entra session the loop exists to use. Would verify a different, unrelated public
  surface, not the thing that is actually broken.
- *Vectorize, right now.* Real product, wrong sequencing. ~130-152 MB and ~287-295 files
  does not justify an embedding pipeline yet, and embeddings likely mean paid API calls,
  cutting directly against the standing paid-API-avoidance posture (ADR-0002). Try D1
  FTS5 keyword search first.
- *Queues, for any ordered multi-writer job.* Cloudflare's own docs state Queues carries
  no ordering guarantee; if ordering matters, they point at Workflows instead.
  Disqualifying for anything shaped like multi-session messaging.
- *KV as a primary multi-writer store.* 1,000 writes/day free, and writes propagate via
  cache expiry with no documented conflict resolution (last write wins, silently, and a
  just-written key can read as missing elsewhere for up to a minute). Fine narrowly as a
  single-writer cursor value; not fine as a mailbox or a multi-writer index.
- *A second, separate Worker for FleetView's backend*, before deciding how live the
  dashboard actually needs to be. Building the backend ahead of that decision repeats
  the same unused-infrastructure shape flagged twice already.
- *Reverting `dot-claude/settings.json` to committed HEAD.* Would re-enable `ultracode`,
  `bypassPermissions`, `skipDangerousModePermissionPrompt`, and
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (still inert without the remote gate, but a
  false signal), while installing a `hooks` block that VERIFIED references 9 scripts
  that do not exist on this machine: a silent-failure hook set, not a safe rollback.
- *`claw-army/claude-node`* (the one substantive addition in the "awesome Claude Code
  mastery" list). Its own README calls it alpha, states Windows is unvalidated, and its
  primary examples run with `skip_permissions=True`. Drives the installed CLI as a
  persistent subprocess with session continuation: expanded permission,
  environment-inheritance, and secret-exposure surface for no requirement this setup has.
- *Bulk plugin marketplaces, unofficial gateways/proxies, remote auto-approval
  controllers, duplicate memory systems.* Rejected as defaults per your own
  `model-selection.md` ("do not introduce gateways or free proxies unless the user
  explicitly requests a controlled experiment"). None installed.
- *`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` as a standalone env var.* Present in HEAD,
  absent from the live file: correctly absent. Does nothing without the remote gate
  (`tengu_amber_flint`); adding it back would gain nothing and imply agent teams is one
  flag away when it structurally is not.

## 5. Open and unknown

- Items 4 and 5 of the "killed by refutation" set were never delivered to this task.
  Unknown, not zero.
- Exactly what differs between the `daily-deep-learning` deploy pattern and what
  FleetView would need: the refutation that killed "verbatim" was cut off before
  stating it. Row 8's effort estimate is a guess against that unknown.
- Whether `CLAUDE_CODE_DISABLE_1M_CONTEXT` being unset means 1M context defaults to
  available or unavailable. Not established by any lane, not independently re-derived
  from the binary this pass. Section 2's recommendation rests on your written policy
  (opt-in per task), not a verified technical default.
- Whether an unset `CLAUDE_CODE_SUBAGENT_MODEL` actually causes subagents to inherit the
  lead model. A bounded, anchored grep this pass surfaced only string-table entries, not
  the consuming function's logic. ASSUMED, not VERIFIED; the policy match alone
  justifies restoring the pin.
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and `DISABLE_AUTO_COMPACT` (as distinct from
  `DISABLE_COMPACT`) were not traced to a function body by any lane, not re-derived this
  pass. STAGED, not verified. Neither is set live, so not currently load-bearing.
- The actual marginal token/quota cost of `xhigh` vs `high` on an identical prompt was
  never measured live, only the mechanism (static, applied uniformly) was verified from
  code. A before/after A/B session is the next evidence-producing step if a number is
  wanted instead of a mechanism.
- Whether the `acceptEdits`/`disableBypassPermissionsMode: disable` change, and the rest
  of the drift between HEAD, the OPERATOR CONTEXT snapshot, and the live file, was
  something you actually asked for anywhere, or something an earlier pass in this same
  session decided unilaterally. Not established by anything read for this document.
  Needs your explicit call before being treated as settled.
- Why the committed HEAD carries `_meta.project: "Axia Seekapa CS Agents"` (an employer
  OTP-auth project) and a hook block referencing 9 scripts VERIFIED missing on this
  machine, imported by commit `8d2277b`. Unresolved provenance question; flagged, not
  fixed here, since it involves a destructive-adjacent git decision (rewriting committed
  history or force-overwriting HEAD) that needs your sign-off, not mine.
- Why OPERATOR CONTEXT states "no model key" when `"model": "opus"` is VERIFIED present
  in the live file, the working-tree file, and committed HEAD, all checked this pass.
  Unlike the env-var drift (traced above to an earlier session snapshot), this specific
  detail does not trace to anything read for this document.
- `tengu_amber_flint`'s actual current value for this account. The gate mechanism is
  VERIFIED (per OPERATOR CONTEXT, not re-derived here to respect the bounded-grep rule
  on a 265 MB binary); the remote flag's live value cannot be read from a static grep.
  Carried as ASSUMED off, from your own prior-session check.
- Whether the Cloudflare account behind the already-live `daily-deep-learning.pages.dev`
  is the same account any new R2/D1/Pages resource would land in. Cannot be checked
  until `wrangler login` actually runs, which has not happened as of this pass.
- GitHub Actions minutes remaining on this account could not be verified via the billing
  API (404, needs a `user` scope not currently granted). The 2,000-min/month
  private-repo figure is a published-pricing number, not an account-specific
  confirmation.
- `ntfy.sh`'s production rate ceiling on the public server. UNVERIFIED: the fetched page
  documents generic self-hosted defaults, not confirmed live values for the public
  instance, and a secondary source's ~250/day/IP claim does not cleanly reconcile with
  the documented burst-and-replenish rate. Load-test before relying on it (row 7).
- AUTO-05's telephony provider (Twilio or equivalent) has not been chosen. This is a
  decision only you can make, not a resource gap.
- Kimi K3 and DeepSeek V4 architecture numbers are vendor-reported at cutoff, not
  independently reproducible. Treat as hypotheses if either is ever evaluated in an
  isolated harness, not as settled fact.
