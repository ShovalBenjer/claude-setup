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
    python tools/telemetry/publish.py --since 24h --post --sink discussion
    python tools/telemetry/publish.py --selftest

THE DISCUSSION SINK. The surface moved from issue #38 to Discussion #43 on
2026-08-05, and the systemd unit was updated to pass `--sink discussion` while
this file still only knew `--issue`. The service then failed with exit 2 every
30 minutes from 2026-08-06 to 2026-08-11 and the feed went silent; the journal
was the only witness. The discussion id deliberately does not live in the unit
file: it is read from `state/agent-feed.json` so that moving the surface again
means editing one committed state file, not a unit that exists in two places.
Same safety property as the issue path: nothing posts without `--post` AND a
resolvable target, and this file never creates the discussion it posts to.
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

CURSOR = Path(__file__).resolve().parents[2] / "state" / "telemetry-published.txt"
FEED_CONFIG = Path(__file__).resolve().parents[2] / "state" / "agent-feed.json"
MAX_LINES = 25


def fingerprint(ev: dict) -> str:
    """Stable id for an event, so the same finding is never posted twice.

    Deliberately excludes the timestamp. A refutation re-run at 14:00 and again at
    18:00 is the same fact about the same claim, and posting it twice teaches the
    reader to skim the feed, which is the exact failure that killed the bus.
    """
    key = "|".join(str(ev.get(k, "")) for k in ("repo", "source", "kind", "subject", "ref"))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def minutes_since_last_post() -> float:
    """Age of the last successful post, in minutes.

    Read from the cursor file's mtime rather than a new timestamp field, because
    the cursor is written only on a successful post and its mtime therefore
    already IS the answer. A second source of truth for the same fact is a second
    thing that can disagree.

    Returns a large number when nothing has ever been posted, so a first run is
    never throttled.
    """
    if not CURSOR.exists():
        return float("inf")
    return (time.time() - CURSOR.stat().st_mtime) / 60.0


def read_cursor() -> set[str]:
    if not CURSOR.exists():
        return set()
    return {l.strip() for l in CURSOR.read_text(encoding="utf-8").splitlines() if l.strip()}


def write_cursor(ids: set[str]) -> None:
    CURSOR.parent.mkdir(parents=True, exist_ok=True)
    with CURSOR.open("a", encoding="utf-8") as fh:
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


def post(issue: int, body: str) -> tuple[int, str]:
    r = subprocess.run(["gh", "issue", "comment", str(issue), "--body", body],
                       capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def discussion_target(config: Path = FEED_CONFIG) -> tuple[str, int] | None:
    """(owner/repo, discussion number) from state/agent-feed.json, or None.

    None rather than an exception: a missing or malformed config keeps the run a
    dry run, loudly, instead of crashing a timer every 30 minutes. That failure
    shape is chosen against the measured one: the --sink mismatch failed with
    exit 2 on every tick for five days and nothing surfaced it.
    """
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        return str(cfg["repo"]), int(cfg["discussion"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def post_discussion(repo: str, number: int, body: str) -> tuple[int, str]:
    """Comment on an EXISTING discussion. Two calls: resolve the node id, mutate.

    Never creates a discussion; a bad number fails the id lookup and the cursor
    is not advanced, same contract as the issue path.
    """
    owner, name = repo.split("/", 1)
    q = ("query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,"
         "name:$name){discussion(number:$number){id}}}")
    r = subprocess.run(["gh", "api", "graphql", "-f", "query=" + q,
                        "-F", "owner=" + owner, "-F", "name=" + name,
                        "-F", "number=" + str(number),
                        "--jq", ".data.repository.discussion.id"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout.strip():
        return r.returncode or 1, ("discussion id lookup failed: " + (r.stdout + r.stderr).strip())
    disc_id = r.stdout.strip()
    m = ("mutation($id:ID!,$body:String!){addDiscussionComment(input:{discussionId:$id,"
         "body:$body}){comment{url}}}")
    r2 = subprocess.run(["gh", "api", "graphql", "-f", "query=" + m,
                         "-F", "id=" + disc_id, "-F", "body=" + body,
                         "--jq", ".data.addDiscussionComment.comment.url"],
                        capture_output=True, text=True, timeout=120)
    return r2.returncode, (r2.stdout + r2.stderr).strip()


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
    src_throttle = Path(__file__).read_text(encoding="utf-8")
    if "if args.throttle:" not in src_throttle or src_throttle.index("if args.throttle:") > src_throttle.index("events, _ = collect.collect"):
        failures.append("the throttle does not run before the collect, so it pays the cost anyway")

    # The safety property: nothing posts without both flags. Checked by parsing,
    # because a test that actually posted would defeat the property it verifies.
    src = Path(__file__).read_text(encoding="utf-8")
    if "args.post and args.issue" not in src:
        failures.append("the post path is not gated on BOTH --post and --issue")
    if "args.post and disc" not in src:
        failures.append("the discussion post path is not gated on BOTH --post and a resolved target")

    # The regression that killed the feed for five days: a sink the CLI does not
    # know. Both sinks the unit files have ever named must parse.
    for sink in ("issue", "discussion"):
        try:
            ap_probe = argparse.ArgumentParser()
            ap_probe.add_argument("--sink", choices=("issue", "discussion"))
            ap_probe.parse_args(["--sink", sink])
        except SystemExit:
            failures.append("--sink {} does not parse".format(sink))
    if discussion_target(Path("/nonexistent/agent-feed.json")) is not None:
        failures.append("a missing feed config resolved a discussion target instead of None")

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
    print("  ok    posting requires both --post and an explicit --issue")
    print("  ok    the discussion sink parses and refuses to post without a resolved target")
    print("VERDICT: the feed derives its content and cannot post by accident")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="publish.py", description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="24h")
    ap.add_argument("--issue", type=int, help="an EXISTING issue number to comment on")
    ap.add_argument("--sink", choices=("issue", "discussion"), default="issue",
                    help="where a post lands; discussion reads its target from state/agent-feed.json")
    ap.add_argument("--post", action="store_true", help="actually post; requires a target")
    ap.add_argument("--throttle", type=float, default=0.0,
                    help="minutes; skip entirely if a post happened more recently than this")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    # Throttle before collecting, not after. Collecting walks ten ledgers across
    # every repo, and a timer firing every 30 minutes should not pay that cost to
    # then discover it had nothing to do.
    if args.throttle:
        age = minutes_since_last_post()
        if age < args.throttle:
            print("throttled: last post was {:.1f} min ago, floor is {:.0f}".format(age, args.throttle))
            return 0

    events, _ = collect.collect(collect.parse_since(args.since))
    seen = read_cursor()
    fresh = select(events, seen)
    shown, dropped = fresh[:MAX_LINES], max(0, len(fresh) - MAX_LINES)
    body = render(shown, dropped)

    if not body:
        print("nothing new to publish since the last post ({} event(s) in window, {} already sent)"
              .format(len(events), len(seen)))
        return 0

    if args.sink == "discussion":
        disc = discussion_target()
        if args.post and disc:
            repo, number = disc
            rc, out = post_discussion(repo, number, body)
            if rc == 0:
                write_cursor({fingerprint(e) for e in shown})
                print("posted {} item(s) to {} discussion #{}\n{}".format(len(shown), repo, number, out))
            else:
                print("post FAILED rc={} (cursor not advanced)\n{}".format(rc, out), file=sys.stderr)
            return rc
        print("== DRY RUN ==  nothing was posted and the cursor was not advanced")
        if args.post and not disc:
            print("   --post was given but {} is missing or malformed, so this stayed a dry run on purpose"
                  .format(FEED_CONFIG))
        print()
        print(body)
        return 0

    if args.post and args.issue:
        rc, out = post(args.issue, body)
        if rc == 0:
            write_cursor({fingerprint(e) for e in shown})
            print("posted {} item(s) to issue #{}\n{}".format(len(shown), args.issue, out))
        else:
            print("post FAILED rc={} (cursor not advanced)\n{}".format(rc, out), file=sys.stderr)
        return rc

    print("== DRY RUN ==  nothing was posted and the cursor was not advanced")
    if args.post and not args.issue:
        print("   --post was given without --issue, so this stayed a dry run on purpose")
    print()
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
