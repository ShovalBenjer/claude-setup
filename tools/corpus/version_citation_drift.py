#!/usr/bin/env python3
"""Version citation drift: citations whose parent chunk changed after verification.

version_edge_impact.py checks claim_edges against chunk_versions.
edge_citation_quality.py checks citation quality on claim_edges.
No tool joins chunk_versions with citations to detect citations that may
be stale because their parent chunk's content was revised after the
citation was last verified.

Usage:
    python tools/corpus/version_citation_drift.py drifted [--db PATH] [--json]
    python tools/corpus/version_citation_drift.py by-tag [--db PATH] [--json]
    python tools/corpus/version_citation_drift.py by-depth [--db PATH] [--json]
    python tools/corpus/version_citation_drift.py summary [--db PATH] [--json]
    python tools/corpus/version_citation_drift.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def drifted_citations(conn) -> list[dict]:
    """Citations whose parent chunk was revised after the citation was verified."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT,"
        "  word_count INTEGER,"
        "  snapshot_utc TEXT,"
        "  UNIQUE(chunk_id, version_num))"
    )
    rows = conn.execute(
        """
        SELECT c.citation_id, c.chunk_id, c.target_uri, c.tag,
               c.verified_utc,
               MAX(cv.snapshot_utc) AS latest_revision,
               COUNT(cv.version_id) AS revisions_after
        FROM citations c
        JOIN chunk_versions cv
          ON cv.chunk_id = c.chunk_id
         AND cv.snapshot_utc > c.verified_utc
        WHERE c.verified = 1
          AND c.verified_utc IS NOT NULL
        GROUP BY c.citation_id
        ORDER BY revisions_after DESC, c.citation_id
        """
    ).fetchall()
    return [
        {
            "citation_id": r[0],
            "chunk_id": r[1],
            "target_uri": r[2],
            "tag": r[3],
            "verified_utc": r[4],
            "latest_revision": r[5],
            "revisions_after": r[6],
        }
        for r in rows
    ]


def drift_by_tag(conn) -> list[dict]:
    """Drifted citation counts per citation tag."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT,"
        "  word_count INTEGER,"
        "  snapshot_utc TEXT,"
        "  UNIQUE(chunk_id, version_num))"
    )
    rows = conn.execute(
        """
        SELECT c.tag,
               COUNT(DISTINCT c.citation_id) AS total_verified,
               COUNT(DISTINCT CASE
                   WHEN cv.version_id IS NOT NULL THEN c.citation_id
               END) AS drifted,
               ROUND(
                   COUNT(DISTINCT CASE
                       WHEN cv.version_id IS NOT NULL THEN c.citation_id
                   END) * 1.0
                   / MAX(COUNT(DISTINCT c.citation_id), 1),
                   4
               ) AS drift_rate
        FROM citations c
        LEFT JOIN chunk_versions cv
          ON cv.chunk_id = c.chunk_id
         AND cv.snapshot_utc > c.verified_utc
        WHERE c.verified = 1
          AND c.verified_utc IS NOT NULL
        GROUP BY c.tag
        ORDER BY drifted DESC, c.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "total_verified": r[1],
            "drifted": r[2],
            "drift_rate": r[3],
        }
        for r in rows
    ]


def drift_by_depth(conn) -> list[dict]:
    """Drifted citations bucketed by revision depth of parent chunk."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT,"
        "  word_count INTEGER,"
        "  snapshot_utc TEXT,"
        "  UNIQUE(chunk_id, version_num))"
    )
    rows = conn.execute(
        """
        SELECT rev_count, COUNT(*) AS drifted_citations
        FROM (
            SELECT c.citation_id,
                   COUNT(cv.version_id) AS rev_count
            FROM citations c
            JOIN chunk_versions cv
              ON cv.chunk_id = c.chunk_id
             AND cv.snapshot_utc > c.verified_utc
            WHERE c.verified = 1
              AND c.verified_utc IS NOT NULL
            GROUP BY c.citation_id
        )
        GROUP BY rev_count
        ORDER BY rev_count
        """
    ).fetchall()
    return [
        {"revision_depth": r[0], "drifted_citations": r[1]}
        for r in rows
    ]


def drift_summary(conn) -> dict:
    """Aggregate citation drift statistics."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT,"
        "  word_count INTEGER,"
        "  snapshot_utc TEXT,"
        "  UNIQUE(chunk_id, version_num))"
    )
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]
    total_verified = conn.execute(
        "SELECT COUNT(*) FROM citations WHERE verified = 1 AND verified_utc IS NOT NULL"
    ).fetchone()[0]
    drifted = conn.execute(
        """
        SELECT COUNT(DISTINCT c.citation_id)
        FROM citations c
        JOIN chunk_versions cv
          ON cv.chunk_id = c.chunk_id
         AND cv.snapshot_utc > c.verified_utc
        WHERE c.verified = 1
          AND c.verified_utc IS NOT NULL
        """
    ).fetchone()[0]
    unverified = conn.execute(
        "SELECT COUNT(*) FROM citations WHERE verified = 0"
    ).fetchone()[0]
    drift_rate = round(drifted / max(total_verified, 1), 4)

    by_tag = drift_by_tag(conn)
    most_drifted_tag = by_tag[0]["tag"] if by_tag and by_tag[0]["drifted"] > 0 else None

    chunks_with_verified = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM citations WHERE verified = 1 AND verified_utc IS NOT NULL"
    ).fetchone()[0]
    chunks_revised = conn.execute(
        """
        SELECT COUNT(DISTINCT c.chunk_id)
        FROM citations c
        JOIN chunk_versions cv
          ON cv.chunk_id = c.chunk_id
         AND cv.snapshot_utc > c.verified_utc
        WHERE c.verified = 1
          AND c.verified_utc IS NOT NULL
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "drifted": drifted,
        "unverified": unverified,
        "drift_rate": drift_rate,
        "most_drifted_tag": most_drifted_tag,
        "chunks_with_verified_citations": chunks_with_verified,
        "chunks_revised_after_verification": chunks_revised,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "  version_id TEXT PRIMARY KEY,"
            "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
            "  version_num INTEGER NOT NULL,"
            "  norm_sha256 TEXT,"
            "  word_count INTEGER,"
            "  snapshot_utc TEXT,"
            "  UNIQUE(chunk_id, version_num))"
        )

        t1 = "2026-01-01T00:00:00Z"
        t2 = "2026-02-01T00:00:00Z"
        t3 = "2026-03-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # c1: verified citation at t1, chunk revised at t2 -> drifted
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "http://a.com", None, "url", None, 1, t1),
        )
        # c2: verified citation at t1, chunk revised at t3 -> drifted
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit2", "c2", "http://b.com", None, "doi", None, 1, t1),
        )
        # c3: verified citation at t3, chunk revised at t2 -> NOT drifted (revision before verification)
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit3", "c3", "http://c.com", None, "url", None, 1, t3),
        )
        # c4: unverified citation, chunk revised at t2 -> NOT drifted (not verified)
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit4", "c4", "http://d.com", None, "doi", None, 0, None),
        )
        # c1: second verified citation at t2, chunk revised at t3 -> drifted (t3 > t2)
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit5", "c1", "http://e.com", None, "url", None, 1, t2),
        )

        # chunk_versions: c1 revised at t2, c2 revised at t3, c3 revised at t2
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v1", "c1", 2, "def", 12, t2),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v2", "c2", 2, "ghi", 11, t3),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v3", "c3", 2, "jkl", 9, t2),
        )
        # c1 has a second revision at t3
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v4", "c1", 3, "mno", 13, t3),
        )
        conn.commit()

        # 1. drifted_citations returns correct count
        d = drifted_citations(conn)
        assert len(d) == 3, f"expected 3 drifted, got {len(d)}"
        ok += 1

        # 2. cit1 is drifted (verified at t1, chunk revised at t2 and t3)
        ids = {r["citation_id"] for r in d}
        assert "cit1" in ids, "cit1 should be drifted"
        ok += 1

        # 3. cit2 is drifted (verified at t1, chunk revised at t3)
        assert "cit2" in ids, "cit2 should be drifted"
        ok += 1

        # 4. cit5 is drifted (verified at t2, chunk c1 revised at t3)
        assert "cit5" in ids, "cit5 should be drifted"
        ok += 1

        # 5. cit3 NOT drifted (verified at t3, revision at t2 is before)
        assert "cit3" not in ids, "cit3 should not be drifted"
        ok += 1

        # 6. cit4 NOT drifted (not verified)
        assert "cit4" not in ids, "cit4 should not be drifted"
        ok += 1

        # 7. cit1 has 2 revisions after (t2 and t3 both > t1)
        cit1 = [r for r in d if r["citation_id"] == "cit1"][0]
        assert cit1["revisions_after"] == 2, f"cit1 revisions_after {cit1['revisions_after']}"
        ok += 1

        # 8. drift_by_tag returns correct tags
        bt = drift_by_tag(conn)
        tags = {r["tag"] for r in bt}
        assert "url" in tags and "doi" in tags, f"expected url and doi tags, got {tags}"
        ok += 1

        # 9. url tag has 2 drifted (cit1, cit5)
        url_row = [r for r in bt if r["tag"] == "url"][0]
        assert url_row["drifted"] == 2, f"url drifted {url_row['drifted']}"
        ok += 1

        # 10. doi tag has 1 drifted (cit2)
        doi_row = [r for r in bt if r["tag"] == "doi"][0]
        assert doi_row["drifted"] == 1, f"doi drifted {doi_row['drifted']}"
        ok += 1

        # 11. drift_by_depth returns buckets
        bd = drift_by_depth(conn)
        assert len(bd) >= 1, "expected at least one depth bucket"
        ok += 1

        # 12. summary totals
        s = drift_summary(conn)
        assert s["total_citations"] == 5, f"total_citations {s['total_citations']}"
        assert s["drifted"] == 3, f"drifted {s['drifted']}"
        assert s["unverified"] == 1, f"unverified {s['unverified']}"
        ok += 1

        # 13. JSON serialisation round-trips
        j = json.loads(json.dumps(s))
        assert j["drift_rate"] == s["drift_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = drift_summary(conn)
        assert s["total_citations"] == 0
        assert s["drifted"] == 0
        assert s["drift_rate"] == 0.0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Version citation drift analysis")
    ap.add_argument("command", choices=["drifted", "by-tag", "by-depth", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS version_citation_drift selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "drifted":
        rows = drifted_citations(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No drifted citations found.")
            else:
                print(f"{'citation_id':<14} {'chunk_id':<10} {'tag':<8} {'revisions':<10} {'latest_revision'}")
                for r in rows:
                    print(f"{r['citation_id']:<14} {r['chunk_id']:<10} {r['tag'] or '':<8} {r['revisions_after']:<10} {r['latest_revision']}")
    elif args.command == "by-tag":
        rows = drift_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'verified':<10} {'drifted':<10} {'drift_rate'}")
            for r in rows:
                print(f"{r['tag'] or '':<16} {r['total_verified']:<10} {r['drifted']:<10} {r['drift_rate']:.4f}")
    elif args.command == "by-depth":
        rows = drift_by_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'rev_depth':<12} {'drifted_citations'}")
            for r in rows:
                print(f"{r['revision_depth']:<12} {r['drifted_citations']}")
    elif args.command == "summary":
        s = drift_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
