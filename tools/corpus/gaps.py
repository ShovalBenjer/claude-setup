#!/usr/bin/env python3
"""Corpus gap analysis: identify underrepresented topics and missing coverage.

Compares corpus content against reference domains (spec topics, directory
subjects, known technology areas) and reports where the corpus is thin.
Useful for guiding new research ingestion and identifying blind spots.

Usage:
    python tools/corpus/gaps.py topics [--db PATH] [--min-chunks N] [--json]
    python tools/corpus/gaps.py terms [--db PATH] [--terms TERM,...] [--json]
    python tools/corpus/gaps.py uncovered-dirs [--db PATH] [--json]
    python tools/corpus/gaps.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import repo_root  # noqa: E402

ROOT = repo_root.resolve()

REFERENCE_DOMAINS = [
    "sqlite", "fts5", "embedding", "dedup", "deduplication",
    "citation", "provenance", "lineage", "contradiction",
    "artifact", "license", "ingestion", "pipeline",
    "retrieval", "search", "cache", "staleness",
    "quality", "validation", "export", "coverage",
    "clustering", "sampling", "promotion", "health",
    "git", "hook", "gate", "review", "testing",
    "skill", "persona", "agent", "swarm",
    "prompt", "context", "token", "model",
    "autonomy", "scheduler", "cron", "routine",
    "whatsapp", "telegram", "slack", "discord",
    "cloudflare", "worker", "d1", "r2", "kv",
    "rust", "python", "typescript", "javascript",
    "react", "next.js", "tailwind", "shadcn",
    "oauth", "jwt", "api", "rest", "graphql",
    "kubernetes", "docker", "ci", "cd", "github actions",
    "observability", "logging", "metrics", "tracing",
    "security", "encryption", "authentication", "authorization",
]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9.]+", text.lower())


def topic_coverage(conn, min_chunks: int = 3) -> list[dict]:
    chunks = conn.execute(
        "SELECT chunk_id, norm_text, kind, status FROM chunks"
    ).fetchall()

    domain_hits: dict[str, dict] = {}
    for domain in REFERENCE_DOMAINS:
        domain_lower = domain.lower()
        matching = [
            {"chunk_id": row[0], "kind": row[2], "status": row[3]}
            for row in chunks if domain_lower in row[1].lower()
        ]
        accepted = sum(1 for m in matching if m["status"] == "accepted")
        domain_hits[domain] = {
            "domain": domain,
            "total_chunks": len(matching),
            "accepted_chunks": accepted,
            "quarantined_chunks": sum(1 for m in matching if m["status"] == "quarantined"),
            "coverage": "strong" if accepted >= min_chunks * 2 else
                        "adequate" if accepted >= min_chunks else
                        "thin" if accepted > 0 else
                        "missing",
        }

    results = sorted(domain_hits.values(),
                     key=lambda x: x["total_chunks"])
    return results


def term_search(conn, terms: list[str]) -> list[dict]:
    results = []
    for term in terms:
        term_lower = term.lower()
        total = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE LOWER(norm_text) LIKE ?",
            (f"%{term_lower}%",),
        ).fetchone()[0]

        accepted = conn.execute(
            "SELECT COUNT(*) FROM chunks "
            "WHERE LOWER(norm_text) LIKE ? AND status = 'accepted'",
            (f"%{term_lower}%",),
        ).fetchone()[0]

        sources_count = conn.execute(
            "SELECT COUNT(DISTINCT c.source_id) FROM chunks c "
            "WHERE LOWER(c.norm_text) LIKE ?",
            (f"%{term_lower}%",),
        ).fetchone()[0]

        results.append({
            "term": term,
            "total_chunks": total,
            "accepted_chunks": accepted,
            "source_count": sources_count,
            "coverage": "strong" if accepted >= 6 else
                        "adequate" if accepted >= 3 else
                        "thin" if accepted > 0 else
                        "missing",
        })

    results.sort(key=lambda x: x["total_chunks"])
    return results


def uncovered_dirs(conn) -> list[dict]:
    source_uris = conn.execute(
        "SELECT canonical_uri FROM sources WHERE kind = 'local_md'"
    ).fetchall()

    covered_dirs: set[str] = set()
    for row in source_uris:
        uri = row[0]
        if uri.startswith("file://"):
            path = uri[7:]
            parts = Path(path).parts
            for i in range(1, len(parts)):
                covered_dirs.add("/".join(parts[:i]))

    source_trees = ["work-docs", "research-papers", "docs/analysis"]
    results = []
    for tree in source_trees:
        tree_path = ROOT / tree
        if not tree_path.is_dir():
            continue
        for dirpath in sorted(tree_path.rglob("*")):
            if not dirpath.is_dir():
                continue
            rel = dirpath.relative_to(ROOT)
            md_files = list(dirpath.glob("*.md"))
            if not md_files:
                continue

            has_source = False
            for md in md_files:
                uri = f"file://{md}"
                check = conn.execute(
                    "SELECT COUNT(*) FROM sources WHERE canonical_uri = ?",
                    (uri,),
                ).fetchone()[0]
                if check > 0:
                    has_source = True
                    break

            if not has_source:
                results.append({
                    "directory": str(rel),
                    "md_files": len(md_files),
                    "status": "not_indexed",
                })

    return results


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "SQLite and FTS5 Guide",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Python Testing Patterns",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "SQLite / FTS5", "claim", None,
             "sqlite fts5 provides full text search with porter stemming tokenizer. "
             "embedding vectors can be stored alongside the fts5 index for reranking.",
             "raw", 25, _sha256("c1"), 0, 1, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Citation Model", "claim", None,
             "citation provenance tracks where each claim came from and what it cites. "
             "lineage can be traced through the citation graph.",
             "raw", 22, _sha256("c2"), 0, 0, "quarantined", "unverified", now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src2", 0, "Testing / Gate", "prose", None,
             "gate validation runs testing checks including review panel and skill evaluation. "
             "python pytest is the test runner.",
             "raw", 20, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src2", 1, "Rust / Performance", "code", None,
             "rust provides memory safety without garbage collection. "
             "the dashboard uses rust for hot paths.",
             "raw", 18, _sha256("c4"), 0, 0, "accepted", None, now),
        )
        conn.commit()

        # Check 1: topic_coverage returns results for all domains
        topics = topic_coverage(conn)
        assert len(topics) == len(REFERENCE_DOMAINS), \
            f"expected {len(REFERENCE_DOMAINS)} domains, got {len(topics)}"
        checks += 1

        # Check 2: sqlite domain found in corpus
        sqlite_topic = next(t for t in topics if t["domain"] == "sqlite")
        assert sqlite_topic["total_chunks"] > 0, "sqlite should have hits"
        checks += 1

        # Check 3: missing domain has zero accepted chunks
        missing_topics = [t for t in topics if t["coverage"] == "missing"]
        for mt in missing_topics:
            assert mt["accepted_chunks"] == 0
        checks += 1

        # Check 4: results sorted by total_chunks ascending
        counts = [t["total_chunks"] for t in topics]
        assert counts == sorted(counts), "should be sorted by total_chunks asc"
        checks += 1

        # Check 5: coverage labels are correct
        for t in topics:
            if t["accepted_chunks"] >= 6:
                assert t["coverage"] == "strong"
            elif t["accepted_chunks"] >= 3:
                assert t["coverage"] == "adequate"
            elif t["accepted_chunks"] > 0:
                assert t["coverage"] == "thin"
            else:
                assert t["coverage"] in ("missing", "thin")
        checks += 1

        # Check 6: term_search finds known terms
        term_results = term_search(conn, ["sqlite", "rust", "nonexistent_xyz"])
        assert len(term_results) == 3
        checks += 1

        # Check 7: known term has hits
        sqlite_term = next(t for t in term_results if t["term"] == "sqlite")
        assert sqlite_term["total_chunks"] > 0
        checks += 1

        # Check 8: unknown term has zero hits
        unknown = next(t for t in term_results if t["term"] == "nonexistent_xyz")
        assert unknown["total_chunks"] == 0
        assert unknown["coverage"] == "missing"
        checks += 1

        # Check 9: term_search reports source_count
        assert sqlite_term["source_count"] >= 1
        checks += 1

        # Check 10: term_search sorted by total_chunks ascending
        term_counts = [t["total_chunks"] for t in term_results]
        assert term_counts == sorted(term_counts)
        checks += 1

        # Check 11: uncovered_dirs returns a list (may be empty in test env)
        dirs = uncovered_dirs(conn)
        assert isinstance(dirs, list)
        checks += 1

        # Check 12: JSON serialization works for topics
        j = json.dumps(topics, indent=2)
        parsed = json.loads(j)
        assert len(parsed) == len(REFERENCE_DOMAINS)
        checks += 1

        # Check 13: JSON serialization works for term_search
        j2 = json.dumps(term_results, indent=2)
        parsed2 = json.loads(j2)
        assert len(parsed2) == 3
        checks += 1

        # Check 14: custom min_chunks changes coverage labels
        strict = topic_coverage(conn, min_chunks=100)
        strong_count = sum(1 for t in strict if t["coverage"] == "strong")
        assert strong_count == 0, "no domain should be strong at min_chunks=100"
        checks += 1

        # Check 15: empty corpus returns all missing
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        empty_topics = topic_coverage(empty_conn)
        assert all(t["coverage"] == "missing" for t in empty_topics)
        empty_conn.close()
        checks += 1

        # Check 16: quarantined chunks counted separately
        sqlite_topic2 = next(t for t in topics if t["domain"] == "sqlite")
        assert "quarantined_chunks" in sqlite_topic2
        checks += 1

        conn.close()

    print(f"PASS gaps selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus gap analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_topics = sub.add_parser("topics", help="Coverage across reference domains")
    p_topics.add_argument("--db", default=str(DEFAULT_DB))
    p_topics.add_argument("--min-chunks", type=int, default=3)
    p_topics.add_argument("--json", action="store_true")

    p_terms = sub.add_parser("terms", help="Search for specific terms")
    p_terms.add_argument("--db", default=str(DEFAULT_DB))
    p_terms.add_argument("--terms", required=True,
                         help="Comma-separated list of terms to check")
    p_terms.add_argument("--json", action="store_true")

    p_dirs = sub.add_parser("uncovered-dirs",
                            help="Directories with markdown not in corpus")
    p_dirs.add_argument("--db", default=str(DEFAULT_DB))
    p_dirs.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "topics":
        results = topic_coverage(conn, min_chunks=args.min_chunks)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                icon = {"strong": "+", "adequate": "~",
                        "thin": "-", "missing": "!"}[r["coverage"]]
                print(f"  [{icon}] {r['domain']:20s}  "
                      f"total={r['total_chunks']:3d}  "
                      f"accepted={r['accepted_chunks']:3d}  "
                      f"quarantined={r['quarantined_chunks']:3d}  "
                      f"{r['coverage']}")

    elif args.cmd == "terms":
        terms = [t.strip() for t in args.terms.split(",") if t.strip()]
        results = term_search(conn, terms)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['term']:30s}  chunks={r['total_chunks']:3d}  "
                      f"accepted={r['accepted_chunks']:3d}  "
                      f"sources={r['source_count']:2d}  {r['coverage']}")

    elif args.cmd == "uncovered-dirs":
        results = uncovered_dirs(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  All source directories are indexed.")
            else:
                for r in results:
                    print(f"  {r['directory']:50s}  "
                          f"md_files={r['md_files']:3d}  {r['status']}")

    conn.close()


if __name__ == "__main__":
    main()
