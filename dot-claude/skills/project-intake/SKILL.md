---
name: project-intake
description: Project intake gate, structure, git hygiene, code quality, testing, deployment checklist. Use when onboarding a new project to ~/workspace/ or a new repository.
---

# /project-intake

Mandatory checklist for any project entering the workspace. The lesson, learned the hard way: a 21K-line monolith with four backend copies and tens of megabytes of images committed. Never again.

## Checklist (all must pass)

- [ ] No file over 500 LOC, no function over 50 LOC
- [ ] `.gitignore` covers: images, `node_modules`, `__pycache__`, `.env`, build artifacts
- [ ] No secrets in the repo (grep for key, token, secret, password patterns)
- [ ] Linter and type checker configured
- [ ] Zero TODOs in production code
- [ ] Tests exist and pass
- [ ] No mocks on business logic (platform stubs only)
- [ ] Single deploy mechanism, documented
- [ ] README with: what it is, how to run, how to test

## How to run the intake

Walk the checklist against the project. For the code-quality and testing rows, use the repo-anatomy standard and the project's own gate where one exists. Record each row as pass or fail with the evidence (command plus output).

## Reflection (mandatory)

The intake is not complete when the checklist is ticked. The final phase drives the project the way a new user would: follow its README to install, run, and test it from a clean state, and record the outputs. If the README path fails, the intake fails, no matter how many boxes are checked. Preserve the run log as evidence.

## Rules

- A project that fails intake does not enter the workspace until the failures are fixed or explicitly waived with a reason
- Waivers are recorded in the intake report, never silent
- Re-run intake after any structural change (new deploy path, new language, monorepo merge)
