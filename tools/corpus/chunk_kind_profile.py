#!/usr/bin/env python3
"""Chunk kind profile: distribution of chunk kinds across sources and domains.

Analyses how chunk kinds (claim, code, table, config, link, prose) are
distributed across the corpus, per source, and per domain, revealing
kind-skewed sources and domain-kind associations.

Usage:
    python tools/corpus/chunk_kind_profile.py distribution [--db PATH] [--json]
    python tools/corpus/chunk_kind_profile.py per-source [--db PATH] [--json]
    python tools/corpus/chunk_kind_profile.py per-domain [--db PATH] [--json]
    python tools/corpus/chunk_kind_profile.py summary [--db PATH] [--json]
    python tools/corpus/chunk_kind_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def kind_distribution(conn) -> list[dict]:
    """Corpus-wide chunk kind distribution."""
    rows = conn.execute(
        "SELECT kind, count(*) FROM chunks "
        "WHERE status = 'accepted' "
        "GROUP BY kind"
    ).fetchall()

    if not rows:
        return []

    total = sum(count for _, count in rows)
    results = []
    for kind, count in rows:
        avg_words = conn.execute(
            "SELECT avg(word_count) FROM chunks "
            "WHERE status = 'accepted' AND kind = ?",
            (kind,),
        ).fetchone()[0] or 0

        results.append({
            "kind": kind,
            "count": count,
            "share": round(count / total, 4) if total > 0 else 0.0,
            "avg_word_count": round(avg_words, 1),
        })

    results.sort(key=lambda r: r["count"], reverse=True)
    return results


def per_source_kinds(conn) -> list[dict]:
    """Per-source chunk kind breakdown."""
    sources = conn.execute(
        "SELECT s.source_id, s.title "
        "FROM sources s "
        "JOIN chunks c ON s.source_id = c.source_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY s.source_id"
    ).fetchall()

    if not sources:
        return []

    results = []
    for src_id, title in sources:
        kind_rows = conn.execute(
            "SELECT kind, count(*) FROM chunks "
            "WHERE source_id = ? AND status = 'accepted' "
            "GROUP BY kind",
            (src_id,),
        ).fetchall()

        total = sum(count for _, count in kind_rows)
        kinds = dict(kind_rows)
        dominant = max(kind_rows, key=lambda r: r[1])[0] if kind_rows else ""
        dominant_share = round(kinds.get(dominant, 0) / total, 4) if total > 0 else 0.0

        results.append({
            "source_id": src_id,
            "title": title,
            "total_chunks": total,
            "kinds": kinds,
            "kind_count": len(kinds),
            "dominant_kind": dominant,
            "dominant_share": dominant_share,
        })

    results.sort(key=lambda r: r["dominant_share"], reverse=True)
    return results


def per_domain_kinds(conn) -> list[dict]:
    """Per-domain chunk kind breakdown (requires chunk_domains table)."""
    try:
        conn.execute("SELECT 1 FROM chunk_domains LIMIT 1")
    except Exception:
        return []

    domains = conn.execute(
        "SELECT DISTINCT domain FROM chunk_domains"
    ).fetchall()

    if not domains:
        return []

    results = []
    for (domain,) in domains:
        kind_rows = conn.execute(
            "SELECT c.kind, count(*) "
            "FROM chunk_domains cd "
            "JOIN chunks c ON cd.chunk_id = c.chunk_id "
            "WHERE cd.domain = ? AND c.status = 'accepted' "
            "GROUP BY c.kind",
            (domain,),
        ).fetchall()

        total = sum(count for _, count in kind_rows)
        kinds = dict(kind_rows)
        dominant = max(kind_rows, key=lambda r: r[1])[0] if kind_rows else ""
        dominant_share = round(kinds.get(dominant, 0) / total, 4) if total > 0 else 0.0

        results.append({
            "domain": domain,
            "total_chunks": total,
            "kinds": kinds,
            "kind_count": len(kinds),
            "dominant_kind": dominant,
            "dominant_share": dominant_share,
        })

    results.sort(key=lambda r: r["total_chunks"], reverse=True)
    return results


def kind_profile_summary(conn) -> dict:
    """Aggregate chunk kind profile statistics."""
    dist = kind_distribution(conn)

    if not dist:
        return {
            "total_accepted": 0,
            "unique_kinds": 0,
            "dominant_kind": "",
            "dominant_share": 0.0,
            "single_kind_sources": 0,
            "multi_kind_sources": 0,
            "mean_kinds_per_source": 0.0,
        }

    total = sum(d["count"] for d in dist)
    dominant = dist[0] if dist else {"kind": "", "share": 0.0}

    per_src = per_source_kinds(conn)
    single_kind = sum(1 for s in per_src if s["kind_count"] == 1)
    multi_kind = sum(1 for s in per_src if s["kind_count"] > 1)
    mean_kinds = (
        round(sum(s["kind_count"] for s in per_src) / len(per_src), 2)
        if per_src else 0.0
    )

    return {
        "total_accepted": total,
        "unique_kinds": len(dist),
        "dominant_kind": dominant["kind"],
        "dominant_share": dominant["share"],
        "single_kind_sources": single_kind,
        "multi_kind_sources": multi_kind,
        "mean_kinds_per_source": mean_kinds,
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

        chunks = [
            ("c0", "s1", "claim", 20), ("c1", "s1", "claim", 15),
            ("c2", "s1", "code", 30), ("c3", "s1", "prose", 50),
            ("c4", "s2", "claim", 10), ("c5", "s2", "claim", 25),
            ("c6", "s2", "claim", 12),
        ]
        for i, (cid, sid, kind, wc) in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, i, f"Heading {i}", kind, "en",
                 f"text {i}", f"text {i}", wc, f"n_{cid}",
                 "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains "
            "(chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        for cid, domain in [("c0", "ml"), ("c1", "ml"), ("c2", "ml"),
                            ("c3", "nlp"), ("c4", "nlp"), ("c5", "ml")]:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)",
                (cid, domain, 0.9, now),
            )

        conn.commit()

        # 1: distribution returns all kinds
        dist = kind_distribution(conn)
        kind_set = {d["kind"] for d in dist}
        assert kind_set == {"claim", "code", "prose"}
        checks += 1

        # 2: shares sum to approximately 1.0
        total_share = sum(d["share"] for d in dist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: claim is dominant kind (4 chunks)
        assert dist[0]["kind"] == "claim"
        assert dist[0]["count"] == 5
        checks += 1

        # 4: avg_word_count is positive
        assert all(d["avg_word_count"] > 0 for d in dist)
        checks += 1

        # 5: per-source returns both sources
        per_src = per_source_kinds(conn)
        assert len(per_src) == 2
        checks += 1

        # 6: s1 has 3 kinds, s2 has 1 kind
        s1 = next(s for s in per_src if s["source_id"] == "s1")
        s2 = next(s for s in per_src if s["source_id"] == "s2")
        assert s1["kind_count"] == 3
        assert s2["kind_count"] == 1
        checks += 1

        # 7: s2 dominant kind is claim at 100%
        assert s2["dominant_kind"] == "claim"
        assert s2["dominant_share"] == 1.0
        checks += 1

        # 8: per-domain returns both domains
        per_dom = per_domain_kinds(conn)
        dom_set = {d["domain"] for d in per_dom}
        assert dom_set == {"ml", "nlp"}
        checks += 1

        # 9: ml domain has claim and code kinds
        ml = next(d for d in per_dom if d["domain"] == "ml")
        assert "claim" in ml["kinds"]
        checks += 1

        # 10: sorted by total_chunks descending
        totals = [d["total_chunks"] for d in per_dom]
        assert totals == sorted(totals, reverse=True)
        checks += 1

        # 11: summary has required keys
        summary = kind_profile_summary(conn)
        assert summary["total_accepted"] == 7
        assert summary["unique_kinds"] == 3
        assert summary["dominant_kind"] == "claim"
        checks += 1

        # 12: single + multi kind sources = total sources
        assert (summary["single_kind_sources"]
                + summary["multi_kind_sources"]) == 2
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(per_src)
        _ = json.dumps(per_dom)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = kind_distribution(conn2)
        assert empty == []
        empty_summary = kind_profile_summary(conn2)
        assert empty_summary["total_accepted"] == 0
        checks += 1

    print(f"PASS chunk_kind_profile selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk kind profile: kind distribution across sources and domains"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Corpus-wide chunk kind distribution")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_src = sub.add_parser("per-source",
                           help="Per-source kind breakdown")
    p_src.add_argument("--db", default=DEFAULT_DB)
    p_src.add_argument("--json", action="store_true")

    p_dom = sub.add_parser("per-domain",
                           help="Per-domain kind breakdown")
    p_dom.add_argument("--db", default=DEFAULT_DB)
    p_dom.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Kind profile statistics")
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

    if args.cmd == "distribution":
        results = kind_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['kind']:8s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  avg {r['avg_word_count']:.0f}w  {bar}")

    elif args.cmd == "per-source":
        results = per_source_kinds(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                kinds_str = ", ".join(
                    f"{k}:{v}" for k, v in sorted(r["kinds"].items())
                )
                print(f"  {r['dominant_share']:5.1%}  {r['dominant_kind']:8s}  "
                      f"{r['source_id'][:12]:12s}  {kinds_str}")

    elif args.cmd == "per-domain":
        results = per_domain_kinds(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No domain classifications found.")
            else:
                for r in results:
                    kinds_str = ", ".join(
                        f"{k}:{v}" for k, v in sorted(r["kinds"].items())
                    )
                    print(f"  {r['domain']:15s}  {r['total_chunks']:4d} chunks  "
                          f"{r['dominant_kind']:8s}  {kinds_str}")

    elif args.cmd == "summary":
        result = kind_profile_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunk Kinds: {result['unique_kinds']} kinds, "
                  f"{result['total_accepted']} accepted chunks")
            print(f"  Dominant: {result['dominant_kind']} "
                  f"({result['dominant_share']:.1%})")
            print(f"  Sources: {result['single_kind_sources']} single-kind, "
                  f"{result['multi_kind_sources']} multi-kind  "
                  f"Mean kinds/source: {result['mean_kinds_per_source']:.1f}")

    conn.close()


if __name__ == "__main__":
    main()
