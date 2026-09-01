#!/usr/bin/env python3
"""Corpus quality scoring: per-chunk and per-source quality metrics.

Computes quality scores from measurable signals: word count adequacy,
citation density, artifact extraction rate, heading structure, and
contradiction involvement.  Useful for prioritising quarantined chunks
for promotion and identifying weak sources.

Usage:
    python tools/corpus/quality.py score [--db PATH] [--status STATUS]
        [--source SOURCE_ID] [--min-score N] [--max-score N] [--n N] [--json]
    python tools/corpus/quality.py sources [--db PATH] [--n N] [--json]
    python tools/corpus/quality.py distribution [--db PATH] [--json]
    python tools/corpus/quality.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

IDEAL_WORD_MIN = 50
IDEAL_WORD_MAX = 500


def _chunk_quality(word_count: int, citation_count: int, has_heading: bool,
                   artifact_count: int, contradiction_count: int,
                   kind: str) -> dict:
    signals = {}

    if word_count < 10:
        signals["word_count"] = 0.0
    elif word_count < IDEAL_WORD_MIN:
        signals["word_count"] = 0.4
    elif word_count <= IDEAL_WORD_MAX:
        signals["word_count"] = 1.0
    elif word_count <= 1000:
        signals["word_count"] = 0.7
    else:
        signals["word_count"] = 0.4

    signals["has_heading"] = 1.0 if has_heading else 0.3

    if kind in ("claim", "prose"):
        if citation_count >= 2:
            signals["citations"] = 1.0
        elif citation_count == 1:
            signals["citations"] = 0.7
        else:
            signals["citations"] = 0.2
    else:
        signals["citations"] = 0.8 if citation_count > 0 else 0.5

    signals["artifacts"] = min(1.0, 0.5 + artifact_count * 0.25)

    if contradiction_count > 0:
        signals["contradictions"] = max(0.0, 0.5 - contradiction_count * 0.2)
    else:
        signals["contradictions"] = 1.0

    weights = {
        "word_count": 0.25,
        "has_heading": 0.10,
        "citations": 0.30,
        "artifacts": 0.15,
        "contradictions": 0.20,
    }

    score = sum(signals[k] * weights[k] for k in weights)
    return {"score": round(score, 3), "signals": signals}


def score_chunks(conn, status: str | None = None,
                 source_id: str | None = None,
                 min_score: float | None = None,
                 max_score: float | None = None,
                 n: int = 20) -> list[dict]:
    where_parts: list[str] = []
    params: list = []

    if status:
        where_parts.append("c.status = ?")
        params.append(status)
    if source_id:
        where_parts.append("c.source_id = ?")
        params.append(source_id)

    where = " AND ".join(where_parts) if where_parts else "1=1"

    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, c.status, c.word_count, "
        "       c.citation_count, c.heading_path, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        f"WHERE {where}",
        params,
    ).fetchall()

    chunk_ids = [r[0] for r in rows]
    art_counts: dict[str, int] = {}
    contra_counts: dict[str, int] = {}

    if chunk_ids:
        for cid in chunk_ids:
            art_counts[cid] = conn.execute(
                "SELECT COUNT(*) FROM artifacts WHERE chunk_id = ?", (cid,)
            ).fetchone()[0]

            contra_counts[cid] = conn.execute(
                "SELECT COUNT(*) FROM claim_edges "
                "WHERE edge_type = 'contradicts' AND resolution IS NULL "
                "  AND (source_chunk = ? OR target_chunk = ?)",
                (cid, cid),
            ).fetchone()[0]

    results = []
    for r in rows:
        cid = r[0]
        has_heading = bool(r[6] and r[6].strip() and r[6].strip() != "/")
        q = _chunk_quality(
            word_count=r[4],
            citation_count=r[5],
            has_heading=has_heading,
            artifact_count=art_counts.get(cid, 0),
            contradiction_count=contra_counts.get(cid, 0),
            kind=r[2],
        )
        if min_score is not None and q["score"] < min_score:
            continue
        if max_score is not None and q["score"] > max_score:
            continue

        results.append({
            "chunk_id": cid,
            "source_id": r[1],
            "kind": r[2],
            "status": r[3],
            "word_count": r[4],
            "source_title": r[7],
            "quality_score": q["score"],
            "signals": q["signals"],
        })

    results.sort(key=lambda x: x["quality_score"], reverse=True)
    return results[:n]


def score_sources(conn, n: int = 20) -> list[dict]:
    sources = conn.execute(
        "SELECT s.source_id, s.title, s.kind, s.liveness, "
        "       COUNT(c.chunk_id), "
        "       SUM(c.word_count), "
        "       AVG(c.word_count), "
        "       SUM(CASE WHEN c.status = 'accepted' THEN 1 ELSE 0 END), "
        "       SUM(c.citation_count) "
        "FROM sources s "
        "LEFT JOIN chunks c ON s.source_id = c.source_id "
        "GROUP BY s.source_id "
        "ORDER BY COUNT(c.chunk_id) DESC",
    ).fetchall()

    results = []
    for row in sources:
        sid = row[0]
        chunk_count = row[4] or 0
        total_words = row[5] or 0
        avg_words = row[6] or 0
        accepted = row[7] or 0
        total_cits = row[8] or 0

        art_count = conn.execute(
            "SELECT COUNT(*) FROM artifacts a "
            "JOIN chunks c ON a.chunk_id = c.chunk_id "
            "WHERE c.source_id = ?", (sid,)
        ).fetchone()[0]

        contra_count = conn.execute(
            "SELECT COUNT(*) FROM claim_edges e "
            "JOIN chunks c ON (e.source_chunk = c.chunk_id OR e.target_chunk = c.chunk_id) "
            "WHERE c.source_id = ? AND e.edge_type = 'contradicts' AND e.resolution IS NULL",
            (sid,),
        ).fetchone()[0]

        acceptance_rate = accepted / chunk_count if chunk_count > 0 else 0.0
        cit_density = total_cits / chunk_count if chunk_count > 0 else 0.0
        art_density = art_count / chunk_count if chunk_count > 0 else 0.0

        score_parts = []
        score_parts.append(min(1.0, acceptance_rate) * 0.30)
        score_parts.append(min(1.0, cit_density / 2.0) * 0.25)
        score_parts.append(min(1.0, art_density) * 0.15)
        score_parts.append((1.0 if contra_count == 0 else max(0.0, 0.5 - contra_count * 0.1)) * 0.15)
        word_score = 1.0 if IDEAL_WORD_MIN <= avg_words <= IDEAL_WORD_MAX else 0.5
        score_parts.append(word_score * 0.15)

        total_score = round(sum(score_parts), 3)

        results.append({
            "source_id": sid,
            "title": row[1],
            "kind": row[2],
            "liveness": row[3],
            "chunk_count": chunk_count,
            "total_words": total_words,
            "accepted_chunks": accepted,
            "acceptance_rate": round(acceptance_rate, 3),
            "citation_density": round(cit_density, 3),
            "artifact_density": round(art_density, 3),
            "open_contradictions": contra_count,
            "quality_score": total_score,
        })

    results.sort(key=lambda x: x["quality_score"], reverse=True)
    return results[:n]


def distribution(conn) -> dict:
    all_chunks = conn.execute(
        "SELECT c.chunk_id, c.kind, c.status, c.word_count, "
        "       c.citation_count, c.heading_path "
        "FROM chunks c"
    ).fetchall()

    art_map: dict[str, int] = {}
    for row in conn.execute(
        "SELECT chunk_id, COUNT(*) FROM artifacts GROUP BY chunk_id"
    ).fetchall():
        art_map[row[0]] = row[1]

    contra_map: dict[str, int] = {}
    for row in conn.execute(
        "SELECT chunk_id, COUNT(*) FROM ("
        "  SELECT source_chunk AS chunk_id FROM claim_edges "
        "    WHERE edge_type = 'contradicts' AND resolution IS NULL "
        "  UNION ALL "
        "  SELECT target_chunk AS chunk_id FROM claim_edges "
        "    WHERE edge_type = 'contradicts' AND resolution IS NULL"
        ") GROUP BY chunk_id"
    ).fetchall():
        contra_map[row[0]] = row[1]

    scores = []
    for row in all_chunks:
        cid = row[0]
        has_heading = bool(row[5] and row[5].strip() and row[5].strip() != "/")
        q = _chunk_quality(
            word_count=row[3],
            citation_count=row[4],
            has_heading=has_heading,
            artifact_count=art_map.get(cid, 0),
            contradiction_count=contra_map.get(cid, 0),
            kind=row[1],
        )
        scores.append(q["score"])

    if not scores:
        return {"total": 0, "buckets": {}, "mean": 0, "median": 0,
                "min": 0, "max": 0}

    scores.sort()
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
               "0.6-0.8": 0, "0.8-1.0": 0}
    for s in scores:
        if s < 0.2:
            buckets["0.0-0.2"] += 1
        elif s < 0.4:
            buckets["0.2-0.4"] += 1
        elif s < 0.6:
            buckets["0.4-0.6"] += 1
        elif s < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1

    n = len(scores)
    median = scores[n // 2] if n % 2 == 1 else (scores[n // 2 - 1] + scores[n // 2]) / 2

    by_status: dict[str, list[float]] = {}
    for row in all_chunks:
        cid = row[0]
        has_heading = bool(row[5] and row[5].strip() and row[5].strip() != "/")
        q = _chunk_quality(
            word_count=row[3],
            citation_count=row[4],
            has_heading=has_heading,
            artifact_count=art_map.get(cid, 0),
            contradiction_count=contra_map.get(cid, 0),
            kind=row[1],
        )
        by_status.setdefault(row[2], []).append(q["score"])

    status_summary = {}
    for st, vals in sorted(by_status.items()):
        vals.sort()
        sn = len(vals)
        smed = vals[sn // 2] if sn % 2 == 1 else (vals[sn // 2 - 1] + vals[sn // 2]) / 2
        status_summary[st] = {
            "count": sn,
            "mean": round(sum(vals) / sn, 3),
            "median": round(smed, 3),
            "min": round(vals[0], 3),
            "max": round(vals[-1], 3),
        }

    return {
        "total": n,
        "mean": round(sum(scores) / n, 3),
        "median": round(median, 3),
        "min": round(scores[0], 3),
        "max": round(scores[-1], 3),
        "buckets": buckets,
        "by_status": status_summary,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    import os
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Source A",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Test Source B",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Introduction / Background", "claim", None,
             "This is a well-structured claim with adequate length for testing. " * 5,
             "raw", 50, _sha256("c1"), 0, 2, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "/", "prose", None,
             "short",
             "raw", 5, _sha256("c2"), 0, 0, "quarantined", "too short", now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src2", 0, "Methods / Analysis", "claim", None,
             "A moderate length claim chunk with some content. " * 8,
             "raw", 80, _sha256("c3"), 0, 1, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src2", 1, "Results", "code", None,
             "import foo\nbar = foo.baz()\n" * 10,
             "raw", 40, _sha256("c4"), 0, 0, "quarantined", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 2, "Discussion", "claim", None,
             "A claim involved in a contradiction. " * 12,
             "raw", 84, _sha256("c5"), 0, 1, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "https://example.com/a", None, None, None, 1, now),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit2", "c1", "https://example.com/b", None, None, None, 1, now),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit3", "c3", "https://example.com/c", None, None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit4", "c5", "https://example.com/d", None, None, None, 1, now),
        )

        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("art1", "c1", "library", "numpy", "1.26", None, 1, "tools/x.py:10"),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("art2", "c1", "api", "pandas.DataFrame", None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("art3", "c3", "library", "sqlite3", None, None, 1, "tools/y.py:5"),
        )

        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c5", "c3", "contradicts", "negation", 0.85, now, None, None),
        )
        conn.commit()

        # Check 1: score_chunks returns results
        scored = score_chunks(conn)
        assert len(scored) == 5, f"expected 5 chunks, got {len(scored)}"
        checks += 1

        # Check 2: results are sorted by score descending
        scores_list = [r["quality_score"] for r in scored]
        assert scores_list == sorted(scores_list, reverse=True), "not sorted desc"
        checks += 1

        # Check 3: well-cited chunk with artifacts scores higher than uncited short chunk
        c1_score = next(r for r in scored if r["chunk_id"] == "c1")["quality_score"]
        c2_score = next(r for r in scored if r["chunk_id"] == "c2")["quality_score"]
        assert c1_score > c2_score, f"c1 ({c1_score}) should outscore c2 ({c2_score})"
        checks += 1

        # Check 4: contradiction chunk scores lower than clean chunk with same citations
        c5_score = next(r for r in scored if r["chunk_id"] == "c5")["quality_score"]
        assert c1_score > c5_score, f"c1 ({c1_score}) should outscore contradicted c5 ({c5_score})"
        checks += 1

        # Check 5: status filter works
        accepted_only = score_chunks(conn, status="accepted")
        assert all(r["status"] == "accepted" for r in accepted_only)
        checks += 1

        # Check 6: source filter works
        src1_only = score_chunks(conn, source_id="src1")
        assert all(r["source_id"] == "src1" for r in src1_only)
        checks += 1

        # Check 7: min_score filter works
        high_only = score_chunks(conn, min_score=0.6)
        assert all(r["quality_score"] >= 0.6 for r in high_only)
        checks += 1

        # Check 8: max_score filter works
        low_only = score_chunks(conn, max_score=0.4)
        assert all(r["quality_score"] <= 0.4 for r in low_only)
        checks += 1

        # Check 9: n limit works
        limited = score_chunks(conn, n=2)
        assert len(limited) <= 2
        checks += 1

        # Check 10: score_sources returns results
        src_scores = score_sources(conn)
        assert len(src_scores) == 2, f"expected 2 sources, got {len(src_scores)}"
        checks += 1

        # Check 11: source scores are sorted descending
        src_score_list = [r["quality_score"] for r in src_scores]
        assert src_score_list == sorted(src_score_list, reverse=True)
        checks += 1

        # Check 12: source with better acceptance rate scores higher
        s1 = next(r for r in src_scores if r["source_id"] == "src1")
        s2 = next(r for r in src_scores if r["source_id"] == "src2")
        assert s1["acceptance_rate"] > 0
        assert s2["acceptance_rate"] > 0
        checks += 1

        # Check 13: distribution returns expected structure
        dist = distribution(conn)
        assert dist["total"] == 5
        assert sum(dist["buckets"].values()) == 5
        checks += 1

        # Check 14: distribution has by_status breakdown
        assert "by_status" in dist
        assert "accepted" in dist["by_status"]
        assert "quarantined" in dist["by_status"]
        checks += 1

        # Check 15: JSON serialization works
        json_out = json.dumps(scored, indent=2)
        parsed = json.loads(json_out)
        assert len(parsed) == 5
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert score_chunks(empty_conn) == []
        assert score_sources(empty_conn) == []
        empty_dist = distribution(empty_conn)
        assert empty_dist["total"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS quality selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus quality scoring",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score", help="Score individual chunks")
    p_score.add_argument("--db", default=str(DEFAULT_DB))
    p_score.add_argument("--status")
    p_score.add_argument("--source", dest="source_id")
    p_score.add_argument("--min-score", type=float)
    p_score.add_argument("--max-score", type=float)
    p_score.add_argument("--n", type=int, default=20)
    p_score.add_argument("--json", action="store_true")

    p_src = sub.add_parser("sources", help="Score sources by aggregate quality")
    p_src.add_argument("--db", default=str(DEFAULT_DB))
    p_src.add_argument("--n", type=int, default=20)
    p_src.add_argument("--json", action="store_true")

    p_dist = sub.add_parser("distribution", help="Quality score distribution")
    p_dist.add_argument("--db", default=str(DEFAULT_DB))
    p_dist.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "score":
        results = score_chunks(conn, status=args.status,
                               source_id=args.source_id,
                               min_score=args.min_score,
                               max_score=args.max_score,
                               n=args.n)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['quality_score']:.3f}  {r['chunk_id'][:12]}  "
                      f"{r['kind']:6s}  {r['status']:12s}  "
                      f"w={r['word_count']:4d}  {r['source_title'][:40]}")

    elif args.cmd == "sources":
        results = score_sources(conn, n=args.n)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['quality_score']:.3f}  {r['source_id'][:12]}  "
                      f"chunks={r['chunk_count']:3d}  "
                      f"accept={r['acceptance_rate']:.0%}  "
                      f"cit={r['citation_density']:.1f}  "
                      f"{r['title'][:40]}")

    elif args.cmd == "distribution":
        dist = distribution(conn)
        if args.json:
            print(json.dumps(dist, indent=2))
        else:
            print(f"Total chunks: {dist['total']}")
            print(f"Mean: {dist['mean']:.3f}  Median: {dist['median']:.3f}  "
                  f"Min: {dist['min']:.3f}  Max: {dist['max']:.3f}")
            print("Buckets:")
            for bucket, count in dist["buckets"].items():
                pct = count / dist["total"] * 100 if dist["total"] else 0
                bar = "#" * int(pct / 2)
                print(f"  {bucket}: {count:5d} ({pct:5.1f}%) {bar}")
            if "by_status" in dist:
                print("By status:")
                for st, info in dist["by_status"].items():
                    print(f"  {st:12s}: n={info['count']:4d}  "
                          f"mean={info['mean']:.3f}  median={info['median']:.3f}")

    conn.close()


if __name__ == "__main__":
    main()
