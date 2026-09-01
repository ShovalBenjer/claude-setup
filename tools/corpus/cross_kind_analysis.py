#!/usr/bin/env python3
"""Cross-kind analysis: chunk, artifact, and citation patterns by source kind.

Cross-tabulates chunk kind, artifact type, and citation density against
source kind.  No existing tool crossed these dimensions: chunk_kind_profile
analyses per source and per domain but never per source kind; artifact_adoption
groups by artifact_type alone; citation_analysis groups by target but never
by source kind.

Usage:
    python tools/corpus/cross_kind_analysis.py chunk-kind [--db PATH] [--json]
    python tools/corpus/cross_kind_analysis.py artifact-type [--db PATH] [--json]
    python tools/corpus/cross_kind_analysis.py citation-density [--db PATH] [--json]
    python tools/corpus/cross_kind_analysis.py summary [--db PATH] [--json]
    python tools/corpus/cross_kind_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def chunk_kind_by_source_kind(conn) -> list[dict]:
    """Chunk kind distribution per source kind."""
    rows = conn.execute(
        "SELECT s.kind AS source_kind, c.kind AS chunk_kind, "
        "count(*) AS cnt "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY s.kind, c.kind "
        "ORDER BY s.kind, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_sk: dict[str, dict] = {}
    for sk, ck, cnt in rows:
        if sk not in by_sk:
            by_sk[sk] = {"total": 0, "breakdown": {}}
        by_sk[sk]["total"] += cnt
        by_sk[sk]["breakdown"][ck] = cnt

    results = []
    for sk, info in sorted(by_sk.items()):
        t = info["total"]
        dominant = max(info["breakdown"], key=info["breakdown"].get)
        results.append({
            "source_kind": sk,
            "chunk_count": t,
            "dominant_chunk_kind": dominant,
            "breakdown": info["breakdown"],
        })

    return results


def artifact_type_by_source_kind(conn) -> list[dict]:
    """Artifact type distribution per source kind."""
    rows = conn.execute(
        "SELECT s.kind AS source_kind, a.artifact_type, "
        "count(*) AS cnt "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "JOIN sources s ON c.source_id = s.source_id "
        "GROUP BY s.kind, a.artifact_type "
        "ORDER BY s.kind, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_sk: dict[str, dict] = {}
    for sk, atype, cnt in rows:
        if sk not in by_sk:
            by_sk[sk] = {"total": 0, "breakdown": {}}
        by_sk[sk]["total"] += cnt
        by_sk[sk]["breakdown"][atype] = cnt

    results = []
    for sk, info in sorted(by_sk.items()):
        t = info["total"]
        dominant = max(info["breakdown"], key=info["breakdown"].get)
        results.append({
            "source_kind": sk,
            "artifact_count": t,
            "dominant_artifact_type": dominant,
            "breakdown": info["breakdown"],
        })

    return results


def citation_density_by_source_kind(conn) -> list[dict]:
    """Citation density per source kind."""
    rows = conn.execute(
        "SELECT s.kind AS source_kind, c.citation_count "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_sk: dict[str, list[int]] = {}
    for sk, cite_count in rows:
        if sk not in by_sk:
            by_sk[sk] = []
        by_sk[sk].append(cite_count)

    results = []
    for sk in sorted(by_sk):
        counts = by_sk[sk]
        n = len(counts)
        total_cites = sum(counts)
        cited = sum(1 for c in counts if c > 0)
        results.append({
            "source_kind": sk,
            "chunk_count": n,
            "total_citations": total_cites,
            "mean_citations": round(total_cites / n, 2) if n > 0 else 0.0,
            "cited_rate": round(cited / n, 4) if n > 0 else 0.0,
        })

    return results


def cross_kind_summary(conn) -> dict:
    """Aggregate cross-kind statistics."""
    ck = chunk_kind_by_source_kind(conn)
    at = artifact_type_by_source_kind(conn)
    cd = citation_density_by_source_kind(conn)

    if not ck:
        return {
            "source_kinds": 0,
            "chunk_kind_dominance": {},
            "artifact_type_dominance": {},
            "citation_by_source_kind": {},
        }

    dominance = {r["source_kind"]: r["dominant_chunk_kind"] for r in ck}
    art_dom = {r["source_kind"]: r["dominant_artifact_type"] for r in at}
    cite_map = {
        r["source_kind"]: {
            "mean": r["mean_citations"],
            "cited_rate": r["cited_rate"],
        }
        for r in cd
    }

    return {
        "source_kinds": len(ck),
        "chunk_kind_dominance": dominance,
        "artifact_type_dominance": art_dom,
        "citation_by_source_kind": cite_map,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        sources = [
            ("s1", "paper"),
            ("s2", "paper"),
            ("s3", "repo"),
            ("s4", "local_md"),
        ]
        for sid, kind in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        # paper sources: mostly claim and prose chunks, high citations
        # repo source: mostly code chunks, low citations
        # local_md: prose chunks, medium citations
        chunks = [
            ("c1", "s1", 0, "claim", 5),
            ("c2", "s1", 1, "prose", 3),
            ("c3", "s2", 0, "claim", 4),
            ("c4", "s2", 1, "claim", 2),
            ("c5", "s3", 0, "code", 0),
            ("c6", "s3", 1, "code", 1),
            ("c7", "s3", 2, "config", 0),
            ("c8", "s4", 0, "prose", 2),
            ("c9", "s4", 1, "prose", 1),
        ]
        for cid, sid, ordinal, kind, cites in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, cites, "accepted", now),
            )

        # Artifacts: libraries in repo, APIs in paper
        artifacts = [
            ("a1", "c1", "api", "REST"),
            ("a2", "c3", "api", "GraphQL"),
            ("a3", "c5", "library", "React"),
            ("a4", "c5", "library", "Flask"),
            ("a5", "c6", "command", "npm"),
            ("a6", "c8", "pattern", "MVC"),
        ]
        for aid, cid, atype, name in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, implemented, "
                "evidence_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, None, None, 0, None),
            )

        conn.commit()

        # 1: chunk-kind returns entries for all source kinds
        ck = chunk_kind_by_source_kind(conn)
        assert len(ck) == 3
        checks += 1

        # 2: paper sources have claim as dominant chunk kind
        paper = next(c for c in ck if c["source_kind"] == "paper")
        assert paper["dominant_chunk_kind"] == "claim"
        assert paper["chunk_count"] == 4
        checks += 1

        # 3: repo source has code as dominant chunk kind
        repo = next(c for c in ck if c["source_kind"] == "repo")
        assert repo["dominant_chunk_kind"] == "code"
        checks += 1

        # 4: local_md has prose as dominant
        lmd = next(c for c in ck if c["source_kind"] == "local_md")
        assert lmd["dominant_chunk_kind"] == "prose"
        checks += 1

        # 5: artifact-type returns entries
        at = artifact_type_by_source_kind(conn)
        assert len(at) > 0
        checks += 1

        # 6: paper sources have api as dominant artifact type
        paper_art = next(
            (a for a in at if a["source_kind"] == "paper"), None
        )
        assert paper_art is not None
        assert paper_art["dominant_artifact_type"] == "api"
        checks += 1

        # 7: repo has library as dominant
        repo_art = next(
            (a for a in at if a["source_kind"] == "repo"), None
        )
        assert repo_art is not None
        assert repo_art["dominant_artifact_type"] == "library"
        checks += 1

        # 8: citation density returns entries
        cd = citation_density_by_source_kind(conn)
        assert len(cd) == 3
        checks += 1

        # 9: paper has highest mean citations
        paper_cite = next(c for c in cd if c["source_kind"] == "paper")
        repo_cite = next(c for c in cd if c["source_kind"] == "repo")
        assert paper_cite["mean_citations"] > repo_cite["mean_citations"]
        checks += 1

        # 10: repo has lowest cited rate
        assert repo_cite["cited_rate"] < paper_cite["cited_rate"]
        checks += 1

        # 11: summary has correct source kind count
        summary = cross_kind_summary(conn)
        assert summary["source_kinds"] == 3
        checks += 1

        # 12: dominance maps populated
        assert summary["chunk_kind_dominance"]["paper"] == "claim"
        assert summary["artifact_type_dominance"]["repo"] == "library"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(ck)
        _ = json.dumps(at)
        _ = json.dumps(cd)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = chunk_kind_by_source_kind(conn2)
        assert empty == []
        empty_summary = cross_kind_summary(conn2)
        assert empty_summary["source_kinds"] == 0
        checks += 1

    print(f"PASS cross_kind_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-kind analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ck = sub.add_parser("chunk-kind",
                          help="Chunk kind by source kind")
    p_ck.add_argument("--db", default=DEFAULT_DB)
    p_ck.add_argument("--json", action="store_true")

    p_at = sub.add_parser("artifact-type",
                          help="Artifact type by source kind")
    p_at.add_argument("--db", default=DEFAULT_DB)
    p_at.add_argument("--json", action="store_true")

    p_cd = sub.add_parser("citation-density",
                          help="Citation density by source kind")
    p_cd.add_argument("--db", default=DEFAULT_DB)
    p_cd.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Cross-kind statistics")
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

    if args.cmd == "chunk-kind":
        results = chunk_kind_by_source_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_kind']:12s}  n={r['chunk_count']:3d}  "
                      f"dominant={r['dominant_chunk_kind']}  "
                      f"{r['breakdown']}")

    elif args.cmd == "artifact-type":
        results = artifact_type_by_source_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_kind']:12s}  "
                      f"n={r['artifact_count']:3d}  "
                      f"dominant={r['dominant_artifact_type']}  "
                      f"{r['breakdown']}")

    elif args.cmd == "citation-density":
        results = citation_density_by_source_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_kind']:12s}  "
                      f"n={r['chunk_count']:3d}  "
                      f"cites={r['total_citations']:4d}  "
                      f"mean={r['mean_citations']:.1f}  "
                      f"cited={r['cited_rate']:.0%}")

    elif args.cmd == "summary":
        result = cross_kind_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Source kinds: {result['source_kinds']}")
            print(f"  Chunk dominance: {result['chunk_kind_dominance']}")
            print(f"  Artifact dominance: "
                  f"{result['artifact_type_dominance']}")
            for sk, info in result["citation_by_source_kind"].items():
                print(f"  {sk}: mean={info['mean']:.1f}  "
                      f"cited={info['cited_rate']:.0%}")

    conn.close()


if __name__ == "__main__":
    main()
