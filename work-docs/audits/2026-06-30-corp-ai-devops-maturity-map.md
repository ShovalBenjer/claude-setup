# Corp-AI DevOps + Azure Maturity Map

Date: 2026-06-30. Org: `dev.azure.com/Corp-domain`, project `Corp-AI`. Author: Shoval.
Scope: every deployable initiative, mapped against `prod-deploy-rules` (the deploy
rules-of-record) and the live Azure estate (`AZAI_group`). Read-only audit, metadata only.
Companion to the 8-tag work applied 2026-06-30 (all 16 app resources now tagged).

## 1. Inventory snapshot

| Surface | Count | Note |
|---|---|---|
| Repos | 30 | 8 empty (size 0), the rest active or stale |
| Pipelines | 18 | 7 active, 11 parked in `\oded-archived-work` (legacy) |
| Variable groups | 4 | hold secret KEYS inline (KV-backing not confirmed) |
| Environments | 5 | only agent-call-tracker, video, sentimark, + generic prod/preview |
| Service connections | not enumerable | CLI token returned 0; verify in portal (permission or scoping) |
| Agent pools | Microsoft-hosted only | no self-hosted pool; CodeQL can use the "Azure Pipelines" pool |
| Task groups | 0 | n/a for this container/serverless estate |
| Deployment groups | 0 | n/a (those are for VM-based deploys) |
| Advanced Security | licensed, not enabled on repos | 2 billed committers; `enableOnCreate=true`; existing repos off |

## 2. Pipeline activity (last run)

Active (registered, recent runs):

| Pipeline | Repo | Last run | Branch | Status |
|---|---|---|---|---|
| agent-call-tracker | agent-call-tracker | 2026-06-29 | main | succeeded |
| cs-agents-ci | axia-seekapa-cs-agents | 2026-06-30 | PR 391 merge | succeeded |
| qc-telephony-api-ci | qc-telephony-api | 2026-06-24 | main | succeeded |
| campaign-analysis | campaign-analysis | 2026-06-23 | feat/ads-roles-vault | succeeded (last run was a feature branch, not the deploy branch) |
| video-understanding | video-understanding | 2026-06-22 | Master | succeeded |
| social-media-agent-admin | orm-agent | 2026-06-30 | main | FAILED (live breakage on the deploy branch) |
| seekapa-training-platform | seekapa-training-platform | none in last 200 | master | DORMANT (registered, not running) |

Archived (11, folder `\oded-archived-work`, treat as dead until reclaimed): sentimark-backend-deploy,
market-daily-reports, client-evaluation-deployment, aeo-docker-deploy, tech4all-deploy,
real-time-monitor-ci, anyChat-CI-CD, BrokersHub-LATAM-SWA, Corp-AI, Seekapa-AI-Assistance,
automation-fabric-cicd.

## 3. Per-project maturity

Legend: Pipe = registered+running pipeline; Adhere = key prod-deploy-rules signals present
(CFSync, IP allowlist, health gate, notify both); Env = has an ADO environment; Tags = 8-tag
standard applied 2026-06-30.

| Project | Repo (path) | Branches | Pipeline | Adhere | Azure resources | Env | Maturity |
|---|---|---|---|---|---|---|---|
| Agent Call Tracker | agent-call-tracker | 10 (feat, no stage) | running, green | CFSync+IPr+health (reference impl) | agent-call-tracker | yes (agent-call-tracker-prod) | HIGH |
| QC Telephony | qc-telephony-api | 17 (feat, no stage) | running, green | function app; notify; CFSync n/a | func-qc-telephony-prod | no | MED-HIGH |
| CS-Agents (Seekapa/AxiaCS) | axia-seekapa-cs-agents | 11 (feat, no stage) | running, green (PR validation) | function app; CI+PR gate; CFSync n/a | func-cs-agents-hedg-prod, func-cs-agents-dev | no | MED-HIGH |
| Video Understanding | video-understanding | 2 (Master + 1 feat) | running, green | CFSync+IPr; health gate MISSING | app-video-understanding-prod | yes (production-video-understanding) | MED-HIGH |
| Social Media Agent | orm-agent/social-media-agent | shares orm-agent (stage exists) | running, FAILED 06-30 | CFSync+IPr present; pipeline currently red | COMP-SMA-PROD, hedg-card-daily-job, hedg-carousel-weekly-job | no | MED (broken) |
| Campaign Analysis | campaign-analysis | 9 (feat, no stage) | running, green | web app but CFSync + health gate MISSING | COMP-CAMPAIGN-PROD, campaign-jobs-env | no | MED |
| Training Platform | seekapa-training-platform | 7 (feat, no stage) | registered, DORMANT | CFSync+IPr+health+notify in YAML, but not running | COMP-SEEKAPAAITRAININGAPI-PROD, func-TrainingWorker-PROD, COMP-SEEKAPAAITRAININGWEB-PROD | no | MED (stale) |
| Widgora | orm-agent/widgora | shares orm-agent (stage exists) | NONE registered (YAML inert) | YAML has CFSync+IPr+health+notify; never wired | comp-widgora-prod, widgora-worker | no | LOW (manual deploy) |
| Review Alert | orm-agent/review-alert | shares orm-agent | NONE registered (orm-root YAML) | jobs deploy path unautomated | orm-review-alert-job | no | LOW (manual deploy) |
| Sentimark | sentimark (444 MB) | 4 (feat, no stage) | ARCHIVED (sentimark-backend-deploy) | deploy path unclear vs archived pipeline | sentimarkregistry (ACR), stsentimarkv2 | yes (sentimark-production) | LOW-MED (verify) |
| market-daily-reports | market-daily-reports | 1 | ARCHIVED | Oded's prod was stopped (memory) | none active | no | DEAD |
| real-time-monitor | real-time-monitor | 1 | ARCHIVED | - | - | no | DEAD |
| anyChat | anyChat | 1 | ARCHIVED | - | - | no | DEAD |
| automation-fabric | automation-fabric (173 MB) | 1 | ARCHIVED | - | - | no | DEAD/STALE |
| aeo | aeo | 2 | ARCHIVED (aeo-docker-deploy) | cert aeob.corp-domain.com exists | (AEO cert) | no | STALE |
| client-evaluation | client-evaluation | 1 | ARCHIVED | scope reduced (memory) | - | no | DEAD |
| sales-agents | sales-agents (368 MB) | 1 | none | no pipeline | - | no | LOW |
| seekapa-compliance-exam | seekapa-compliance-exam | 1 | none | no pipeline | - | no | LOW |
| taqyeem-broker-website | taqyeem-broker-website (46 MB) | 1 | none | no pipeline | - | no | LOW |
| tech4all | tech4all (77 MB) | 1 | ARCHIVED | - | - | no | STALE |

Empty repos (size 0, scaffolding debt): anychat-docker-deploy, brokershub-latam,
client-eval-docker-deploy, cs-agents-docker-deploy, kever-rachel, realtime-docker-deploy,
seekapa-training-docker-deploy, sentimark-docker-deploy.

## 4. Cross-cutting maturity gaps (ranked)

P0 (production-affecting now):
1. social-media-agent-admin FAILED on the deploy branch (2026-06-30). Live pipeline red.
2. Widgora has no registered pipeline; comp-widgora-prod + widgora-worker deploy by hand.
   The widgora YAML is complete but inert (the "register the pipeline" step was never done).
3. Review Alert job (orm-review-alert-job) has no automated deploy path.
4. Training pipeline is dormant; the 3 live Training resources drift from the repo.

P1 (security + governance):
5. Advanced Security (CodeQL + Dependency scanning) is licensed but OFF on every existing
   repo. This is the "code security" addition requested (section 6).
6. Secrets live as inline variable-group values (funcDeployPassword, AZURE_OPENAI_KEY,
   AZURE_AI_FOUNDRY_KEY, etc.), not Key-Vault-backed. Violates prod-deploy-rules rule 24.
7. Service connections not enumerable via CLI token. Confirm least-privilege + that prod
   deploys use a scoped connection, in the portal (_settings connected services).
8. No tagging step in any pipeline. The 8-tag standard (new rule H) is applied manually
   today; add an `az tag update --operation merge` step so new resources are born tagged.

P2 (flow + hygiene):
9. No stage tier. Only orm-agent has a `stage` branch; the rules' `feature -> stage ->
   prod` flow is unenforced estate-wide. 9 repos are single-branch.
10. Inconsistent deploy branches (main / master / Master, plus a "Corp"-named branch on
    campaign-analysis). Pick one per repo and set branch policy.
11. 11 archived pipelines + 8 empty repos = noise. Archive/delete to clarify the live set.
12. Only 5 environments; most projects have no environment, so no approval gate or
    deployment history. Add environments for the live projects that lack one.
13. campaign-analysis and video-understanding (public web apps) are missing the health
    gate; campaign-analysis is also missing CFSync. Bring them to the agent-call-tracker bar.

## 5. The reference implementation

agent-call-tracker is the closest to the rules (running, green, CFSync + IP allowlist +
health gate 200/403 + its own environment). Use its `azure-pipelines.yml` as the template
when wiring Widgora, fixing SMA, and reviving Training.

## 6. Code Security (GitHub Advanced Security for Azure DevOps) plan

State (probed via the AdvSec management API):
- License: ACTIVE (2 billed committers at org level).
- `enableOnCreate = true` (new repos auto-enable going forward).
- Existing repos: NOT enabled. Sampled repos show advSecEnabled=false, dependabotEnabled=false,
  codeQLEnabled=null. So the org pays for AdvSec but the active repos are unscanned.

What the requested setup maps to (per active repo, Repo Settings > Code Security):
- Dependency alerts, default setup: branch Default, triggers on push + PR. One toggle.
- CodeQL alerts, default setup: agent pool "Azure Pipelines" (the hosted pool exists and is
  valid), query suite Default, branch Default, trigger Weekly (Mondays). Language Python.
- "Bring your own tools" is the only path that needs pipeline YAML; default setup does not.

Why the settings pages you tried do not let you add it:
- `_settings/storage`, `xamlservices` (connected services), `agentqueues` are not where
  scanning is enabled. CodeQL/Dependency default setup lives on each repo's Code Security
  tab (or Project Settings > Repositories > Code Security), and CodeQL needs an agent pool
  selected in org settings. The "Azure Pipelines" hosted pool satisfies that.

Cost caveat (gate before enabling broadly): AdvSec bills per active committer across
ENABLED repos. Enabling it on more repos can raise the bill beyond the current 2 committers.
Enable on the active set first, confirm the committer count, then expand.

Priority repos to enable (Python, active): axia-seekapa-cs-agents, qc-telephony-api,
campaign-analysis, orm-agent, seekapa-training-platform, agent-call-tracker,
video-understanding. Skip archived/empty repos.

## 7. What to do, where (action list)

P0:
- [ ] Fix social-media-agent-admin (read the failed run log, repair, re-run).
- [ ] Register the Widgora pipeline (widgora/earning-calendar/azure-pipelines.yml) as an ADO
      pipeline; wire its variable group + service connection; first run on a feature branch.
- [ ] Decide Review Alert + hedg jobs deploy path: a container-apps-job pipeline, or fold
      into the SMA/orm-agent pipeline.
- [ ] Run the Training pipeline (or confirm it is intentionally frozen and tag it so).

P1:
- [ ] Enable Dependency + CodeQL default setup on the 7 priority repos (after the cost check).
- [ ] Move inline variable-group secrets to Key Vault references (rule 24); rotate any that
      were committed.
- [ ] Audit service connections in the portal; confirm scoped, least-privilege, no broad
      Owner-level connection.
- [ ] Add an `az tag update --operation merge` tagging step to the shared pipeline template
      so new resources are born with the 8 tags (rule H).

P2:
- [ ] Introduce a stage branch + environment per active project; set branch policy to enforce
      feature -> stage -> prod.
- [ ] Normalize each repo's default branch and document it.
- [ ] Archive/delete the 11 legacy pipelines and 8 empty repos.
- [ ] Add ADO environments for the active projects that lack one (Widgora, SMA, Campaign,
      Training, CS-Agents, QC) to get approval gates + deploy history.
- [ ] Add the health gate to campaign-analysis + video-understanding; add CFSync to
      campaign-analysis.

## Method / caveats

- Pipeline adherence was scored by signal grep over the local YAMLs; CFSync and health-gate
  strings are reliable, notify-both is approximate (verify by reading the YAML before acting).
- Service connections and exact AdvSec per-repo state need a portal confirm (CLI token scope).
- All enablement, AdvSec, and secret moves remain proposals pending explicit per-action OK
  (several carry cost or are outward-facing). Pipeline wiring below was done under explicit
  "fix and wire" authorization.

## Update — 2026-06-30 (execution pass)

The section 2-3 snapshot was captured before the day's merges. Corrections + work delivered:

- SMA pipeline: GREEN, not red. Failed build 13603 was the pre-fix commit a1da2a04; PR 395
  merged the e2e DEV-stub fix to main (6995185) and builds 13606/13607 succeeded. The failing
  tests were PRD-gated Phase-3 admin-UI work, fixed on the owner's feat/admin-ui branch. No
  action taken (did not touch the 13 in-flight WIP files).
- Training pipeline: healthy, not dormant. Last green build 13016 on 2026-06-08; no commits
  since. Downgraded from P0.
- Widgora: pipeline WIRED + CI verified green. New ADO pipeline `widgora-dashboard` (def id
  137, folder \Marketing) registered against orm-agent, YAML at
  widgora/earning-calendar/azure-pipelines.yml on branch feat/widgora-pipeline. Concrete and
  rules-compliant: reuses ARM service connection 6d2cd8b6 + ACR sentimarkregistry, builds on
  the agent, deploys comp-widgora-prod, CFSync (CF IPs + deny-all), /healthz gate, keep-5,
  Telegram notify (skips if unset). No var-group/secret dependency. Deploy stages gate on main;
  CI run 13617 succeeded on the feature branch. Promotion to main is a human-approved PR.
  Follow-up: open the PR feat/widgora-pipeline -> main (deploy fires on merge); the inert
  skeleton was superseded in place.
- Branch-promotion rule added to prod-deploy-rules (section I, rules 31-33 + checklist line):
  no auto-merge feature->stage, no auto-merge stage->prod, enforce via branch policy.
- Branch policies: NONE exist on main in any active repo (orm-agent + agent-call-tracker
  verified: 0 policies). Enforcing rules 31-33 (build validation + require-PR + reviewers) is a
  pending, team-affecting rollout awaiting scope + reviewer-count decision.
- Org standard of record = the Corp-domain "Corp Home" wiki (SAML/Entra SSO, Azure-group ->
  role -> access:{slug} RBAC, per-app jwt_secret in app settings, COMP-<NAME>-PROD deploy on
  trunk + ACR keep-N + Telegram notify). prod-deploy-rules aligns with it. Documentation gap:
  Corp-AI projects have no equivalent wiki; add per-app Auth/CICD/Roles/Codebase pages.
- AdvSec: licensed (2 billed committers), enable-on-create true, existing repos OFF. Enable
  steps prepared; gated on explicit cost OK (billing scales per active committer across enabled
  repos).
