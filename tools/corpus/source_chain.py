#!/usr/bin/env python3
"""Source provenance chain: traces supersession relationships between sources.

Builds provenance chains from the supersedes column, identifies active
heads and superseded tails, and detects broken chains where a superseded
source's replacement is missing.

Usage:
    python tools/corpus/source_chain.py chains [--db PATH] [--json]
    python tools/corpus/source_chain.py heads [--db PATH] [--json]
    python tools/corpus/source_chain.py broken [--db PATH] [--json]
    python tools/corpus/source_chain.py selftest
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


def provenance_chains(conn) -> list[dict]:
    """Build all supersession chains from tail to head."""
    if not _table_exists(conn, "sources"):
        return []

    rows = conn.execute(
        "SELECT source_id, supersedes FROM sources "
        "WHERE supersedes IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    supersedes_map: dict[str, str] = {}
    for r in rows:
        supersedes_map[r[0]] = r[1]

    all_sources = {r[0] for r in conn.execute(
        "SELECT source_id FROM sources"
    ).fetchall()}

    superseded_ids = set(supersedes_map.values())

    heads = set()
    for sid in supersedes_map:
        if sid not in superseded_ids:
            heads.add(sid)

    chains = []
    for head in sorted(heads):
        chain = [head]
        current = head
        visited = {current}
        while current in supersedes_map:
            prev = supersedes_map[current]
            if prev in visited:
                break
            chain.append(prev)
            visited.add(prev)
            current = prev

        chunk_counts = {}
        for sid in chain:
            if sid in all_sources:
                count = conn.execute(
                    "SELECT count(*) FROM chunks WHERE source_id = ?",
                    (sid,),
                ).fetchone()[0]
                chunk_counts[sid] = count

        chains.append({
            "head": head,
            "tail": chain[-1],
            "length": len(chain),
            "chain": chain,
            "chunk_counts": chunk_counts,
        })

    chains.sort(key=lambda c: c["length"], reverse=True)
    return chains


def active_heads(conn) -> list[dict]:
    """Sources that supersede others but are not themselves superseded."""
    if not _table_exists(conn, "sources"):
        return []

    rows = conn.execute(
        "SELECT source_id, supersedes FROM sources "
        "WHERE supersedes IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    supersedes_map: dict[str, str] = {r[0]: r[1] for r in rows}
    superseded_ids = set(supersedes_map.values())

    heads = []
    for sid in supersedes_map:
        if sid not in superseded_ids:
            row = conn.execute(
                "SELECT source_id, title, kind, liveness FROM sources "
                "WHERE source_id = ?",
                (sid,),
            ).fetchone()
            if row:
                chunk_count = conn.execute(
                    "SELECT count(*) FROM chunks WHERE source_id = ?",
                    (sid,),
                ).fetchone()[0]
                heads.append({
                    "source_id": row[0], "title": row[1],
                    "kind": row[2], "liveness": row[3],
                    "chunk_count": chunk_count,
                    "supersedes": supersedes_map[sid],
                })

    heads.sort(key=lambda h: h["source_id"])
    return heads


def broken_chains(conn) -> list[dict]:
    """Sources that reference a superseded source_id not in the sources table."""
    if not _table_exists(conn, "sources"):
        return []

    rows = conn.execute(
        "SELECT s.source_id, s.title, s.supersedes "
        "FROM sources s "
        "WHERE s.supersedes IS NOT NULL "
        "AND s.supersedes NOT IN (SELECT source_id FROM sources)"
    ).fetchall()

    return [
        {"source_id": r[0], "title": r[1], "missing_predecessor": r[2]}
        for r in rows
    ]


# ── selftest ─────────────────────────────────────────────────────────


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

        def _insert_source(sid, title, supersedes=None):
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", "paper", title,
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, supersedes),
            )

        def _insert_chunk(cid, sid):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, 0, "H1", "claim", "en",
                 "text", "text", 10, f"n_{cid}", now),
            )

        _insert_source("s1", "Original paper v1")
        _insert_source("s2", "Updated paper v2", supersedes="s1")
        _insert_source("s3", "Latest paper v3", supersedes="s2")

        _insert_source("s4", "Independent paper")

        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_source("s5", "Broken ref paper", supersedes="s_missing")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        for sid in ["s1", "s2", "s3"]:
            _insert_chunk(f"c_{sid}", sid)

        conn.commit()

        # 1: chains detected
        ch = provenance_chains(conn)
        assert len(ch) >= 1
        checks += 1

        # 2: chain s3 -> s2 -> s1
        main_chain = [c for c in ch if c["head"] == "s3"]
        assert len(main_chain) == 1
        assert main_chain[0]["chain"] == ["s3", "s2", "s1"]
        assert main_chain[0]["length"] == 3
        checks += 1

        # 3: head and tail correct
        assert main_chain[0]["head"] == "s3"
        assert main_chain[0]["tail"] == "s1"
        checks += 1

        # 4: chunk counts in chain
        assert main_chain[0]["chunk_counts"]["s1"] == 1
        assert main_chain[0]["chunk_counts"]["s3"] == 1
        checks += 1

        # 5: independent source not in chains
        chain_sources = set()
        for c in ch:
            chain_sources.update(c["chain"])
        assert "s4" not in chain_sources
        checks += 1

        # 6: active heads
        heads = active_heads(conn)
        head_ids = {h["source_id"] for h in heads}
        assert "s3" in head_ids
        checks += 1

        # 7: superseded sources not heads
        assert "s1" not in head_ids
        assert "s2" not in head_ids
        checks += 1

        # 8: head details
        s3_head = [h for h in heads if h["source_id"] == "s3"][0]
        assert s3_head["supersedes"] == "s2"
        assert s3_head["chunk_count"] == 1
        checks += 1

        # 9: broken chains detected
        br = broken_chains(conn)
        assert len(br) == 1
        assert br[0]["source_id"] == "s5"
        assert br[0]["missing_predecessor"] == "s_missing"
        checks += 1

        # 10: valid chains not broken
        broken_ids = {b["source_id"] for b in br}
        assert "s2" not in broken_ids
        assert "s3" not in broken_ids
        checks += 1

        # 11: JSON serialisable
        _ = json.dumps(ch)
        _ = json.dumps(heads)
        _ = json.dumps(br)
        checks += 1

        # 12: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert provenance_chains(conn2) == []
        assert active_heads(conn2) == []
        assert broken_chains(conn2) == []
        checks += 1

        # 13: no supersession relationships
        conn3 = connect(":memory:")
        init_schema(conn3)
        conn3.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Solo",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha1", 1000, None),
        )
        conn3.commit()
        assert provenance_chains(conn3) == []
        assert active_heads(conn3) == []
        assert broken_chains(conn3) == []
        checks += 1

        # 14: chains sorted by length descending
        ch2 = provenance_chains(conn)
        lengths = [c["length"] for c in ch2]
        assert lengths == sorted(lengths, reverse=True)
        checks += 1

    print(f"PASS source_chain selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source provenance chain analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ch = sub.add_parser("chains", help="Supersession chains")
    p_ch.add_argument("--db", default=DEFAULT_DB)
    p_ch.add_argument("--json", action="store_true")

    p_hd = sub.add_parser("heads", help="Active chain heads")
    p_hd.add_argument("--db", default=DEFAULT_DB)
    p_hd.add_argument("--json", action="store_true")

    p_br = sub.add_parser("broken", help="Broken chain references")
    p_br.add_argument("--db", default=DEFAULT_DB)
    p_br.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "chains":
        result = provenance_chains(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Supersession chains: {len(result)}")
            for c in result:
                arrow = " -> ".join(c["chain"])
                print(f"  [{c['length']}] {arrow}")

    elif args.cmd == "heads":
        result = active_heads(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Active chain heads: {len(result)}")
            for h in result:
                print(f"  {h['source_id']}: {h['title']} "
                      f"({h['chunk_count']} chunks, "
                      f"supersedes {h['supersedes']})")

    elif args.cmd == "broken":
        result = broken_chains(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Broken chains: {len(result)}")
            for b in result:
                print(f"  {b['source_id']}: {b['title']} "
                      f"references missing {b['missing_predecessor']}")

    conn.close()


if __name__ == "__main__":
    main()
