# GOAL: consolidate 32 repos into one system that lives and evolves

Status: PHASE 1 COMPLETE (recon). Opened 2026-07-26. Scope: full refactor.
This file is the standing goal. Re-read it after every compaction. It is the
"remind yourself" artifact the operator asked for.

## The enhanced prompt (what was actually asked, sharpened)

The literal ask was five things braided together. Separated, they are:

1. **Triage the WhatsApp dump** now sitting in this repo root: say what to delete.
2. **Surface the personal thinking** in the self-chat worth keeping.
3. **Mine `_chat.txt` exhaustively** for every GitHub repo referenced, then
   deep-reverse-investigate each one: what it does, why it was saved, what idea
   in it is worth absorbing.
4. **Audit the operator's own 32 GitHub repos**: how commit / PR / code review
   actually works today, and what the full upgrade path is.
5. **Converge on one mature system** that "lives and evolves" rather than 32
   dormant repos plus a scattering of saved links.

Sharpened into an acceptance checklist:

- [x] Inventory the dump: file count, size, duplicates, tracked-vs-untracked
- [x] Identify which transcript is the self-chat (תזכורת לעצמי)
- [x] Extract every GitHub reference from the self-chat (77 found)
- [x] Secret-scan the dump before anything else touches it
- [x] Inventory the 32 GitHub repos and their CI/PR/protection posture
- [x] Scrape every past Claude session for operator inputs only (691 prompts)
- [x] Classify the referenced repos: absorb / watch / discard (47 triaged)
- [x] Deep-read the remaining long-form messages (pre-2026 era, 34 messages)
- [x] Map the 32 repos onto a target architecture (keep / merge / archive)
- [x] Write the commit/PR/review upgrade spec with concrete config
- [ ] Land the refactor in reviewable increments  <- ONLY REMAINING ITEM

## CORRECTION 2: I gave the wrong retrieval prescription

Earlier in this session I told the operator, on the strength of the paper's
abstract: "build vector retrieval, not keyword. BM25 degrades badly on distilled
text while vector holds." The first half is right. **The prescription was wrong**,
and it would have sent the build in the wrong direction.

What the paper actually supports (abstract re-fetched and confirmed: best pure
distilled 0.717 vs best verbatim 0.745, best cross-layer 0.759, "all 20 vector
configurations remain non-significant after Bonferroni correction, while all 20
BM25 configurations degrade significantly"):

BM25 degrades when run over **distilled** text. It does not follow that BM25 is
the wrong mechanism. Per the full-paper read, BM25-FTS over **verbatim** text is
the single best pure configuration at 0.745, ahead of vector-over-verbatim at
0.645 — mechanism choice matters more than distillation mode. Since the two-tier
design mandates keeping verbatim text anyway (the distilled text is *never shown*
to the operator; it only decides rank order), verbatim BM25 is available for free.

The local environment settles it. Verified on this machine: `sentence_transformers`,
`faiss`, `sqlite_vec`, `tiktoken`, `rank_bm25` are **all absent**; `numpy` and
`duckdb` are present; SQLite 3.45.1 ships with **FTS5 compiled in**. So the
vector path needs an install approval and the FTS5 path needs nothing.

Correct ordering, inverted from what I originally said:

1. **Day 1** — FTS5/BM25 over verbatim. Zero new dependencies. Lands 0.745.
2. **Later, once an embedding install is approved** — add HNSW over distilled
   text as a second signal and fuse. Lands 0.759.

Step 1 is not thrown away by step 2: the paper's best configuration needs both
layers and keeps them as separate indices regardless (density mismatch, ~1,500
chars verbatim vs ~200 distilled).

Two smaller corrections worth carrying: the 11x compression figure is
**corpus-total**; per-item it is **9.9x**. And "two-tier" is stronger than a
storage split: distilled text is never displayed, only ranked on.

## CORRECTION 3: 97% of the corpus was not operator input

The scraper counted **compaction summaries** as operator prompts. Those are
written by the assistant and re-injected into the user turn when a session runs
out of context. They are not input. Each runs 20-60 KB, and there are 136 of
them, so they came to **97.0% of the corpus by character count**.

Every length statistic previously reported in this file was an artifact of them.

| claim made earlier | actual, after the fix |
| --- | --- |
| 5,350,807 chars of prompts | **160,007** |
| p50 165, p90 37,960, max 70,073 | **p50 112, p75 253, p90 503** |
| claude-setup 3,546,437 chars (66%) | **58,920 chars (37%)** |
| "bimodal: one-liner or a 70 KB document" | **withdrawn entirely** |

**The bimodal claim is dead.** The operator does not write 70 KB pastes as a
second mode. Those were compaction summaries the harness inserted. The real
distribution is unimodal and short: three quarters of all prompts are under 253
characters.

The claude-setup-is-the-god-project finding **survives but shrinks**: 58,920 of
160,007 chars is 37% of content from 97 of 587 prompts (16.5%). Still the largest
single topic by volume, no longer two thirds of everything.

The steering finding **strengthens**: 383 of 587 prompts (65%, up from 52%) are
short continuations. With the assistant's own text removed, the operator's real
signature is even more clearly supervision rather than instruction.

Corrected corpus:

| topic | prompts | chars |
| --- | ---: | ---: |
| unclassified | 383 | 52,154 |
| claude-setup | 97 | 58,920 |
| resume-engine | 81 | 30,854 |
| learning-platform | 20 | 17,000 |
| social-posting | 6 | 1,079 |

### How this was caught, and the control that closed it

The defect surfaced as a retrieval symptom: `search` returned compaction
summaries for nearly every query. Diagnosing the symptom found the cause.

After the fix, `search "branch protection"` returned **zero** hits. Per the
operator's own standing rule ("a zero-hit grep requires a positive control before
it can close an item"), that was not accepted on its own:

- positive control: `search "ultracode"` returns 4, `search "resume"` returns 8
- negative control: `search "zzqqxwv"` returns 0
- ground truth: the literal string "branch protection" appears in **0 of 587**
  real prompts; "branch" appears in 3

So the zero-hit is correct. The operator never typed that phrase; the two earlier
"hits" were the assistant's own summaries quoting itself. **The index was
previously retrieving my writing and presenting it as his.**

Index size fell from 7.6 MB to 0.6 MB once `VACUUM` was added, since `DROP` plus
recreate leaves the old pages allocated and the reported size was stale.

## Verdicts (workflow wwenzymta, 43/43 agents, 0 errors)

**Own 32 repos** — delete 11, archive 4, merge-into-monorepo 4, keep-standalone 8,
needs-scrub-before-public 5.

- merge: agenteval-bench, admaven-python-data-engineering, Explorations_With_KAN,
  deep_learning_neural_networks
- keep: sqltok, daily-deep-learning, mcp-guard, claude-memes-skills, ShovalBenjer,
  phone-social-reminder, protobuf-fuzz-guard, JSQ-SLQ
- scrub first: claude-setup, oren-roast-hq, Bank-Change-Prediction,
  Machine_Learning_Study_Guidebook, phantom-reach
- archive: matchiq, argmax_solution, Housing_Price_Prediction..., Catering_Company...
- delete: Resonant-Harmonics-Agents, altius-financial-analysis, time-twist-visualizer,
  LeetCode_C_Python_SQL, Power_Transform_Box-Cox_Supervised_ML,
  Natural_Language_Proccessing_NLP_Projects, CS_188-..., Manage-Warehouse-OOP-Python,
  pull-request-podcast, next.py-solution-campusil, crowd-transcribe

**47 referenced repos triaged** — adopt-dependency 9, absorb-idea 18, watch 7,
discard 13. Coverage note: 47 of 77, because the 15 org-only handles (NVIDIA,
google, microsoft, huggingface, stanford...) came from a single pasted list
repeated six times and are one decision, not fifteen.

Headline: **adopt `bd` (beads), do not rebuild it** — but not on day 1, because
`bd` is not installed, and `bd dolt push` is unusable for this corpus since
DoltHub free accounts host public databases only (a constraint the operator's own
`tools/dolt/client.py` header already documents). Also: only one bus cursor
exists, so the multi-writer problem cell-level merge solves does not exist yet.

## The 732 standing rules, and what they say about this session

Strength split: 106 emphatic-correction, 492 repeated, 134 stated-once.

The most-repeated emphatic corrections are, uncomfortably, about exactly the
failure mode this session has been exhibiting:

- "i dont want only reports i want code implementations"
- "you dont match my intent in implementing and do small patches and report done
  fast instead of looping"
- "You failed me that you didnt do it on your own"
- "i dont want any stop guards, i want redirects to keep it flowing and running"

This session has produced roughly 90 KB of markdown specifications and almost no
running code. By the operator's own most-repeated rule, that is the wrong
deliverable. The remaining checklist item is therefore not optional bookkeeping:
it is the whole point.

## BLOCKING — do this before any other work

`_chat.txt` contains **three live Telegram bot tokens** in plaintext, at lines
7194, 7693, and 7740. Fingerprints (never the full value):

| line | fingerprint |
| --- | --- |
| 7194 | `859534...27gU` sha256:a153dc85 |
| 7693 | `843793..._pYU` sha256:af067e72 |
| 7740 | `871667...ms94` sha256:b291cbbd |

One of them is the `t.me/Gazuzu_bot` token, pasted straight from BotFather.

They are **untracked**, so git history is clean and no rewrite is needed. But
they travelled through WhatsApp and now sit in a repo working directory. Revoke
all three via BotFather (`/revoke`), then re-run the scanner at
`scratchpad/secret_scan.py`. Revocation is the fix; deleting the line is not,
because the token is already out.

The ship gate's `security` domain reported PASS on this same tree. That is not a
contradiction and not a gate failure: it scans **tracked files only** (90 of
them). An untracked 951 MB dump is outside its coverage boundary. That gap is
itself a finding: the gate should scan the working tree, not just the index.

## What landed in the repo

344 numbered artifacts, **951 MB**, flat in the repo root. Nothing is tracked in
HEAD (`git ls-files` → 0 matches), so no history was polluted. `.gitignore`
already swallows `*.jpg/*.png/*.jpeg`, which covers 205 of the files; git still
sees 91 untracked artifacts.

Breakdown: 205 jpg, 39 pdf, 21 mp4, 20 zip, 17 webp, 8 txt, 8 opus, 4 pptx,
4 mp3, 4 md, 3 mov, 3 m4a, 3 docx, 1 xlsx, 1 html, 1 gif.

### Executable triage (pass 3)

`scripts/wa_dump_triage.py` turns the recommendation below into something
reviewable. **Dry run by default**; `--apply` moves files to `_wa_quarantine/`
rather than deleting, so it stays reversible until `--purge-quarantine`.
Measured output over all 345 files:

| category | files | size |
| --- | ---: | ---: |
| MEDIA | 260 | 299.6 MB |
| DUPLICATE | 5 | 16.8 MB |
| THIRD_PARTY | 7 | 12.7 MB |
| SENSITIVE | 1 | 543.1 KB |
| REVIEW | 72 | **621.0 MB** |
| TOTAL | 345 | 950.7 MB |

329.1 MB is safely reclaimable (MEDIA + DUPLICATE + THIRD_PARTY). SENSITIVE and
REVIEW are never auto-moved.

Six exact-duplicate groups confirmed by md5, including `00001174-_chat 15.txt`
== `00001175-_chat 14.txt` byte-for-byte.

### The 621 MB REVIEW bucket is one file

`00001159-claude-setup-FULL-20260508.zip` is **495 MB — 52% of the entire dump**
and 80% of the REVIEW bucket. Opened, it holds only 390 entries, and it is not
really a claude-setup backup at all:

- **358.8 MB**: a single nested `research-papers/el-vadt/docs/sales-agents.zip`
- **127.8 MB**: two near-identical copies of `AI_Status_Meeting_May_2026.pptx`
  (`- Copy` and `- Copy - Copy` of the same deck)
- **~8 MB**: commercial books (Seven and a Half Lessons About the Brain, The
  Psychology of Persuasion, The Challenger Sale)
- the actual harness configuration is a rounding error inside it

So it is an employer deck plus a third-party sales bundle plus commercial books,
wearing a claude-setup filename. Two rules already forbid keeping it here: the
global contract's commercial-books-are-metadata-only rule, and this repo's own
"not this project" policy on i-sdd work material. **Delete candidate, high
confidence** — and it alone accounts for more than half the 951 MB.

### The god project's git history is healthy; its working directory is not

Measured directly, and this inverts the obvious assumption:

- `~/claude-setup` is **660 MB on disk** but only **24 MB tracked** across 1,572
  files. The repository is lean. The bloat is entirely untracked material
  sitting beside it: `research-papers/` 375 MB, `pptx/` 131 MB,
  `intent-control-plane/` 116 MB, `work-docs/` 11 MB.

The consolidation therefore does **not** need a history rewrite on claude-setup.
It needs the working directory swept.

One complication that lands directly on the branch-protection problem: the
largest *tracked* files are
`work-docs/audits/2026-06-29-hedg-com-website-engineering-audit/` — screenshots
and Lighthouse evidence from a client website audit. That is employer/client
material, tracked, in the repo. So "make claude-setup public to get free branch
protection" is not a one-step move: it requires scrubbing `work-docs/` first, or
splitting it out. Options are (a) pay for GitHub Pro and keep it private,
(b) split `work-docs/` into a separate private repo and make the harness public,
or (c) accept no branch protection on the god project. (b) is the only one that
is both free and safe, and it is real work.

### Delete recommendation

- **Media (stickers, GIFs, photos, audio, video): delete.** ~205 jpg + 21 mp4 +
  17 webp + 8 opus + 4 mp3 + 3 mov + 3 m4a. Zero engineering value; they are the
  bulk of the 951 MB.
- **Six exact byte-duplicates** (md5-confirmed): `00000315-*.pptx`,
  `00000074-STICKER-*.webp`, `00000776-WhatsApp Chat - לוּלָה.zip`,
  `00001289-Deterministic_Layout_Optimization.pdf`, `00001175-_chat 14.txt`,
  `00000216-GIF-*.mp4`. Delete the duplicate of each pair.
- **Third-party chat transcripts: delete or move out.** `00000973-_chat 7.txt`
  (2-party), `00000974-_chat 6.txt` (10-party), `00001039/00001176-_chat 10/12`
  (10-party, 54k messages each), `00001174/00001175-_chat 14/15` (9-party),
  `00000777-_chat.txt` (4-party). These are **other people's conversations** —
  tens of thousands of messages from named third parties. Under this repo's own
  `pii-handling` rule and the `.gitignore`'s stated "other people's data"
  policy, they must not stay in a repo that may one day get a remote.
- **KEEP: `_chat.txt`** (556 KB, root, unnumbered). This is the self-chat, 798
  logical messages, 28.10.2020 → 26.7.2026. It is the actual subject of the work.
- **KEEP for now:** the 39 PDFs and 4 MDs pending a skim; several are papers and
  the 2026-05-08 personal-context bundle the chat references.

Recommended landing zone: move the keepers to `docs/wa-selfchat/` and delete the
rest, rather than leaving 951 MB loose in the root.

## The self-chat: what is actually in it

798 messages. Link domains, ranked: github.com (193), youtube.com (70+55+48
across three hosts), linkedin.com (43), facebook.com (33), learn.microsoft.com
(17), gadial.net (16), perplexity.ai (13), reddit.com (13), arxiv.org (12),
edx.org (11), kaggle.com (8), datacamp (8), anthropic.com (7), code.claude.com (6).

This is a **research-capture channel**, not a diary. The dominant behavior is:
find a repo or paper, paste the link, occasionally paste a long synthesized
analysis back to himself.

### Personal thinking worth keeping

Four threads stand out, all of them his own framing rather than pasted content:

1. **"Repo is memory, not chat history."** Message #556 (8.1.2026) is a full
   *Claude Code Operating System* spec: a deterministic state machine with
   phases DEFINE → PLAN → DEBATE → IMPLEMENT → TEST → HANDOFF → RELEASE → CLOSE,
   each with required artifacts and a pass/fail gate, plus a "context bankruptcy
   rule" (end sessions at phase boundaries). **This is the direct ancestor of the
   ship gate that exists in this repo today.** The idea was written down six
   months before the gate was built.

2. **Builder → Reviewer → Adversary.** Message #724 (5.5.2026): having already
   built builder-vs-reviewer, he argues for a third adversarial role whose job is
   to break the solution. He ties it to what labs are doing with alignment
   auditing agents. This is the seed of the persona-panel reviewer in the gate.

3. **Evaluation awareness breaks testing.** Same message: models detect they are
   being tested and behave differently in deployment, so fixed eval prompts are
   worthless. His prescription: randomize evaluation, paraphrase prompts, reorder
   instructions, inject noise tasks. **This directly indicts the current gate's
   fixed 32-pattern review panel** — the panel is exactly the kind of fixed
   oracle he argued against, and today it produced a false positive by matching
   the word "eval" in an English sentence.

4. **The production-fragility list.** Message #731 (9.5.2026): AI-generated apps
   look good in demos and become fragile in production — insecure auth, broken
   state management, API exposure, duplicated logic, hallucinated packages, and
   "people building apps without understanding the code." This is the honest
   counterweight to his own velocity, and it is the argument for the refactor.

A fifth, lighter one: message #736 (14.5.2026) is a repo-virality playbook, and
its best line is about voice — end the README with a personal verbal tic
("bottom line", Hebrew code-switching) so the repo reads as made by a person.

## CORRECTION: `_chat.txt` is not an engineering notebook

Earlier in this file I wrote "KEEP `_chat.txt`" and called the channel a
research-capture log. That was true of the 2026 portion and **wrong about the
file as a whole.** Reading the 34 pre-2026 long messages (>=900 chars, 84,378
chars total: 1 from 2020, 2 from 2021, 1 from 2022, 1 from 2023, 4 from 2024,
25 from 2025) shows the archive is bimodal in kind, not just in length.

Before roughly mid-2025 this was a **personal channel**. It contains, by
category and without quotation here:

- **Intimate personal writing**, including a long 2022 message about
  sexuality, body image, and a relationship. Private in the ordinary sense.
- **Health and psychological content**, in the same register.
- **A military identity number** in a 2023 reserve-deferral request, alongside
  rank, unit context, and named operations.
- **Family and biographical detail**: parents, a sibling's employer, birthplace.
- **Hebrew comedy, rap, and satire written for named friends**, which is the
  single largest genre by message count and names real people throughout.
- **Teaching material** for a school mathematics competition, including
  instructions naming a student.

Consequences, and they are not optional:

1. **`_chat.txt` must not be committed, ever**, and must not move into
   `docs/wa-selfchat/` inside a repo that may get a remote. Supersede the
   earlier recommendation in this file.
2. **It must not be sent to any external model or third-party service.** That
   includes the Gemini Free Tier path the global contract already forbids for
   resumes, and it includes any "summarize my notes" convenience call.
3. The engineering-relevant portion is **only 2026 onward**. If a durable
   artifact is wanted, extract that slice to a new file and leave the original
   outside the repo entirely.
4. The military ID means this is not merely private, it is identity data. Treat
   the file at the same level as `.env`.

The corpus mining already done complied with this: extraction ran locally, only
metadata and 2026-era engineering content was surfaced, and nothing intimate was
reproduced into any report.

### The pre-2026 engineering signal, such as it is

Four messages carry real technical content, and one carries a behavioral pattern
worth building on:

- **#269 (18.7.2024)** — a Titanic/scikit-learn pipeline being tuned, with the
  operator noting the gap between 78.5% actual and 82-84% validation. The
  earliest visible instance of him distrusting a metric rather than accepting it.
- **#315 (11.11.2024)** — PhantomReach hardware reasoning: Integrum uses
  fiducial markers plus muscle sensors, and his insight is that detecting the
  *armband* rather than the *hand* generalizes the training set from amputees to
  anyone. A genuine product insight, and it maps to the `phantom-reach` repo.
- **#337 (13.1.2025)** — a full AR phantom-limb-pain clinical trial proposal:
  control arm, NRS/VAS outcome measures, EEG/fMRI for neuroplasticity,
  HIPAA/GDPR handling. Substantially more rigorous than anything in the 2026
  material.
- **#331 (9.1.2025)** — a multi-channel complaint-analysis architecture with
  cited literature, FastAPI + Kafka, sub-2-second targets.
- **#356 (7.2.2025)** — the highest-leverage one for the GitHub strategy. He
  saw a principal engineer's post, found the linked repo broken, messaged them
  within **11 minutes**, and had a serious pull request open shortly after,
  having cloned and extended the project. He explicitly frames it as practice:
  learning to contribute quickly to external code. This is a demonstrated,
  repeatable behavior and it is worth far more to a hiring story than another
  private repo.

**Bottom line for the architecture work:** the 2020-2025 portion of this archive
is biography, not engineering, and the consolidation plan should draw on it for
exactly two things: the PhantomReach product insight, and the evidence that he
already knows how to land external PRs fast.

## The 77 referenced GitHub repos

Full machine-readable list at `scratchpad/selfchat_repos.json`. Shape of it:

- **Agent/Claude tooling (the largest and most recent cluster):**
  `anthropics/claude-code` (x9, the most-referenced single repo),
  `musistudio/claude-code-router`, `majkonautic/claude-code-mcp-guide`,
  `affaan-m/everything-claude-code`, `amirfish1/claude-command-center`,
  `breaking-brake/cc-wf-studio`, `Master0fFate/just-my-skills`,
  `mattpocock/skills`, `AI-Builder-Club/skills`,
  `nextlevelbuilder/ui-ux-pro-max-skill`, `AgriciDaniel/claude-obsidian`,
  `scottstts/Threejs-Awesome-Graphics-Agent-Skills`, `github/spec-kit`,
  `ofekron/better-agent`, `glittercowboy/get-shit-done`
- **Memory / knowledge graph (the newest cluster, all July 2026):**
  `topoteretes/cognee`, `MemTensor/MemRL`, `MemPalace/mempalace`,
  `FalkorDB/FalkorDB`, `colbymchenry/codegraph`, `dolthub/dolt`
- **Multi-agent research:** `facebookresearch/HyperAgents`,
  `bytedance/deer-flow`, `karpathy/autoresearch`, `uditgoenka/autoresearch`,
  `emergent-inc/mosaic`, `katanemo/plano`, `significant-gravitas/AutoGPT`
- **Code review / quality:** `alibaba/open-code-review`, `pbakaus/impeccable`,
  `rtk-ai/rtk`, `safety-research/bloom`
- **Older ML/DS era (2024-2025):** `cerlymarco/shap-hypetune`,
  `princeton-nlp/tree-of-thought-llm`, `molson194/...CS188`, `astral-sh/uv`
- **Org-only refs** (a single 15.7.2026 message pasted 6 times listing NVIDIA,
  google, google-deepmind, microsoft, MicrosoftResearch, facebookresearch, apple,
  11labs, huggingface, stanford, berkeley, harvard, EleutherAI, mistralai, and
  others) — this is a "follow these orgs" list, not 15 separate decisions.

Classification into absorb / watch / discard is the next unit of work.

## The 32 own repos: current posture

32 repos: 27 public, 5 private, 3 forks. Languages: Python 9, Jupyter 9,
TypeScript 4, Rust 2, HTML 2, C++ 1, SQL 1, none 4. Push activity: 23 in 2026,
7 in 2025, 2 in 2024.

Active core (pushed within the last week): `Resonant-Harmonics-Agents`,
`agenteval-bench`, `sqltok`, `matchiq`, `daily-deep-learning`, `mcp-guard`,
`claude-memes-skills`, `claude-setup`.

### The single biggest finding

**Branch protection is off on every repository checked.** Nine repos sampled,
nine unprotected. Two distinct causes:

- Public repos (`agenteval-bench`, `sqltok`, `mcp-guard`, `matchiq`,
  `daily-deep-learning`, `protobuf-fuzz-guard`, `phantom-reach`, `ShovalBenjer`):
  404 "Branch not protected" — simply never configured.
- Private repos (`claude-setup`): 403 "Upgrade to GitHub Pro" — **branch
  protection on private repos is a paid feature.** `claude-setup`, the repo that
  holds the operating rules for everything else, is structurally unprotectable
  on the current plan. Either it goes public (after a scrub) or it gets Pro.

CI exists but is decorative without protection: workflows per repo run 1-6
(`sqltok` 6, `protobuf-fuzz-guard` 5, most others 2-3), yet nothing blocks a
direct push to `main`. PR counts are low (0-9), so the dominant path is
commit-straight-to-main with CI as an after-the-fact notification.

`protobuf-fuzz-guard` is the outlier worth copying from: 5 workflows, 9 PRs, and
the only repo still on `master` rather than `main`.

## The operator-input corpus (added mid-session, on request)

Scraped from every past Claude Code session. **Inputs only**: no assistant turns,
no tool results, no subagent turns, no hook or system injections.

Two sources merged and deduplicated:

- **46 session transcripts** at `~/.claude/projects/*/*.jsonl` → 440 prompts,
  reaching back to 2026-06-25. The other 545 `.jsonl` files under those
  directories are `subagents/` and `subagents/workflows/` transcripts and were
  deliberately excluded: those are prompts written *by* Claude to its own
  workers, not by the operator.
- **`~/.claude/history.jsonl`** → 539 entries reaching back to **2026-05-25**,
  a month earlier than any surviving session file, and covering two projects
  whose transcripts have since rotated away (`oren-roast-hq`, and a OneDrive
  copy of new-recruit).

**Merged: 691 distinct prompts, 2026-05-25 → 2026-07-26, 5,350,807 chars.**
Four secret-shaped values were redacted in flight; a re-scan of the landed
corpus found only a secret *name* (`JIRA…KEY`) and two `AAAA…` placeholders.

Landed at `~/.claude/corpus-operator-inputs/` — deliberately **outside this
repo**, because 5.35 MB of raw personal prompt history must not sit in a tree
that may one day get a remote.

### Topic split (classified on content, not just cwd)

| topic | prompts | chars |
| --- | ---: | ---: |
| claude-setup | 173 | 3,546,437 |
| resume-engine | 124 | 1,501,275 |
| learning-platform | 30 | 253,298 |
| social-posting | 6 | 1,079 |
| unclassified | 358 | 48,718 |

cwd alone mislabels this corpus badly: the operator does claude-setup work from
inside the new-recruit working directory constantly (this very session is an
example), so bucketing is keyword-based with cwd only as an override.

### What the corpus says about how he works

1. **claude-setup is empirically the god project.** It is 66% of all prompt
   content by volume despite being 25% of prompts by count. His own framing is
   confirmed by the data, not just asserted.
2. **Prompt length is bimodal, hard.** p50 is 165 chars; p90 is 37,960; max is
   70,073. He either types a one-line directive or pastes an entire document.
   There is almost nothing in between. Any system built for him must handle both
   a terse imperative and a 70 KB dump as first-class inputs.
3. **358 of 691 prompts are unclassifiable and average 136 chars.** These are
   continuation tokens: "yes", "go on", "did you finish". Over half of all
   operator turns are steering an in-flight task rather than starting one. That
   is the strongest argument in the corpus for the loop/gate architecture: the
   bottleneck is not instructing, it is supervising.
4. **social-posting barely exists** (6 prompts, 1,079 chars), consistent with it
   being the stated *planned* fourth project rather than an active one.

## Next actions, in order

1. **Revoke the three Telegram tokens.** Nothing else matters until this is done.
2. Delete the media and duplicate files; move third-party transcripts out of the
   repo; land `_chat.txt` in `docs/wa-selfchat/`.
3. Classify the 77 referenced repos into absorb / watch / discard.
4. Deep-read the ~30 pre-2026 long messages not yet covered.
5. Draft the target architecture: which of the 32 repos merge, which archive.
6. Write the commit/PR/review upgrade with concrete config, starting with
   branch protection + required status checks on the active core.

## Coverage boundary

Read in full: `_chat.txt` (798 messages, parsed and indexed; long-form messages
from May-July 2026 read closely, plus the top-15 longest overall). **Not yet
read closely:** roughly 30 long messages from 2020-2025, and the 39 PDFs. The
other seven transcripts were profiled for sender-count and date-range only,
deliberately not read, because they are third-party conversations. Repo posture
was sampled on 9 of 32 repos, chosen by recent push activity, not all 32.
