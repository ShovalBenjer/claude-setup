# Claude Code Mastery, Evidence, and Learning-Corpus Audit

Verified: 2026-07-25, Asia/Jerusalem  
Primary target: `claw-army/awesome-claude-code-mastery`  
Local Claude Code: 2.1.220, first-party subscription routing  
Research prompt written before the deep pass:
[`2026-07-25-claude-mastery-research-prompt.md`](2026-07-25-claude-mastery-research-prompt.md)

## Executive decision

Do not install or copy the “awesome” repository wholesale.

Use it as a discovery index frozen at commit
[`b5b1f7f`](https://github.com/claw-army/awesome-claude-code-mastery/commit/b5b1f7f4935f41b9b905c6049e7bb4ce41ce7d43),
then evaluate individual resources against official documentation, local needs,
security, maintenance, and executable evidence.

The useful upgrade is not “more prompts.” It is a smaller control plane:

1. short, project-neutral global instructions;
2. just-in-time skills and source retrieval;
3. explicit alternatives before non-trivial implementation;
4. executable oracles and repository-state-bound proof;
5. a skeptical evaluator separated from the authoring context;
6. a fail-closed learning → attempt → project → resume evidence lineage; and
7. current vendor documentation for changing implementation details.

This has now been implemented locally. It does not establish that any generated
implementation is globally optimal. It makes the decision falsifiable and
prevents a familiar default from being called “best” without comparative proof.

## What was actually covered

### Mastery repository

The live GitHub repository still points to the same latest commit on the cutoff:
March 24, 2026. All six tracked files were read:

| File | Lines | Role |
|---|---:|---|
| `README.MD` | 1,610 | Curated external-resource index |
| `CONTRIBUTING.md` | 149 | Contribution policy |
| `.github/workflows/link-checker.yml` | 43 | Monthly link check |
| `.gitignore` | 40 | Ignore policy |
| `favicon.svg` | 28 | Branding |
| `docs/.gitkeep` | 3 | Empty placeholder |

The repository contains 838 URL occurrences and 791 unique URL lexemes across
tracked files. The README body contains 779 navigational occurrences and 760
unique destinations. Every destination was inventoried and normalized. The
latest available link-check result was inspected, and selected high-value,
security-sensitive, current, or official destinations were content-reviewed.

This does **not** mean all 760 external destinations were read end to end. That
would be a false coverage claim and a poor stopping rule for a changing link
directory.

### Technology, resumes, work resources, and learning platform

The adjacent technology-corpus pass inspected 117 canonical URL entries across
26 source families. It deep-read 14 Cloudflare Pipelines pages and inspected 49
Cloudflare URL entries across the selected families. Three attempted external
pages remain explicit failures rather than being counted as reads.

Local coverage included:

- the canonical resume generator, routing configuration, active and legacy
  resume artifacts, screening pack, LinkedIn pack, and regression tests;
- 85 PDF/DOCX/HTML resume artifacts in the earlier coverage pass;
- current project manifests, work contexts, handoffs, project evidence,
  readable Git bundles, and selected source/tests/configuration;
- the learning platform’s frontend/API contracts, current and legacy database
  schemas, migrations, scoring paths, representative tests, CI, and PRD.

The production learning database, remote voice agents/prompts, customer data,
and live deployments were **not** accessed. “Visible locally” and “verified in
production” remain separate states.

The detailed, updated ledger is in
[`02_COVERAGE_AUDIT.md`](../../../Downloads/new-recruit/docs/technology-corpus/02_COVERAGE_AUDIT.md).

## Repository trust assessment

### Provenance and maintenance concerns

- The repository is overwhelmingly a copy of Shrey Shah’s resource list. The
  fork-specific substantive addition is `claw-army/claude-node`.
- The stars badge, hosted site, issue link, and several contribution references
  still point to the original `shahshrey` project.
- A CC0 badge is displayed, but the audited commit has no tracked `LICENSE` or
  `COPYING` file. A badge alone is not a sufficient rights record.
- The README contains dated star counts, pricing references, Chrome-extension
  references, and command terminology that can drift.
- The link workflow uses movable action tags, does not declare least-privilege
  permissions, and configures the checker with `fail: false`. The later
  issue-creation condition therefore does not reliably make broken links fail
  the workflow.
- The last inspected link report contained substantial redirects and errors,
  while the workflow could remain green. Link-check success is not source
  quality, safety, compatibility, or maintenance evidence.

### The unique `claude-node` addition

Do not adopt it into this Windows subscription setup.

Its own README describes it as alpha, says Windows has not been validated, and
shows `skip_permissions=True` in the primary examples. It drives the installed
Claude CLI as a persistent subprocess and supports session continuation. That
combination expands the permission, environment inheritance, lifecycle, and
secret-exposure surface without solving a current requirement.

The package may be useful in an isolated, explicitly sandboxed Linux experiment.
It is not an appropriate default controller for a host-level Windows Claude
installation.

### Resource disposition

| Disposition | Resources |
|---|---|
| Adopt as authority | Official Claude Code docs, Anthropic engineering/system cards, current vendor docs, standards, executable local evidence |
| Evaluate individually | `jezweb/claude-skills`, Trail of Bits skills, official `claude-code-action` |
| Reference patterns only | `fcakyon/claude-codex-settings`, `ChrisWiles/claude-code-showcase` |
| Reject as defaults | bulk marketplaces, unofficial gateways/proxies, remote auto-approval controllers, duplicate memory systems, `claude-node` on this host |

No third-party plugin, marketplace, MCP server, gateway, or controller was
installed during this run.

## Why Claude appears “lazy”

“It wrote a `for` loop” is not enough to diagnose laziness. A plain loop may be
the most correct option when order, backpressure, rate limits, memory, error
isolation, or small input sizes dominate.

The real failure classes are:

1. **Distributional defaulting** — a familiar loop/library/architecture has high
   prior probability, so it appears before workload constraints are modeled.
2. **Under-specified success** — “make it fast” or “production-ready” has no
   executable oracle.
3. **Search truncation** — one plausible solution is emitted before viable
   alternatives are compared.
4. **Context dilution** — stale rules, duplicated instructions, long traces,
   and irrelevant tools compete with the current contract.
5. **Premature completion** — the model infers “done” from visible progress,
   context pressure, or a passing happy-path test.
6. **Self-review leniency** — the authoring context knows its own rationale and
   tends to explain away defects.
7. **Outcome/trace mismatch** — a convincing final message is mistaken for the
   filesystem, database, deployment, or user-visible state.
8. **Harness failure** — lost tool state, unsafe permissions, broken hooks,
   compaction, or a stale proof record makes a capable model look unreliable.
9. **Reward or grader gaming** — a static check can be satisfied without
   delivering the intended outcome.

Anthropic’s own harness work reports context anxiety, premature completion,
under-scoping, and overly generous self-evaluation; it recommends explicit
contracts, structured handoffs, and a separate evaluator. Its eval guidance
also distinguishes a model’s final statement from the actual environment
outcome:

- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

## The implemented anti-default proof gate

The new `prove-implementation` skill treats model output as a candidate, not
evidence.

For non-trivial work it requires:

1. observable acceptance criteria and external oracles;
2. at least two candidates, or three for high-risk work;
3. the simplest correct candidate among the alternatives;
4. explicit loop/I/O/N+1/batching/pushdown/streaming/indexing/bounded-concurrency
   analysis;
5. recorded complexity, operational, failure, maintenance, and reversibility
   trade-offs;
6. executable checks with command, exit status, time, output digest, Git commit,
   tracked diff, and bounded untracked-file fingerprint;
7. representative benchmark results before comparative superlatives;
8. a fresh independent review for high-risk work; and
9. residual-risk reporting.

The validator invalidates a record when any declared check fails, when an
acceptance criterion lacks a passing check, when a launch fails or times out,
when the repository state changes, or when a “best/optimal/fastest/complete”
claim lacks a multi-candidate benchmark.

The state fingerprint refuses automatic proof for a home/root repository, does
not follow untracked symlinks, redacts common secret-bearing paths, and stops
when file/count/byte budgets would make the fingerprint incomplete.

The pre-push hook asks for review when behavior-affecting files change without a
valid proof. It understands current source, notebook, component, schema,
Cloudflare, compiler, package, lock, build, workflow, migration, and deployment
formats. It resolves `@{push}`, rejects ambiguous multi-ref/default/refspec
configurations, and binds proof to the current state.

This proves only:

> the selected candidate satisfied the declared oracles and beat or matched the
> tested alternatives under the recorded conditions.

It does not prove global optimality or eliminate hidden requirements.

## Current model comparison without invented Claude internals

Claude’s exact parameter count, attention layout, MoE routing, training corpus,
and decoding/search implementation are not public. They must not be reverse
engineered from product behavior and presented as fact.

| Model surface at cutoff | Publicly supported architecture facts | Practical implication |
|---|---|---|
| Claude Fable 5 / local Opus 5 | Anthropic publishes capability and safety evaluations, but not the detailed model architecture. Local Claude Code reported a 1,000,000-token context window for the working Opus 5 alias. | Treat Claude as a closed model inside an observable harness. Measure outcomes, traces, state changes, and multi-trial reliability. Do not invent decoder internals. |
| Kimi K3 | Vendor reports 2.8T parameters, Kimi Delta Attention, Attention Residuals, Stable LatentMoE, 16/896 active experts, and up to 1M context. Full weights/report were scheduled for July 27, after this July 25 cutoff. | Architecture claims are useful hypotheses, not independently reproducible evidence yet. Do not redesign the stack around pre-release claims. |
| DeepSeek V4 Pro / Flash | Vendor reports Pro at 1.6T total/49B active, Flash at 284B/13B active, token-wise compression plus DeepSeek Sparse Attention, open weights, and 1M context. | Useful as an isolated external candidate/reviewer. Thinking-mode traces must be preserved across tool-call turns; unsupported sampling controls are ignored. |

Primary sources:

- [Claude Fable 5 / Mythos 5](https://www.anthropic.com/news/claude-fable-5-mythos-5)
- [Fable 5 / Mythos 5 system card](https://www-cdn.anthropic.com/2f9323abbcc4abe219577539efe19a623c9ca2bd/Claude%20Fable%205%20%26%20Claude%20Mythos%205%20System%20Card.pdf)
- [Kimi K3 technical blog](https://www.kimi.com/blog/kimi-k3)
- [DeepSeek V4 release](https://api-docs.deepseek.com/news/news260424/)
- [DeepSeek thinking-mode contract](https://api-docs.deepseek.com/guides/thinking_mode/)

### Model policy

- Keep first-party Claude subscription routing for daily Claude Code work.
- Use the strongest available Claude model for hard planning/review and a
  cheaper/faster model only after a task-specific eval shows no unacceptable
  regression.
- Do not assume a competing model is a better judge merely because it is
  different.
- If Kimi or DeepSeek is evaluated, run it in an isolated harness against the
  same task, tools, constraints, trials, and independent executable oracle.
- Never feed private work, credentials, customer data, or proprietary prompts
  to an external provider merely to obtain “model diversity.”

## Local Claude Code enhancements

### Configuration

- `model: opus` currently resolves to the working local Opus 5 surface.
- `effortLevel: xhigh`.
- Adaptive thinking and the available 1M context are no longer disabled.
- Forced Sonnet worker routing was removed.
- Default permissions changed from bypass to `acceptEdits`.
- `disableBypassPermissionsMode: "disable"` prevents re-enabling bypass.
- Remote Control no longer starts automatically.
- Dangerous-mode prompt suppression was removed.
- The global skill-listing budget is 0.02.
- Persisted invalid model aliases and stale global task instructions were
  removed.

The global contract is approximately 3.2 KB. Nine unconditional rules total
approximately 3.3 KB; eight heavier rules are path-scoped. This reduces context
competition while retaining hard boundaries.

### Hooks

- `safety_gate.py`: common destructive Git/filesystem operations, remote
  pipe-to-shell patterns, and common credential-output paths.
- `pre_push_gate.py`: exact push-target resolution and current-state-bound
  implementation proof.
- `completion_gate.py`: blocks unsubstantiated completion language in English
  and Hebrew while preventing Stop-hook loops.
- compact session start/pre-compact handoffs without stale task injection.

Regex shell guards are defense in depth, not an operating-system security
boundary. Exotic equivalent shell spellings will always exist; permissions,
sandboxing, least privilege, and human review remain primary controls.

### Security remediation

Two credential-shaped values were found inside project permission allow lists:

- `projects/qc-telephony-api/.claude/settings.local.json`
- `projects/seekapa-training-platform/.claude/settings.local.json`

The two entries were removed without printing their values or making
secret-bearing backups. A disposable Temp snapshot’s affected settings file
was also removed.

Removal prevents future reuse by Claude but does not revoke a credential that
may already have been exposed. Rotate the affected credentials and reintroduce
them through an environment/secret store rather than a permission rule.

## Rights-aware learn-on-demand corpus

The new corpus contains 32 selected records:

- 25 published books available by the cutoff;
- 4 current competence/workforce/taxonomy sources; and
- 3 explicitly non-final watchlist books.

Commercial books remain metadata-only until the user explicitly attests lawful
access and private processing rights for a local copy. Extracted chunks stay in
`~/.claude/private-knowledge`, are never committed, and can be revoked. The
SQLite index binds itself to the catalog SHA-256 and rebuilds when metadata
changes.

Reading is not evidence of skill. The promotion ladder is:

```text
source metadata/text
  -> learning objective
  -> exercise
  -> retained passing attempt
  -> reviewed project contribution
  -> deployment evidence when claimed
  -> exact human-approved resume wording
```

### Every selected book by domain

#### Software design, correctness, testing, and concurrency

1. *Software Engineering at Google* — maintenance, review, testing at scale.
2. *Learning Domain-Driven Design* — model the domain before choosing a stack.
3. *Effective Software Testing* — derive tests from contracts and boundaries.
4. *Practical TLA+* — state machines, invariants, liveness, model checking.
5. *A Science of Concurrent Programs* (2026) — safety, liveness, fairness,
   refinement.
6. *Property-Based Testing with PropEr, Erlang, and Elixir* — generators,
   shrinking, model/state-machine testing.

#### Distributed, data, and cloud systems

7. *Designing Data-Intensive Applications, 2nd Edition* (2026) — workload,
   consistency, failure, storage, and streaming trade-offs.
8. *Designing Distributed Systems, 2nd Edition* — reusable distributed-system
   patterns and operational boundaries.
9. *Fundamentals of Data Engineering* — lifecycle, architecture, ingestion,
   transformation, orchestration, governance.

#### Security and reliability

10. *Web Application Security, 2nd Edition* — modern web threat and control
    surfaces.
11. *Threat Modeling: Designing for Security* — assets, trust boundaries,
    attack paths, mitigations.
12. *Site Reliability Engineering* — SLOs, error budgets, toil, incidents, and
    production operations.

#### AI, agents, ML systems, context, and evaluation

13. *AI Engineering* — foundations-to-application AI system design.
14. *AI Agents in Action, Second Edition* (June 2026) — current agent patterns.
15. *Designing Machine Learning Systems* — data/model/system feedback loops.
16. *Reliable Machine Learning* — production ML reliability and operations.
17. *Prompt Engineering for LLMs* — prompt/context design without treating
    wording as the whole system.
18. *Practical LLM Evaluation for Production Systems* (June 30, 2026) —
    evaluator design, regression, production feedback.

#### Product, UX, delivery, teams, and platform engineering

19. *Laws of UX, 2nd Edition* — usable interfaces and cognitive constraints.
20. *Continuous Discovery Habits* — evidence-driven product decisions.
21. *Accelerate* — measurable delivery performance.
22. *Team Topologies, Second Edition* — ownership, cognitive load, interaction
    modes.
23. *Platform Engineering on Kubernetes* — self-service APIs, golden paths,
    GitOps, progressive delivery.

#### Career and truthful resume positioning

24. *The Software Engineer’s Guidebook* — realistic level/impact calibration.
25. *The Tech Resume Inside Out* — relevance, evidence, scanability, and
    truthful claim selection.

### Canonical bridge frameworks

26. ESCO 1.2.1 — stable multilingual occupation/skill concept URIs.
27. O*NET 30.3 — occupation, task, activity, knowledge, skill, and level data.
28. NICE Framework Components 2.0.0 — cybersecurity roles/tasks/knowledge/skills.
29. DigComp 3.0 — proficiency-aware digital and AI competence.

### Non-final watchlist

30. *Site Reliability Engineering, 2nd Edition* — September 2026 target.
31. *Evals for AI Engineers* — October 2026 target; contents not final.
32. *LLM Evaluation and Alignment, The Foundational Ideas* — MEAP/Fall 2026.

Announced books are excluded from normal query results unless
`--include-announced` is explicitly used.

The complete official publisher/government URL, date, rights, weak-point, and
intended-use ledger is in:

- `learn-on-demand/references/catalog.json`
- `book_catalog_sources.md`
- `book_catalog_proposal.json`

## Learning-platform and resume-engine bridge

The technology corpus currently validates:

- 26 source families;
- 10 lessons;
- 22 market/resume signals; and
- 12 evidence records.

The new sidecar defines six content-addressed objects:

```text
source_revision
  -> learning_objective
  -> exercise
  -> attempt_evidence
  -> project_evidence
  -> resume_claim
```

It enforces exact source/card hashes, real ESCO or O*NET identifiers, versioned
objective/exercise references, deterministic attempt evidence, candidate
contribution, contradiction resolution, full repository commit IDs, artifact
hashes, review expiry, active resume lanes, exact claim-text hashes, and
deployment evidence for production claims.

All top-level and per-record automatic learning/resume write flags must be
`false`.

All 32 learn-on-demand records are also exposed through a metadata-only
projection bound to the canonical catalog hash. Together with the 26 technology
cards, the bridge can address 58 sources. The projection copies no book text,
narrows every source to `metadata_summary_links`, labels the three watchlist
books non-final, and fails closed on catalog drift, missing/extra records,
rights widening, content inclusion, or automatic promotion.

The checked-in evidence registry remains empty. That is intentional: no book,
documentation page, taxonomy match, time spent, or quiz was fabricated into
project or resume evidence.

The sidecar is implemented and tested but is **not a production database
integration**. The learning-platform snapshot has divergent schema sources and
no safe general curriculum import seam; production is VNET-only and was not
queried.

## Resume remediation performed

The contradicted `24% to 64%` support-agent claim was removed from:

- the canonical resume generator;
- two tailored resume overrides;
- the 60-second screening narrative;
- the LinkedIn profile pack;
- the A/B outreach plan; and
- the active project manifest.

It was replaced with the evidence-supported statement that prompt and
knowledge-base evaluation tooling was built and agent behavior was iterated
against scored test sets.

All 11 current `ShovalBenjer-*-Resume` PDF/DOCX/HTML variants were regenerated.
Legacy numbered and historical artifacts were not rewritten; they remain
historical and must not be routed as current resumes.

## Verification evidence

| Check | Result |
|---|---:|
| Mastery-control adversarial suite | 18/18 passed |
| Sidecar/corpus suite | 21/21 passed |
| Resume source claim suite | 10/10 passed |
| Rendered current-PDF suite | 24/24 passed |
| Skill package validation | 2/2 valid |
| Claude setup audit after credential-entry removal | 0 findings |
| Official settings-schema validation | 0 errors |
| Live/canonical config, instructions, and hook hashes | matched |
| Python compile / JSON parse | passed |
| Git whitespace check | passed; line-ending notices only |
| Claude Code doctor | 2.1.220, no installation issues |

## Change-surface reconciliation

The desktop file counter was not a reliable count of intentional edits. At the
03:33 +03:00 audit snapshot:

- `claude-setup` had 110 dirty Git paths;
- `new-recruit` had 43 dirty Git paths; and
- a separate hiring-engine writer was actively committing and changing the
  latter count during the read-only audit.

There are also two legitimate counting modes. After the judge follow-up,
`claude-setup` showed 86 collapsed status entries but 112 expanded physical
paths (`--untracked-files=all`). `new-recruit` showed 22 collapsed entries and
42 expanded paths after the concurrent writer committed more hiring work.
This makes a UI snapshot of 87 understandable: an untracked directory can be
one displayed entry while containing many files.

The work directly tied to this mastery/corpus pass was classified as follows:

- 36 core `claude-setup` source/config paths: the research prompt and report,
  global contract/settings, 17 rules, three enforcement hooks, two skills, the
  mastery test, and setup auditor;
- 47 `new-recruit` source/config paths: 21 technology-corpus/bridge files, 13
  removed project-local duplicate rules, six resume claim/policy sources, five
  ignored nested Claude settings, and two root configuration paths;
- 33 regenerated current resume artifacts (`11 x HTML/PDF/DOCX`); and
- ten ignored validation artifacts (Python bytecode and the corpus SQLite
  index).

The live `~/.claude` tree is a deployed view, not a second independent edit
set: 27 files matched canonical hashes and the two new skill trees were exposed
through two junction objects.

Twenty staged deletions of older meme/visual tooling also existed in
`claude-setup`, with 13 preservation copies under
`state/retired-2026-07-25`. They were outside the core mastery handoff and are
not being mislabeled as generated noise. No attempt was made here to commit,
push, or silently revert them.

The external-judge follow-up then changed five canonical source/document paths:
the global Claude contract, `prove-implementation`, `codex-call`, the new judge
wrapper, and this report. It also updated three live deployment paths: the
global contract, `codex-call`, and a small launcher for the canonical wrapper.
The npm package trees for Codex/Gemini live under the user npm prefix and are
not repository edits.

Therefore, a historical UI count of 87 may describe one intermediate snapshot
or deduplication rule, but it does not mean 87 intentional hand edits were made
by one operation.

## External review judges added

The current stable CLIs were installed from their official npm packages:

- Codex CLI `0.145.0`;
- Gemini CLI `0.52.0`.

Codex now resolves from the user npm directory before the inaccessible desktop
app binary. `codex login status` reports ChatGPT authentication; no OpenAI API
key is introduced.

The `/codex-call` skill was replaced with a bounded judge workflow. Its wrapper:

- constructs a capped, secret-scanned review bundle;
- runs Codex in a temporary Git repository with read-only sandboxing, no
  approval escalation, no user config, no hooks, no web search, and no
  persistent session;
- requires ChatGPT authentication and strips API-key/provider overrides;
- requires schema-valid findings;
- discards verdicts if the source repository changes during the review; and
- never applies findings automatically.

A forward test seeded `value >= 0` into `count_positive`. The judge returned
`changes_requested`, identified the exact line, explained that zero is not
positive, and proposed the correct boundary tests.

The first self-review of the wrapper produced six findings. Five were accepted
and fixed: unambiguous bundle delivery, Gemini criteria/rename privacy checks,
rejection of contradictory `pass` plus findings, malformed-attestation
handling, and bounded child-process output. One was rejected with current
primary-source evidence: `store` is a documented GenerateContent request field.
Additional local review added exact HEAD/base binding, bounded untracked-file
hashing, review-artifact exclusion, and process-tree timeout cleanup.

A final full-wrapper Codex review hit the explicit 180-second limit and was
recorded as `unavailable`; it was not converted into approval. The smaller
seeded-regression test passed repeatedly after hardening.

Google's May 19 transition notice supersedes the older Gemini CLI free-quota
documentation: free consumer Gemini CLI service stopped on June 18, 2026.
Therefore Gemini CLI is installed but not used automatically under a free-only
promise.

The Gemini judge instead uses one tool-free Developer API request pinned to
`gemini-3.6-flash`, with no paid/model/backend fallback. It remains fail-closed
until:

1. `GEMINI_API_KEY` is securely available to the local Claude process; and
2. the operator verifies in AI Studio that its project shows Billing
   Tier `Free`, with no billing account linked, then records the 30-day
   hash-bound attestation.

The repository's GitHub Actions secret named `GEMINI_API_KEY` exists, but
GitHub secrets cannot be read back into the local process. Free Tier Gemini
content may be used to improve Google products, so the wrapper also refuses
Gemini unless the exact bundle is explicitly marked public and
non-confidential. Resumes, recruiting/work resources, employer/customer code,
credentials, and PII are prohibited.

## Residual risks and next evidence-producing actions

1. Rotate the two credentials formerly embedded in project permission entries.
2. Securely expose the already-created Gemini key to the local Claude process,
   verify its AI Studio project is still unbilled Free Tier, and record the
   wrapper attestation before enabling the public-code Gemini judge.
3. Do not route any legacy numbered resume or historical claim source.
4. Run one Cloudflare Pipelines lab with retained source, tests, failure case,
   cost/limit notes, and a content-addressed attempt record.
5. Add real ESCO/O*NET concept IDs only after a human checks the exact concept;
   dataset-version labels are not skill IDs.
6. Promote the lab to project evidence only after candidate contribution,
   repository commit, artifact hashes, and contradictions are reviewed.
7. Add resume wording only after exact text review; retain the existing
   rendered-PDF hash approval as the final application gate.
8. Refresh Kimi K3 only after the scheduled weights/report are actually
   released and reproducible.
9. Keep full commercial-book text private and on demand; do not preload it into
   global Claude context.
10. Treat loop detection as a heuristic review prompt. AST-/language-specific
   analyzers and representative benchmarks are still required for high-risk
   performance claims.
11. The proof gate can establish comparative evidence under declared
    conditions, never universal “best.”

## Final self-review

The initial instinct—copy a large mastery list and ingest every new book—would
have increased context noise, supply-chain risk, copyright risk, stale advice,
and self-confirming output.

The converged design instead separates:

- discovery from authority;
- reading from competence;
- competence from project evidence;
- project evidence from production state;
- model output from proof;
- source consistency from factual truth; and
- current routed resumes from historical artifacts.

That separation is the main enhancement. The hooks, skills, catalogs, tests, and
sidecar make it executable.
