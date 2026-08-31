#!/usr/bin/env python3
"""Language distribution analysis: patterns in chunk language tags.

Analyses the lang column of chunks to reveal language diversity,
per-source language profiles, and language-quality correlations.

Usage:
    python tools/corpus/language_distribution.py distribution [--db PATH] [--json]
    python tools/corpus/language_distribution.py per-source [--db PATH] [--json]
    python tools/corpus/language_distribution.py per-kind [--db PATH] [--json]
    python tools/corpus/language_distribution.py summary [--db PATH] [--json]
    python tools/corpus/language_distribution.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def lang_distribution(conn) -> list[dict]:
    """Language distribution across accepted chunks."""
    rows = conn.execute(
        "SELECT COALESCE(lang, '(unset)') AS language, "
        "count(*) AS chunk_count, "
        "sum(word_count) AS total_words "
        "FROM chunks WHERE status = 'accepted' "
        "GROUP BY language "
        "ORDER BY chunk_count DESC"
    ).fetchall()

    if not rows:
        return []

    grand_total = sum(r[1] for r in rows)
    return [
        {
            "language": r[0],
            "chunk_count": r[1],
            "share": round(r[1] / grand_total, 4) if grand_total > 0 else 0.0,
            "total_words": r[2],
        }
        for r in rows
    ]


def lang_per_source(conn) -> list[dict]:
    """Language diversity per source."""
    rows = conn.execute(
        "SELECT ch.source_id, s.title, "
        "COALESCE(ch.lang, '(unset)') AS language "
        "FROM chunks ch "
        "JOIN sources s ON ch.source_id = s.source_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_source: dict[str, dict] = {}
    for sid, title, lang in rows:
        if sid not in by_source:
            by_source[sid] = {"title": title, "langs": {}}
        by_source[sid]["langs"][lang] = (
            by_source[sid]["langs"].get(lang, 0) + 1
        )

    results = []
    for sid, info in by_source.items():
        total = sum(info["langs"].values())
        dominant = max(info["langs"], key=info["langs"].get)
        results.append({
            "source_id": sid,
            "title": info["title"],
            "chunk_count": total,
            "distinct_languages": len(info["langs"]),
            "dominant_language": dominant,
            "dominant_share": round(
                info["langs"][dominant] / total, 4
            ) if total > 0 else 0.0,
        })

    results.sort(key=lambda r: -r["distinct_languages"])
    return results


def lang_per_kind(conn) -> list[dict]:
    """Language distribution per chunk kind."""
    rows = conn.execute(
        "SELECT kind, COALESCE(lang, '(unset)') AS language, "
        "count(*) AS chunk_count "
        "FROM chunks WHERE status = 'accepted' "
        "GROUP BY kind, language "
        "ORDER BY chunk_count DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "kind": r[0],
            "language": r[1],
            "chunk_count": r[2],
        }
        for r in rows
    ]


def lang_summary(conn) -> dict:
    """Aggregate language statistics."""
    rows = conn.execute(
        "SELECT COALESCE(lang, '(unset)'), kind, word_count, source_id "
        "FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_chunks": 0,
            "distinct_languages": 0,
            "unset_count": 0,
            "unset_rate": 0.0,
            "dominant_language": None,
            "source_count": 0,
            "multilingual_sources": 0,
        }

    langs: dict[str, int] = {}
    sources: dict[str, set] = {}
    unset = 0

    for lang, kind, wc, sid in rows:
        langs[lang] = langs.get(lang, 0) + 1
        if sid not in sources:
            sources[sid] = set()
        sources[sid].add(lang)
        if lang == "(unset)":
            unset += 1

    n = len(rows)
    dominant = max(langs, key=langs.get)
    multilingual = sum(1 for s in sources.values() if len(s) > 1)

    return {
        "total_chunks": n,
        "distinct_languages": len(langs),
        "unset_count": unset,
        "unset_rate": round(unset / n, 4) if n > 0 else 0.0,
        "dominant_language": dominant,
        "source_count": len(sources),
        "multilingual_sources": multilingual,
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

        for sid, uri, kind in [("s1", "https://s1.com", "paper"),
                                ("s2", "https://s2.com", "local_md")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunks = [
            ("c1", "s1", 0, "en", "claim"),
            ("c2", "s1", 1, "en", "prose"),
            ("c3", "s1", 2, "python", "code"),
            ("c4", "s2", 0, "en", "prose"),
            ("c5", "s2", 1, None, "config"),
            ("c6", "s2", 2, "sql", "code"),
            ("c7", "s2", 3, "en", "claim"),
        ]
        for cid, sid, ordinal, lang, kind in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", kind, lang,
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        conn.commit()

        # 1: distribution returns entries
        dist = lang_distribution(conn)
        assert len(dist) > 0
        checks += 1

        # 2: en is the most common language
        assert dist[0]["language"] == "en"
        assert dist[0]["chunk_count"] == 4
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(d["share"] for d in dist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: (unset) present for c5
        lang_set = {d["language"] for d in dist}
        assert "(unset)" in lang_set
        checks += 1

        # 5: per-source returns 2 sources
        ps = lang_per_source(conn)
        assert len(ps) == 2
        checks += 1

        # 6: s1 has 2 distinct languages (en, python)
        s1 = next(p for p in ps if p["source_id"] == "s1")
        assert s1["distinct_languages"] == 2
        checks += 1

        # 7: s2 has 3 distinct languages (en, sql, (unset))
        s2 = next(p for p in ps if p["source_id"] == "s2")
        assert s2["distinct_languages"] == 3
        checks += 1

        # 8: sorted by distinct_languages descending
        dl = [p["distinct_languages"] for p in ps]
        assert dl == sorted(dl, reverse=True)
        checks += 1

        # 9: per-kind returns entries
        pk = lang_per_kind(conn)
        assert len(pk) > 0
        checks += 1

        # 10: code kind has python and sql
        code_langs = {r["language"] for r in pk if r["kind"] == "code"}
        assert code_langs == {"python", "sql"}
        checks += 1

        # 11: summary has correct totals
        summary = lang_summary(conn)
        assert summary["total_chunks"] == 7
        assert summary["distinct_languages"] == 4
        checks += 1

        # 12: unset count and multilingual sources
        assert summary["unset_count"] == 1
        assert summary["multilingual_sources"] == 2
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(ps)
        _ = json.dumps(pk)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = lang_distribution(conn2)
        assert empty == []
        empty_summary = lang_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS language_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Language distribution analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Language distribution")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_src = sub.add_parser("per-source",
                           help="Language diversity per source")
    p_src.add_argument("--db", default=DEFAULT_DB)
    p_src.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("per-kind",
                            help="Language distribution per chunk kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Language statistics")
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

    if args.cmd == "distribution":
        results = lang_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['language']:12s}  {r['chunk_count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-source":
        results = lang_per_source(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['title'][:30]:30s}  langs={r['distinct_languages']}  "
                      f"dominant={r['dominant_language']}  "
                      f"({r['dominant_share']:.0%})")

    elif args.cmd == "per-kind":
        results = lang_per_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:8s}  {r['language']:12s}  "
                      f"n={r['chunk_count']:3d}")

    elif args.cmd == "summary":
        result = lang_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunks: {result['total_chunks']}, "
                  f"{result['distinct_languages']} languages")
            print(f"  Dominant: {result['dominant_language']}  "
                  f"Unset: {result['unset_count']} "
                  f"({result['unset_rate']:.1%})")
            print(f"  Sources: {result['source_count']}  "
                  f"Multilingual: {result['multilingual_sources']}")

    conn.close()


if __name__ == "__main__":
    main()
