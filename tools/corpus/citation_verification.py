#!/usr/bin/env python3
"""Citation verification rate: verified vs unverified citation patterns.

Analyses what fraction of citations are verified per source, per tag,
and corpus-wide, identifying sources with low verification coverage.

Usage:
    python tools/corpus/citation_verification.py rate [--db PATH] [--json]
    python tools/corpus/citation_verification.py per-tag [--db PATH] [--json]
    python tools/corpus/citation_verification.py unverified [--db PATH] [--threshold F] [--json]
    python tools/corpus/citation_verification.py summary [--db PATH] [--json]
    python tools/corpus/citation_verification.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def verification_rate(conn) -> list[dict]:
    """Per-source citation verification rate."""
    rows = conn.execute(
        "SELECT s.source_id, s.title, "
        "count(cit.citation_id) as total, "
        "sum(CASE WHEN cit.verified = 1 THEN 1 ELSE 0 END) as verified "
        "FROM sources s "
        "JOIN chunks c ON s.source_id = c.source_id "
        "JOIN citations cit ON c.chunk_id = cit.chunk_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY s.source_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for src_id, title, total, verified in rows:
        unverified = total - verified
        rate = round(verified / total, 4) if total > 0 else 0.0

        results.append({
            "source_id": src_id,
            "title": title,
            "total_citations": total,
            "verified": verified,
            "unverified": unverified,
            "verification_rate": rate,
        })

    results.sort(key=lambda r: r["verification_rate"])
    return results


def per_tag_verification(conn) -> list[dict]:
    """Verification rate grouped by citation tag."""
    rows = conn.execute(
        "SELECT COALESCE(cit.tag, '(none)') as tag, "
        "count(cit.citation_id) as total, "
        "sum(CASE WHEN cit.verified = 1 THEN 1 ELSE 0 END) as verified "
        "FROM citations cit "
        "JOIN chunks c ON cit.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY tag"
    ).fetchall()

    if not rows:
        return []

    results = []
    for tag, total, verified in rows:
        rate = round(verified / total, 4) if total > 0 else 0.0
        results.append({
            "tag": tag,
            "total": total,
            "verified": verified,
            "unverified": total - verified,
            "verification_rate": rate,
        })

    results.sort(key=lambda r: r["verification_rate"])
    return results


def unverified_sources(conn, threshold: float = 0.5) -> list[dict]:
    """Sources where verification rate is below threshold."""
    all_rates = verification_rate(conn)
    return [r for r in all_rates if r["verification_rate"] < threshold]


def verification_summary(conn) -> dict:
    """Aggregate citation verification statistics."""
    row = conn.execute(
        "SELECT count(cit.citation_id), "
        "sum(CASE WHEN cit.verified = 1 THEN 1 ELSE 0 END) "
        "FROM citations cit "
        "JOIN chunks c ON cit.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchone()

    total = row[0] or 0
    verified = row[1] or 0

    if total == 0:
        return {
            "total_citations": 0,
            "verified": 0,
            "unverified": 0,
            "overall_rate": 0.0,
            "sources_with_citations": 0,
            "fully_verified_sources": 0,
            "zero_verified_sources": 0,
            "unique_tags": 0,
        }

    per_src = verification_rate(conn)
    fully_verified = sum(1 for s in per_src if s["verification_rate"] == 1.0)
    zero_verified = sum(1 for s in per_src if s["verified"] == 0)

    per_tag = per_tag_verification(conn)

    return {
        "total_citations": total,
        "verified": verified,
        "unverified": total - verified,
        "overall_rate": round(verified / total, 4) if total > 0 else 0.0,
        "sources_with_citations": len(per_src),
        "fully_verified_sources": fully_verified,
        "zero_verified_sources": zero_verified,
        "unique_tags": len(per_tag),
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

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        for i in range(4):
            sid = "s1" if i < 2 else "s2"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", sid, i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        citations = [
            ("ci1", "c0", "https://x.com", "ref", 1),
            ("ci2", "c0", "https://y.com", "ref", 1),
            ("ci3", "c1", "https://z.com", "see", 0),
            ("ci4", "c2", "https://w.com", "ref", 1),
            ("ci5", "c2", "https://v.com", "ref", 0),
            ("ci6", "c3", "https://u.com", "see", 0),
        ]
        for cit_id, chunk_id, uri, tag, verified in citations:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, target_uri, "
                "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
                (cit_id, chunk_id, uri, tag, verified,
                 now if verified else None),
            )

        conn.commit()

        # 1: rate returns both sources
        rates = verification_rate(conn)
        assert len(rates) == 2
        checks += 1

        # 2: s1 has 2/3 verified
        s1 = next(r for r in rates if r["source_id"] == "s1")
        assert s1["verified"] == 2
        assert s1["total_citations"] == 3
        checks += 1

        # 3: s2 has 1/3 verified
        s2 = next(r for r in rates if r["source_id"] == "s2")
        assert s2["verified"] == 1
        assert s2["total_citations"] == 3
        checks += 1

        # 4: sorted by verification_rate ascending
        v_rates = [r["verification_rate"] for r in rates]
        assert v_rates == sorted(v_rates)
        checks += 1

        # 5: per-tag returns both tags
        per_tag = per_tag_verification(conn)
        tags = {t["tag"] for t in per_tag}
        assert tags == {"ref", "see"}
        checks += 1

        # 6: ref tag has higher verification rate than see
        ref = next(t for t in per_tag if t["tag"] == "ref")
        see = next(t for t in per_tag if t["tag"] == "see")
        assert ref["verification_rate"] > see["verification_rate"]
        checks += 1

        # 7: see tag has 0% verification
        assert see["verified"] == 0
        assert see["verification_rate"] == 0.0
        checks += 1

        # 8: unverified with high threshold returns sources
        unv = unverified_sources(conn, threshold=0.8)
        assert len(unv) > 0
        checks += 1

        # 9: unverified with low threshold returns fewer
        unv_low = unverified_sources(conn, threshold=0.1)
        assert len(unv_low) <= len(unv)
        checks += 1

        # 10: summary has required keys
        summary = verification_summary(conn)
        assert summary["total_citations"] == 6
        assert summary["verified"] == 3
        assert summary["unverified"] == 3
        checks += 1

        # 11: overall rate is 0.5
        assert summary["overall_rate"] == 0.5
        checks += 1

        # 12: verified + unverified = total
        assert (summary["verified"]
                + summary["unverified"]) == summary["total_citations"]
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(rates)
        _ = json.dumps(per_tag)
        _ = json.dumps(unv)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = verification_rate(conn2)
        assert empty == []
        empty_summary = verification_summary(conn2)
        assert empty_summary["total_citations"] == 0
        checks += 1

    print(f"PASS citation_verification selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation verification rate: verified vs unverified patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_rate = sub.add_parser("rate",
                            help="Per-source verification rate")
    p_rate.add_argument("--db", default=DEFAULT_DB)
    p_rate.add_argument("--json", action="store_true")

    p_tag = sub.add_parser("per-tag",
                           help="Verification rate per citation tag")
    p_tag.add_argument("--db", default=DEFAULT_DB)
    p_tag.add_argument("--json", action="store_true")

    p_unv = sub.add_parser("unverified",
                           help="Sources with low verification")
    p_unv.add_argument("--db", default=DEFAULT_DB)
    p_unv.add_argument("--threshold", type=float, default=0.5)
    p_unv.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Verification statistics")
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

    if args.cmd == "rate":
        results = verification_rate(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['verification_rate']:5.1%}  "
                      f"{r['verified']:3d}/{r['total_citations']:3d}  "
                      f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "per-tag":
        results = per_tag_verification(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['verification_rate']:5.1%}  "
                      f"{r['verified']:3d}/{r['total']:3d}  "
                      f"{r['tag']}")

    elif args.cmd == "unverified":
        results = unverified_sources(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No low-verification sources found.")
            else:
                print(f"{len(results)} sources with verification "
                      f"< {args.threshold:.0%}:")
                for r in results:
                    print(f"  {r['verification_rate']:5.1%}  "
                          f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "summary":
        result = verification_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citations: {result['total_citations']}  "
                  f"Verified: {result['verified']}  "
                  f"Rate: {result['overall_rate']:.1%}")
            print(f"  Fully verified sources: "
                  f"{result['fully_verified_sources']}  "
                  f"Zero verified: {result['zero_verified_sources']}")
            print(f"  Unique tags: {result['unique_tags']}")

    conn.close()


if __name__ == "__main__":
    main()
