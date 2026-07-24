# Initiative: Video Understanding Roadmap

**Date drafted:** 2026-05-12
**Owner:** Shoval (Adnan = business owner / dogfood reviewer)
**Context (1-2 sentences):** Three-phase plan agreed with Adnan today: get the deployed app working through Yasha's pipeline/Bicep flow, wrap the pipeline as a secured Telegram bot, then stand up an Azure-native learning loop that ingests videos and generates new scripts. Today the prod app is crashing on every upload (FileNotFoundError on `az` subprocess); fix is sitting in worktree but hasn't shipped via the right path.

---

## TASK 1: Ship Video Understanding v3 to ACA via Azure DevOps pipeline + Bicep

- **Type:** Task
- **Priority:** P0
- **Components / labels:** Infra, DevOps, video-understanding
- **Estimate:** M
- **Depends on:** none (blocker for all downstream Adnan testing)

**Description:**
Adopt Yasha's existing PR → ADO pipeline → Bicep `what-if` → Bicep deploy flow as the only path to production. Retire the manual `app-video-understanding-prod` App Service. New target compute is the Bicep-defined Container App (`ca-video-understanding`). The v3 image carries 4 code fixes from the worktree: workdir path env-var, `az` subprocess removed (now Key Vault SDK with MI), download filenames SHA-keyed, multilingual auto-detect across ar/es/pt/en.

**Acceptance criteria:**
- PR merged to master triggers the pipeline cleanly
- Bicep `what-if` reviewed and approved (no surprise resources)
- ACA `ca-video-understanding` reachable on public FQDN; `/_stcore/health` returns 200
- Adnan can upload an ar AND a non-ar TikTok video; both produce a brief with the right transcript
- Manual `app-video-understanding-prod` App Service deleted (or stopped, pending Yasha OK)

### Subtasks

- [ ] **SUB 1.1:** Decide ACR target (acrazaivideogen vs sentimarkregistry)
      Description: Bicep `main.bicepparam` currently points at `acrazaivideogen` which doesn't exist. Either create it (~$5/mo Basic, matches Yasha's design intent) or repoint to existing `sentimarkregistry`. Surface to Yasha; record decision.
      Estimate: S

- [x] **SUB 1.2:** Remove Docker Hub from Dockerfile — base from MCR only ✅ DONE in worktree
      Description: Both `FROM` lines switched to `mcr.microsoft.com/devcontainers/python:3.12-bookworm`. Local `docker build .` passes (17 steps). Image runs: ffmpeg + curl present, no `az` CLI, all Python deps import. Policy enforced: never Docker Hub in Dockerfile, deploys ONLY via Azure DevOps pipelines.
      Estimate: S

- [ ] **SUB 1.2a:** Slim the runtime image (3.6GB → target ≤500MB)
      Description: Devcontainers base is heavy (vscode-server, sudo, ssh, git, dev tools). Follow-up after the deploy is healthy: multi-stage with `mcr.microsoft.com/azurelinux/base/python:3.12` as runtime + ffmpeg from static binary (BtbN/FFmpeg-Builds GitHub release) since ffmpeg is not in Azure Linux base repos. Keeps zero Docker Hub usage.
      Estimate: M

- [ ] **SUB 1.3:** Commit worktree changes + open PR to master
      Description: 40/40 tests green in `worktree-vu-workdir-fix`. Commits to land: workdir env-var fix, KV SDK auth fix, download filename SHA fix, multilingual auto-detect (STT + vision + synth + template). PR description references this initiative + the meeting notes file.
      Estimate: S

- [ ] **SUB 1.4:** Run pipeline → Bicep `what-if` → Deploy stage (manual approval gate)
      Description: Confirm `what-if` only proposes the documented resources (ACA, ACA env, Log Analytics, 3 role assignments). Approve deploy stage. Validate the in-pipeline smoke check returns 200 from `/_stcore/health`.
      Estimate: S

- [ ] **SUB 1.5:** Live smoke via Playwright + real upload
      Description: Open the new ACA FQDN, upload the ssstik @assadtradess TikTok video, verify Step 6 completes, the result panel shows the correct video name + SHA, transcript is raw Arabic dialect (not analysis). Upload one non-Arabic clip from Adnan's batch and verify auto-detect picks up the language.
      Estimate: S

- [ ] **SUB 1.6:** Retire manual App Service `app-video-understanding-prod`
      Description: After SUB 1.5 passes, send Yasha a one-liner that the orphan App Service is going away. Wait for OK, then delete. Counts as one resource cleanup, NOT a creation.
      Estimate: S

---

## TASK 2: Wrap Video Understanding pipeline as a secured Telegram bot

- **Type:** Task
- **Priority:** P1
- **Components / labels:** Backend, AI, video-understanding, Bot
- **Estimate:** L
- **Depends on:** TASK 1 (ACA must be healthy first; the bot calls the same pipeline)

**Description:**
Adnan wants to drop a TikTok URL or attach an MP4 in Telegram and get back a structured brief (HTML + JSON) without opening a browser. The bot must be secured (only allowlisted Telegram user IDs trigger it, webhook is Entra-gated, no public commands). Architecture is sketched below; spec lives under SUB 2.1.

**Acceptance criteria:**
- Bot responds only to allowlisted Telegram chat IDs / usernames (configurable via App Setting, not hardcoded)
- Bot accepts: (a) a TikTok URL OR (b) a direct MP4 attachment
- For URL: downloads via ssstik-style scraper or yt-dlp into the same workdir scheme
- Reuses the existing pipeline (no duplicate code path); reuses the SHA-dedup of the workdir
- Returns three artifacts in chat: (1) short text summary, (2) brief.json, (3) link or attached brief.html
- Bot infra deploys via the same Bicep pattern as TASK 1 — no manual `az` from a workstation

### Subtasks

- [ ] **SUB 2.1:** Architecture spec — auth, ingest, dedup, output
      Description: Markdown spec under `docs/superpowers/specs/`. Covers: bot framework choice (python-telegram-bot vs Azure Bot Service), webhook hosting (Function App vs ACA), allowlist mechanism (App Setting list, or AAD group), TikTok URL ingest (yt-dlp via subprocess in a hardened image — same Dockerfile pattern as today), dedup hit/miss UX (when SHA hits cache, just resend the previous brief — saves cost).
      Estimate: M

- [ ] **SUB 2.2:** Implement TikTok URL → MP4 downloader behind same workdir scheme
      Description: Single function `download_to_workdir(url) -> Path`. Uses yt-dlp; output filename derived from URL hash so re-uploads of same URL hit cache. Unit tests with recorded HTML fixtures (no live yt-dlp calls in CI).
      Estimate: M

- [ ] **SUB 2.3:** Telegram bot handler + allowlist gate
      Description: Single entry point that receives Telegram update → checks allowlist → routes to URL or file handler → calls pipeline → posts response. Allowlist hot-reloads from App Setting. Tests cover deny (non-allowlist) AND accept paths.
      Estimate: M

- [ ] **SUB 2.4:** Bicep + pipeline wiring for bot infra
      Description: Extend `infra/main.bicep` with bot-specific resources (likely a 2nd ACA or Function App), Telegram webhook secret in Key Vault, same MI grants. Pipeline gains a 2nd build/deploy track gated on the same PR flow.
      Estimate: M

- [ ] **SUB 2.5:** End-to-end smoke with Adnan
      Description: Adnan sends a TikTok URL + an MP4 attachment from his phone; both produce the expected brief in chat within ~3 minutes; deny path verified by Shoval sending from a non-allowlisted account.
      Estimate: S

---

## TASK 3: Stand up Azure-native data + learning loop → generative script feature

- **Type:** Task
- **Priority:** P2
- **Components / labels:** AI, Data, video-understanding, ML
- **Estimate:** XL
- **Depends on:** TASK 1, TASK 2 (need a live ingest path before there's data to learn on)

**Description:**
Every video ingested (via app or bot) gets stored once, keyed by content hash for dedup. Build a reward / signal layer Adnan can rate against. Run Azure-native learning from low-end (RL on a value function) up through fine-tuning a generation model on the curated corpus. End goal: a button that says "generate a new ad script in the style of <subset of the corpus>" backed by a fine-tuned model.

**Acceptance criteria:**
- Every video processed has exactly ONE row in the store keyed by SHA-256 of bytes (no duplicates ever)
- Reward signal definition agreed with Adnan and recorded in a spec — what makes a script "good"
- At least one trained model deployed to Foundry that produces a brief in the same schema, demonstrably scoring above the GPT-5.4-SIU baseline on Adnan's hand-labeled eval set
- Generation endpoint reachable via the same Bicep-deployed surface

### Subtasks

- [ ] **SUB 3.1:** Dedup-keyed store design (Blob + Postgres or Cosmos Table)
      Description: Decide storage shape. Blob for raw MP4 + brief.html + brief.json keyed by `sha256/<hex>/...`; metadata index in Postgres (cheap, SQL-friendly for analytics) or Azure Table (cheaper, less expressive). Spec under `docs/superpowers/specs/`. Schema covers: source URL, ingest timestamp, source_language, target_country, dialect, Adnan rating (when set), embedding (for later kNN retrieval).
      Estimate: M

- [ ] **SUB 3.2:** Dedup write-path in pipeline
      Description: After `stage_render`, write all artifacts to the dedup store. If SHA already exists with same template version, no-op. Wire into both TASK 1 (Streamlit) and TASK 2 (bot) ingest paths through a single `store_brief()` function. Tests cover collision + same-version skip + different-template-version write.
      Estimate: M

- [ ] **SUB 3.3:** Reward signal definition (with Adnan)
      Description: 30-min session with Adnan. What makes a generated script "good"? Options: numeric rating, side-by-side preference, structured feedback per brief section (hook, pain, CTA). Pick ONE definition and lock it in writing.
      Estimate: S

- [ ] **SUB 3.4:** Labeling UI + eval set
      Description: Tiny Streamlit page that lets Adnan rate stored briefs against the reward definition. Produces a labeled CSV / Parquet that's the eval set for SUB 3.5/3.6. Start with 30-50 briefs.
      Estimate: M

- [ ] **SUB 3.5:** R-learning / value-function baseline
      Description: Fit a simple reward model (gradient-boosted regressor over brief features + Adnan ratings). Use Azure ML or Foundry; not OpenAI platform. This is the baseline that fine-tuning has to beat. Document score.
      Estimate: M

- [ ] **SUB 3.6:** Fine-tune a generation model on the curated corpus
      Description: Pick the Azure-native fine-tune target (Azure OpenAI fine-tuning on gpt-4o-mini OR Foundry fine-tuning). Train on the labeled corpus. Deploy to Foundry. Wire an inference call that produces a brief in the same schema.
      Estimate: L

- [ ] **SUB 3.7:** "Generate new script" feature in the app + bot
      Description: New button: "Generate a script in the style of <subset>". Inference call to the fine-tuned model from SUB 3.6 with conditioning on the subset selection. Output: brief.json + brief.html using the same Jinja template.
      Estimate: M
