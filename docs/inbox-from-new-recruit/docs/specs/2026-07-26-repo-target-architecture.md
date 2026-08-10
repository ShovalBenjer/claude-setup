I verified the codebase directly. Three findings materially change the architecture answer versus the audit packet I was given. Here is the design.

---

# Target Repo Architecture: one system that lives and evolves

## Corrections to the audit packet (verified this session)

Three claims in the input audit are wrong or incomplete. They change the recommendation, so they come first.

**1. claude-setup's real gate exists, and it has never left the machine.** The audit says "Two workflows, neither of which tests anything... 44 test files, 0 CI executions." There is a third workflow, `.github/workflows/ship-gate.yml`, added 2026-07-25, which runs a full multi-domain contract (`gate.py run --project .`), a separate `falsifiability` job that runs mutation testing (`tools/audit/mutate.py --spec all`) to prove the selftests can fail, and a Windows job driving real Chrome. It is genuinely non-vacuous. But: [EVIDENCE] `git log origin/main..HEAD` returns **21 unpushed commits**, and `gh api repos/ShovalBenjer/claude-setup/contents/.github/workflows` returns only `claude-code-review.yml` and `claude-nightly.yml`. The gate is built and unshipped. The audit's conclusion ("0 CI executions") is right by accident; the cause is not "nobody wrote it," it is "nobody pushed it."

**2. new-recruit has no git remote at all.** [EVIDENCE] `git remote -v` is empty. Its own `.gitignore` states: "This repo has NO REMOTE and must not get one without a scrub pass first." It tracks 107 files; `projects/` (employer work), `docs/company_context.txt`, and `docs/Auth_vlad.txt` are **untracked** [EVIDENCE: `git ls-files projects/` returns 0]. So the employer-material problem the audit attributes to claude-setup is, in new-recruit, already solved by a default-deny ignore file. new-recruit cannot be "consolidated into" anything on GitHub until a scrub-and-remote decision is made, because it is not on GitHub.

**3. The harness/product boundary already exists and is load-bearing.** All three live projects carry a `quality-contract.json` with the same schema. [EVIDENCE] new-recruit's contract contains `"cmd": "python C:/Users/shova/claude-setup/tools/review/panel.py run --project ."`, and daily-deep-learning's contains `python C:/Users/shova/claude-setup/tools/e2e/flow.py audit ...`. `gate.py` (1,293 lines) exposes `init/run/status --project <path>` and a `detect_stack()` function. daily-deep-learning's `tools/sync_resume_skills.py:16` hardcodes `C:/Users/shova/Downloads/new-recruit/resumes_2026/gen.py`.

This is decisive. **The question is not "monorepo or polyrepo." A hybrid is already running in production. It is wired with hardcoded absolute Windows paths, which makes it a single-machine architecture.** The work is to formalize the seam, not to merge repos.

---

## Verdict: hybrid, with a versioned harness contract

**Not a monorepo.** Five independent reasons, each sufficient:

1. daily-deep-learning deploys with `wrangler pages deploy . --project-name=daily-deep-learning`, coupled to repo root. Merging breaks the only live deploy in the estate.
2. claude-setup tracks 260 employer files in `work-docs/` [EVIDENCE: `git ls-files work-docs/ | wc -l`]. Anything merged into it inherits "private forever."
3. [EVIDENCE] Branch protection on claude-setup returns HTTP 403: "Upgrade to GitHub Pro or make this repository public." `gh api user` reports `plan: null` (free). A single private monorepo would be one unprotectable trunk holding the entire estate.
4. Toolchains do not compose: Rust (mcp-guard is Python, but protobuf-fuzz-guard and claude-memes-skills are Cargo workspaces with MSRV pins and release matrices), React Native with EAS credentials, Quarto, stdlib Python, a no-build PWA.
5. sqltok and mcp-guard have external audiences. Their value is `pip install` and `git clone`. A folder in a personal monorepo destroys that.

**Not a pure polyrepo either**, because the harness is genuinely shared and duplication is already measurable: 71 skills in `dot-claude`, 61 in `dot-codex`, 70 in `dot-agents`, with 60 names shared between claude and codex and 32 shared across all three [EVIDENCE: `ls | wc -l` and `comm -12`]. Sampled shared skills **differ in content**, so these are drifted forks, not mirrors.

### The tier model

| Tier | Contains | Rule |
|---|---|---|
| **0. Harness** | claude-setup: `gate.py`, `panel.py`, `tools/`, skills tree, ADRs, `intent-control-plane` | Knows *how* to build and judge. Contains zero domain logic. Never imports from a product. |
| **1. Live products** | new-recruit (hiring), daily-deep-learning (learning), social-publish (new) | Each owns a remote, a deploy, and one `quality-contract.json`. Consumes Tier 0; never the reverse. |
| **2. Published artifacts** | sqltok, mcp-guard, protobuf-fuzz-guard, claude-memes-skills, ShovalBenjer (profile) | External audience. Own release path. Gated by Tier 0 but not owned by it. |
| **3. Frozen evidence** | archived coursework and take-homes | Read-only. No CI. No claims. |

### Where the boundary sits

The line is **"does it know what the work is about?"**

- A thing that scores an eval, routes a model, checks a secret, measures skill drift, or decides whether a change may merge is **harness**.
- A thing that knows what a resume claim is, what a Hebrew learning post is, or what an ATS endpoint returns is **product**.

Concretely: `agenteval-bench`'s deterministic matchers and CI threshold are harness. The hiring engine's `fit_score.py` is product. The SM-2 scheduler from `deep_learning_neural_networks/src/quiz` is product (learning platform), not harness, even though it is generic, because the learning platform is the only consumer and premature promotion to Tier 0 is how the triplication started.

**The interface is three things, and nothing else:**
1. `quality-contract.json` at each product root, with a declared schema version.
2. `gate.py run --project <path>` as the only entry point.
3. The deployed skills tree, with `tools/audit/skills_sync.py` as its drift oracle.

**The defect to fix:** the interface is currently transported by absolute paths (`C:/Users/shova/claude-setup/...`). Replace with a resolution order: `$CLAUDE_HARNESS` env var, then a `.harness-ref` file at product root pinning a commit SHA, then a vendored fallback. [INFERENCE] This is my design proposal; no such mechanism exists in the tree today.

Note the contract schema is **already drifting**: claude-setup's contract declares `codemap` and `prior_art` domains that new-recruit's does not [EVIDENCE: diff of the two files]. Version the schema now, before a third consumer.

---

## How a new project gets created

The mechanism already exists and should be made mandatory rather than invented. [EVIDENCE: `gate.py init [--project .]` writes a starter contract; `detect_stack()` probes for `package.json`, `pyproject.toml`, `.github/workflows`.]

1. `python <harness>/tools/gate/gate.py init --project <new>` writes `quality-contract.json` with detected stack.
2. Fill every `na_reason` with a **reason, not a blank**. The existing contracts model this well: claude-setup's e2e says "claude-setup serves no application of its own," not "TODO."
3. Write `.harness-ref` pinning the harness SHA.
4. Declare tier in the README. Tier 1 and 2 get a remote; Tier 3 never does.
5. First commit must pass `gate.py run`. The starter contract deliberately fails a project with no tests [EVIDENCE: gate.py:204, "no test script found; a project with no tests cannot pass this gate"].
6. Register in one `PROJECTS.md` index in the harness. This replaces the current `PROJECTS-MANIFEST.md`, which is prose positioning, not a machine-readable registry.

The planned **social-publish** project is the first customer of this path, and the harness already has its policy: ADR-0014, "social-publish-draft-first-hard-gate."

---

## Disposition of all 32 repos

Eight are already archived [EVIDENCE: `gh repo list --json isArchived`].

| Repo | Tier / action | Note |
|---|---|---|
| claude-setup | **T0 hub** | Push 21 commits. Extract `work-docs/`. Fix triplication. |
| new-recruit | **T1** | No remote. Scrub pass, then private remote. |
| daily-deep-learning | **T1 keep** | Only live deploy. Do not move. |
| *social-publish* | **T1 new** | Create via `gate.py init`. |
| sqltok | **T2 keep** | Cut v0.1.0; zero tags today. |
| mcp-guard | **T2 keep** | Fix "65 findings" calibration in README. |
| protobuf-fuzz-guard | **T2 keep** | Add LICENSE (absent). |
| claude-memes-skills | **T2 keep** | Flip public, tag v1.3.1, or archive. |
| ShovalBenjer | **T2 forced** | Remove retracted 24%→64% metric. Urgent. |
| agenteval-bench | **merge → T0** | Becomes harness eval subsystem. |
| deep_learning_neural_networks | **lift → T1** | `src/quiz` to learning platform, then archive. |
| admaven-python-data-engineering | **lift → T1** | `src/lib` to hiring engine. Make private first. |
| Explorations_With_KAN | **lift → T1** | Only `rmt_activation.py` + its test. Then archive. |
| Machine_Learning_Study_Guidebook | **lift → T1** | README to corpus **after** purging 41 MB of textbook PDFs from history. |
| matchiq | **archive** | Fast-forward main to the work branch **first**. |
| argmax_solution | **archive** | Delete the fake all-green `if: always()` summary step. |
| phantom-reach | **archive** | Open the `.docx`/`.pptx` files first. |
| phone-social-reminder | **archive or ship** | Decide App Store intent. |
| oren-roast-hq | **stay private forever** | Rotate 13 credentials now. |
| Bank-Change-Prediction | **private, then archive** | Republishes Insait's assessment. |
| JSQ-SLQ | **T2 keep, scrub** | Remove false build/license badges. |
| Housing_Price_Prediction | already archived, keep | Best frozen evidence. |
| Catering_Company_Management_System | already archived, keep | Fix false README or private. |
| time-twist-visualizer | **delete** | Fabricated benchmark table over `Math.random()`. |
| altius-financial-analysis | **delete** | Third-party PE fund data. |
| LeetCode_C_Python_SQL | **delete** | Public FizzBuzz under JPMorgan filenames. |
| Resonant-Harmonics-Agents | **delete** | Pull the 3 binaries first; MIT applied over third-party PDFs. |
| CS_188-...-Final_Project | **delete (urgent)** | Israeli-ID-formatted number in a public filename. Archiving does not remove it. |
| Manage-Warehouse-OOP-Python | **delete** | Same ID in commit history. |
| Power_Transform_Box-Cox | delete | Archived, placeholder clone URL. |
| Natural_Language_Proccessing_NLP | delete | Archived, no README, misspelled name. |
| pull-request-podcast | delete | A fork. |
| next.py-solution-campusil | delete | Coursework. |
| crowd-transcribe | delete | Coursework. |

Net: 32 into 4 live (Tier 0 + 1), 5 published (Tier 2), 8 frozen, 12 deleted, 3 lifted-then-archived.

---

## Migration sequence

Ordering rule: **irreversible harm first, then harness integrity, then boundary, then absorption, then cleanup.** Absorption is late on purpose: importing code into a hub that is private-forever and triple-duplicated multiplies both defects.

### Phase 0: bleeding (today, no architecture involved)
1. Rotate all 13 credentials in `oren-roast-hq:.env`, starting with `SUPABASE_SERVICE_ROLE_KEY` (it bypasses every RLS policy, making the `security_lockdown` migrations decorative). They are in git history; removing from HEAD is insufficient.
2. Delete the retracted `24% to 64%` line from the public profile README. The project CLAUDE.md forbids it and it is live right now.
3. Delete `CS_188-...-Final_Project` and `Manage-Warehouse-OOP-Python`. Both are already archived, which does **not** hide the ID-bearing filenames.
4. Make private: `time-twist-visualizer`, `admaven-python-data-engineering`, `altius-financial-analysis`, `Bank-Change-Prediction`.

Nothing below depends on Phase 0, and Phase 0 depends on nothing. Do it independently.

### Phase 1: get the harness's own gate onto the remote
5. Review the 21 unpushed commits, then push. **This is the highest-leverage single action in the plan.** Until `ship-gate.yml` is on `origin/main`, every "the harness enforces X" claim is local-only.
6. Treat the first run as the confirmation, not the proof. The workflow's own comments flag two untested assumptions: that the Windows runner has Chrome at `cdp.py`'s hardcoded path, and that the falsifiability steps (measured exit 0 on Windows) hold on ubuntu. [EVIDENCE: both are stated verbatim in the workflow header.]
7. Close the stale seeded-defect PR #2 and fix or delete the two failing `Claude Code Review` runs.

### Phase 2: make the hub fit to absorb anything
8. Resolve the skills triplication using the oracle that already exists: `tools/audit/skills_sync.py`, already wired into the falsifiability job. Pick one canonical tree, generate the others, and let the selftest fail on drift. Do not hand-merge 60 drifted pairs.
9. Version the `quality-contract.json` schema (`"schema": 1`) and reconcile the `codemap`/`prior_art` gap between the two live contracts.
10. Clear or re-date the three `until: 2026-08-01` waivers in new-recruit's contract (unit, types, pipeline). They expire in six days and will turn the gate red on a date, not on a defect.

### Phase 3: the privacy decision (this unblocks everything downstream)
11. Extract `work-docs/` (260 tracked files), plus employer references in `research-papers/` and `dot-codex/`, into a separate **private** archive repo. This requires history rewrite, not a `git rm`.
12. Then choose:
    - **(a) Pay GitHub Pro.** Restores branch protection on the private repo. Smallest change, costs money, leaves the harness unpublishable.
    - **(b) Flip claude-setup public after the extraction.** Free branch protection and rulesets, makes the gate itself the strongest portfolio artifact in the estate, and unblocks external contribution.
    - **(c) Status quo.** The nightly workflow's own comment concedes "the structure IS the guard." That guard just allowed 21 commits, including the entire gate, to sit unpushed for two days.

    **Recommend (b), with (a) as interim cover during the rewrite.** Caveat the operator owns: publishing the harness publishes a dated record of their own workflow, rules, and skill gaps. That is the same self-disclosure choice already made in daily-deep-learning's `skills.json`, so it should be made deliberately, not inherited.

### Phase 4: replace absolute paths with a real interface
13. Implement harness resolution (`$CLAUDE_HARNESS` → `.harness-ref` → vendored). Migrate the two contract `cmd` strings and `sync_resume_skills.py:16`.
14. Move the skills/talents ledger tooling from daily-deep-learning into the harness and have the PWA consume it. This is the correct direction: the audit's instinct to move the *ledger* rather than the *site* is right, because the site's deploy is root-coupled.

### Phase 5: new-recruit's remote
15. Run the scrub pass its own `.gitignore` demands, verify with `gate.py`'s `secret_scan`, then create a **private** remote and wire `ship-gate.yml`. This flips its waived `pipeline` domain from "no forge exists" to genuinely green.
16. Note the repo-in-repo topology: `C:/Users/shova` is itself a git repo whose `.git/info/exclude` explicitly excludes `Downloads/new-recruit/` [EVIDENCE]. Do not let a remote reintroduce the divergent-copy problem that exclusion was added to stop.

### Phase 6: absorption (only now)
17. `agenteval-bench` → harness eval subsystem. Land its open bot PR fixing the ruff I001 that currently makes every CI run fail at Lint (so pytest and the eval gate never execute) **before** merging, otherwise you import a dead gate.
18. `deep_learning_neural_networks/src/quiz` + its 4 test files → learning platform. Carry the caveat: AI-authored code with AI-authored tests, not resume evidence on its own.
19. `admaven` `src/lib` (fraud detection, ad detection, scraper) + 6 tests → hiring engine collection layer. Discard the PDF, PNGs, MCP wrapper, Streamlit, fly.toml.
20. `Explorations_With_KAN`: only `rmt_activation.py` + its test. Leave the 10 MB PDF of unestablished provenance behind.

### Phase 7: publish Tier 2
21. Tag `sqltok` v0.1.0. Its trusted-publishing workflow has never fired; until a release exists, "Publish to PyPI" is staged, not shipped.
22. Flip `claude-memes-skills` public and tag v1.3.1, or archive it. Its README currently tells readers to install from Releases that do not exist.
23. Fix `mcp-guard`'s README calibration (FINDING means "payload accepted without error"; LEADERBOARD.md is honest, README is not) and land its two open PRs.
24. Add a LICENSE to `protobuf-fuzz-guard`. It asks people to run it in their pipelines.

### Phase 8: archive and delete sweep
25. **Before archiving anything**: fast-forward `matchiq` main to `claude/implement-in-full-6vkgx7` (otherwise you freeze a 9-byte README and destroy the only asset), and purge the two textbook PDFs from `Machine_Learning_Study_Guidebook`'s history (archived repos stay readable).
26. Pull binaries off `Resonant-Harmonics-Agents` to local storage, then delete.
27. Execute the delete list. Archive the rest.
28. Delete the `if: always()` hardcoded all-green summary step in `argmax_solution` wherever else it was copied. It renders seven passing rows on a fully red run.

---

## What breaks if the order changes

- Absorb before Phase 3 → imported code becomes private-forever and inherits the triplication.
- Archive matchiq or the study guidebook before Phase 8 step 25 → irreversible.
- Push new-recruit before Phase 5's scrub → the exact failure its `.gitignore` was written to prevent.
- Skip Phase 1 → every later phase claims enforcement from a gate that is not on the remote.

## Residual risk and unknowns

- [INFERENCE] The harness-resolution mechanism is my proposal; nothing like it exists in the tree. It is unbuilt and unmeasured.
- [UNKNOWN] I did not run `gate.py run` on any project. Every green/red statement about the contracts is read from the contract files' own recorded notes, not re-measured this session.
- [UNKNOWN] I did not read the 21 unpushed commits' diffs, only their subject lines.
- [UNKNOWN] `ship-gate.yml` has never executed anywhere. Its ubuntu portability and the Windows Chrome path are both self-flagged as unconfirmed in the file.
- [UNKNOWN] I did not open `work-docs/Auth_vlad.txt` or the two flagged `.appsettings.json` values. The audit's "secret found at" locations stand unverified by me.
- [EVIDENCE, unresolved] `docs/Auth_vlad.txt` and `docs/company_context.txt` exist untracked in new-recruit's working tree while tracked copies live in claude-setup's `work-docs/`. The Phase 3 extraction must cover both locations, or the material survives the rewrite on disk.

**Relevant paths:** `C:\Users\shova\claude-setup\.github\workflows\ship-gate.yml`, `C:\Users\shova\claude-setup\tools\gate\gate.py`, `C:\Users\shova\claude-setup\tools\audit\skills_sync.py`, `C:\Users\shova\claude-setup\quality-contract.json`, `C:\Users\shova\Downloads\new-recruit\quality-contract.json`, `C:\Users\shova\Downloads\new-recruit\.gitignore`, `C:\Users\shova\Downloads\daily-deep-learning\quality-contract.json`, `C:\Users\shova\Downloads\daily-deep-learning\tools\sync_resume_skills.py`