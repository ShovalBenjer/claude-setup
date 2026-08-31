#!/usr/bin/env python3
"""Artifact version analysis: version and snippet patterns.

Analyses the version and snippet columns of the artifacts table to
reveal versioning patterns, snippet coverage, and version diversity
across artifact types and sources.

Usage:
    python tools/corpus/artifact_version_analysis.py version-distribution [--db PATH] [--json]
    python tools/corpus/artifact_version_analysis.py snippet-coverage [--db PATH] [--json]
    python tools/corpus/artifact_version_analysis.py per-type [--db PATH] [--json]
    python tools/corpus/artifact_version_analysis.py summary [--db PATH] [--json]
    python tools/corpus/artifact_version_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


_SEMVER_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
_MAJOR_ONLY_RE = re.compile(r"^\d+$")
_CALVER_RE = re.compile(r"^\d{4}[.\-]\d{1,2}")


def _classify_version(v: str | None) -> str:
    if not v or not v.strip():
        return "unset"
    v = v.strip()
    if _SEMVER_RE.match(v):
        return "semver"
    if _MAJOR_ONLY_RE.match(v):
        return "major-only"
    if _CALVER_RE.match(v):
        return "calver"
    return "other"


def version_distribution(conn) -> list[dict]:
    """Distribution of version formats across artifacts."""
    rows = conn.execute(
        "SELECT version FROM artifacts"
    ).fetchall()

    if not rows:
        return []

    formats: dict[str, int] = {}
    for (ver,) in rows:
        fmt = _classify_version(ver)
        formats[fmt] = formats.get(fmt, 0) + 1

    total = sum(formats.values())
    results = [
        {
            "format": fmt,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        }
        for fmt, n in formats.items()
    ]
    results.sort(key=lambda r: -r["count"])
    return results


def snippet_coverage(conn) -> list[dict]:
    """Snippet coverage and length statistics per artifact type."""
    rows = conn.execute(
        "SELECT artifact_type, snippet FROM artifacts"
    ).fetchall()

    if not rows:
        return []

    by_type: dict[str, dict] = {}
    for atype, snippet in rows:
        if atype not in by_type:
            by_type[atype] = {
                "total": 0,
                "has_snippet": 0,
                "lengths": [],
            }
        t = by_type[atype]
        t["total"] += 1
        if snippet and snippet.strip():
            t["has_snippet"] += 1
            t["lengths"].append(len(snippet.strip()))

    results = []
    for atype, info in by_type.items():
        total = info["total"]
        has = info["has_snippet"]
        lengths = info["lengths"]
        mean_len = round(sum(lengths) / len(lengths), 1) if lengths else 0.0
        max_len = max(lengths) if lengths else 0
        results.append({
            "artifact_type": atype,
            "total": total,
            "has_snippet": has,
            "coverage": round(has / total, 4) if total > 0 else 0.0,
            "mean_length": mean_len,
            "max_length": max_len,
        })

    results.sort(key=lambda r: -r["total"])
    return results


def per_type_versions(conn) -> list[dict]:
    """Version patterns per artifact type."""
    rows = conn.execute(
        "SELECT artifact_type, version FROM artifacts"
    ).fetchall()

    if not rows:
        return []

    by_type: dict[str, dict] = {}
    for atype, ver in rows:
        if atype not in by_type:
            by_type[atype] = {"total": 0, "versions": [], "formats": {}}
        t = by_type[atype]
        t["total"] += 1
        fmt = _classify_version(ver)
        t["formats"][fmt] = t["formats"].get(fmt, 0) + 1
        if ver and ver.strip():
            t["versions"].append(ver.strip())

    results = []
    for atype, info in by_type.items():
        distinct = len(set(info["versions"]))
        populated = len(info["versions"])
        results.append({
            "artifact_type": atype,
            "total": info["total"],
            "version_populated": populated,
            "version_rate": round(
                populated / info["total"], 4
            ) if info["total"] > 0 else 0.0,
            "distinct_versions": distinct,
            "format_breakdown": info["formats"],
        })

    results.sort(key=lambda r: -r["total"])
    return results


def version_summary(conn) -> dict:
    """Aggregate version and snippet statistics."""
    rows = conn.execute(
        "SELECT artifact_type, version, snippet, name FROM artifacts"
    ).fetchall()

    if not rows:
        return {
            "total_artifacts": 0,
            "version_populated": 0,
            "version_rate": 0.0,
            "snippet_populated": 0,
            "snippet_rate": 0.0,
            "distinct_versions": 0,
            "distinct_names": 0,
            "version_formats": {},
            "artifact_types": 0,
        }

    n = len(rows)
    ver_pop = 0
    snip_pop = 0
    versions: set[str] = set()
    names: set[str] = set()
    types: set[str] = set()
    formats: dict[str, int] = {}

    for atype, ver, snippet, name in rows:
        types.add(atype)
        names.add(name)
        fmt = _classify_version(ver)
        formats[fmt] = formats.get(fmt, 0) + 1
        if ver and ver.strip():
            ver_pop += 1
            versions.add(ver.strip())
        if snippet and snippet.strip():
            snip_pop += 1

    return {
        "total_artifacts": n,
        "version_populated": ver_pop,
        "version_rate": round(ver_pop / n, 4) if n > 0 else 0.0,
        "snippet_populated": snip_pop,
        "snippet_rate": round(snip_pop / n, 4) if n > 0 else 0.0,
        "distinct_versions": len(versions),
        "distinct_names": len(names),
        "version_formats": formats,
        "artifact_types": len(types),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source s1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for cid, ordinal in [("c1", 0), ("c2", 1), ("c3", 2)]:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, "s1", ordinal, f"/h/{cid}", "prose", "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        artifacts = [
            ("a1", "c1", "library", "numpy", "1.24.3",
             "import numpy as np", 1),
            ("a2", "c1", "library", "pandas", "2.1",
             "import pandas as pd", 1),
            ("a3", "c1", "api", "REST endpoint", None, None, 0),
            ("a4", "c2", "command", "pip install", "",
             "pip install numpy", 1),
            ("a5", "c2", "config", "pyproject.toml", "2024.1",
             "[project]\nname = 'foo'", 0),
            ("a6", "c3", "library", "torch", "2",
             "", 1),
            ("a7", "c3", "pattern", "singleton", None, None, 0),
            ("a8", "c3", "oneliner", "list comp", None,
             "[x for x in range(10)]", 1),
        ]
        for aid, cid, atype, name, ver, snippet, impl in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, implemented, "
                "evidence_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, ver, snippet, impl, None),
            )

        conn.commit()

        # 1: version-distribution returns entries
        vd = version_distribution(conn)
        assert len(vd) > 0
        checks += 1

        # 2: semver format detected (1.24.3, 2.1)
        fmt_set = {v["format"] for v in vd}
        assert "semver" in fmt_set
        checks += 1

        # 3: unset detected (api, pattern have None versions)
        assert "unset" in fmt_set
        checks += 1

        # 4: shares sum to approximately 1.0
        total_share = sum(v["share"] for v in vd)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 5: snippet-coverage returns entries
        sc = snippet_coverage(conn)
        assert len(sc) > 0
        checks += 1

        # 6: library type has 2 snippets out of 3
        lib = next(s for s in sc if s["artifact_type"] == "library")
        assert lib["total"] == 3
        assert lib["has_snippet"] == 2
        checks += 1

        # 7: pattern type has 0 snippets
        pat = next(s for s in sc if s["artifact_type"] == "pattern")
        assert pat["has_snippet"] == 0
        assert pat["coverage"] == 0.0
        checks += 1

        # 8: per-type returns entries
        pt = per_type_versions(conn)
        assert len(pt) > 0
        checks += 1

        # 9: library has 3 versions populated (1.24.3, 2.1, 2)
        pt_lib = next(p for p in pt if p["artifact_type"] == "library")
        assert pt_lib["version_populated"] == 3
        assert pt_lib["distinct_versions"] == 3
        checks += 1

        # 10: api has 0 versions populated
        pt_api = next(p for p in pt if p["artifact_type"] == "api")
        assert pt_api["version_populated"] == 0
        checks += 1

        # 11: summary has correct totals
        summary = version_summary(conn)
        assert summary["total_artifacts"] == 8
        assert summary["distinct_names"] == 8
        checks += 1

        # 12: version and snippet rates
        assert summary["version_populated"] == 4
        assert summary["snippet_populated"] == 5
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(vd)
        _ = json.dumps(sc)
        _ = json.dumps(pt)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = version_distribution(conn2)
        assert empty == []
        empty_summary = version_summary(conn2)
        assert empty_summary["total_artifacts"] == 0
        checks += 1

    print(f"PASS artifact_version_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact version and snippet analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ver = sub.add_parser("version-distribution",
                           help="Version format distribution")
    p_ver.add_argument("--db", default=DEFAULT_DB)
    p_ver.add_argument("--json", action="store_true")

    p_snip = sub.add_parser("snippet-coverage",
                            help="Snippet coverage per type")
    p_snip.add_argument("--db", default=DEFAULT_DB)
    p_snip.add_argument("--json", action="store_true")

    p_type = sub.add_parser("per-type",
                            help="Version patterns per artifact type")
    p_type.add_argument("--db", default=DEFAULT_DB)
    p_type.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Version and snippet statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "version-distribution":
        results = version_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['format']:12s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "snippet-coverage":
        results = snippet_coverage(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_type']:10s}  n={r['total']:3d}  "
                      f"snippets={r['has_snippet']}  "
                      f"coverage={r['coverage']:.0%}  "
                      f"mean_len={r['mean_length']:.0f}")

    elif args.cmd == "per-type":
        results = per_type_versions(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_type']:10s}  n={r['total']:3d}  "
                      f"versioned={r['version_populated']}  "
                      f"({r['version_rate']:.0%})  "
                      f"distinct={r['distinct_versions']}")

    elif args.cmd == "summary":
        result = version_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total_artifacts']}")
            print(f"  Versioned: {result['version_populated']} "
                  f"({result['version_rate']:.1%})  "
                  f"Snippets: {result['snippet_populated']} "
                  f"({result['snippet_rate']:.1%})")
            print(f"  Distinct versions: {result['distinct_versions']}  "
                  f"Names: {result['distinct_names']}  "
                  f"Types: {result['artifact_types']}")

    conn.close()


if __name__ == "__main__":
    main()
