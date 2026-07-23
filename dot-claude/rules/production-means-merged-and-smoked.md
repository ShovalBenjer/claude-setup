# "Production" / "Live" means merged-to-main + deployed + live-smoked

Global rule. Applies to every project and session. Companion to
`prod-deploy-rules`, `repo-topology.md`, and the Forge Loop CI BIND axis.

## Trigger

Whenever Shoval says "production", "prod", "live", "ship it", "deploy it", "go
live", or asks whether something is in production, this rule is in force.

## The rule

A change is NOT in production until ALL THREE are true and evidenced. "Built",
"staged", "done locally", "tests green on the feature branch", or "code-complete"
are NOT production. State which step is missing when one is.

1. **Merged to the deploy branch.** The change is merged into the branch the
   prod pipeline actually deploys from (for qc-telephony-api that is `main`, not
   `master`, not a `feat/*` branch). Verify, do not assume:
   `git merge-base --is-ancestor <commit> origin/main` must pass. A commit that
   lives only on a feature branch is invisible to prod even if its tests are green.
2. **Deployed.** The pipeline ran against prod and reported success. Capture the
   build id / deploy timestamp / deployed commit sha.
3. **Live-smoked.** A smoke test ran against the real prod URL (not localhost,
   not a test host) and returned real, pasted output: HTTP status plus the one
   signal that proves the change is live (the new field, the new route returning
   200/401 instead of 404, the telemetry row appearing, etc.).

## Persist the evidence

Record, in the PR description and in project memory, the three facts: the merge
commit on the deploy branch, the deploy build id, and the live-smoke output. This
is the durable proof that "production" happened, so a later session does not have
to re-litigate whether it shipped. If any of the three is missing, write the gap
down too ("merged + deployed, smoke pending").

## Why this exists

2026-06-29, qc-telephony-api monitoring investigation. The assistant concluded
TWICE that the App Insights observability wiring was "not deployed to prod" and
recommended merging a large feature branch to fix it. Both conclusions were wrong,
from trusting indirect/stale signals instead of verifying live:

1. A `git merge-base --is-ancestor` check ran against a STALE local graph (before
   `git fetch`) and reported the observability commit was not in the deployed
   build. After fetching, `origin/main` HEAD equalled the deployed commit and DID
   contain it. Lesson: verify deploy state against freshly-fetched refs, never a
   stale local graph.
2. A telemetry query reading "0 rows" was run while the app was IDLE (no traffic),
   and was misread as "pipeline dead". Generating load then re-querying showed
   thousands of AppTraces rows: the pipeline worked the whole time. Lesson: a live
   smoke means generate-traffic-then-observe, not query-an-idle-system-and-assume.

The rule stands and these errors are exactly why: do not claim production state
(deployed, live, working, blind) from local assumptions or idle queries. Verify
with fresh refs, an actual deploy record, and a generate-then-observe live smoke,
every time. Had the merge proceeded on the wrong diagnosis, it would have shipped
an unrelated branch to prod and fixed nothing.
