#!/usr/bin/env python3
"""Health scorecard: unified corpus quality summary from all signal tables.

Pulls metrics from chunks, citations, claim_edges, chunk_tags,
chunk_versions, chunk_domains, artifacts, and analytical tables into
a single health report with per-dimension scores.

Usage:
    python tools/corpus/health_scorecard.py report [--db PATH] [--json]
    python tools/corpus/health_scorecard.py dimensions [--db PATH] [--json]
    python tools/corpus/health_scorecard.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _count(conn, table: str, where: str = "") -> int:
    if not _table_exists(conn, table):
        return 0
    q = f"SELECT count(*) FROM {table}"
    if where:
        q += f" WHERE {where}"
    return conn.execute(q).fetchone()[0]


def _chunk_status_counts(conn) -> dict:
    rows = conn.execute(
        "SELECT status, count(*) FROM chunks GROUP BY status"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _citation_verification_rate(conn) -> float:
    if not _table_exists(conn, "citations"):
        return 0.0
    total = _count(conn, "citations")
    if total == 0:
        return 0.0
    verified = _count(conn, "citations", "verified = 1")
    return round(verified / total, 4)


def _edge_resolution_rate(conn) -> float:
    total = _count(conn, "claim_edges")
    if total == 0:
        return 0.0
    resolved = _count(conn, "claim_edges", "resolution IS NOT NULL")
    return round(resolved / total, 4)


def _tag_confidence(conn) -> float:
    if not _table_exists(conn, "chunk_tags"):
        return 0.0
    row = conn.execute(
        "SELECT round(avg(score), 4) FROM chunk_tags"
    ).fetchone()
    return row[0] if row[0] is not None else 0.0


def _artifact_adoption_rate(conn) -> float:
    total = _count(conn, "artifacts")
    if total == 0:
        return 0.0
    implemented = _count(conn, "artifacts", "implemented = 1")
    return round(implemented / total, 4)


def _acceptance_rate(conn) -> float:
    total = _count(conn, "chunks")
    if total == 0:
        return 0.0
    accepted = _count(conn, "chunks", "status = 'accepted'")
    return round(accepted / total, 4)


def dimensions(conn) -> list[dict]:
    """Individual health dimensions with scores and context."""
    dims = []

    total_chunks = _count(conn, "chunks")
    statuses = _chunk_status_counts(conn) if total_chunks > 0 else {}
    accepted = statuses.get("accepted", 0)
    acc_rate = round(accepted / total_chunks, 4) if total_chunks else 0.0
    dims.append({
        "dimension": "acceptance",
        "score": acc_rate,
        "detail": f"{accepted}/{total_chunks} chunks accepted",
    })

    cit_rate = _citation_verification_rate(conn)
    cit_total = _count(conn, "citations") if _table_exists(conn, "citations") else 0
    dims.append({
        "dimension": "citation_verification",
        "score": cit_rate,
        "detail": f"{cit_total} citations, {cit_rate:.0%} verified",
    })

    edge_rate = _edge_resolution_rate(conn)
    edge_total = _count(conn, "claim_edges")
    dims.append({
        "dimension": "edge_resolution",
        "score": edge_rate,
        "detail": f"{edge_total} edges, {edge_rate:.0%} resolved",
    })

    tag_conf = _tag_confidence(conn)
    tag_total = _count(conn, "chunk_tags") if _table_exists(conn, "chunk_tags") else 0
    dims.append({
        "dimension": "tag_confidence",
        "score": tag_conf,
        "detail": f"{tag_total} tag assignments, avg score {tag_conf:.2f}",
    })

    art_rate = _artifact_adoption_rate(conn)
    art_total = _count(conn, "artifacts")
    dims.append({
        "dimension": "artifact_adoption",
        "score": art_rate,
        "detail": f"{art_total} artifacts, {art_rate:.0%} implemented",
    })

    domain_chunks = 0
    if _table_exists(conn, "chunk_domains"):
        domain_chunks = conn.execute(
            "SELECT count(DISTINCT chunk_id) FROM chunk_domains"
        ).fetchone()[0]
    domain_coverage = round(domain_chunks / total_chunks, 4) if total_chunks else 0.0
    dims.append({
        "dimension": "domain_coverage",
        "score": domain_coverage,
        "detail": f"{domain_chunks}/{total_chunks} chunks domain-classified",
    })

    versioned = 0
    if _table_exists(conn, "chunk_versions"):
        versioned = conn.execute(
            "SELECT count(DISTINCT chunk_id) FROM chunk_versions"
        ).fetchone()[0]
    version_coverage = round(versioned / total_chunks, 4) if total_chunks else 0.0
    dims.append({
        "dimension": "version_tracking",
        "score": version_coverage,
        "detail": f"{versioned}/{total_chunks} chunks version-tracked",
    })

    return dims


def full_report(conn) -> dict:
    """Unified health report with overall score and per-dimension breakdown."""
    dims = dimensions(conn)

    scores = [d["score"] for d in dims]
    overall = round(sum(scores) / len(scores), 4) if scores else 0.0

    total_sources = _count(conn, "sources")
    total_chunks = _count(conn, "chunks")

    return {
        "overall_score": overall,
        "total_sources": total_sources,
        "total_chunks": total_chunks,
        "dimensions": dims,
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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        chunk_data = [
            ("c1", "accepted"),
            ("c2", "accepted"),
            ("c3", "quarantined"),
            ("c4", "accepted"),
        ]
        for i, (cid, status) in enumerate(chunk_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", i, f"H{i}", "claim", "en",
                 "text", "text", 10, f"n_{cid}", status, now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
            ("ci1", "c1", "https://ref.com", "primary", "p.5", 1),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
            ("ci2", "c2", "https://ref2.com", "primary", "p.10", 0),
        )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc, resolution) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "supports", "semantic", 0.8, now, "accepted"),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e2", "c2", "c4", "contradicts", "semantic", 0.7, now),
        )

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c1", "ml", 0.9, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c2", "ml", 0.6, now),
        )

        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, version, snippet, implemented, evidence_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("a1", "c1", "library", "numpy", "1.26", None, 1, None),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, version, snippet, implemented, evidence_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("a2", "c2", "command", "pip", None, None, 0, None),
        )

        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v1", "c1", 1, "sha1", 10, now),
        )

        conn.commit()

        # 1: full report structure
        rpt = full_report(conn)
        assert "overall_score" in rpt
        assert "dimensions" in rpt
        assert rpt["total_sources"] == 1
        assert rpt["total_chunks"] == 4
        checks += 1

        # 2: acceptance rate (3/4 accepted)
        acc_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "acceptance"][0]
        assert acc_dim["score"] == 0.75
        checks += 1

        # 3: citation verification rate (1/2 verified)
        cit_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "citation_verification"][0]
        assert cit_dim["score"] == 0.5
        checks += 1

        # 4: edge resolution rate (1/2 resolved)
        edge_dim = [d for d in rpt["dimensions"]
                    if d["dimension"] == "edge_resolution"][0]
        assert edge_dim["score"] == 0.5
        checks += 1

        # 5: tag confidence (avg of 0.9 and 0.6)
        tag_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "tag_confidence"][0]
        assert tag_dim["score"] == 0.75
        checks += 1

        # 6: artifact adoption (1/2 implemented)
        art_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "artifact_adoption"][0]
        assert art_dim["score"] == 0.5
        checks += 1

        # 7: domain coverage (0/4, no chunk_domains table entries)
        dom_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "domain_coverage"][0]
        assert dom_dim["score"] == 0.0
        checks += 1

        # 8: version tracking (1/4 tracked)
        ver_dim = [d for d in rpt["dimensions"]
                   if d["dimension"] == "version_tracking"][0]
        assert ver_dim["score"] == 0.25
        checks += 1

        # 9: overall score is average of dimension scores
        dim_scores = [d["score"] for d in rpt["dimensions"]]
        expected_overall = round(sum(dim_scores) / len(dim_scores), 4)
        assert rpt["overall_score"] == expected_overall
        checks += 1

        # 10: dimensions subcommand matches report dimensions
        dims = dimensions(conn)
        assert len(dims) == 7
        checks += 1

        # 11: all dimensions have required keys
        for d in dims:
            assert "dimension" in d
            assert "score" in d
            assert "detail" in d
        checks += 1

        # 12: detail strings are non-empty
        for d in dims:
            assert len(d["detail"]) > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(rpt)
        _ = json.dumps(dims)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        rpt2 = full_report(conn2)
        assert rpt2["overall_score"] == 0.0
        assert rpt2["total_chunks"] == 0
        checks += 1

    print(f"PASS health_scorecard selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Health scorecard: unified corpus quality summary"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_rpt = sub.add_parser("report",
                           help="Full health report with overall score")
    p_rpt.add_argument("--db", default=DEFAULT_DB)
    p_rpt.add_argument("--json", action="store_true")

    p_dim = sub.add_parser("dimensions",
                           help="Individual dimension scores")
    p_dim.add_argument("--db", default=DEFAULT_DB)
    p_dim.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "report":
        result = full_report(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Corpus Health: {result['overall_score']:.1%} "
                  f"({result['total_sources']} sources, "
                  f"{result['total_chunks']} chunks)")
            for d in result["dimensions"]:
                bar = "#" * int(d["score"] * 20)
                pad = "." * (20 - len(bar))
                print(f"  {d['dimension']:25s} [{bar}{pad}] "
                      f"{d['score']:.0%}  {d['detail']}")

    elif args.cmd == "dimensions":
        result = dimensions(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for d in result:
                print(f"  {d['dimension']}: {d['score']:.2f} - {d['detail']}")

    conn.close()


if __name__ == "__main__":
    main()
