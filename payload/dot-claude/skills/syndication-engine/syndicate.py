"""syndication-engine CLI.

  syndicate render [platform ...]     project the article, print A/B variants
  syndicate check                     validate every variant against its budget
  syndicate plan                      the publish order and gates
  syndicate publish <platform>        DRY-RUN by default; real posting is gated

Nothing posts without --go, and even with --go the only wired path is dev.to
(the one platform with a working write API). Every other surface prints the
draft and the manual step, because their APIs are retired, write-limited, or
rule-gated. Credentials are read from the environment by the poster, never by
this module, and never printed.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from platforms import PLATFORMS  # noqa: E402
from project import project, render  # noqa: E402
from spans import ARTICLE, CANONICAL_URL  # noqa: E402

ORDER = ["devto", "github_readme", "bluesky", "x", "medium", "reddit", "linkedin"]


def cmd_render(a):
    names = a.platforms or ORDER
    for n in names:
        print(render(n, ab=a.ab))


def cmd_check(a):
    bad = 0
    for n in PLATFORMS:
        for v in project(n):
            status = "OVER" if v["over_budget"] else "ok"
            if v["over_budget"]:
                bad += 1
            print(f"{n:<14} {v['variant']} {v['hook_angle']:<14} "
                  f"{v['unit_count']} unit(s) longest {v['longest_unit']:>5}/"
                  f"{v['budget']:<6} {status}")
    print(f"\n{'all variants within budget' if not bad else str(bad)+' OVER budget'}")
    return 1 if bad else 0


def cmd_plan(a):
    print(f"canonical: {CANONICAL_URL}\n")
    print("publish order and gates:\n")
    steps = [
        ("devto", "First. Real Articles API, canonical_url support, produces "
                  "the citable link the rest reference.", "DEVTO_API_KEY"),
        ("github_readme", "Fully under our control. Already live as an interim; "
                          "the resume engine owns the full version.", None),
        ("bluesky", "After dev.to. atproto app-password auth.",
         "BLUESKY_HANDLE + BLUESKY_APP_PASSWORD"),
        ("x", "Manual. Free tier is write-limited; post the generated thread by "
              "hand.", None),
        ("medium", "Import tool, manual. Writer API retired; import preserves "
                   "canonical.", None),
        ("reddit", "Last, and only if dev.to landed. Read each subreddit's "
                   "self-promotion rule the same day.", None),
    ]
    for i, (p, why, cred) in enumerate(steps, 1):
        c = f"  needs: {cred}" if cred else "  no credential / manual"
        print(f"{i}. {p}\n   {why}\n {c}\n")


def cmd_publish(a):
    p = a.platform
    if p not in PLATFORMS:
        sys.exit(f"unknown platform {p!r}")
    variants = project(p)
    print(render(p))
    if not a.go:
        print("DRY RUN. Nothing sent. Re-run with --go to attempt a real post "
              "(only dev.to is wired; others remain manual).")
        return
    if p != "devto":
        sys.exit(f"{p} has no automated path (API retired / write-limited / "
                 f"rule-gated). Post the draft above by hand.")
    _publish_devto(variants, dry=False)


def _publish_devto(variants, dry):
    """Post to dev.to as a DRAFT (published:false) via the Articles API.

    Reads DEVTO_API_KEY from the environment. Never prints it. Posts a draft,
    not a live article, so a human still flips it live in the dev.to UI: the
    engine's job is to place a correct, canonical-tagged draft, not to publish
    unattended.
    """
    key = os.environ.get("DEVTO_API_KEY")
    if not key:
        sys.exit("DEVTO_API_KEY not in environment; not attempting a post.")
    try:
        import urllib.request
        import json
    except Exception as e:
        sys.exit(f"stdlib import failed: {e}")

    v = variants[0]
    body = "\n\n".join(v["units"])
    payload = {
        "article": {
            "title": "It started as \"help me reply to my messages\" and ended "
                     "ten hours later in a decryption",
            "published": False,                 # draft, never auto-live
            "canonical_url": CANONICAL_URL,     # credit the original
            "tags": ["ai", "agents", "security", "postmortem"],
            "body_markdown": body,
        }
    }
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    print(f"dev.to draft created: {resp.get('url', '(no url returned)')}")
    print("It is a DRAFT. Review it in the dev.to dashboard and publish there.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render"); r.add_argument("platforms", nargs="*")
    r.add_argument("--ab", type=int, default=1,
                   help="number of distinct-angle hook variants to A/B (default 1)")
    r.set_defaults(fn=cmd_render)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    pub = sub.add_parser("publish"); pub.add_argument("platform")
    pub.add_argument("--go", action="store_true")
    pub.set_defaults(fn=cmd_publish)

    a = p.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
