# Gap analysis: official anthropics/claude-code vs this harness

Date: 2026-08-12. Read-only. Point-in-time snapshot (docs-control-plane: this is an
`analysis/` scan, an input to the TODO, not a spec or PRD).

## What the official repo actually is (corrects the pasted-answer framing)

`github.com/anthropics/claude-code` is public (141k stars) but is **not** the CLI
source. No `cli.js`, no `node_modules`. It ships: `README`, a 498 KB `CHANGELOG.md`,
`examples/` (hooks, settings, mdm, gateway), and **13 reference plugins** under a
marketplace manifest (`.claude-plugin/marketplace.json`). So "pull the repo, see what
we lack" is a comparison against Anthropic's reference *plugins and examples*, not
against the closed binary. The binary is a Bun single-file executable (entrypoint
`/$bunfs/root/src/entrypoints/cli.js`), inspectable via `strings`/`unbuned` but not
shipped here.

## Verdict per official surface

Evidence class inline. HAVE = this harness already implements it. LACK = genuine gap.

| Official surface | Verdict | This harness |
|---|---|---|
| code-review | HAVE | `code-review` + `review` + `red-team-review` skills |
| pr-review-toolkit | HAVE | `review` posts structured PR threads; `codex-call` adds independent judge |
| feature-dev | HAVE | `brainstorming` + `tdd` + engineering-firm agent |
| commit-commands | HAVE | `commit-push-pr` skill |
| frontend-design | HAVE | `frontend-design` skill (direct) |
| security-guidance | HAVE | security-compliance-office agent + `pii-scrubber` |
| agent-sdk-dev | PARTIAL | `write-a-skill` covers skill authoring; no dedicated SDK-agent authoring flow |
| explanatory-output-style | HAVE (VERIFIED) | `output-styles/shoval.md` exists live AND in repo, identical 5194 bytes. The harness ships its own working output style; the two Anthropic plugins just demonstrate the mechanism. |
| learning-output-style | HAVE | same `output-styles/` mechanism, populated |
| bash_command_validator example | HAVE | `rtk-bash-guard.sh` + gate hooks do bash validation |
| ralph-wiggum | HAVE-WITH-TWIST | see below |
| plugin-dev | LACK | no skill to author/package a Claude Code plugin (manifest + marketplace). Low urgency: only matters if this harness ever ships plugins externally. |
| hookify | LACK | no NL-to-wired-hook authoring flow; `update-config` is adjacent. Low urgency. |
| claude-opus-4-5-migration | LACK | no guided model-migration skill; `model-selection.md` is routing policy, not a migration walkthrough. Low urgency, and note the roster shifted 2026-08-12 (fable-5/sonnet-5/opus-4.6/haiku-4.5, no opus-5). |
| examples/settings presets | LACK | one undifferentiated `settings.json`; no lax/strict/sandbox profiles. See below. |
| examples/mdm | NON-GAP | enterprise MDM (Jamf/Intune/GPO); single-operator workstation, out of scope by design. |
| examples/gateway (aws/gcp) | NON-GAP | Bedrock/Vertex gateway; first-party Claude.ai OAuth only per `model-selection.md`. Intentional. |

## The one correction the subagent got wrong

The gap-analysis subagent reported output-styles as an **empty directory** and inferred
the "shoval" style was unbacked. That was judged from the repo copy by existence-check,
without a live read. Cheap live check refutes it:

```
$ ls -la ~/.claude/output-styles/                 -> shoval.md (5194 bytes)
$ ls -la dot-claude/output-styles/                 -> shoval.md (5194 bytes, identical)
```

Both trees carry it. This is the "findings go stale, existence-check misfires" class
(L-2026-08-08-a: the cheap half of a check ran, the expensive half did not). Output-style
is a HAVE, dropped from the adopt list.

## ralph-wiggum is already implemented here, for a different purpose

ralph-wiggum's whole mechanism (README): a **Stop hook that blocks session exit and
re-feeds the same prompt** until a completion promise appears. That is architecturally
identical to this harness's `completion_gate.py` Stop hook, which blocked exit and
re-prompted three times in the session that produced this document. The harness runs the
ralph pattern today, aimed at **follow-through enforcement** (don't stop and hand the
decision back) rather than **task-loop iteration** (re-run the same build prompt until
tests pass). Adopting ralph would mean generalizing the existing Stop-hook loop to accept
a task prompt + completion-promise, not building the mechanism from scratch. It also sits
squarely inside the already-accepted `the-loop-may-act` boundary. Worth doing only if
autonomous overnight build loops are actually wanted; the mechanism is not the blocker.

## The only clear adopt: settings presets

Anthropic ships three managed-settings profiles (`examples/settings/`):

- **settings-lax**: disables `--dangerously-skip-permissions`, blocks plugin marketplaces.
- **settings-strict**: lax + blocks user/project permission rules and hooks, denies
  WebFetch/WebSearch, forces Bash to ask.
- **settings-bash-sandbox**: forces Bash to run inside a sandbox.

This harness has one live `settings.json` and no documented switchable profiles. Value
here is modest and specific: a `strict` profile is a real safety artifact for the
autonomous loop (`the-loop-may-act`) — a background session that cannot self-escalate
permissions, cannot add marketplaces, and cannot reach the web is a smaller blast radius
than the current single config. Note the README warning: several of these keys
(`allowManagedHooksOnly`, `strictKnownMarketplaces`) only take effect in *enterprise*
managed-settings, not user `settings.json`, so a straight copy would silently no-op some
lines. Adopting means adapting to the user-settings subset, not pasting.

## Bottom line

Of 13 plugins + 4 example trees, the harness HAS or intentionally-declines all but a
short tail: settings presets (one worth adapting, for the autonomous-loop blast radius),
and three low-urgency authoring/migration skills. The headline "we lack implementations"
is mostly false — the coverage is already broad. The one genuinely useful import is a
strict settings profile scoped to background sessions, and even that needs adapting to
the user-settings key subset rather than copying.
