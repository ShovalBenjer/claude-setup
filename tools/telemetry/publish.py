#!/usr/bin/env python3
"""Push what one agent learned to a GitHub issue the other agents read.

THE SPLIT, and why it is two surfaces rather than one.

Telemetry is high volume and machine-read: 8822 events today, 7029 of them gate
runs. Comms is low volume and human-read: the bus holds 25 messages in ten days.
Putting both on the same surface guarantees the second is buried by the first, so
they get different homes:

  telemetry  ->  a committed JSONL stream. Cheap, greppable, diffable, no API
                 rate limit, and `git log` is already a time index. Not built
                 here; `collect.py --json` is its producer and the sync target
                 is an operator decision because it publishes data.
  comms      ->  GitHub issue comments. This file. Notification-bearing,
                 threaded, works on a phone, already has an identity model and
                 an audit trail. It is "Slack without Slack" in the literal
                 sense that the feature you want from Slack is the notification.

WHY DERIVED RATHER THAN COMPOSED. `bus.py` has worked since 2026-07-25 and is read
automatically from two hooks. It holds 25 messages and none since 07-30. Reading
was never the problem; SENDING is voluntary, and this repository's lessons ledger
is a list of voluntary steps that stopped happening. So nothing here asks an agent
to write a message. Every line posted is derived from a ledger row a hook already
wrote, which means the failure mode is inverted: instead of an agent forgetting to
report, an agent would have to actively suppress a report.

NOTHING IS POSTED WITHOUT AN EXPLICIT FLAG AND AN EXPLICIT ISSUE NUMBER. Dry run
is the default and `--post` alone is not enough; `--issue N` must name a target
that already exists. This file never creates an issue and never opens a repo,
because publishing is outward-facing and that is the operator's call, not an
agent's. The cursor is written only on a real post, so a dry run can be repeated
without consuming anything.

    python tools/telemetry/publish.py --since 24h                 # dry run, the default
    python tools/telemetry/publish.py --since 24h --post --issue 36
    python tools/telemetry/publish.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import sinks  # noqa: E402

STATE = Path(__file__).resolve().parents[2] / "state"
CURSOR = STATE / "telemetry-published.txt"
FEED_CONFIG = STATE / "agent-feed.json"
MAX_LINES = 25


def cursor_path(sink_name: str) -> Path:
    """One cursor per surface.

    The extractor fix on 2026-08-05 changed `subject` and `ref` for every lessons and
    claims row, so their fingerprints changed with them. A single shared cursor would
    make the first discussion post repost up to 25 already-published items into a brand
    new surface, which is the worst possible first impression for a feed whose whole
    problem is that nobody reads it.

    Per-surface also makes the throttle per-surface, which is correct:
    minutes_since_last_post reads this file's own mtime, and a post to the discussion
    should not be suppressed because the issue was written to ten minutes ago.
    """
    return CURSOR if sink_name == "issue" else STATE / "telemetry-published-{}.txt".format(sink_name)


def fingerprint(ev: dict) -> str:
    """Stable id for an event, so the same finding is never posted twice.

    Deliberately excludes the timestamp. A refutation re-run at 14:00 and again at
    18:00 is the same fact about the same claim, and posting it twice teaches the
    reader to skim the feed, which is the exact failure that killed the bus.
    """
    key = "|".join(str(ev.get(k, "")) for k in ("repo", "source", "kind", "subject", "ref"))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def minutes_since_last_post(cursor: Path | None = None) -> float:
    """Age of the last successful post, in minutes.

    Read from the cursor file's mtime rather than a new timestamp field, because
    the cursor is written only on a successful post and its mtime therefore
    already IS the answer. A second source of truth for the same fact is a second
    thing that can disagree.

    Returns a large number when nothing has ever been posted, so a first run is
    never throttled.
    """
    cursor = cursor or CURSOR
    if not cursor.exists():
        return float("inf")
    return (time.time() - cursor.stat().st_mtime) / 60.0


def read_cursor(cursor: Path | None = None) -> set[str]:
    cursor = cursor or CURSOR
    if not cursor.exists():
        return set()
    return {l.strip() for l in cursor.read_text(encoding="utf-8").splitlines() if l.strip()}


def write_cursor(ids: set[str], cursor: Path | None = None) -> None:
    cursor = cursor or CURSOR
    cursor.parent.mkdir(parents=True, exist_ok=True)
    with cursor.open("a", encoding="utf-8") as fh:
        for i in sorted(ids):
            fh.write(i + "\n")


def select(events: list[dict], seen: set[str]) -> list[dict]:
    """Alerts and notes that have not been published, newest first, capped.

    The cap is not cosmetic. An uncapped first run would post 8822 lines into an
    issue and the surface would be abandoned on day one. What is dropped is
    reported by the caller rather than silently truncated.
    """
    fresh = [e for e in events
             if e["severity"] in (collect.ALERT, collect.NOTE)
             and fingerprint(e) not in seen]
    fresh.sort(key=lambda e: e["ts"] or "", reverse=True)
    return fresh


def render(events: list[dict], dropped: int) -> str:
    if not events:
        return ""
    lines = ["**agent feed**, {} item(s) since the last post".format(len(events)), ""]
    for e in events:
        lines.append("- `{}` **{}** {} `{}` {}".format(
            (e["ts"] or "")[:16], e["severity"], e["repo"] or "?", e["source"], e["subject"]))
    if dropped:
        lines += ["", "_{} further item(s) not shown; the cap is {} per post._".format(dropped, MAX_LINES)]
    lines += ["", "_Derived from state ledgers by `tools/telemetry/publish.py`. "
                  "No agent composed this._"]
    return "\n".join(lines)


def bootstrap(owner: str, repo: str, title: str) -> int:
    """Create the one long-lived discussion and record its ids. Never posts a digest.

    Separate verb on purpose. Creating a surface is outward-facing and happens once;
    folding it into the posting path would mean a timer could create a discussion, and
    a timer that can create things is a timer that eventually creates 48 of them.
    """
    rc, doc = sinks.graphql(
        "query($o:String!,$n:String!){repository(owner:$o,name:$n){id hasDiscussionsEnabled}}",
        {"o": owner, "n": repo})
    node = ((doc.get("data") or {}).get("repository") or {}) if rc == 0 else {}
    if rc != 0 or not node.get("id"):
        print("could not read the repository: {}".format(doc), file=sys.stderr)
        return 1
    if not node.get("hasDiscussionsEnabled"):
        print("Discussions is not enabled on {}/{}. Enable it first:\n"
              "  gh api graphql -f query='mutation($rid:ID!){{updateRepository("
              "input:{{repositoryId:$rid, hasDiscussionsEnabled:true}}){{repository{{"
              "hasDiscussionsEnabled}}}}}}' -F rid={}".format(owner, repo, node["id"]),
              file=sys.stderr)
        return 1
    category = sinks.resolve_category(owner, repo)
    if not category:
        print("no open-ended discussion category exists. Categories are UI-only: GitHub "
              "publishes no createDiscussionCategory mutation. Create one named "
              "`agent-feed` in the repo's Discussions tab, then re-run.", file=sys.stderr)
        return 1
    body = ("Machine-written feed. Every comment below is **derived** from an append-only "
            "ledger under `state/`, not composed by an agent.\n\n"
            "Moved here from issue #38 on 2026-08-05. That surface took 12 comments and "
            "146 item lines in 19 hours and received zero reactions and zero replies, "
            "which is the condition its own body named as failure.\n\n"
            "Producer: `tools/telemetry/publish.py --sink discussion`. Dedupe is by a "
            "timestamp-independent fingerprint, so the same fact never posts twice.\n\n"
            "If this discussion also goes unread, the answer is to post less, not more. "
            "Recheck 2026-08-19 per `docs/prior-art/tools-telemetry.json`.")
    rc, disc = sinks.create_discussion(node["id"], category["id"],
                                       "Agent feed: derived cross-repo telemetry", body)
    if rc != 0 or not disc.get("id"):
        print("createDiscussion failed: {}".format(disc), file=sys.stderr)
        return 1
    FEED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    FEED_CONFIG.write_text(json.dumps({
        "_note": "Ids resolved once and recorded. A node id is stable and a per-post "
                 "lookup would be a network call on the throttle path.",
        "repository_id": node["id"], "category_id": category["id"],
        "category_name": category["name"], "discussion_id": disc["id"],
        "discussion_number": disc.get("number"), "discussion_url": disc.get("url"),
        "created": "2026-08-05",
        "superseded_surface": "issue 38, 12 comments, 0 reactions, 0 replies",
    }, indent=2) + "\n", encoding="utf-8")
    print("created {}\nrecorded {}\nNOTHING was posted: seed the cursor next, with\n"
          "  publish.py --sink discussion --discussion-id {} --seed-cursor-from {}"
          .format(disc.get("url"), FEED_CONFIG, disc["id"], CURSOR))
    return 0


def load_feed_config() -> dict:
    try:
        return json.loads(FEED_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def selftest() -> int:
    failures = []

    a = {"repo": "x", "source": "gate-runs", "kind": "gate", "subject": "s", "ref": "r", "ts": "2026-01-01"}
    b = dict(a, ts="2026-06-06")
    if fingerprint(a) != fingerprint(b):
        failures.append("the same fact at two times fingerprints differently, so it will repost")
    if fingerprint(a) == fingerprint(dict(a, subject="other")):
        failures.append("two different facts share a fingerprint, so one will be swallowed")

    evs = [collect.event(severity=collect.ALERT, subject="a", ts="2026-08-01"),
           collect.event(severity=collect.TRACE, subject="b", ts="2026-08-02"),
           collect.event(severity=collect.NOTE, subject="c", ts="2026-08-03")]
    got = select(evs, set())
    if any(e["severity"] == collect.TRACE for e in got):
        failures.append("trace-level volume reached the feed")
    if [e["subject"] for e in got] != ["c", "a"]:
        failures.append("selection is not newest-first")
    if select(evs, {fingerprint(e) for e in evs}):
        failures.append("an already-published event was selected again")

    body = render(got, dropped=7)
    if "7 further item(s)" not in body:
        failures.append("a truncated post does not say how much it dropped")
    if not render([], 0) == "":
        failures.append("an empty selection still renders a body, so it would post nothing loudly")

    if minutes_since_last_post() < 0:
        failures.append("the post age went negative, so the throttle would never engage")

    # THE SAFETY PROPERTIES, read from this file's own AST rather than from a substring
    # search over its own text.
    #
    # The substring form was self-satisfying and had been since the file was written. It
    # asked whether "args.post and args.issue" appeared anywhere in the source, and the
    # assertion LINE contains that literal, so the check passed by finding itself. It
    # would have stayed green with the real gate deleted, which is the precise failure
    # this repository writes mutation specs to catch. Found 2026-08-05 while moving the
    # publishing surface, when the gate changed and the check did not notice.
    #
    # Walking main()'s body instead means the assertion cannot see itself: selftest() is
    # a different function node.
    import ast  # noqa: PLC0415

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    main_fn = next((n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if main_fn is None:
        failures.append("main() was not found, so no safety property could be checked")
    else:
        gates = [ast.unparse(n.test) for n in ast.walk(main_fn) if isinstance(n, ast.If)]
        posting = [g for g in gates if "args.post" in g]
        if not posting:
            failures.append("nothing in main() gates on --post, so a run could post "
                            "without being asked to")
        elif not any("sink" in g for g in posting):
            failures.append("the post path is gated on --post alone; it must also "
                            "require a resolved sink, or a missing target posts nowhere "
                            "while reporting success")
        body_src = ast.unparse(main_fn)
        if body_src.index("args.throttle") > body_src.index("collect.collect"):
            failures.append("the throttle does not run before the collect, so it pays "
                            "the ledger walk it was meant to avoid")

    # No local post path may exist beside the sinks, or a future edit can bypass the
    # sink contract without changing any gate.
    if any(isinstance(n, ast.FunctionDef) and n.name == "post" for n in tree.body):
        failures.append("publish.py defines its own post(), so a caller can bypass the "
                        "sink and the surface choice stops being explicit")

    # Per-surface cursors, asserted directly. One shared cursor would make the first
    # discussion post repost up to 25 already-published items, and would make the
    # throttle global so a post to one surface suppresses the other.
    if cursor_path("issue") == cursor_path("discussion"):
        failures.append("every sink shares one cursor, so a surface change reposts "
                        "already-published items and the throttle stops being per-surface")
    if cursor_path("issue") != CURSOR:
        failures.append("the issue cursor moved, so the existing surface loses its memory "
                        "and reposts its whole history once")

    # STRUCTURAL, in the shape bus.py uses for its lock: assert where a statement SITS,
    # not what a string says. These two paths cannot be exercised without posting or
    # seeding for real, and a test that did either would defeat the property it verifies.
    if main_fn is not None:
        def _direct_calls(stmts) -> set[str]:
            """Names called by a DIRECT child statement, not by a nested block.

            Walking the whole subtree would report the outer `if args.post ...` and the
            seed branch as containers of write_cursor, which they are, and neither is
            the guard being asserted. Only the innermost block matters.
            """
            names = set()
            for st in stmts:
                for n in ast.walk(st) if not isinstance(st, (ast.If, ast.For, ast.While)) else []:
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                        names.add(n.func.id)
            return names

        # POSITIVE form. Asserting "no bad if exists" flags every legitimate enclosing
        # block; asserting "the good one exists" does not, and it is what the mutation
        # removes.
        guarded = [n for n in ast.walk(main_fn)
                   if isinstance(n, ast.If)
                   and "write_cursor" in _direct_calls(n.body)
                   and "rc" in ast.unparse(n.test)]
        if not guarded:
            failures.append("no write_cursor call sits directly inside a test of the "
                            "post's return code, so a FAILED post can mark its items "
                            "published and they are lost rather than retried")

        seed = [n for n in ast.walk(main_fn)
                if isinstance(n, ast.If) and "seed_cursor_from" in ast.unparse(n.test)]
        if not seed:
            failures.append("the seed-cursor branch was not found")
        elif not any(isinstance(b, ast.Return) for b in seed[0].body):
            failures.append("the seed-cursor branch does not return, so seeding falls "
                            "through into a post, which is the one thing it exists to avoid")

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    the same fact at two times fingerprints identically")
    print("  ok    two different facts do not collide")
    print("  ok    trace volume never reaches the feed")
    print("  ok    selection is newest-first and skips what was published")
    print("  ok    a capped post states what it dropped")
    print("  ok    an empty selection renders nothing")
    print("  ok    the throttle is evaluated before the ledger walk, not after")
    print("  ok    posting requires --post AND a resolved sink, read from main's AST")
    print("  ok    publish.py defines no post() of its own, so no path bypasses a sink")
    print("  ok    each surface keeps its own cursor and the issue cursor is unmoved")
    print("  ok    write_cursor sits inside a return-code test, so a failed post is retried")
    print("  ok    the seed-cursor branch returns rather than falling through to a post")
    print("VERDICT: the feed derives its content and cannot post by accident")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="publish.py", description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="24h")
    ap.add_argument("--sink", choices=["issue", "discussion"], default="issue",
                    help="where to post. Default issue, so an un-redeployed systemd "
                         "unit keeps working rather than silently doing nothing")
    ap.add_argument("--issue", type=int, help="an EXISTING issue number to comment on")
    ap.add_argument("--discussion-id", help="the D_kw... node id, not the number")
    ap.add_argument("--post", action="store_true", help="actually post")
    ap.add_argument("--throttle", type=float, default=0.0,
                    help="minutes; skip entirely if a post happened more recently than this")
    ap.add_argument("--bootstrap", action="store_true",
                    help="create the long-lived discussion, record its ids, post nothing")
    ap.add_argument("--seed-cursor-from", metavar="PATH",
                    help="copy an existing cursor into this sink's cursor and exit; "
                         "writes no post")
    ap.add_argument("--repo", default="ShovalBenjer/claude-setup")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.bootstrap:
        owner, _, name = args.repo.partition("/")
        return bootstrap(owner, name, "Agent feed: derived cross-repo telemetry")

    # A discussion id may come from the flag or from the recorded config, so the timer
    # does not have to carry a node id in its ExecStart line.
    discussion_id = args.discussion_id or load_feed_config().get("discussion_id")
    cursor = cursor_path(args.sink)

    if args.seed_cursor_from:
        src = Path(args.seed_cursor_from)
        if not src.exists():
            print("no cursor at {}".format(src), file=sys.stderr)
            return 1
        already = read_cursor(cursor)
        incoming = {l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()}
        write_cursor(incoming - already, cursor)
        print("seeded {} with {} fingerprint(s) from {} ({} were already there). "
              "NOTHING was posted.".format(cursor.name, len(incoming - already), src.name,
                                           len(already & incoming)))
        return 0

    try:
        sink = sinks.sink_from_config(args.sink, args.issue, discussion_id)
    except ValueError as exc:
        # Refuse rather than fall back. A publish that silently posts to the surface
        # being retired is worse than one that does nothing and says why.
        print("no sink resolved: {}".format(exc), file=sys.stderr)
        return 2

    # Throttle before collecting, not after. Collecting walks ten ledgers across
    # every repo, and a timer firing every 30 minutes should not pay that cost to
    # then discover it had nothing to do.
    if args.throttle:
        age = minutes_since_last_post(cursor)
        if age < args.throttle:
            print("throttled: last post to {} was {:.1f} min ago, floor is {:.0f}".format(
                sink.describe(), age, args.throttle))
            return 0

    events, _ = collect.collect(collect.parse_since(args.since))
    seen = read_cursor(cursor)
    fresh = select(events, seen)
    shown, dropped = fresh[:MAX_LINES], max(0, len(fresh) - MAX_LINES)
    body = render(shown, dropped)

    if not body:
        print("nothing new to publish since the last post ({} event(s) in window, {} "
              "already sent to {})".format(len(events), len(seen), sink.describe()))
        return 0

    if args.post and sink is not None:
        rc, out = sink.post(body)
        if rc == 0:
            write_cursor({fingerprint(e) for e in shown}, cursor)
            print("posted {} item(s) to {}\n{}".format(len(shown), sink.describe(), out))
        else:
            print("post FAILED rc={} (cursor not advanced)\n{}".format(rc, out), file=sys.stderr)
        return rc

    print("== DRY RUN ==  nothing was posted and the cursor was not advanced")
    print("   target would have been {}".format(sink.describe()))
    print()
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
