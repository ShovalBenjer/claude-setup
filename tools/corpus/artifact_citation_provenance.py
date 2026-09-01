#!/usr/bin/env python3
"""Artifact citation provenance: which artifacts have citation backing.

artifact_adoption.py joins artifacts with chunks and sources but never
touches citations.  artifact_edge_profile.py joins artifacts with
claim_edges but never touches citations.  No tool joins artifacts with
citations via their shared chunk_id to show which technology references
have evidentiary backing versus being unsubstantiated mentions.

Usage:
    python tools/corpus/artifact_citation_provenance.py by-artifact [--db PATH] [--json]
    python tools/corpus/artifact_citation_provenance.py unbacked [--db PATH] [--json]
    python tools/corpus/artifact_citation_provenance.py by-type [--db PATH] [--json]
    python tools/corpus/artifact_citation_provenance.py summary [--db PATH] [--json]
    python tools/corpus/artifact_citation_provenance.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def artifacts_with_citations(conn) -> list[dict]:
    """Per-artifact citation backing via chunk_id join."""
    rows = conn.execute(
        "SELECT a.artifact_id, a.name, a.artifact_type, "
        "  a.implemented, a.version, "
        "  count(DISTINCT ci.citation_id) AS total_cites, "
        "  count(DISTINCT CASE WHEN ci.verified = 1 "
        "    THEN ci.citation_id END) AS verified_cites "
        "FROM artifacts a "
        "LEFT JOIN citations ci ON a.chunk_id = ci.chunk_id "
        "GROUP BY a.artifact_id "
        "ORDER BY a.name"
    ).fetchall()

    if not rows:
        return []

    results = []
    for (aid, name, atype, impl, ver,
         total, verified) in rows:
        backed = total > 0
        results.append({
            "artifact_id": aid,
            "name": name,
            "artifact_type": atype,
            "implemented": impl,
            "version": ver,
            "citation_count": total,
            "verified_count": verified,
            "backed": backed,
        })

    return results


def unbacked_artifacts(conn) -> list[dict]:
    """Artifacts on chunks with zero citations."""
    awc = artifacts_with_citations(conn)
    return [a for a in awc if not a["backed"]]


def citation_provenance_by_type(conn) -> list[dict]:
    """Citation backing rates per artifact_type."""
    awc = artifacts_with_citations(conn)
    if not awc:
        return []

    by_type: dict[str, dict] = {}
    for a in awc:
        t = a["artifact_type"]
        if t not in by_type:
            by_type[t] = {
                "total": 0, "backed": 0,
                "citations": 0, "verified": 0,
            }
        by_type[t]["total"] += 1
        if a["backed"]:
            by_type[t]["backed"] += 1
        by_type[t]["citations"] += a["citation_count"]
        by_type[t]["verified"] += a["verified_count"]

    results = []
    for atype in sorted(by_type):
        d = by_type[atype]
        rate = (
            round(d["backed"] / d["total"], 4)
            if d["total"] > 0 else 0.0
        )
        results.append({
            "artifact_type": atype,
            "total_artifacts": d["total"],
            "backed_artifacts": d["backed"],
            "backing_rate": rate,
            "total_citations": d["citations"],
            "verified_citations": d["verified"],
        })

    return results


def artifact_citation_summary(conn) -> dict:
    """Aggregate artifact-citation provenance statistics."""
    awc = artifacts_with_citations(conn)

    if not awc:
        return {
            "total_artifacts": 0,
            "backed_artifacts": 0,
            "unbacked_artifacts": 0,
            "backing_rate": 0.0,
            "total_citations": 0,
            "verified_citations": 0,
            "best_backed_type": None,
            "worst_backed_type": None,
        }

    total = len(awc)
    backed = sum(1 for a in awc if a["backed"])
    unbacked = total - backed
    total_cites = sum(a["citation_count"] for a in awc)
    verified_cites = sum(a["verified_count"] for a in awc)

    by_type = citation_provenance_by_type(conn)
    best = max(by_type, key=lambda t: t["backing_rate"])
    worst = min(by_type, key=lambda t: t["backing_rate"])

    return {
        "total_artifacts": total,
        "backed_artifacts": backed,
        "unbacked_artifacts": unbacked,
        "backing_rate": (
            round(backed / total, 4) if total > 0 else 0.0
        ),
        "total_citations": total_cites,
        "verified_citations": verified_cites,
        "best_backed_type": best["artifact_type"],
        "worst_backed_type": worst["artifact_type"],
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"
        later = "2026-06-15T00:00:00Z"

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

        # Artifacts:
        # a1: library "torch" on c1 (c1 has 2 verified citations)
        # a2: api "openai" on c2 (c2 has 1 unverified citation)
        # a3: pattern "singleton" on c3 (c3 has 0 citations)
        # a4: command "pip" on c1 (c1 has 2 verified citations)
        artifacts = [
            ("a1", "c1", "library", "torch", "2.0", None, 1, None),
            ("a2", "c2", "api", "openai", "1.0", None, 0, None),
            ("a3", "c3", "pattern", "singleton", None, None, 0, None),
            ("a4", "c1", "command", "pip", None, None, 1, None),
        ]
        for a in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, "
                "implemented, evidence_path) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", a,
            )

        # Citations:
        # c1: 2 citations (both verified)
        # c2: 1 citation (unverified)
        # c3: 0 citations
        # c4: 1 citation (verified) -- no artifact on c4
        cits = [
            ("ci1", "c1", "https://r1.com", None, "url",
             None, 1, later),
            ("ci2", "c1", "https://r2.com", None, "doi",
             None, 1, later),
            ("ci3", "c2", "https://r3.com", None, "url",
             None, 0, None),
            ("ci4", "c4", "https://r4.com", None, "doi",
             None, 1, later),
        ]
        for c in cits:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", c,
            )

        conn.commit()

        # 1: artifacts_with_citations returns 4 artifacts
        awc = artifacts_with_citations(conn)
        assert len(awc) == 4
        checks += 1

        # 2: a1 (torch on c1) has 2 citations, 2 verified
        a1 = next(a for a in awc if a["artifact_id"] == "a1")
        assert a1["citation_count"] == 2
        assert a1["verified_count"] == 2
        assert a1["backed"] is True
        checks += 1

        # 3: a2 (openai on c2) has 1 citation, 0 verified
        a2 = next(a for a in awc if a["artifact_id"] == "a2")
        assert a2["citation_count"] == 1
        assert a2["verified_count"] == 0
        assert a2["backed"] is True
        checks += 1

        # 4: a3 (singleton on c3) has 0 citations -- unbacked
        a3 = next(a for a in awc if a["artifact_id"] == "a3")
        assert a3["citation_count"] == 0
        assert a3["backed"] is False
        checks += 1

        # 5: a4 (pip on c1) shares c1 citations = 2 verified
        a4 = next(a for a in awc if a["artifact_id"] == "a4")
        assert a4["citation_count"] == 2
        assert a4["verified_count"] == 2
        checks += 1

        # 6: unbacked_artifacts returns only a3
        ub = unbacked_artifacts(conn)
        assert len(ub) == 1
        assert ub[0]["artifact_id"] == "a3"
        checks += 1

        # 7: citation_provenance_by_type returns 4 types
        bt = citation_provenance_by_type(conn)
        assert len(bt) == 4
        checks += 1

        # 8: library type: 1 artifact, 1 backed, rate 1.0
        lib = next(t for t in bt if t["artifact_type"] == "library")
        assert lib["total_artifacts"] == 1
        assert lib["backed_artifacts"] == 1
        assert abs(lib["backing_rate"] - 1.0) < 0.001
        checks += 1

        # 9: pattern type: 1 artifact, 0 backed, rate 0.0
        pat = next(t for t in bt if t["artifact_type"] == "pattern")
        assert pat["total_artifacts"] == 1
        assert pat["backed_artifacts"] == 0
        assert abs(pat["backing_rate"] - 0.0) < 0.001
        checks += 1

        # 10: summary totals
        summary = artifact_citation_summary(conn)
        assert summary["total_artifacts"] == 4
        assert summary["backed_artifacts"] == 3
        assert summary["unbacked_artifacts"] == 1
        checks += 1

        # 11: summary backing rate = 3/4 = 0.75
        assert abs(summary["backing_rate"] - 0.75) < 0.001
        checks += 1

        # 12: summary total citations = 2+1+0+2 = 5
        assert summary["total_citations"] == 5
        assert summary["verified_citations"] == 4
        checks += 1

        # 13: best backed type is not pattern (0.0)
        assert summary["worst_backed_type"] == "pattern"
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(awc)
        _ = json.dumps(ub)
        _ = json.dumps(bt)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = artifacts_with_citations(conn2)
        assert empty == []
        empty_summary = artifact_citation_summary(conn2)
        assert empty_summary["total_artifacts"] == 0
        checks += 1

    print(
        f"PASS artifact_citation_provenance selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact citation provenance analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ba = sub.add_parser("by-artifact",
                          help="Citation backing per artifact")
    p_ba.add_argument("--db", default=DEFAULT_DB)
    p_ba.add_argument("--json", action="store_true")

    p_ub = sub.add_parser("unbacked",
                           help="Artifacts with no citation backing")
    p_ub.add_argument("--db", default=DEFAULT_DB)
    p_ub.add_argument("--json", action="store_true")

    p_bt = sub.add_parser("by-type",
                           help="Citation backing rates per type")
    p_bt.add_argument("--db", default=DEFAULT_DB)
    p_bt.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Artifact citation provenance stats")
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

    if args.cmd == "by-artifact":
        results = artifacts_with_citations(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                backed = "Y" if r["backed"] else "N"
                print(f"  {r['name']:20s}  "
                      f"{r['artifact_type']:10s}  "
                      f"cites={r['citation_count']:2d}  "
                      f"verified={r['verified_count']:2d}  "
                      f"backed={backed}")

    elif args.cmd == "unbacked":
        results = unbacked_artifacts(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['name']:20s}  "
                      f"{r['artifact_type']:10s}")

    elif args.cmd == "by-type":
        results = citation_provenance_by_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['artifact_type']:10s}  "
                      f"total={r['total_artifacts']:3d}  "
                      f"backed={r['backed_artifacts']:3d}  "
                      f"rate={r['backing_rate']:.3f}  "
                      f"cites={r['total_citations']:3d}")

    elif args.cmd == "summary":
        result = artifact_citation_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total_artifacts']}  "
                  f"Backed: {result['backed_artifacts']}  "
                  f"Unbacked: {result['unbacked_artifacts']}")
            print(f"  Backing rate: "
                  f"{result['backing_rate']:.3f}  "
                  f"Citations: {result['total_citations']}  "
                  f"Verified: {result['verified_citations']}")
            if result["best_backed_type"]:
                print(f"  Best: {result['best_backed_type']}  "
                      f"Worst: {result['worst_backed_type']}")

    conn.close()


if __name__ == "__main__":
    main()
