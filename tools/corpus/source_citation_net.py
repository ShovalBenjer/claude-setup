#!/usr/bin/env python3
"""Source citation network: source-to-source citation graph.

Aggregates chunk-level citations up to source pairs, revealing which
sources cite which other sources and computing source-level network
metrics (in-degree, out-degree, mutual citation pairs).

Usage:
    python tools/corpus/source_citation_net.py links [--db PATH] [--json]
    python tools/corpus/source_citation_net.py ranks [--db PATH] [--json]
    python tools/corpus/source_citation_net.py summary [--db PATH] [--json]
    python tools/corpus/source_citation_net.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def source_links(conn) -> list[dict]:
    """Source-to-source citation links with citation counts.

    A link from source A to source B means chunks in A cite a target_uri
    that matches source B's canonical_uri, or citations with
    target_source_id pointing to B.
    """
    rows = conn.execute(
        "SELECT c.source_id as citing_source, "
        "COALESCE(cit.target_source_id, s2.source_id) as cited_source, "
        "count(*) as citation_count "
        "FROM citations cit "
        "JOIN chunks c ON cit.chunk_id = c.chunk_id "
        "LEFT JOIN sources s2 ON cit.target_uri = s2.canonical_uri "
        "WHERE c.status = 'accepted' "
        "AND COALESCE(cit.target_source_id, s2.source_id) IS NOT NULL "
        "AND c.source_id != COALESCE(cit.target_source_id, s2.source_id) "
        "GROUP BY citing_source, cited_source "
        "ORDER BY citation_count DESC"
    ).fetchall()

    if not rows:
        return []

    source_titles = dict(conn.execute(
        "SELECT source_id, title FROM sources"
    ).fetchall())

    results = []
    for citing, cited, count in rows:
        results.append({
            "citing_source": citing,
            "citing_title": source_titles.get(citing, ""),
            "cited_source": cited,
            "cited_title": source_titles.get(cited, ""),
            "citation_count": count,
        })

    return results


def source_ranks(conn) -> list[dict]:
    """Source-level network metrics: in-degree, out-degree, net citations."""
    links = source_links(conn)

    if not links:
        return []

    in_deg: dict[str, int] = {}
    out_deg: dict[str, int] = {}
    in_weight: dict[str, int] = {}
    out_weight: dict[str, int] = {}

    all_sources: set[str] = set()
    for lnk in links:
        citing = lnk["citing_source"]
        cited = lnk["cited_source"]
        count = lnk["citation_count"]

        all_sources.add(citing)
        all_sources.add(cited)

        out_deg[citing] = out_deg.get(citing, 0) + 1
        in_deg[cited] = in_deg.get(cited, 0) + 1
        out_weight[citing] = out_weight.get(citing, 0) + count
        in_weight[cited] = in_weight.get(cited, 0) + count

    source_titles = dict(conn.execute(
        "SELECT source_id, title FROM sources"
    ).fetchall())

    citing_set = {lnk["citing_source"] for lnk in links}
    cited_set = {lnk["cited_source"] for lnk in links}
    mutual = citing_set & cited_set

    results = []
    for sid in all_sources:
        ind = in_deg.get(sid, 0)
        outd = out_deg.get(sid, 0)
        results.append({
            "source_id": sid,
            "title": source_titles.get(sid, ""),
            "in_degree": ind,
            "out_degree": outd,
            "in_citations": in_weight.get(sid, 0),
            "out_citations": out_weight.get(sid, 0),
            "net_citations": in_weight.get(sid, 0) - out_weight.get(sid, 0),
            "is_mutual": sid in mutual,
        })

    results.sort(key=lambda r: r["in_citations"], reverse=True)
    return results


def citation_net_summary(conn) -> dict:
    """Aggregate source citation network statistics."""
    links = source_links(conn)
    ranks = source_ranks(conn)

    if not links:
        return {
            "total_source_links": 0,
            "total_citations_across_sources": 0,
            "sources_citing": 0,
            "sources_cited": 0,
            "mutual_pairs": 0,
            "isolated_sources": 0,
            "most_cited": None,
            "most_citing": None,
            "mean_in_degree": 0.0,
            "mean_out_degree": 0.0,
        }

    total_cites = sum(lnk["citation_count"] for lnk in links)
    citing_ids = {lnk["citing_source"] for lnk in links}
    cited_ids = {lnk["cited_source"] for lnk in links}
    mutual = citing_ids & cited_ids

    total_sources = conn.execute(
        "SELECT count(*) FROM sources"
    ).fetchone()[0]
    participating = citing_ids | cited_ids
    isolated = total_sources - len(participating)

    most_cited = max(ranks, key=lambda r: r["in_citations"])
    most_citing = max(ranks, key=lambda r: r["out_citations"])

    in_degs = [r["in_degree"] for r in ranks]
    out_degs = [r["out_degree"] for r in ranks]

    return {
        "total_source_links": len(links),
        "total_citations_across_sources": total_cites,
        "sources_citing": len(citing_ids),
        "sources_cited": len(cited_ids),
        "mutual_pairs": len(mutual),
        "isolated_sources": max(isolated, 0),
        "most_cited": most_cited["source_id"],
        "most_citing": most_citing["source_id"],
        "mean_in_degree": round(sum(in_degs) / len(in_degs), 2),
        "mean_out_degree": round(sum(out_degs) / len(out_degs), 2),
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

        for sid, uri in [("s1", "https://s1.com"), ("s2", "https://s2.com"),
                         ("s3", "https://s3.com")]:
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

        for i, sid in enumerate(["s1", "s1", "s2", "s2", "s3"]):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", sid, i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit1", "c0", "https://s2.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit2", "c1", "https://s2.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit3", "c2", "https://s1.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit4", "c3", "https://s3.com", "ref", 0, None),
        )

        conn.commit()

        # 1: links returns source-to-source pairs
        links = source_links(conn)
        assert len(links) >= 2
        checks += 1

        # 2: s1->s2 link exists with count 2
        s1_s2 = [l for l in links
                 if l["citing_source"] == "s1" and l["cited_source"] == "s2"]
        assert len(s1_s2) == 1
        assert s1_s2[0]["citation_count"] == 2
        checks += 1

        # 3: s2->s1 link exists (mutual citation)
        s2_s1 = [l for l in links
                 if l["citing_source"] == "s2" and l["cited_source"] == "s1"]
        assert len(s2_s1) == 1
        checks += 1

        # 4: no self-citations in links
        self_cites = [l for l in links
                      if l["citing_source"] == l["cited_source"]]
        assert len(self_cites) == 0
        checks += 1

        # 5: sorted by citation_count descending
        counts = [l["citation_count"] for l in links]
        assert counts == sorted(counts, reverse=True)
        checks += 1

        # 6: ranks returns all participating sources
        ranks = source_ranks(conn)
        rank_ids = {r["source_id"] for r in ranks}
        assert "s1" in rank_ids
        assert "s2" in rank_ids
        checks += 1

        # 7: s2 has highest in_citations (cited by s1 twice)
        s2_rank = next(r for r in ranks if r["source_id"] == "s2")
        assert s2_rank["in_citations"] >= 2
        checks += 1

        # 8: mutual flag is correct for s1 and s2
        s1_rank = next(r for r in ranks if r["source_id"] == "s1")
        assert s1_rank["is_mutual"] is True
        assert s2_rank["is_mutual"] is True
        checks += 1

        # 9: ranks sorted by in_citations descending
        in_cites = [r["in_citations"] for r in ranks]
        assert in_cites == sorted(in_cites, reverse=True)
        checks += 1

        # 10: summary has required keys
        summary = citation_net_summary(conn)
        assert summary["total_source_links"] >= 2
        assert summary["total_citations_across_sources"] >= 3
        checks += 1

        # 11: mutual pairs counted
        assert summary["mutual_pairs"] >= 2
        checks += 1

        # 12: most_cited is s2
        assert summary["most_cited"] == "s2"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(links)
        _ = json.dumps(ranks)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = source_links(conn2)
        assert empty == []
        empty_summary = citation_net_summary(conn2)
        assert empty_summary["total_source_links"] == 0
        checks += 1

    print(f"PASS source_citation_net selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source citation network: source-to-source citations"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_links = sub.add_parser("links",
                             help="Source-to-source citation links")
    p_links.add_argument("--db", default=DEFAULT_DB)
    p_links.add_argument("--json", action="store_true")

    p_ranks = sub.add_parser("ranks",
                             help="Source-level network metrics")
    p_ranks.add_argument("--db", default=DEFAULT_DB)
    p_ranks.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Network statistics")
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

    if args.cmd == "links":
        results = source_links(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['citation_count']:3d}  "
                      f"{r['citing_source'][:12]:12s} -> "
                      f"{r['cited_source'][:12]:12s}  "
                      f"{r['citing_title'][:20]} -> {r['cited_title'][:20]}")

    elif args.cmd == "ranks":
        results = source_ranks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                mut = "M" if r["is_mutual"] else " "
                print(f"  in:{r['in_citations']:3d}  out:{r['out_citations']:3d}  "
                      f"net:{r['net_citations']:+4d}  [{mut}]  "
                      f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "summary":
        result = citation_net_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Source Citation Network: {result['total_source_links']} links, "
                  f"{result['total_citations_across_sources']} citations")
            print(f"  Citing: {result['sources_citing']}  "
                  f"Cited: {result['sources_cited']}  "
                  f"Mutual: {result['mutual_pairs']}  "
                  f"Isolated: {result['isolated_sources']}")
            if result["most_cited"]:
                print(f"  Most cited: {result['most_cited']}  "
                      f"Most citing: {result['most_citing']}")

    conn.close()


if __name__ == "__main__":
    main()
