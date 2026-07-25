# Deployment gap audit — claimed setup vs live harness, 2026-07-24

Point-in-time scan (docs-control-plane: `analysis/`). Triggered by a direct comparison:
another operator got a Call-of-Duty-Zombies clone out of ONE Opus 5 session using 13
named parallel teammate subagents (`@rounddata @powerups @weapondata @nav @vfx @audio
@interactables @viewmodels @props @hud @textures @zombiemodel`) plus headless-Chrome
CDP verification with 60+ scripted checks and an honest bug report. This audit
quantifies why this setup would not reproduce that, today, as configured.

Evidence classes per `rules/calibrated-claims.md`: **VERIFIED** = command + real output
in this session (below). **STAGED** = exists on disk, unproven live. **ASSUMED** =
inferred, not directly tested. Broken/unknown leads; what exists comes after.

---

## Bottom line (broken first)

The reference run's core mechanism — named subagents with harness-enforced tool and
model boundaries, invoked by `@name` — **does not exist on this machine**.
`~/.claude/agents/` is not merely empty, it **does not exist as a directory**
(VERIFIED, `ls` errors "No such file or directory", not "0 files"). 23 correctly
formatted agent definitions sit one directory to the left, in the git repo, imported
today and never copied over. The routing rules that are supposed to dispatch work to
those agents by name (`gastown-company-registry.md`, `hive-mind-workflows.md`) are
**not even loaded as global rules** — they exist live in exactly one of at least three
known projects (this one), by accident of where a file was copied, not by the "Global
rule. Applies to every project and session." header both files carry. Of the 99 skill
names those rules route to, the honest cross-project hit rate is **24%**; of the 19
persona names, it is **0%**. The CDP-driven verification loop that gave the reference
run's report its credibility is also unreachable here: the launcher script the `/cdp`
command depends on (`~/.codex/bin/obscura-cdp`) does not exist outside the repo, and
no MCP server is configured anywhere (`mcpServers: {}` in every known project + global
settings). Three independent instances of the same root defect: real content in
`claude-setup/`, nothing copied to where the harness reads from, and no working sync
between the two.

---

## 1. Live vs canonical inventory (re-verified independently)

### 1a. Agents — VERIFIED

```
$ ls -la ~/.claude/agents/
ls: cannot access '/c/Users/shova/.claude/agents/': No such file or directory
```

Not zero files in an existing dir — the directory itself was never created. Compare:

```
$ ls ~/claude-setup/dot-claude/agents/ | wc -l
23
```

All 23 checked carry valid Claude Code subagent frontmatter (`name:`, `description:`,
`tools:`, `model:`) — e.g. `mayor-opus.md` (`tools: Read, Grep, Glob, Task`, `model: opus`)
and `qa-lab.md` (`tools: Read, Grep, Glob, Bash`, `model: sonnet`), VERIFIED by reading
both files whole. These are not sketches; they are ready to deploy as-is. 19 of the 23
map onto the registry's persona list; 4 (`azure-resource-investigator`,
`eval-row-diagnoser`, `foundry-agent-inspector`, `tdd-slice-planner`) are task
specialists the registry itself does not know about.

Provenance: added in exactly one commit, `8d2277b` ("feat(archive): complete
work-setup import from work-archive-2026-07-12"), 2026-07-24 19:46:19 +0300 — roughly
3 hours before this audit (VERIFIED `git log --oneline --all -- dot-claude/agents/`
returns one line). Imported from a 12-day-old archive and undeployed the entire time
since arriving in this repo.

### 1b. Skills — VERIFIED

| Estate | Path | Count |
|---|---|---:|
| Live (global) | `~/.claude/skills/` | 30 |
| Repo dot-claude | `claude-setup/dot-claude/skills/` | 62 |
| Repo dot-agents | `claude-setup/dot-agents/skills/` | 71 |
| Repo dot-codex | `claude-setup/dot-codex/skills/` | 63 |
| This project overlay | `new-recruit/.claude/skills/` | 27 |

Counts match the operator's brief exactly (re-verified independently, not trusted from
the prompt). Prior same-day audit (`2026-07-24-skills-wiring-audit.md`, read whole)
already established 35 of the 62 dot-claude entries and 35 of 63 dot-codex entries are
dead one-line WSL-path stub files, not real skill directories — that finding is
consistent with what I found independently below and is not re-litigated here.

### 1c. Commands — VERIFIED

```
$ ls -la ~/.claude/commands/
cdp.md  commit-push-pr.md  diverge.md  slop.md
```

4 live, matching the brief. Only `commit-push-pr` also appears as a registry-owned
skill name; `cdp`, `diverge`, `slop` are live but invisible to the registry (not
routing defects, just unrouted extras — noted for completeness, not scored below).

### 1d. MCP servers — VERIFIED, confirms the brief

```
$ node -e "console.log(JSON.parse(require('fs').readFileSync('.../settings.json')).mcpServers)"
undefined
```

Checked in four places, all empty or absent: global `~/.claude/settings.json`
(`mcpServers` key not present at all), `~/.claude/settings.local.json` (same),
and every one of the 3 tracked projects in `~/.claude.json` (`C:/Users/shova`,
`C:/Users/shova/oren-roast-hq`, `C:/Users/shova/Downloads/daily-deep-learning`) —
each shows `"mcpServers": {}, "enabledMcpjsonServers": []`. No `~/.mcp.json` file
exists at all (`ls` errors, VERIFIED). Zero MCP servers, confirmed independently.

### 1e. A claim that does not survive contact: model default

`rules/model-selection.md` states the Opus 5 default is "Set in
`~/.claude/settings.json` as `\"model\": \"opus\"`". VERIFIED live: the `model` key is
**absent** from `settings.json` entirely (`model: undefined`, checked directly, not
inferred). The rule document and the live config disagree about what the default even
is — a fourth instance of documentation asserting a state that isn't on disk.

---

## 2. Named routing hit rate — the registry and hive-mind-workflows route by NAME

### 2a. Where the routing rules themselves actually load — VERIFIED

Before scoring hit rate, a prior question: do `gastown-company-registry.md` and
`hive-mind-workflows.md` even load outside this one conversation? Both carry the
header "Global rule. Applies to every project and session." Checked directly:

```
$ ls ~/.claude/rules/
calibrated-claims.md
```

Neither file is present. Checked the other two projects Claude Code has session
history for (`oren-roast-hq`, `daily-deep-learning`): neither has a copy either
(VERIFIED `find`, zero hits in both). The only live copy of either file on this
machine is the one under `new-recruit/.claude/rules/` — the exact project this audit
runs in. So the routing map that is supposed to govern "every project and session" is
in force in **1 of at least 4 known contexts** (global + 3 projects), and that one
is incidental to where this audit happened to be asked from, not to any deploy step.
Of 17 rule files in the repo, only 1 (`calibrated-claims.md`) is deployed to the one
place (`~/.claude/rules/`) a global rule needs to be to actually be global.

### 2b. Skill-name hit rate — VERIFIED via `comm`

Extracted all 99 backtick-quoted owned-skill names from the "Persona Owners" section
of the registry (`grep -oE '^- \`[a-zA-Z0-9_-]+\`$'`, deduplicated, 99 unique — matches
the prior skills-wiring-audit's independent count of 99, cross-check holds).

| Baseline | Hits | Rate |
|---|---:|---:|
| Global live only (`~/.claude/skills`, 30 entries) — the correct baseline for a rule marked "every project and session" | 24 / 99 | **24%** |
| Global + this-project overlay (`new-recruit/.claude/skills`, 27 entries) — what this specific session happens to see | 39 / 99 | 39% |

75 names miss against the strict global baseline; 60 miss even counting the local
project overlay this session benefits from. `hive-mind-workflows.md`'s own "Default
Skill Routes" section was checked separately for any name not already in the
registry's 99 — **zero new names found** (VERIFIED `comm -23`), meaning it inherits
the registry's hit rate exactly rather than adding independent routing surface.

Sample of registry names that resolve to nothing live anywhere on this machine (of
60): `agent-team`, `brainstorming`, `qa`, `tdd`, `to-prd`, `to-issues`, `deploy-prod`,
`domain-model`, `azure-devops`, `azure-foundry`, `mcp-activation`, `notebook`,
`ponytail`, `red-team`, `watchdog`, `web-inspect`. Several of these are exactly the
skills a Mayor/QA Lab/Release Bureau persona would reach for mid-task (`qa`, `tdd`,
`deploy-prod`, `to-issues`) — the miss is not confined to exotic corners of the list.

### 2c. Persona-name hit rate — VERIFIED

19 personas named as `###` headers in the registry (Mayor Opus, Workflow Clerk,
Evidence Clerk, Latent Systems Lab, Engineering Firm, QA Lab, Review Board,
Architecture Office, Release Bureau, Azure Ops Utility, Runtime Agents Division, MCP
and Tooling Office, Security and Compliance Office, Data Bureau, Product Studio, Voice
and Media Studio, Communications Desk, Conversation Layer, Learning Desk). Against
`~/.claude/agents/` (does not exist): **0 / 19 = 0%.**

### 2d. Combined figure

118 distinct names routed by these two rule files (19 personas + 99 skills, hive-mind
contributing zero net-new). Live hits: 24 (skills, strict global baseline) + 0
(personas) = **24 / 118 ≈ 20%.** Using the more generous this-session-only baseline:
39 / 118 ≈ 33%. Either way, roughly two-thirds to four-fifths of every name these
"Global rule[s]" dispatch to resolves to nothing when the harness tries to act on it —
the exact "prose not enforcement" failure mode the brief named, now with a number
attached, and it is worse than the 30% floor the raw skill-directory count alone would
suggest, because the persona layer (the thing structurally equivalent to the reference
run's named teammates) is at flat zero.

---

## 3. Deploy/sync script status — exists, wrong direction, never run

Three candidate scripts found in `dot-claude/bin/`: `sync-setup.sh`, `sync-skills.sh`,
`docs-sync.sh`. Read all three whole (per `read-whole-before-reasoning.md`).

**None of the three syncs the repo (`dot-claude/`) into the live location
(`~/.claude/`).** `sync-setup.sh` and `sync-skills.sh` both union two already-live
directories against each other — `$HOME/.claude` and `$HOME/.codex` — via one-way-safe
symlinks ("Claude gains Codex skills" / "Codex gains Claude skills"). Neither script's
source or target argument is ever the git repo. `docs-sync.sh` is unrelated: it
rebuilds a local best-practices SQLite corpus, not agents or skills. **There is no
script anywhere in this repo that deploys `dot-claude/agents` or `dot-claude/skills`
to `~/.claude/`.** The two prior same-day audits' recommended fix (`cp -r
dot-claude/agents/. ~/.claude/agents/`) is accurate precisely because no existing
tooling does it.

**Does even the live-to-live sync run?** No evidence it ever has, on either side.
`sync-skills.sh` would `mkdir -p ~/.codex/skills` and populate both sides with
symlinks on first run. VERIFIED: `~/.codex/skills` exists but contains only a
`.system` subdirectory — zero populated skill symlinks. VERIFIED: every entry in
`~/.claude/skills/` is a real directory (`drwxr-xr-x`), not a symlink — sync-skills.sh
has never round-tripped through it. Not wired into any hook either: `settings.json`'s
`hooks` block has exactly 4 hooks (SessionStart→`session-recall.sh`,
UserPromptSubmit→`kernel-anchor.sh`, PreCompact→`precompact-handoff.sh`,
Notification→`notify-toast.ps1`) and none of them call any of the three sync scripts
(VERIFIED, read `session-recall.sh` whole — it reads memory/TODO/resume-pointer files,
nothing else). **Mtimes** on the scripts are all `Jul 23 04:44` (last edit, not last
run — there is no execution log for them, unlike hooks which do write to
`state/hook-fires.log`). Best available evidence: these scripts have been edited, not
executed, since being written.

Same failure mode found a third time, unprompted: `dot-claude/commands/cdp.md`
documents driving a headless Chromium over CDP via a `playwright-mcp-obscura` MCP
server declared in `~/.mcp.json`, launched by `~/.codex/bin/obscura-cdp`. VERIFIED:
`~/.mcp.json` does not exist; `~/.codex/bin/` does not exist as a directory at all
(the launcher and the MCP registration both live only under the repo's
`dot-codex/bin/`); ports 9222 and 9223 are both unreachable right now (`curl`
connection refused). The one differentiator that made the reference run's report
credible — driving real UI and reporting real bugs from real CDP output — is
currently unreachable by the documented path on this machine.

---

## 4. What an undeployed fleet costs, concretely, against the reference run

The reference run's structural primitive — 13 subagents, each with a fixed name, a
narrow tool/file scope, and (implicitly) its own context window, invoked by `@name` —
maps exactly onto Claude Code's custom-agent mechanism: a `.md` file in
`~/.claude/agents/` with `name:`/`tools:`/`model:` frontmatter, callable by that name
through the Task tool. This repo has the equivalent artifact already written (23
files, correct frontmatter, VERIFIED above) and simply never copied it to the one
directory the harness reads. The gap is not "the pattern doesn't exist here" — it is
"the pattern is fully specified and sitting 3 hours from being live, additive, zero
risk, and untouched."

What is lost, concretely, while it stays undeployed:

- **No harness-enforced boundaries, only requestable ones.** A named subagent's
  `tools:` and `model:` lines are enforced by Claude Code itself — QA Lab literally
  cannot invoke a tool outside `Read, Grep, Glob, Bash` because the harness never
  offers it the others. Without deployment, the only way to get "QA-Lab-shaped"
  behavior is to type the role, tools, and model into a Task-tool prompt by hand,
  every time, as a request the model can drift from or a compaction can drop. This is
  the same enforcement-over-prose gap `boundary-contracts.md` and ADR-0005 name for
  code; the routing layer built to dispatch to those very principles violates the
  principle itself.
- **No named, addressable teammates.** The reference screenshot's readability
  (`@weapondata`, `@zombiemodel`) comes from persistent identity: each subagent owns a
  domain and can be referred back to. A generic Task-tool subagent has no persistent
  name across a run and no persona memory to accumulate; the fanout has to be
  re-explained from scratch each time it's spun up.
- **No verification loop equivalent to the CDP harness.** The reference run's honest
  bug report was possible because it drove the actual artifact and read real CDP
  output. The nearest analog here (`/cdp` → Obscura/Edge bridge) is currently
  unreachable end-to-end (§3) — so even if 13 named agents existed today, nothing in
  this setup currently closes the loop the way the reference run did.
- **The routing map can't be trusted to route.** Because 76-80% of registry/hive-mind
  names miss (§2), any lead persona that tried to dispatch by the book — "send this to
  Engineering Firm, owned skill `tdd`" — would be routing to nothing 4 times out of 5
  on the skill side and every single time on the agent side. A route that fails
  silently is worse than no route: it looks like a decision was made when none was
  enforced.

Cheapest fix, ranked by leverage-to-risk (additive, per the Authorization rule — new
dirs/files, proceed without a propose-first step):

1. `mkdir -p ~/.claude/agents && cp -r ~/claude-setup/dot-claude/agents/. ~/.claude/agents/` — takes the persona hit rate from 0/19 to 19/19 in one command, matching the exact primitive the reference run used. This is the single highest-leverage fix in this whole audit.
2. `cp -rn ~/claude-setup/dot-claude/rules/. ~/.claude/rules/` — makes the registry and hive-mind rules (and the other 15 currently-undeployed rules) actually global instead of accidentally-scoped to one project.
3. Materialize the 35 dead WSL-stub entries in `dot-claude/skills` from their real siblings in `dot-agents`/`dot-codex` (already scoped as move #2 in the prior skills-wiring-audit), then deploy the skills directory — moves the skill hit rate from 24% toward parent-repo coverage.
4. Write the one missing script: a real `dot-claude/bin/deploy-setup.sh` that does 1-3 idempotently, so this stops being a manual one-off and starts being what the operator's mental model already assumes exists.

None of this requires new design work — every artifact needed already exists in the
repo, correctly formed. The gap is entirely a missing `cp`, run once.
