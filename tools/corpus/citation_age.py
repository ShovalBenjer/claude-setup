#!/usr/bin/env python3
"""Citation verification age: staleness of citation checks.

Analyses how recently citations were verified, identifies citations
overdue for re-verification, and reports verification coverage
relative to corpus growth.

Usage:
    python tools/corpus/citation_age.py age [--db PATH] [--json]
    python tools/corpus/citation_age.py overdue [--db PATH] [--days N] [--json]
    python tools/corpus/citation_age.py summary [--db PATH] [--json]
    python tools/corpus/citation_age.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_utc(s: str | None) -> datetime.datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def citation_ages(conn) -> list[dict]:
    """Per-citation verification age in days."""
    rows = conn.execute(
        "SELECT c.citation_id, c.chunk_id, c.target_uri, c.tag, "
        "c.verified, c.verified_utc, ch.heading_path, ch.source_id "
        "FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    now = datetime.datetime.now(datetime.timezone.utc)
    results = []

    for cit_id, chunk_id, target_uri, tag, verified, verified_utc, heading, source_id in rows:
        v_dt = _parse_utc(verified_utc)
        age_days = None
        if v_dt:
            age_days = round((now - v_dt).total_seconds() / 86400, 1)

        results.append({
            "citation_id": cit_id,
            "chunk_id": chunk_id,
            "source_id": source_id,
            "target_uri": target_uri,
            "tag": tag,
            "verified": bool(verified),
            "verified_utc": verified_utc,
            "age_days": age_days,
            "heading": heading,
        })

    results.sort(key=lambda r: (r["age_days"] is None, -(r["age_days"] or 0)))
    return results


def overdue_citations(conn, max_age_days: int = 90) -> list[dict]:
    """Citations that were verified more than max_age_days ago, or never."""
    all_ages = citation_ages(conn)
    now = datetime.datetime.now(datetime.timezone.utc)

    overdue = []
    for c in all_ages:
        if c["age_days"] is None:
            overdue.append(c)
        elif c["age_days"] > max_age_days:
            overdue.append(c)

    overdue.sort(key=lambda r: (r["age_days"] is None, -(r["age_days"] or 0)))
    return overdue


def age_summary(conn) -> dict:
    """Aggregate citation verification age statistics."""
    all_ages = citation_ages(conn)

    if not all_ages:
        return {
            "total_citations": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "verification_rate": 0.0,
            "mean_age_days": 0.0,
            "median_age_days": 0.0,
            "max_age_days": 0.0,
            "overdue_90d": 0,
            "never_verified": 0,
        }

    verified = [c for c in all_ages if c["verified"]]
    unverified = [c for c in all_ages if not c["verified"]]
    never_verified = [c for c in all_ages if c["age_days"] is None]

    with_age = [c["age_days"] for c in all_ages if c["age_days"] is not None]
    with_age_sorted = sorted(with_age)

    mean_age = round(sum(with_age) / len(with_age), 1) if with_age else 0.0
    median_age = round(
        with_age_sorted[len(with_age_sorted) // 2], 1
    ) if with_age_sorted else 0.0
    max_age = round(max(with_age), 1) if with_age else 0.0

    overdue_90 = sum(1 for a in with_age if a > 90) + len(never_verified)

    return {
        "total_citations": len(all_ages),
        "verified_count": len(verified),
        "unverified_count": len(unverified),
        "verification_rate": round(
            len(verified) / len(all_ages), 4) if all_ages else 0.0,
        "mean_age_days": mean_age,
        "median_age_days": median_age,
        "max_age_days": max_age,
        "overdue_90d": overdue_90,
        "never_verified": len(never_verified),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        old_date = "2025-01-15T00:00:00Z"
        recent_date = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(days=10)
        recent_str = recent_date.strftime("%Y-%m-%dT%H:%M:%SZ")

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

        for i in range(3):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit1", "c0", "https://ref1.com", "ref", 1, recent_str),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit2", "c1", "https://ref2.com", "ref", 1, old_date),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit3", "c2", "https://ref3.com", "ref", 0, None),
        )

        conn.commit()

        # 1: ages returned for all citations
        ages = citation_ages(conn)
        assert len(ages) == 3
        checks += 1

        # 2: recent citation has small age
        recent = next(a for a in ages if a["citation_id"] == "cit1")
        assert recent["age_days"] is not None
        assert recent["age_days"] < 30
        checks += 1

        # 3: old citation has large age
        old = next(a for a in ages if a["citation_id"] == "cit2")
        assert old["age_days"] is not None
        assert old["age_days"] > 300
        checks += 1

        # 4: unverified citation has None age
        unverified = next(a for a in ages if a["citation_id"] == "cit3")
        assert unverified["age_days"] is None
        checks += 1

        # 5: verified flag is correct
        assert recent["verified"] is True
        assert unverified["verified"] is False
        checks += 1

        # 6: overdue returns old and unverified
        overdue = overdue_citations(conn, max_age_days=90)
        overdue_ids = [o["citation_id"] for o in overdue]
        assert "cit2" in overdue_ids
        assert "cit3" in overdue_ids
        checks += 1

        # 7: recent citation excluded from overdue
        assert "cit1" not in overdue_ids
        checks += 1

        # 8: overdue with very high threshold returns fewer
        overdue_high = overdue_citations(conn, max_age_days=9999)
        assert len(overdue_high) <= len(overdue)
        checks += 1

        # 9: summary has required keys
        summary = age_summary(conn)
        assert summary["total_citations"] == 3
        assert summary["verified_count"] == 2
        assert summary["unverified_count"] == 1
        checks += 1

        # 10: verification rate is correct
        assert abs(summary["verification_rate"] - 0.6667) < 0.01
        checks += 1

        # 11: never_verified count
        assert summary["never_verified"] == 1
        checks += 1

        # 12: mean age is positive
        assert summary["mean_age_days"] > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(ages)
        _ = json.dumps(overdue)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = citation_ages(conn2)
        assert empty == []
        empty_summary = age_summary(conn2)
        assert empty_summary["total_citations"] == 0
        checks += 1

    print(f"PASS citation_age selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation verification age: staleness of checks"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_age = sub.add_parser("age",
                           help="Per-citation verification age")
    p_age.add_argument("--db", default=DEFAULT_DB)
    p_age.add_argument("--json", action="store_true")

    p_over = sub.add_parser("overdue",
                            help="Citations overdue for re-verification")
    p_over.add_argument("--db", default=DEFAULT_DB)
    p_over.add_argument("--days", type=int, default=90)
    p_over.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Verification age statistics")
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

    if args.cmd == "age":
        results = citation_ages(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                age_str = f"{r['age_days']:7.1f}d" if r["age_days"] else "  never"
                v_str = "Y" if r["verified"] else "N"
                print(f"  {age_str}  [{v_str}]  "
                      f"{r['citation_id'][:12]:12s}  {r['target_uri']}")

    elif args.cmd == "overdue":
        results = overdue_citations(conn, args.days)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No citations overdue.")
            else:
                print(f"{len(results)} citations overdue "
                      f"(>{args.days} days or never verified):")
                for c in results:
                    age_str = (f"{c['age_days']:.0f}d"
                               if c["age_days"] else "never")
                    print(f"  {age_str:>8s}  {c['citation_id'][:12]:12s}  "
                          f"{c['target_uri']}")

    elif args.cmd == "summary":
        result = age_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citation Age: {result['total_citations']} citations, "
                  f"{result['verification_rate']:.1%} verified")
            print(f"  Mean age: {result['mean_age_days']:.1f}d  "
                  f"Median: {result['median_age_days']:.1f}d  "
                  f"Max: {result['max_age_days']:.1f}d")
            print(f"  Overdue (>90d): {result['overdue_90d']}  "
                  f"Never verified: {result['never_verified']}")

    conn.close()


if __name__ == "__main__":
    main()
