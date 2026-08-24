# Whole-repository stack reasoning

Operator directive 2026-07-29: every stack or technology choice the setup makes
runs through whole-repo reasoning first. A change fits the repository as a
connected system; satisfying the immediate request is not enough.

Before choosing a stack, framework, or dependency:

1. **Discover** what the repository already is: languages, runtimes, package
   managers, build/test/lint tooling, infrastructure, CI/CD, deployment
   platform, storage and messaging.
2. **Understand** how it is arranged: architecture style, module boundaries,
   data flow, design patterns, the repo's own conventions and rules.
3. **Hold the model**: technology inventory, dependency graph, module
   relationships, shared utilities, cross-project conventions. In this
   ecosystem the inventory lives in docs/CODEBASE-MAP.md, dir-purpose.txt,
   and the prior-art records; read them before proposing.
4. **Plan in the model**: which layer owns the change, which existing
   abstraction is reused, what downstream modules, tests, docs, configs, and
   deployments must move with it.
5. **Feed back** what the change taught: new conventions, debt, migration
   plans, and decisions land in the repo's records, not in memory.

Always weigh: architecture consistency, existing patterns, performance,
security, scalability, backward compatibility, developer experience,
maintainability.

Interaction with existing discipline: this rule does not replace /diverge
(candidate generation) or /prove-implementation (evidence); it is the step
BEFORE them that fixes the constraint set they run under. A stack chosen for a
new component (e.g. the operator's own session UI replacing Claude's
statusline) must name the repo facts it grounds on: stdlib-only tools, JSONL
ledgers under state/, Windows-native constraints, no server processes without
an owner.

## Correction 2026-08-13: stdlib-only was never a rule

Operator, verbatim intent: sessions hardened "stdlib-only tools" (a DESCRIPTION of
this repo's existing habit, cited above as a grounding example) into an enforced
default, and it "very much annoyed me across multiple requests". It is hereby
demoted: stdlib is ONE candidate, never the default. For any new tool with a UI,
performance, or product surface, /diverge MUST include at least two modern
candidates from the current landscape (checked fresh, not from memory; as of
2026-08-13: Leptos or Dioxus for Rust UI, Tauri for desktop shells, Next.js/React
Server Components for web product surfaces). Choosing stdlib is allowed only when
it WINS the comparison on stated constraints, and the comparison is shown. A
session that silently defaults to stdlib repeats the exact drift this correction
exists to end.
