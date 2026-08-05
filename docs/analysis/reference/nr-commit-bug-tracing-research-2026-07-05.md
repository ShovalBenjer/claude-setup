# Commit-to-Bug Time-Continuous Tracing on Azure DevOps + Agentic Flow

OSS / self-hostable tooling research. Date: 2026-07-05. Author: Shoval (via Claude Code deep-research).
Context: Azure DevOps (Azure Repos Git + Azure Pipelines), Azure Functions (Python), AI coding agents
(Claude / Codex). Goal: backward "which commit led to which bug", exact time-continuous tracing.

Companion to the live diagnosis of `agent-call-tracker` (pipeline def 135): CI runs but writes no git
commit status, 0 branch policies, PR builds run on `refs/pull/*/merge` not real commits. That report
covers the ADO-native fix (POST commit statuses + branch-policy build validation). This report covers
the runtime "commit -> bug" half that ADO does not do natively.

---

## Executive summary

The one idea that ties everything together: **make the git commit SHA the join key across the whole
lifecycle.** Stamp it once at deploy, and it threads build status, deploy markers, runtime errors, and
observability into a single backward-traceable timeline. Every tool below is just a consumer of that SHA.

The minimal, mostly-OSS stack for your stack, in priority order:

1. **Foundation (free, native, do first):** stamp `service.version = <SHA>` as a Function App setting at
   deploy; POST the commit status from CI; keep using the `agent-call-tracker-prod` ADO Environment as
   your deploy timeline. Cost: 0.
2. **Runtime error -> suspect commit (highest leverage):** self-hosted **Sentry** (Functional Source
   License, free for in-house self-host) with its first-class **Azure DevOps** integration for suspect
   commits + release/commit association. Pure-OSS alternative: **GlitchTip** (MIT), Sentry-SDK
   compatible, but commit linking is generic-git, not native ADO.
3. **Regression culprit-finding (agentic):** `git bisect run` driven by your agent against a repro; for
   performance regressions, **Apache Otava** / **Nyrkiö** or **Bencher** (all Apache-2.0 core) in CI.
4. **Observability SHA-stamping:** OpenTelemetry `service.version` = SHA on every trace/log/metric
   (you already ship to App Insights via `azure-monitor-opentelemetry`); optional Grafana deploy
   annotations via the native ADO service hook.
5. **Agent bridge:** Microsoft's official **Azure DevOps MCP server** (GA Oct 2025) so Claude/Codex can
   read pipeline status, commits, PRs, and work items directly, and drive the bisect loop.

Honest caveats up front: Sentry is Fair Source, not OSI-open-source (converts to Apache-2.0 after two
years) [2][3]; the OpenTelemetry VCS attributes are still experimental, so lean on the stable
`service.version` [5]; GlitchTip has no native Azure DevOps commit integration [4]; the Grafana Azure
DevOps data-source plugin is a paid Enterprise plugin (the service-hook annotation path is free) [10].

---

## Q1. Binding commits/SHAs to CI/CD status and deploy markers

### Azure DevOps native (use these first; they are free and already partly wired)
- **Git commit Status REST API.** `POST /_apis/git/repositories/{repo}/commits/{sha}/statuses` with a
  `state` + `context.genre`. Azure Pipelines does not auto-post this for its own CI on Azure Repos, which
  is exactly why your commits list is blank. A one-line pipeline step that POSTs it fixes the badge and
  makes the verdict API-queryable. (See the diagnosis report for the ready YAML step.)
- **Branch-policy Build Validation.** The sanctioned enforced status check on a PR. You have 0 policies;
  adding one binds a blocking green/red to every PR.
- **Environments / Deployments.** `agent-call-tracker-prod` (env id 10) already records each deploy ->
  commit with timestamps. That is your native deploy timeline; enrich it by stamping the SHA (Q4).

### OSS deploy-marker / release-annotation layer
- **CDviz** (open source, CDEvents-based) [9]. Observability platform built on the CD Foundation's
  **CDEvents** standard; normalizes delivery events into PostgreSQL/TimescaleDB and ships pre-built
  Grafana deployment-timeline + DORA dashboards. Bridge Azure Pipelines events into it via webhook.
- **Grafana annotations (native ADO path)** [10]. Azure DevOps has a built-in Grafana service hook: on
  "Release deployment completed" it POSTs a deployment marker to Grafana `/api/annotations`. Free; the
  Grafana *data-source* plugin for querying ADO is paid Enterprise, but the annotation push is not.

Agent usage: a coding agent posts the commit status and the deploy marker with a single `curl` to the
respective REST endpoints, keyed on `$(Build.SourceVersion)`.

---

## Q2. Automatically finding which commit introduced a regression

### `git bisect run` (the core primitive, and the best agentic fit) [7][8]
Binary search over history: `git bisect start; git bisect bad <bad>; git bisect good <good>;
git bisect run ./repro.sh`. The script exits 0 = good, 1-127 (except 125) = bad, 125 = untestable/skip.
It converges in ~log2(N) steps and prints the first bad commit's hash/author/message. This is the single
most powerful thing your agent can do autonomously: given a failing test or repro, an agent runs
`git bisect run` and comes back with the culprit SHA, no human in the loop. Ideal when the bug is
deterministic and commits are independently buildable (your Azure Functions Python app qualifies).

### Performance-regression / change-point detection (which commit moved the number)
- **Apache Otava (incubating)** / **Nyrkiö** [8b]. Apache-2.0. E-Divisive Means change-point detection
  over a benchmark time series; reliably flags even ~1% regressions and attributes them to a commit.
  Otava is the CLI/library (ex-"Hunter", built over 8 years at MongoDB/Datastax/Confluent); Nyrkiö is the
  self-hostable service around it that can open a GitHub issue or Slack on a detected regression.
- **Bencher** [4b]. Apache-2.0 / MIT core (source-available "plus" features), fully self-hostable
  (Docker/K8s). Runs your existing benchmarks in CI on stable hardware and fails the PR on regression,
  tracking results per commit/branch. Used by Microsoft CCF, GitLab, Mozilla, Servo, Diesel.

Agent usage: the agent invokes the bisect/benchmark CLI and parses the culprit commit from stdout or the
tool's REST API, then opens a fix PR.

---

## Q3. Linking runtime errors/exceptions back to the suspect commit

### Sentry, self-hosted (best ADO integration; Fair Source, free in-house) [1][2][3]
- **What:** error/crash tracking with releases and **suspect commits**: for an issue whose stack-trace
  files match files in commits sent to Sentry, it shows the suspect commit + author as suggested
  assignee, and links the stack frame to the exact source version at error time [1].
- **Azure DevOps integration is first-class** (formerly VSTS): commit tracking, suspect commits,
  stack-trace linking, and two-way work-item creation/linking [1]. This is the differentiator over the
  OSS alternatives.
- **License:** Functional Source License (FSL-1.1-Apache-2.0). Free to run/modify/self-host for any
  purpose except selling a competing Sentry-like SaaS; each release converts to Apache-2.0 after two
  years. Not OSI-open-source, but unrestricted for your in-house use [2][3].
- **Critical caveat for your PR-merge flow:** "the commit must be associated with a release, otherwise if
  the commit is squashed Sentry won't know when the commit was released, and the issue may never be
  marked as a regression" [1]. So you must create a Sentry **release = the deploy SHA** and set its
  commits. This is why Q1/Q4 SHA-stamping is a prerequisite, not optional.
- **Python Azure Functions:** `sentry-sdk` with `release=<SHA>`; in CI, `sentry-cli releases new <SHA>`
  then `sentry-cli releases set-commits <SHA> --auto`.
- **Agent usage:** REST API (query issues -> suspect commit); Sentry also ships an MCP server for
  agent-native root-cause queries. Verify exact MCP capabilities against current docs before relying.

### GlitchTip (pure OSS alternative; MIT) [4]
Sentry-API compatible (keep your `sentry-sdk` clients, point them at your server). MIT-licensed,
lightweight Django app. `glitchtip-cli releases set-commits <ver> --auto` auto-discovers commits from
git, plus deploy tracking. Trade-off: **no native Azure DevOps integration** - commit linking is
generic git auto-discovery, and there is no ADO work-item sync. Choose it if strict OSI-OSS licensing
matters more than the native ADO wiring.

Also in this space (verify license/ADO fit before adopting): Highlight.io, OpenObserve, SigNoz, Bugsink,
Apache SkyWalking. None match Sentry's native ADO suspect-commit integration today.

---

## Q4. Observability that stamps the git SHA onto traces/logs/metrics

### Use the stable attribute: `service.version` [5]
- The OpenTelemetry **VCS semantic conventions** (`vcs.ref.head.revision`, `vcs.ref.base.revision`) are
  the "correct" home for a commit SHA, but they are still **experimental** in 2026 (the VCS entity has
  attributes without defined roles, which blocks stabilization) [5]. Note: the attribute is
  `vcs.ref.head.revision`, not `vcs.repository.ref.revision`.
- So stamp the SHA on the **stable** `service.version` resource attribute now, and optionally also emit
  `vcs.ref.head.revision` for forward-compatibility. Set it at deploy:
  `OTEL_RESOURCE_ATTRIBUTES=service.version=$(Build.SourceVersion)` as a Function App setting, or pass it
  into `configure_azure_monitor()` / the OTel Resource in your Python startup.
- **Azure-native:** you already export to Application Insights via `azure-monitor-opentelemetry`. With
  `service.version` set, every trace, log, and exception carries the SHA, so you filter any signal by
  commit. App Insights also supports **release annotations** on metric charts to mark deploys [11].
- **CI/CD observability:** OTel has CICD span/metric/log semconv and `otel-cli` can emit a span per
  pipeline run, so the build itself becomes a trace correlated by SHA [5b].

Agent usage: the agent queries traces/logs/exceptions filtered by `service.version = <SHA>` (KQL in App
Insights, or LogQL/TraceQL in Grafana Loki/Tempo) to see which release an error belongs to.

---

## Q5. The agentic glue (recommended minimal stack)

### Azure DevOps MCP server, Microsoft official [6]
`microsoft/azure-devops-mcp`, GA since Oct 2025. Gives a Claude/Codex agent secure, local (or remote,
`https://mcp.dev.azure.com/{org}`, Entra auth) access to domains: core, work, work-items, search,
test-plans, repositories, wiki, **pipelines**, advanced-security. The agent can ask "status of the latest
build for main", read PRs, and inspect pipeline results directly. Supports `ADO_MCP_AUTH_TOKEN` env-var
auth for CI, and an `X-MCP-Readonly` header to keep the agent read-only. For local Claude Code / Codex,
the local server is the supported path today (remote-server OAuth registration for those clients was
still being enabled).

### The end-to-end loop a coding agent runs
```
build:   stamp SERVICE_VERSION = <SHA>; POST commit status; sentry-cli releases new <SHA> + set-commits
deploy:  ADO Environment records SHA; post Grafana/App Insights deploy annotation
runtime: exception fires -> Sentry release=<SHA> -> suspect commit + author surfaced
agent:   read suspect commit via Sentry REST/MCP + build status via ADO MCP
confirm: git bisect run ./repro.sh  ->  culprit SHA (autonomous)
fix:     agent opens PR; branch-policy build validation gates the merge (green/red bound to the commit)
```

### Code-intelligence layer (optional, for symbol -> commit mapping)
Sourcegraph (self-hostable; verify current license tier) or OpenGrok (Apache-2.0/CDDL) index the repo so
the agent can jump from a symbol in a stack trace to its introducing commit via `git blame`.

---

## Recommendations (owned + dated)

- **ACTIONABLE (Shoval, by 2026-07-08):** Add the commit-status POST step + one branch-policy build
  validation on `agent-call-tracker` main. Closes the ADO-native gap; zero cost. (See diagnosis report.)
- **ACTIONABLE (Shoval, by 2026-07-12):** Stamp `service.version = $(Build.SourceVersion)` as a Function
  App setting at deploy across the active repos. This one change is the join key that unlocks Q3+Q4.
- **DIRECTIONAL:** Stand up self-hosted Sentry (FSL) with the Azure DevOps integration for suspect
  commits, OR GlitchTip (MIT) if OSI-OSS licensing is a hard requirement. Requires a container host;
  weigh against the existing App Insights spend before committing.
- **DIRECTIONAL:** Wire the Microsoft Azure DevOps MCP server into the Claude/Codex flow (read-only
  first), and script an agent `git bisect run` harness against a repro test.

## Limitations & caveats

- Sentry is Fair Source (FSL), not OSI-open-source; fine for in-house self-host, but flag it if a policy
  requires OSI licenses [2][3].
- OTel VCS/CICD conventions are experimental; `service.version` is the stable bet [5].
- GlitchTip's ADO commit linking is generic git, no native integration or work-item sync [4].
- The official ADO MCP remote server's OAuth registration for Claude Code / Codex was still being
  enabled; use the local server for those clients and verify current status [6].
- The Grafana Azure DevOps *data-source* plugin is paid Enterprise; the deploy-annotation service hook is
  free [10].

## Bibliography

1. Sentry, Azure DevOps integration (commit tracking, suspect commits, stack-trace linking, work items). https://docs.sentry.io/integrations/source-code-mgmt/azure-devops/
2. Sentry, Licensing (Functional Source License / Fair Source). https://open.sentry.io/licensing/
3. Sentry Blog, Introducing the Functional Source License. https://blog.sentry.io/introducing-the-functional-source-license-freedom-without-free-riding/
4. GlitchTip (MIT, Sentry-API compatible) + CLI releases/deploys. https://glitchtip.com/ and https://glitchtip.com/documentation/cli/
4b. Bencher, self-hosted continuous benchmarking (Apache-2.0/MIT core). https://github.com/bencherdev/bencher and https://bencher.dev/docs/explanation/bencher-self-hosted/
5. OpenTelemetry VCS semantic conventions (experimental). https://opentelemetry.io/docs/specs/semconv/registry/entities/vcs/
5b. OpenTelemetry CI/CD resource + spans/metrics semconv. https://opentelemetry.io/docs/specs/semconv/resource/cicd/
6. Microsoft Azure DevOps MCP Server. https://github.com/microsoft/azure-devops-mcp and https://learn.microsoft.com/en-us/azure/devops/mcp-server/mcp-server-overview
7. Fully automated bisecting with "git bisect run" (LWN). https://lwn.net/Articles/317154/
8. Automate finding a regression commit with git bisect run. https://staabm.github.io/2026/02/07/git-bisect-run
8b. Nyrkiö / Apache Otava change-point detection (Apache-2.0). https://github.com/nyrkio/nyrkio and https://blog.nyrkio.com/2025/05/08/welcome-apache-otava-incubating-project/
9. CDviz, CDEvents-based delivery observability with Grafana dashboards. https://cdviz.dev/
10. Azure DevOps -> Grafana service hook (deploy annotations). https://learn.microsoft.com/en-us/azure/devops/service-hooks/services/grafana
11. Application Insights release annotations. https://learn.microsoft.com/en-us/azure/azure-monitor/app/annotations
