#!/usr/bin/env python3
"""License gate for the research corpus (spec step 6, section 6 stage 1).

Mechanically enforces license verdicts before source ingestion. Refuses
blocked sources by canonical hostname, marks stale sources, and records
every admit/refuse decision. developer-roadmap is refused by a test,
not by a policy sentence.

Usage:
    python tools/corpus/license_gate.py check --uri URI --license SPDX [--verdict VERDICT]
    python tools/corpus/license_gate.py batch --manifest PATH [--db PATH]
    python tools/corpus/license_gate.py blocked
    python tools/corpus/license_gate.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    _sha256,
    connect,
    init_schema,
)

BLOCKED_HOSTNAMES = frozenset({
    "nilbuild/developer-roadmap",
    "kamranahmedse/developer-roadmap",
})

COPYLEFT_LICENSES = frozenset({
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "LGPL-2.1",
    "LGPL-3.0",
})

NONCOMMERCIAL_LICENSES = frozenset({
    "CC-BY-NC-4.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-4.0",
})

SHAREALIKE_LICENSES = frozenset({
    "CC-BY-SA-4.0",
    "CC-BY-SA-3.0",
})

STALE_MONTHS = 18


def _parse_utc(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _is_blocked(canonical_uri):
    uri_lower = canonical_uri.lower()
    for hostname in BLOCKED_HOSTNAMES:
        if hostname.lower() in uri_lower:
            return True
    return False


def _resolve_verdict(license_spdx, canonical_uri):
    if _is_blocked(canonical_uri):
        return "blocked", "hostname in BLOCKED_HOSTNAMES"

    if not license_spdx or license_spdx.upper() in ("NOASSERTION", "NONE", ""):
        return "blocked", "no license or NOASSERTION (must read actual LICENSE text)"

    upper = license_spdx.upper()
    if "ALL RIGHTS RESERVED" in upper:
        return "blocked", "all rights reserved"

    if license_spdx in NONCOMMERCIAL_LICENSES:
        return "link_only", f"{license_spdx} has NonCommercial clause"

    if license_spdx in COPYLEFT_LICENSES:
        return "link_only", f"{license_spdx} is copyleft"

    if license_spdx in SHAREALIKE_LICENSES:
        return "index_only", f"{license_spdx} has ShareAlike clause"

    return "vendor", f"{license_spdx} permits vendoring with attribution"


def _resolve_liveness(upstream_mtime, fetched_utc=None):
    mtime = _parse_utc(upstream_mtime)
    if mtime is None:
        return "live"

    now = _parse_utc(fetched_utc) if fetched_utc else datetime.datetime.utcnow()
    if now is None:
        now = datetime.datetime.utcnow()

    age_months = (now.year - mtime.year) * 12 + (now.month - mtime.month)
    if age_months > STALE_MONTHS:
        return "stale"
    return "live"


def check_source(canonical_uri, license_spdx, upstream_mtime=None,
                 fetched_utc=None, override_verdict=None):
    """Check a single source against the license gate.

    Returns a decision dict with verdict, liveness, reason, and admit flag.
    """
    if override_verdict:
        verdict = override_verdict
        reason = f"operator override to {override_verdict}"
    else:
        verdict, reason = _resolve_verdict(license_spdx, canonical_uri)

    liveness = _resolve_liveness(upstream_mtime, fetched_utc)

    admitted = verdict in ("vendor", "index_only")

    return {
        "canonical_uri": canonical_uri,
        "license_spdx": license_spdx,
        "verdict": verdict,
        "liveness": liveness,
        "reason": reason,
        "admitted": admitted,
    }


def gate_batch(manifest):
    """Screen a batch of candidate sources.

    manifest is a list of dicts, each with at least:
        canonical_uri, license_spdx
    and optionally:
        upstream_mtime, fetched_utc, override_verdict

    Returns (admitted, refused) lists of decision dicts.
    """
    admitted = []
    refused = []

    for entry in manifest:
        decision = check_source(
            canonical_uri=entry["canonical_uri"],
            license_spdx=entry["license_spdx"],
            upstream_mtime=entry.get("upstream_mtime"),
            fetched_utc=entry.get("fetched_utc"),
            override_verdict=entry.get("override_verdict"),
        )
        if decision["admitted"]:
            admitted.append(decision)
        else:
            refused.append(decision)

    return admitted, refused


SPEC_SOURCES = [
    {
        "canonical_uri": "github://shadcn-ui/taxonomy",
        "license_spdx": "MIT",
        "upstream_mtime": "2026-04-20T00:00:00Z",
    },
    {
        "canonical_uri": "github://shadcn-ui/ui",
        "license_spdx": "MIT",
        "upstream_mtime": "2026-07-30T00:00:00Z",
    },
    {
        "canonical_uri": "github://Chalarangelo/30-seconds-of-code",
        "license_spdx": "CC-BY-4.0",
        "upstream_mtime": "2026-07-29T00:00:00Z",
        "override_verdict": "index_only",
    },
    {
        "canonical_uri": "github://nilbuild/developer-roadmap",
        "license_spdx": "all rights reserved",
        "upstream_mtime": "2026-07-30T00:00:00Z",
    },
    {
        "canonical_uri": "github://goldbergyoni/nodebestpractices",
        "license_spdx": "CC-BY-SA-4.0",
        "upstream_mtime": "2026-06-15T00:00:00Z",
    },
    {
        "canonical_uri": "github://donnemartin/system-design-primer",
        "license_spdx": "CC-BY-4.0",
        "upstream_mtime": "2026-03-20T00:00:00Z",
    },
    {
        "canonical_uri": "github://ashishps1/awesome-system-design-resources",
        "license_spdx": "GPL-3.0",
        "upstream_mtime": "2026-02-16T00:00:00Z",
    },
    {
        "canonical_uri": "github://binhnguyennus/awesome-scalability",
        "license_spdx": "MIT",
        "upstream_mtime": "2026-01-04T00:00:00Z",
    },
    {
        "canonical_uri": "github://GoogleCloudPlatform/ml-design-patterns",
        "license_spdx": "Apache-2.0",
        "upstream_mtime": "2021-04-28T00:00:00Z",
    },
    {
        "canonical_uri": "github://eugeneyan/applied-ml",
        "license_spdx": "MIT",
        "upstream_mtime": "2024-07-18T00:00:00Z",
    },
    {
        "canonical_uri": "github://e2b-dev/awesome-ai-agents",
        "license_spdx": "CC-BY-NC-SA-4.0",
        "upstream_mtime": "2026-07-09T00:00:00Z",
    },
    {
        "canonical_uri": "github://modelcontextprotocol/modelcontextprotocol",
        "license_spdx": "Apache-2.0",
        "upstream_mtime": "2026-07-30T00:00:00Z",
    },
    {
        "canonical_uri": "github://modelcontextprotocol/servers",
        "license_spdx": "MIT",
        "upstream_mtime": "2026-07-29T00:00:00Z",
    },
    {
        "canonical_uri": "github://modelcontextprotocol/python-sdk",
        "license_spdx": "MIT",
        "upstream_mtime": "2026-07-30T00:00:00Z",
    },
]


def selftest():
    failures = []

    # Test 1: developer-roadmap blocked by hostname
    d = check_source("github://nilbuild/developer-roadmap",
                      "all rights reserved")
    if d["admitted"]:
        failures.append("developer-roadmap should be refused (blocked)")
    if d["verdict"] != "blocked":
        failures.append(f"developer-roadmap verdict is {d['verdict']}, expected blocked")

    # Test 2: old alias also blocked
    d2 = check_source("github://kamranahmedse/developer-roadmap", "MIT")
    if d2["admitted"]:
        failures.append("kamranahmedse/developer-roadmap should be refused")
    if d2["verdict"] != "blocked":
        failures.append(f"alias verdict is {d2['verdict']}, expected blocked")

    # Test 3: MIT vendor admitted
    d3 = check_source("github://shadcn-ui/ui", "MIT")
    if not d3["admitted"]:
        failures.append("MIT source should be admitted")
    if d3["verdict"] != "vendor":
        failures.append(f"MIT verdict is {d3['verdict']}, expected vendor")

    # Test 4: GPL is link_only (refused)
    d4 = check_source("github://foo/bar", "GPL-3.0")
    if d4["admitted"]:
        failures.append("GPL-3.0 should be refused (link_only)")
    if d4["verdict"] != "link_only":
        failures.append(f"GPL verdict is {d4['verdict']}, expected link_only")

    # Test 5: CC-BY-SA is index_only (admitted)
    d5 = check_source("github://foo/baz", "CC-BY-SA-4.0")
    if not d5["admitted"]:
        failures.append("CC-BY-SA-4.0 should be admitted (index_only)")
    if d5["verdict"] != "index_only":
        failures.append(f"CC-BY-SA verdict is {d5['verdict']}, expected index_only")

    # Test 6: CC-BY-NC is link_only (refused)
    d6 = check_source("github://foo/nc", "CC-BY-NC-SA-4.0")
    if d6["admitted"]:
        failures.append("CC-BY-NC-SA should be refused (link_only)")

    # Test 7: NOASSERTION is blocked
    d7 = check_source("github://foo/noassert", "NOASSERTION")
    if d7["admitted"]:
        failures.append("NOASSERTION should be refused")
    if d7["verdict"] != "blocked":
        failures.append(f"NOASSERTION verdict is {d7['verdict']}, expected blocked")

    # Test 8: stale liveness for >18 month old source
    d8 = check_source("github://old/repo", "MIT",
                       upstream_mtime="2021-04-28T00:00:00Z",
                       fetched_utc="2026-08-30T00:00:00Z")
    if d8["liveness"] != "stale":
        failures.append(f"5-year-old source liveness is {d8['liveness']}, expected stale")

    # Test 9: batch gate matches spec verdicts
    admitted, refused = gate_batch(SPEC_SOURCES)
    admitted_uris = {d["canonical_uri"] for d in admitted}
    refused_uris = {d["canonical_uri"] for d in refused}

    if "github://nilbuild/developer-roadmap" not in refused_uris:
        failures.append("developer-roadmap not in refused set")
    if "github://shadcn-ui/ui" not in admitted_uris:
        failures.append("shadcn-ui/ui not in admitted set")
    if "github://ashishps1/awesome-system-design-resources" not in refused_uris:
        failures.append("GPL awesome-system-design not in refused set")
    if "github://e2b-dev/awesome-ai-agents" not in refused_uris:
        failures.append("NC awesome-ai-agents not in refused set")

    expected_admitted = 11
    if len(admitted) != expected_admitted:
        failures.append(
            f"batch admitted {len(admitted)} sources, expected {expected_admitted}"
        )
    expected_refused = 3
    if len(refused) != expected_refused:
        failures.append(
            f"batch refused {len(refused)} sources, expected {expected_refused}"
        )

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print("PASS license_gate selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check a single source")
    p_check.add_argument("--uri", required=True)
    p_check.add_argument("--license", required=True, dest="license_spdx")
    p_check.add_argument("--verdict", default=None, dest="override_verdict")
    p_check.add_argument("--mtime", default=None)

    p_batch = sub.add_parser("batch", help="Screen a manifest file")
    p_batch.add_argument("--manifest", required=True)
    p_batch.add_argument("--db", default=None)

    sub.add_parser("blocked", help="List blocked hostnames")
    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "blocked":
        for h in sorted(BLOCKED_HOSTNAMES):
            print(f"  {h}")
        return 0

    if args.command == "check":
        decision = check_source(
            args.uri, args.license_spdx,
            upstream_mtime=args.mtime,
            override_verdict=args.override_verdict,
        )
        for k, v in decision.items():
            print(f"  {k}: {v}")
        return 0 if decision["admitted"] else 1

    if args.command == "batch":
        manifest = json.loads(Path(args.manifest).read_text())
        admitted, refused = gate_batch(manifest)
        print(f"  admitted: {len(admitted)}")
        for d in admitted:
            print(f"    [{d['verdict']}] {d['canonical_uri']} ({d['liveness']})")
        print(f"  refused: {len(refused)}")
        for d in refused:
            print(f"    [{d['verdict']}] {d['canonical_uri']}: {d['reason']}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
