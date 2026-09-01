#!/usr/bin/env python3
"""Tag-citation yield: which topical tags produce the most-cited chunks.

No tool correlates chunk_tags.tag with chunks.citation_count.
citation_tag_profile analyses the citations.tag column (a different
field); tag_landscape covers tag-edge correlation but not citations.
This tool answers which topical tags produce the most-cited chunks.

Usage:
    python tools/corpus/tag_citation_yield.py yield [--db PATH] [--json]
    python tools/corpus/tag_citation_yield.py top-tags [--db PATH] [--json]
    python tools/corpus/tag_citation_yield.py uncited [--db PATH] [--json]
    python tools/corpus/tag_citation_yield.py summary [--db PATH] [--json]
    python tools/corpus/tag_citation_yield.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tag_citation_yield(conn) -> list[dict]:
    """Mean citation count per tag."""
    rows = conn.execute(
        "SELECT ct.tag, c.citation_count "
        "FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, list[int]] = {}
    for tag, cc in rows:
        if tag not in by_tag:
            by_tag[tag] = []
        by_tag[tag].append(cc)

    results = []
    for tag in sorted(by_tag):
        counts = by_tag[tag]
        n = len(counts)
        total = sum(counts)
        cited = sum(1 for c in counts if c > 0)
        results.append({
            "tag": tag,
            "chunk_count": n,
            "total_citations": total,
            "mean_citations": round(total / n, 2) if n > 0 else 0.0,
            "cited_rate": round(cited / n, 4) if n > 0 else 0.0,
        })

    return results


def top_cited_tags(conn, limit: int = 10) -> list[dict]:
    """Tags ranked by mean citation count, highest first."""
    all_tags = tag_citation_yield(conn)
    ranked = sorted(
        all_tags, key=lambda t: t["mean_citations"], reverse=True
    )
    return ranked[:limit]


def uncited_tags(conn) -> list[dict]:
    """Tags where no chunk has any citations."""
    all_tags = tag_citation_yield(conn)
    return [t for t in all_tags if t["total_citations"] == 0]


def yield_summary(conn) -> dict:
    """Aggregate tag-citation yield statistics."""
    all_tags = tag_citation_yield(conn)

    if not all_tags:
        return {
            "total_tags": 0,
            "tags_with_citations": 0,
            "tags_without_citations": 0,
            "highest_yield_tag": None,
            "overall_mean_citations": 0.0,
        }

    with_cites = sum(1 for t in all_tags if t["total_citations"] > 0)
    best = max(all_tags, key=lambda t: t["mean_citations"])
    total_chunks = sum(t["chunk_count"] for t in all_tags)
    total_cites = sum(t["total_citations"] for t in all_tags)

    return {
        "total_tags": len(all_tags),
        "tags_with_citations": with_cites,
        "tags_without_citations": len(all_tags) - with_cites,
        "highest_yield_tag": best["tag"],
        "overall_mean_citations": round(
            total_cites / total_chunks, 2
        ) if total_chunks > 0 else 0.0,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        chunks = [
            ("c1", 0, "claim", 5),
            ("c2", 1, "code", 3),
            ("c3", 2, "prose", 0),
            ("c4", 3, "claim", 8),
            ("c5", 4, "code", 0),
        ]
        for cid, ordinal, kind, cites in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, "s1", ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 10,
                 f"sha_{cid}", 0, cites, "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "tag TEXT NOT NULL, "
            "score REAL NOT NULL, "
            "tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )

        tags = [
            ("c1", "ml", 0.9),
            ("c1", "security", 0.7),
            ("c2", "ml", 0.8),
            ("c3", "ml", 0.6),
            ("c4", "security", 0.9),
            ("c4", "ml", 0.5),
            ("c5", "testing", 0.8),
        ]
        for cid, tag, score in tags:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, "
                "tagged_utc) VALUES (?, ?, ?, ?)",
                (cid, tag, score, now),
            )

        conn.commit()

        # 1: yield returns entries for 3 tags
        yld = tag_citation_yield(conn)
        assert len(yld) == 3
        checks += 1

        # 2: ml tag: chunks c1(5), c2(3), c3(0), c4(8) = 16 total
        ml = next(t for t in yld if t["tag"] == "ml")
        assert ml["chunk_count"] == 4
        assert ml["total_citations"] == 16
        checks += 1

        # 3: ml mean is 16/4 = 4.0
        assert abs(ml["mean_citations"] - 4.0) < 0.01
        checks += 1

        # 4: security tag: c1(5), c4(8) = 13 total, mean 6.5
        sec = next(t for t in yld if t["tag"] == "security")
        assert sec["total_citations"] == 13
        assert abs(sec["mean_citations"] - 6.5) < 0.01
        checks += 1

        # 5: testing tag: c5(0) = 0 total
        test_tag = next(t for t in yld if t["tag"] == "testing")
        assert test_tag["total_citations"] == 0
        checks += 1

        # 6: top-tags returns security first (highest mean)
        top = top_cited_tags(conn, limit=3)
        assert len(top) == 3
        assert top[0]["tag"] == "security"
        checks += 1

        # 7: uncited returns testing
        unc = uncited_tags(conn)
        assert len(unc) == 1
        assert unc[0]["tag"] == "testing"
        checks += 1

        # 8: ml cited_rate is 3/4 = 0.75
        assert abs(ml["cited_rate"] - 0.75) < 0.01
        checks += 1

        # 9: security cited_rate is 1.0
        assert abs(sec["cited_rate"] - 1.0) < 0.01
        checks += 1

        # 10: testing cited_rate is 0.0
        assert abs(test_tag["cited_rate"] - 0.0) < 0.01
        checks += 1

        # 11: summary has correct totals
        summary = yield_summary(conn)
        assert summary["total_tags"] == 3
        assert summary["tags_with_citations"] == 2
        assert summary["tags_without_citations"] == 1
        checks += 1

        # 12: highest yield tag is security
        assert summary["highest_yield_tag"] == "security"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(yld)
        _ = json.dumps(top)
        _ = json.dumps(unc)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL, tag TEXT NOT NULL, "
            "score REAL NOT NULL, tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )
        empty = tag_citation_yield(conn2)
        assert empty == []
        empty_summary = yield_summary(conn2)
        assert empty_summary["total_tags"] == 0
        checks += 1

    print(f"PASS tag_citation_yield selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag-citation yield analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_yld = sub.add_parser("yield",
                           help="Mean citations per tag")
    p_yld.add_argument("--db", default=DEFAULT_DB)
    p_yld.add_argument("--json", action="store_true")

    p_top = sub.add_parser("top-tags",
                           help="Tags by citation yield")
    p_top.add_argument("--db", default=DEFAULT_DB)
    p_top.add_argument("--json", action="store_true")
    p_top.add_argument("--limit", type=int, default=10)

    p_unc = sub.add_parser("uncited",
                           help="Tags with zero citations")
    p_unc.add_argument("--db", default=DEFAULT_DB)
    p_unc.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Yield statistics")
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

    if args.cmd == "yield":
        results = tag_citation_yield(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:16s}  n={r['chunk_count']:3d}  "
                      f"cites={r['total_citations']:4d}  "
                      f"mean={r['mean_citations']:.1f}  "
                      f"cited={r['cited_rate']:.0%}")

    elif args.cmd == "top-tags":
        results = top_cited_tags(conn, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for i, r in enumerate(results, 1):
                print(f"  {i:2d}. {r['tag']:16s}  "
                      f"mean={r['mean_citations']:.1f}  "
                      f"n={r['chunk_count']}")

    elif args.cmd == "uncited":
        results = uncited_tags(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  (all tags have citations)")
            for r in results:
                print(f"  {r['tag']:16s}  n={r['chunk_count']}")

    elif args.cmd == "summary":
        result = yield_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tags: {result['total_tags']}  "
                  f"With citations: "
                  f"{result['tags_with_citations']}  "
                  f"Without: "
                  f"{result['tags_without_citations']}")
            if result["highest_yield_tag"]:
                print(f"  Highest yield: "
                      f"{result['highest_yield_tag']}")
            print(f"  Overall mean: "
                  f"{result['overall_mean_citations']:.1f}")

    conn.close()


if __name__ == "__main__":
    main()
