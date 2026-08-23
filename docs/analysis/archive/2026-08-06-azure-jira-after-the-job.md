# Azure and Jira after the job ended: what has a counterpart, what does not

Point-in-time reasoning, 2026-08-06. The operator's instruction was not "file
these away", it was: do we need them recreated against our GitHub and our current
setup. So this reasons capability by capability rather than deleting by keyword.

## First, the thing that decides how much of this matters

`gh repo view ShovalBenjer/claude-setup` reports `visibility=PRIVATE`,
`isPrivate=true`, remotes being GitHub plus a local Windows clone. **This is a
staleness problem, not a disclosure problem.** 210 of the 321 tracked files that
name an ex-employer identifier are dated analysis, work-docs, research-papers and
master-plans. Those are the record of what happened and they should stay exactly
as they are. Rewriting history to remove a former employer's project names would
destroy evidence and buy nothing on a private repo.

That leaves 63 files that change agent behaviour, and 8 always-loaded rules.

## The inversion, which is the finding

Three Azure skills bound to a tenant nobody can reach were loaded and available in
every session. Eight skills that target the current stack, including the GitHub
ones, existed only in `dot-agents/skills` and could not load at all.

| | in the live tree, before today |
|---|---|
| `azure-audit`, `azure-activity-watch`, `azure-runtime` (brn-azai / AZAI_group) | yes, all three |
| `to-issues`, `to-prd`, `github-triage`, `domain-model`, `ubiquitous-language`, `improve-codebase-architecture`, `request-refactor-plan`, `write-a-skill` | no, none of the eight |

The dead-tenant tooling was the tooling that worked. The mechanism is the tree
mismatch: `skills_sync deploy` syncs `dot-claude/skills` into `~/.claude/skills`,
and everything in the second row lived in `dot-agents/skills`, which is synced
nowhere. The registry routed Architecture Office at six skills, all six real files,
none of them loadable.

Worth stating plainly because it reframes the whole question: the problem was never
that we had Azure skills. It was that we had Azure skills *instead of* GitHub ones,
and no check could see the difference.

## Capability by capability

| Ex-employer capability | What it actually did | Counterpart in the current setup | Status | Verdict |
|---|---|---|---|---|
| `azure-audit` | Weekly dormancy and cost audit across resources, dated report under `~/docs/audits/`, never deletes autonomously | Same shape applies to a repo: stale branches, long-open PRs, Actions minutes, skills nobody invokes. `pointers.py` and `selfimprove/scan.py` cover fragments | Partial | **Recreate the method, not the skill.** The reusable part is the discipline (dated report, propose don't delete), not the `az` calls |
| `azure-activity-watch` | Who other than the owner stopped, restarted, deleted or resized something | Nothing. And there is a measured need: two clones running parallel sessions on a shared stash, and a claim row recording 8 subagents against one shared dirty tree | **Missing** | **Real gap.** The strongest recreate candidate in this document, and the one with local pain behind it |
| `azure-runtime` | Call a deployed model with step observability | `codex-call`, `dispatch`, `advisor` | Covered | Retire. Superseded by things that work |
| `agent-builder` (Foundry CRUD) | Author and deploy agents to a cloud runtime | Our personas are 23 markdown files in `~/.claude/agents`; `persona_audit.py` now measures them | Covered differently | Retire the Foundry half. The authoring need is real and is already local |
| `foundry-deployment-per-project` rule | One deployment per project so cost is attributable and there is a scoped off-switch | The principle is stack-independent: any shared resource with several owners can be neither costed nor switched off safely | Principle transfers, example dead | **Rewrite as a general rule**, drop `brn-azai` and the migration section |
| `jira-read` | Read a ticket WHOLE, all comments, no truncation | `gh issue view --comments`. The rule that birthed it, `read-whole-before-reasoning`, is already global and stack-independent | **Missing as a skill** | **Recreate against `gh`.** Small, and the discipline is already written down |
| `jira-task-draft` | Draft a ticket locally, never call the API | `to-issues` and `to-prd`, which already auto-detect ADO or GitHub | Covered, now live | Retire once the GitHub path is exercised |
| `jira-comment-drafting` rule | Register for outward-facing comments: bottom line first, name the specific thing, close the loop, draft never post | PR and issue comments. This repo already ships through PRs | Register transfers, tenant does not | **Refactor.** Keep draft-never-post and the register, drop `qboservices` and the per-colleague tone table |
| `prod-deploy-rules` skill | Azure container web app deploy specifics | Nothing here deploys | Not needed | Retire the skill. `production-means-merged-and-smoked` already carries the general rule |
| `pii-handling` rule | Mask at the model boundary, never mutate production | The masking principle is fully general; the named stores (az-corp, vTiger, PandaCRM, `qc_analyzer`) are unreachable | Principle transfers | **Relabel** the stores as the historical case they now are |

## The eight always-loaded rules, in three classes

Measured: 8 of 23 rules in `~/.claude/rules/` are grounded in the ex-employer.
They do not all need the same treatment, and treating them alike is how a good
rule gets deleted alongside a dead one.

**Keep, relabel the example as historical (4).** `boundary-contracts`,
`production-means-merged-and-smoked`, `read-whole-before-reasoning`,
`hidden-trees`. Each states a stack-independent rule and then proves it with a
worked example from a job that ended. The example is what makes the rule stick,
and `calibrated-claims` already models the fix by dating its incidents and citing
them as history. Relabel, do not rewrite.

**Rewrite, principle survives the tenant (2).** `foundry-deployment-per-project`
and `pii-handling`. Both are about a real discipline expressed entirely in
unreachable nouns.

**Retire or refactor hardest (2).** `jira-comment-drafting` exists solely to post
into a tenant we no longer have, and names three colleagues by first name in every
session's context. `repo-topology` is the odd one: its rule (one umbrella repo,
never a repo inside a repo) is one of the most useful here and its entire worked
example is ORM-AGENT. Highest value per line of any rewrite on this list.

## What was done today, and what still needs a decision

Done, and measured by `python tools/audit/persona_audit.py scan`:

- Deployed 33 repo-only skills into the live tree, then promoted the eight
  `dot-agents`-only skills into the payload and deployed those too. Live coverage
  of routed skills went from 23 to 61.
- Held back `jira-read`, `jira-task-draft` and `prod-deploy-rules` from the live
  tree. All three remain in the repo; one `skills_sync.py deploy --apply` restores
  them. They were held back because a live skill that opens `az keyvault secret
  show` against a dead tenant is a trap, not a capability.
- Granted `Edit, Write` to Architecture Office, QA Lab and Review Board, each of
  which owned a file-producing skill and could not write. Release Bureau was
  examined and left alone: `commit-push-pr` is gates plus git, so Bash is enough.
- Routed-dead personas: 7 before, 0 after. Write-blocked: 3 before, 0 after.

Still open, and each is the operator's call:

1. The three held-back skills: retire, or rebind. `jira-read` is the only one with
   a clean GitHub counterpart worth writing.
2. The 8 rules, per the three classes above. The relabel class can proceed without
   a decision; the retire class cannot.
3. `azure-activity-watch` recreated against git and gh, which is the one genuine
   capability gap this analysis found rather than inherited.

## What this does not claim

Nothing here says the Azure knowledge was wasted. `foundry-deployment-per-project`
is a good rule that was learned by getting it wrong once, and `boundary-contracts`
came out of a real review by a named engineer. The argument is narrower: a rule
loads into every prompt, so the cost of one that cannot fire is paid every session,
and the cost of the worked example going stale is that a reader cannot tell which
half is still binding.
