#!/usr/bin/env python3
"""Cross-reference density: internal vs external citation patterns.

Measures how densely chunks cite other chunks within the same source
versus across sources, revealing self-contained documents versus
outward-linking ones.

Usage:
    python tools/corpus/cross_ref_density.py density [--db PATH] [--json]
    python tools/corpus/cross_ref_density.py insular [--db PATH] [--threshold F] [--json]
    python tools/corpus/cross_ref_density.py summary [--db PATH] [--json]
    python tools/corpus/cross_ref_density.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def cross_ref_density(conn) -> list[dict]:
    """Per-source internal vs external citation density."""
    sources = conn.execute(
        "SELECT s.source_id, s.title, "
        "count(DISTINCT c.chunk_id) as chunk_count "
        "FROM sources s "
        "JOIN chunks c ON s.source_id = c.source_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY s.source_id"
    ).fetchall()

    if not sources:
        return []

    source_uris = dict(conn.execute(
        "SELECT source_id, canonical_uri FROM sources"
    ).fetchall())

    results = []
    for src_id, title, chunk_count in sources:
        internal = conn.execute(
            "SELECT count(*) FROM citations cit "
            "JOIN chunks c ON cit.chunk_id = c.chunk_id "
            "WHERE c.source_id = ? AND c.status = 'accepted' "
            "AND (cit.target_source_id = ? "
            "OR cit.target_uri = ?)",
            (src_id, src_id, source_uris.get(src_id, "")),
        ).fetchone()[0]

        total = conn.execute(
            "SELECT count(*) FROM citations cit "
            "JOIN chunks c ON cit.chunk_id = c.chunk_id "
            "WHERE c.source_id = ? AND c.status = 'accepted'",
            (src_id,),
        ).fetchone()[0]

        external = total - internal

        internal_rate = internal / chunk_count if chunk_count > 0 else 0.0
        external_rate = external / chunk_count if chunk_count > 0 else 0.0
        insularity = internal / total if total > 0 else 0.0

        results.append({
            "source_id": src_id,
            "title": title,
            "chunk_count": chunk_count,
            "internal_citations": internal,
            "external_citations": external,
            "total_citations": total,
            "internal_rate": round(internal_rate, 4),
            "external_rate": round(external_rate, 4),
            "insularity": round(insularity, 4),
        })

    results.sort(key=lambda r: r["total_citations"], reverse=True)
    return results


def insular_sources(conn, threshold: float = 0.7) -> list[dict]:
    """Sources where insularity (internal/total) exceeds threshold."""
    all_dens = cross_ref_density(conn)
    insular = [d for d in all_dens
               if d["total_citations"] > 0 and d["insularity"] > threshold]
    insular.sort(key=lambda d: d["insularity"], reverse=True)
    return insular


def cross_ref_summary(conn) -> dict:
    """Aggregate cross-reference density statistics."""
    all_dens = cross_ref_density(conn)

    if not all_dens:
        return {
            "total_sources": 0,
            "sources_with_citations": 0,
            "total_internal": 0,
            "total_external": 0,
            "overall_insularity": 0.0,
            "mean_internal_rate": 0.0,
            "mean_external_rate": 0.0,
            "highly_insular": 0,
            "highly_outward": 0,
        }

    with_cites = [d for d in all_dens if d["total_citations"] > 0]

    total_internal = sum(d["internal_citations"] for d in all_dens)
    total_external = sum(d["external_citations"] for d in all_dens)
    total_all = total_internal + total_external

    overall_insularity = (
        total_internal / total_all if total_all > 0 else 0.0
    )

    int_rates = [d["internal_rate"] for d in with_cites]
    ext_rates = [d["external_rate"] for d in with_cites]

    mean_int = round(
        sum(int_rates) / len(int_rates), 4
    ) if int_rates else 0.0
    mean_ext = round(
        sum(ext_rates) / len(ext_rates), 4
    ) if ext_rates else 0.0

    highly_insular = sum(
        1 for d in with_cites if d["insularity"] > 0.7
    )
    highly_outward = sum(
        1 for d in with_cites if d["insularity"] < 0.3
    )

    return {
        "total_sources": len(all_dens),
        "sources_with_citations": len(with_cites),
        "total_internal": total_internal,
        "total_external": total_external,
        "overall_insularity": round(overall_insularity, 4),
        "mean_internal_rate": mean_int,
        "mean_external_rate": mean_ext,
        "highly_insular": highly_insular,
        "highly_outward": highly_outward,
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

        for sid, uri in [("s1", "https://s1.com"), ("s2", "https://s2.com")]:
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

        chunk_data = [
            ("c0", "s1"), ("c1", "s1"), ("c2", "s1"),
            ("c3", "s2"), ("c4", "s2"),
        ]
        for i, (cid, sid) in enumerate(chunk_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_{cid}",
                 "accepted", now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit1", "c0", "https://s1.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit2", "c1", "https://s1.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit3", "c1", "https://s2.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit4", "c3", "https://s1.com", "ref", 1, now),
        )

        conn.commit()

        # 1: density returns both sources
        dens = cross_ref_density(conn)
        assert len(dens) == 2
        checks += 1

        # 2: s1 has 2 internal + 1 external citations
        s1 = next(d for d in dens if d["source_id"] == "s1")
        assert s1["internal_citations"] == 2
        assert s1["external_citations"] == 1
        assert s1["total_citations"] == 3
        checks += 1

        # 3: s2 has 0 internal + 1 external
        s2 = next(d for d in dens if d["source_id"] == "s2")
        assert s2["internal_citations"] == 0
        assert s2["external_citations"] == 1
        checks += 1

        # 4: insularity is correct for s1
        expected = 2 / 3
        assert abs(s1["insularity"] - expected) < 0.01
        checks += 1

        # 5: s2 insularity is 0 (all external)
        assert s2["insularity"] == 0.0
        checks += 1

        # 6: sorted by total_citations descending
        totals = [d["total_citations"] for d in dens]
        assert totals == sorted(totals, reverse=True)
        checks += 1

        # 7: insular sources with low threshold
        insular = insular_sources(conn, threshold=0.5)
        insular_ids = [d["source_id"] for d in insular]
        assert "s1" in insular_ids
        assert "s2" not in insular_ids
        checks += 1

        # 8: high threshold returns fewer
        insular_high = insular_sources(conn, threshold=0.9)
        assert len(insular_high) <= len(insular)
        checks += 1

        # 9: summary has required keys
        summary = cross_ref_summary(conn)
        assert summary["total_sources"] == 2
        assert summary["sources_with_citations"] == 2
        checks += 1

        # 10: internal + external = total
        assert (summary["total_internal"]
                + summary["total_external"]) == 4
        checks += 1

        # 11: overall insularity between 0 and 1
        assert 0 <= summary["overall_insularity"] <= 1.0
        checks += 1

        # 12: rates are non-negative
        assert summary["mean_internal_rate"] >= 0
        assert summary["mean_external_rate"] >= 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dens)
        _ = json.dumps(insular)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = cross_ref_density(conn2)
        assert empty == []
        empty_summary = cross_ref_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS cross_ref_density selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-reference density: internal vs external citations"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dens = sub.add_parser("density",
                            help="Per-source internal vs external citations")
    p_dens.add_argument("--db", default=DEFAULT_DB)
    p_dens.add_argument("--json", action="store_true")

    p_ins = sub.add_parser("insular",
                           help="Highly self-referencing sources")
    p_ins.add_argument("--db", default=DEFAULT_DB)
    p_ins.add_argument("--threshold", type=float, default=0.7)
    p_ins.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Cross-reference statistics")
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

    if args.cmd == "density":
        results = cross_ref_density(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  int:{r['internal_citations']:3d}  "
                      f"ext:{r['external_citations']:3d}  "
                      f"ins:{r['insularity']:.2f}  "
                      f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "insular":
        results = insular_sources(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No highly insular sources found.")
            else:
                print(f"{len(results)} insular sources "
                      f"(insularity > {args.threshold:.2f}):")
                for d in results:
                    print(f"  {d['insularity']:.2f}  "
                          f"{d['internal_citations']:3d}/{d['total_citations']:3d}  "
                          f"{d['source_id'][:12]:12s}  {d['title'][:30]}")

    elif args.cmd == "summary":
        result = cross_ref_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cross-Reference: {result['total_internal']} internal, "
                  f"{result['total_external']} external citations")
            print(f"  Overall insularity: {result['overall_insularity']:.2%}")
            print(f"  Highly insular: {result['highly_insular']}  "
                  f"Highly outward: {result['highly_outward']}")

    conn.close()


if __name__ == "__main__":
    main()
