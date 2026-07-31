# Local dependency audit, 2026-07-29

Hypothesis under test: "im afraid my projects, are very dependant locally, or on the
internal claude session running them."

Terms. DEPLOYED, running for users now without this laptop. RUNNABLE, would run if
someone typed a command. ASPIRATIONAL, a document exists and no code does. Offsite,
a copy on a disk that is not this SSD.

## 1. Is he right?

Partly, and the correct half is worse than he framed it while the wrong half is
wrong in his favour. Worst first: four asset piles have exactly one copy and no
remote. `C:\Users\shova\Downloads\new-recruit` in full (no git remote, 26 commits,
working tree four days ahead of the last commit), which also holds the only known
copy of `work-archive-2026-07-12\social-media-agent.bundle` (25,461,889 bytes,
gitignored at `.gitignore:103`, so it would not travel even if a remote were added).
`C:\Users\shova\claude-setup`, 23 commits unpushed since `origin/main` at `a0eb384`
dated 2026-07-24, where `CLAUDE.md` is untracked and in no commit on any machine.
`daily-deep-learning\docs\`, 71 files and 17 MB, gitignored at `.gitignore:20`,
holding the requirement source of record that `ROUTINE.md:8` orders the cloud
generator to read and that the generator therefore cannot see.
`C:\Users\shova\.claude\skills\voice-metrics\` and `whatsapp-query\`, under no
version control at all. Where he is wrong: the dependency is on the machine being
powered on and logged in, not on a Claude session being open. Five enabled Windows
tasks (`Hiring Engine Daily Sweep`, `SadnaGenFallback`, `SadnaCriticFallback`,
`SadnaDiscover`, `SadnaCouncil`) plus `Startup\sadna-daemon.cmd` fire without him,
and two Anthropic cloud routines (`trig_01HMgWmXQFAyMj8XCf4tq84c`,
`trig_015wiN9mmkQMKUbFkCpYLMdo`) have written and pushed content for six days with
the laptop irrelevant. The pre-audit inventory saying "exactly one scheduled task,
disabled" was false and is void. Two findings outrank the hypothesis: the 48
character `sadna-sync` bearer sits in plaintext in both routine prompts, byte
identical to `daily-deep-learning\daemon\.key`; and `index.html:2166` reads
Cloudflare Pages' 200 SPA fallback as a hit, so 320 of 321 units render the app's
own 135 KB HTML as the lesson body, live now.

## 2. The kill tests

| | new-recruit (resume engine) | daily-deep-learning (learning) | social | claude-setup (substrate) |
|---|---|---|---|---|
| K1 laptop dies | Total loss. No remote, ledger gitignored, 11 offsite backup attempts, 0 successes | Site and code survive on GitHub and Cloudflare. `docs/` 17 MB and `writing/` die | Six design docs survive. The 25 MB bundle and the fitted voice model die | 23 commits, 993 gate verdicts, 287 refutations and `CLAUDE.md` die |
| K2 no session 7 days | Sweep keeps running at 07:00. Zero applications sent, gate closed by operator | Cloud routines keep publishing, against a `ROUTINE.md` they now contradict. Chat dies on reboot | Nothing stops, nothing ever started | Everything stops. Gate, bus, panel are all session hooks |
| K3 subscription lapses | Nothing breaks. Zero Anthropic code in the loop | All four generators, both cloud routines and the chat daemon stop. Site freezes | Nothing breaks. Future approval rail would break hard | Nightly workflow and review fabric stop. `tools/` still runnable |

## 3. What is actually independent of this machine

- `daily-deep-learning.pages.dev`, rebuilt from GitHub by `.github/workflows/deploy.yml`, never uploaded from this disk. Local `main` equals `origin/main`.
- `sadna-sync.shovalb9.workers.dev` and KV `9a4001260c914316a6f63f1494b69d7d`, holding all learner state.
- The two cloud routines, 12 commits by `noreply@anthropic.com` from 2026-07-23 to 2026-07-28.
- `github.com/ShovalBenjer/claude-setup` as of 2026-07-24, carrying the social docs and ADR-0014.

Not empty, which falsifies the blanket form of the hypothesis. It also excludes
every ledger, every doc pile, and every skill.

## 4. The single point of failure

`C:\Users\shova\Downloads\new-recruit`, the whole 2.8 GB directory. No remote at any
commit, its valuable half (`hiring_engine\ledger.sqlite`, 272 jobs, 4 applications,
21 approvals) gitignored by design, its backup module writing only to
`C:\Users\shova\.hiring-engine\backups\` on the same SSD, the only copy of the social
bundle inside it, and `daily-deep-learning\daemon\council.cmd` reading its
`Perplexity research` directory weekly, so a second lane depends on it. Runners up
lose on recoverability: claude-setup's gap closes with one `git push`,
`daily-deep-learning/docs` is gitignored on purpose because that remote is public,
and `.claude/skills` is small. Cost to fix:
set four `HIRING_ENGINE_R2_*` variables against a private bucket, which
`hiring_engine/backup.py` already implements including SigV4 signing and
`tests/test_r2.py`. The blocking work is not code, it is the scrub decision the
`.gitignore` header already demands, because the ledger holds real recruiter names
and contact details.

## 5. Cheapest three fixes

1. `cd C:\Users\shova\claude-setup; git add CLAUDE.md docs state; git commit -m "checkpoint"; git push origin main`. Closes 23 unpushed commits and puts the project contract into version control for the first time.
2. Set the offsite destination the hiring engine has been asking for since 2026-07-25: create a private R2 bucket, then `setx HIRING_ENGINE_R2_ACCOUNT`, `_BUCKET`, `_KEY_ID`, `_SECRET`. This also clears the `LASTRESULT : 1` on `Hiring Engine Daily Sweep`.
3. `Disable-ScheduledTask -TaskName SadnaGenFallback` and `-TaskName SadnaCriticFallback`, plus disable both cloud routines, until `daemon\gen-fallback.cmd`, `daemon\critic-fallback.cmd` and both prompts are rewritten against `ROUTINE.md` sections 0 to 7. They still name sections `1b` and `2b`, which no longer exist, and write to `posts/`, which `ROUTINE.md:159` forbids.

## 6. What I could not verify

Whether `HiveUploadTask` exists at all; two audits disagree. Whether OneDrive here is
signed in and syncing. Whether the `gws` Gmail OAuth grant is still valid. Whether
today's 06:02 and 03:07 runs produced contract violating commits. Cloud routine
prompts beyond what `RemoteTrigger list` returns. The expiry of
`secrets.CLAUDE_CODE_OAUTH_TOKEN`. Whether access to upstream
`ORM-AGENT/social-media-agent` still exists. No test suite was executed, so every
test count here is a file count.
