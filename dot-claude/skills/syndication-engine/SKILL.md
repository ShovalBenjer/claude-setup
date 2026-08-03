---
name: syndication-engine
description: Project one canonical post onto many platforms by selecting semantically-tagged spans, with per-platform hook strategy and A/B variants. Use to draft or publish a POSSE syndication of a blog post across dev.to, X, Bluesky, Medium, Reddit, LinkedIn, GitHub. Never auto-publishes anything live.
disable-model-invocation: true
---

# syndication-engine

Turns one canonical article into platform-appropriate posts by **selecting
spans**, not by rewriting prose. POSSE: the canonical URL is always the original,
every copy links back to it.

## Why a projector and not seven drafts

Seven hand-maintained variants drift the moment the article changes, and a
per-platform string table is the same drift in different clothing. Here the
article is annotated once into semantic spans (`hook`, `claim`, `number`,
`reversal`, `failure`, `method`, `artifact`, `punchline`, `cta`). Each platform
declares a shape; a platform-agnostic projector fills that shape from the spans.
Adding a surface is a dict in `platforms.py`, never a change to the projector.

## Files

- `spans.py` — the article as tagged spans. The single source of truth for
  content. Hooks carry an `angle` so the A/B layer has real alternatives.
- `platforms.py` — per-platform budget, thread/single, markdown, **hook angle**,
  span order, and a human note. Declarative.
- `project.py` — the projector and the A/B variant generator.
- `syndicate.py` — CLI.

## Commands

```bash
python syndicate.py render [platform ...] --ab 3   # drafts, N distinct-angle variants
python syndicate.py check                          # every variant vs its budget
python syndicate.py plan                           # publish order and gates
python syndicate.py publish <platform>             # DRY-RUN; --go gated, dev.to only
```

## Hook strategy is per platform, on purpose

The same opener everywhere is the tell that a bot posted it. Each platform names
the hook **angle** it rewards and the projector leads with a hook of that angle:

- **X** — cold number, subject withheld to buy the second post
- **Bluesky** — wry, conversational
- **dev.to** — problem statement
- **Medium** — in-media-res, on the wrong answer
- **Reddit** — **no hook at all**; any hook reads as self-promotion and gets removed
- **GitHub / LinkedIn** — what-it-is and methodology respectively

`--ab N` returns the platform's lead-angle variant plus alternatives from
*different* angles, so a test compares cold-number vs wry vs in-media-res rather
than paraphrases of one angle. The body is held constant across a platform's
variants, so the test isolates the hook.

## Publishing: gated, and mostly manual by necessity

`publish` is dry-run by default. Even with `--go`, only **dev.to** has a wired
path, because it is the only surface with a working write API. It posts a
**draft** (`published:false`) with `canonical_url` set to the original; a human
flips it live in the dev.to dashboard. The engine places a correct draft, it
does not publish unattended.

Everything else is manual by platform reality, not by omission:

- **Medium**: writer API retired. Use the import tool; it preserves canonical.
- **X**: free tier is write-limited. Post the generated thread by hand.
- **Reddit**: rule-gated per subreddit; post last, only after dev.to lands.

**Credentials** (`DEVTO_API_KEY`, `BLUESKY_*`) are read from the environment by
the poster only, never by the projector, and never printed. This skill does not
read `.env`.

## Order

1. dev.to (API, canonical, produces the citable link)
2. GitHub README (under our control; interim link already live)
3. Bluesky
4. X (manual)
5. Medium (import, manual)
6. Reddit (last, only if dev.to landed)

## Before publishing anything

- `check` must show all variants within budget.
- Run the drafts through `voice-metrics` prose-tell gate. The spans are authored
  against the article, so they pass at zero fails; a hand-edit could reintroduce
  a tell.
- The canonical article must be live and correct first: syndication points at
  it. Re-run `case-ledger-post/shots.py` on the article if it changed.
- Update `spans.py` when the article changes. The drafts are only as current as
  the last annotation.
- A dry-run draft is not consent to post. Publishing is per-surface and needs
  the operator.
