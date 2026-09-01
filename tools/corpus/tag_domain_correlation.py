#!/usr/bin/env python3
"""Tag domain correlation: how chunk tags relate to semantic domains.

tag_citation_yield.py measures tags against citations.
tag_edge_correlation.py measures tags against claim edges.
No tool joins chunk_tags with chunk_domains to measure which tags
co-occur with which domains, whether tag diversity correlates with
domain diversity, or how domain scores vary across tag vocabularies.

Usage:
    python tools/corpus/tag_domain_correlation.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_domain_correlation.py by-domain [--db PATH] [--json]
    python tools/corpus/tag_domain_correlation.py co-occurrence [--db PATH] [--json]
    python tools/corpus/tag_domain_correlation.py summary [--db PATH] [--json]
    python tools/corpus/tag_domain_correlation.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_tag(conn) -> list[dict]:
    """Domain distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               ROUND(AVG(cd.score), 4) AS avg_domain_score
        FROM chunk_tags ct
        JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY domain_assignments DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_domain_score": r[4],
        }
        for r in rows
    ]


def tags_by_domain(conn) -> list[dict]:
    """Tag distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               ROUND(AVG(ct.score), 4) AS avg_tag_score
        FROM chunk_domains cd
        JOIN chunk_tags ct ON ct.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY tag_assignments DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "classified_chunks": r[3],
            "avg_tag_score": r[4],
        }
        for r in rows
    ]


def tag_domain_co_occurrence(conn) -> list[dict]:
    """Co-occurrence counts for each tag-domain pair."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               cd.domain,
               COUNT(DISTINCT ct.chunk_id) AS shared_chunks,
               ROUND(AVG(ct.score), 4) AS avg_tag_score,
               ROUND(AVG(cd.score), 4) AS avg_domain_score
        FROM chunk_tags ct
        JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
        GROUP BY ct.tag, cd.domain
        ORDER BY shared_chunks DESC, ct.tag, cd.domain
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "domain": r[1],
            "shared_chunks": r[2],
            "avg_tag_score": r[3],
            "avg_domain_score": r[4],
        }
        for r in rows
    ]


def tag_domain_summary(conn) -> dict:
    """Aggregate tag-domain co-occurrence statistics."""
    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    tags_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.tag)
        FROM chunk_tags ct
        JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
        """
    ).fetchone()[0]

    domains_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT cd.domain)
        FROM chunk_domains cd
        JOIN chunk_tags ct ON ct.chunk_id = cd.chunk_id
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag, cd.domain
            FROM chunk_tags ct
            JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
            GROUP BY ct.tag, cd.domain
        )
        """
    ).fetchone()[0]

    max_possible_pairs = max(tags_with_domains * domains_with_tags, 1)

    avg_domains_per_tag = conn.execute(
        """
        SELECT ROUND(AVG(dom_count), 4)
        FROM (
            SELECT ct.tag, COUNT(DISTINCT cd.domain) AS dom_count
            FROM chunk_tags ct
            JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
            GROUP BY ct.tag
        )
        """
    ).fetchone()[0]

    return {
        "total_tags": total_tags,
        "total_domains": total_domains,
        "tags_with_domains": tags_with_domains,
        "domains_with_tags": domains_with_tags,
        "distinct_pairs": distinct_pairs,
        "pair_density": round(distinct_pairs / max_possible_pairs, 4),
        "avg_domains_per_tag": avg_domains_per_tag or 0.0,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1: tags(law, tech) + domains(nlp, ml)
        # c2: tags(tech) + domains(ml, cv)
        # c3: tags(bio) + domains(nlp)
        # c4: tags(law) + no domains
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "discussion", "claim", None, "t", "t", 35, "jkl", 4000, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "bio", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "law", 0.6, t1))

        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "ml", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "cv", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "nlp", 0.75, t1))
        conn.commit()

        # 1. by-tag: "tech" co-occurs with 3 domains (nlp, ml via c1; ml, cv via c2)
        bt = domains_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_domains"] == 3, f"expected 3, got {tech['distinct_domains']}"
        ok += 1

        # 2. "law" co-occurs with 2 domains (nlp, ml via c1; c4 has no domains)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_domains"] == 2
        ok += 1

        # 3. "bio" co-occurs with 1 domain (nlp via c3)
        bio = [r for r in bt if r["tag"] == "bio"][0]
        assert bio["distinct_domains"] == 1
        ok += 1

        # 4. by-domain: "ml" co-occurs with 2 tags (law+tech via c1, tech via c2)
        bd = tags_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ml"][0]
        assert ml["distinct_tags"] == 2
        ok += 1

        # 5. "nlp" co-occurs with 3 tags (law+tech via c1, bio via c3)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_tags"] == 3
        ok += 1

        # 6. "cv" co-occurs with 1 tag (tech via c2)
        cv = [r for r in bd if r["domain"] == "cv"][0]
        assert cv["distinct_tags"] == 1
        ok += 1

        # 7. co-occurrence: tech+ml has 2 shared chunks (c1, c2)
        co = tag_domain_co_occurrence(conn)
        tech_ml = [r for r in co if r["tag"] == "tech" and r["domain"] == "ml"][0]
        assert tech_ml["shared_chunks"] == 2
        ok += 1

        # 8. co-occurrence: law+nlp has 1 shared chunk (c1)
        law_nlp = [r for r in co if r["tag"] == "law" and r["domain"] == "nlp"][0]
        assert law_nlp["shared_chunks"] == 1
        ok += 1

        # 9. co-occurrence: bio+cv does not exist
        bio_cv = [r for r in co if r["tag"] == "bio" and r["domain"] == "cv"]
        assert len(bio_cv) == 0
        ok += 1

        # 10. summary: tags_with_domains = 3 (law, tech, bio; c4's law has no domain but c1's law does)
        s = tag_domain_summary(conn)
        assert s["tags_with_domains"] == 3
        ok += 1

        # 11. domains_with_tags = 3 (nlp, ml, cv)
        assert s["domains_with_tags"] == 3
        ok += 1

        # 12. distinct_pairs: law+nlp, law+ml, tech+nlp, tech+ml, tech+cv, bio+nlp = 6
        assert s["distinct_pairs"] == 6
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["pair_density"] == s["pair_density"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = tag_domain_summary(conn)
        assert s["tags_with_domains"] == 0
        assert s["domains_with_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Tag domain correlation analysis")
    ap.add_argument("command", choices=["by-tag", "by-domain", "co-occurrence", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS tag_domain_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = domains_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag domain data found.")
            else:
                print(f"{'tag':<20} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_domain_score']:.4f}")
    elif args.command == "by-domain":
        rows = tags_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain tag data found.")
            else:
                print(f"{'domain':<20} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['classified_chunks']:<8} {r['avg_tag_score']:.4f}")
    elif args.command == "co-occurrence":
        rows = tag_domain_co_occurrence(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag-domain co-occurrences found.")
            else:
                print(f"{'tag':<20} {'domain':<20} {'chunks':<8} {'tag_score':<10} {'dom_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['domain']:<20} {r['shared_chunks']:<8} {r['avg_tag_score']:.4f}     {r['avg_domain_score']:.4f}")
    elif args.command == "summary":
        s = tag_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
