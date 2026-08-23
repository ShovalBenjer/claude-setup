#!/usr/bin/env python3
"""The flâneur: assemble the office-gossip briefing that a session carries on its walk.

Coffee v2's carrier (taste row 2026-08-12). The flâneur is a persona that visits
live sessions and moves news between them; this tool builds what it carries, so the
walk costs one SendMessage per session instead of N-squared pairwise chats. It does
NOT call ListAgents or SendMessage itself (those are the calling session's tools):
it reads the durable ledgers and emits a compact briefing string plus the open
futures positions worth needling people about.

Composes breakroom (recent posts), futures (open bets + standings), and coffee
(recent gripes). Read-only over state/*.jsonl. If the flâneur is later run as a
standing headless persona, it calls this each lap.

Commands: brief, selftest.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breakroom as _br  # noqa: E402
import futures as _fut  # noqa: E402
import smoking as _smk  # noqa: E402


def brief(state_dir: Path, n: int = 6) -> str:
    lines = ["office gossip, freshest first:"]

    posts = _br.read_rows(state_dir / "breakroom.jsonl")[-n:]
    for p in reversed(posts):
        lines.append(f"  [{p['kind']}] {p['session']}: {p['text']}")

    frows = _fut.read_rows(state_dir / "futures.jsonl")
    settled = {r["id"] for r in frows if r["kind"] == "settle"}
    open_posts = [r for r in frows if r["kind"] == "post" and r["id"] not in settled]
    if open_posts:
        lines.append("open bets on the board:")
        for p in open_posts[-n:]:
            bets = sum(1 for r in frows if r["kind"] == "bet" and r["id"] == p["id"])
            lines.append(f"  {p['id']} {p['session']}: {p['claim']} ({bets} bet(s))")
    standings = _fut.standings(frows)
    if standings:
        top = sorted(standings.items(), key=lambda kv: -kv[1])
        lines.append("reputation: " + ", ".join(f"{s} {r}" for s, r in top[:5]))

    gripes = [r for r in _smk.read_rows(state_dir / "coffee.jsonl")
              if r["kind"] == "gripe"][-n:]
    for g in reversed(gripes):
        lines.append(f"  overheard: {g['session']} griping about {g.get('about') or '?'}")

    return "\n".join(lines)


def selftest() -> int:
    import tempfile
    fails = 0

    def check(name, ok):
        nonlocal fails
        if not ok:
            fails += 1
            print(f"FAIL {name}")

    with tempfile.TemporaryDirectory() as td:
        sd = Path(td)
        _br.append_row(sd / "breakroom.jsonl",
                       {"ts": "t", "session": "eng", "kind": "brag", "text": "shipped coffee"})
        _fut.append_row(sd / "futures.jsonl",
                        {"kind": "post", "id": "ab12cd34ef56", "ts": "t",
                         "session": "qa", "claim": "gate stays green",
                         "falsifier": "gate", "settle_by": "2026-08-20"})
        _smk.append_row(sd / "coffee.jsonl",
                        {"kind": "gripe", "ts": "t", "session": "eng",
                         "text": "runner flaked", "about": "actions"})
        b = brief(sd)
        check("mentions a brag", "shipped coffee" in b)
        check("mentions the open bet", "gate stays green" in b)
        check("mentions the gripe", "actions" in b)
        check("empty state does not crash", isinstance(brief(Path(td) / "nope"), str))
    print(f"flaneur selftest: {fails} checks failed")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", type=Path, default=Path("state"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    br = sub.add_parser("brief")
    br.add_argument("-n", type=int, default=6)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    print(brief(a.state, a.n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
