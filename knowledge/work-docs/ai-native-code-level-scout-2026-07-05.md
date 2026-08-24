# AI-native code-level scout, 2026-07-05

## Bottom line

You are already strongest where the work needs AI-native systems: contracts, evals, cloud runtime, live probes, data/product reasoning, and agent workflows. The other engineers' visible strength is not "more advanced AI"; it is steadier conventional product engineering: small PRs, UI shells, enterprise app plumbing, Rails/WordPress maintenance, SAML/RBAC, and deploy hardening.

The code-level upgrade is not to become less AI-native. It is to wrap the AI-native speed in the same boring product-engineering discipline they show: smaller slices, cleaner ownership boundaries, less artifact sprawl, and more durable UI/product polish.

## What you can do that they do

- Build Vlad-style frontend shells: Next/React, typed UI models, TanStack Query/Table, Radix/shadcn-style components, role screens, audit screens, archive browsers, and docs pages.
- Build Nikolay-style production hardening: App Service startup scripts, web/worker split, health probes, rollback stages, migration guards, Redis/DB compatibility checks, ACR cleanup, and Azure deployment runbooks.
- Build RBAC/SAML/admin surfaces: role matrices, scoped permissions, user-management screens, and policy tests.
- Maintain CMS/business sites when needed: WordPress child-theme fixes, form flows, tracking snippets, language switchers, and lead-capture plumbing.
- Do Yasha-style acceptance work when you slow down enough: verify that the API or feature matches the actual business workflow, not just the code contract.

## What you do better

- AI contract design: you think in request/response schemas, eval fixtures, evidence objects, citation fields, confidence fields, and failure modes.
- Runtime verification: you are more likely to hit live endpoints, inspect Azure state, check logs, and prove what actually deployed.
- Agent/eval thinking: you design judge loops, scorecards, mutation/property tests, HITL samples, and regression gates.
- Data-to-decision work: you connect code to Liron/Amit/Yasha business outcomes instead of stopping at implementation detail.
- Cross-system integration: you are stronger across Azure Functions, Foundry, MCP, OpenAI/Azure OpenAI, Key Vault, CI, and custom APIs.
- Ambiguous problem solving: you can turn messy stakeholder asks into a working system path faster than a narrow feature implementer.

## What you do worse

- Product-code calmness: your repos can accumulate many artifacts, docs, outputs, generated plans, stale TODOs, and one-off scripts.
- Small PR discipline: you tend to solve across the whole system, while Nikolay often lands tight production increments.
- Frontend finish: Vlad's visible style is cleaner for reusable UI shell structure, component inventory, and product-facing navigation.
- Long-lived monolith stewardship: Nikolay is stronger at patching a large existing product without trying to reinvent it.
- Conventional admin plumbing: SAML/RBAC/WordPress/enterprise settings are less exciting, but they are real production work.
- Repo boundary hygiene: several of your projects mix source, reports, artifacts, screenshots, notebooks, env examples, and generated outputs in the root.
- "Done" definition drift: you often prove one deep path very well, but the surrounding boring paths can remain stale: README, TODO, deploy notes, CI matrix, UI a11y, rollback docs.

## AI-native advantage, used correctly

AI-native should mean:

1. Every external boundary has a named contract.
2. Every AI output has an eval, fixture, or acceptance sample.
3. Every generated artifact has a lifecycle: source, output, archive, or delete.
4. Every live deployment has health, logs, rollback, and owner-facing proof.
5. Every product surface has a small UI and contract test, not only a notebook or script.

AI-native should not mean:

- More agents than ownership.
- More docs than decisions.
- More generated files than maintained source.
- More clever pipelines than simple product behavior.
- More "SOTA" labels than executable acceptance criteria.

## Global code-level suggestions

- Adopt Nikolay's small-PR rhythm: one production behavior per PR, with the deploy/rollback implication explicit.
- Adopt Vlad's UI shell discipline: one stable app shell, typed client layer, component inventory, and route map per frontend.
- Keep your AI-native edge: every scoring, transcription, moderation, or analysis feature gets fixtures, eval rows, malformed-response tests, and live smoke notes.
- Add a project-root artifact policy: source stays near source, generated reports go under dated outputs, and vendor/cache/media artifacts stay out of root.
- Prefer thin handlers plus service/client modules: handlers parse/auth/dispatch, services own business behavior, clients own external calls, DTOs own contracts.
- Treat READMEs and TODOs as runtime surfaces: stale docs are bugs because agents and humans will follow them.

## Where to focus next

The highest leverage is not learning another stack. It is making every active project look like it has one adult owner: clean root, current README, current TODO, typed contracts, tests that prove the top workflows, and a deployment proof path.
