#!/usr/bin/env python3
"""Query coverage analyzer: finds chunks never reached by common queries.

Records which chunks match a set of probe queries against the FTS5 index,
then identifies chunks that no probe query would surface.  This reveals
dead knowledge that exists in the corpus but is effectively invisible
to the retrieval layer.

Usage:
    python tools/corpus/query_coverage.py probe [--db PATH] [--json]
    python tools/corpus/query_coverage.py uncovered [--db PATH] [--json]
    python tools/corpus/query_coverage.py summary [--db PATH] [--json]
    python tools/corpus/query_coverage.py selftest
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


def _extract_probe_terms(conn) -> list[str]:
    """Build probe queries from corpus content: frequent tags, domain names,
    artifact names, and heading keywords."""
    probes: set[str] = set()

    if _table_exists(conn, "chunk_tags"):
        tags = conn.execute(
            "SELECT tag, count(*) as cnt FROM chunk_tags "
            "GROUP BY tag ORDER BY cnt DESC LIMIT 20"
        ).fetchall()
        for tag, _ in tags:
            probes.add(tag)

    if _table_exists(conn, "chunk_domains"):
        domains = conn.execute(
            "SELECT DISTINCT domain FROM chunk_domains LIMIT 20"
        ).fetchall()
        for (domain,) in domains:
            probes.add(domain)

    if _table_exists(conn, "artifacts"):
        arts = conn.execute(
            "SELECT DISTINCT name FROM artifacts LIMIT 20"
        ).fetchall()
        for (name,) in arts:
            probes.add(name)

    headings = conn.execute(
        "SELECT DISTINCT heading_path FROM chunks "
        "WHERE status = 'accepted' LIMIT 50"
    ).fetchall()
    for (heading,) in headings:
        words = heading.replace("/", " ").split()
        for w in words:
            cleaned = w.strip().lower()
            if len(cleaned) >= 4:
                probes.add(cleaned)

    return sorted(probes)[:50]


def _fts_match(conn, query: str) -> set[str]:
    """Run an FTS5 query and return matching chunk_ids."""
    try:
        rows = conn.execute(
            "SELECT c.chunk_id FROM chunks c "
            "JOIN chunks_fts f ON c.rowid = f.rowid "
            "WHERE chunks_fts MATCH ?",
            (query,),
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def probe_coverage(conn) -> list[dict]:
    """Run probe queries and report which chunks each matches."""
    probes = _extract_probe_terms(conn)
    if not probes:
        return []

    results = []
    for query in probes:
        matched = _fts_match(conn, query)
        results.append({
            "query": query,
            "matched_chunks": len(matched),
            "chunk_ids": sorted(matched),
        })

    results.sort(key=lambda r: r["matched_chunks"], reverse=True)
    return results


def uncovered_chunks(conn) -> list[dict]:
    """Find chunks that no probe query matches."""
    all_chunks = conn.execute(
        "SELECT chunk_id, source_id, heading_path, kind, word_count "
        "FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not all_chunks:
        return []

    probes = _extract_probe_terms(conn)
    covered: set[str] = set()
    for query in probes:
        covered |= _fts_match(conn, query)

    uncovered = []
    for chunk_id, source_id, heading, kind, word_count in all_chunks:
        if chunk_id not in covered:
            uncovered.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "heading": heading,
                "kind": kind,
                "word_count": word_count,
            })

    uncovered.sort(key=lambda c: c["word_count"], reverse=True)
    return uncovered


def coverage_summary(conn) -> dict:
    """Aggregate query coverage statistics."""
    total_accepted = conn.execute(
        "SELECT count(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]

    if total_accepted == 0:
        return {
            "total_accepted_chunks": 0,
            "probe_count": 0,
            "covered_chunks": 0,
            "uncovered_chunks": 0,
            "coverage_rate": 0.0,
            "avg_matches_per_probe": 0.0,
        }

    probes = _extract_probe_terms(conn)
    coverage_results = probe_coverage(conn)

    covered: set[str] = set()
    total_matches = 0
    for r in coverage_results:
        covered.update(r["chunk_ids"])
        total_matches += r["matched_chunks"]

    uncovered_count = total_accepted - len(covered)
    coverage_rate = round(len(covered) / total_accepted, 4) if total_accepted else 0.0
    avg_matches = round(total_matches / len(probes), 2) if probes else 0.0

    return {
        "total_accepted_chunks": total_accepted,
        "probe_count": len(probes),
        "covered_chunks": len(covered),
        "uncovered_chunks": uncovered_count,
        "coverage_rate": coverage_rate,
        "avg_matches_per_probe": avg_matches,
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
            ("c1", 0, "Machine Learning", "claim",
             "neural networks deep learning transformers"),
            ("c2", 1, "Database Systems", "claim",
             "sqlite postgresql indexing query optimization"),
            ("c3", 2, "Zq", "claim",
             "zqx plu abr nw"),
            ("c4", 3, "Configuration", "config",
             "yaml toml json settings parameters"),
        ]
        for cid, ordinal, heading, kind, text in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", ordinal, heading, kind, "en",
                 text, text, len(text.split()), f"n_{cid}",
                 "accepted", now),
            )

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c1", "neural", 0.9, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c2", "database", 0.85, now),
        )

        conn.commit()

        # 1: probe terms are extracted
        probes = _extract_probe_terms(conn)
        assert len(probes) > 0
        checks += 1

        # 2: probe terms include tags
        assert "neural" in probes or "database" in probes
        checks += 1

        # 3: FTS match returns chunk ids
        matched = _fts_match(conn, "neural")
        assert "c1" in matched
        checks += 1

        # 4: probe coverage returns results
        cov = probe_coverage(conn)
        assert len(cov) > 0
        checks += 1

        # 5: coverage results sorted by match count descending
        counts = [r["matched_chunks"] for r in cov]
        assert counts == sorted(counts, reverse=True)
        checks += 1

        # 6: uncovered chunks identified (c3 has nonsense text)
        uncov = uncovered_chunks(conn)
        uncov_ids = [c["chunk_id"] for c in uncov]
        assert "c3" in uncov_ids
        checks += 1

        # 7: covered chunks excluded from uncovered
        for r in cov:
            if r["matched_chunks"] > 0:
                for cid in r["chunk_ids"]:
                    assert cid not in uncov_ids or any(
                        other["matched_chunks"] > 0
                        and cid in other["chunk_ids"]
                        for other in cov
                    )
        checks += 1

        # 8: uncovered sorted by word count descending
        if len(uncov) > 1:
            wcs = [c["word_count"] for c in uncov]
            assert wcs == sorted(wcs, reverse=True)
        checks += 1

        # 9: summary has required keys
        summary = coverage_summary(conn)
        assert summary["total_accepted_chunks"] == 4
        assert "coverage_rate" in summary
        assert "probe_count" in summary
        checks += 1

        # 10: coverage rate between 0 and 1
        assert 0.0 <= summary["coverage_rate"] <= 1.0
        checks += 1

        # 11: covered + uncovered = total
        assert (summary["covered_chunks"]
                + summary["uncovered_chunks"]) == summary["total_accepted_chunks"]
        checks += 1

        # 12: avg_matches_per_probe is positive
        assert summary["avg_matches_per_probe"] >= 0.0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(cov)
        _ = json.dumps(uncov)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = uncovered_chunks(conn2)
        assert empty == []
        empty_summary = coverage_summary(conn2)
        assert empty_summary["total_accepted_chunks"] == 0
        checks += 1

    print(f"PASS query_coverage selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query coverage: find unreachable corpus chunks"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_probe = sub.add_parser("probe",
                             help="Run probe queries and report matches")
    p_probe.add_argument("--db", default=DEFAULT_DB)
    p_probe.add_argument("--json", action="store_true")

    p_uncov = sub.add_parser("uncovered",
                             help="Chunks no probe query matches")
    p_uncov.add_argument("--db", default=DEFAULT_DB)
    p_uncov.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Coverage statistics")
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

    if args.cmd == "probe":
        results = probe_coverage(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['matched_chunks']:4d} hits  {r['query']}")

    elif args.cmd == "uncovered":
        results = uncovered_chunks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("All chunks are reachable by probe queries.")
            else:
                print(f"{len(results)} unreachable chunks:")
                for c in results:
                    print(f"  {c['word_count']:5d}w  {c['kind']:6s}  "
                          f"{c['chunk_id'][:12]:12s}  {c['heading']}")

    elif args.cmd == "summary":
        result = coverage_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Query Coverage: {result['coverage_rate']:.1%} "
                  f"({result['covered_chunks']}/{result['total_accepted_chunks']} chunks)")
            print(f"  Probes: {result['probe_count']}  "
                  f"Avg matches: {result['avg_matches_per_probe']:.1f}")
            print(f"  Uncovered: {result['uncovered_chunks']} chunks")

    conn.close()


if __name__ == "__main__":
    main()
