#!/usr/bin/env python3
"""Citation locator analysis: patterns in citation locator specificity.

Analyses the locator field of citations to reveal completeness rates,
format patterns, and whether locator specificity correlates with
verification outcomes.

Usage:
    python tools/corpus/citation_locator_analysis.py completeness [--db PATH] [--json]
    python tools/corpus/citation_locator_analysis.py formats [--db PATH] [--json]
    python tools/corpus/citation_locator_analysis.py verification [--db PATH] [--json]
    python tools/corpus/citation_locator_analysis.py summary [--db PATH] [--json]
    python tools/corpus/citation_locator_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

FORMAT_PATTERNS = [
    ("page", re.compile(r"^p(?:p|ages?)?\.?\s*\d", re.IGNORECASE)),
    ("section", re.compile(r"^(?:sec(?:tion)?|ch(?:apter)?|§)\s*\d", re.IGNORECASE)),
    ("line", re.compile(r"^l(?:ine)?s?\s*\d", re.IGNORECASE)),
    ("url_fragment", re.compile(r"^#")),
    ("figure", re.compile(r"^(?:fig(?:ure)?|table)\s*\.?\s*\d", re.IGNORECASE)),
    ("paragraph", re.compile(r"^(?:para(?:graph)?|¶)\s*\d", re.IGNORECASE)),
]


def _classify_format(locator: str) -> str:
    for name, pat in FORMAT_PATTERNS:
        if pat.search(locator):
            return name
    return "other"


def locator_completeness(conn) -> list[dict]:
    """Per-tag locator completeness rates."""
    rows = conn.execute(
        "SELECT c.tag, count(*) AS total, "
        "sum(CASE WHEN c.locator IS NOT NULL AND c.locator != '' "
        "    THEN 1 ELSE 0 END) AS with_locator "
        "FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted' "
        "GROUP BY c.tag "
        "ORDER BY total DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "tag": r[0] or "(none)",
            "total": r[1],
            "with_locator": r[2],
            "without_locator": r[1] - r[2],
            "completeness": round(r[2] / r[1], 4) if r[1] > 0 else 0.0,
        }
        for r in rows
    ]


def locator_formats(conn) -> list[dict]:
    """Distribution of locator format types."""
    rows = conn.execute(
        "SELECT c.locator FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted' "
        "AND c.locator IS NOT NULL AND c.locator != ''"
    ).fetchall()

    if not rows:
        return []

    counts: dict[str, int] = {}
    for (loc,) in rows:
        fmt = _classify_format(loc)
        counts[fmt] = counts.get(fmt, 0) + 1

    total = sum(counts.values())
    results = [
        {
            "format": fmt,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        }
        for fmt, n in counts.items()
    ]
    results.sort(key=lambda r: -r["count"])
    return results


def locator_verification(conn) -> list[dict]:
    """Verification rates by locator presence and format."""
    rows = conn.execute(
        "SELECT c.locator, c.verified FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, dict] = {}
    for loc, verified in rows:
        if not loc or not loc.strip():
            key = "(no locator)"
        else:
            key = _classify_format(loc)
        if key not in buckets:
            buckets[key] = {"total": 0, "verified": 0}
        buckets[key]["total"] += 1
        if verified:
            buckets[key]["verified"] += 1

    results = []
    for key, b in buckets.items():
        results.append({
            "category": key,
            "total": b["total"],
            "verified": b["verified"],
            "unverified": b["total"] - b["verified"],
            "verification_rate": round(
                b["verified"] / b["total"], 4
            ) if b["total"] > 0 else 0.0,
        })
    results.sort(key=lambda r: -r["total"])
    return results


def locator_summary(conn) -> dict:
    """Aggregate locator statistics."""
    rows = conn.execute(
        "SELECT c.locator, c.verified, c.tag FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_citations": 0,
            "with_locator": 0,
            "without_locator": 0,
            "completeness_rate": 0.0,
            "format_count": 0,
            "tag_count": 0,
            "verified_with_locator": 0,
            "verified_without_locator": 0,
        }

    total = len(rows)
    with_loc = 0
    without_loc = 0
    verified_with = 0
    verified_without = 0
    formats_seen: set[str] = set()
    tags_seen: set[str | None] = set()

    for loc, verified, tag in rows:
        tags_seen.add(tag)
        has_loc = bool(loc and loc.strip())
        if has_loc:
            with_loc += 1
            formats_seen.add(_classify_format(loc))
            if verified:
                verified_with += 1
        else:
            without_loc += 1
            if verified:
                verified_without += 1

    return {
        "total_citations": total,
        "with_locator": with_loc,
        "without_locator": without_loc,
        "completeness_rate": round(with_loc / total, 4) if total > 0 else 0.0,
        "format_count": len(formats_seen),
        "tag_count": len(tags_seen),
        "verified_with_locator": verified_with,
        "verified_without_locator": verified_without,
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

        src_id = "s1"
        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (src_id, "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        chunks = [
            ("c1", 0, "claim"), ("c2", 1, "prose"),
            ("c3", 2, "claim"), ("c4", 3, "code"),
        ]
        for cid, ordinal, kind in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, src_id, ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 2, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        citations = [
            ("ci1", "c1", "https://a.com", None, "doi", "p. 42", 1),
            ("ci2", "c1", "https://b.com", None, "doi", "pp. 10-15", 1),
            ("ci3", "c2", "https://c.com", None, "url", "#section-3", 0),
            ("ci4", "c2", "https://d.com", None, "url", "", 0),
            ("ci5", "c3", "https://e.com", None, "isbn", None, 1),
            ("ci6", "c3", "https://f.com", None, "isbn",
             "Section 4.2", 0),
            ("ci7", "c4", "https://g.com", None, "doi",
             "Figure 3", 0),
            ("ci8", "c4", "https://h.com", None, "url",
             "line 55", 1),
        ]
        for cit_id, chunk, uri, tgt_src, tag, loc, verified in citations:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)",
                (cit_id, chunk, uri, tgt_src, tag, loc,
                 verified, now if verified else None),
            )

        conn.commit()

        # 1: completeness returns entries per tag
        comp = locator_completeness(conn)
        assert len(comp) > 0
        checks += 1

        # 2: all tags present
        tag_set = {c["tag"] for c in comp}
        assert tag_set == {"doi", "url", "isbn"}
        checks += 1

        # 3: doi tag has 3 total, all with locator
        doi_row = next(c for c in comp if c["tag"] == "doi")
        assert doi_row["total"] == 3
        assert doi_row["with_locator"] == 3
        checks += 1

        # 4: isbn tag has 1 of 2 with locator
        isbn_row = next(c for c in comp if c["tag"] == "isbn")
        assert isbn_row["with_locator"] == 1
        checks += 1

        # 5: formats returns at least 3 distinct formats
        fmts = locator_formats(conn)
        fmt_set = {f["format"] for f in fmts}
        assert len(fmt_set) >= 3
        checks += 1

        # 6: page format detected for "p. 42" and "pp. 10-15"
        assert "page" in fmt_set
        checks += 1

        # 7: shares sum to approximately 1.0
        total_share = sum(f["share"] for f in fmts)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 8: url_fragment detected for "#section-3"
        assert "url_fragment" in fmt_set
        checks += 1

        # 9: verification returns categories
        verif = locator_verification(conn)
        assert len(verif) > 0
        checks += 1

        # 10: no-locator category exists (ci4 empty, ci5 None)
        no_loc = next(
            (v for v in verif if v["category"] == "(no locator)"), None
        )
        assert no_loc is not None
        assert no_loc["total"] == 2
        checks += 1

        # 11: summary has correct totals
        summary = locator_summary(conn)
        assert summary["total_citations"] == 8
        assert summary["with_locator"] == 6
        assert summary["without_locator"] == 2
        checks += 1

        # 12: completeness rate matches
        assert abs(summary["completeness_rate"] - 6 / 8) < 0.01
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(comp)
        _ = json.dumps(fmts)
        _ = json.dumps(verif)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = locator_completeness(conn2)
        assert empty == []
        empty_summary = locator_summary(conn2)
        assert empty_summary["total_citations"] == 0
        checks += 1

    print(f"PASS citation_locator_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation locator analysis: specificity patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_comp = sub.add_parser("completeness",
                            help="Locator completeness per tag")
    p_comp.add_argument("--db", default=DEFAULT_DB)
    p_comp.add_argument("--json", action="store_true")

    p_fmt = sub.add_parser("formats",
                           help="Locator format distribution")
    p_fmt.add_argument("--db", default=DEFAULT_DB)
    p_fmt.add_argument("--json", action="store_true")

    p_ver = sub.add_parser("verification",
                           help="Verification rates by locator type")
    p_ver.add_argument("--db", default=DEFAULT_DB)
    p_ver.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Locator statistics")
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

    if args.cmd == "completeness":
        results = locator_completeness(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["completeness"] * 30)
                print(f"  {r['tag']:10s}  {r['with_locator']:3d}/"
                      f"{r['total']:3d}  {r['completeness']:5.1%}  {bar}")

    elif args.cmd == "formats":
        results = locator_formats(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['format']:14s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "verification":
        results = locator_verification(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['category']:14s}  "
                      f"total={r['total']:3d}  "
                      f"verified={r['verified']:3d}  "
                      f"rate={r['verification_rate']:5.1%}")

    elif args.cmd == "summary":
        result = locator_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citations: {result['total_citations']}, "
                  f"{result['tag_count']} tags")
            print(f"  With locator: {result['with_locator']}  "
                  f"Without: {result['without_locator']}  "
                  f"Rate: {result['completeness_rate']:.1%}")
            print(f"  Formats: {result['format_count']}  "
                  f"Verified w/loc: {result['verified_with_locator']}  "
                  f"Verified w/o: {result['verified_without_locator']}")

    conn.close()


if __name__ == "__main__":
    main()
