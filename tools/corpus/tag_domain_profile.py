#!/usr/bin/env python3
"""Tag domain profile: how chunk tags distribute across semantic domains.

heading_tag_profile.py profiles headings by chunk tags.
heading_domain_profile.py profiles headings by semantic domains.
No tool cross-tabulates chunk_tags.tag with chunk_domains.domain to measure
which tags co-occur with which domains, or how domain classifications
distribute across tag assignments.

Usage:
    python tools/corpus/tag_domain_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/tag_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/tag_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/tag_domain_profile.py selftest
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
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks
        FROM chunk_tags ct
        JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY distinct_domains DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_domains": r[1],
            "tagged_chunks": r[2],
            "classified_chunks": r[3],
        }
        for r in rows
    ]


def tags_by_domain(conn) -> list[dict]:
    """Tag distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks
        FROM chunk_domains cd
        JOIN chunk_tags ct ON ct.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY distinct_tags DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_tags": r[1],
            "classified_chunks": r[2],
            "tagged_chunks": r[3],
        }
        for r in rows
    ]


def tag_domain_concentration(conn) -> list[dict]:
    """Per-tag domain diversity ordered by distinct domains."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks
        FROM chunk_tags ct
        JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY distinct_domains DESC, tagged_chunks DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_domains": r[1],
            "tagged_chunks": r[2],
            "classified_chunks": r[3],
            "domain_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def tag_domain_summary(conn) -> dict:
    """Aggregate tag-domain statistics."""
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

    multi_domain_tags = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT cd.domain) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT ct.tag, cd.domain
            FROM chunk_tags ct
            JOIN chunk_domains cd ON cd.chunk_id = ct.chunk_id
            GROUP BY ct.tag, cd.domain
        )
        """
    ).fetchone()[0]

    return {
        "total_tags": total_tags,
        "total_domains": total_domains,
        "tags_with_domains": tags_with_domains,
        "multi_domain_tags": multi_domain_tags,
        "multi_domain_rate": round(multi_domain_tags / max(tags_with_domains, 1), 4),
        "distinct_tag_domain_pairs": distinct_pairs,
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
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # c1: tags(python, ml), domains(nlp, ml)
        # c2: tags(python), domains(nlp)
        # c3: tags(ml), domains(ml)
        # c4: tags(web), domains(web)
        # c5: tags(python), no domain (unclassified)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3001, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c5", "python", 0.4, t1))

        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "nlp", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))
        conn.commit()

        # 1. by-tag: "python" spans 2 domains (nlp, ml) via c1 and c2
        bt = domains_by_tag(conn)
        python = [r for r in bt if r["tag"] == "python"][0]
        assert python["distinct_domains"] == 2
        ok += 1

        # 2. "ml" spans 2 domains (nlp, ml) via c1 and c3
        ml = [r for r in bt if r["tag"] == "ml"][0]
        assert ml["distinct_domains"] == 2
        ok += 1

        # 3. "web" spans 1 domain (web)
        web = [r for r in bt if r["tag"] == "web"][0]
        assert web["distinct_domains"] == 1
        ok += 1

        # 4. python tagged_chunks = 2 (c1, c2; c5 has no domain so not in join)
        assert python["tagged_chunks"] == 2
        ok += 1

        # 5. by-domain: "nlp" has 2 distinct tags (python, ml) via c1 and c2
        bd = tags_by_domain(conn)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_tags"] == 2
        ok += 1

        # 6. "ml" domain has 2 distinct tags (python, ml) via c1 and c3
        ml_dom = [r for r in bd if r["domain"] == "ml"][0]
        assert ml_dom["distinct_tags"] == 2
        ok += 1

        # 7. "web" domain has 1 distinct tag (web)
        web_dom = [r for r in bd if r["domain"] == "web"][0]
        assert web_dom["distinct_tags"] == 1
        ok += 1

        # 8. concentration: python domain_ratio = 2/2 = 1.0
        conc = tag_domain_concentration(conn)
        c_python = [r for r in conc if r["tag"] == "python"][0]
        assert c_python["domain_ratio"] == 1.0
        ok += 1

        # 9. web domain_ratio = 1/1 = 1.0
        c_web = [r for r in conc if r["tag"] == "web"][0]
        assert c_web["domain_ratio"] == 1.0
        ok += 1

        # 10. summary: total_tags = 3 (python, ml, web)
        s = tag_domain_summary(conn)
        assert s["total_tags"] == 3
        ok += 1

        # 11. tags_with_domains = 3 (all tags have at least one chunk with a domain)
        assert s["tags_with_domains"] == 3
        ok += 1

        # 12. multi_domain_tags = 2 (python and ml each span 2 domains)
        assert s["multi_domain_tags"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_domain_rate"] == s["multi_domain_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = tag_domain_summary(conn)
        assert s["total_tags"] == 0
        assert s["total_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Tag domain profile analysis")
    ap.add_argument("command", choices=["by-tag", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS tag_domain_profile selftest ({ok} checks)")
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
                print(f"{'tag':<16} {'domains':<10} {'tagged':<8} {'classified'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['distinct_domains']:<10} {r['tagged_chunks']:<8} {r['classified_chunks']}")
    elif args.command == "by-domain":
        rows = tags_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain tag data found.")
            else:
                print(f"{'domain':<16} {'tags':<10} {'classified':<12} {'tagged'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['distinct_tags']:<10} {r['classified_chunks']:<12} {r['tagged_chunks']}")
    elif args.command == "concentration":
        rows = tag_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag domain data found.")
            else:
                print(f"{'tag':<16} {'domains':<10} {'tagged':<8} {'classified':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['distinct_domains']:<10} {r['tagged_chunks']:<8} {r['classified_chunks']:<12} {r['domain_ratio']:.4f}")
    elif args.command == "summary":
        s = tag_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
