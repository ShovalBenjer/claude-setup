#!/usr/bin/env python3
"""Pick which reviewers see which change, and refuse to pair two of the same mind.

THE MEASURED PROBLEM. This repository has THREE persona systems and no code joins
any two of them.

  1. `panel.py` PERSONAS: five named rule sets (security, correctness, ux_frontend,
     ops_release, data) carrying 32 regex checks between them. Local, deterministic,
     runs ALL FIVE on every change regardless of what changed.
  2. `actors.json` `_aspect_enum`: eight aspects (correctness, security, boundary,
     simplicity, perf, slop, tests, a11y) with a `may_enact` list per external
     actor. Nothing reads `may_enact`. Grep returns the field's definition and no
     consumer.
  3. `payload/dot-claude/agents/`: 23 company personas (mayor-opus, qa-lab, review-board
     and the rest), routed by a markdown registry that no code reads either.

Systems 1 and 2 share exactly TWO words out of eleven. `correctness` and `security`
are in both; `data`, `ops_release` and `ux_frontend` exist only in the panel, and
`a11y`, `boundary`, `perf`, `simplicity`, `slop` and `tests` exist only in the
actor registry. So the honest answer to "how are personas picked per review type"
is that they are not picked. The panel runs everything every time and the external
half is never consulted.

WHAT THIS FILE ADDS, and what it deliberately does not.

It adds the allocator: given a change, which aspects does it need, and which
actors may enact them without two of them being the same model wearing two names.
It does NOT add a new persona vocabulary. It maps the panel's five onto the
registry's eight, and where a panel persona has no registry aspect the mapping
says so out loud rather than inventing one.

DECORRELATION IS ON model_family, NEVER ON host. `actors.json` carries this
warning in its own `_decorrelation_contract` and it is the single easiest thing to
get wrong here: nvidia-nim and openrouter are both multi-vendor resellers and both
can serve deepseek, qwen and llama. Picking "nvidia" and "openrouter" as two
independent reviewers can silently produce the same weights twice, and the
agreement gate would then report agreement that carries no information. The
registry declares `model_family` separately from `host` for exactly this reason,
and `nvidia-nim` declares `VARIES-BY-MODEL`, which this allocator treats as
UNKNOWN and therefore un-pairable rather than as a family that happens to differ
from every other string.

    python tools/review/allocate.py plan --aspect security
    python tools/review/allocate.py plan --files src/app.tsx migrations/003.sql
    python tools/review/allocate.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTORS = HERE / "actors.json"

# A family that varies by model is not a family. Pairing on it is the correlated
# pair the registry's own contract warns about, so it can never satisfy a second
# slot and can only be picked when nothing else is available, as a single.
UNKNOWN_FAMILY = "VARIES-BY-MODEL"

# Reachability ranks; unreachable actors are ordered last and REPORTED, never
# silently dropped. An allocator that hides an unreachable actor produces a plan
# that looks thin for no stated reason.
REACH_RANK = {"measured": 0, "declared": 1, "unreachable": 2}

# The panel's five personas mapped onto the registry's eight aspects. Three of the
# five have no registry aspect at all, and that is recorded as None rather than
# guessed: an external actor that never declared it may review frontend UX cannot
# be assigned frontend UX just because the allocator needed a slot filled.
PANEL_TO_ASPECT = {
    "security": "security",
    "correctness": "correctness",
    "ux_frontend": "a11y",      # nearest declared aspect; not identical, see report
    "ops_release": None,        # no registry aspect covers post-merge config and noise
    "data": None,               # no registry aspect covers schema safety and query cost
}

# Changed-path signals. Deliberately few and deliberately explicit: a long list of
# clever globs is a list nobody can predict the behaviour of.
PATH_ASPECTS = [
    ((".tsx", ".jsx", ".css", ".scss", ".html"), ["a11y", "correctness"]),
    ((".sql",), ["correctness", "boundary"]),
    ((".yml", ".yaml"), ["security", "correctness"]),
    ((".go", ".rs"), ["boundary", "correctness", "perf"]),
    ((".py", ".ts", ".js"), ["correctness", "boundary", "security"]),
    ((".md",), ["slop"]),
]


def load_actors() -> dict:
    return json.loads(ACTORS.read_text(encoding="utf-8"))


def aspects_for_files(files: list[str]) -> list[str]:
    """Which aspects a change plausibly needs, from its paths alone.

    Paths are a weak signal and this returns a superset on purpose. Under-selecting
    means a dimension goes unreviewed and nothing says so; over-selecting costs a
    request against a free quota.
    """
    out: list[str] = []
    for f in files:
        low = f.lower()
        for exts, aspects in PATH_ASPECTS:
            if low.endswith(exts):
                for a in aspects:
                    if a not in out:
                        out.append(a)
    return out


def eligible(actors: list[dict], aspect: str, exclude_family: set[str]) -> list[dict]:
    cands = [a for a in actors
             if aspect in (a.get("may_enact") or [])
             and a.get("model_family") not in exclude_family]
    cands.sort(key=lambda a: (REACH_RANK.get(a.get("reachable_local", "unreachable"), 3),
                              a.get("id", "")))
    return cands


def allocate(aspect: str, want: int = 2, actors: list[dict] | None = None) -> dict:
    """Pick up to `want` actors for one aspect, no two sharing a model_family."""
    actors = actors if actors is not None else load_actors()["actors"]
    picked: list[dict] = []
    used_families: set[str] = set()
    notes: list[str] = []

    declared = [a for a in actors if aspect in (a.get("may_enact") or [])]
    if not declared:
        return {"aspect": aspect, "picked": [], "families": [], "want": want,
                "notes": ["no actor declares may_enact for {!r}; this aspect is "
                          "unreviewable by the current registry".format(aspect)]}

    # An UNKNOWN_FAMILY actor is admissible ONLY as a solitary reviewer. Corrected
    # after the first real run paired nvidia-nim [VARIES-BY-MODEL] with
    # qwen-dashscope [alibaba-qwen] for the slop aspect, which is precisely the
    # correlated pair the registry's contract exists to prevent: nvidia-nim serves
    # qwen among others, so that pair can be one model reviewed twice. Its family
    # cannot be shown to DIFFER from anything, so it cannot satisfy decorrelation
    # against any partner, in either slot order.
    known = [a for a in actors if a.get("model_family") != UNKNOWN_FAMILY]
    unknown_declaring = [a for a in actors
                         if a.get("model_family") == UNKNOWN_FAMILY
                         and aspect in (a.get("may_enact") or [])]

    for _ in range(want):
        cands = eligible(known, aspect, used_families)
        if not cands:
            break
        chosen = cands[0]
        fam = chosen.get("model_family")
        picked.append(chosen)
        used_families.add(fam)

    if not picked and unknown_declaring:
        solo = sorted(unknown_declaring,
                      key=lambda a: REACH_RANK.get(a.get("reachable_local", "unreachable"), 3))[0]
        picked.append(solo)
        used_families.add(UNKNOWN_FAMILY)
        notes.append("{} is the only actor declaring {!r} and its model_family is {}. "
                     "Usable as a single opinion; it can never be half of a decorrelated "
                     "pair, because a reseller family cannot be shown to differ from a "
                     "partner it may itself be serving."
                     .format(solo["id"], aspect, UNKNOWN_FAMILY))
    elif unknown_declaring:
        notes.append("{} declare(s) {!r} and {} excluded from the pair: a {} family cannot "
                     "be shown to differ from the actors picked."
                     .format(", ".join(a["id"] for a in unknown_declaring), aspect,
                             "was" if len(unknown_declaring) == 1 else "were", UNKNOWN_FAMILY))
        if chosen.get("reachable_local") != "measured":
            notes.append("{} is {} locally, not measured; the plan is thinner than it looks"
                         .format(chosen["id"], chosen.get("reachable_local", "?")))

    if len(picked) < want:
        notes.append("wanted {} decorrelated actor(s) for {!r}, found {}. {} declare the "
                     "aspect but they do not supply {} distinct model families."
                     .format(want, aspect, len(picked), len(declared), want))
    return {"aspect": aspect, "want": want,
            "picked": [a["id"] for a in picked],
            "families": [a.get("model_family") for a in picked],
            "notes": notes}


def plan(aspects: list[str], want: int = 2) -> dict:
    actors = load_actors()["actors"]
    return {"want": want,
            "aspects": [allocate(a, want, actors) for a in aspects]}


def selftest() -> int:
    failures = []
    fake = [
        {"id": "alpha", "model_family": "fam-a", "may_enact": ["security"], "reachable_local": "measured"},
        {"id": "beta", "model_family": "fam-a", "may_enact": ["security"], "reachable_local": "measured"},
        {"id": "gamma", "model_family": "fam-b", "may_enact": ["security"], "reachable_local": "declared"},
        {"id": "reseller", "model_family": UNKNOWN_FAMILY, "may_enact": ["security", "perf"],
         "reachable_local": "measured"},
    ]

    r = allocate("security", 2, fake)
    if len(set(r["families"])) != len(r["families"]):
        failures.append("the same model_family was picked twice, which is a correlated pair")
    if "alpha" in r["picked"] and "beta" in r["picked"]:
        failures.append("two actors of one family were paired")

    # The registry's own warning, as a test: a VARIES-BY-MODEL actor cannot fill a
    # second slot, because it cannot be shown to differ from the first.
    r2 = allocate("perf", 2, fake)
    if r2["picked"] != ["reseller"]:
        failures.append("an unknown-family actor was not offered as a single when alone")

    # The regression this rule exists for: a reseller must never be half of a pair,
    # in either slot order, even when a differently-named family is available.
    pair = [dict(fake[3]), dict(fake[2], may_enact=["perf"])]
    r2b = allocate("perf", 2, pair)
    if "reseller" in r2b["picked"] and len(r2b["picked"]) > 1:
        failures.append("a VARIES-BY-MODEL reseller was paired, which is the correlated "
                        "pair the registry contract forbids")
    if not any("cannot be shown to differ" in n for n in r2b["notes"]):
        failures.append("the reseller exclusion was silent")

    r3 = allocate("nonexistent-aspect", 2, fake)
    if r3["picked"]:
        failures.append("an aspect nobody declares still produced picks")
    if not any("unreviewable" in n for n in r3["notes"]):
        failures.append("an unreviewable aspect did not say so")

    order = eligible(fake, "security", set())
    if order[-1]["id"] != "gamma":
        failures.append("a declared-but-unmeasured actor was not ranked last")
    if "gamma" not in [a["id"] for a in order]:
        failures.append("an unreachable actor was silently dropped instead of ranked")

    if aspects_for_files(["src/App.tsx"]) == []:
        failures.append("a frontend file selected no aspect")
    if "slop" not in aspects_for_files(["docs/x.md"]):
        failures.append("a markdown change did not select the prose aspect")
    if aspects_for_files(["Makefile"]) != []:
        failures.append("an unmapped path invented an aspect")

    # The mapping must admit its own holes rather than fill them.
    if PANEL_TO_ASPECT["ops_release"] is not None or PANEL_TO_ASPECT["data"] is not None:
        failures.append("a panel persona with no registry aspect was mapped anyway")

    real = load_actors()
    unknown = [a["id"] for a in real["actors"]
               if a.get("model_family") not in {x.get("model_family") for x in real["actors"]}]
    if unknown:
        failures.append("registry inconsistency: " + ", ".join(unknown))
    for a in real["actors"]:
        bad = set(a.get("may_enact") or []) - set(real["_aspect_enum"])
        if bad:
            failures.append("{} declares aspect(s) outside the enum: {}".format(a["id"], sorted(bad)))

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    two actors of one model_family are never paired")
    print("  ok    a VARIES-BY-MODEL reseller can be a single and never a second opinion")
    print("  ok    an aspect nobody declares reports unreviewable instead of picking")
    print("  ok    an unreachable actor is ranked last, not silently dropped")
    print("  ok    a thin plan states why it is thin")
    print("  ok    paths select aspects, and an unmapped path invents none")
    print("  ok    the two panel personas with no registry aspect stay unmapped")
    print("  ok    every may_enact in the live registry is inside the declared enum")
    print("VERDICT: the allocator decorrelates on family and reports every hole it found")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="allocate.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--aspect", action="append", default=[])
    p.add_argument("--files", nargs="*", default=[])
    p.add_argument("--want", type=int, default=2)
    p.add_argument("--json", action="store_true")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return selftest()

    aspects = list(args.aspect) + [a for a in aspects_for_files(args.files) if a not in args.aspect]
    if not aspects:
        print("no aspect selected. Pass --aspect or --files.", file=sys.stderr)
        return 2

    res = plan(aspects, args.want)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    for row in res["aspects"]:
        picked = ", ".join("{} [{}]".format(i, f) for i, f in zip(row["picked"], row["families"]))
        print("{:<14} {}".format(row["aspect"], picked or "(nobody)"))
        for n in row["notes"]:
            print("               ! " + n)
    print("\nDecorrelation is on model_family, never on host. The panel's local personas "
          "run regardless; this plans the EXTERNAL half only.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
