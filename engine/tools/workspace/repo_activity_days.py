"""Separate development from a one-day sweep.

Counting human commits was not enough: on 2026-07-23 the operator swept most of
the estate himself, so 16 repositories show 2 to 5 human commits all landing on
that single day. Volume alone therefore reports 22 live repositories and 0
dormant, which is the same non-answer pushedAt gave.

The discriminator is DISTINCT COMMIT DAYS. Work spread over several days is
development. Everything landing in one day is housekeeping, whoever authored it.

  ACTIVE    human commits on 2 or more distinct days in 2026
  SWEPT     all 2026 human commits on a single day
  QUIET     no human commits in 2026 at all
"""
from __future__ import annotations

import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OWNER = "ShovalBenjer"
SINCE = "2026-01-01T00:00:00Z"
BOTS = ("dependabot", "claude", "kilo-code", "github-actions", "actions-user", "web-flow")


def gh(*a: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip()


def is_bot(login: str) -> bool:
    lo = (login or "").lower()
    return any(b in lo for b in BOTS) or lo.endswith("[bot]")


def main() -> int:
    rc, out = gh("repo", "list", "--limit", "100", "--json",
                 "name,isArchived,visibility")
    repos = [r for r in json.loads(out) if not r["isArchived"]]

    rows = []
    for r in repos:
        n = r["name"]
        rc, out = gh("api", f"repos/{OWNER}/{n}/commits?since={SINCE}&per_page=100",
                     "--jq", "[.[] | {a:(.author.login // .commit.author.name), d:.commit.author.date}]")
        try:
            cs = json.loads(out) if rc == 0 and out else []
        except json.JSONDecodeError:
            cs = []
        # This session's own API commits are excluded: they are not the operator
        # developing, they are tonight's cleanup.
        human = [c for c in cs if not is_bot(c["a"]) and not c["d"].startswith("2026-07-27")]
        days = sorted({c["d"][:10] for c in human})
        rows.append({"n": n, "v": r["visibility"][:7], "c": len(human),
                     "days": days, "nd": len(days)})

    active = [x for x in rows if x["nd"] >= 2]
    swept = [x for x in rows if x["nd"] == 1]
    quiet = [x for x in rows if x["nd"] == 0]

    print(f"ACTIVE  ({len(active)})  human commits on 2+ distinct days in 2026")
    for x in sorted(active, key=lambda z: (-z["nd"], -z["c"])):
        print(f"  {x['v']:<7} {x['n']:<34} {x['c']:>3} commits over {x['nd']:>2} days"
              f"   {x['days'][0]} .. {x['days'][-1]}")

    print(f"\nSWEPT   ({len(swept)})  every 2026 commit on ONE day: housekeeping, not development")
    for x in sorted(swept, key=lambda z: z["days"][0], reverse=True):
        print(f"  {x['v']:<7} {x['n']:<34} {x['c']:>3} commits, all on {x['days'][0]}")

    if quiet:
        print(f"\nQUIET   ({len(quiet)})  no human commit in 2026")
        for x in quiet:
            print(f"  {x['v']:<7} {x['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
