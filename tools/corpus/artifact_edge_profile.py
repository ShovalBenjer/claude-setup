#!/usr/bin/env python3
"""Artifact-edge profile: edge patterns correlated with artifact type.

artifact_graph.py uses claim_edges only to connect artifact pairs.
No tool cross-tabulates artifact_type or implemented status against
edge_type or confidence.  This tool answers whether chunks containing
implemented APIs attract more supports edges than chunks with
unimplemented patterns, and whether confidence differs by artifact type.

Usage:
    python tools/corpus/artifact_edge_profile.py edge-by-type [--db PATH] [--json]
    python tools/corpus/artifact_edge_profile.py confidence [--db PATH] [--json]
    python tools/corpus/artifact_edge_profile.py impl-edges [--db PATH] [--json]
    python tools/corpus/artifact_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/artifact_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_artifact_type(conn) -> list[dict]:
    """Edge type distribution per artifact type."""
    rows = conn.execute(
        "SELECT a.artifact_type, e.edge_type, count(*) AS cnt "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "JOIN claim_edges e ON (c.chunk_id = e.source_chunk "
        "    OR c.chunk_id = e.target_chunk) "
        "GROUP BY a.artifact_type, e.edge_type "
        "ORDER BY a.artifact_type, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_at: dict[str, dict] = {}
    for atype, etype, cnt in rows:
        if atype not in by_at:
            by_at[atype] = {"total": 0, "breakdown": {}}
        by_at[atype]["total"] += cnt
        by_at[atype]["breakdown"][etype] = (
            by_at[atype]["breakdown"].get(etype, 0) + cnt
        )

    results = []
    for atype in sorted(by_at):
        info = by_at[atype]
        dominant = max(
            info["breakdown"], key=info["breakdown"].get
        )
        results.append({
            "artifact_type": atype,
            "edge_count": info["total"],
            "dominant_edge_type": dominant,
            "breakdown": info["breakdown"],
        })

    return results


def confidence_by_artifact_type(conn) -> list[dict]:
    """Mean edge confidence per artifact type."""
    rows = conn.execute(
        "SELECT a.artifact_type, e.confidence "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "JOIN claim_edges e ON (c.chunk_id = e.source_chunk "
        "    OR c.chunk_id = e.target_chunk)"
    ).fetchall()

    if not rows:
        return []

    by_at: dict[str, list[float]] = {}
    for atype, conf in rows:
        if atype not in by_at:
            by_at[atype] = []
        by_at[atype].append(conf)

    results = []
    for atype in sorted(by_at):
        confs = by_at[atype]
        n = len(confs)
        results.append({
            "artifact_type": atype,
            "edge_count": n,
            "mean_confidence": round(sum(confs) / n, 4),
            "min_confidence": round(min(confs), 4),
            "max_confidence": round(max(confs), 4),
        })

    return results


def implementation_edge_profile(conn) -> list[dict]:
    """Edge patterns for implemented vs unimplemented artifacts."""
    rows = conn.execute(
        "SELECT a.implemented, e.edge_type, count(*) AS cnt "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "JOIN claim_edges e ON (c.chunk_id = e.source_chunk "
        "    OR c.chunk_id = e.target_chunk) "
        "GROUP BY a.implemented, e.edge_type "
        "ORDER BY a.implemented, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_impl: dict[int, dict] = {}
    for impl, etype, cnt in rows:
        if impl not in by_impl:
            by_impl[impl] = {"total": 0, "breakdown": {}}
        by_impl[impl]["total"] += cnt
        by_impl[impl]["breakdown"][etype] = (
            by_impl[impl]["breakdown"].get(etype, 0) + cnt
        )

    results = []
    for impl in sorted(by_impl):
        info = by_impl[impl]
        label = "implemented" if impl else "unimplemented"
        dominant = max(
            info["breakdown"], key=info["breakdown"].get
        )
        results.append({
            "status": label,
            "edge_count": info["total"],
            "dominant_edge_type": dominant,
            "breakdown": info["breakdown"],
        })

    return results


def artifact_edge_summary(conn) -> dict:
    """Aggregate artifact-edge profile statistics."""
    ebt = edges_by_artifact_type(conn)
    cbt = confidence_by_artifact_type(conn)
    iep = implementation_edge_profile(conn)

    if not ebt:
        return {
            "artifact_types_with_edges": 0,
            "total_artifact_edges": 0,
            "highest_edge_type": None,
            "highest_confidence_type": None,
            "impl_vs_unimpl": {},
        }

    total_edges = sum(e["edge_count"] for e in ebt)
    highest_edge = max(ebt, key=lambda e: e["edge_count"])
    highest_conf = max(
        cbt, key=lambda c: c["mean_confidence"]
    ) if cbt else None

    impl_map = {r["status"]: r["edge_count"] for r in iep}

    return {
        "artifact_types_with_edges": len(ebt),
        "total_artifact_edges": total_edges,
        "highest_edge_type": highest_edge["artifact_type"],
        "highest_confidence_type": (
            highest_conf["artifact_type"] if highest_conf else None
        ),
        "impl_vs_unimpl": impl_map,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

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

        for i in range(4):
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

        # Artifacts: library(impl) on c1, api(impl) on c2,
        # pattern(unimpl) on c3, command(impl) on c4
        artifacts = [
            ("a1", "c1", "library", "React", 1),
            ("a2", "c2", "api", "REST", 1),
            ("a3", "c3", "pattern", "Observer", 0),
            ("a4", "c4", "command", "npm", 1),
        ]
        for aid, cid, atype, name, impl in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, "
                "implemented, evidence_path) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, None, None, impl, None),
            )

        # Edges: c1->c2 supports (high conf), c1->c3 contradicts,
        # c2->c4 supports, c3->c4 refines (low conf)
        edges = [
            ("e1", "c1", "c2", "supports", "shared API", 0.9),
            ("e2", "c1", "c3", "contradicts", "design", 0.7),
            ("e3", "c2", "c4", "supports", "tooling", 0.85),
            ("e4", "c3", "c4", "refines", "pattern", 0.5),
        ]
        for eid, sc, tc, etype, basis, conf in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (eid, sc, tc, etype, basis, conf, now),
            )

        conn.commit()

        # 1: edges-by-artifact-type returns entries
        ebt = edges_by_artifact_type(conn)
        assert len(ebt) > 0
        checks += 1

        # 2: library type has edges (c1 is in e1 src, e2 src)
        lib = next(
            (e for e in ebt if e["artifact_type"] == "library"),
            None
        )
        assert lib is not None
        assert lib["edge_count"] >= 2
        checks += 1

        # 3: api type has edges (c2 is in e1 tgt, e3 src)
        api = next(
            (e for e in ebt if e["artifact_type"] == "api"), None
        )
        assert api is not None
        checks += 1

        # 4: confidence returns entries
        cbt = confidence_by_artifact_type(conn)
        assert len(cbt) > 0
        checks += 1

        # 5: library mean confidence involves e1(0.9) and e2(0.7)
        lib_c = next(
            c for c in cbt if c["artifact_type"] == "library"
        )
        assert lib_c["mean_confidence"] > 0.0
        checks += 1

        # 6: pattern has lower confidence (e2 0.7, e4 0.5)
        pat_c = next(
            (c for c in cbt if c["artifact_type"] == "pattern"),
            None
        )
        assert pat_c is not None
        checks += 1

        # 7: implementation edge profile returns entries
        iep = implementation_edge_profile(conn)
        assert len(iep) > 0
        checks += 1

        # 8: implemented status has edges
        impl_entry = next(
            (r for r in iep if r["status"] == "implemented"), None
        )
        assert impl_entry is not None
        assert impl_entry["edge_count"] > 0
        checks += 1

        # 9: unimplemented status has edges
        unimpl = next(
            (r for r in iep if r["status"] == "unimplemented"), None
        )
        assert unimpl is not None
        checks += 1

        # 10: implemented has more edges than unimplemented
        assert impl_entry["edge_count"] > unimpl["edge_count"]
        checks += 1

        # 11: summary has correct totals
        summary = artifact_edge_summary(conn)
        assert summary["artifact_types_with_edges"] > 0
        assert summary["total_artifact_edges"] > 0
        checks += 1

        # 12: highest confidence type identified
        assert summary["highest_confidence_type"] is not None
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(ebt)
        _ = json.dumps(cbt)
        _ = json.dumps(iep)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = edges_by_artifact_type(conn2)
        assert empty == []
        empty_summary = artifact_edge_summary(conn2)
        assert empty_summary["artifact_types_with_edges"] == 0
        checks += 1

    print(
        f"PASS artifact_edge_profile selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact-edge profile analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ebt = sub.add_parser("edge-by-type",
                           help="Edge types per artifact type")
    p_ebt.add_argument("--db", default=DEFAULT_DB)
    p_ebt.add_argument("--json", action="store_true")

    p_conf = sub.add_parser("confidence",
                            help="Edge confidence by artifact type")
    p_conf.add_argument("--db", default=DEFAULT_DB)
    p_conf.add_argument("--json", action="store_true")

    p_impl = sub.add_parser("impl-edges",
                            help="Edges by implementation status")
    p_impl.add_argument("--db", default=DEFAULT_DB)
    p_impl.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Artifact-edge statistics")
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

    if args.cmd == "edge-by-type":
        results = edges_by_artifact_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_type']:12s}  "
                      f"edges={r['edge_count']:3d}  "
                      f"dominant={r['dominant_edge_type']}  "
                      f"{r['breakdown']}")

    elif args.cmd == "confidence":
        results = confidence_by_artifact_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_type']:12s}  "
                      f"n={r['edge_count']}  "
                      f"mean={r['mean_confidence']:.3f}  "
                      f"min={r['min_confidence']:.3f}  "
                      f"max={r['max_confidence']:.3f}")

    elif args.cmd == "impl-edges":
        results = implementation_edge_profile(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['status']:16s}  "
                      f"edges={r['edge_count']}  "
                      f"dominant={r['dominant_edge_type']}  "
                      f"{r['breakdown']}")

    elif args.cmd == "summary":
        result = artifact_edge_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifact types with edges: "
                  f"{result['artifact_types_with_edges']}  "
                  f"Total edges: "
                  f"{result['total_artifact_edges']}")
            if result["highest_edge_type"]:
                print(f"  Most edges: "
                      f"{result['highest_edge_type']}  "
                      f"Highest confidence: "
                      f"{result['highest_confidence_type']}")
            if result["impl_vs_unimpl"]:
                print(f"  Impl vs unimpl: "
                      f"{result['impl_vs_unimpl']}")

    conn.close()


if __name__ == "__main__":
    main()
