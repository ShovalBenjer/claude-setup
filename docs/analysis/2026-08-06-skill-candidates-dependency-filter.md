# Which skills can actually run here, 2026-08-06

Point-in-time scan. The question was "find all related skills, such as DORA, so we
do not make errors like linear / notion / obsidian". Two things had to be settled
before any list was worth writing: what the error actually is, and whether we are
already committing it.

Every count below is emitted by `python tools/audit/skill_deps.py counts`, not typed
into the prose. Run it before quoting any figure from this file.

## The finding that reverses the question

The filter that rejects a Notion skill rejects 26 of our own 71 committed skills.

```
dot-claude/skills: 71 skills, 26 blocked, 43 unbound, 2 runnable
dot-agents/skills: 70 skills, 22 blocked, 42 unbound, 6 runnable
~/.claude/skills:  41 skills, 13 blocked, 25 unbound, 3 runnable
```

`az` is not installed on this machine. `command -v az` returns nothing, and
`az account show` fails with "No such file or directory". Nine committed skills
open with an `az` invocation, the gastown registry routes an entire Azure Ops
Utility persona at eight owned skills, and `jira-read` reaches for
`az keyvault secret` to fetch the Jira token, so the Jira path is dead here too by
inheritance. `jq` is absent and four skills pipe through it. `bun` is absent and ten
skills invoke it, although see the grading below, because that ten is the softest
number in this document.

`dot-agents/skills/obsidian-vault` exists, is routed in the registry to Workflow
Clerk, and hardcodes a vault at `/mnt/d/Obsidian Vault/AI Research/`. Five candidate
Obsidian locations were probed on this host, including the Windows AppData roaming
path. All five are absent. We already shipped the error we were asked to avoid,
and it has been sitting in the registry long enough to have a persona pointed at it.

That is why the deliverable is a checker rather than a list. A list of
recommendations goes stale and cannot be pointed at us. `tools/audit/skill_deps.py`
runs against any tree, including our own, and is the only reason to believe the
recommendations further down.

## Grading the 26, because the classifier over-reports

The scanner detects a named invocation. That is a proxy for a dependency, and it is
wrong in both directions. Hand-graded, with each row's evidence snippet visible via
`skill_deps.py scan --json`:

| Grade | Count | What it means | Examples |
|---|---|---|---|
| Hard block | 11 | The skill's purpose is the absent tool. It cannot start. | `azure-runtime` (`az login`), `azure-audit` (`az devops`), `agent-builder` (`az login`, `pac auth`), `jira-read`, `openai-agents`, `prod-deploy-rules`, `voice-explainer`, `gws-gmail-read` |
| Project-conditional | 10 | `bun test` or `bun run` inside a JS workflow. Blocked only when the target project is JavaScript, and no lane currently ships one. | `testing-pyramid`, `cleanup-crew`, `mutation-runner`, `triage-tests` |
| Prose mention | 5 | The classifier read an illustration as a requirement. The skill runs fine. | `premortem` (one `az cognitiveservices` example), `shoval-voice-draft` (names HeyGen access as a thing to ask Yasha about), `jira-task-draft` (whose own text says it never calls the Jira API) |

So the honest headline is 11 hard, not 26. The over-report is recorded here rather
than tuned away, because a classifier quiet enough to never over-report would have
missed `jira-read`, whose Azure dependency is one line deep and invisible from the
skill's name.

One false positive is worth keeping on the record. The first run flagged
`voice-metrics` as needing Notion and Obsidian. It ships a 200,000-line English
lexicon, and both are ordinary English words. The filter written to reject Notion
skills had flagged a dictionary for containing the word "notion".
`looks_like_wordlist()` now skips data files, and the selftest pins it.

## DORA: the answer is no, and not for the reason expected

DORA-shaped skills exist. Six independent implementations were found, none dominant,
none above single-digit stars. The best of them, `manikumarkv/devrunway-claude-plugin`
(MIT), computes the four keys from `git log`, git tags and `gh pr` with no account at
all. It passes the dependency filter cleanly.

It should still not be adopted, and the argument is already in this repo.
`docs/specs/2026-07-31-github-native-project-surface.md` section 4.1 read the DORA
2025 report and DX Core 4 and concluded that the throughput half does not transfer:
DX's speed dimension is PRs per engineer and lead time, and this repo has one
operator and no customers. What transfers is DORA's pairing rule, that a KPI
counting output without a matching correctness or rework counter is a vanity metric.
That rule is already implemented as K1 to K15 against our own ledgers, ten of the
fifteen computable today with no new instrumentation. Installing a skill to compute
deployment frequency here would produce four numbers our own spec calls
uninformative.

The sharper find is `npow/claude-skills/dora-lite-report`, which needs a configurable
external DORA metrics API with a Spinnaker fallback. A DORA skill is not
automatically dependency-free. That one has the same shape as a Notion skill wearing
engineering-practice vocabulary, which is the version of this error that is hardest
to catch by reading the name. `harness/harness-skills` fails the same way at
collection scale: correct SBOM and CI governance language, vendor platform
underneath.

## What the official and popular sources do not give you

`anthropics/skills` holds 17 skills and not one is practice or measurement shaped.
The list is docx, pdf, pptx, xlsx, canvas-design, frontend-design, mcp-builder,
skill-creator, webapp-testing and similar. GitHub's licence endpoint returns no
LICENSE file for it, so vendoring is blocked pending that check regardless.

`ComposioHQ/awesome-claude-skills` is the index most likely to be reached for, and
its flagship plugin needs a Composio API key. Of roughly 30 top-level entries read
directly, the large majority are connector-shaped. An index is not a shortlist, and
following one is precisely how a tree acquires a Notion skill.

## The shortlist

Seven adopt-candidates, from 24 decision rows in `state/external-skills.jsonl`. Each
was selected because it runs on git, gh and files, and because it aims at a defect
this repo has already measured rather than at a capability it might one day want.

| Skill | Source | Licence | Aims at |
|---|---|---|---|
| `octocode-skills` | bgauryy/octocode | MIT | Skill drift. 33 of 71 committed skills are absent from the live tree, and `skills_sync.py check` exits 0 while reporting drift (open TODO row A). |
| `octocode-graph-eval` | bgauryy/octocode | MIT | The DORA-shaped slot, done against our own signals: goal-to-KPI contracts and ACCEPT/REVERT loops. |
| `octocode-awareness` | bgauryy/octocode | MIT | Two clones in parallel sessions, and the 2026-07-31 claim row recording 8 subagents against one shared dirty tree. |
| `neat-freak` | KKKKhazix/khazix-skills | MIT | Reconciling CLAUDE.md, AGENTS.md and agent memory against the code. AGENTS.md already documents 359 files citing a home directory that does not exist here. |
| `caveman-stats` | JuliusBrussee/caveman | MIT | Token figures computed by a hook rather than by the model, which is the METR self-report finding our own KPI spec leans on. |
| `resolving-merge-conflicts` | mattpocock/skills | MIT | Our merge-not-rebase-against-a-live-base practice, currently written nowhere. |
| `verification-before-completion` | obra/superpowers | MIT | 134 `completion_without_evidence` handback events, 16.1% of all handbacks (K6). |

Two of these are read at metadata depth only and are marked as such in the ledger.
The distinction matters here more than usual: `mattpocock/skills` is already partly
in our tree (7 name matches across the three trees, fewer than the 45 forks the open
TODO row suggests) and `obra/superpowers` was listed but not opened.

Adopt-patterns, not skills: `dmmulroy/.dotfiles` ships a `.skill-lock.json` pinning
which skills are installed at which version. That is the missing half of our sync
drift. No licence is declared, so the pattern is adoptable and the file is not.

Cited as prior art rather than adopted: `UditAkhourii/adhd` does parallel divergent
ideation under named cognitive frames, scored and pruned, which is genuine prior art
for `/diverge` and the out-of-distribution rule. `danlavee/Conductor` is a
disk-backed agent bus and duplicates `tools/bus/bus.py`, which is already
hash-chained and verified.

## What was skipped, and what stays unknown

Roughly 370 skills were enumerated across 17 saved repositories, and 24 carry a
decision row. The remainder are unreviewed, not rejected. The largest unreviewed
block is `K-Dense-AI/scientific-agent-skills` at 158 skills, marked leave at
collection level because several entries are laboratory vendor connectors
(benchling, dnanexus, latchbio, opentrons) and no lane in `docs/charters.md` is
scientific. If that judgement is wrong it is wrong for all 158 at once.

Star counts as returned by the GitHub API are reported as fetched and not
corroborated: `obra/superpowers` at 267,743 and `mattpocock/skills` at 205,862 are
each high for their age. The two agree in scale with each other and with the numbers
already committed in `state/external-repos.jsonl`, so nothing was normalised.

Nothing was installed. No skill was removed, no registry entry was edited, and the
26 blocked skills are still exactly where they were. The gastown registry still
routes `azure-cert-coach`, which resolves to no file in any of the four trees.

## What to do next, in order

1. Decide the `az` question, because it governs 11 skills and one whole persona.
   Either install the Azure CLI in WSL, or mark the Azure persona as
   Windows-side-only in the registry. Right now it is neither, which is the worst of
   the three states: routed, unrunnable, and silent about it.
2. `apt install jq` unblocks four skills for the cost of one command.
3. Wire `skill_deps.py scan --strict` into the skills domain of the gate, so a
   newly added skill that cannot run here fails at commit rather than at first use.
   That is the durable fix; this document is only the first run of it.
4. Read the two metadata-depth shortlist entries before adopting either.
