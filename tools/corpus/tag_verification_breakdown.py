#!/usr/bin/env python3
"""Tag-verification breakdown: citation verification rates by topical tag.

tag_citation_yield correlates chunk_tags.tag with chunks.citation_count
(the aggregate count column).  No tool joins chunk_tags with individual
citation rows from the citations table to show which topical tags have
the highest verification rates at the per-citation level.

Usage:
    python tools/corpus/tag_verification_breakdown.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_verification_breakdown.py unverified [--db PATH] [--json]
    python tools/corpus/tag_verification_breakdown.py lag [--db PATH] [--json]
    python tools/corpus/tag_verification_breakdown.py summary [--db PATH] [--json]
    python tools/corpus/tag_verification_breakdown.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def verification_by_tag(conn) -> list[dict]:
    """Citation verification rates per topical tag."""
    rows = conn.execute(
        "SELECT ct.tag, "
        "  count(DISTINCT ci.citation_id) AS total_cites, "
        "  count(DISTINCT CASE WHEN ci.verified = 1 "
        "    THEN ci.citation_id END) AS verified_cites "
        "FROM chunk_tags ct "
        "JOIN citations ci ON ct.chunk_id = ci.chunk_id "
        "GROUP BY ct.tag "
        "ORDER BY ct.tag"
    ).fetchall()

    if not rows:
        return []

    results = []
    for tag, total, verified in rows:
        rate = round(verified / total, 4) if total > 0 else 0.0
        results.append({
            "tag": tag,
            "total_citations": total,
            "verified_citations": verified,
            "unverified_citations": total - verified,
            "verification_rate": rate,
        })

    return results


def unverified_tags(conn) -> list[dict]:
    """Tags where no citation on any tagged chunk is verified."""
    vbt = verification_by_tag(conn)
    return [t for t in vbt if t["verified_citations"] == 0]


def verification_lag_by_tag(conn) -> list[dict]:
    """Mean verification lag (ingested to verified) per topical tag."""
    rows = conn.execute(
        "SELECT ct.tag, ci.citation_id, "
        "  ch.ingested_utc, ci.verified_utc "
        "FROM chunk_tags ct "
        "JOIN chunks ch ON ct.chunk_id = ch.chunk_id "
        "JOIN citations ci ON ct.chunk_id = ci.chunk_id "
        "WHERE ci.verified = 1 AND ci.verified_utc IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, list[float]] = {}
    for tag, _cid, ingested, verified in rows:
        try:
            from datetime import datetime
            t_ing = datetime.fromisoformat(
                ingested.replace("Z", "+00:00")
            )
            t_ver = datetime.fromisoformat(
                verified.replace("Z", "+00:00")
            )
            lag_days = (t_ver - t_ing).total_seconds() / 86400.0
        except (ValueError, AttributeError):
            continue
        if tag not in by_tag:
            by_tag[tag] = []
        by_tag[tag].append(lag_days)

    results = []
    for tag in sorted(by_tag):
        lags = by_tag[tag]
        n = len(lags)
        results.append({
            "tag": tag,
            "verified_count": n,
            "mean_lag_days": round(sum(lags) / n, 2),
            "min_lag_days": round(min(lags), 2),
            "max_lag_days": round(max(lags), 2),
        })

    return results


def tag_verification_summary(conn) -> dict:
    """Aggregate tag-verification statistics."""
    vbt = verification_by_tag(conn)

    if not vbt:
        return {
            "tags_with_citations": 0,
            "total_tag_citations": 0,
            "overall_verification_rate": 0.0,
            "fully_verified_tags": 0,
            "unverified_tags": 0,
            "highest_rate_tag": None,
            "lowest_rate_tag": None,
        }

    total_cites = sum(t["total_citations"] for t in vbt)
    total_verified = sum(t["verified_citations"] for t in vbt)
    fully = sum(1 for t in vbt if t["verification_rate"] == 1.0)
    unver = sum(1 for t in vbt if t["verified_citations"] == 0)
    highest = max(vbt, key=lambda t: t["verification_rate"])
    lowest = min(vbt, key=lambda t: t["verification_rate"])

    return {
        "tags_with_citations": len(vbt),
        "total_tag_citations": total_cites,
        "overall_verification_rate": (
            round(total_verified / total_cites, 4)
            if total_cites > 0 else 0.0
        ),
        "fully_verified_tags": fully,
        "unverified_tags": unver,
        "highest_rate_tag": highest["tag"],
        "lowest_rate_tag": lowest["tag"],
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"
        later = "2026-06-15T00:00:00Z"

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

        for i in range(4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "tag TEXT NOT NULL, score REAL NOT NULL, "
            "tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )

        # Tags: ml on c1,c2; security on c3; testing on c4
        tags = [
            ("c1", "ml", 0.9, now), ("c2", "ml", 0.8, now),
            ("c3", "security", 0.85, now),
            ("c4", "testing", 0.7, now),
        ]
        for t in tags:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, "
                "tagged_utc) VALUES (?, ?, ?, ?)", t,
            )

        # Citations:
        # c1: 2 citations (both verified)
        # c2: 1 citation (unverified)
        # c3: 2 citations (1 verified, 1 unverified)
        # c4: 1 citation (unverified)
        cits = [
            ("ci1", "c1", "https://r1.com", None, "url",
             None, 1, later),
            ("ci2", "c1", "https://r2.com", None, "doi",
             None, 1, later),
            ("ci3", "c2", "https://r3.com", None, "url",
             None, 0, None),
            ("ci4", "c3", "https://r4.com", None, "doi",
             None, 1, later),
            ("ci5", "c3", "https://r5.com", None, "url",
             None, 0, None),
            ("ci6", "c4", "https://r6.com", None, "doi",
             None, 0, None),
        ]
        for c in cits:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", c,
            )

        conn.commit()

        # 1: verification_by_tag returns 3 tags
        vbt = verification_by_tag(conn)
        assert len(vbt) == 3
        checks += 1

        # 2: ml tag: c1 has ci1+ci2 (verified), c2 has ci3 (unverified)
        ml = next(t for t in vbt if t["tag"] == "ml")
        assert ml["total_citations"] == 3
        assert ml["verified_citations"] == 2
        checks += 1

        # 3: ml verification rate = 2/3
        assert abs(ml["verification_rate"] - 0.6667) < 0.001
        checks += 1

        # 4: security tag: ci4 verified, ci5 unverified
        sec = next(t for t in vbt if t["tag"] == "security")
        assert sec["total_citations"] == 2
        assert sec["verified_citations"] == 1
        checks += 1

        # 5: testing tag: ci6 unverified only
        test = next(t for t in vbt if t["tag"] == "testing")
        assert test["total_citations"] == 1
        assert test["verified_citations"] == 0
        checks += 1

        # 6: unverified_tags returns testing
        uv = unverified_tags(conn)
        assert len(uv) == 1
        assert uv[0]["tag"] == "testing"
        checks += 1

        # 7: verification lag returns entries
        lag = verification_lag_by_tag(conn)
        assert len(lag) > 0
        checks += 1

        # 8: ml lag is 14 days (Jun 1 to Jun 15)
        ml_lag = next(l for l in lag if l["tag"] == "ml")
        assert abs(ml_lag["mean_lag_days"] - 14.0) < 0.01
        checks += 1

        # 9: security lag is also 14 days
        sec_lag = next(l for l in lag if l["tag"] == "security")
        assert abs(sec_lag["mean_lag_days"] - 14.0) < 0.01
        checks += 1

        # 10: summary totals correct
        summary = tag_verification_summary(conn)
        assert summary["tags_with_citations"] == 3
        assert summary["total_tag_citations"] == 6
        checks += 1

        # 11: fully verified tags = 0 (ml is 2/3, sec is 1/2)
        assert summary["fully_verified_tags"] == 0
        checks += 1

        # 12: unverified tags = 1 (testing)
        assert summary["unverified_tags"] == 1
        checks += 1

        # 13: highest rate tag is ml (0.6667 > 0.5)
        assert summary["highest_rate_tag"] == "ml"
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(vbt)
        _ = json.dumps(uv)
        _ = json.dumps(lag)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL, tag TEXT NOT NULL, "
            "score REAL NOT NULL, tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )
        empty = verification_by_tag(conn2)
        assert empty == []
        empty_summary = tag_verification_summary(conn2)
        assert empty_summary["tags_with_citations"] == 0
        checks += 1

    print(
        f"PASS tag_verification_breakdown selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag-verification breakdown analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_bt = sub.add_parser("by-tag",
                          help="Verification rates per tag")
    p_bt.add_argument("--db", default=DEFAULT_DB)
    p_bt.add_argument("--json", action="store_true")

    p_uv = sub.add_parser("unverified",
                           help="Tags with zero verified citations")
    p_uv.add_argument("--db", default=DEFAULT_DB)
    p_uv.add_argument("--json", action="store_true")

    p_lag = sub.add_parser("lag",
                           help="Verification lag per tag")
    p_lag.add_argument("--db", default=DEFAULT_DB)
    p_lag.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Tag-verification statistics")
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

    if args.cmd == "by-tag":
        results = verification_by_tag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:16s}  "
                      f"total={r['total_citations']:3d}  "
                      f"verified={r['verified_citations']:3d}  "
                      f"rate={r['verification_rate']:.3f}")

    elif args.cmd == "unverified":
        results = unverified_tags(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:16s}  "
                      f"citations={r['total_citations']}")

    elif args.cmd == "lag":
        results = verification_lag_by_tag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:16s}  "
                      f"n={r['verified_count']}  "
                      f"mean={r['mean_lag_days']:.1f}d  "
                      f"min={r['min_lag_days']:.1f}d  "
                      f"max={r['max_lag_days']:.1f}d")

    elif args.cmd == "summary":
        result = tag_verification_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tags with citations: "
                  f"{result['tags_with_citations']}  "
                  f"Total: {result['total_tag_citations']}")
            print(f"  Verification rate: "
                  f"{result['overall_verification_rate']:.3f}  "
                  f"Fully verified: "
                  f"{result['fully_verified_tags']}  "
                  f"Unverified: {result['unverified_tags']}")
            if result["highest_rate_tag"]:
                print(f"  Highest rate: "
                      f"{result['highest_rate_tag']}  "
                      f"Lowest: {result['lowest_rate_tag']}")

    conn.close()


if __name__ == "__main__":
    main()
