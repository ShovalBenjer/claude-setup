# Foundry Deployment-Per-Project Rule

STATUS 2026-08-18: SUPERSEDED. The account this whole file was written around,
`brn-azai` (project `seekapa_ai`), is confirmed stale and out of use, and the
operator has directed it deleted from memory, unwired, and removed from Azure.
Every example below (the migration table, the specific deployment names) describes
that dead account, not a generic case. Do not follow this file's specifics. The
PRINCIPLE below (one project owns its own named deployment) still applies the day a
new Foundry account is provisioned; re-derive the concrete names against whatever
account is live then, do not reuse anything named here.

Global rule, principle only. Applies to every project and session once a live
Foundry account exists again. Governs how Azure AI Foundry / Azure OpenAI model
deployments map to projects, so that cost is attributable and any one project can be
throttled, paused, or retired without collateral. Companion to `repo-topology.md`
(one repo per deployable) and `gastown-company-registry.md` (ownership).

## Principle: one project owns its own named deployment(s)

Every project gets its OWN deployment for each model it uses, named `<model>-<project>`
(add `-<role>` when one project needs the same model for two distinct jobs). A
deployment is owned by exactly one project. No project calls another project's
deployment, and no generic "shared heavy model" deployment is called by several
projects at once.

- Correct (already compliant): `gpt-5.4-nano-cs-agent`, `gpt-5.4-mini-qc-api-telephony`,
  `gpt-5.4-mini-training`, `gpt-5.4-nano-call-analysis-agent`. The name resolves to one
  owner.
- Wrong (the anti-pattern this rule exists to kill): `gpt-5.4-SIU`, called at the same
  time by campaign-analysis (call scorer), video-understanding (vision), and ORM-AGENT
  (vision). A generic name, three owners, no clean off-switch.

## Why (the incident, 2026-07-01)

During a June cost review, campaign-analysis was found decommissioned, but its scorer
called the shared `gpt-5.4-SIU` deployment that video-understanding and ORM-AGENT also
call. Two failures followed directly from the shared deployment:

1. Cost could not be attributed. The ~$305 June `gpt-5.4-SIU` line was a one-time
   campaign backfill (Jun 7) mixed with ongoing video vision, and Azure Monitor exposes
   no per-project split (a single `ApiName=OpenAI` series). Attribution had to be
   reconstructed from local file mtimes.
2. It could not be turned off. Zero-scaling or deleting the deployment to stop the dead
   project would have broken the two live ones. There was no scoped off-switch.

A per-project deployment makes both trivial: read that one deployment's meter for the
project's cost, and delete or zero-scale it to retire the project, with zero blast radius.

## Rules

1. Name every deployment `<model>-<project>`. Add `-<role>` for a second job in the same
   project (`-eval`, `-batch`, `-vision`). Never a bare model name, a person's initials,
   or a team tag that invites reuse.
2. One owning project per deployment. If a second project needs the same model, it gets
   its OWN deployment, even if the config is identical. Deployments are cheap to create;
   shared ownership is the expensive mistake.
3. Cost must be readable from the deployment name. If you cannot answer "what did project
   X spend on model Y" from the deployment alone, the mapping is broken and must be split.
4. Retirement is scoped. Retiring a project means deleting or zero-scaling ONLY its
   deployments. It must never require first checking whether another project also calls
   them.
5. Batch and eval lanes are roles, not shared pools: `<model>-<project>-batch`,
   `<model>-<project>-eval`.
6. Prefer Standard / GlobalStandard / GlobalBatch (pay-per-token, idle costs ~$0). Use
   ProvisionedManaged (PTU) only with explicit written justification: PTU bills hourly
   whether used or not, so an orphaned PTU deployment is real recurring money, not clutter.

## Enforcement checklist

- [ ] Every deployment name resolves to exactly one project. Grep every codebase: no two
      projects hardcode the same deployment string.
- [ ] No deployment carries a generic name (bare model, initials, team tag).
- [ ] Retiring any project has a one-line, project-scoped deployment off-switch.
- [ ] Every ProvisionedManaged (PTU) deployment has a named owner and a live workload. No
      idle PTU.
- [ ] Stale deployments (no tokens in 90 days) are deleted, not left as ambiguous shared
      surface. Deletion still needs explicit per-action approval.

## Migration for the current violation (VOID, dead account)

This section described a split inside `brn-azai`. The account is gone, so nothing
here is actionable; kept only so the reasoning pattern (per-caller deployments,
scoped retirement) is available as a worked example for the next live account.
