#!/usr/bin/env python3
"""Domain-tag affinity: which tags characterise which domains.

Joins chunk_domains and chunk_tags to reveal which tags concentrate in
specific domains, which domains a tag spans, and how well the tag
vocabulary discriminates between domains.

Usage:
    python tools/corpus/domain_tag_affinity.py affinity [--db PATH] [--json]
    python tools/corpus/domain_tag_affinity.py spanning [--db PATH] [--json]
    python tools/corpus/domain_tag_affinity.py summary [--db PATH] [--json]
    python tools/corpus/domain_tag_affinity.py selftest
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


def _tables_exist(conn) -> bool:
    for name in ("chunk_domains", "chunk_tags"):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        if row is None:
            return False
    return True


def domain_tag_affinity(conn) -> list[dict]:
    """Per-domain tag affinities: tags disproportionately present in a domain.

    For each (domain, tag) pair, computes:
      observed = chunks carrying both this domain and this tag
      expected = (domain_size * tag_size) / total_tagged_chunks
      affinity = log2(observed / expected)  (positive = over-represented)
    """
    if not _tables_exist(conn):
        return []

    total_tagged = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]

    if total_tagged == 0:
        return []

    pairs = conn.execute(
        "SELECT d.domain, t.tag, count(DISTINCT d.chunk_id) as co_count "
        "FROM chunk_domains d "
        "JOIN chunk_tags t ON d.chunk_id = t.chunk_id "
        "GROUP BY d.domain, t.tag "
        "HAVING co_count > 0"
    ).fetchall()

    if not pairs:
        return []

    domain_sizes = dict(conn.execute(
        "SELECT domain, count(DISTINCT chunk_id) FROM chunk_domains "
        "GROUP BY domain"
    ).fetchall())

    tag_sizes = dict(conn.execute(
        "SELECT tag, count(DISTINCT chunk_id) FROM chunk_tags "
        "GROUP BY tag"
    ).fetchall())

    results = []
    for domain, tag, co_count in pairs:
        d_size = domain_sizes.get(domain, 0)
        t_size = tag_sizes.get(tag, 0)
        if d_size == 0 or t_size == 0:
            continue

        expected = (d_size * t_size) / total_tagged
        if expected == 0:
            continue

        affinity = math.log2(co_count / expected)

        results.append({
            "domain": domain,
            "tag": tag,
            "co_count": co_count,
            "domain_size": d_size,
            "tag_size": t_size,
            "affinity": round(affinity, 4),
        })

    results.sort(key=lambda r: r["affinity"], reverse=True)
    return results


def spanning_tags(conn) -> list[dict]:
    """Tags that appear across multiple domains, sorted by domain count."""
    if not _tables_exist(conn):
        return []

    rows = conn.execute(
        "SELECT t.tag, count(DISTINCT d.domain) as domain_count, "
        "count(DISTINCT t.chunk_id) as chunk_count "
        "FROM chunk_tags t "
        "JOIN chunk_domains d ON t.chunk_id = d.chunk_id "
        "GROUP BY t.tag "
        "HAVING domain_count > 1 "
        "ORDER BY domain_count DESC, chunk_count DESC"
    ).fetchall()

    results = []
    for tag, domain_count, chunk_count in rows:
        domains = conn.execute(
            "SELECT DISTINCT d.domain FROM chunk_domains d "
            "JOIN chunk_tags t ON d.chunk_id = t.chunk_id "
            "WHERE t.tag = ?", (tag,)
        ).fetchall()

        results.append({
            "tag": tag,
            "domain_count": domain_count,
            "chunk_count": chunk_count,
            "domains": sorted(d[0] for d in domains),
        })

    return results


def affinity_summary(conn) -> dict:
    """Aggregate domain-tag affinity statistics."""
    if not _tables_exist(conn):
        return {
            "total_domains": 0,
            "total_tags": 0,
            "total_pairs": 0,
            "spanning_tags": 0,
            "domain_specific_tags": 0,
            "mean_affinity": 0.0,
            "max_affinity": 0.0,
            "min_affinity": 0.0,
        }

    affinities = domain_tag_affinity(conn)
    spanning = spanning_tags(conn)

    if not affinities:
        return {
            "total_domains": 0,
            "total_tags": 0,
            "total_pairs": 0,
            "spanning_tags": 0,
            "domain_specific_tags": 0,
            "mean_affinity": 0.0,
            "max_affinity": 0.0,
            "min_affinity": 0.0,
        }

    all_domains = {a["domain"] for a in affinities}
    all_tags = {a["tag"] for a in affinities}
    spanning_tag_set = {s["tag"] for s in spanning}
    domain_specific = all_tags - spanning_tag_set

    aff_values = [a["affinity"] for a in affinities]

    return {
        "total_domains": len(all_domains),
        "total_tags": len(all_tags),
        "total_pairs": len(affinities),
        "spanning_tags": len(spanning_tag_set),
        "domain_specific_tags": len(domain_specific),
        "mean_affinity": round(sum(aff_values) / len(aff_values), 4),
        "max_affinity": round(max(aff_values), 4),
        "min_affinity": round(min(aff_values), 4),
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
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        chunk_data = [
            ("c1", "ML heading", "neural networks"),
            ("c2", "DB heading", "postgresql indexing"),
            ("c3", "ML heading 2", "deep learning models"),
            ("c4", "Security heading", "cryptography protocols"),
        ]
        for i, (cid, heading, text) in enumerate(chunk_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", i, heading, "claim", "en",
                 text, text, len(text.split()), f"n_{cid}",
                 "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains "
            "(chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )

        conn.execute("INSERT INTO chunk_domains VALUES (?, ?, ?, ?)",
                     ("c1", "ml", 0.9, now))
        conn.execute("INSERT INTO chunk_domains VALUES (?, ?, ?, ?)",
                     ("c2", "databases", 0.85, now))
        conn.execute("INSERT INTO chunk_domains VALUES (?, ?, ?, ?)",
                     ("c3", "ml", 0.88, now))
        conn.execute("INSERT INTO chunk_domains VALUES (?, ?, ?, ?)",
                     ("c4", "security", 0.92, now))
        conn.execute("INSERT INTO chunk_domains VALUES (?, ?, ?, ?)",
                     ("c1", "databases", 0.3, now))

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c1", "neural", 0.9, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c2", "indexing", 0.85, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c3", "neural", 0.88, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c4", "crypto", 0.92, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c1", "data", 0.5, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c2", "data", 0.6, now))

        conn.commit()

        # 1: affinity returns results
        aff = domain_tag_affinity(conn)
        assert len(aff) > 0
        checks += 1

        # 2: sorted by affinity descending
        aff_vals = [a["affinity"] for a in aff]
        assert aff_vals == sorted(aff_vals, reverse=True)
        checks += 1

        # 3: neural tag has positive affinity with ml domain
        ml_neural = [a for a in aff
                     if a["domain"] == "ml" and a["tag"] == "neural"]
        assert len(ml_neural) == 1
        assert ml_neural[0]["affinity"] > 0
        checks += 1

        # 4: co_count is correct for ml+neural (c1 and c3)
        assert ml_neural[0]["co_count"] == 2
        checks += 1

        # 5: spanning tags returns tags in multiple domains
        span = spanning_tags(conn)
        assert len(span) > 0
        checks += 1

        # 6: data tag spans ml and databases domains
        data_span = [s for s in span if s["tag"] == "data"]
        assert len(data_span) == 1
        assert data_span[0]["domain_count"] >= 2
        checks += 1

        # 7: spanning tag lists its domains
        assert "ml" in data_span[0]["domains"] or \
               "databases" in data_span[0]["domains"]
        checks += 1

        # 8: domain-specific tag not in spanning
        span_tags = {s["tag"] for s in span}
        assert "crypto" not in span_tags
        checks += 1

        # 9: summary has required keys
        summary = affinity_summary(conn)
        assert summary["total_domains"] > 0
        assert summary["total_pairs"] > 0
        assert "spanning_tags" in summary
        assert "domain_specific_tags" in summary
        checks += 1

        # 10: spanning + domain_specific covers all tags
        assert (summary["spanning_tags"]
                + summary["domain_specific_tags"]) == summary["total_tags"]
        checks += 1

        # 11: affinity values span positive and could be negative
        assert summary["max_affinity"] > 0
        checks += 1

        # 12: sorted by domain count descending for spanning
        if len(span) > 1:
            dcounts = [s["domain_count"] for s in span]
            assert dcounts == sorted(dcounts, reverse=True)
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(aff)
        _ = json.dumps(span)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = domain_tag_affinity(conn2)
        assert empty == []
        empty_summary = affinity_summary(conn2)
        assert empty_summary["total_domains"] == 0
        checks += 1

    print(f"PASS domain_tag_affinity selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain-tag affinity: tag vocabulary per domain"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_aff = sub.add_parser("affinity",
                           help="Per-domain tag affinity scores")
    p_aff.add_argument("--db", default=DEFAULT_DB)
    p_aff.add_argument("--json", action="store_true")

    p_span = sub.add_parser("spanning",
                            help="Tags spanning multiple domains")
    p_span.add_argument("--db", default=DEFAULT_DB)
    p_span.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Affinity statistics")
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

    if args.cmd == "affinity":
        results = domain_tag_affinity(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                sign = "+" if r["affinity"] >= 0 else ""
                print(f"  {sign}{r['affinity']:6.2f}  "
                      f"{r['domain']:12s}  {r['tag']:12s}  "
                      f"({r['co_count']} chunks)")

    elif args.cmd == "spanning":
        results = spanning_tags(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No tags span multiple domains.")
            else:
                for s in results:
                    print(f"  {s['tag']:12s}  {s['domain_count']} domains  "
                          f"{s['chunk_count']} chunks  "
                          f"[{', '.join(s['domains'])}]")

    elif args.cmd == "summary":
        result = affinity_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Domain-Tag Affinity: {result['total_pairs']} pairs "
                  f"({result['total_domains']} domains, "
                  f"{result['total_tags']} tags)")
            print(f"  Spanning: {result['spanning_tags']}  "
                  f"Domain-specific: {result['domain_specific_tags']}")
            print(f"  Affinity range: {result['min_affinity']:.2f} to "
                  f"{result['max_affinity']:.2f}  "
                  f"Mean: {result['mean_affinity']:.2f}")

    conn.close()


if __name__ == "__main__":
    main()
