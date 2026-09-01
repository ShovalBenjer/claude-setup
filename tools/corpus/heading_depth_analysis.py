#!/usr/bin/env python3
"""Heading depth analysis: document structure patterns from heading paths.

Analyses the heading_path column of chunks to reveal document hierarchy
depth, section organization patterns, and structural outliers.

Usage:
    python tools/corpus/heading_depth_analysis.py depth-distribution [--db PATH] [--json]
    python tools/corpus/heading_depth_analysis.py per-source [--db PATH] [--json]
    python tools/corpus/heading_depth_analysis.py top-sections [--db PATH] [--top N] [--json]
    python tools/corpus/heading_depth_analysis.py summary [--db PATH] [--json]
    python tools/corpus/heading_depth_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _heading_depth(path: str) -> int:
    if not path or path == "/":
        return 0
    parts = [p for p in path.split("/") if p]
    return len(parts)


def _top_heading(path: str) -> str:
    if not path or path == "/":
        return "(root)"
    parts = [p for p in path.split("/") if p]
    return parts[0] if parts else "(root)"


def depth_distribution(conn) -> list[dict]:
    """Distribution of heading depths across accepted chunks."""
    rows = conn.execute(
        "SELECT heading_path FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    depths: dict[int, int] = {}
    for (hp,) in rows:
        d = _heading_depth(hp)
        depths[d] = depths.get(d, 0) + 1

    total = sum(depths.values())
    results = []
    for depth in sorted(depths):
        n = depths[depth]
        results.append({
            "depth": depth,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        })

    return results


def per_source_depth(conn) -> list[dict]:
    """Heading depth statistics per source."""
    rows = conn.execute(
        "SELECT ch.source_id, s.title, ch.heading_path "
        "FROM chunks ch "
        "JOIN sources s ON ch.source_id = s.source_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_source: dict[str, dict] = {}
    for sid, title, hp in rows:
        d = _heading_depth(hp)
        if sid not in by_source:
            by_source[sid] = {"title": title, "depths": []}
        by_source[sid]["depths"].append(d)

    results = []
    for sid, info in by_source.items():
        ds = info["depths"]
        n = len(ds)
        mean = sum(ds) / n
        results.append({
            "source_id": sid,
            "title": info["title"],
            "chunk_count": n,
            "mean_depth": round(mean, 1),
            "max_depth": max(ds),
            "min_depth": min(ds),
            "distinct_depths": len(set(ds)),
        })

    results.sort(key=lambda r: -r["max_depth"])
    return results


def top_sections(conn, top_n: int = 20) -> list[dict]:
    """Most common top-level heading sections."""
    rows = conn.execute(
        "SELECT heading_path FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    sections: dict[str, int] = {}
    for (hp,) in rows:
        sec = _top_heading(hp)
        sections[sec] = sections.get(sec, 0) + 1

    total = sum(sections.values())
    results = [
        {
            "section": sec,
            "chunk_count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        }
        for sec, n in sections.items()
    ]
    results.sort(key=lambda r: -r["chunk_count"])
    return results[:top_n]


def heading_summary(conn) -> dict:
    """Aggregate heading depth statistics."""
    rows = conn.execute(
        "SELECT heading_path, source_id FROM chunks "
        "WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_chunks": 0,
            "mean_depth": 0.0,
            "median_depth": 0,
            "max_depth": 0,
            "distinct_top_sections": 0,
            "distinct_depths": 0,
            "shallow_count": 0,
            "deep_count": 0,
        }

    depths = [_heading_depth(r[0]) for r in rows]
    top_secs = {_top_heading(r[0]) for r in rows}
    n = len(depths)
    sorted_depths = sorted(depths)
    mean = sum(depths) / n

    return {
        "total_chunks": n,
        "mean_depth": round(mean, 1),
        "median_depth": sorted_depths[n // 2],
        "max_depth": max(depths),
        "distinct_top_sections": len(top_secs),
        "distinct_depths": len(set(depths)),
        "shallow_count": sum(1 for d in depths if d <= 1),
        "deep_count": sum(1 for d in depths if d >= 4),
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

        for sid, uri, kind in [("s1", "https://s1.com", "paper"),
                                ("s2", "https://s2.com", "local_md")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunks = [
            ("c1", "s1", 0, "/intro", "claim"),
            ("c2", "s1", 1, "/methods/data", "prose"),
            ("c3", "s1", 2, "/methods/analysis/stats", "code"),
            ("c4", "s1", 3, "/results", "claim"),
            ("c5", "s2", 0, "/overview", "prose"),
            ("c6", "s2", 1, "/overview/setup/config/advanced", "config"),
            ("c7", "s2", 2, "/api", "code"),
        ]
        for cid, sid, ordinal, hp, kind in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, hp, kind, "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        conn.commit()

        # 1: depth-distribution returns entries
        dist = depth_distribution(conn)
        assert len(dist) > 0
        checks += 1

        # 2: depths 1-4 are all present
        depth_set = {d["depth"] for d in dist}
        assert {1, 2, 3, 4}.issubset(depth_set)
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(d["share"] for d in dist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: depth 1 has 4 chunks (intro, results, overview, api)
        d1 = next(d for d in dist if d["depth"] == 1)
        assert d1["count"] == 4
        checks += 1

        # 5: per-source returns entries for both sources
        ps = per_source_depth(conn)
        assert len(ps) == 2
        checks += 1

        # 6: s1 has max_depth 3 (methods/analysis/stats)
        s1 = next(p for p in ps if p["source_id"] == "s1")
        assert s1["max_depth"] == 3
        checks += 1

        # 7: s2 has max_depth 4 (overview/setup/config/advanced)
        s2 = next(p for p in ps if p["source_id"] == "s2")
        assert s2["max_depth"] == 4
        checks += 1

        # 8: sorted by max_depth descending
        max_depths = [p["max_depth"] for p in ps]
        assert max_depths == sorted(max_depths, reverse=True)
        checks += 1

        # 9: top-sections returns entries
        ts = top_sections(conn)
        assert len(ts) > 0
        checks += 1

        # 10: "overview" section has 2 chunks
        ov = next(t for t in ts if t["section"] == "overview")
        assert ov["chunk_count"] == 2
        checks += 1

        # 11: summary has correct totals
        summary = heading_summary(conn)
        assert summary["total_chunks"] == 7
        assert summary["max_depth"] == 4
        checks += 1

        # 12: shallow count (depth <= 1) is 4
        assert summary["shallow_count"] == 4
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(ps)
        _ = json.dumps(ts)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = depth_distribution(conn2)
        assert empty == []
        empty_summary = heading_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS heading_depth_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Heading depth analysis: document structure patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("depth-distribution",
                            help="Heading depth distribution")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_src = sub.add_parser("per-source",
                           help="Depth statistics per source")
    p_src.add_argument("--db", default=DEFAULT_DB)
    p_src.add_argument("--json", action="store_true")

    p_top = sub.add_parser("top-sections",
                           help="Most common top-level sections")
    p_top.add_argument("--db", default=DEFAULT_DB)
    p_top.add_argument("--top", type=int, default=20)
    p_top.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Heading depth statistics")
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

    if args.cmd == "depth-distribution":
        results = depth_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  depth {r['depth']}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-source":
        results = per_source_depth(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['title'][:30]:30s}  chunks={r['chunk_count']:3d}  "
                      f"mean={r['mean_depth']:.1f}  max={r['max_depth']}  "
                      f"depths={r['distinct_depths']}")

    elif args.cmd == "top-sections":
        results = top_sections(conn, args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['section']:20s}  {r['chunk_count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "summary":
        result = heading_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunks: {result['total_chunks']}")
            print(f"  Depth: mean={result['mean_depth']:.1f}  "
                  f"median={result['median_depth']}  "
                  f"max={result['max_depth']}")
            print(f"  Sections: {result['distinct_top_sections']}  "
                  f"Depth levels: {result['distinct_depths']}")
            print(f"  Shallow (<=1): {result['shallow_count']}  "
                  f"Deep (>=4): {result['deep_count']}")

    conn.close()


if __name__ == "__main__":
    main()
