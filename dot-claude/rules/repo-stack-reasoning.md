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
