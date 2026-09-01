#!/usr/bin/env python3
"""Artifact name analysis: frequency, overlap, and implementation patterns.

Analyses the artifacts.name column which had zero GROUP BY queries
anywhere in the codebase, revealing which named artifacts appear
most frequently, which span multiple sources, and how implementation
rates vary by name.

Usage:
    python tools/corpus/artifact_name_analysis.py frequency [--db PATH] [--json]
    python tools/corpus/artifact_name_analysis.py multi-source [--db PATH] [--json]
    python tools/corpus/artifact_name_analysis.py implementation [--db PATH] [--json]
    python tools/corpus/artifact_name_analysis.py summary [--db PATH] [--json]
    python tools/corpus/artifact_name_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def name_frequency(conn) -> list[dict]:
    """Artifact name frequency distribution, most common first."""
    rows = conn.execute(
        "SELECT name, artifact_type, count(*) AS cnt "
        "FROM artifacts GROUP BY name, artifact_type "
        "ORDER BY cnt DESC, name"
    ).fetchall()

    if not rows:
        return []

    total = sum(r[2] for r in rows)
    results = [
        {
            "name": name,
            "artifact_type": atype,
            "count": cnt,
            "share": round(cnt / total, 4) if total > 0 else 0.0,
        }
        for name, atype, cnt in rows
    ]
    return results


def multi_source_artifacts(conn) -> list[dict]:
    """Artifacts that appear across multiple sources."""
    rows = conn.execute(
        "SELECT a.name, a.artifact_type, "
        "count(DISTINCT c.source_id) AS source_count, "
        "count(*) AS total_refs "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "GROUP BY a.name, a.artifact_type "
        "HAVING source_count > 1 "
        "ORDER BY source_count DESC, total_refs DESC"
    ).fetchall()

    if not rows:
        return []

    results = [
        {
            "name": name,
            "artifact_type": atype,
            "source_count": sc,
            "total_refs": tr,
        }
        for name, atype, sc, tr in rows
    ]
    return results


def implementation_by_name(conn) -> list[dict]:
    """Implementation rate per artifact name."""
    rows = conn.execute(
        "SELECT name, artifact_type, "
        "count(*) AS total, "
        "sum(CASE WHEN implemented = 1 THEN 1 ELSE 0 END) AS impl "
        "FROM artifacts "
        "GROUP BY name, artifact_type "
        "HAVING total >= 1 "
        "ORDER BY total DESC, name"
    ).fetchall()

    if not rows:
        return []

    results = [
        {
            "name": name,
            "artifact_type": atype,
            "total": total,
            "implemented": impl,
            "impl_rate": round(impl / total, 4) if total > 0 else 0.0,
        }
        for name, atype, total, impl in rows
    ]
    return results


def name_summary(conn) -> dict:
    """Aggregate artifact name statistics."""
    rows = conn.execute(
        "SELECT a.name, a.artifact_type, a.implemented, "
        "c.source_id "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id"
    ).fetchall()

    if not rows:
        return {
            "total_artifacts": 0,
            "distinct_names": 0,
            "distinct_name_type_pairs": 0,
            "multi_source_names": 0,
            "implemented_count": 0,
            "impl_rate": 0.0,
            "top_names": [],
        }

    n = len(rows)
    names: set[str] = set()
    name_types: set[tuple[str, str]] = set()
    name_sources: dict[str, set[str]] = {}
    impl_count = 0
    name_counts: dict[str, int] = {}

    for name, atype, implemented, source_id in rows:
        names.add(name)
        name_types.add((name, atype))
        if name not in name_sources:
            name_sources[name] = set()
        name_sources[name].add(source_id)
        if implemented:
            impl_count += 1
        name_counts[name] = name_counts.get(name, 0) + 1

    multi_source = sum(
        1 for s in name_sources.values() if len(s) > 1
    )
    top = sorted(name_counts.items(), key=lambda x: -x[1])[:5]

    return {
        "total_artifacts": n,
        "distinct_names": len(names),
        "distinct_name_type_pairs": len(name_types),
        "multi_source_names": multi_source,
        "implemented_count": impl_count,
        "impl_rate": round(impl_count / n, 4) if n > 0 else 0.0,
        "top_names": [{"name": nm, "count": ct} for nm, ct in top],
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

        sources = [
            ("s1", "paper"),
            ("s2", "repo"),
        ]
        for sid, kind in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunks = [
            ("c1", "s1", 0),
            ("c2", "s1", 1),
            ("c3", "s2", 0),
            ("c4", "s2", 1),
        ]
        for cid, sid, ordinal in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", "prose", "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        # Artifacts: React appears in both sources, Flask only in s1
        artifacts = [
            ("a1", "c1", "library", "React", "18.2.0", "import React", 1),
            ("a2", "c2", "api", "Flask", "2.3.0", "from flask", 1),
            ("a3", "c3", "library", "React", "18.2.0", "import React", 0),
            ("a4", "c3", "command", "npm", None, "npm install", 1),
            ("a5", "c4", "library", "React", "18.3.0", None, 1),
            ("a6", "c4", "pattern", "Observer", None, None, 0),
            ("a7", "c1", "api", "REST", None, None, 0),
        ]
        for aid, cid, atype, name, version, snippet, impl in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, implemented, "
                "evidence_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, version, snippet, impl, None),
            )

        conn.commit()

        # 1: frequency returns entries
        freq = name_frequency(conn)
        assert len(freq) > 0
        checks += 1

        # 2: React is the most frequent (3 occurrences)
        react_entries = [f for f in freq if f["name"] == "React"]
        react_total = sum(f["count"] for f in react_entries)
        assert react_total == 3
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(f["share"] for f in freq)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: multi-source returns entries
        ms = multi_source_artifacts(conn)
        assert len(ms) > 0
        checks += 1

        # 5: React appears in 2 sources
        react_ms = next(
            (m for m in ms if m["name"] == "React"), None
        )
        assert react_ms is not None
        assert react_ms["source_count"] == 2
        checks += 1

        # 6: Flask does NOT appear in multi-source (only in s1)
        flask_ms = next(
            (m for m in ms if m["name"] == "Flask"), None
        )
        assert flask_ms is None
        checks += 1

        # 7: implementation returns entries
        impl = implementation_by_name(conn)
        assert len(impl) > 0
        checks += 1

        # 8: React has 2 implemented out of 3
        react_impl = next(
            (i for i in impl if i["name"] == "React"
             and i["artifact_type"] == "library"), None
        )
        assert react_impl is not None
        assert react_impl["implemented"] == 2
        assert react_impl["total"] == 3
        checks += 1

        # 9: Observer has 0% implementation rate
        obs_impl = next(
            (i for i in impl if i["name"] == "Observer"), None
        )
        assert obs_impl is not None
        assert obs_impl["impl_rate"] == 0.0
        checks += 1

        # 10: Flask has 100% implementation rate
        flask_impl = next(
            (i for i in impl if i["name"] == "Flask"), None
        )
        assert flask_impl is not None
        assert flask_impl["impl_rate"] == 1.0
        checks += 1

        # 11: summary has correct totals
        summary = name_summary(conn)
        assert summary["total_artifacts"] == 7
        assert summary["distinct_names"] == 5
        checks += 1

        # 12: multi-source count and impl count
        assert summary["multi_source_names"] == 1
        assert summary["implemented_count"] == 4
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(freq)
        _ = json.dumps(ms)
        _ = json.dumps(impl)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = name_frequency(conn2)
        assert empty == []
        empty_summary = name_summary(conn2)
        assert empty_summary["total_artifacts"] == 0
        checks += 1

    print(f"PASS artifact_name_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact name analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_freq = sub.add_parser("frequency",
                            help="Artifact name frequency")
    p_freq.add_argument("--db", default=DEFAULT_DB)
    p_freq.add_argument("--json", action="store_true")

    p_ms = sub.add_parser("multi-source",
                          help="Artifacts spanning multiple sources")
    p_ms.add_argument("--db", default=DEFAULT_DB)
    p_ms.add_argument("--json", action="store_true")

    p_impl = sub.add_parser("implementation",
                            help="Implementation rate by name")
    p_impl.add_argument("--db", default=DEFAULT_DB)
    p_impl.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Artifact name statistics")
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

    if args.cmd == "frequency":
        results = name_frequency(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['name'][:20]:20s}  {r['artifact_type']:10s}  "
                      f"{r['count']:3d}  {r['share']:5.1%}  {bar}")

    elif args.cmd == "multi-source":
        results = multi_source_artifacts(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['name'][:20]:20s}  {r['artifact_type']:10s}  "
                      f"sources={r['source_count']}  "
                      f"refs={r['total_refs']}")

    elif args.cmd == "implementation":
        results = implementation_by_name(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['name'][:20]:20s}  {r['artifact_type']:10s}  "
                      f"{r['implemented']}/{r['total']}  "
                      f"{r['impl_rate']:.0%}")

    elif args.cmd == "summary":
        result = name_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total_artifacts']}  "
                  f"Names: {result['distinct_names']}  "
                  f"Pairs: {result['distinct_name_type_pairs']}")
            print(f"  Multi-source: {result['multi_source_names']}  "
                  f"Implemented: {result['implemented_count']} "
                  f"({result['impl_rate']:.0%})")
            if result["top_names"]:
                top = ", ".join(
                    f"{t['name']}({t['count']})"
                    for t in result["top_names"]
                )
                print(f"  Top: {top}")

    conn.close()


if __name__ == "__main__":
    main()
