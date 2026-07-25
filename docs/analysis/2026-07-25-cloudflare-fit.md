# Cloudflare fit audit — 2026-07-25

Scope: does Cloudflare close any of Shoval's five named weak points (AUTO-18 sleep-surviving
schedules, the transcript-archive gap, AUTO-05 phone concierge, AUTO-19 FleetView, the broken
CDP verification loop). Not a Cloudflare product tour. Every claim below is tagged VERIFIED
(command run, output pasted), STAGED (artifact exists, unproven), or ASSUMED (inferred, not
run). Free-tier numbers are dated 2026-07-25, fetched from developers.cloudflare.com same day.

## Bottom line first

Two of five weak points get a real, cheap Cloudflare fix (transcript archive via R2, FleetView
via Pages — the second literally reusing a pattern already proven). One gets a partial fix that
still leaves the hard half unsolved (AUTO-05: Workers can receive the phone signal, nothing on
the free tier can wake or drive the local Claude Code CLI). One is a false fit that should be
said plainly: Cron Triggers do not solve AUTO-18 as scoped, and a native scheduling capability
already in this Claude Code build (the `schedule` skill / CronCreate tool) is redundant with it
where it would help at all. One is a non-fit and should not be adopted: Browser Rendering cannot
reach `localhost` or the Windows-side Edge SSO session the CDP loop depends on, so it cannot
verify a local build no matter how the loop gets fixed.

Everything below shares one unmet prerequisite: **wrangler is not authenticated on this machine.**
`~/.wrangler/config/` (where the OAuth token or scoped API token would live) does not exist —
only `logs/`, `tmp/`, `metrics.json`, and a repo cache file. No `CLOUDFLARE_API_TOKEN` or `CF_*`
env var name is set (checked names only, no values printed, per the pii-handling rule). The
existing daily-deep-learning deploy works because it runs entirely inside GitHub Actions using
`secrets.CLOUDFLARE_API_TOKEN` / `secrets.CLOUDFLARE_ACCOUNT_ID` — a CI-side credential this
machine has never had. Before any item below, run `bunx wrangler login` (or set a scoped
`CLOUDFLARE_API_TOKEN`) and confirm with `bunx wrangler whoami`.

## What he already has (established before speculating)

- **wrangler**: not previously installed as a persistent binary; `bunx wrangler --version` on
  2026-07-25 resolved and ran `4.114.0` fresh via bunx's on-demand fetch. VERIFIED (command run,
  exit 0). This is bunx pulling wrangler on demand, not evidence of a standing local tool.
- **wrangler auth**: NOT configured locally. VERIFIED — `~/.wrangler/config` does not exist
  (`ls` errored "cannot access"); the only files under `~/.wrangler/` are `logs/`, `tmp/`,
  `cloudflare-skills-repo-cache.json`, `metrics.json`. No local OAuth session, no local scoped
  token.
- **`CLOUDFLARE_API_TOKEN` / `CF_*` env var names**: none set in this shell. VERIFIED (`Get-ChildItem
  Env: | Where-Object Name -match 'CLOUDFLARE|CF_'` returned nothing). Values were never requested
  or printed.
- **daily-deep-learning.pages.dev**: real, live, deployed. VERIFIED — WebFetch returned an
  actual rendered Hebrew SPA ("הסדנה אלפא", nav items היום/העץ/האוצר/תגליות/המסלול), not a
  placeholder or 404.
- **Deploy mechanism**: GitHub Actions, not local wrangler. VERIFIED — `.github/workflows/deploy.yml`
  in `C:\Users\shova\Downloads\daily-deep-learning` runs `cloudflare/wrangler-action@v3` with
  `command: pages deploy . --project-name=daily-deep-learning --branch=main`, gated on push to
  `main`, using `secrets.CLOUDFLARE_API_TOKEN` and `secrets.CLOUDFLARE_ACCOUNT_ID` (GitHub-side
  secrets, values unread and unreadable from here).
- **A live Worker already exists**: `daily-deep-learning/sadna-sync/wrangler.toml` defines a
  Worker (`sadna-sync`, `worker.js`) bound to one KV namespace (`STATE`). VERIFIED by reading
  both files. `worker.js` is a small bearer-token-gated sync endpoint (PUT/GET a JSON blob into
  KV, 300KB size cap, JSON-parse validated before storage, CORS locked to the Pages origin). This
  means Workers + KV are not new territory — there is a real, already-running, reasonably-typed
  boundary (auth check, size cap, JSON validation before write) to build the next thing next to,
  not a green field.
- **cloudflared (Tunnel client)**: installed, unconfigured. VERIFIED — `C:\Users\shova\bin\cloudflared.exe`,
  version `2026.7.2` (`cloudflared --version` ran clean), downloaded 2026-07-21. No `~/.cloudflared/`
  config directory exists — no tunnel has ever been created or run. This is a staged capability,
  not an active one, and it matters below because it is the actual missing piece for reaching a
  local process from outside, not any Workers product.
- **Local transcript store** (the thing to archive): VERIFIED — `C:\Users\shova\.claude\projects`
  holds 4 project directories, 287 `.jsonl` files, **130.34 MB total** (0.127 GB). Measured by
  summing file lengths directly, not estimated.
- **The CDP verification loop** (per `.claude/commands/cdp.md`, read in full): a dual-target
  local browser automation setup — Obscura/stealth Chromium on WSL port 9222 for public scraping,
  and a Windows-side Edge launched with `--remote-debugging-port=9223 --remote-debugging-address=0.0.0.0`
  for anything needing Windows SSO/Entra/domain auth (explicitly lists Azure portal, ADO, Widgora
  prod). Its entire reason to exist is attaching to a *locally running, locally authenticated*
  browser process. This is load-bearing for the Browser Rendering verdict below.
- **Task Scheduler** (AUTO-18's current state): VERIFIED via `Get-ScheduledTask` — the four
  Sadna daemon tasks (`SadnaCouncil`, `SadnaCriticFallback`, `SadnaDiscover`, `SadnaGenFallback`)
  ARE registered and in `Ready` state. The "not registered" framing in the brief may be stale, or
  refers to a different task set not visible here; either way, native registration is proven
  possible on this box today, at zero cost, with no Cloudflare involved.

## Free-tier numbers (Cloudflare docs, fetched 2026-07-25)

| Product | Free-tier limit | Source |
|---|---|---|
| Workers | 100,000 requests/day, 10ms CPU time/request, resets midnight UTC, Error 1027 on overage | developers.cloudflare.com/workers/platform/limits/ |
| Cron Triggers | 5 triggers/account max, 10ms CPU time per invocation (shares the Workers cap) | same page |
| Pages | 500 builds/month, 1 concurrent build, 100 projects/account, 20,000 files/site, 25 MiB/file, 20 min build timeout, 100 custom domains/project | developers.cloudflare.com/pages/platform/limits/ |
| R2 | 10 GB-month storage, 1M Class A ops/month, 10M Class B ops/month, **egress free** (Standard storage only, not Infrequent Access) | developers.cloudflare.com/r2/pricing/ |
| D1 | 10 databases/account, 500 MB/database, 5 GB/account total, 50 queries/Worker invocation, 30s max query duration | developers.cloudflare.com/d1/platform/limits/ |
| Vectorize | 100 indexes/account (free) vs 50,000 (paid), 1536 dims/32-bit, 10M vectors/index, 1,000 namespaces/index (free); monthly query cap not stated in the doc fetched | developers.cloudflare.com/vectorize/platform/limits/ |
| Browser Rendering | Available on Workers Free. 10 minutes browser time/day, 3 concurrent browsers, 1 new instance/20s, 60s browser timeout, 5 `/crawl` jobs/day, 100 pages/crawl | developers.cloudflare.com/browser-rendering/platform/limits/ |

## Weak point by weak point

### AUTO-18 — schedules must survive laptop sleep

Cloudflare Cron Triggers (free: 5/account, 10ms CPU/invocation) fire reliably on Cloudflare's
edge regardless of the laptop's power state. That is real. But the thing that needs to survive
sleep is **driving the local Claude Code CLI** — a process bound to this filesystem, this git
worktrees, this MCP server set. A Worker cron firing in the cloud has nothing to call when the
laptop is asleep: there is no local listener, and even if there were, an asleep laptop does not
answer network calls. Cloudflare does not, and structurally cannot, wake a Windows laptop.

Honest failure mode: adopting Cron Triggers here would fire a schedule that reaches nothing,
which is worse than the current gap because it looks solved. The actual fix for "survive sleep"
is either (a) Windows' own Task Scheduler "Wake the computer to run this task" option on the
existing Sadna tasks (native, free, zero new surface), or (b) moving the specific scheduled work
off the local CLI entirely onto something cloud-native — which is exactly what the `schedule`
skill / `CronCreate` tool already installed in this Claude Code build does (scheduled cloud
agents on a cron, no laptop required). That tool is redundant with Cloudflare Cron Triggers for
any job that can be fully cloud-side, and superior to Cron Triggers for anything that still needs
Claude Code specifically, because Cron Triggers cannot invoke Claude Code either way.

Verdict: **does not close AUTO-18 as scoped.** Do not adopt Cron Triggers for this. Fix path is
Task Scheduler wake-flags on the existing four registered tasks, or the already-available
`schedule`/`CronCreate` capability for anything cloud-portable.

### The transcript archive gap (compaction deletes conversation, wants it archived + mined)

This is the strongest fit. R2 free tier is 10 GB-month storage against a measured 130.34 MB
today (287 files) — under 1.3% of the free allowance. Even 50x growth over a year fits inside
the free tier with room. Egress is free, so pulling data back out for mining costs nothing extra.

D1 (5 GB free, SQLite-based) is the natural place for a queryable index over the archive — one
row per transcript session with path/timestamp/project/size, so "find sessions about X" doesn't
require pulling every object out of R2 first. D1 is SQLite, so FTS5 keyword search is plausible
without adding Vectorize at all; that should be tried before adding a vector store, given today's
volume.

Vectorize (100 indexes free, 10M vectors/index) would let "mine the raw gold" mean semantic
search, not just keyword grep. This is real but should be phase 2, not phase 1: it needs an
embedding pipeline (Workers AI has separate limits and cost not checked here, or embeddings would
be generated via the paid Claude/OpenAI API — direct tension with the standing paid-API-avoidance
posture, ADR-0002). At 130 MB and 287 files, D1 FTS or even local ripgrep over a synced copy is
probably sufficient; do not build the vector layer before the keyword layer proves inadequate.

Honest failure mode: none of this writes itself. Cloudflare is the storage backend, not the
ingestion job. Someone still has to hook the PreCompact hook (or a nightly sweep) to push each
`.jsonl` to R2 before/after Claude Code's own deletion, and insert the matching D1 row. That is
real local automation work, not a product toggle. Also: R2 needs its own S3-compatible Access
Key ID/Secret (a new credential, separate from the Cloudflare API token) — must be handled per
the pii-handling/secrets rule (never printed, never committed) once created.

Verdict: **real fit, adopt R2 + D1 first, defer Vectorize.**

### AUTO-05 — phone concierge, capture intent from phone

Workers Free (100k requests/day, 10ms CPU/request) comfortably covers an inbound webhook receiver
for personal-scale phone traffic — CPU time is spent on active computation, not on I/O wait, so a
thin auth-check-and-forward relay (the same shape as the existing `sadna-sync` worker) fits
inside 10ms. This closes the "receive the signal reliably and for free" half.

It does not close the other half: getting the captured intent to actually **drive** Claude Code
locally. That requires either (a) a live local listener reachable from outside, which is exactly
what the already-installed-but-unconfigured `cloudflared` Tunnel is for (not a Workers product —
Workers cannot reach into this laptop; cloudflared is the piece that can, once a tunnel + local
listener are actually configured), or (b) routing to a fully cloud-side agent instead of local
Claude Code, which brings back the paid-API-cost tension from the AUTO-18 discussion above.

Verdict: **partial fit.** Workers is a fine, free inbound endpoint for the phone side. The
concierge is not "solved" by adopting Workers; the local-drive leg still needs the cloudflared
tunnel configured (today: installed, zero config) and a decision on whether the laptop must be
awake for it to work — which reopens the same sleep problem as AUTO-18.

### AUTO-19 — FleetView dashboard

Pages fits cleanly and cheaply: 500 builds/month, 100 projects/account, both far above personal
usage, and there is a proven, working template to copy line-for-line — `daily-deep-learning`'s
own `deploy.yml` (`cloudflare/wrangler-action@v3`, `pages deploy . --project-name=X`). Per the
repo-topology rule, FleetView should be a folder inside an existing umbrella repo with its own
path-triggered pipeline step, not a new top-level repo, and the `pages deploy <subdir>` command
form already supports deploying a subdirectory, so this is compatible with that rule without
modification.

Honest failure mode: Pages only serves what was last pushed. If FleetView needs to show *live*
current state (task status, session activity), Pages alone gives a stale-until-next-push
dashboard, not a live one — something still has to push a fresh JSON snapshot (a GitHub Action,
a local cron, or a small Worker+KV/D1 backend like the existing `sadna-sync` pattern) on some
cadence. That is an explicit design choice to make, not a Cloudflare limitation to solve away.

Verdict: **real fit, cheapest and lowest-risk of the four.** Copy the existing deploy pattern
directly; decide separately (and explicitly) how "live" the data needs to be.

### The CDP verification loop (currently broken)

Say this plainly: Browser Rendering (10 min/day, 3 concurrent, free tier confirmed available)
does not fit and should not be adopted for this. The CDP loop's whole job, per `.claude/commands/cdp.md`,
is attaching to a browser that is already running *locally* — Obscura on WSL port 9222, or Edge
on the Windows host at port 9223 launched with the user's own profile so Entra/Windows-SSO/domain
auth is already live. Cloudflare's Browser Rendering runs a serverless browser on Cloudflare's own
network. It has no path to `localhost` on this laptop, no access to the Windows Edge profile or
its SSO cookies, and cannot see an internal dev server or `*.i-sdd.com`/Azure-portal session that
depends on this machine being the one that's authenticated. Swapping in Browser Rendering would
not fix whatever is currently broken in the local loop; it would verify a different, unrelated
thing (a public URL with its own separate auth, if any).

The one place Browser Rendering could legitimately help is a *different* job than the one named:
a post-deploy visual smoke check against a fully public URL, e.g. screenshotting
`daily-deep-learning.pages.dev` after each Pages deploy to catch a blank/broken render. That is
real but not what was asked, and not urgent enough to take one of the four shortlist slots below.

Verdict: **does not fit, do not adopt for CDP verification.** Whatever is broken in the local
Obscura/Edge loop needs to be diagnosed and fixed locally (that diagnosis is out of scope here).

## Ranked shortlist (at most 4, in adoption order)

All four share the same step 0: **`bunx wrangler login`** (or set a scoped `CLOUDFLARE_API_TOKEN`
env var), then **`bunx wrangler whoami`** to confirm. Nothing below can be created until that
runs — currently ASSUMED-blocked, not yet attempted.

1. **R2 — transcript raw archive.** Closes the named "raw gold" gap; 130 MB today against 10 GB
   free. First command after auth: `bunx wrangler r2 bucket create claude-transcripts-archive`.
   Cost if it grows past free tier: R2 storage is $0.015/GB-month beyond 10 GB — negligible even
   at 10x current volume. Real remaining work: the ingestion hook (PreCompact -> R2 upload),
   not a Cloudflare task.

2. **Pages — second project for FleetView.** Reuses a working pattern verbatim; lowest risk of
   the four. First command after auth: `bunx wrangler pages project list` (confirm the account
   and existing `daily-deep-learning` project before adding a second one).

3. **D1 — transcript metadata/search index, paired with R2, not standalone.** 5 GB free is ample
   for metadata rows; try SQLite FTS5 before reaching for Vectorize. First command after auth:
   `bunx wrangler d1 create claude-transcripts-index`. Real remaining work: schema design and a
   backfill script for the existing 287 files — a small project, not a toggle.

4. **Workers — phone-concierge inbound webhook only (not the full concierge).** First command
   after auth: `bunx wrangler init phone-concierge-inbound` (scaffold, modeled on the existing
   `sadna-sync` worker's auth+size-cap+JSON-validate shape). Explicitly partial: closes only the
   "receive the signal" half of AUTO-05; the "drive Claude Code locally" half still needs the
   already-installed `cloudflared` tunnel configured, which is separate work with its own sleep
   caveat.

## What NOT to adopt, and why

- **Cron Triggers**, for AUTO-18. Cannot wake the laptop or invoke local Claude Code; redundant
  with the native `schedule`/`CronCreate` capability already in this Claude Code build for
  anything that is genuinely cloud-portable, and unable to help with anything that isn't.
- **Browser Rendering**, for the CDP loop. No path to `localhost`, no access to the Windows Edge
  SSO session the loop exists to use. Would verify a different (public-only) surface, not the one
  named broken.
- **Vectorize**, for now. Real product, wrong sequencing — adopt only after R2 + D1 exist and
  keyword/FTS search on D1 proves insufficient at actual volume. Today's 130 MB / 287 files does
  not justify standing up an embedding pipeline, and embeddings likely mean paid API calls, which
  cuts against the standing paid-API-avoidance posture.
- **A second, separate Worker for FleetView's backend**, until the "how live does it need to be"
  question in the AUTO-19 section is actually decided. Building a Worker+KV backend before that
  decision risks the same shape of throwaway work the excavate-before-building lesson already
  flagged once this month.

## Gaps / not verified

- Whether D1's free tier has a daily row-read/row-write cap beyond the size limits: the fetched
  doc only stated 50 queries/invocation and 30s query timeout, no explicit daily row quota. ASSUMED
  safe at current volume; re-check before relying on it for a nightly high-write job.
- Vectorize's monthly query cap on the free tier: not stated in the page fetched. ASSUMED
  non-blocking since Vectorize is deferred anyway.
- Whether the Cloudflare account behind `daily-deep-learning.pages.dev` is the same account that
  would own any new R2/D1/Pages resources: not verified, since `wrangler whoami` was not run (no
  local auth exists yet to run it against). Confirm as the very first step, before creating
  anything.
