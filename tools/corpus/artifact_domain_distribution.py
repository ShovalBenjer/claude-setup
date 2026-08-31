#!/usr/bin/env python3
"""Artifact domain distribution: which domains contain which artifact types.

artifact_citation_provenance.py checks citation backing on artifacts.
evidence_chain_audit.py audits the full provenance chain through artifacts.
No tool joins artifacts with chunk_domains to show which knowledge domains
contain which artifact types, or which domains are richest in actionable
artifacts.

Usage:
    python tools/corpus/artifact_domain_distribution.py by-domain [--db PATH] [--json]
    python tools/corpus/artifact_domain_distribution.py by-type [--db PATH] [--json]
    python tools/corpus/artifact_domain_distribution.py cross [--db PATH] [--json]
    python tools/corpus/artifact_domain_distribution.py summary [--db PATH] [--json]
    python tools/corpus/artifact_domain_distribution.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CD_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_domains ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  domain TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  classified_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, domain))"
)


def artifacts_by_domain(conn) -> list[dict]:
    """Artifact counts per domain, with type breakdown."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT a.artifact_id) AS artifact_count,
               COUNT(DISTINCT a.chunk_id) AS chunk_count,
               COUNT(DISTINCT CASE WHEN a.implemented = 1 THEN a.artifact_id END) AS implemented,
               ROUND(AVG(cd.score), 4) AS avg_domain_score
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        GROUP BY cd.domain
        ORDER BY artifact_count DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "artifact_count": r[1],
            "chunk_count": r[2],
            "implemented": r[3],
            "avg_domain_score": r[4],
        }
        for r in rows
    ]


def artifacts_by_type(conn) -> list[dict]:
    """Domain counts per artifact type."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT a.artifact_type,
               COUNT(DISTINCT cd.domain) AS domain_count,
               COUNT(DISTINCT a.artifact_id) AS artifact_count,
               COUNT(DISTINCT CASE WHEN a.implemented = 1 THEN a.artifact_id END) AS implemented
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        GROUP BY a.artifact_type
        ORDER BY artifact_count DESC, a.artifact_type
        """
    ).fetchall()
    return [
        {
            "artifact_type": r[0],
            "domain_count": r[1],
            "artifact_count": r[2],
            "implemented": r[3],
        }
        for r in rows
    ]


def cross_distribution(conn) -> list[dict]:
    """Full domain x artifact_type cross-tabulation."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain, a.artifact_type,
               COUNT(DISTINCT a.artifact_id) AS count,
               COUNT(DISTINCT CASE WHEN a.implemented = 1 THEN a.artifact_id END) AS implemented
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        GROUP BY cd.domain, a.artifact_type
        ORDER BY cd.domain, count DESC
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "artifact_type": r[1],
            "count": r[2],
            "implemented": r[3],
        }
        for r in rows
    ]


def distribution_summary(conn) -> dict:
    """Aggregate artifact-domain distribution statistics."""
    conn.execute(_CD_DDL)
    total_artifacts = conn.execute(
        "SELECT COUNT(*) FROM artifacts"
    ).fetchone()[0]
    classified_artifacts = conn.execute(
        """
        SELECT COUNT(DISTINCT a.artifact_id)
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        """
    ).fetchone()[0]
    unclassified = total_artifacts - classified_artifacts
    classification_rate = round(classified_artifacts / max(total_artifacts, 1), 4)

    domains_with_artifacts = conn.execute(
        """
        SELECT COUNT(DISTINCT cd.domain)
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        """
    ).fetchone()[0]
    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]
    artifact_types_classified = conn.execute(
        """
        SELECT COUNT(DISTINCT a.artifact_type)
        FROM artifacts a
        JOIN chunk_domains cd ON cd.chunk_id = a.chunk_id
        """
    ).fetchone()[0]

    by_domain = artifacts_by_domain(conn)
    richest_domain = by_domain[0]["domain"] if by_domain else None
    sparsest_domain = by_domain[-1]["domain"] if by_domain else None

    return {
        "total_artifacts": total_artifacts,
        "classified_artifacts": classified_artifacts,
        "unclassified_artifacts": unclassified,
        "classification_rate": classification_rate,
        "domains_with_artifacts": domains_with_artifacts,
        "total_domains": total_domains,
        "artifact_types_classified": artifact_types_classified,
        "richest_domain": richest_domain,
        "sparsest_domain": sparsest_domain,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CD_DDL)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # artifacts: c1 has library+api, c2 has command, c3 has config, c5 has library (no domain)
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a1", "c1", "library", "requests", "2.31", None, 1, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a2", "c1", "api", "GET /users", None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a3", "c2", "command", "pip install", None, None, 1, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a4", "c3", "config", "pyproject.toml", None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a5", "c5", "library", "numpy", "1.26", None, 1, None),
        )

        # chunk_domains: c1 in "ml" and "web", c2 in "devops", c3 in "ml"
        # c5 has no domain classification
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "web", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "devops", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.8, t1))
        conn.commit()

        # 1. artifacts_by_domain: ml has 3 artifacts (a1, a2, a4)
        bd = artifacts_by_domain(conn)
        ml_row = [r for r in bd if r["domain"] == "ml"][0]
        assert ml_row["artifact_count"] == 3, f"ml artifacts {ml_row['artifact_count']}"
        ok += 1

        # 2. web domain has 2 artifacts (a1, a2 from c1)
        web_row = [r for r in bd if r["domain"] == "web"][0]
        assert web_row["artifact_count"] == 2, f"web artifacts {web_row['artifact_count']}"
        ok += 1

        # 3. devops has 1 artifact (a3)
        devops_row = [r for r in bd if r["domain"] == "devops"][0]
        assert devops_row["artifact_count"] == 1
        ok += 1

        # 4. ml implemented count is 1 (a1 from c1; a4 from c3 is not implemented)
        assert ml_row["implemented"] == 1, f"ml implemented {ml_row['implemented']}"
        ok += 1

        # 5. artifacts_by_type: library has 1 classified (a1; a5 is unclassified)
        bt = artifacts_by_type(conn)
        lib_row = [r for r in bt if r["artifact_type"] == "library"][0]
        assert lib_row["artifact_count"] == 1, f"library count {lib_row['artifact_count']}"
        ok += 1

        # 6. library spans 2 domains (ml, web via c1)
        assert lib_row["domain_count"] == 2, f"library domains {lib_row['domain_count']}"
        ok += 1

        # 7. cross_distribution has correct entries
        cr = cross_distribution(conn)
        ml_lib = [r for r in cr if r["domain"] == "ml" and r["artifact_type"] == "library"]
        assert len(ml_lib) == 1 and ml_lib[0]["count"] == 1
        ok += 1

        # 8. cross has ml/config entry
        ml_cfg = [r for r in cr if r["domain"] == "ml" and r["artifact_type"] == "config"]
        assert len(ml_cfg) == 1 and ml_cfg[0]["count"] == 1
        ok += 1

        # 9. summary: total artifacts is 5
        s = distribution_summary(conn)
        assert s["total_artifacts"] == 5, f"total {s['total_artifacts']}"
        ok += 1

        # 10. classified is 4 (a5 on c5 has no domain)
        assert s["classified_artifacts"] == 4, f"classified {s['classified_artifacts']}"
        ok += 1

        # 11. unclassified is 1
        assert s["unclassified_artifacts"] == 1
        ok += 1

        # 12. domains_with_artifacts is 3
        assert s["domains_with_artifacts"] == 3
        ok += 1

        # 13. JSON serialisation round-trips
        j = json.loads(json.dumps(s))
        assert j["classification_rate"] == s["classification_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = distribution_summary(conn)
        assert s["total_artifacts"] == 0
        assert s["classified_artifacts"] == 0
        assert s["classification_rate"] == 0.0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Artifact domain distribution analysis")
    ap.add_argument("command", choices=["by-domain", "by-type", "cross", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS artifact_domain_distribution selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-domain":
        rows = artifacts_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No artifacts with domain classification found.")
            else:
                print(f"{'domain':<16} {'artifacts':<10} {'chunks':<8} {'implemented':<12} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['artifact_count']:<10} {r['chunk_count']:<8} {r['implemented']:<12} {r['avg_domain_score']:.4f}")
    elif args.command == "by-type":
        rows = artifacts_by_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'artifact_type':<16} {'domains':<10} {'artifacts':<10} {'implemented'}")
            for r in rows:
                print(f"{r['artifact_type']:<16} {r['domain_count']:<10} {r['artifact_count']:<10} {r['implemented']}")
    elif args.command == "cross":
        rows = cross_distribution(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'domain':<16} {'artifact_type':<16} {'count':<8} {'implemented'}")
            for r in rows:
                print(f"{r['domain']:<16} {r['artifact_type']:<16} {r['count']:<8} {r['implemented']}")
    elif args.command == "summary":
        s = distribution_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
