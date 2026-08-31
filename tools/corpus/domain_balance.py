#!/usr/bin/env python3
"""Domain coverage balance: how evenly content is distributed across domains.

Computes Shannon entropy, Gini coefficient, and per-domain representation
metrics to reveal whether corpus content is concentrated in a few domains
or spread evenly.

Usage:
    python tools/corpus/domain_balance.py balance [--db PATH] [--json]
    python tools/corpus/domain_balance.py skew [--db PATH] [--json]
    python tools/corpus/domain_balance.py summary [--db PATH] [--json]
    python tools/corpus/domain_balance.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _gini(values: list[float]) -> float:
    """Gini coefficient for a list of non-negative values."""
    if not values or all(v == 0 for v in values):
        return 0.0
    n = len(values)
    sorted_vals = sorted(values)
    cumulative = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(sorted_vals))
    return round(cumulative / (n * sum(sorted_vals)), 4)


def _shannon_entropy(counts: list[int]) -> float:
    """Shannon entropy in bits for a frequency distribution."""
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def domain_balance(conn) -> list[dict]:
    """Per-domain chunk counts and share of total."""
    rows = conn.execute(
        "SELECT cd.domain, count(DISTINCT cd.chunk_id) as chunk_count "
        "FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY cd.domain "
        "ORDER BY chunk_count DESC"
    ).fetchall()

    if not rows:
        return []

    total = sum(r[1] for r in rows)
    n_domains = len(rows)
    uniform_share = 1.0 / n_domains if n_domains > 0 else 0.0

    results = []
    for domain, count in rows:
        share = count / total if total > 0 else 0.0
        deviation = share - uniform_share
        results.append({
            "domain": domain,
            "chunk_count": count,
            "share": round(share, 4),
            "uniform_share": round(uniform_share, 4),
            "deviation": round(deviation, 4),
        })

    return results


def skewed_domains(conn, threshold: float = 0.05) -> list[dict]:
    """Domains whose share deviates from uniform by more than threshold."""
    bal = domain_balance(conn)
    skewed = [d for d in bal if abs(d["deviation"]) > threshold]
    skewed.sort(key=lambda d: abs(d["deviation"]), reverse=True)
    return skewed


def balance_summary(conn) -> dict:
    """Aggregate domain coverage balance statistics."""
    bal = domain_balance(conn)

    if not bal:
        return {
            "total_domains": 0,
            "total_classified_chunks": 0,
            "entropy_bits": 0.0,
            "max_entropy_bits": 0.0,
            "normalised_entropy": 0.0,
            "gini_coefficient": 0.0,
            "most_covered": None,
            "least_covered": None,
            "over_represented": 0,
            "under_represented": 0,
        }

    counts = [d["chunk_count"] for d in bal]
    total_chunks = sum(counts)
    n_domains = len(bal)

    entropy = _shannon_entropy(counts)
    max_entropy = round(math.log2(n_domains), 4) if n_domains > 1 else 0.0
    norm_entropy = round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0

    gini = _gini([float(c) for c in counts])

    over = sum(1 for d in bal if d["deviation"] > 0.01)
    under = sum(1 for d in bal if d["deviation"] < -0.01)

    return {
        "total_domains": n_domains,
        "total_classified_chunks": total_chunks,
        "entropy_bits": entropy,
        "max_entropy_bits": max_entropy,
        "normalised_entropy": norm_entropy,
        "gini_coefficient": gini,
        "most_covered": bal[0]["domain"],
        "least_covered": bal[-1]["domain"],
        "over_represented": over,
        "under_represented": under,
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

        for i in range(6):
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
            "CREATE TABLE IF NOT EXISTS chunk_domains "
            "(chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )

        conn.execute("INSERT INTO chunk_domains VALUES ('c0', 'biology', 0.9, ?)", (now,))
        conn.execute("INSERT INTO chunk_domains VALUES ('c1', 'biology', 0.8, ?)", (now,))
        conn.execute("INSERT INTO chunk_domains VALUES ('c2', 'biology', 0.7, ?)", (now,))
        conn.execute("INSERT INTO chunk_domains VALUES ('c3', 'physics', 0.9, ?)", (now,))
        conn.execute("INSERT INTO chunk_domains VALUES ('c4', 'chemistry', 0.8, ?)", (now,))
        conn.execute("INSERT INTO chunk_domains VALUES ('c5', 'chemistry', 0.7, ?)", (now,))

        conn.commit()

        # 1: balance returns all domains
        bal = domain_balance(conn)
        domains = [d["domain"] for d in bal]
        assert len(bal) == 3
        assert "biology" in domains
        assert "physics" in domains
        assert "chemistry" in domains
        checks += 1

        # 2: sorted by chunk_count descending
        counts = [d["chunk_count"] for d in bal]
        assert counts == sorted(counts, reverse=True)
        checks += 1

        # 3: biology has highest count (3 chunks)
        bio = next(d for d in bal if d["domain"] == "biology")
        assert bio["chunk_count"] == 3
        checks += 1

        # 4: shares sum to 1.0
        total_share = sum(d["share"] for d in bal)
        assert abs(total_share - 1.0) < 0.001
        checks += 1

        # 5: deviation signs are correct
        assert bio["deviation"] > 0
        phys = next(d for d in bal if d["domain"] == "physics")
        assert phys["deviation"] < 0
        checks += 1

        # 6: skewed domains returns biology (over) and physics (under)
        skewed = skewed_domains(conn, threshold=0.05)
        skewed_names = [d["domain"] for d in skewed]
        assert "biology" in skewed_names
        assert "physics" in skewed_names
        checks += 1

        # 7: high threshold returns fewer
        skewed_high = skewed_domains(conn, threshold=0.5)
        assert len(skewed_high) <= len(skewed)
        checks += 1

        # 8: summary has required keys
        summary = balance_summary(conn)
        assert summary["total_domains"] == 3
        assert summary["total_classified_chunks"] == 6
        checks += 1

        # 9: entropy is positive and bounded
        assert summary["entropy_bits"] > 0
        assert summary["entropy_bits"] <= summary["max_entropy_bits"]
        checks += 1

        # 10: normalised entropy is between 0 and 1
        assert 0 < summary["normalised_entropy"] <= 1.0
        checks += 1

        # 11: gini coefficient is between 0 and 1
        assert 0 <= summary["gini_coefficient"] <= 1.0
        checks += 1

        # 12: most/least covered are correct
        assert summary["most_covered"] == "biology"
        assert summary["least_covered"] == "physics"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(bal)
        _ = json.dumps(skewed)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains "
            "(chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        empty = domain_balance(conn2)
        assert empty == []
        empty_summary = balance_summary(conn2)
        assert empty_summary["total_domains"] == 0
        checks += 1

    print(f"PASS domain_balance selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain coverage balance: distribution evenness"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_bal = sub.add_parser("balance",
                           help="Per-domain chunk counts and share")
    p_bal.add_argument("--db", default=DEFAULT_DB)
    p_bal.add_argument("--json", action="store_true")

    p_skew = sub.add_parser("skew",
                            help="Domains deviating from uniform")
    p_skew.add_argument("--db", default=DEFAULT_DB)
    p_skew.add_argument("--threshold", type=float, default=0.05)
    p_skew.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Balance statistics")
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

    if args.cmd == "balance":
        results = domain_balance(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                dev = f"{r['deviation']:+.3f}"
                print(f"  {r['chunk_count']:4d} chunks  {r['share']:.1%}  "
                      f"{dev}  {r['domain']}")

    elif args.cmd == "skew":
        results = skewed_domains(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("All domains within uniform threshold.")
            else:
                print(f"{len(results)} skewed domains "
                      f"(deviation > {args.threshold:.2f}):")
                for d in results:
                    direction = "over" if d["deviation"] > 0 else "under"
                    print(f"  {abs(d['deviation']):.3f} {direction:5s}  "
                          f"{d['chunk_count']:4d} chunks  {d['domain']}")

    elif args.cmd == "summary":
        result = balance_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Domain Balance: {result['total_domains']} domains, "
                  f"{result['total_classified_chunks']} classified chunks")
            print(f"  Entropy: {result['entropy_bits']:.2f} / "
                  f"{result['max_entropy_bits']:.2f} bits "
                  f"(normalised: {result['normalised_entropy']:.2%})")
            print(f"  Gini: {result['gini_coefficient']:.3f}")
            print(f"  Over-represented: {result['over_represented']}  "
                  f"Under-represented: {result['under_represented']}")
            if result["most_covered"]:
                print(f"  Most: {result['most_covered']}  "
                      f"Least: {result['least_covered']}")

    conn.close()


if __name__ == "__main__":
    main()
