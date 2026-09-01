#!/usr/bin/env python3
"""Kind tag profile: which chunk kinds attract which tags.

chunk_kind_profile.py profiles kinds per source and per domain.
tag_landscape.py profiles tags corpus-wide.
No tool joins chunks.kind with chunk_tags to measure which chunk
kinds concentrate which tags, whether claims attract different tags
than code or prose chunks, or how tag diversity varies by kind.

Usage:
    python tools/corpus/kind_tag_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/kind_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/kind_tag_profile.py diversity [--db PATH] [--json]
    python tools/corpus/kind_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/kind_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_kind(conn) -> list[dict]:
    """Tag distribution per chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.kind
        ORDER BY tag_assignments DESC, c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def kinds_by_tag(conn) -> list[dict]:
    """Kind distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT c.kind) AS distinct_kinds,
               COUNT(ct.tag) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY distinct_kinds DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_kinds": r[1],
            "assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def kind_tag_diversity(conn) -> list[dict]:
    """Per-kind tag diversity: ratio of distinct tags to total assignments."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.kind
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "tagged_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def kind_tag_summary(conn) -> dict:
    """Aggregate kind-tag statistics."""
    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM chunks"
    ).fetchone()[0]

    kinds_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT c.kind)
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_tags"
    ).fetchone()[0]

    avg_tags_per_kind = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT c.kind, COUNT(DISTINCT ct.tag) AS tag_count
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.kind
        )
        """
    ).fetchone()[0]

    single_kind_tags = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT c.kind) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_kinds": total_kinds,
        "kinds_with_tags": kinds_with_tags,
        "kind_tag_coverage": round(kinds_with_tags / max(total_kinds, 1), 4),
        "total_distinct_tags": total_tags,
        "total_tag_assignments": total_assignments,
        "avg_tags_per_kind": avg_tags_per_kind or 0.0,
        "single_kind_tags": single_kind_tags,
        "single_kind_tag_rate": round(single_kind_tags / max(total_tags, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1,c2 are "claim"; c3 is "code"; c4 is "prose"; c5 is "claim" (no tags)
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

        # Tags: claims get law+tech+science, code gets tech, prose gets law
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "science", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "law", 0.75, t1))
        conn.commit()

        # 1. by-kind: "claim" has 3 distinct tags (law, tech, science)
        bk = tags_by_kind(conn)
        claim_row = [r for r in bk if r["kind"] == "claim"][0]
        assert claim_row["distinct_tags"] == 3
        ok += 1

        # 2. "claim" has 3 tag assignments
        assert claim_row["tag_assignments"] == 3
        ok += 1

        # 3. "code" has 1 distinct tag (tech)
        code_row = [r for r in bk if r["kind"] == "code"][0]
        assert code_row["distinct_tags"] == 1
        ok += 1

        # 4. "prose" has 1 distinct tag (law)
        prose_row = [r for r in bk if r["kind"] == "prose"][0]
        assert prose_row["distinct_tags"] == 1
        ok += 1

        # 5. by-tag: "tech" spans 2 kinds (claim, code)
        bt = kinds_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_kinds"] == 2
        ok += 1

        # 6. "science" spans 1 kind (claim only)
        sci = [r for r in bt if r["tag"] == "science"][0]
        assert sci["distinct_kinds"] == 1
        ok += 1

        # 7. "law" spans 2 kinds (claim, prose)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_kinds"] == 2
        ok += 1

        # 8. diversity: "claim" has 3/3=1.0
        div = kind_tag_diversity(conn)
        claim_div = [r for r in div if r["kind"] == "claim"][0]
        assert claim_div["diversity_ratio"] == 1.0
        ok += 1

        # 9. "code" not in diversity (only 1 assignment)
        code_div = [r for r in div if r["kind"] == "code"]
        assert len(code_div) == 0
        ok += 1

        # 10. summary: kinds_with_tags = 3 (claim, code, prose)
        s = kind_tag_summary(conn)
        assert s["kinds_with_tags"] == 3
        ok += 1

        # 11. total_distinct_tags = 3 (law, tech, science)
        assert s["total_distinct_tags"] == 3
        ok += 1

        # 12. single_kind_tags = 1 (science is claim-only)
        assert s["single_kind_tags"] == 1, f"expected 1, got {s['single_kind_tags']}"
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["kind_tag_coverage"] == s["kind_tag_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = kind_tag_summary(conn)
        assert s["kinds_with_tags"] == 0
        assert s["total_distinct_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Kind tag profile analysis")
    ap.add_argument("command", choices=["by-kind", "by-tag", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS kind_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-kind":
        rows = tags_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind tag data found.")
            else:
                print(f"{'kind':<15} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['kind']:<15} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = kinds_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag kind data found.")
            else:
                print(f"{'tag':<20} {'kinds':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_kinds']:<8} {r['assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = kind_tag_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kinds with multiple tags found.")
            else:
                print(f"{'kind':<15} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['kind']:<15} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['tagged_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = kind_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
