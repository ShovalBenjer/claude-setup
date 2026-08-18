# Taste ledger

Design picks the operator made, with the reason in one line. `/diverge` writes here
after every non-mechanical decision, and future creative work reads it before
sampling candidates. The research position is that no automated taste model works
yet, so a human-curated corpus is the state of the art. This is that corpus.

Append only. One row per decision. Never rewrite a row: if a pick is reversed, add a
new row that supersedes it by date and say what changed.

| Date | Decision | Pick | `p_conventional` | Reason |
|---|---|---|---|---|
| 2026-08-12 | Gastown coffee-break v2 design (cross-session social/serendipity mechanism); default was a scheduled random-pair chat on cron | Compose three: smoking area (frustration-triggered gripe sessions mined into TODO/lesson candidates), idea futures (sessions bet persona reputation on each other's riskiest assumptions, settled by gate/refute outcomes), and the flâneur (a standing gossip persona that walks ListAgents across clones and machines carrying news) | 0.10 / 0.20 / 0.35 | Chatter must be causally attached to real signal: complaints ride failure telemetry, bets settle against oracles, and the courier replaces fetch-before-working with a character. The rejected default (p 0.75) and the overhearing wall (p 0.05) lost for having no stakes. |
| 2026-07-29 | Tamper-evidence for `state/prompt-tickets.jsonl`, given that `bus.py::canonical()` hashes a fixed `CHAIN_FIELDS` tuple that covers none of a ticket's content fields | Self-describing rows: each row carries `chain_fields`, and `canonical()` hashes the named fields plus the list itself | 0.10 | A row becomes verifiable by a reader that knows no schema, and shrinking a row's coverage changes its hash instead of hiding. The rejected default put coverage in a constant far from the data, which is what let the original defect exist. |

## Notes on the 2026-07-29 pick

The defect being fixed is worth stating, because it is a category this repo keeps
finding rather than a one-off. `CHAIN_FIELDS` names `id`, `ts`, `from_lane`,
`origin_lane`, `from_session`, `to`, `kind`, `subject`, `body`, `refs`, `prev`. A
prompt-ticket row carries `id`, `ts`, `session`, `repo`, `branch`, `text_sha`,
`state`, `prev`. The intersection is three keys. Had the spec's instruction to import
`canonical` been followed literally, every ticket row would have shipped with a hash
committing to its id, its time, and its predecessor, and to nothing about the ticket.
`row_altered()` would have returned False after an edit to `state` or `text_sha`.

That is the same class as the waiver whose reason is never checked (L-2026-07-29-c)
and the confidence gate with no stored outcomes (L-2026-07-27-d): an accountability
mechanism that is present, runs, reports success, and is structurally incapable of
failing. The pick was made on which option makes that class detectable, not on which
option was smallest.

Constraint killed during defixation: "a hash payload should be a fixed schema
constant." That was inherited from fixed-header chain designs and from how `bus.py`
happens to be written. The real requirement is only that a verifier can recompute the
bytes, and a declared list satisfies it strictly better than a constant the verifier
must already possess. Cost is about sixty bytes per row.

## 2026-07-29: Naming the split writing site: case-ledgers

Decision: the writing site (formerly daily-deep-learning.pages.dev/writing/) deploys
to Cloudflare Pages project `case-ledgers`. Candidates carried conventionality
estimates per the out-of-distribution rule: the-bench (p 0.25, publication named for
its flagship essay), case-ledgers (p 0.35, names the genre; the site's own subtitle
is "Case ledgers and working notes"), ktav-yad (p 0.15, Hebrew anchor), shoval-writing
(p 0.9, the mode, rejected). The operator was asked twice and did not pick; the-bench
ranked first and was attempted, and failed on a fact, not a preference:
the-bench.pages.dev is a third party's Access-walled project, discovered when the
deploy returned "Project not found" [8000007]. case-ledgers was the next candidate
that survives both the taste ordering and the global namespace. The anchor is the
site's own subtitle, so the grounding is auditable in the artifact itself.
Renaming later is one variable in deploy.yml plus _redirects plus canonicals.

## 2026-08-01: The kitty 0.48 surface: which chrome earns its pixels

Context: `~/.config/kitty/kitty.conf` had been written and commented against 0.48.2
while the binary that actually ran was the apt 0.32.2, so 51 options were being
silently dropped. Fixing the launcher made a real design decision available for the
first time, and the operator's ask was "modern image, css styling (beyond latest
react)", which is a look, not a feature list.

Anchor: Kanagawa Dragon by rebelot, already the palette in the COLORS block of that
file. No new theme was invented, and the accents in the generated lane logos are the
same hexes as `color1..color15`.

Candidates, with p_conventional:

- **Stock modern kitty** (p 0.90). Enable what 0.48 already defaults to and stop.
  Rejected: it is the mode by construction, and it answers none of the ask.
- **Glass terminal** (p 0.75). `background_opacity 0.85`, blur, tint. Rejected on a
  fact rather than taste: transparency under WSLg depends on the Weston RAIL
  compositor honouring alpha, that was never eyeballed here, and the failure mode is
  a solid black window rather than an error.
- **Kanagawa instrument panel** (p 0.25). PICKED. Scrollbar, progress bar and split
  title bars styled in the existing accents, cursor trail tuned tight, and a per-lane
  watermark generated from the charter letters.
- **Sumi-e ink wash** (p 0.12). A low-alpha ink render as `background_image` with
  `background_tint 0.9` and `transparent_background_colors`. Rejected: it is the most
  distinctive candidate and it carries no information, so every pixel it costs is
  decoration. It also inherits the same unverified-alpha problem as glass.
- **Zero chrome** (p 0.20). No title bar, no scrollbar, no tabs, larger font.
  Rejected: it is a coherent position and it deletes the progress and depth signals
  that a long agent run actually needs.

The rule the pick follows, and the one worth carrying forward: chrome that carries
information is kept, chrome that only decorates is not. The scrollbar says how deep
the buffer is during a run, the progress bar reads OSC 9;4, the split title bars
appear only once a tab is split, and the watermark says which lane the window is.
The cursor trail is the single exception, kept because it is the one effect no web UI
ships by default and the operator asked for exactly that.

Evidence, since a visual claim with no oracle is a preference: 14 asserted option
values parse to the intended values with zero mismatches under 0.48.2, the four lane
PNGs decode to exactly their expected glyph pixel counts, `kitten icat
--detect-support` returns 0 under WSLg so in-terminal images work, and a deliberately
wrong `--logo` path raises `FileNotFoundError` out of `kitty/render_cache.py` while
the real path is silent, which proves the watermark is rasterised rather than merely
parsed. What is NOT verified is whether it looks good; that needs the operator's eyes.

## 2026-08-05: how the six governance domains reach the satellite repos

Five candidates, ordered weird-first. Picked #5 at p_conventional 0.12: **claude-setup
runs one nightly sweep that gates all three repos with `gate.py --project`, and the
satellites publish evidence rather than executing anything.**

Losers and why: copying the six rows into each contract (0.85) is the default and was
forbidden; a git submodule of `tools/` (0.55) ships the whole tree and is the thing people
forget to update; a contract `extends:` a pinned git ref (0.35) is the tidy answer and
needs new resolution code in gate.py; an installable `claude-harness` package (0.22) is
the right long-term shape and turns a stale copy into a visible version number.

The reason the tail candidate won is a measurement, not taste. Both satellites have **zero**
rows in `state/gate-runs.jsonl`. Every other candidate assumes the satellite runs its own
gate, and neither ever has. The inherited constraint being killed is that a gate must run
inside the repo it gates; `gate.py` already takes `--project`, and ddl already reaches
across repos, badly, into a stale clone.

Transferable rule: when a mechanism has never once executed, do not improve its inputs.
Move the execution somewhere that already runs.
- 2026-08-13 kitty window: all-four composition (glass 0.84 + centered 7%-alpha Clawd
  pixel watermark + Kanagawa wave-accents-boosted over dragon base + loud chrome: top
  slanted tabs always visible, gold active tab, 14px padding, gold active border).
  Operator picked all four directions and asked for OOD composition; rejected Tokyo
  Night / Rose Pine swap as the in-distribution mode. Lives as the marked override
  block at the end of ~/.config/kitty/kitty.conf; revert = delete block or restore
  kitty.conf.bak-2026-08-13-pre-glass.
