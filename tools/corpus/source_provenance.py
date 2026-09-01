#!/usr/bin/env python3
"""Source provenance scorer: composite quality score per source.

Scores each source on a 0-1 composite scale derived from five signals:
license standing, liveness, chunk acceptance rate, citation density, and
temporal freshness.  Sources with low provenance scores carry content
that is less trustworthy or less well-maintained.

Usage:
    python tools/corpus/source_provenance.py score [--db PATH] [--json]
    python tools/corpus/source_provenance.py weak [--db PATH] [--threshold F] [--json]
    python tools/corpus/source_provenance.py summary [--db PATH] [--json]
    python tools/corpus/source_provenance.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

LICENSE_SCORES = {
    "vendor": 1.0,
    "index_only": 0.6,
    "link_only": 0.3,
    "blocked": 0.0,
}

LIVENESS_SCORES = {
    "live": 1.0,
    "stale": 0.5,
    "archived": 0.3,
    "dead": 0.0,
}

WEIGHTS = {
    "license": 0.25,
    "liveness": 0.20,
    "acceptance": 0.25,
    "citation_density": 0.15,
    "freshness": 0.15,
}


def _source_scores(conn) -> list[dict]:
    """Compute per-source provenance scores."""
    sources = conn.execute(
        "SELECT source_id, title, kind, license_verdict, liveness, "
        "published_utc, fetched_utc FROM sources"
    ).fetchall()

    if not sources:
        return []

    now = datetime.datetime.now(datetime.timezone.utc)
    results = []

    for src_id, title, kind, lic_verdict, liveness, pub_utc, fetch_utc in sources:
        license_score = LICENSE_SCORES.get(lic_verdict, 0.0)
        liveness_score = LIVENESS_SCORES.get(liveness, 0.0)

        total_chunks = conn.execute(
            "SELECT count(*) FROM chunks WHERE source_id = ?", (src_id,)
        ).fetchone()[0]

        accepted_chunks = conn.execute(
            "SELECT count(*) FROM chunks WHERE source_id = ? "
            "AND status = 'accepted'", (src_id,)
        ).fetchone()[0]

        acceptance_score = (
            accepted_chunks / total_chunks if total_chunks > 0 else 0.0
        )

        citation_count = conn.execute(
            "SELECT count(*) FROM citations WHERE chunk_id IN "
            "(SELECT chunk_id FROM chunks WHERE source_id = ?)", (src_id,)
        ).fetchone()[0]

        citation_density = min(citation_count / max(total_chunks, 1), 5.0) / 5.0

        freshness_score = 0.5
        ref_utc = fetch_utc or pub_utc
        if ref_utc:
            try:
                if ref_utc.endswith("Z"):
                    ref_utc = ref_utc[:-1] + "+00:00"
                ref_dt = datetime.datetime.fromisoformat(ref_utc)
                if ref_dt.tzinfo is None:
                    ref_dt = ref_dt.replace(tzinfo=datetime.timezone.utc)
                age_days = (now - ref_dt).total_seconds() / 86400
                half_life = 365.0
                freshness_score = math.exp(-0.693 * age_days / half_life)
            except (ValueError, TypeError):
                pass

        composite = (
            WEIGHTS["license"] * license_score
            + WEIGHTS["liveness"] * liveness_score
            + WEIGHTS["acceptance"] * acceptance_score
            + WEIGHTS["citation_density"] * citation_density
            + WEIGHTS["freshness"] * freshness_score
        )

        results.append({
            "source_id": src_id,
            "title": title,
            "kind": kind,
            "license_score": round(license_score, 4),
            "liveness_score": round(liveness_score, 4),
            "acceptance_score": round(acceptance_score, 4),
            "citation_density_score": round(citation_density, 4),
            "freshness_score": round(freshness_score, 4),
            "provenance_score": round(composite, 4),
            "total_chunks": total_chunks,
            "accepted_chunks": accepted_chunks,
        })

    results.sort(key=lambda r: r["provenance_score"], reverse=True)
    return results


def weak_sources(conn, threshold: float = 0.4) -> list[dict]:
    """Sources below the provenance threshold."""
    all_scores = _source_scores(conn)
    weak = [s for s in all_scores if s["provenance_score"] < threshold]
    weak.sort(key=lambda s: s["provenance_score"])
    return weak


def provenance_summary(conn) -> dict:
    """Aggregate provenance statistics."""
    all_scores = _source_scores(conn)

    if not all_scores:
        return {
            "total_sources": 0,
            "mean_provenance": 0.0,
            "median_provenance": 0.0,
            "min_provenance": 0.0,
            "max_provenance": 0.0,
            "weak_count": 0,
            "strong_count": 0,
            "by_kind": {},
        }

    scores = [s["provenance_score"] for s in all_scores]
    scores_sorted = sorted(scores)
    n = len(scores_sorted)

    weak_count = sum(1 for s in scores if s < 0.4)
    strong_count = sum(1 for s in scores if s >= 0.7)

    by_kind: dict[str, list[float]] = {}
    for s in all_scores:
        by_kind.setdefault(s["kind"], []).append(s["provenance_score"])

    kind_summary = {}
    for kind, vals in sorted(by_kind.items()):
        kind_summary[kind] = {
            "count": len(vals),
            "mean": round(sum(vals) / len(vals), 4),
        }

    return {
        "total_sources": n,
        "mean_provenance": round(sum(scores) / n, 4),
        "median_provenance": round(scores_sorted[n // 2], 4),
        "min_provenance": round(scores_sorted[0], 4),
        "max_provenance": round(scores_sorted[-1], 4),
        "weak_count": weak_count,
        "strong_count": strong_count,
        "by_kind": kind_summary,
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

        old_date = "2024-01-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Good Source",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s2", "https://b.com", "local_md", "Weak Source",
             "NONE", "blocked", "none", "Unknown",
             old_date, old_date, "", "", "dead", "sha_s2", 500, None),
        )

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s3", "https://c.com", "paper", "Mid Source",
             "MIT", "index_only", "inferred", "PubC",
             now, now, "", "", "stale", "sha_s3", 800, None),
        )

        for i, src in enumerate(["s1", "s1", "s1", "s2", "s3", "s3"]):
            status = "accepted" if src != "s2" else "rejected"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", src, i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 status, now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit1", "c0", "https://ref.com", "ref", 1, now),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, verified, verified_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("cit2", "c1", "https://ref2.com", "ref", 0, None),
        )

        conn.commit()

        # 1: scores are returned for all sources
        scores = _source_scores(conn)
        assert len(scores) == 3
        checks += 1

        # 2: sorted by provenance descending
        pscores = [s["provenance_score"] for s in scores]
        assert pscores == sorted(pscores, reverse=True)
        checks += 1

        # 3: good source (s1) scores higher than weak source (s2)
        s1_score = next(s for s in scores if s["source_id"] == "s1")
        s2_score = next(s for s in scores if s["source_id"] == "s2")
        assert s1_score["provenance_score"] > s2_score["provenance_score"]
        checks += 1

        # 4: license scores mapped correctly
        assert s1_score["license_score"] == 1.0
        assert s2_score["license_score"] == 0.0
        checks += 1

        # 5: liveness scores mapped correctly
        assert s1_score["liveness_score"] == 1.0
        assert s2_score["liveness_score"] == 0.0
        checks += 1

        # 6: acceptance score for s1 (3/3 accepted) = 1.0
        assert s1_score["acceptance_score"] == 1.0
        checks += 1

        # 7: acceptance score for s2 (0/1 accepted) = 0.0
        assert s2_score["acceptance_score"] == 0.0
        checks += 1

        # 8: weak sources returns s2 (blocked license, dead, old)
        weak = weak_sources(conn, threshold=0.4)
        weak_ids = [w["source_id"] for w in weak]
        assert "s2" in weak_ids
        checks += 1

        # 9: good source excluded from weak
        assert "s1" not in weak_ids
        checks += 1

        # 10: summary has required keys
        summary = provenance_summary(conn)
        assert summary["total_sources"] == 3
        assert "mean_provenance" in summary
        assert "by_kind" in summary
        checks += 1

        # 11: provenance scores bounded 0-1
        for s in scores:
            assert 0.0 <= s["provenance_score"] <= 1.0
        checks += 1

        # 12: summary weak + non-weak plausible
        assert summary["weak_count"] >= 1
        assert summary["strong_count"] >= 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(scores)
        _ = json.dumps(weak)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = _source_scores(conn2)
        assert empty == []
        empty_summary = provenance_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS source_provenance selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source provenance: composite quality score per source"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score",
                             help="Per-source provenance scores")
    p_score.add_argument("--db", default=DEFAULT_DB)
    p_score.add_argument("--json", action="store_true")

    p_weak = sub.add_parser("weak",
                            help="Sources below provenance threshold")
    p_weak.add_argument("--db", default=DEFAULT_DB)
    p_weak.add_argument("--threshold", type=float, default=0.4)
    p_weak.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Provenance statistics")
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

    if args.cmd == "score":
        results = _source_scores(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['provenance_score']:.3f}  {r['kind']:8s}  "
                      f"{r['source_id'][:12]:12s}  {r['title']}")

    elif args.cmd == "weak":
        results = weak_sources(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No sources below threshold.")
            else:
                print(f"{len(results)} weak sources "
                      f"(below {args.threshold}):")
                for s in results:
                    print(f"  {s['provenance_score']:.3f}  "
                          f"{s['source_id'][:12]:12s}  {s['title']}")

    elif args.cmd == "summary":
        result = provenance_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Source Provenance: {result['mean_provenance']:.3f} mean "
                  f"({result['total_sources']} sources)")
            print(f"  Range: {result['min_provenance']:.3f} - "
                  f"{result['max_provenance']:.3f}  "
                  f"Median: {result['median_provenance']:.3f}")
            print(f"  Weak (<0.4): {result['weak_count']}  "
                  f"Strong (>=0.7): {result['strong_count']}")
            if result["by_kind"]:
                for kind, stats in result["by_kind"].items():
                    print(f"    {kind}: {stats['count']} sources, "
                          f"mean {stats['mean']:.3f}")

    conn.close()


if __name__ == "__main__":
    main()
