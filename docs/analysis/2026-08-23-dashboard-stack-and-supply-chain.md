# Dashboard stack decisions and the intake security regime, 2026-08-23

Point-in-time record of three operator questions asked mid-session: why npm and not bun;
which of the suggested Rust crates the dashboard actually needs; what security measures
apply when outside binaries and repos come in. Sources are named inline; nothing here is
from memory.

## 1. Package manager: bun, decided and applied

npm was used earlier today only because `dashboard/web` carried a `package-lock.json` and
the repo convention rule says follow the existing manager. Two facts broke that tie the
same hour: Vite 7 refuses Node 18.19 (the apt default this shell gets; the Node 22 the
08-19 measurement used lives in nvm and only interactive shells see it), and bun 1.3.14
is already installed and runs the build in 4.95s with no Node at all.

Landscape check (TECHSY 2026-02-12 comparison; nazarboyko.com 2026-05-30; craigory.dev
2026-05-29 cooldown reference; pnpm.io/supply-chain-security):

- bun: fastest installs by 3x to 17x, dependency lifecycle scripts blocked by default
  behind `trustedDependencies`, text lockfile since 1.2, `bun audit`, and
  `install.minimumReleaseAge` (seconds) since 1.3.0. Joined Anthropic December 2025.
- pnpm 11: the strictest defaults in the ecosystem (cooldown 1440 min and
  `blockExoticSubdeps` on by default, `trustPolicy no-downgrade` against provenance
  regression) and the strongest monorepo story. The general-case winner in both surveys.
- npm 11: `min-release-age` and `allowScripts` exist but are opt-in until npm 12.

Decision: bun. The repo's global rule already names it, it is the only one of the three
that removes the Node-version problem instead of managing it, and its security defaults
match pnpm's on the two controls that matter (scripts blocked, cooldown available).
pnpm would win in a many-package monorepo; `dashboard/web` is one package. Applied:
`bun.lock` committed, `package-lock.json` removed, `bunfig.toml` sets
`minimumReleaseAge = 86400` seconds, CI's dashboard-web-build step now uses
oven-sh/setup-bun with `bun install --frozen-lockfile` so a drifted lockfile fails
instead of rewriting itself. `bun audit` on the tree: no vulnerabilities.

## 2. The suggested crate list, item by item

The list arrived as a block (pool, locks, serde, errors, async, watch, logs). Verdicts
against the code as it exists, not against the category:

| suggested | verdict | why |
|---|---|---|
| r2d2 + r2d2_sqlite | rejected for now | a pool solves write contention and connection reuse under load; this is a desktop app reading five local files. Opening a SQLite connection read-only costs microseconds, so the SQL tab opens one per command with `SQLITE_OPEN_READ_ONLY`. The falsifier that revives the pool: a measured query rate where per-open cost shows up. |
| parking_lot | rejected | std's Mutex has been futex-based and fast for years; adopting a replacement without a measured contention profile is the exact pattern /prove-implementation exists to stop. |
| serde derive | already present | both crates carry it since DASH-1 slice 1. |
| thiserror | accepted, added (2.0.20) | but not to `Result<T, String>`. The boundary-contracts rule requires a typed error DTO across the IPC seam, so the SQL commands return `Result<T, SqlError>` where `SqlError` derives `Serialize` and `thiserror::Error`. Stringly errors are the half-contract the rule names. |
| anyhow | rejected | for a library crate with a typed boundary, thiserror covers it; anyhow belongs in binaries that only report. Adding both is how error types stop meaning anything. |
| tokio direct | rejected | Tauri 2 already embeds a tokio runtime; heavy queries go through `tauri::async_runtime::spawn_blocking`. A second tokio dependency adds feature-flag drift for zero new capability. |
| notify (debounced) | accepted, added (notify-debouncer-mini 0.7) | the real gap: the feed polls today. A debounced watcher on `state/*.jsonl` and the intent db pushing `tauri::Emitter` events is the difference between a dashboard and a refresh button. |
| tracing + tracing-subscriber | accepted, added (0.1.44 / 0.3.23, env-filter) | replaces `println!` diagnostics before the SQL tab lands, so slow queries are attributable. |

`cargo test --workspace` after all additions: clean full rebuild in 7m41s, 16 tests pass.

## 3. Intake security: what runs before anything third-party lands

The infrastructure already existed and had never fired: ADR-0019 built
`tools/supply/verify.py` (hash-chained ledger, fetch-script that refuses to execute
installers, sign-check via `gh attestation verify` or cosign, scanner harness) and
`state/supply-chain.jsonl` did not exist until today. Today's own installs went in
unrecorded first: the duckdb binary arrived by `curl | sh`, which is precisely the path
`fetch-script` exists to replace. Recorded retroactively as rows 0 to 2 (duckdb binary
sha256 3d33b1df..., bun.lock, Cargo.lock); chain verifies.

The regime, in the order a new artifact meets it:

1. Provenance before bytes. A repo gets an `external-repo.v1` row (source, licence,
   stars, pushed date) before serious use; a binary gets a `supply-chain.jsonl` row with
   its sha256. `curl | sh` is replaced by `verify.py fetch-script`, which downloads,
   hashes, records, and refuses to run the installer until it is read.
2. Signature where one exists. GitHub releases with attestations: `gh attestation
   verify` (gh is installed; this works today). Sigstore bundles: cosign `verify-blob`
   with `--certificate-identity` pinned to the producing repo's workflow, per the
   sigstore end-user guidance. Checksum-only verifies integrity, not authenticity, and
   is recorded as exactly that.
3. Install-time gates for package managers. bun: scripts blocked by default plus the
   86400s cooldown now in `bunfig.toml`; frozen lockfile in CI. Cargo: `--locked`
   installs, and (compiling now) `cargo audit` for RUSTSEC advisories and `cargo deny`
   for licence and source policy. The scanner harness records `unavailable` rather than
   clean when nothing is installed, which was the state of this machine until today:
   zero of osv-scanner, trivy, grype, cargo-audit, cargo-deny, cosign present.
4. Review depth by blast radius. A dependency that runs at install time or in CI gets
   read before adoption (cargo-vet's relative-audit model is the pattern to grow into);
   a leaf library behind a typed boundary gets metadata plus scan. This is the same
   depth-by-risk split the gate already applies to code.

Not done, named: cosign and osv-scanner are not installed (cosign's own bootstrap
requires TUF-verifying the first binary, a deliberate step, not an apt line); no gate
domain runs `verify-ledger` yet, so the supply chain ledger is as unverified-by-default
as the resource ledger was this morning (L-2026-08-23-a applies); the bun cooldown does
not cover `cargo install`, which has no equivalent knob and relies on `--locked` plus
audit.
