#!/usr/bin/env python3
"""Evidence coverage analysis: evidence_path population and patterns.

Analyses the artifacts.evidence_path column which had zero analytical
queries anywhere in the codebase, revealing evidence coverage rates,
path patterns, and how coverage varies by artifact type.

Usage:
    python tools/corpus/evidence_coverage.py coverage [--db PATH] [--json]
    python tools/corpus/evidence_coverage.py by-type [--db PATH] [--json]
    python tools/corpus/evidence_coverage.py patterns [--db PATH] [--json]
    python tools/corpus/evidence_coverage.py summary [--db PATH] [--json]
    python tools/corpus/evidence_coverage.py selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _path_pattern(p: str) -> str:
    if not p:
        return "unset"
    ext = os.path.splitext(p)[1].lower()
    if ext in (".py", ".js", ".ts", ".rs", ".go", ".java", ".rb", ".c",
               ".cpp", ".h", ".hpp"):
        return "source-code"
    if ext in (".md", ".txt", ".rst"):
        return "documentation"
    if ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"):
        return "config"
    if ext in (".sh", ".bash"):
        return "script"
    if ext == "":
        if "/" in p:
            return "directory"
        return "bare-name"
    return "other"


def evidence_coverage(conn) -> list[dict]:
    """Overall evidence_path coverage statistics."""
    rows = conn.execute(
        "SELECT artifact_type, "
        "count(*) AS total, "
        "sum(CASE WHEN evidence_path IS NOT NULL "
        "    AND evidence_path != '' THEN 1 ELSE 0 END) AS populated "
        "FROM artifacts GROUP BY artifact_type "
        "ORDER BY total DESC"
    ).fetchall()

    if not rows:
        return []

    results = [
        {
            "artifact_type": atype,
            "total": total,
            "with_evidence": populated,
            "coverage_rate": round(populated / total, 4) if total > 0 else 0.0,
        }
        for atype, total, populated in rows
    ]
    return results


def evidence_by_type(conn) -> list[dict]:
    """Evidence path presence cross-tabulated by artifact type and implementation."""
    rows = conn.execute(
        "SELECT artifact_type, implemented, "
        "count(*) AS total, "
        "sum(CASE WHEN evidence_path IS NOT NULL "
        "    AND evidence_path != '' THEN 1 ELSE 0 END) AS with_ev "
        "FROM artifacts GROUP BY artifact_type, implemented "
        "ORDER BY artifact_type, implemented"
    ).fetchall()

    if not rows:
        return []

    results = [
        {
            "artifact_type": atype,
            "implemented": bool(impl),
            "total": total,
            "with_evidence": with_ev,
            "coverage_rate": round(with_ev / total, 4) if total > 0 else 0.0,
        }
        for atype, impl, total, with_ev in rows
    ]
    return results


def evidence_patterns(conn) -> list[dict]:
    """Distribution of evidence_path patterns."""
    rows = conn.execute(
        "SELECT evidence_path FROM artifacts"
    ).fetchall()

    if not rows:
        return []

    pattern_counts: dict[str, int] = {}
    for (path,) in rows:
        pat = _path_pattern(path or "")
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

    total = sum(pattern_counts.values())
    results = [
        {
            "pattern": pat,
            "count": cnt,
            "share": round(cnt / total, 4) if total > 0 else 0.0,
        }
        for pat, cnt in sorted(
            pattern_counts.items(), key=lambda x: -x[1]
        )
    ]
    return results


def evidence_summary(conn) -> dict:
    """Aggregate evidence coverage statistics."""
    rows = conn.execute(
        "SELECT artifact_type, implemented, evidence_path "
        "FROM artifacts"
    ).fetchall()

    if not rows:
        return {
            "total_artifacts": 0,
            "with_evidence": 0,
            "coverage_rate": 0.0,
            "implemented_with_evidence": 0,
            "implemented_without_evidence": 0,
            "unimplemented_with_evidence": 0,
            "types_with_zero_coverage": 0,
            "distinct_paths": 0,
            "pattern_counts": {},
        }

    n = len(rows)
    with_ev = 0
    impl_with = 0
    impl_without = 0
    unimpl_with = 0
    type_ev: dict[str, list[bool]] = {}
    paths: set[str] = set()
    pattern_counts: dict[str, int] = {}

    for atype, impl, path in rows:
        has = bool(path)
        if has:
            with_ev += 1
            paths.add(path)
        pat = _path_pattern(path or "")
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

        if atype not in type_ev:
            type_ev[atype] = []
        type_ev[atype].append(has)

        if impl and has:
            impl_with += 1
        elif impl and not has:
            impl_without += 1
        elif not impl and has:
            unimpl_with += 1

    zero_cov = sum(
        1 for evs in type_ev.values() if not any(evs)
    )

    return {
        "total_artifacts": n,
        "with_evidence": with_ev,
        "coverage_rate": round(with_ev / n, 4) if n > 0 else 0.0,
        "implemented_with_evidence": impl_with,
        "implemented_without_evidence": impl_without,
        "unimplemented_with_evidence": unimpl_with,
        "types_with_zero_coverage": zero_cov,
        "distinct_paths": len(paths),
        "pattern_counts": pattern_counts,
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
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source s1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i, ordinal in enumerate(range(4)):
            cid = f"c{i+1}"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, "s1", ordinal, f"/h/{cid}", "prose", "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        artifacts = [
            ("a1", "c1", "library", "React", 1, "src/components/app.js"),
            ("a2", "c1", "api", "REST", 1, "docs/api.md"),
            ("a3", "c2", "library", "Flask", 0, None),
            ("a4", "c2", "command", "npm", 1, None),
            ("a5", "c3", "config", "eslint", 1, ".eslintrc.json"),
            ("a6", "c3", "pattern", "Observer", 0, "src/patterns.py"),
            ("a7", "c4", "library", "Django", 1, "setup.sh"),
            ("a8", "c4", "api", "GraphQL", 0, None),
        ]
        for aid, cid, atype, name, impl, evpath in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, implemented, "
                "evidence_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, None, None, impl, evpath),
            )

        conn.commit()

        # 1: coverage returns entries
        cov = evidence_coverage(conn)
        assert len(cov) > 0
        checks += 1

        # 2: library type: 2 of 3 have evidence (React, Django)
        lib = next(c for c in cov if c["artifact_type"] == "library")
        assert lib["total"] == 3
        assert lib["with_evidence"] == 2
        checks += 1

        # 3: api type: 1 of 2 has evidence (REST)
        api = next(c for c in cov if c["artifact_type"] == "api")
        assert api["with_evidence"] == 1
        checks += 1

        # 4: by-type returns entries
        bt = evidence_by_type(conn)
        assert len(bt) > 0
        checks += 1

        # 5: implemented libraries with evidence
        lib_impl = next(
            (b for b in bt if b["artifact_type"] == "library"
             and b["implemented"]), None
        )
        assert lib_impl is not None
        assert lib_impl["with_evidence"] >= 1
        checks += 1

        # 6: patterns returns entries
        pats = evidence_patterns(conn)
        assert len(pats) > 0
        checks += 1

        # 7: unset is the most common pattern (3 artifacts with no path)
        unset = next((p for p in pats if p["pattern"] == "unset"), None)
        assert unset is not None
        assert unset["count"] == 3
        checks += 1

        # 8: source-code pattern present (app.js, patterns.py)
        sc = next(
            (p for p in pats if p["pattern"] == "source-code"), None
        )
        assert sc is not None
        assert sc["count"] == 2
        checks += 1

        # 9: shares sum to approximately 1.0
        total_share = sum(p["share"] for p in pats)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 10: documentation pattern present (api.md)
        doc = next(
            (p for p in pats if p["pattern"] == "documentation"), None
        )
        assert doc is not None
        assert doc["count"] == 1
        checks += 1

        # 11: summary has correct totals
        summary = evidence_summary(conn)
        assert summary["total_artifacts"] == 8
        assert summary["with_evidence"] == 5
        checks += 1

        # 12: implementation-evidence cross counts
        assert summary["implemented_with_evidence"] == 4
        assert summary["implemented_without_evidence"] == 1
        assert summary["unimplemented_with_evidence"] == 1
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(cov)
        _ = json.dumps(bt)
        _ = json.dumps(pats)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = evidence_coverage(conn2)
        assert empty == []
        empty_summary = evidence_summary(conn2)
        assert empty_summary["total_artifacts"] == 0
        checks += 1

    print(f"PASS evidence_coverage selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence coverage analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_cov = sub.add_parser("coverage",
                           help="Evidence coverage per artifact type")
    p_cov.add_argument("--db", default=DEFAULT_DB)
    p_cov.add_argument("--json", action="store_true")

    p_type = sub.add_parser("by-type",
                            help="Evidence by type and implementation")
    p_type.add_argument("--db", default=DEFAULT_DB)
    p_type.add_argument("--json", action="store_true")

    p_pat = sub.add_parser("patterns",
                           help="Evidence path pattern distribution")
    p_pat.add_argument("--db", default=DEFAULT_DB)
    p_pat.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Evidence coverage statistics")
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

    if args.cmd == "coverage":
        results = evidence_coverage(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["coverage_rate"] * 40)
                print(f"  {r['artifact_type']:10s}  "
                      f"{r['with_evidence']}/{r['total']}  "
                      f"{r['coverage_rate']:5.1%}  {bar}")

    elif args.cmd == "by-type":
        results = evidence_by_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                impl_s = "impl" if r["implemented"] else "not "
                print(f"  {r['artifact_type']:10s}  {impl_s}  "
                      f"{r['with_evidence']}/{r['total']}  "
                      f"{r['coverage_rate']:5.1%}")

    elif args.cmd == "patterns":
        results = evidence_patterns(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['pattern']:15s}  {r['count']:3d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "summary":
        result = evidence_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total_artifacts']}  "
                  f"With evidence: {result['with_evidence']} "
                  f"({result['coverage_rate']:.1%})")
            print(f"  Impl+evidence: "
                  f"{result['implemented_with_evidence']}  "
                  f"Impl-no-evidence: "
                  f"{result['implemented_without_evidence']}  "
                  f"Unimpl+evidence: "
                  f"{result['unimplemented_with_evidence']}")
            print(f"  Zero-coverage types: "
                  f"{result['types_with_zero_coverage']}  "
                  f"Distinct paths: {result['distinct_paths']}")

    conn.close()


if __name__ == "__main__":
    main()
