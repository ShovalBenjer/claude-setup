#!/usr/bin/env python3
"""Status domain profile: how chunk status relates to chunk domain patterns.

status_tag_profile.py profiles statuses by chunk tag patterns.
status_edge_profile.py profiles statuses by claim edge patterns.
No tool joins chunks.status with chunk_domains to measure whether
accepted chunks span different knowledge domains than quarantined
or rejected ones, or how domain scores vary across chunk statuses.

Usage:
    python tools/corpus/status_domain_profile.py by-status [--db PATH] [--json]
    python tools/corpus/status_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/status_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/status_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/status_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_status(conn) -> list[dict]:
    """Domain distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.status
        ORDER BY domain_assignments DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def status_by_domain(conn) -> list[dict]:
    """Status distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT c.status) AS distinct_statuses,
               COUNT(cd.domain) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY distinct_statuses DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_statuses": r[1],
            "assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def status_domain_concentration(conn) -> list[dict]:
    """Per-status domain concentration: ratio of distinct domains to assignments."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.status
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "classified_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def status_domain_summary(conn) -> dict:
    """Aggregate status-domain statistics."""
    total_statuses = conn.execute(
        "SELECT COUNT(DISTINCT status) FROM chunks"
    ).fetchone()[0]

    statuses_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT c.status)
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

    avg_domains_per_status = conn.execute(
        """
        SELECT ROUND(AVG(domain_count), 4)
        FROM (
            SELECT c.status, COUNT(DISTINCT cd.domain) AS domain_count
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.status
        )
        """
    ).fetchone()[0]

    single_status_domains = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cd.domain
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            GROUP BY cd.domain
            HAVING COUNT(DISTINCT c.status) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_statuses": total_statuses,
        "statuses_with_domains": statuses_with_domains,
        "status_domain_coverage": round(statuses_with_domains / max(total_statuses, 1), 4),
        "total_distinct_domains": total_domains,
        "total_domain_assignments": total_assignments,
        "avg_domains_per_status": avg_domains_per_status or 0.0,
        "single_status_domains": single_status_domains,
        "single_status_domain_rate": round(single_status_domains / max(total_domains, 1), 4),
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

        # c1: accepted, c2: accepted, c3: quarantined, c4: rejected (no domains)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 25, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "discussion", "claim", None, "t", "t", 35, "jkl", 4000, 0, "rejected", "duplicate", t1))

        # Domains: accepted gets nlp+ml+ir (3), quarantined gets ml+cv (2), rejected gets none
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "ir", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "cv", 0.6, t1))
        conn.commit()

        # 1. by-status: accepted has 3 distinct domains
        bs = domains_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["distinct_domains"] == 3
        ok += 1

        # 2. accepted has 3 domain assignments
        assert accepted["domain_assignments"] == 3
        ok += 1

        # 3. quarantined has 2 distinct domains
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["distinct_domains"] == 2
        ok += 1

        # 4. rejected not in results (no domains)
        rejected = [r for r in bs if r["status"] == "rejected"]
        assert len(rejected) == 0
        ok += 1

        # 5. by-domain: "ml" spans 2 statuses (accepted, quarantined)
        bd = status_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ml"][0]
        assert ml["distinct_statuses"] == 2
        ok += 1

        # 6. "cv" spans 1 status (quarantined)
        cv = [r for r in bd if r["domain"] == "cv"][0]
        assert cv["distinct_statuses"] == 1
        ok += 1

        # 7. "nlp" spans 1 status (accepted)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_statuses"] == 1
        ok += 1

        # 8. concentration: accepted has diversity 3/3=1.0
        conc = status_domain_concentration(conn)
        acc_conc = [r for r in conc if r["status"] == "accepted"][0]
        assert acc_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. quarantined has diversity 2/2=1.0
        q_conc = [r for r in conc if r["status"] == "quarantined"][0]
        assert q_conc["diversity_ratio"] == 1.0
        ok += 1

        # 10. rejected not in concentration (no domains)
        rej_conc = [r for r in conc if r["status"] == "rejected"]
        assert len(rej_conc) == 0
        ok += 1

        # 11. summary: statuses_with_domains = 2 (accepted, quarantined)
        s = status_domain_summary(conn)
        assert s["statuses_with_domains"] == 2
        ok += 1

        # 12. total_distinct_domains = 4 (nlp, ml, ir, cv)
        assert s["total_distinct_domains"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["status_domain_coverage"] == s["status_domain_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = status_domain_summary(conn)
        assert s["statuses_with_domains"] == 0
        assert s["total_distinct_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Status domain profile analysis")
    ap.add_argument("command", choices=["by-status", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS status_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-status":
        rows = domains_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status domain data found.")
            else:
                print(f"{'status':<14} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = status_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain status data found.")
            else:
                print(f"{'domain':<20} {'statuses':<10} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_statuses']:<10} {r['assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = status_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No statuses with multiple domains found.")
            else:
                print(f"{'status':<14} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['classified_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = status_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
