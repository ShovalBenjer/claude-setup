#!/usr/bin/env python3
"""Kind domain profile: which chunk kinds attract which semantic domains.

chunk_kind_profile.py profiles kinds per source and has a per-domain view.
kind_tag_profile.py profiles kinds by tag vocabulary.
No tool joins chunks.kind with chunk_domains to measure which chunk
kinds concentrate which domains, whether claims attract different domains
than code or prose chunks, or how domain diversity varies by kind.

Usage:
    python tools/corpus/kind_domain_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/kind_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/kind_domain_profile.py diversity [--db PATH] [--json]
    python tools/corpus/kind_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/kind_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_kind(conn) -> list[dict]:
    """Domain distribution per chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.kind
        ORDER BY domain_assignments DESC, c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def kinds_by_domain(conn) -> list[dict]:
    """Kind distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT c.kind) AS distinct_kinds,
               COUNT(cd.domain) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY distinct_kinds DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_kinds": r[1],
            "assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def kind_domain_diversity(conn) -> list[dict]:
    """Per-kind domain diversity: ratio of distinct domains to assignments."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.kind
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "classified_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def kind_domain_summary(conn) -> dict:
    """Aggregate kind-domain statistics."""
    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM chunks"
    ).fetchone()[0]

    kinds_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT c.kind)
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_domains"
    ).fetchone()[0]

    avg_domains_per_kind = conn.execute(
        """
        SELECT ROUND(AVG(dom_count), 4)
        FROM (
            SELECT c.kind, COUNT(DISTINCT cd.domain) AS dom_count
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.kind
        )
        """
    ).fetchone()[0]

    single_kind_domains = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cd.domain
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            GROUP BY cd.domain
            HAVING COUNT(DISTINCT c.kind) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_kinds": total_kinds,
        "kinds_with_domains": kinds_with_domains,
        "kind_domain_coverage": round(kinds_with_domains / max(total_kinds, 1), 4),
        "total_distinct_domains": total_domains,
        "total_domain_assignments": total_assignments,
        "avg_domains_per_kind": avg_domains_per_kind or 0.0,
        "single_kind_domains": single_kind_domains,
        "single_kind_domain_rate": round(single_kind_domains / max(total_domains, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1,c2 are "claim"; c3 is "code"; c4 is "prose"; c5 is "claim" (no domains)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "code", "code", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "notes", "prose", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "appendix", "claim", None, "t", "t", 10, "mno", 5000, 0, "accepted", None, t1))

        # Domains: claims get ML+NLP+stats, code gets ML, prose gets NLP
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ML", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "NLP", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "stats", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ML", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "NLP", 0.75, t1))
        conn.commit()

        # 1. by-kind: "claim" has 3 distinct domains (ML, NLP, stats)
        bk = domains_by_kind(conn)
        claim_row = [r for r in bk if r["kind"] == "claim"][0]
        assert claim_row["distinct_domains"] == 3
        ok += 1

        # 2. "claim" has 3 domain assignments
        assert claim_row["domain_assignments"] == 3
        ok += 1

        # 3. "code" has 1 distinct domain (ML)
        code_row = [r for r in bk if r["kind"] == "code"][0]
        assert code_row["distinct_domains"] == 1
        ok += 1

        # 4. "prose" has 1 distinct domain (NLP)
        prose_row = [r for r in bk if r["kind"] == "prose"][0]
        assert prose_row["distinct_domains"] == 1
        ok += 1

        # 5. by-domain: "ML" spans 2 kinds (claim, code)
        bd = kinds_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ML"][0]
        assert ml["distinct_kinds"] == 2
        ok += 1

        # 6. "stats" spans 1 kind (claim only)
        stats = [r for r in bd if r["domain"] == "stats"][0]
        assert stats["distinct_kinds"] == 1
        ok += 1

        # 7. "NLP" spans 2 kinds (claim, prose)
        nlp = [r for r in bd if r["domain"] == "NLP"][0]
        assert nlp["distinct_kinds"] == 2
        ok += 1

        # 8. diversity: "claim" has 3/3=1.0
        div = kind_domain_diversity(conn)
        claim_div = [r for r in div if r["kind"] == "claim"][0]
        assert claim_div["diversity_ratio"] == 1.0
        ok += 1

        # 9. "code" not in diversity (only 1 assignment)
        code_div = [r for r in div if r["kind"] == "code"]
        assert len(code_div) == 0
        ok += 1

        # 10. summary: kinds_with_domains = 3 (claim, code, prose)
        s = kind_domain_summary(conn)
        assert s["kinds_with_domains"] == 3
        ok += 1

        # 11. total_distinct_domains = 3 (ML, NLP, stats)
        assert s["total_distinct_domains"] == 3
        ok += 1

        # 12. single_kind_domains = 1 (stats is claim-only)
        assert s["single_kind_domains"] == 1, f"expected 1, got {s['single_kind_domains']}"
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["kind_domain_coverage"] == s["kind_domain_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = kind_domain_summary(conn)
        assert s["kinds_with_domains"] == 0
        assert s["total_distinct_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Kind domain profile analysis")
    ap.add_argument("command", choices=["by-kind", "by-domain", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS kind_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-kind":
        rows = domains_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind domain data found.")
            else:
                print(f"{'kind':<15} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['kind']:<15} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = kinds_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain kind data found.")
            else:
                print(f"{'domain':<20} {'kinds':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_kinds']:<8} {r['assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = kind_domain_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kinds with multiple domains found.")
            else:
                print(f"{'kind':<15} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['kind']:<15} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['classified_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = kind_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
