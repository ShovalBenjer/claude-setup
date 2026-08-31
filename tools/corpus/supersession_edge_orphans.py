#!/usr/bin/env python3
"""Supersession edge orphans: edges stranded by source supersession.

supersession_analysis.py analyses the sources.supersedes column (chain
depths, rates by kind) but never joins with claim_edges.  source_chain.py
walks supersession chains but never checks downstream edge impact.  No
tool identifies claim_edges pointing to or from chunks whose source has
been superseded, leaving edges that may need re-evaluation or resolution.

Usage:
    python tools/corpus/supersession_edge_orphans.py orphans [--db PATH] [--json]
    python tools/corpus/supersession_edge_orphans.py by-type [--db PATH] [--json]
    python tools/corpus/supersession_edge_orphans.py resolvable [--db PATH] [--json]
    python tools/corpus/supersession_edge_orphans.py summary [--db PATH] [--json]
    python tools/corpus/supersession_edge_orphans.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _superseded_source_ids(conn) -> set[str]:
    """Source IDs that have been superseded by another source."""
    rows = conn.execute(
        "SELECT source_id FROM sources "
        "WHERE source_id IN ("
        "  SELECT supersedes FROM sources "
        "  WHERE supersedes IS NOT NULL"
        ")"
    ).fetchall()
    return {r[0] for r in rows}


def orphaned_edges(conn) -> list[dict]:
    """Edges where at least one endpoint chunk belongs to a superseded source."""
    superseded = _superseded_source_ids(conn)
    if not superseded:
        return []

    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  e.source_chunk, e.target_chunk, "
        "  e.resolution, "
        "  cs.source_id AS src_source, "
        "  ct.source_id AS tgt_source "
        "FROM claim_edges e "
        "JOIN chunks cs ON e.source_chunk = cs.chunk_id "
        "JOIN chunks ct ON e.target_chunk = ct.chunk_id "
        "ORDER BY e.edge_id"
    ).fetchall()

    results = []
    for (eid, etype, conf, src_chunk, tgt_chunk,
         resolution, src_source, tgt_source) in rows:
        src_superseded = src_source in superseded
        tgt_superseded = tgt_source in superseded
        if not (src_superseded or tgt_superseded):
            continue
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "source_chunk": src_chunk,
            "target_chunk": tgt_chunk,
            "resolution": resolution,
            "source_superseded": src_superseded,
            "target_superseded": tgt_superseded,
            "both_superseded": src_superseded and tgt_superseded,
        })

    return results


def orphans_by_edge_type(conn) -> list[dict]:
    """Orphaned edge counts per edge_type."""
    orph = orphaned_edges(conn)
    if not orph:
        return []

    by_type: dict[str, dict] = {}
    for e in orph:
        t = e["edge_type"]
        if t not in by_type:
            by_type[t] = {"total": 0, "resolved": 0, "both": 0}
        by_type[t]["total"] += 1
        if e["resolution"] is not None:
            by_type[t]["resolved"] += 1
        if e["both_superseded"]:
            by_type[t]["both"] += 1

    results = []
    for etype in sorted(by_type):
        d = by_type[etype]
        results.append({
            "edge_type": etype,
            "orphaned_count": d["total"],
            "resolved_count": d["resolved"],
            "unresolved_count": d["total"] - d["resolved"],
            "both_superseded": d["both"],
        })

    return results


def resolvable_orphans(conn) -> list[dict]:
    """Orphaned edges that have no resolution yet."""
    orph = orphaned_edges(conn)
    return [e for e in orph if e["resolution"] is None]


def orphan_summary(conn) -> dict:
    """Aggregate supersession-orphan statistics."""
    orph = orphaned_edges(conn)

    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    if not orph:
        return {
            "total_edges": total_edges,
            "orphaned_edges": 0,
            "orphan_rate": 0.0,
            "resolved_orphans": 0,
            "unresolved_orphans": 0,
            "both_superseded": 0,
            "source_only_superseded": 0,
            "target_only_superseded": 0,
        }

    resolved = sum(1 for e in orph if e["resolution"] is not None)
    both = sum(1 for e in orph if e["both_superseded"])
    src_only = sum(
        1 for e in orph
        if e["source_superseded"] and not e["target_superseded"]
    )
    tgt_only = sum(
        1 for e in orph
        if e["target_superseded"] and not e["source_superseded"]
    )

    return {
        "total_edges": total_edges,
        "orphaned_edges": len(orph),
        "orphan_rate": (
            round(len(orph) / total_edges, 4)
            if total_edges > 0 else 0.0
        ),
        "resolved_orphans": resolved,
        "unresolved_orphans": len(orph) - resolved,
        "both_superseded": both,
        "source_only_superseded": src_only,
        "target_only_superseded": tgt_only,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        # s1 is superseded by s2; s3 is not superseded
        for sid, uri, sup in [
            ("s1", "https://s1.com", None),
            ("s2", "https://s2.com", "s1"),
            ("s3", "https://s3.com", None),
        ]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, "
                "license_evidence, publisher, published_utc, "
                "fetched_utc, upstream_rev, upstream_mtime, liveness, "
                "content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, sup),
            )

        # c1,c2 from s1 (superseded); c3,c4 from s2; c5,c6 from s3
        chunks = [
            ("c1", "s1", 0), ("c2", "s1", 1),
            ("c3", "s2", 0), ("c4", "s2", 1),
            ("c5", "s3", 0), ("c6", "s3", 1),
        ]
        for cid, sid, ordinal in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", "claim", "en",
                 f"text {cid}", f"text {cid}", 10,
                 f"sha_{cid}", 0, 0, "accepted", now),
            )

        # Edges:
        # e1: c1(s1,superseded) -> c3(s2) = orphan (src superseded)
        # e2: c3(s2) -> c2(s1,superseded) = orphan (tgt superseded)
        # e3: c1(s1) -> c2(s1) = orphan (both superseded)
        # e4: c3(s2) -> c5(s3) = NOT orphan
        # e5: c5(s3) -> c6(s3) = NOT orphan
        # e6: c4(s2) -> c1(s1,superseded) = orphan (tgt), resolved
        edges = [
            ("e1", "c1", "c3", "supports", "text", 0.9, now,
             None, None),
            ("e2", "c3", "c2", "contradicts", "semantic", 0.7, now,
             None, None),
            ("e3", "c1", "c2", "duplicates", "simhash", 0.95, now,
             None, None),
            ("e4", "c3", "c5", "supports", "text", 0.8, now,
             None, None),
            ("e5", "c5", "c6", "refines", "version", 0.85, now,
             None, None),
            ("e6", "c4", "c1", "supersedes", "chain", 0.99, now,
             "superseded", now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc, resolution, resolved_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)", e,
            )

        conn.commit()

        # 1: orphaned_edges returns 4 (e1, e2, e3, e6)
        orph = orphaned_edges(conn)
        assert len(orph) == 4
        checks += 1

        # 2: e1 has source_superseded=True, target_superseded=False
        e1 = next(e for e in orph if e["edge_id"] == "e1")
        assert e1["source_superseded"] is True
        assert e1["target_superseded"] is False
        checks += 1

        # 3: e2 has source_superseded=False, target_superseded=True
        e2 = next(e for e in orph if e["edge_id"] == "e2")
        assert e2["source_superseded"] is False
        assert e2["target_superseded"] is True
        checks += 1

        # 4: e3 has both_superseded=True
        e3 = next(e for e in orph if e["edge_id"] == "e3")
        assert e3["both_superseded"] is True
        checks += 1

        # 5: e6 is orphaned and resolved
        e6 = next(e for e in orph if e["edge_id"] == "e6")
        assert e6["resolution"] == "superseded"
        assert e6["target_superseded"] is True
        checks += 1

        # 6: e4 and e5 are NOT orphaned
        orph_ids = {e["edge_id"] for e in orph}
        assert "e4" not in orph_ids
        assert "e5" not in orph_ids
        checks += 1

        # 7: orphans_by_edge_type counts
        bt = orphans_by_edge_type(conn)
        assert len(bt) == 4
        checks += 1

        # 8: supports type has 1 orphan
        sup = next(t for t in bt if t["edge_type"] == "supports")
        assert sup["orphaned_count"] == 1
        assert sup["unresolved_count"] == 1
        checks += 1

        # 9: supersedes type has 1 orphan, resolved
        sups = next(t for t in bt if t["edge_type"] == "supersedes")
        assert sups["orphaned_count"] == 1
        assert sups["resolved_count"] == 1
        checks += 1

        # 10: resolvable_orphans returns 3 (e1, e2, e3)
        res = resolvable_orphans(conn)
        assert len(res) == 3
        res_ids = {e["edge_id"] for e in res}
        assert res_ids == {"e1", "e2", "e3"}
        checks += 1

        # 11: summary totals
        summary = orphan_summary(conn)
        assert summary["total_edges"] == 6
        assert summary["orphaned_edges"] == 4
        checks += 1

        # 12: summary orphan rate = 4/6
        assert abs(summary["orphan_rate"] - 0.6667) < 0.001
        checks += 1

        # 13: summary breakdown
        assert summary["resolved_orphans"] == 1
        assert summary["unresolved_orphans"] == 3
        assert summary["both_superseded"] == 1
        assert summary["source_only_superseded"] == 1
        assert summary["target_only_superseded"] == 2
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(orph)
        _ = json.dumps(bt)
        _ = json.dumps(res)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = orphaned_edges(conn2)
        assert empty == []
        empty_summary = orphan_summary(conn2)
        assert empty_summary["orphaned_edges"] == 0
        checks += 1

    print(
        f"PASS supersession_edge_orphans selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supersession edge orphan analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_or = sub.add_parser("orphans",
                          help="Edges with superseded endpoints")
    p_or.add_argument("--db", default=DEFAULT_DB)
    p_or.add_argument("--json", action="store_true")

    p_bt = sub.add_parser("by-type",
                           help="Orphan counts per edge type")
    p_bt.add_argument("--db", default=DEFAULT_DB)
    p_bt.add_argument("--json", action="store_true")

    p_res = sub.add_parser("resolvable",
                            help="Unresolved orphaned edges")
    p_res.add_argument("--db", default=DEFAULT_DB)
    p_res.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Orphan statistics")
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

    if args.cmd == "orphans":
        results = orphaned_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                ss = "Y" if r["source_superseded"] else "N"
                ts = "Y" if r["target_superseded"] else "N"
                res = r["resolution"] or "-"
                print(f"  {r['edge_id']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"src_sup={ss}  tgt_sup={ts}  "
                      f"res={res}")

    elif args.cmd == "by-type":
        results = orphans_by_edge_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:12s}  "
                      f"orphaned={r['orphaned_count']:3d}  "
                      f"resolved={r['resolved_count']:3d}  "
                      f"unresolved={r['unresolved_count']:3d}")

    elif args.cmd == "resolvable":
        results = resolvable_orphans(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_id']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"conf={r['confidence']:.2f}")

    elif args.cmd == "summary":
        result = orphan_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total_edges']}  "
                  f"Orphaned: {result['orphaned_edges']}  "
                  f"Rate: {result['orphan_rate']:.3f}")
            print(f"  Resolved: {result['resolved_orphans']}  "
                  f"Unresolved: {result['unresolved_orphans']}")
            print(f"  Both superseded: "
                  f"{result['both_superseded']}  "
                  f"Src only: "
                  f"{result['source_only_superseded']}  "
                  f"Tgt only: "
                  f"{result['target_only_superseded']}")

    conn.close()


if __name__ == "__main__":
    main()
