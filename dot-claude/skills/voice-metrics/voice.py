"""voice-metrics CLI.

  fit      measure profiles from the local corpus and write profiles.json
  check    score a draft file against a profile
  variants generate randomised burst groupings of a draft, ranked
  rules    print the asserted rules for a use case

Everything runs locally. The WhatsApp corpus is private message content and no
part of this sends it anywhere.
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from profiles import RULES, fit_profile, fit_run_profile, load, save  # noqa: E402
from voice_engine import IdiolectEmbedding, load_threads  # noqa: E402
from voice_score import render, score  # noqa: E402
from voice_variants import render_variants, variants  # noqa: E402

DEFAULT_DB = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp",
                          "wa-decrypted", "genericStorage.dec.db")


def resolve_chat(db, who):
    """chatId whose contact name matches `who`, busiest thread wins."""
    import sqlite3
    cpath = os.path.join(os.path.dirname(db), "contacts.dec.db")
    names = {}
    if os.path.exists(cpath):
        c = sqlite3.connect(f"file:{cpath}?mode=ro", uri=True)
        try:
            for cid, nm in c.execute(
                    "SELECT Id, COALESCE(ContactName,FirstName,PushName) FROM UserStatuses"):
                if nm:
                    names[cid] = nm
        except Exception:
            pass
        c.close()
    if "@" in who:
        return who
    hits = [cid for cid, nm in names.items() if who.lower() in nm.lower()]
    if not hits:
        raise SystemExit(f"no contact matching {who!r}")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    counts = [(cid, con.execute("SELECT COUNT(*) FROM message WHERE chatId=?",
                                (cid,)).fetchone()[0]) for cid in hits]
    con.close()
    counts.sort(key=lambda x: -x[1])
    if not counts or counts[0][1] == 0:
        raise SystemExit(f"contact {who!r} has no messages in this store")
    return counts[0][0]


def cmd_fit(a):
    threads = load_threads(a.db, min_msgs=a.min_msgs)
    if not threads:
        raise SystemExit("no threads met the minimum; lower --min-msgs")
    profiles = load()
    # one profile per named contact, plus a pooled all-chats baseline
    pooled = [t for msgs in threads.values() for _, t in msgs]
    profiles["whatsapp_pooled"] = fit_profile(pooled, "whatsapp_pooled",
                                              "thread-level, both sides, all direct chats")
    allmsgs = [m for msgs in threads.values() for m in msgs]
    profiles["whatsapp_pooled__runs"] = fit_run_profile(allmsgs, "whatsapp_pooled__runs")
    for who in (a.contact or []):
        cid = resolve_chat(a.db, who)
        msgs = threads.get(cid)
        if not msgs:
            print(f"  skip {who}: thread below --min-msgs")
            continue
        key = f"whatsapp_{who.lower()}"
        profiles[key] = fit_profile([t for _, t in msgs], key,
                                    "thread-level, both sides, one contact")
        profiles[key + "__runs"] = fit_run_profile(msgs, key + "__runs")
        print(f"  {key}: {len(msgs)} messages, "
              f"{profiles[key + '__runs']['n']} runs")
    path = save(profiles)
    print(f"wrote {path}")
    for k, p in profiles.items():
        m = p["metrics"]
        if k.endswith("__runs"):
            print(f"  {k:<34} n={p['n']:>6}  sends p50 {m['sends']['p50']:.0f} "
                  f"p95 {m['sends']['p95']:.0f}  len_cv p10 {m['len_cv']['p10']:.2f} "
                  f"p50 {m['len_cv']['p50']:.2f}")
        else:
            print(f"  {k:<34} n={p['n']:>6}  chars p50 {m['chars']['p50']:.0f} "
                  f"p95 {m['chars']['p95']:.0f}  lines p50 {m['lines']['p50']:.0f}")


def _corpus_for(profile_key, db, min_msgs):
    """Texts backing a profile, for the centrality check."""
    threads = load_threads(db, min_msgs=min_msgs)
    if profile_key == "whatsapp_pooled" or not profile_key.startswith("whatsapp_"):
        return [t for msgs in threads.values() for _, t in msgs]
    who = profile_key.split("_", 1)[1]
    cid = resolve_chat(db, who)
    return [t for _, t in threads.get(cid, [])]


def cmd_check(a):
    profiles = load()
    rules = RULES.get(a.rules or a.profile) or RULES["whatsapp_close"]
    prof = None if a.profile in ("none", None) else profiles.get(a.profile)
    if a.profile not in ("none", None) and prof is None:
        raise SystemExit(f"unknown profile {a.profile!r}; have {sorted(profiles)}\n"
                         f"use --profile none to run the asserted rules only")
    text = io.open(a.file, encoding="utf-8").read()
    emb, corpus = None, None
    if a.embed and prof is not None:
        corpus = _corpus_for(a.profile, a.db, a.min_msgs)
        emb = IdiolectEmbedding(seed=a.seed).fit(corpus)
    rep = score(text, prof, rules, corpus, emb)
    label = a.profile if prof is not None else f"rules-only ({a.rules or 'default'})"
    print(render(rep, f"{os.path.basename(a.file)} vs {label}"))
    if prof is None:
        print("  note: no measured profile for this surface; only the asserted "
              "rules ran (dashes, register markers, LLM tells).")
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep["ok"] else 1


def cmd_variants(a):
    profiles = load()
    if a.profile not in profiles:
        raise SystemExit(f"unknown profile {a.profile!r}; have {sorted(profiles)}")
    rules = RULES.get(a.rules or a.profile) or RULES["whatsapp_close"]
    lines = [l.rstrip() for l in io.open(a.file, encoding="utf-8").read().split("\n")
             if l.strip()]
    corpus = _corpus_for(a.profile, a.db, a.min_msgs)
    emb = IdiolectEmbedding(seed=a.seed).fit(corpus) if a.embed else None
    runs = profiles.get(a.profile + "__runs")
    vs = variants(lines, corpus, profiles[a.profile], rules, emb, n=a.n,
                  seed=a.seed, run_profile=runs)
    print(f"{len(lines)} lines, {len(vs)} distinct groupings, seed {a.seed}")
    print(render_variants(vs, top=a.top))


def cmd_rules(a):
    for k, v in RULES.items():
        if a.use_case and k != a.use_case:
            continue
        print(f"\n[{k}]  send_as={v['send_as']}  band=p{v['band'][0]}-p{v['band'][1]}")
        print(f"  gates:   {', '.join(v['gates'])}")
        if v["ceiling"]:
            print(f"  ceiling: {v['ceiling']}")
        for n in v["notes"]:
            print(f"  - {n}")


def main():
    p = argparse.ArgumentParser(prog="voice", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--min-msgs", type=int, default=120)
    p.add_argument("--seed", type=int, default=0)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fit", help="measure profiles from the corpus")
    f.add_argument("--contact", action="append", help="per-contact profile (repeatable)")
    f.set_defaults(fn=cmd_fit)

    c = sub.add_parser("check", help="score a draft")
    c.add_argument("file")
    c.add_argument("--profile", default="whatsapp_pooled")
    c.add_argument("--rules", help="rule set, defaults to the profile name")
    c.add_argument("--embed", action="store_true", help="run the centrality check")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)

    v = sub.add_parser("variants", help="randomised burst groupings, ranked")
    v.add_argument("file", help="one line per line to send")
    v.add_argument("--profile", default="whatsapp_pooled")
    v.add_argument("--rules")
    v.add_argument("--embed", action="store_true")
    v.add_argument("-n", type=int, default=24)
    v.add_argument("--top", type=int, default=3)
    v.set_defaults(fn=cmd_variants)

    r = sub.add_parser("rules", help="print asserted rules")
    r.add_argument("use_case", nargs="?")
    r.set_defaults(fn=cmd_rules)

    a = p.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
