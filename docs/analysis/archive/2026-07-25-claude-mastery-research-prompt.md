# Claude Code mastery research prompt

Date boundary: 2026-07-25
Primary user environment: native Windows, Claude Code, Claude.ai first-party Max

## Role

Act as a skeptical AI-systems engineer, software-quality lead, security reviewer,
learning architect, and career-evidence auditor. Treat models, prompts, repositories,
books, plugins, and benchmarks as fallible inputs. Prefer observable outcomes and
primary sources.

## Objective

Investigate `claw-army/awesome-claude-code-mastery` completely enough to decide
what is safe and useful for this specific Claude Code installation. Diagnose why
Claude may choose familiar or low-effort implementations, including unexamined
loops, and build controls that make correctness, implementation choice, context
continuity, and completion claims externally checkable.

Design a rights-aware, on-demand knowledge corpus that supports:

1. learning and deliberate practice;
2. implementation and architecture decisions;
3. the learning platform's curriculum vocabulary;
4. the resume engine's skill vocabulary without manufacturing experience claims.

## Evidence hierarchy

1. Live machine state, repository code, executable tests, and measured behavior.
2. Current official documentation, system cards, standards, release notes, and
   vendor technical reports.
3. Primary research papers and open technical references.
4. Publisher metadata for commercial books.
5. Community material only for discovery or experience reports.

Record date, provenance, rights, uncertainty, and what was actually inspected.
Do not equate a visible link, a passing visible test, or a model explanation with
verified final state.

## Epistemic constraints

- Anthropic has not published enough detail to assert Claude's exact architecture,
  decoder, expert routing, training mixture, or inference search. Do not invent it.
- Separate vendor claims about Kimi K3 and DeepSeek V4 from independently
  reproducible evidence. Record release and weights/report availability at cutoff.
- Do not blame beam search, sampling, MoE routing, or a hidden decoder mechanism
  without evidence. Analyze observable failure surfaces: likelihood-favored defaults,
  missing alternatives, weak task contracts, context position and pollution,
  compaction loss, stale session state, tool-state mismatch, reward hacking,
  self-evaluation leniency, and harness/configuration regressions.
- "Best" means best among explicitly compared candidates under stated constraints
  and a representative oracle. A newer technique is not automatically better.

## Repository audit

- Freeze the exact commit and inventory every tracked file.
- Extract every outbound link and action dependency; deduplicate and classify by
  section, host, source type, license, activity, Windows suitability, permissions,
  credential exposure, and installation risk.
- Inspect repository provenance, fork lineage, badges, contribution instructions,
  license claims, update automation, open issues/PRs, redirects, dead links, and
  false-green checks.
- Deep-review all official resources, every dead-link class, the fork's unique
  addition, and the third-party resources most relevant to this user's weak points.
- Clearly distinguish exhaustive URL inventory/availability coverage from selective
  content and security review. Do not claim to have read 791 linked resources when
  only their metadata or availability was checked.

## Local Claude audit

- Verify executable, version, doctor status, authentication provider, model aliases,
  plugins, MCP servers, global/project settings, rules, skills, agents, commands,
  hooks, state/cache growth, context/compaction controls, and stale paths.
- Never print credentials or PII. Report suspicious file paths and key names only.
- Inspect configuration precedence, project overrides, bypass permissions, automatic
  MCP enablement, dangerous startup behavior, and whether hooks referenced by
  settings actually exist and execute.
- Measure duplicated unconditional context and contradictory model instructions.

## Implementation-quality controls

Build a workflow that:

- turns intent into observable acceptance criteria and oracles;
- compares at least two viable implementations, or three for high-risk work;
- explicitly considers a plain loop, batching, pushdown, streaming, indexing,
  caching, vectorization, and bounded concurrency when applicable;
- records constraints, asymptotic and operational costs, failure isolation,
  maintainability, reversibility, and break conditions;
- runs boundary, property, metamorphic, differential, fuzz, mutation, concurrency,
  or benchmark checks when ordinary examples are insufficient;
- binds passing checks to exit codes, timestamps, output hashes, and repository
  commit/diff state;
- requires a fresh reviewer for high-risk decisions;
- blocks destructive commands, unreviewed behavior-affecting pushes, and unsupported
  completion claims without creating infinite hook loops.

Forward-test the controls. Use failed tests as design feedback rather than weakening
the oracle.

## Knowledge corpus and books

Cover the useful domains rather than indiscriminately collecting titles:

- software engineering, domain modeling, architecture, and maintenance;
- testing, property testing, formal methods, concurrency, and distributed systems;
- data systems, data engineering, ML systems, evaluation, reliability, and SRE;
- application security, threat modeling, privacy, and supply-chain safety;
- AI engineering, agents, context engineering, prompt/tool design, and evals;
- UX, product discovery, platform engineering, delivery, and team design;
- career development, technical communication, resume vocabulary, and skills
  taxonomies.

For every source record: title, edition, authors, publisher/owner, publication and
verification dates, canonical URL, official rights/terms URL, availability status,
domains/topics, intended use, weakness addressed, freshness note, and rights mode.
Mark post-cutoff or unfinished books as announced, not current.

Commercial books are metadata-only until the user explicitly attests a lawful
private-use basis for a local copy. "Downloaded," "subscribed," and "free to read"
do not imply corpus reuse rights. Private chunks stay outside repositories, are
treated as untrusted data, and have a revocation/deletion path.

Use ESCO, O*NET, NICE, and DigComp identifiers as the machine-readable learning-to-
resume bridge where their licenses permit. These taxonomies define vocabulary;
they never prove that the user has a skill. Only approved project, assessment, or
production evidence can support a resume claim.

## Required deliverables

1. Frozen repository clone and evidence-backed audit with coverage limits.
2. Current local Claude risk and drift audit.
3. Safe live/canonical settings with least privilege and no permanent bypass mode.
4. Small, tested safety, pre-push, and completion-evidence hooks.
5. A `/prove-implementation` skill with execution-backed evidence tooling and loop
   review.
6. A `/learn-on-demand` skill with a validated metadata catalog, private FTS index,
   explicit attestation, query, and revocation workflow.
7. A concise project-neutral global contract and nonduplicated path-scoped rules.
8. Automated regression tests and a read-only setup validator.
9. A decision report: adopt, consider individually, reference only, avoid, or reject.
10. Explicit residual risks and user actions, especially credentials that require
    rotation and books that require rights attestation.

## Convergence test

Do not stop because files exist. Stop only after:

- configuration and scripts parse;
- referenced hooks exist;
- representative safe and unsafe hook cases behave as intended;
- implementation-proof valid and invalid cases are tested;
- multiline loop cases are tested;
- the knowledge catalog validates and can build/query without copyrighted full text;
- Claude doctor remains healthy;
- live and canonical files match where intended;
- independent review findings have been resolved or recorded as residual risks;
- the final report states exactly what was and was not verified.
