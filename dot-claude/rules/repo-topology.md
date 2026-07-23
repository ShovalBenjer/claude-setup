# Repo Topology Rule

Global rule. Applies to every project and session. How code is split into repositories,
how the local workspace mirrors the remote, and what is forbidden. Companion to
`prod-deploy-rules` (how a repo deploys) and `gastown-company-registry.md` (ownership).

## Default: one umbrella repo per initiative (monorepo), subprojects are folders

Operator standard (Shoval, 2026-06): consolidate related subprojects under ONE umbrella
repo (e.g. `orm-agent`), each subproject a top-level FOLDER, not its own repo. Do NOT spin
up a separate top-level repo per subproject by default. "Under the same umbrella" means the
same git repo here, plus the same org/platform (corp-home SSO, ACR, Cloudflare).

```
orm-agent/                      [ONE git repo, ONE .git]
├── review-alert/               subproject (folder) + its own pipeline
├── social-media-agent/         subproject (folder) + its own pipeline(s)
├── widgora/                    subproject (folder) + its own pipeline
├── docs/  bin/  .gitignore
```

## Hard prohibition (universal, survives the mono/poly choice): no repo-in-repo

A `.git` directory MUST NOT sit inside another repo's working tree. An un-declared nested
repo is the actual defect: the outer repo either double-tracks the inner files (they
silently diverge) or leaves them untracked (they vanish from its history). A subproject in
the monorepo is a plain FOLDER with no `.git` of its own. The only sanctioned nesting is a
deliberate git submodule recorded in `.gitmodules`. If you find an un-declared nested repo,
fold it into the umbrella (remove its `.git`, track its files) - that is the fix, not a
new top-level repo.

## Many deployables from one repo: path-triggered pipelines

A monorepo deploys to many resources via SEPARATE pipeline definitions, each PATH-TRIGGERED
to its subproject and each with its own variable group naming its own resources:

```yaml
# widgora/azure-pipelines.yml
trigger:
  branches: { include: [main, stage] }
  paths:    { include: [ "widgora/**" ] }   # fires ONLY on widgora changes
```

So: one repo, one push, but only the touched subproject's pipeline runs, and it touches only
its own Web App / ACR / DB (selected by its variables). Branch still selects stage vs prod.
This gives full per-service deploy isolation without per-service repos.

## Local == remote shape

Clone the umbrella once; subprojects are folders within it. The parent of the clone is a
plain directory, never itself a second git repo wrapping the clone.

## When a SEPARATE top-level repo is justified (the exception, needs explicit cause)

Only with an explicit boundary: a different org/owner, a hard security/access split, an
OSS extraction, or a genuinely independent product with its own release org. Absent that,
default to a folder in the umbrella. When unsure, keep it in the monorepo; extracting later
is cheap, and a sprawl of micro-repos is the costlier mistake here.

## Enforcement checklist (before serious work, and before shipping)

- [ ] `find <umbrella-root> -maxdepth 4 -name .git -type d` returns EXACTLY ONE path (the
      umbrella). Any `.git` under a subproject folder = nested-repo defect; fold it in.
- [ ] Each deployable subproject has its own `azure-pipelines.yml` with a `paths:` trigger
      scoped to its folder, and its own variable group naming its own resources.
- [ ] One shared root `.gitignore` covers all subprojects (`.env`, `*.db`, `.venv/`).
- [ ] A new subproject starts as a folder in the umbrella, not a new repo, unless it meets
      the separate-repo exception above.

## Worked example: the ORM-AGENT anomaly (what NOT to do, and the fix)

`projects/ORM-AGENT/` (2026-06, observed): the umbrella repo (`Corp-AI/orm-agent`) contained
two un-declared nested repos - `social-media-agent/.git` (ALSO double-tracked as ~606 files
by the outer repo) and `widgora/earning-calendar/.git` (untracked by the outer). The defect
is the repo-in-repo, NOT the monorepo. Correct end state: ONE `orm-agent` repo with
`review-alert/`, `social-media-agent/`, `widgora/` as folders, each with its own
path-triggered pipeline; the nested `.git` dirs removed and their files folded into the
umbrella. The lesson that generalizes: keep related work in one umbrella repo, and never let
a subproject grow its own `.git` inside it.
