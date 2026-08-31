#!/usr/bin/env python3
"""Liveness domain profile: how source liveness relates to chunk domain patterns.

publisher_domain_profile.py profiles domains by publisher.
liveness_tag_profile.py correlates liveness with chunk tags.
No tool joins sources.liveness with chunk_domains to measure whether
live sources span different knowledge domains than stale or archived
ones, or how domain scores vary across liveness states.

Usage:
    python tools/corpus/liveness_domain_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/liveness_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/liveness_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/liveness_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/liveness_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_liveness(conn) -> list[dict]:
    """Domain distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.liveness
        ORDER BY domain_assignments DESC, s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def liveness_by_domain(conn) -> list[dict]:
    """Liveness distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT s.liveness) AS distinct_states,
               COUNT(cd.domain) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY cd.domain
        ORDER BY distinct_states DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_states": r[1],
            "assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def liveness_domain_concentration(conn) -> list[dict]:
    """Per-liveness domain concentration: ratio of distinct domains to assignments."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.liveness
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "classified_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def liveness_domain_summary(conn) -> dict:
    """Aggregate liveness-domain statistics."""
    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    states_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT s.liveness)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_domains"
    ).fetchone()[0]

    avg_domains_per_state = conn.execute(
        """
        SELECT ROUND(AVG(domain_count), 4)
        FROM (
            SELECT s.liveness, COUNT(DISTINCT cd.domain) AS domain_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY s.liveness
        )
        """
    ).fetchone()[0]

    single_state_domains = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cd.domain
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY cd.domain
            HAVING COUNT(DISTINCT s.liveness) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_liveness_states": total_states,
        "states_with_domains": states_with_domains,
        "liveness_domain_coverage": round(states_with_domains / max(total_states, 1), 4),
        "total_distinct_domains": total_domains,
        "total_domain_assignments": total_assignments,
        "avg_domains_per_state": avg_domains_per_state or 0.0,
        "single_state_domains": single_state_domains,
        "single_state_domain_rate": round(single_state_domains / max(total_domains, 1), 4),
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "ghi", 150, None),
        )

        # c1,c2 from s1 (live); c3,c4 from s2 (stale); c5 from s3 (archived, no domains)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "def", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 2, "results", "claim", None, "t", "t", 35, "def", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s3", 1, "intro", "claim", None, "t", "t", 15, "ghi", 5000, 0, "accepted", None, t1))

        # Domains: live gets nlp+ml+ir (3), stale gets ml+cv (2), archived gets none
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "ir", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "cv", 0.6, t1))
        conn.commit()

        # 1. by-liveness: live has 3 distinct domains
        bl = domains_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["distinct_domains"] == 3
        ok += 1

        # 2. live has 3 domain assignments
        assert live["domain_assignments"] == 3
        ok += 1

        # 3. stale has 2 distinct domains
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["distinct_domains"] == 2
        ok += 1

        # 4. archived not in results (no domains)
        archived = [r for r in bl if r["liveness"] == "archived"]
        assert len(archived) == 0
        ok += 1

        # 5. by-domain: "ml" spans 2 liveness states (live, stale)
        bd = liveness_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ml"][0]
        assert ml["distinct_states"] == 2
        ok += 1

        # 6. "cv" spans 1 liveness state (stale)
        cv = [r for r in bd if r["domain"] == "cv"][0]
        assert cv["distinct_states"] == 1
        ok += 1

        # 7. "nlp" spans 1 liveness state (live)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_states"] == 1
        ok += 1

        # 8. concentration: live has diversity 3/3=1.0
        conc = liveness_domain_concentration(conn)
        live_conc = [r for r in conc if r["liveness"] == "live"][0]
        assert live_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. stale has diversity 2/2=1.0
        stale_conc = [r for r in conc if r["liveness"] == "stale"][0]
        assert stale_conc["diversity_ratio"] == 1.0
        ok += 1

        # 10. archived not in concentration (no domains)
        archived_conc = [r for r in conc if r["liveness"] == "archived"]
        assert len(archived_conc) == 0
        ok += 1

        # 11. summary: states_with_domains = 2 (live, stale)
        s = liveness_domain_summary(conn)
        assert s["states_with_domains"] == 2
        ok += 1

        # 12. total_distinct_domains = 4 (nlp, ml, ir, cv)
        assert s["total_distinct_domains"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["liveness_domain_coverage"] == s["liveness_domain_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = liveness_domain_summary(conn)
        assert s["states_with_domains"] == 0
        assert s["total_distinct_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Liveness domain profile analysis")
    ap.add_argument("command", choices=["by-liveness", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS liveness_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-liveness":
        rows = domains_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness domain data found.")
            else:
                print(f"{'liveness':<14} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = liveness_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain liveness data found.")
            else:
                print(f"{'domain':<20} {'states':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_states']:<8} {r['assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = liveness_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness states with multiple domains found.")
            else:
                print(f"{'liveness':<14} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['classified_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = liveness_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
