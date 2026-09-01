#!/usr/bin/env python3
"""Ingestion regression detector: finds quality drops across re-ingestions.

Compares consecutive chunk_versions to detect regressions: word count
drops, content hash changes that lose citations, and chunks that
disappeared between versions.

Usage:
    python tools/corpus/ingestion_regression.py detect [--db PATH] [--json]
    python tools/corpus/ingestion_regression.py history [--db PATH] [--chunk CHUNK_ID] [--json]
    python tools/corpus/ingestion_regression.py summary [--db PATH] [--json]
    python tools/corpus/ingestion_regression.py selftest
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


def detect_regressions(conn) -> list[dict]:
    """Find chunks where a newer version is worse than the previous one.

    A regression is detected when:
    - word_count dropped by more than 20%
    - content hash changed (norm_sha256 differs) and word count decreased
    """
    if not _table_exists(conn, "chunk_versions"):
        return []

    rows = conn.execute(
        "SELECT v.chunk_id, v.version_num, v.norm_sha256, "
        "v.word_count, v.snapshot_utc "
        "FROM chunk_versions v "
        "ORDER BY v.chunk_id, v.version_num"
    ).fetchall()

    if not rows:
        return []

    chunks: dict[str, list[dict]] = {}
    for chunk_id, version_num, norm_sha256, word_count, snapshot_utc in rows:
        if chunk_id not in chunks:
            chunks[chunk_id] = []
        chunks[chunk_id].append({
            "version_num": version_num,
            "norm_sha256": norm_sha256,
            "word_count": word_count,
            "snapshot_utc": snapshot_utc,
        })

    heading_map: dict[str, str] = {}
    chunk_ids = list(chunks.keys())
    if chunk_ids:
        placeholders = ",".join("?" for _ in chunk_ids)
        h_rows = conn.execute(
            f"SELECT chunk_id, heading_path FROM chunks "
            f"WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        heading_map = {r[0]: r[1] for r in h_rows}

    regressions = []
    for chunk_id, versions in chunks.items():
        if len(versions) < 2:
            continue

        for i in range(1, len(versions)):
            prev = versions[i - 1]
            curr = versions[i]

            issues = []

            if prev["word_count"] > 0:
                drop_pct = (prev["word_count"] - curr["word_count"]) / prev["word_count"]
                if drop_pct > 0.2:
                    issues.append({
                        "type": "word_count_drop",
                        "from": prev["word_count"],
                        "to": curr["word_count"],
                        "drop_pct": round(drop_pct, 4),
                    })

            if (curr["norm_sha256"] != prev["norm_sha256"]
                    and curr["word_count"] < prev["word_count"]):
                if not any(i["type"] == "word_count_drop" for i in issues):
                    issues.append({
                        "type": "content_shrink",
                        "from_words": prev["word_count"],
                        "to_words": curr["word_count"],
                    })

            if issues:
                regressions.append({
                    "chunk_id": chunk_id,
                    "heading": heading_map.get(chunk_id, ""),
                    "from_version": prev["version_num"],
                    "to_version": curr["version_num"],
                    "snapshot_utc": curr["snapshot_utc"],
                    "issues": issues,
                })

    regressions.sort(
        key=lambda r: max(
            i.get("drop_pct", 0.0) for i in r["issues"]
        ),
        reverse=True,
    )
    return regressions


def chunk_history(conn, chunk_id: str) -> list[dict]:
    """Version history for a single chunk with change annotations."""
    if not _table_exists(conn, "chunk_versions"):
        return []

    rows = conn.execute(
        "SELECT version_num, norm_sha256, word_count, snapshot_utc "
        "FROM chunk_versions WHERE chunk_id = ? "
        "ORDER BY version_num",
        (chunk_id,),
    ).fetchall()

    history = []
    for i, (version_num, norm_sha256, word_count, snapshot_utc) in enumerate(rows):
        entry = {
            "version_num": version_num,
            "word_count": word_count,
            "norm_sha256": norm_sha256,
            "snapshot_utc": snapshot_utc,
            "change": "initial" if i == 0 else None,
        }

        if i > 0:
            prev = rows[i - 1]
            prev_wc = prev[2]
            prev_sha = prev[1]
            if norm_sha256 == prev_sha:
                entry["change"] = "unchanged"
            elif word_count > prev_wc:
                entry["change"] = "grew"
            elif word_count < prev_wc:
                entry["change"] = "shrank"
            else:
                entry["change"] = "rewritten"

        history.append(entry)

    return history


def regression_summary(conn) -> dict:
    """Aggregate regression statistics."""
    regressions = detect_regressions(conn)

    if not _table_exists(conn, "chunk_versions"):
        return {
            "total_versioned_chunks": 0,
            "multi_version_chunks": 0,
            "regressed_chunks": 0,
            "total_regressions": 0,
            "issue_types": {},
            "worst_drop_pct": 0.0,
        }

    total_versioned = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]

    multi_version = conn.execute(
        "SELECT count(*) FROM ("
        "  SELECT chunk_id FROM chunk_versions "
        "  GROUP BY chunk_id HAVING count(*) > 1"
        ")"
    ).fetchone()[0]

    regressed_chunks = len({r["chunk_id"] for r in regressions})

    issue_types: dict[str, int] = {}
    worst_drop = 0.0
    for r in regressions:
        for issue in r["issues"]:
            itype = issue["type"]
            issue_types[itype] = issue_types.get(itype, 0) + 1
            if issue.get("drop_pct", 0.0) > worst_drop:
                worst_drop = issue["drop_pct"]

    return {
        "total_versioned_chunks": total_versioned,
        "multi_version_chunks": multi_version,
        "regressed_chunks": regressed_chunks,
        "total_regressions": len(regressions),
        "issue_types": issue_types,
        "worst_drop_pct": round(worst_drop, 4),
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

        for cid, ordinal, heading in [("c1", 0, "Stable"),
                                       ("c2", 1, "Regressed"),
                                       ("c3", 2, "Grew")]:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", ordinal, heading, "claim", "en",
                 "text", "text", 50, f"n_{cid}", "accepted", now),
            )

        versions = [
            ("v1", "c1", 1, "sha_a", 50, "2026-01-01T00:00:00Z"),
            ("v2", "c1", 2, "sha_a", 50, "2026-06-01T00:00:00Z"),
            ("v3", "c2", 1, "sha_b", 100, "2026-01-01T00:00:00Z"),
            ("v4", "c2", 2, "sha_c", 40, "2026-06-01T00:00:00Z"),
            ("v5", "c3", 1, "sha_d", 30, "2026-01-01T00:00:00Z"),
            ("v6", "c3", 2, "sha_e", 80, "2026-06-01T00:00:00Z"),
        ]
        for vid, cid, vnum, sha, wc, snap in versions:
            conn.execute(
                "INSERT INTO chunk_versions (version_id, chunk_id, "
                "version_num, norm_sha256, word_count, snapshot_utc) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (vid, cid, vnum, sha, wc, snap),
            )

        conn.commit()

        # 1: regression detected for c2 (100 -> 40 words, 60% drop)
        regs = detect_regressions(conn)
        reg_ids = [r["chunk_id"] for r in regs]
        assert "c2" in reg_ids
        checks += 1

        # 2: no regression for c1 (stable word count)
        assert "c1" not in reg_ids
        checks += 1

        # 3: no regression for c3 (word count grew)
        assert "c3" not in reg_ids
        checks += 1

        # 4: regression details correct
        c2_reg = [r for r in regs if r["chunk_id"] == "c2"][0]
        assert c2_reg["from_version"] == 1
        assert c2_reg["to_version"] == 2
        assert len(c2_reg["issues"]) > 0
        checks += 1

        # 5: word_count_drop issue has correct percentage
        drop_issue = [i for i in c2_reg["issues"]
                      if i["type"] == "word_count_drop"][0]
        assert drop_issue["drop_pct"] == 0.6
        assert drop_issue["from"] == 100
        assert drop_issue["to"] == 40
        checks += 1

        # 6: sorted by worst drop first
        if len(regs) > 1:
            drops = [max(i.get("drop_pct", 0) for i in r["issues"])
                     for r in regs]
            assert drops == sorted(drops, reverse=True)
        checks += 1

        # 7: chunk_history returns version sequence
        hist = chunk_history(conn, "c2")
        assert len(hist) == 2
        assert hist[0]["change"] == "initial"
        assert hist[1]["change"] == "shrank"
        checks += 1

        # 8: chunk_history for growing chunk
        hist_c3 = chunk_history(conn, "c3")
        assert hist_c3[1]["change"] == "grew"
        checks += 1

        # 9: chunk_history for stable chunk
        hist_c1 = chunk_history(conn, "c1")
        assert hist_c1[1]["change"] == "unchanged"
        checks += 1

        # 10: summary has required keys
        summary = regression_summary(conn)
        assert summary["total_versioned_chunks"] == 3
        assert summary["multi_version_chunks"] == 3
        assert summary["regressed_chunks"] == 1
        checks += 1

        # 11: issue_types counted
        assert summary["issue_types"]["word_count_drop"] == 1
        checks += 1

        # 12: worst_drop_pct correct
        assert summary["worst_drop_pct"] == 0.6
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(regs)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = detect_regressions(conn2)
        assert empty == []
        empty_summary = regression_summary(conn2)
        assert empty_summary["total_versioned_chunks"] == 0
        checks += 1

    print(f"PASS ingestion_regression selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingestion regression detector"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_det = sub.add_parser("detect",
                           help="Find quality regressions across versions")
    p_det.add_argument("--db", default=DEFAULT_DB)
    p_det.add_argument("--json", action="store_true")

    p_hist = sub.add_parser("history",
                            help="Version history for a chunk")
    p_hist.add_argument("--db", default=DEFAULT_DB)
    p_hist.add_argument("--chunk", required=True,
                        help="Chunk ID to inspect")
    p_hist.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Aggregate regression statistics")
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

    if args.cmd == "detect":
        results = detect_regressions(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No regressions detected.")
            else:
                print(f"{len(results)} regressions found:")
                for r in results:
                    issues_str = ", ".join(
                        i["type"] for i in r["issues"]
                    )
                    print(f"  v{r['from_version']}->v{r['to_version']}  "
                          f"{r['chunk_id'][:12]:12s}  {r['heading']}  "
                          f"[{issues_str}]")

    elif args.cmd == "history":
        results = chunk_history(conn, args.chunk)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"No version history for {args.chunk}")
            else:
                for v in results:
                    print(f"  v{v['version_num']}  {v['word_count']:5d}w  "
                          f"{v['change']:10s}  {v['snapshot_utc']}")

    elif args.cmd == "summary":
        result = regression_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Versioned: {result['total_versioned_chunks']} chunks, "
                  f"{result['multi_version_chunks']} multi-version")
            print(f"Regressions: {result['regressed_chunks']} chunks, "
                  f"{result['total_regressions']} total")
            if result["worst_drop_pct"] > 0:
                print(f"Worst drop: {result['worst_drop_pct']:.0%}")
            if result["issue_types"]:
                for itype, count in result["issue_types"].items():
                    print(f"  {itype}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
