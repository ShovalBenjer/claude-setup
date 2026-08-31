#!/usr/bin/env python3
"""Classification timeline: chunk_domains.classified_utc distribution.

The chunk_domains.classified_utc column had no temporal distribution
analysis.  Existing tools (domain_analysis, domain_balance,
domain_score_distribution) analyse domain membership and scores but
never when classification activity happens over time or how scores
evolve across classification periods.

Usage:
    python tools/corpus/classification_timeline.py timeline [--db PATH] [--json]
    python tools/corpus/classification_timeline.py by-domain [--db PATH] [--json]
    python tools/corpus/classification_timeline.py score-trend [--db PATH] [--json]
    python tools/corpus/classification_timeline.py summary [--db PATH] [--json]
    python tools/corpus/classification_timeline.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_month(s: str | None) -> str | None:
    if not s and s != "":
        return None
    if not s:
        return None
    try:
        return s[:7]
    except (TypeError, IndexError):
        return None


def classification_timeline(conn) -> list[dict]:
    """Distribution of domain classification times by month."""
    rows = conn.execute(
        "SELECT classified_utc FROM chunk_domains "
        "WHERE classified_utc IS NOT NULL AND classified_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, int] = {}
    for (cutc,) in rows:
        mk = _parse_month(cutc)
        if mk:
            by_month[mk] = by_month.get(mk, 0) + 1

    if not by_month:
        return []

    total = sum(by_month.values())
    results = [
        {
            "month": m,
            "count": c,
            "share": round(c / total, 4),
        }
        for m, c in sorted(by_month.items())
    ]
    return results


def classification_by_domain(conn) -> list[dict]:
    """Classification timeline broken down by domain."""
    rows = conn.execute(
        "SELECT domain, classified_utc FROM chunk_domains "
        "WHERE classified_utc IS NOT NULL AND classified_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_dom: dict[str, dict] = {}
    for domain, cutc in rows:
        if domain not in by_dom:
            by_dom[domain] = {"total": 0, "months": set()}
        by_dom[domain]["total"] += 1
        mk = _parse_month(cutc)
        if mk:
            by_dom[domain]["months"].add(mk)

    results = []
    for dom in sorted(by_dom):
        info = by_dom[dom]
        results.append({
            "domain": dom,
            "total_classifications": info["total"],
            "distinct_months": len(info["months"]),
        })

    return results


def score_trend_by_month(conn) -> list[dict]:
    """Mean classification score per month."""
    rows = conn.execute(
        "SELECT classified_utc, score FROM chunk_domains "
        "WHERE classified_utc IS NOT NULL AND classified_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, list[float]] = {}
    for cutc, score in rows:
        mk = _parse_month(cutc)
        if mk:
            if mk not in by_month:
                by_month[mk] = []
            by_month[mk].append(score)

    if not by_month:
        return []

    results = []
    for m in sorted(by_month):
        scores = by_month[m]
        n = len(scores)
        results.append({
            "month": m,
            "count": n,
            "mean_score": round(sum(scores) / n, 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
        })

    return results


def classification_summary(conn) -> dict:
    """Aggregate classification timeline statistics."""
    total_row = conn.execute(
        "SELECT count(*) FROM chunk_domains"
    ).fetchone()

    if not total_row or total_row[0] == 0:
        return {
            "total_classifications": 0,
            "distinct_domains": 0,
            "distinct_months": 0,
            "classification_range": None,
            "mean_score": 0.0,
        }

    total = total_row[0]

    dom_row = conn.execute(
        "SELECT count(DISTINCT domain) FROM chunk_domains"
    ).fetchone()
    distinct_domains = dom_row[0] if dom_row else 0

    score_row = conn.execute(
        "SELECT avg(score) FROM chunk_domains"
    ).fetchone()
    mean_score = round(score_row[0], 4) if score_row and score_row[0] else 0.0

    tl = classification_timeline(conn)
    months = [r["month"] for r in tl]

    return {
        "total_classifications": total,
        "distinct_domains": distinct_domains,
        "distinct_months": len(months),
        "classification_range": (
            {"earliest": months[0], "latest": months[-1]}
            if months else None
        ),
        "mean_score": mean_score,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             "2026-06-01T00:00:00Z", "2026-06-01T00:00:00Z",
             "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted",
                 "2026-06-01T00:00:00Z"),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "domain TEXT NOT NULL, "
            "score REAL NOT NULL, "
            "classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )

        classifications = [
            ("c1", "ml", 0.9, "2026-06-10T00:00:00Z"),
            ("c1", "nlp", 0.7, "2026-06-10T00:00:00Z"),
            ("c2", "ml", 0.8, "2026-06-20T00:00:00Z"),
            ("c2", "systems", 0.6, "2026-07-05T00:00:00Z"),
            ("c3", "nlp", 0.85, "2026-07-15T00:00:00Z"),
            ("c3", "ml", 0.5, "2026-07-15T00:00:00Z"),
            ("c4", "systems", 0.95, "2026-08-01T00:00:00Z"),
            ("c4", "ml", 0.4, "2026-08-01T00:00:00Z"),
        ]
        for cid, dom, score, cutc in classifications:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)",
                (cid, dom, score, cutc),
            )

        conn.commit()

        # 1: timeline returns 3 months (Jun, Jul, Aug)
        tl = classification_timeline(conn)
        assert len(tl) == 3
        checks += 1

        # 2: June has 3 classifications
        jun = next(t for t in tl if t["month"] == "2026-06")
        assert jun["count"] == 3
        checks += 1

        # 3: shares sum to 1.0
        share_sum = sum(t["share"] for t in tl)
        assert abs(share_sum - 1.0) < 0.01
        checks += 1

        # 4: July has 3 classifications
        jul = next(t for t in tl if t["month"] == "2026-07")
        assert jul["count"] == 3
        checks += 1

        # 5: by-domain returns 3 domains
        bd = classification_by_domain(conn)
        assert len(bd) == 3
        checks += 1

        # 6: ml domain has 4 total classifications
        ml = next(d for d in bd if d["domain"] == "ml")
        assert ml["total_classifications"] == 4
        checks += 1

        # 7: ml spans 3 distinct months
        assert ml["distinct_months"] == 3
        checks += 1

        # 8: systems has 2 classifications
        sys_dom = next(d for d in bd if d["domain"] == "systems")
        assert sys_dom["total_classifications"] == 2
        checks += 1

        # 9: score trend returns entries
        st = score_trend_by_month(conn)
        assert len(st) == 3
        checks += 1

        # 10: June mean score: (0.9+0.7+0.8)/3 = 0.8
        jun_st = next(s for s in st if s["month"] == "2026-06")
        assert abs(jun_st["mean_score"] - 0.8) < 0.01
        checks += 1

        # 11: August has lowest mean (0.95+0.4)/2 = 0.675
        aug_st = next(s for s in st if s["month"] == "2026-08")
        assert abs(aug_st["mean_score"] - 0.675) < 0.01
        checks += 1

        # 12: summary has correct totals
        summary = classification_summary(conn)
        assert summary["total_classifications"] == 8
        assert summary["distinct_domains"] == 3
        assert summary["distinct_months"] == 3
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(tl)
        _ = json.dumps(bd)
        _ = json.dumps(st)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL NOT NULL, classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        empty = classification_timeline(conn2)
        assert empty == []
        empty_summary = classification_summary(conn2)
        assert empty_summary["total_classifications"] == 0
        checks += 1

    print(f"PASS classification_timeline selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classification timeline analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_tl = sub.add_parser("timeline",
                          help="Classification times by month")
    p_tl.add_argument("--db", default=DEFAULT_DB)
    p_tl.add_argument("--json", action="store_true")

    p_bd = sub.add_parser("by-domain",
                          help="Classification per domain")
    p_bd.add_argument("--db", default=DEFAULT_DB)
    p_bd.add_argument("--json", action="store_true")

    p_st = sub.add_parser("score-trend",
                          help="Score trend by month")
    p_st.add_argument("--db", default=DEFAULT_DB)
    p_st.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Classification statistics")
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

    if args.cmd == "timeline":
        results = classification_timeline(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['month']}  count={r['count']}  "
                      f"share={r['share']:.0%}")

    elif args.cmd == "by-domain":
        results = classification_by_domain(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['domain']:16s}  "
                      f"n={r['total_classifications']:3d}  "
                      f"months={r['distinct_months']}")

    elif args.cmd == "score-trend":
        results = score_trend_by_month(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['month']}  n={r['count']}  "
                      f"mean={r['mean_score']:.3f}  "
                      f"min={r['min_score']:.3f}  "
                      f"max={r['max_score']:.3f}")

    elif args.cmd == "summary":
        result = classification_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Classifications: "
                  f"{result['total_classifications']}  "
                  f"Domains: {result['distinct_domains']}  "
                  f"Months: {result['distinct_months']}")
            print(f"  Mean score: {result['mean_score']:.3f}")
            if result["classification_range"]:
                cr = result["classification_range"]
                print(f"  Range: {cr['earliest']} to "
                      f"{cr['latest']}")

    conn.close()


if __name__ == "__main__":
    main()
