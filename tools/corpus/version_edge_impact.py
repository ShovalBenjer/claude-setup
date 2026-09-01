#!/usr/bin/env python3
"""Version edge impact: edges whose endpoint content changed since detection.

chunk_evolution.py and version_churn.py analyse chunk_versions in isolation.
edge_reachability.py and edge_density.py analyse claim_edges without
considering content revisions.  No tool joins chunk_versions with
claim_edges to detect edges that may be stale because their source or
target chunk has been revised after the edge was detected.

Usage:
    python tools/corpus/version_edge_impact.py stale [--db PATH] [--json]
    python tools/corpus/version_edge_impact.py by-edge-type [--db PATH] [--json]
    python tools/corpus/version_edge_impact.py by-version-depth [--db PATH] [--json]
    python tools/corpus/version_edge_impact.py summary [--db PATH] [--json]
    python tools/corpus/version_edge_impact.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def stale_edges(conn) -> list[dict]:
    """Edges where at least one endpoint was revised after edge detection."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT NOT NULL,"
        "  word_count INTEGER NOT NULL,"
        "  snapshot_utc TEXT NOT NULL,"
        "  UNIQUE(chunk_id, version_num))"
    )
    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  e.detected_utc, e.source_chunk, e.target_chunk, "
        "  max(vs.snapshot_utc) AS src_latest_rev, "
        "  max(vt.snapshot_utc) AS tgt_latest_rev, "
        "  max(vs.version_num) AS src_depth, "
        "  max(vt.version_num) AS tgt_depth "
        "FROM claim_edges e "
        "LEFT JOIN chunk_versions vs "
        "  ON e.source_chunk = vs.chunk_id "
        "LEFT JOIN chunk_versions vt "
        "  ON e.target_chunk = vt.chunk_id "
        "GROUP BY e.edge_id "
        "HAVING (src_latest_rev IS NOT NULL "
        "        AND src_latest_rev > e.detected_utc) "
        "    OR (tgt_latest_rev IS NOT NULL "
        "        AND tgt_latest_rev > e.detected_utc)"
    ).fetchall()

    results = []
    for (eid, etype, conf, det, src, tgt,
         src_rev, tgt_rev, src_d, tgt_d) in rows:
        src_stale = (
            src_rev is not None and src_rev > det
        )
        tgt_stale = (
            tgt_rev is not None and tgt_rev > det
        )
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "detected_utc": det,
            "source_chunk": src,
            "target_chunk": tgt,
            "source_revised": src_stale,
            "target_revised": tgt_stale,
            "both_revised": src_stale and tgt_stale,
            "source_version_depth": src_d,
            "target_version_depth": tgt_d,
        })

    return results


def stale_by_edge_type(conn) -> list[dict]:
    """Stale edge counts per edge_type."""
    se = stale_edges(conn)
    if not se:
        return []

    by_type: dict[str, dict] = {}
    for e in se:
        et = e["edge_type"]
        if et not in by_type:
            by_type[et] = {
                "stale": 0, "both_revised": 0,
            }
        by_type[et]["stale"] += 1
        if e["both_revised"]:
            by_type[et]["both_revised"] += 1

    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    type_totals = {}
    for row in conn.execute(
        "SELECT edge_type, count(*) FROM claim_edges "
        "GROUP BY edge_type"
    ).fetchall():
        type_totals[row[0]] = row[1]

    results = []
    for et in sorted(by_type):
        d = by_type[et]
        tt = type_totals.get(et, 0)
        results.append({
            "edge_type": et,
            "stale_edges": d["stale"],
            "both_revised": d["both_revised"],
            "total_edges": tt,
            "stale_rate": (
                round(d["stale"] / tt, 4) if tt > 0 else 0.0
            ),
        })

    return results


def stale_by_version_depth(conn) -> list[dict]:
    """Stale edge counts bucketed by max endpoint version depth."""
    se = stale_edges(conn)
    if not se:
        return []

    buckets: dict[int, int] = {}
    for e in se:
        depth = max(
            e["source_version_depth"] or 0,
            e["target_version_depth"] or 0,
        )
        buckets[depth] = buckets.get(depth, 0) + 1

    total = sum(buckets.values())
    results = []
    for depth in sorted(buckets):
        results.append({
            "max_version_depth": depth,
            "stale_edges": buckets[depth],
            "rate": round(
                buckets[depth] / total, 4
            ) if total > 0 else 0.0,
        })

    return results


def version_edge_summary(conn) -> dict:
    """Aggregate version-edge impact statistics."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk_versions ("
        "  version_id TEXT PRIMARY KEY,"
        "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
        "  version_num INTEGER NOT NULL,"
        "  norm_sha256 TEXT NOT NULL,"
        "  word_count INTEGER NOT NULL,"
        "  snapshot_utc TEXT NOT NULL,"
        "  UNIQUE(chunk_id, version_num))"
    )

    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    if total_edges == 0:
        return {
            "total_edges": 0,
            "stale_edges": 0,
            "stale_rate": 0.0,
            "both_revised": 0,
            "source_only": 0,
            "target_only": 0,
            "most_stale_type": None,
            "versioned_chunks": 0,
        }

    se = stale_edges(conn)
    both = sum(1 for e in se if e["both_revised"])
    src_only = sum(
        1 for e in se
        if e["source_revised"] and not e["target_revised"]
    )
    tgt_only = sum(
        1 for e in se
        if e["target_revised"] and not e["source_revised"]
    )

    by_type = stale_by_edge_type(conn)
    most_stale = (
        max(by_type, key=lambda t: t["stale_rate"])
        if by_type else None
    )

    versioned = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "stale_edges": len(se),
        "stale_rate": round(
            len(se) / total_edges, 4
        ) if total_edges > 0 else 0.0,
        "both_revised": both,
        "source_only": src_only,
        "target_only": tgt_only,
        "most_stale_type": (
            most_stale["edge_type"] if most_stale else None
        ),
        "versioned_chunks": versioned,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "  version_id TEXT PRIMARY KEY,"
            "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
            "  version_num INTEGER NOT NULL,"
            "  norm_sha256 TEXT NOT NULL,"
            "  word_count INTEGER NOT NULL,"
            "  snapshot_utc TEXT NOT NULL,"
            "  UNIQUE(chunk_id, version_num))"
        )

        now = "2026-06-01T00:00:00Z"
        t1 = "2026-06-01T00:00:00Z"
        t2 = "2026-06-02T00:00:00Z"
        t3 = "2026-06-03T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(5):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted", now),
            )

        # Edges detected at t1:
        # e1: c1->c2 (both will be revised)
        # e2: c2->c3 (source revised, target not)
        # e3: c3->c4 (neither revised -- not stale)
        # e4: c4->c5 (target revised only)
        edges = [
            ("e1", "c1", "c2", "supports", "text", 0.9, t1),
            ("e2", "c2", "c3", "contradicts", "sem", 0.8, t1),
            ("e3", "c3", "c4", "refines", "version", 0.7, t1),
            ("e4", "c4", "c5", "duplicates", "simhash", 0.95, t1),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        # Versions: c1 revised at t2, c2 revised at t3,
        # c5 revised at t2
        versions = [
            ("v1", "c1", 2, "sha_c1_v2", 12, t2),
            ("v2", "c2", 2, "sha_c2_v2", 14, t3),
            ("v3", "c5", 2, "sha_c5_v2", 11, t2),
        ]
        for v in versions:
            conn.execute(
                "INSERT INTO chunk_versions (version_id, chunk_id, "
                "version_num, norm_sha256, word_count, "
                "snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)", v,
            )

        conn.commit()

        # 1: stale_edges returns 3 (e1, e2, e4; not e3)
        se = stale_edges(conn)
        se_ids = {e["edge_id"] for e in se}
        assert len(se) == 3
        assert "e3" not in se_ids
        checks += 1

        # 2: e1 has both revised (c1 at t2, c2 at t3)
        e1 = next(e for e in se if e["edge_id"] == "e1")
        assert e1["both_revised"] is True
        assert e1["source_revised"] is True
        assert e1["target_revised"] is True
        checks += 1

        # 3: e2 has source revised (c2 at t3), target not
        e2 = next(e for e in se if e["edge_id"] == "e2")
        assert e2["source_revised"] is True
        assert e2["target_revised"] is False
        checks += 1

        # 4: e4 has target revised (c5 at t2), source not
        e4 = next(e for e in se if e["edge_id"] == "e4")
        assert e4["source_revised"] is False
        assert e4["target_revised"] is True
        checks += 1

        # 5: stale_by_edge_type has entries
        bt = stale_by_edge_type(conn)
        assert len(bt) > 0
        checks += 1

        # 6: supports has 1 stale edge
        sup = next(t for t in bt if t["edge_type"] == "supports")
        assert sup["stale_edges"] == 1
        assert sup["both_revised"] == 1
        checks += 1

        # 7: contradicts has 1 stale, 0 both
        con = next(
            t for t in bt if t["edge_type"] == "contradicts"
        )
        assert con["stale_edges"] == 1
        assert con["both_revised"] == 0
        checks += 1

        # 8: stale_rate > 0 for affected types
        assert sup["stale_rate"] > 0
        checks += 1

        # 9: stale_by_version_depth has entries
        bd = stale_by_version_depth(conn)
        assert len(bd) > 0
        checks += 1

        # 10: all version depths are 2
        assert all(d["max_version_depth"] == 2 for d in bd)
        checks += 1

        # 11: summary totals
        summary = version_edge_summary(conn)
        assert summary["total_edges"] == 4
        assert summary["stale_edges"] == 3
        checks += 1

        # 12: summary side breakdown
        assert summary["both_revised"] == 1
        assert summary["source_only"] == 1
        assert summary["target_only"] == 1
        checks += 1

        # 13: summary stale rate
        assert summary["stale_rate"] == 0.75
        assert summary["versioned_chunks"] == 3
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(se)
        _ = json.dumps(bt)
        _ = json.dumps(bd)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = version_edge_summary(conn2)
        assert empty["total_edges"] == 0
        assert empty["stale_edges"] == 0
        checks += 1

    print(
        f"PASS version_edge_impact selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Version-edge impact analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_st = sub.add_parser("stale",
                          help="Stale edges after revisions")
    p_st.add_argument("--db", default=DEFAULT_DB)
    p_st.add_argument("--json", action="store_true")

    p_bt = sub.add_parser("by-edge-type",
                           help="Staleness per edge type")
    p_bt.add_argument("--db", default=DEFAULT_DB)
    p_bt.add_argument("--json", action="store_true")

    p_bd = sub.add_parser("by-version-depth",
                           help="Staleness by version depth")
    p_bd.add_argument("--db", default=DEFAULT_DB)
    p_bd.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Version-edge impact statistics")
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

    if args.cmd == "stale":
        results = stale_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No stale edges.")
            else:
                for r in results:
                    sides = []
                    if r["source_revised"]:
                        sides.append("src")
                    if r["target_revised"]:
                        sides.append("tgt")
                    print(f"  {r['edge_id']:12s}  "
                          f"{r['edge_type']:12s}  "
                          f"revised={'+'.join(sides)}  "
                          f"conf={r['confidence']:.2f}")

    elif args.cmd == "by-edge-type":
        results = stale_by_edge_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:12s}  "
                      f"stale={r['stale_edges']:4d}/"
                      f"{r['total_edges']:4d}  "
                      f"rate={r['stale_rate']:.3f}  "
                      f"both={r['both_revised']}")

    elif args.cmd == "by-version-depth":
        results = stale_by_version_depth(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  depth={r['max_version_depth']:2d}  "
                      f"stale={r['stale_edges']:4d}  "
                      f"rate={r['rate']:.3f}")

    elif args.cmd == "summary":
        result = version_edge_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total_edges']}  "
                  f"Stale: {result['stale_edges']}  "
                  f"Rate: {result['stale_rate']:.3f}")
            print(f"  Both revised: "
                  f"{result['both_revised']}  "
                  f"Source only: "
                  f"{result['source_only']}  "
                  f"Target only: "
                  f"{result['target_only']}")
            if result["most_stale_type"]:
                print(f"  Most stale type: "
                      f"{result['most_stale_type']}")

    conn.close()


if __name__ == "__main__":
    main()
