#!/usr/bin/env python3
"""Simhash distribution: hash-space density and collision patterns.

Analyses the distribution of simhash values across accepted chunks,
measuring bit-entropy, collision rates, and hamming distance
clustering to detect potential dedup blind spots.

Usage:
    python tools/corpus/simhash_distribution.py entropy [--db PATH] [--json]
    python tools/corpus/simhash_distribution.py collisions [--db PATH] [--json]
    python tools/corpus/simhash_distribution.py bit-balance [--db PATH] [--json]
    python tools/corpus/simhash_distribution.py summary [--db PATH] [--json]
    python tools/corpus/simhash_distribution.py selftest
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


def _popcount(n: int) -> int:
    """Count set bits in a non-negative integer."""
    return bin(n).count("1")


def bit_entropy(conn) -> list[dict]:
    """Per-bit set-rate across all accepted simhashes.

    For a well-distributed hash each bit should be set ~50% of the time.
    Significant deviation suggests the hash function or input is biased.
    """
    rows = conn.execute(
        "SELECT simhash FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    hashes = [r[0] for r in rows]
    n = len(hashes)

    max_bits = max(h.bit_length() for h in hashes) if any(h > 0 for h in hashes) else 64
    num_bits = max(max_bits, 64)

    results = []
    for bit in range(num_bits):
        mask = 1 << bit
        set_count = sum(1 for h in hashes if h & mask)
        rate = round(set_count / n, 4)
        results.append({
            "bit": bit,
            "set_count": set_count,
            "set_rate": rate,
            "deviation": round(abs(rate - 0.5), 4),
        })

    results.sort(key=lambda r: r["deviation"], reverse=True)
    return results


def hash_collisions(conn) -> list[dict]:
    """Groups of chunks sharing the same simhash value.

    Exact simhash collisions are expected for near-duplicates but
    a high collision rate on distinct content signals hash weakness.
    """
    rows = conn.execute(
        "SELECT simhash, count(*) as cnt, "
        "group_concat(chunk_id, ',') as chunk_ids "
        "FROM chunks WHERE status = 'accepted' "
        "GROUP BY simhash HAVING cnt > 1 "
        "ORDER BY cnt DESC"
    ).fetchall()

    if not rows:
        return []

    results = []
    for simhash, cnt, chunk_ids in rows:
        results.append({
            "simhash": simhash,
            "count": cnt,
            "chunk_ids": chunk_ids.split(","),
        })

    return results


def bit_balance(conn) -> list[dict]:
    """Distribution of popcount (number of set bits) across simhashes.

    For a 64-bit hash the popcount should cluster around 32.
    A skewed distribution suggests systematic bias in the hash inputs.
    """
    rows = conn.execute(
        "SELECT simhash FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    hashes = [r[0] for r in rows]
    buckets: dict[int, int] = {}
    for h in hashes:
        pc = _popcount(h)
        buckets[pc] = buckets.get(pc, 0) + 1

    n = len(hashes)
    return [
        {
            "popcount": pc,
            "count": buckets[pc],
            "share": round(buckets[pc] / n, 4),
        }
        for pc in sorted(buckets)
    ]


def simhash_summary(conn) -> dict:
    """Aggregate simhash distribution statistics."""
    rows = conn.execute(
        "SELECT simhash FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_chunks": 0,
            "unique_hashes": 0,
            "collision_groups": 0,
            "colliding_chunks": 0,
            "collision_rate": 0.0,
            "mean_popcount": 0.0,
            "median_popcount": 0,
            "max_bit_deviation": 0.0,
        }

    hashes = [r[0] for r in rows]
    n = len(hashes)

    unique = len(set(hashes))
    colliding_chunks = n - unique
    from collections import Counter
    freq = Counter(hashes)
    collision_groups = sum(1 for v in freq.values() if v > 1)

    popcounts = sorted(_popcount(h) for h in hashes)
    mean_pc = sum(popcounts) / n
    median_pc = popcounts[n // 2]

    num_bits = 64
    bit_rates = []
    for bit in range(num_bits):
        mask = 1 << bit
        rate = sum(1 for h in hashes if h & mask) / n
        bit_rates.append(abs(rate - 0.5))
    max_dev = max(bit_rates)

    return {
        "total_chunks": n,
        "unique_hashes": unique,
        "collision_groups": collision_groups,
        "colliding_chunks": colliding_chunks,
        "collision_rate": round(colliding_chunks / n, 4) if n > 0 else 0.0,
        "mean_popcount": round(mean_pc, 1),
        "median_popcount": median_pc,
        "max_bit_deviation": round(max_dev, 4),
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

        chunks = [
            ("c0", 0x5A5A5A5A5A5A5A5A),
            ("c1", 0x2525252525252525),
            ("c2", 0x5A5A5A5A5A5A5A5A),
            ("c3", 0x7FFFFFFF00000000),
            ("c4", 0x000000007FFFFFFF),
            ("c5", 0x7F007F007F007F00),
            ("c6", 0),
        ]
        for i, (cid, sh) in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 50, f"n_{cid}",
                 sh, "accepted", now),
            )

        conn.commit()

        # 1: bit_entropy returns 64 entries
        ent = bit_entropy(conn)
        assert len(ent) == 64
        checks += 1

        # 2: each bit rate is between 0 and 1
        for e in ent:
            assert 0.0 <= e["set_rate"] <= 1.0
        checks += 1

        # 3: deviation is non-negative
        for e in ent:
            assert e["deviation"] >= 0.0
        checks += 1

        # 4: sorted by deviation descending
        devs = [e["deviation"] for e in ent]
        assert devs == sorted(devs, reverse=True)
        checks += 1

        # 5: collisions found (c0 and c2 share simhash)
        coll = hash_collisions(conn)
        assert len(coll) >= 1
        checks += 1

        # 6: collision group has c0 and c2
        found = False
        for g in coll:
            if "c0" in g["chunk_ids"] and "c2" in g["chunk_ids"]:
                found = True
                break
        assert found
        checks += 1

        # 7: collision group count is 2 for that pair
        pair = next(g for g in coll if "c0" in g["chunk_ids"])
        assert pair["count"] == 2
        checks += 1

        # 8: bit_balance returns entries
        bal = bit_balance(conn)
        assert len(bal) > 0
        checks += 1

        # 9: shares sum to approximately 1.0
        total_share = sum(b["share"] for b in bal)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 10: c6 (all zeros) has popcount 0 represented
        zero_entry = [b for b in bal if b["popcount"] == 0]
        assert len(zero_entry) == 1
        assert zero_entry[0]["count"] >= 1
        checks += 1

        # 11: summary has correct total
        summary = simhash_summary(conn)
        assert summary["total_chunks"] == 7
        checks += 1

        # 12: unique hashes < total (c0 and c2 collide)
        assert summary["unique_hashes"] == 6
        assert summary["collision_groups"] == 1
        assert summary["colliding_chunks"] == 1
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(ent)
        _ = json.dumps(coll)
        _ = json.dumps(bal)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = bit_entropy(conn2)
        assert empty == []
        empty_summary = simhash_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS simhash_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simhash distribution: hash-space density and collision patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ent = sub.add_parser("entropy",
                           help="Per-bit set-rate analysis")
    p_ent.add_argument("--db", default=DEFAULT_DB)
    p_ent.add_argument("--json", action="store_true")

    p_coll = sub.add_parser("collisions",
                            help="Simhash collision groups")
    p_coll.add_argument("--db", default=DEFAULT_DB)
    p_coll.add_argument("--json", action="store_true")

    p_bal = sub.add_parser("bit-balance",
                           help="Popcount distribution")
    p_bal.add_argument("--db", default=DEFAULT_DB)
    p_bal.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Simhash distribution statistics")
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

    if args.cmd == "entropy":
        results = bit_entropy(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No accepted chunks found.")
            else:
                print("Per-bit set rates (sorted by deviation):")
                for r in results[:20]:
                    bar = "#" * int(r["set_rate"] * 40)
                    print(f"  bit {r['bit']:2d}  {r['set_rate']:5.1%}  "
                          f"dev={r['deviation']:.4f}  {bar}")
                if len(results) > 20:
                    print(f"  ... {len(results) - 20} more bits")

    elif args.cmd == "collisions":
        results = hash_collisions(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No simhash collisions found.")
            else:
                print(f"{len(results)} collision groups:")
                for r in results:
                    ids = ", ".join(r["chunk_ids"][:5])
                    extra = f" +{len(r['chunk_ids']) - 5}" if len(r["chunk_ids"]) > 5 else ""
                    print(f"  n={r['count']:3d}  hash={r['simhash']}  "
                          f"{ids}{extra}")

    elif args.cmd == "bit-balance":
        results = bit_balance(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No accepted chunks found.")
            else:
                print("Popcount distribution:")
                for r in results:
                    bar = "#" * int(r["share"] * 40)
                    print(f"  {r['popcount']:3d} bits set  "
                          f"{r['count']:4d}  {r['share']:5.1%}  {bar}")

    elif args.cmd == "summary":
        result = simhash_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Simhash: {result['total_chunks']} chunks, "
                  f"{result['unique_hashes']} unique hashes")
            print(f"  Collisions: {result['collision_groups']} groups, "
                  f"{result['colliding_chunks']} chunks "
                  f"({result['collision_rate']:.1%})")
            print(f"  Popcount: mean={result['mean_popcount']:.1f}  "
                  f"median={result['median_popcount']}")
            print(f"  Max bit deviation: {result['max_bit_deviation']:.4f}")

    conn.close()


if __name__ == "__main__":
    main()
