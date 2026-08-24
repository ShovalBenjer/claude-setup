"""Which repositories is the operator actually developing?

`pushedAt` is the obvious signal and it is misleading here. A bulk operation on
2026-07-23 touched most of the estate, and several 2026-07-27 timestamps are this
session's own API commits (licences, a badge removal, a README repair). Sorting by
pushedAt reports 22 active repos and 0 archive candidates, which is no answer.

So this counts COMMITS IN 2026 and splits them by author:

  human        commits by a person
  bot          dependabot, claude, kilo-code, github-actions
  this-session commits authored today by the API work in this session

A repository is "live" when a human committed to it in 2026. Everything else is
finished, whatever its push date says.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OWNER = "ShovalBenjer"
SINCE = "2026-01-01T00:00:00Z"
TODAY = "2026-07-27"
BOTS = ("dependabot", "claude", "kilo-code", "github-actions", "actions-user",
        "gt/", "web-flow")


def gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip()


def is_bot(login: str) -> bool:
    lo = (login or "").lower()
    return any(b in lo for b in BOTS) or lo.endswith("[bot]")


def main() -> int:
    rc, out = gh("repo", "list", "--limit", "100", "--json",
                 "name,isArchived,visibility,pushedAt")
    repos = [r for r in json.loads(out) if not r["isArchived"]]
    print(f"unarchived repositories: {len(repos)}\n")

    rows = []
    for r in repos:
        name = r["name"]
        rc, out = gh("api", f"repos/{OWNER}/{name}/commits?since={SINCE}&per_page=100",
                     "--jq", "[.[] | {a:(.author.login // .commit.author.name), d:.commit.author.date}]")
        try:
            commits = json.loads(out) if rc == 0 and out else []
        except json.JSONDecodeError:
            commits = []
        human = [c for c in commits if not is_bot(c["a"]) and not c["d"].startswith(TODAY)]
        bot = [c for c in commits if is_bot(c["a"])]
        mine = [c for c in commits if c["d"].startswith(TODAY) and not is_bot(c["a"])]
        rows.append({
            "name": name, "vis": r["visibility"], "pushed": r["pushedAt"][:10],
            "human": len(human), "bot": len(bot), "session": len(mine),
            "last_human": max((c["d"][:10] for c in human), default="-"),
            "who": Counter(c["a"] for c in human).most_common(2),
        })

    live = [x for x in rows if x["human"] > 0]
    dormant = [x for x in rows if x["human"] == 0]

    print(f"LIVE: a human committed in 2026  ({len(live)})")
    for x in sorted(live, key=lambda z: z["last_human"], reverse=True):
        who = ", ".join(f"{n}:{c}" for n, c in x["who"])
        print(f"  {x['last_human']}  {x['vis'][:7]:<7} {x['name']:<34} "
              f"human={x['human']:<4} bot={x['bot']:<4} [{who}]")

    print(f"\nDORMANT: no human commit in 2026, push date is bots or this session  ({len(dormant)})")
    for x in sorted(dormant, key=lambda z: z["pushed"], reverse=True):
        print(f"  pushed {x['pushed']}  {x['vis'][:7]:<7} {x['name']:<34} "
              f"bot={x['bot']:<4} this-session={x['session']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
