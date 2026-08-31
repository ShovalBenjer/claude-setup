#!/usr/bin/env python3
"""Artifact version conflicts: contradicting edges between same-name artifacts.

artifact_graph.py finds co-occurrence relationships between artifacts but
never inspects whether linked artifacts have the same name with differing
versions.  artifact_edge_profile.py cross-tabulates artifact_type against
edge_type but never checks name/version matches.  No tool detects when a
contradicts edge links two chunks that reference the same artifact name
with different versions, which is a version conflict signal.

Usage:
    python tools/corpus/artifact_version_conflicts.py conflicts [--db PATH] [--json]
    python tools/corpus/artifact_version_conflicts.py by-artifact [--db PATH] [--json]
    python tools/corpus/artifact_version_conflicts.py all-version-edges [--db PATH] [--json]
    python tools/corpus/artifact_version_conflicts.py summary [--db PATH] [--json]
    python tools/corpus/artifact_version_conflicts.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def version_conflict_edges(conn) -> list[dict]:
    """Edges where both endpoints reference the same artifact name with different versions."""
    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  e.source_chunk, e.target_chunk, "
        "  a1.name, a1.version AS src_version, "
        "  a2.version AS tgt_version, "
        "  a1.artifact_type "
        "FROM claim_edges e "
        "JOIN artifacts a1 ON e.source_chunk = a1.chunk_id "
        "JOIN artifacts a2 ON e.target_chunk = a2.chunk_id "
        "WHERE a1.name = a2.name "
        "  AND a1.version IS NOT NULL "
        "  AND a2.version IS NOT NULL "
        "  AND a1.version != a2.version "
        "ORDER BY a1.name, e.edge_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for (eid, etype, conf, src, tgt,
         name, src_ver, tgt_ver, atype) in rows:
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "source_chunk": src,
            "target_chunk": tgt,
            "artifact_name": name,
            "source_version": src_ver,
            "target_version": tgt_ver,
            "artifact_type": atype,
            "is_contradiction": etype == "contradicts",
        })

    return results


def conflicts_by_artifact(conn) -> list[dict]:
    """Version conflict counts per artifact name."""
    vce = version_conflict_edges(conn)
    if not vce:
        return []

    by_name: dict[str, dict] = {}
    for e in vce:
        name = e["artifact_name"]
        if name not in by_name:
            by_name[name] = {
                "type": e["artifact_type"],
                "edges": 0,
                "contradictions": 0,
                "versions": set(),
            }
        by_name[name]["edges"] += 1
        if e["is_contradiction"]:
            by_name[name]["contradictions"] += 1
        by_name[name]["versions"].add(e["source_version"])
        by_name[name]["versions"].add(e["target_version"])

    results = []
    for name in sorted(by_name):
        d = by_name[name]
        results.append({
            "artifact_name": name,
            "artifact_type": d["type"],
            "conflict_edges": d["edges"],
            "contradiction_edges": d["contradictions"],
            "distinct_versions": len(d["versions"]),
            "versions": sorted(d["versions"]),
        })

    return results


def all_version_edges(conn) -> list[dict]:
    """All edges between chunks sharing an artifact name, regardless of version match."""
    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  a1.name, a1.version AS src_version, "
        "  a2.version AS tgt_version "
        "FROM claim_edges e "
        "JOIN artifacts a1 ON e.source_chunk = a1.chunk_id "
        "JOIN artifacts a2 ON e.target_chunk = a2.chunk_id "
        "WHERE a1.name = a2.name "
        "ORDER BY a1.name, e.edge_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for eid, etype, conf, name, src_ver, tgt_ver in rows:
        same = (src_ver == tgt_ver) or (
            src_ver is None and tgt_ver is None
        )
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "artifact_name": name,
            "source_version": src_ver,
            "target_version": tgt_ver,
            "same_version": same,
        })

    return results


def version_conflict_summary(conn) -> dict:
    """Aggregate version conflict statistics."""
    vce = version_conflict_edges(conn)
    ave = all_version_edges(conn)

    if not ave:
        return {
            "total_same_name_edges": 0,
            "version_conflict_edges": 0,
            "conflict_rate": 0.0,
            "contradiction_conflicts": 0,
            "artifacts_with_conflicts": 0,
            "max_versions_artifact": None,
        }

    conflicts = len(vce)
    contradictions = sum(1 for e in vce if e["is_contradiction"])

    by_art = conflicts_by_artifact(conn)
    max_ver = (
        max(by_art, key=lambda a: a["distinct_versions"])
        if by_art else None
    )

    return {
        "total_same_name_edges": len(ave),
        "version_conflict_edges": conflicts,
        "conflict_rate": (
            round(conflicts / len(ave), 4)
            if len(ave) > 0 else 0.0
        ),
        "contradiction_conflicts": contradictions,
        "artifacts_with_conflicts": len(by_art),
        "max_versions_artifact": (
            max_ver["artifact_name"] if max_ver else None
        ),
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

        # Artifacts:
        # c1: torch 1.0
        # c2: torch 2.0  (different version from c1)
        # c3: torch 2.0  (same version as c2)
        # c4: numpy 1.24
        # c5: torch (no version)
        artifacts = [
            ("a1", "c1", "library", "torch", "1.0", None, 1, None),
            ("a2", "c2", "library", "torch", "2.0", None, 1, None),
            ("a3", "c3", "library", "torch", "2.0", None, 0, None),
            ("a4", "c4", "library", "numpy", "1.24", None, 1, None),
            ("a5", "c5", "library", "torch", None, None, 0, None),
        ]
        for a in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, "
                "implemented, evidence_path) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", a,
            )

        # Edges:
        # e1: c1(torch 1.0) contradicts c2(torch 2.0) = conflict!
        # e2: c2(torch 2.0) supports c3(torch 2.0) = same version
        # e3: c1(torch 1.0) refines c3(torch 2.0) = conflict!
        # e4: c1(torch 1.0) supports c4(numpy 1.24) = different name
        # e5: c1(torch 1.0) duplicates c5(torch None) = no version
        edges = [
            ("e1", "c1", "c2", "contradicts", "semantic", 0.9, now),
            ("e2", "c2", "c3", "supports", "text", 0.85, now),
            ("e3", "c1", "c3", "refines", "version", 0.7, now),
            ("e4", "c1", "c4", "supports", "text", 0.8, now),
            ("e5", "c1", "c5", "duplicates", "simhash", 0.95, now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        conn.commit()

        # 1: version_conflict_edges returns 2 (e1, e3)
        vce = version_conflict_edges(conn)
        assert len(vce) == 2
        checks += 1

        # 2: e1 is a contradiction conflict
        e1 = next(e for e in vce if e["edge_id"] == "e1")
        assert e1["artifact_name"] == "torch"
        assert e1["source_version"] == "1.0"
        assert e1["target_version"] == "2.0"
        assert e1["is_contradiction"] is True
        checks += 1

        # 3: e3 is a non-contradiction conflict (refines)
        e3 = next(e for e in vce if e["edge_id"] == "e3")
        assert e3["is_contradiction"] is False
        assert e3["edge_type"] == "refines"
        checks += 1

        # 4: e2 (same version) not in conflicts
        vce_ids = {e["edge_id"] for e in vce}
        assert "e2" not in vce_ids
        checks += 1

        # 5: e4 (different name) not in conflicts
        assert "e4" not in vce_ids
        checks += 1

        # 6: e5 (null version) not in conflicts
        assert "e5" not in vce_ids
        checks += 1

        # 7: conflicts_by_artifact returns 1 (torch)
        ba = conflicts_by_artifact(conn)
        assert len(ba) == 1
        assert ba[0]["artifact_name"] == "torch"
        checks += 1

        # 8: torch has 2 conflict edges, 1 contradiction
        assert ba[0]["conflict_edges"] == 2
        assert ba[0]["contradiction_edges"] == 1
        checks += 1

        # 9: torch has 2 distinct versions (1.0, 2.0)
        assert ba[0]["distinct_versions"] == 2
        assert set(ba[0]["versions"]) == {"1.0", "2.0"}
        checks += 1

        # 10: all_version_edges includes same-version e2
        ave = all_version_edges(conn)
        ave_ids = {e["edge_id"] for e in ave}
        assert "e2" in ave_ids
        checks += 1

        # 11: e2 is same_version=True
        e2_ave = next(e for e in ave if e["edge_id"] == "e2")
        assert e2_ave["same_version"] is True
        checks += 1

        # 12: summary totals
        summary = version_conflict_summary(conn)
        assert summary["version_conflict_edges"] == 2
        assert summary["contradiction_conflicts"] == 1
        assert summary["artifacts_with_conflicts"] == 1
        checks += 1

        # 13: summary conflict rate
        assert summary["total_same_name_edges"] > 0
        assert summary["conflict_rate"] > 0
        assert summary["max_versions_artifact"] == "torch"
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(vce)
        _ = json.dumps(ba)
        _ = json.dumps(ave)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = version_conflict_edges(conn2)
        assert empty == []
        empty_summary = version_conflict_summary(conn2)
        assert empty_summary["version_conflict_edges"] == 0
        checks += 1

    print(
        f"PASS artifact_version_conflicts selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact version conflict detection"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_cf = sub.add_parser("conflicts",
                          help="Version conflict edges")
    p_cf.add_argument("--db", default=DEFAULT_DB)
    p_cf.add_argument("--json", action="store_true")

    p_ba = sub.add_parser("by-artifact",
                           help="Conflicts per artifact name")
    p_ba.add_argument("--db", default=DEFAULT_DB)
    p_ba.add_argument("--json", action="store_true")

    p_av = sub.add_parser("all-version-edges",
                           help="All same-name artifact edges")
    p_av.add_argument("--db", default=DEFAULT_DB)
    p_av.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Version conflict statistics")
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

    if args.cmd == "conflicts":
        results = version_conflict_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                contr = "!" if r["is_contradiction"] else " "
                print(f"  {r['artifact_name']:16s}  "
                      f"{r['source_version']:8s} vs "
                      f"{r['target_version']:8s}  "
                      f"{r['edge_type']:12s}  "
                      f"conf={r['confidence']:.2f}  "
                      f"[{contr}]")

    elif args.cmd == "by-artifact":
        results = conflicts_by_artifact(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_name']:16s}  "
                      f"conflicts={r['conflict_edges']:3d}  "
                      f"contradictions="
                      f"{r['contradiction_edges']:3d}  "
                      f"versions={r['versions']}")

    elif args.cmd == "all-version-edges":
        results = all_version_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                sv = r["source_version"] or "?"
                tv = r["target_version"] or "?"
                same = "=" if r["same_version"] else "!"
                print(f"  {r['artifact_name']:16s}  "
                      f"{sv:8s} {same} {tv:8s}  "
                      f"{r['edge_type']:12s}")

    elif args.cmd == "summary":
        result = version_conflict_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Same-name edges: "
                  f"{result['total_same_name_edges']}  "
                  f"Conflicts: "
                  f"{result['version_conflict_edges']}  "
                  f"Rate: {result['conflict_rate']:.3f}")
            print(f"  Contradictions: "
                  f"{result['contradiction_conflicts']}  "
                  f"Artifacts: "
                  f"{result['artifacts_with_conflicts']}")
            if result["max_versions_artifact"]:
                print(f"  Most versions: "
                      f"{result['max_versions_artifact']}")

    conn.close()


if __name__ == "__main__":
    main()
