#!/usr/bin/env python3
"""Artifact adoption: analyses technology artifacts extracted from chunks.

Examines the artifacts table to find adoption patterns, unimplemented
references, type distribution, and orphaned artifacts whose parent
chunk has been quarantined or rejected.

Usage:
    python tools/corpus/artifact_adoption.py summary [--db PATH] [--json]
    python tools/corpus/artifact_adoption.py unimplemented [--db PATH] [--limit N] [--json]
    python tools/corpus/artifact_adoption.py by-source [--db PATH] [--json]
    python tools/corpus/artifact_adoption.py orphans [--db PATH] [--json]
    python tools/corpus/artifact_adoption.py selftest
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


def adoption_summary(conn) -> dict:
    """Corpus-wide artifact adoption statistics."""
    if not _table_exists(conn, "artifacts"):
        return {"total": 0, "implemented": 0, "unimplemented": 0,
                "rate": 0.0, "by_type": {}}

    total = conn.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    if total == 0:
        return {"total": 0, "implemented": 0, "unimplemented": 0,
                "rate": 0.0, "by_type": {}}

    implemented = conn.execute(
        "SELECT count(*) FROM artifacts WHERE implemented = 1"
    ).fetchone()[0]

    rows = conn.execute(
        "SELECT artifact_type, count(*) AS total, "
        "sum(CASE WHEN implemented = 1 THEN 1 ELSE 0 END) AS impl "
        "FROM artifacts GROUP BY artifact_type ORDER BY total DESC"
    ).fetchall()

    by_type = {}
    for r in rows:
        t = r[1]
        i = r[2]
        by_type[r[0]] = {
            "total": t, "implemented": i,
            "rate": round(i / t, 4) if t else 0.0,
        }

    return {
        "total": total,
        "implemented": implemented,
        "unimplemented": total - implemented,
        "rate": round(implemented / total, 4),
        "by_type": by_type,
    }


def unimplemented_artifacts(conn, limit: int = 50) -> list[dict]:
    """Artifacts marked as not implemented, with their parent chunk context."""
    if not _table_exists(conn, "artifacts"):
        return []

    rows = conn.execute(
        "SELECT a.artifact_id, a.name, a.artifact_type, a.version, "
        "a.chunk_id, c.source_id, c.heading_path, c.kind "
        "FROM artifacts a "
        "JOIN chunks c ON c.chunk_id = a.chunk_id "
        "WHERE a.implemented = 0 "
        "ORDER BY a.artifact_type, a.name "
        "LIMIT ?",
        (limit,),
    ).fetchall()

    return [
        {"artifact_id": r[0], "name": r[1], "artifact_type": r[2],
         "version": r[3], "chunk_id": r[4], "source_id": r[5],
         "heading_path": r[6], "chunk_kind": r[7]}
        for r in rows
    ]


def artifacts_by_source(conn) -> list[dict]:
    """Artifact counts per source, showing technology density."""
    if not _table_exists(conn, "artifacts"):
        return []

    rows = conn.execute(
        "SELECT c.source_id, s.title, count(*) AS artifact_count, "
        "sum(CASE WHEN a.implemented = 1 THEN 1 ELSE 0 END) AS implemented, "
        "count(DISTINCT a.artifact_type) AS type_variety "
        "FROM artifacts a "
        "JOIN chunks c ON c.chunk_id = a.chunk_id "
        "JOIN sources s ON s.source_id = c.source_id "
        "GROUP BY c.source_id "
        "ORDER BY artifact_count DESC",
    ).fetchall()

    return [
        {"source_id": r[0], "title": r[1], "artifact_count": r[2],
         "implemented": r[3], "type_variety": r[4],
         "adoption_rate": round(r[3] / r[2], 4) if r[2] else 0.0}
        for r in rows
    ]


def orphan_artifacts(conn) -> list[dict]:
    """Artifacts whose parent chunk is quarantined or rejected."""
    if not _table_exists(conn, "artifacts"):
        return []

    rows = conn.execute(
        "SELECT a.artifact_id, a.name, a.artifact_type, a.implemented, "
        "a.chunk_id, c.status, c.source_id "
        "FROM artifacts a "
        "JOIN chunks c ON c.chunk_id = a.chunk_id "
        "WHERE c.status IN ('quarantined', 'rejected') "
        "ORDER BY c.status, a.name",
    ).fetchall()

    return [
        {"artifact_id": r[0], "name": r[1], "artifact_type": r[2],
         "implemented": r[3], "chunk_id": r[4], "chunk_status": r[5],
         "source_id": r[6]}
        for r in rows
    ]


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

        for sid in ["s1", "s2"]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_data = [
            ("c1", "s1", 0, "H1", "claim", "accepted"),
            ("c2", "s1", 1, "H2", "code", "accepted"),
            ("c3", "s2", 0, "H3", "claim", "accepted"),
            ("c4", "s2", 1, "H4", "claim", "quarantined"),
            ("c5", "s2", 2, "H5", "code", "rejected"),
        ]
        for cd in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cd[0], cd[1], cd[2], cd[3], cd[4], "en",
                 "text", "text", 10, f"n_{cd[0]}", cd[5], now),
            )

        artifact_data = [
            ("a1", "c1", "library", "numpy", "1.26", "import numpy", 1, None),
            ("a2", "c1", "api", "REST /v2", None, "GET /v2/items", 1, None),
            ("a3", "c2", "command", "pip install", None, None, 0, None),
            ("a4", "c3", "library", "pandas", "2.1", "import pandas", 0, None),
            ("a5", "c3", "pattern", "factory", None, None, 1, None),
            ("a6", "c4", "library", "torch", "2.0", None, 1, None),
            ("a7", "c5", "config", "pyproject.toml", None, None, 0, None),
        ]
        for ad in artifact_data:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
                "name, version, snippet, implemented, evidence_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ad,
            )
        conn.commit()

        # 1: summary totals
        s = adoption_summary(conn)
        assert s["total"] == 7
        assert s["implemented"] == 4
        assert s["unimplemented"] == 3
        checks += 1

        # 2: adoption rate
        assert s["rate"] == round(4 / 7, 4)
        checks += 1

        # 3: by_type breakdown
        assert "library" in s["by_type"]
        assert s["by_type"]["library"]["total"] == 3
        assert s["by_type"]["library"]["implemented"] == 2
        checks += 1

        # 4: unimplemented list
        ui = unimplemented_artifacts(conn, limit=50)
        ui_names = {u["name"] for u in ui}
        assert "pip install" in ui_names
        assert "pandas" in ui_names
        assert "pyproject.toml" in ui_names
        checks += 1

        # 5: implemented artifacts excluded from unimplemented
        assert "numpy" not in ui_names
        assert "factory" not in ui_names
        checks += 1

        # 6: unimplemented includes chunk context
        pandas_entry = [u for u in ui if u["name"] == "pandas"][0]
        assert pandas_entry["source_id"] == "s2"
        assert pandas_entry["chunk_kind"] == "claim"
        checks += 1

        # 7: limit parameter
        ui2 = unimplemented_artifacts(conn, limit=1)
        assert len(ui2) == 1
        checks += 1

        # 8: by-source counts
        bs = artifacts_by_source(conn)
        assert len(bs) == 2
        checks += 1

        # 9: source ordering by artifact count
        assert bs[0]["source_id"] == "s2"
        assert bs[0]["artifact_count"] == 4
        checks += 1

        # 10: type variety
        s1_row = [b for b in bs if b["source_id"] == "s1"][0]
        assert s1_row["type_variety"] == 3
        checks += 1

        # 11: orphan artifacts (quarantined/rejected parent chunks)
        orph = orphan_artifacts(conn)
        orph_names = {o["name"] for o in orph}
        assert "torch" in orph_names
        assert "pyproject.toml" in orph_names
        checks += 1

        # 12: accepted chunk artifacts excluded from orphans
        assert "numpy" not in orph_names
        assert "pandas" not in orph_names
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(s)
        _ = json.dumps(ui)
        _ = json.dumps(bs)
        _ = json.dumps(orph)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert adoption_summary(conn2)["total"] == 0
        assert unimplemented_artifacts(conn2) == []
        assert artifacts_by_source(conn2) == []
        assert orphan_artifacts(conn2) == []
        checks += 1

    print(f"PASS artifact_adoption selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact adoption: technology reference analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_sum = sub.add_parser("summary",
                           help="Corpus-wide adoption statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    p_ui = sub.add_parser("unimplemented",
                          help="Unimplemented artifact references")
    p_ui.add_argument("--db", default=DEFAULT_DB)
    p_ui.add_argument("--limit", type=int, default=50)
    p_ui.add_argument("--json", action="store_true")

    p_bs = sub.add_parser("by-source",
                          help="Artifact counts per source")
    p_bs.add_argument("--db", default=DEFAULT_DB)
    p_bs.add_argument("--json", action="store_true")

    p_or = sub.add_parser("orphans",
                          help="Artifacts on quarantined/rejected chunks")
    p_or.add_argument("--db", default=DEFAULT_DB)
    p_or.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "summary":
        result = adoption_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total']} total, "
                  f"{result['implemented']} implemented "
                  f"({result['rate']:.1%})")
            for typ, stats in sorted(result["by_type"].items()):
                print(f"  {typ}: {stats['implemented']}/{stats['total']} "
                      f"({stats['rate']:.1%})")

    elif args.cmd == "unimplemented":
        result = unimplemented_artifacts(conn, limit=args.limit)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Unimplemented artifacts: {len(result)}")
            for r in result:
                ver = f" v{r['version']}" if r["version"] else ""
                print(f"  {r['name']}{ver} ({r['artifact_type']}) "
                      f"in {r['chunk_id']}")

    elif args.cmd == "by-source":
        result = artifacts_by_source(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources with artifacts: {len(result)}")
            for r in result:
                print(f"  {r['source_id']}: {r['artifact_count']} artifacts, "
                      f"{r['implemented']} implemented "
                      f"({r['adoption_rate']:.1%}), "
                      f"{r['type_variety']} types")

    elif args.cmd == "orphans":
        result = orphan_artifacts(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Orphaned artifacts: {len(result)}")
            for r in result:
                impl = "impl" if r["implemented"] else "unimpl"
                print(f"  {r['name']} ({r['artifact_type']}, {impl}) "
                      f"chunk {r['chunk_id']} [{r['chunk_status']}]")

    conn.close()


if __name__ == "__main__":
    main()
