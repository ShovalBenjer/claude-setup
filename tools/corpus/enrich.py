#!/usr/bin/env python3
"""Corpus enrichment: extract named entities and link to artifacts.

Scans chunk text for mentions of known libraries, frameworks, tools,
and APIs, then creates or updates entries in the artifacts table.
Supports evidence linking where an artifact is mentioned alongside
code patterns indicating actual implementation.

Usage:
    python tools/corpus/enrich.py scan [--db PATH] [--json]
    python tools/corpus/enrich.py apply [--db PATH] [--dry-run]
    python tools/corpus/enrich.py lookup --name NAME [--db PATH] [--json]
    python tools/corpus/enrich.py stats [--db PATH] [--json]
    python tools/corpus/enrich.py selftest
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

KNOWN_ENTITIES: dict[str, dict] = {
    "sqlite": {"type": "library", "patterns": [r"\bsqlite\b", r"\bsqlite3\b"]},
    "fts5": {"type": "library", "patterns": [r"\bfts5\b"]},
    "numpy": {"type": "library", "patterns": [r"\bnumpy\b", r"\bnp\.\w+"]},
    "pandas": {"type": "library", "patterns": [r"\bpandas\b", r"\bpd\.\w+"]},
    "polars": {"type": "library", "patterns": [r"\bpolars\b", r"\bpl\.\w+"]},
    "scikit-learn": {"type": "library", "patterns": [r"\bsklearn\b", r"\bscikit-learn\b"]},
    "pytorch": {"type": "library", "patterns": [r"\bpytorch\b", r"\btorch\.\w+"]},
    "tensorflow": {"type": "library", "patterns": [r"\btensorflow\b", r"\btf\.\w+"]},
    "react": {"type": "library", "patterns": [r"\breact\b", r"\buseState\b", r"\buseEffect\b"]},
    "next.js": {"type": "library", "patterns": [r"\bnext\.js\b", r"\bnextjs\b"]},
    "tailwind": {"type": "library", "patterns": [r"\btailwind\b", r"\btailwindcss\b"]},
    "fastapi": {"type": "api", "patterns": [r"\bfastapi\b"]},
    "flask": {"type": "api", "patterns": [r"\bflask\b"]},
    "django": {"type": "api", "patterns": [r"\bdjango\b"]},
    "express": {"type": "api", "patterns": [r"\bexpress\b", r"\bexpress\.js\b"]},
    "docker": {"type": "command", "patterns": [r"\bdocker\b", r"\bdockerfile\b"]},
    "kubernetes": {"type": "command", "patterns": [r"\bkubernetes\b", r"\bk8s\b", r"\bkubectl\b"]},
    "git": {"type": "command", "patterns": [r"\bgit\s+(commit|push|pull|merge|rebase|stash)\b"]},
    "pytest": {"type": "command", "patterns": [r"\bpytest\b"]},
    "ruff": {"type": "command", "patterns": [r"\bruff\b"]},
    "pip": {"type": "command", "patterns": [r"\bpip\s+install\b"]},
    "cargo": {"type": "command", "patterns": [r"\bcargo\b"]},
    "npm": {"type": "command", "patterns": [r"\bnpm\b"]},
    "cloudflare workers": {"type": "api", "patterns": [r"\bcloudflare\s+workers?\b", r"\bwrangler\b"]},
    "oauth": {"type": "pattern", "patterns": [r"\boauth\b", r"\boauth2\b"]},
    "jwt": {"type": "pattern", "patterns": [r"\bjwt\b", r"\bjson\s+web\s+token\b"]},
    "rest api": {"type": "pattern", "patterns": [r"\brest\s+api\b", r"\brestful\b"]},
    "graphql": {"type": "api", "patterns": [r"\bgraphql\b"]},
    "websocket": {"type": "pattern", "patterns": [r"\bwebsocket\b", r"\bwss?://"]},
    "redis": {"type": "library", "patterns": [r"\bredis\b"]},
    "postgresql": {"type": "library", "patterns": [r"\bpostgresql\b", r"\bpostgres\b", r"\bpsycopg\b"]},
}

IMPLEMENTATION_SIGNALS = [
    re.compile(r"^(import |from \S+ import )", re.MULTILINE),
    re.compile(r"^(pip install |npm install |cargo add )", re.MULTILINE),
    re.compile(r"^\$\s+\w+", re.MULTILINE),
    re.compile(r"```(python|javascript|typescript|rust|bash|shell)", re.MULTILINE),
]


def _find_entities(text: str) -> list[dict]:
    text_lower = text.lower()
    found = []
    for name, info in KNOWN_ENTITIES.items():
        for pat_str in info["patterns"]:
            pat = re.compile(pat_str, re.IGNORECASE)
            matches = list(pat.finditer(text_lower))
            if matches:
                impl_signals = sum(
                    1 for p in IMPLEMENTATION_SIGNALS if p.search(text)
                )
                found.append({
                    "name": name,
                    "type": info["type"],
                    "mentions": len(matches),
                    "implemented": impl_signals > 0,
                    "snippet": matches[0].group()[:60],
                })
                break
    return found


def scan_enrichments(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.norm_text, c.kind, "
        "       c.status, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status != 'superseded'"
    ).fetchall()

    results = []
    for row in rows:
        entities = _find_entities(row[2])
        if entities:
            results.append({
                "chunk_id": row[0],
                "source_id": row[1],
                "kind": row[3],
                "status": row[4],
                "source_title": row[5],
                "entities": entities,
            })

    results.sort(key=lambda r: sum(e["mentions"] for e in r["entities"]),
                 reverse=True)
    return results


def apply_enrichments(conn, dry_run: bool = True) -> list[dict]:
    scan = scan_enrichments(conn)
    actions = []

    for item in scan:
        for entity in item["entities"]:
            artifact_id = "a" + _sha256(
                item["chunk_id"] + entity["name"]
            )[:15]

            existing = conn.execute(
                "SELECT artifact_id FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()

            if existing:
                continue

            action = {
                "artifact_id": artifact_id,
                "chunk_id": item["chunk_id"],
                "name": entity["name"],
                "type": entity["type"],
                "implemented": entity["implemented"],
                "applied": not dry_run,
            }

            if not dry_run:
                conn.execute(
                    "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
                    (artifact_id, item["chunk_id"], entity["type"],
                     entity["name"], None, entity["snippet"],
                     1 if entity["implemented"] else 0, None),
                )

            actions.append(action)

    if not dry_run:
        conn.commit()

    return actions


def lookup_entity(conn, name: str) -> list[dict]:
    name_lower = name.lower()
    rows = conn.execute(
        "SELECT a.artifact_id, a.chunk_id, a.artifact_type, a.name, "
        "       a.version, a.snippet, a.implemented, a.evidence_path, "
        "       c.kind, c.status "
        "FROM artifacts a "
        "JOIN chunks c ON a.chunk_id = c.chunk_id "
        "WHERE LOWER(a.name) = ?",
        (name_lower,),
    ).fetchall()

    return [
        {
            "artifact_id": r[0],
            "chunk_id": r[1],
            "artifact_type": r[2],
            "name": r[3],
            "version": r[4],
            "snippet": r[5],
            "implemented": bool(r[6]),
            "evidence_path": r[7],
            "chunk_kind": r[8],
            "chunk_status": r[9],
        }
        for r in rows
    ]


def enrich_stats(conn) -> dict:
    scan = scan_enrichments(conn)

    entity_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    impl_count = 0
    total_mentions = 0

    for item in scan:
        for e in item["entities"]:
            entity_counts[e["name"]] += 1
            type_counts[e["type"]] += 1
            total_mentions += e["mentions"]
            if e["implemented"]:
                impl_count += 1

    existing_artifacts = conn.execute(
        "SELECT COUNT(*) FROM artifacts"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    return {
        "total_active_chunks": total_chunks,
        "chunks_with_entities": len(scan),
        "entity_coverage": round(len(scan) / total_chunks, 3) if total_chunks else 0,
        "unique_entities_found": len(entity_counts),
        "total_mentions": total_mentions,
        "implemented_count": impl_count,
        "existing_artifacts": existing_artifacts,
        "top_entities": dict(entity_counts.most_common(15)),
        "type_distribution": dict(type_counts.most_common()),
    }


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
            ("src1", "file:///a.md", "local_md", "Tech Stack Guide",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Database", "code", None,
             "import sqlite3\nfrom sqlite3 import connect\n\n"
             "db = sqlite3.connect('corpus.db')\n"
             "cursor = db.execute('SELECT * FROM chunks')\n",
             "raw", 15, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "ML Stack", "prose", None,
             "The pipeline uses numpy for array operations and "
             "scikit-learn for classification. pytorch handles "
             "the neural network training loop.",
             "raw", 20, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Frontend", "prose", None,
             "The dashboard is built with react and next.js using "
             "tailwind for styling. Components use useState and "
             "useEffect hooks for state management.",
             "raw", 22, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src1", 3, "Plain", "prose", None,
             "This text mentions no specific libraries or frameworks. "
             "It is purely descriptive prose about general concepts.",
             "raw", 16, _sha256("c4"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 4, "Old", "prose", None,
             "sqlite and numpy are mentioned but this is superseded.",
             "raw", 10, _sha256("c5"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: _find_entities detects sqlite
        entities = _find_entities("sqlite3 database with fts5 search")
        names = [e["name"] for e in entities]
        assert "sqlite" in names, f"should find sqlite, got {names}"
        checks += 1

        # Check 2: _find_entities detects numpy
        entities = _find_entities("import numpy as np\nnp.array([1,2,3])")
        names = [e["name"] for e in entities]
        assert "numpy" in names
        checks += 1

        # Check 3: implementation signal detected
        entities = _find_entities("import numpy as np\nnp.array([1,2,3])")
        np_entity = next(e for e in entities if e["name"] == "numpy")
        assert np_entity["implemented"] is True
        checks += 1

        # Check 4: no implementation signal for plain mention
        entities = _find_entities("numpy is a popular library for arrays")
        np_entity = next(e for e in entities if e["name"] == "numpy")
        assert np_entity["implemented"] is False
        checks += 1

        # Check 5: scan finds chunks with entities
        scan = scan_enrichments(conn)
        assert len(scan) >= 3, f"expected at least 3 chunks with entities, got {len(scan)}"
        checks += 1

        # Check 6: plain text chunk not in scan results
        plain_ids = [s["chunk_id"] for s in scan]
        assert "c4" not in plain_ids
        checks += 1

        # Check 7: superseded chunk excluded
        assert "c5" not in plain_ids
        checks += 1

        # Check 8: code chunk has sqlite entity
        c1_scan = next(s for s in scan if s["chunk_id"] == "c1")
        c1_names = [e["name"] for e in c1_scan["entities"]]
        assert "sqlite" in c1_names
        checks += 1

        # Check 9: dry run does not create artifacts
        before = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        apply_enrichments(conn, dry_run=True)
        after = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        assert before == after == 0
        checks += 1

        # Check 10: apply creates artifacts
        actions = apply_enrichments(conn, dry_run=False)
        assert len(actions) > 0
        for a in actions:
            assert a["applied"] is True
        checks += 1

        # Check 11: artifacts exist in database
        artifact_count = conn.execute(
            "SELECT COUNT(*) FROM artifacts"
        ).fetchone()[0]
        assert artifact_count > 0
        checks += 1

        # Check 12: lookup finds created artifacts
        results = lookup_entity(conn, "sqlite")
        assert len(results) > 0
        assert results[0]["name"] == "sqlite"
        checks += 1

        # Check 13: lookup for unknown entity returns empty
        assert lookup_entity(conn, "nonexistent_lib_xyz") == []
        checks += 1

        # Check 14: enrich_stats returns expected structure
        stats = enrich_stats(conn)
        assert "total_active_chunks" in stats
        assert "chunks_with_entities" in stats
        assert stats["unique_entities_found"] > 0
        checks += 1

        # Check 15: JSON serialization works
        j = json.dumps(scan, indent=2)
        parsed = json.loads(j)
        assert len(parsed) > 0
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert scan_enrichments(empty_conn) == []
        empty_stats = enrich_stats(empty_conn)
        assert empty_stats["total_active_chunks"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS enrich selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus enrichment")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan for entity mentions")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Create artifact entries")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    p_lookup = sub.add_parser("lookup", help="Look up an entity")
    p_lookup.add_argument("--name", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Enrichment statistics")
    p_stats.add_argument("--db", default=str(DEFAULT_DB))
    p_stats.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "scan":
        results = scan_enrichments(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No entities found.")
            else:
                print(f"  {len(results)} chunk(s) with entities:")
                for r in results[:50]:
                    names = ", ".join(e["name"] for e in r["entities"])
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"[{names}]")

    elif args.cmd == "apply":
        results = apply_enrichments(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}: {len(results)} artifact(s)")
        for r in results[:50]:
            impl = "impl" if r["implemented"] else "disc"
            print(f"    {r['name']:20s}  {r['type']:10s}  {impl}")

    elif args.cmd == "lookup":
        results = lookup_entity(conn, args.name)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No artifacts for '{args.name}'.")
            else:
                print(f"  {len(results)} artifact(s) for '{args.name}':")
                for r in results:
                    impl = "implemented" if r["implemented"] else "discussed"
                    print(f"    {r['artifact_id'][:12]}  {r['artifact_type']:10s}  "
                          f"{impl}  {r['chunk_status']}")

    elif args.cmd == "stats":
        stats = enrich_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Active chunks:       {stats['total_active_chunks']}")
            print(f"  With entities:       {stats['chunks_with_entities']}")
            print(f"  Entity coverage:     {stats['entity_coverage']:.1%}")
            print(f"  Unique entities:     {stats['unique_entities_found']}")
            print(f"  Total mentions:      {stats['total_mentions']}")
            print(f"  Implemented:         {stats['implemented_count']}")
            print(f"  Existing artifacts:  {stats['existing_artifacts']}")
            print("  Top entities:")
            for name, count in stats["top_entities"].items():
                print(f"    {name:20s}: {count:5d}")

    conn.close()


if __name__ == "__main__":
    main()
