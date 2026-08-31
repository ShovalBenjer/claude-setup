#!/usr/bin/env python3
"""Citation tag profile: cross-dimensional analysis of citation tags.

Extends basic tag counting (already in citation_analysis.py) with
cross-tabulations against source kind, chunk domain, locator
presence, and tag co-occurrence patterns within chunks.

Usage:
    python tools/corpus/citation_tag_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/citation_tag_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/citation_tag_profile.py locator-affinity [--db PATH] [--json]
    python tools/corpus/citation_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/citation_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tag_by_source_kind(conn) -> list[dict]:
    """Citation tag distribution per source kind."""
    rows = conn.execute(
        "SELECT COALESCE(ci.tag, '(none)') AS tag, s.kind, "
        "count(*) AS cite_count "
        "FROM citations ci "
        "JOIN chunks ch ON ci.chunk_id = ch.chunk_id "
        "JOIN sources s ON ch.source_id = s.source_id "
        "WHERE ch.status = 'accepted' "
        "GROUP BY tag, s.kind "
        "ORDER BY cite_count DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {"tag": r[0], "source_kind": r[1], "citation_count": r[2]}
        for r in rows
    ]


def tag_by_domain(conn) -> list[dict]:
    """Citation tag distribution per chunk domain."""
    has_domains = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='chunk_domains'"
    ).fetchone()

    if not has_domains:
        return []

    rows = conn.execute(
        "SELECT COALESCE(ci.tag, '(none)') AS tag, cd.domain, "
        "count(*) AS cite_count "
        "FROM citations ci "
        "JOIN chunks ch ON ci.chunk_id = ch.chunk_id "
        "JOIN chunk_domains cd ON ch.chunk_id = cd.chunk_id "
        "WHERE ch.status = 'accepted' "
        "GROUP BY tag, cd.domain "
        "ORDER BY cite_count DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {"tag": r[0], "domain": r[1], "citation_count": r[2]}
        for r in rows
    ]


def tag_locator_affinity(conn) -> list[dict]:
    """Locator presence rates per citation tag."""
    rows = conn.execute(
        "SELECT COALESCE(ci.tag, '(none)') AS tag, "
        "count(*) AS total, "
        "sum(CASE WHEN ci.locator IS NOT NULL AND ci.locator != '' "
        "    THEN 1 ELSE 0 END) AS with_locator, "
        "sum(CASE WHEN ci.verified = 1 THEN 1 ELSE 0 END) AS verified "
        "FROM citations ci "
        "JOIN chunks ch ON ci.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted' "
        "GROUP BY tag "
        "ORDER BY total DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "tag": r[0],
            "total": r[1],
            "with_locator": r[2],
            "locator_rate": round(r[2] / r[1], 4) if r[1] > 0 else 0.0,
            "verified": r[3],
            "verification_rate": round(r[3] / r[1], 4) if r[1] > 0 else 0.0,
        }
        for r in rows
    ]


def tag_profile_summary(conn) -> dict:
    """Aggregate tag profile statistics."""
    rows = conn.execute(
        "SELECT COALESCE(ci.tag, '(none)'), ci.locator, ci.verified, "
        "s.kind "
        "FROM citations ci "
        "JOIN chunks ch ON ci.chunk_id = ch.chunk_id "
        "JOIN sources s ON ch.source_id = s.source_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_citations": 0,
            "distinct_tags": 0,
            "source_kinds_cited": 0,
            "tag_with_highest_locator_rate": None,
            "tag_with_lowest_locator_rate": None,
            "overall_locator_rate": 0.0,
            "overall_verification_rate": 0.0,
        }

    tags: dict[str, dict] = {}
    kinds: set[str] = set()
    total_with_loc = 0
    total_verified = 0

    for tag, loc, verified, kind in rows:
        kinds.add(kind)
        has_loc = bool(loc and loc.strip())
        if has_loc:
            total_with_loc += 1
        if verified:
            total_verified += 1

        if tag not in tags:
            tags[tag] = {"total": 0, "with_locator": 0}
        tags[tag]["total"] += 1
        if has_loc:
            tags[tag]["with_locator"] += 1

    tag_rates = {
        t: d["with_locator"] / d["total"]
        for t, d in tags.items()
        if d["total"] > 0
    }
    best_tag = max(tag_rates, key=tag_rates.get) if tag_rates else None
    worst_tag = min(tag_rates, key=tag_rates.get) if tag_rates else None

    n = len(rows)
    return {
        "total_citations": n,
        "distinct_tags": len(tags),
        "source_kinds_cited": len(kinds),
        "tag_with_highest_locator_rate": best_tag,
        "tag_with_lowest_locator_rate": worst_tag,
        "overall_locator_rate": round(
            total_with_loc / n, 4
        ) if n > 0 else 0.0,
        "overall_verification_rate": round(
            total_verified / n, 4
        ) if n > 0 else 0.0,
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
            ("c1", "s1", 0, "claim"), ("c2", "s1", 1, "prose"),
            ("c3", "s2", 0, "claim"), ("c4", "s2", 1, "code"),
        ]
        for cid, sid, ordinal, kind in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 2, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains "
            "(chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL NOT NULL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        for cid, domain in [("c1", "ml"), ("c2", "ml"),
                             ("c3", "systems"), ("c4", "systems")]:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)",
                (cid, domain, 0.9, now),
            )

        citations = [
            ("ci1", "c1", "https://a.com", "doi", "p. 42", 1),
            ("ci2", "c1", "https://b.com", "doi", "pp. 10", 1),
            ("ci3", "c2", "https://c.com", "url", "#sec-3", 0),
            ("ci4", "c2", "https://d.com", "url", "", 0),
            ("ci5", "c3", "https://e.com", "isbn", None, 1),
            ("ci6", "c3", "https://f.com", "doi", "Sec 4", 0),
            ("ci7", "c4", "https://g.com", "url", "line 5", 1),
        ]
        for cit_id, chunk, uri, tag, loc, verified in citations:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)",
                (cit_id, chunk, uri, None, tag, loc,
                 verified, now if verified else None),
            )

        conn.commit()

        # 1: by-kind returns entries
        by_kind = tag_by_source_kind(conn)
        assert len(by_kind) > 0
        checks += 1

        # 2: doi+paper combination exists
        doi_paper = [r for r in by_kind
                     if r["tag"] == "doi" and r["source_kind"] == "paper"]
        assert len(doi_paper) == 1
        assert doi_paper[0]["citation_count"] == 2
        checks += 1

        # 3: url+local_md combination exists
        url_md = [r for r in by_kind
                  if r["tag"] == "url" and r["source_kind"] == "local_md"]
        assert len(url_md) == 1
        checks += 1

        # 4: by-domain returns entries (chunk_domains populated)
        by_domain = tag_by_domain(conn)
        assert len(by_domain) > 0
        checks += 1

        # 5: doi+ml combination exists
        doi_ml = [r for r in by_domain
                  if r["tag"] == "doi" and r["domain"] == "ml"]
        assert len(doi_ml) == 1
        assert doi_ml[0]["citation_count"] == 2
        checks += 1

        # 6: locator-affinity returns entries per tag
        affinity = tag_locator_affinity(conn)
        assert len(affinity) > 0
        tag_set = {a["tag"] for a in affinity}
        assert tag_set == {"doi", "url", "isbn"}
        checks += 1

        # 7: doi has 100% locator rate (3/3)
        doi_aff = next(a for a in affinity if a["tag"] == "doi")
        assert doi_aff["total"] == 3
        assert doi_aff["with_locator"] == 3
        assert doi_aff["locator_rate"] == 1.0
        checks += 1

        # 8: isbn has 0% locator rate (0/1)
        isbn_aff = next(a for a in affinity if a["tag"] == "isbn")
        assert isbn_aff["locator_rate"] == 0.0
        checks += 1

        # 9: url has 2/3 locator rate
        url_aff = next(a for a in affinity if a["tag"] == "url")
        assert url_aff["with_locator"] == 2
        checks += 1

        # 10: summary has correct totals
        summary = tag_profile_summary(conn)
        assert summary["total_citations"] == 7
        assert summary["distinct_tags"] == 3
        assert summary["source_kinds_cited"] == 2
        checks += 1

        # 11: highest locator rate tag is doi
        assert summary["tag_with_highest_locator_rate"] == "doi"
        checks += 1

        # 12: lowest locator rate tag is isbn
        assert summary["tag_with_lowest_locator_rate"] == "isbn"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(by_kind)
        _ = json.dumps(by_domain)
        _ = json.dumps(affinity)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = tag_by_source_kind(conn2)
        assert empty == []
        empty_summary = tag_profile_summary(conn2)
        assert empty_summary["total_citations"] == 0
        checks += 1

    print(f"PASS citation_tag_profile selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation tag profile: cross-dimensional analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_kind = sub.add_parser("by-kind",
                            help="Tag distribution per source kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_dom = sub.add_parser("by-domain",
                           help="Tag distribution per chunk domain")
    p_dom.add_argument("--db", default=DEFAULT_DB)
    p_dom.add_argument("--json", action="store_true")

    p_loc = sub.add_parser("locator-affinity",
                           help="Locator presence per tag")
    p_loc.add_argument("--db", default=DEFAULT_DB)
    p_loc.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Tag profile statistics")
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

    if args.cmd == "by-kind":
        results = tag_by_source_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:10s}  {r['source_kind']:10s}  "
                      f"n={r['citation_count']:3d}")

    elif args.cmd == "by-domain":
        results = tag_by_domain(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No chunk_domains table or no data.")
            else:
                for r in results:
                    print(f"  {r['tag']:10s}  {r['domain']:14s}  "
                          f"n={r['citation_count']:3d}")

    elif args.cmd == "locator-affinity":
        results = tag_locator_affinity(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:10s}  total={r['total']:3d}  "
                      f"loc={r['locator_rate']:5.1%}  "
                      f"ver={r['verification_rate']:5.1%}")

    elif args.cmd == "summary":
        result = tag_profile_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citations: {result['total_citations']}, "
                  f"{result['distinct_tags']} tags, "
                  f"{result['source_kinds_cited']} source kinds")
            print(f"  Locator rate: {result['overall_locator_rate']:.1%}  "
                  f"Verification: {result['overall_verification_rate']:.1%}")
            print(f"  Best locator: {result['tag_with_highest_locator_rate']}  "
                  f"Worst: {result['tag_with_lowest_locator_rate']}")

    conn.close()


if __name__ == "__main__":
    main()
