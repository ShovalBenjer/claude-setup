# Saved GitHub repositories: first triage, and what it blocks

Date: 2026-07-30. Lane B. Data: `state/saved-repos-2026-07-30.json`.

The operator's observation on 2026-07-30 was that the saved repositories had never been
iterated over and no adopt / install-as-is / leave / concepts-only decision had been
recorded for any of them. That is correct. `TODO.md` ABSORB-06 already stated the
coverage boundary in the abstract ("the true absorption rate across all external
evaluation is unknown, not zero"); this document replaces the abstraction with a list.

## What was done, and what was not

Done: every GitHub URL in `~/wa-export-archive/self-chat-links-2026-07-29.csv` was
extracted, deduplicated to owner/repo, the four repositories saved on 2026-07-30 were
added by hand because the CSV predates them, and each name was resolved against the
GitHub API for stars, last push, license, archived and fork status. 56 of 57 resolved.

**Not done: nobody has visited these repositories file by file.** The operator asked for
a decision made after reading each one. What follows is metadata triage, which can
defensibly answer "leave this" and cannot answer "adopt this". Those two questions are
separated below on purpose, because presenting a metadata sort as a reading pass is the
completeness-without-coverage failure recorded as L-2026-07-29-h.

## Two extraction defects found and fixed

**Truncation.** The CSV's URLs were cut mid-path, so a naive extract produced names that
are not repositories. Five were re-resolved through repository search rather than
dropped, since a dropped saved link becomes an unknown unknown:

| Saved as | Actually |
| --- | --- |
| `affaan-m/everything-claude-code` | `affaan-m/ECC`, 235,979 stars |
| `github/spec-k` | `github/spec-kit`, 124,583 stars |
| `dolthub/dol` | `dolthub/dolt` |
| `ofekron/better-agen` | `ofekron/better-agent` |
| `glittercowboy/get-shit-done` | `gsd-build/get-shit-done`, and it is ARCHIVED |

One name did not resolve at all: `covibes/zerosho`, saved 2026-01-10.

**Staleness.** The CSV stops at 2026-07-29, so it is missing the ACP specification,
goose, and no-ai-slop. Any pipeline built on this CSV inherits a one-day blind spot,
and the extract should be regenerated from the message store rather than from the
frozen file.

## The licensing gate, which is where this stops being bookkeeping

**17 of 56 repositories carry no license or NOASSERTION.** No license means all rights
reserved, so those are concepts-only regardless of how good the code is. Two of them
have already been planned into work:

- `amirfish1/claude-command-center`, 110 stars, no license. AUTO-19 and ABSORB-05 both
  intend to take from it. Nothing in it may be copied. The 12-row feature table in
  `docs/specs/2026-07-24-command-center-superior.md` is a description of behaviour and
  is fine; lifting implementation is not.
- `Master0fFate/just-my-skills`, 7 stars, no license. **ABSORB-04 already saved 419
  lines of its `AGENTS.md` to `docs/analysis/reference/coherence-governor-AGENTS.md`,
  17,923 bytes, and that file is tracked in git.** A verbatim copy of an
  all-rights-reserved document sits in this repository now. This is a second blocker on
  making `claude-setup` public, alongside the third-party PII in
  `research-papers/el-vadt` already recorded. Options: replace the copy with a summary
  plus a link, ask the author for a license, or keep it and accept that the repository
  cannot go public. That is an operator decision, not a lane decision.

## Decisions defensible from metadata alone

**LEAVE, 14 repositories.** One archived (`gsd-build/get-shit-done`), two forks whose
upstream should be used instead (`merlihson/scientific-resources`,
`omkarpawar2001/azure-docs`), and eleven not pushed since May 2026, several by years:
`molson194/AI-CS188` last touched 2016, `biopatrec/biopatrec` 2023,
`cerlymarco/shap-hypetune` 2024, `omkarpawar2001/azure-docs` 2022,
`majkonautic/NOVA_claude-code-mcp-guide` and `princeton-nlp/tree-of-thought-llm` 2025.
Course material and one-off references, not live tooling.

**CONCEPTS ONLY, 17 repositories.** The unlicensed set above. Read, describe, rebuild;
do not copy. This is the same treatment ABSORB-03 already applies to `Sdraugel/albert`
under PolyForm Noncommercial, so the pattern exists.

**INSTALL AS IS, 1 repository so far.** `rtk-ai/rtk`, done 2026-07-30: v0.44.1,
Apache-2.0, 73,967 stars, SHA256 verified against the published checksums, `rtk.exe`
placed in `~/.local/bin`. Measured saving on this tree is **20 percent** across four
commands (`git status` 25, `git diff --stat` 11, `git log --oneline` 0, `ls -la` 68),
against the project's advertised 60 to 90. The advertised range does not reproduce on
git plumbing here, and the wins concentrate in directory listings. `astral-sh/uv` is
already installed and in daily use, which makes it the second member of this class
retroactively.

## The set that needs an actual reading pass, ranked

Ranked by bearing on work already ticketed, not by stars. Each row names what it would
change here, so the reading has a question to answer.

1. `agentclientprotocol/agent-client-protocol`, Apache-2.0. Would replace
   `a2a-codex-call.sh` and `a2a-foundry-call.py`, a bespoke bridge with zero recorded
   calls. `kilo acp` already exists in the installed Kilo CLI.
2. `aaif-goose/goose`, Apache-2.0. Candidate actor for the persona spec, and a native
   ACP server, so it tests 1 without writing an adapter.
3. `petergyang/no-ai-slop`, MIT. Direct comparison against `tools/slop_lint.py`. MIT
   means patterns can be taken, not only read.
4. `alibaba/open-code-review`, Apache-2.0, and `The-PR-Agent/pr-agent`, MIT. Both bear
   on the `review` domain, which is on its third waiver for the same `panel.py`
   false-positive class.
5. `reviewdog/reviewdog`, MIT, 9,488 stars. Not saved by the operator, found by topic
   search. It is the established path for turning a review artifact into PR comments,
   which is exactly what `state/reviews/<sha>.json` currently does not do.
6. `github/spec-kit`, MIT, 124,583 stars. Bears on the PRD and spec lifecycle that
   `docs/specs/` and `docmap` already model.
7. `thedotmack/claude-mem`, Apache-2.0, 89,025 stars, and `letta-ai/letta`,
   Apache-2.0. Both bear on the memory directory and on the OKF question.
8. `affaan-m/ECC`, MIT, 235,979 stars. The operator saved both the repository and
   `ecc.tools/skills`, the selective install builder, so the interesting artefact is
   the install model rather than the skills.

## New candidates found by topic search

Keyword search returned almost nothing usable; topic search did. Recorded so the search
method is reusable: `gh search repos --topic <t> --sort stars --json ...` across
`claude-code`, `ai-agents`, `agent-framework`, `code-review`, `llm-agent`.

Worth a look and not previously saved: `reviewdog/reviewdog` (review plumbing),
`The-PR-Agent/pr-agent` (PR review), `pydantic/pydantic-ai` (typed agent boundaries,
which is what `dot-claude/rules/boundary-contracts.md` asks for),
`microsoft/agent-framework`, `thedotmack/claude-mem`, `farion1231/cc-switch` (model and
config switching, bears on `model-selection.md`), and `JuliusBrussee/caveman`, which
claims 65 percent token reduction and is therefore a direct alternative to the RTK
install above and belongs in its prior-art record.

Stars are a measure of attention, not of trustworthiness or fitness. Several counts in
this ecosystem are large enough to be surprising for the apparent age of the project,
and the number was used here only to order a reading list.

## Next actions this creates

- Operator decision on `coherence-governor-AGENTS.md`, since it blocks going public.
- Regenerate the link extract from the message store, not the frozen CSV.
- Record a decision row per repository in a durable ledger. 56 rows of judgement do not
  belong in a dated analysis document, which is a snapshot by definition.
- Resolve or retire `covibes/zerosho`.
