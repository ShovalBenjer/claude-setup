#!/usr/bin/env python3
"""Corpus export: serialize the corpus or filtered subsets to JSON/JSONL.

Exports full section 7.2 records with source provenance, citations,
contradictions, artifacts, staleness, trust, and tags. Supports
filtering by status, kind, source kind, tag, and date range.
Produces structured output suitable for dashboards, external
analysis, or consumption by other tools.

Usage:
    python tools/corpus/export.py full [--db PATH] [--format json|jsonl] [--status STATUS] [--kind KIND] [--source-kind KIND] [--tag TAG] [--since DATE] [--before DATE] [--out FILE]
    python tools/corpus/export.py defects [--db PATH] [--format json|jsonl]
    python tools/corpus/export.py artifacts [--db PATH] [--implemented] [--format json|jsonl]
    python tools/corpus/export.py sources [--db PATH] [--format json|jsonl]
    python tools/corpus/export.py summary [--db PATH] [--json]
    python tools/corpus/export.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    _sha256,
    connect,
    init_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_utc(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            continue
    return None


def _staleness_verdict(source_row):
    now = _now_utc()
    reasons = []
    age_days = None

    mtime = _parse_utc(source_row.get("upstream_mtime"))
    if mtime:
        age_days = (now - mtime).days
        if source_row.get("liveness") == "archived":
            reasons.append("archived")
        elif age_days > 548:
            reasons.append("stale")

    fetched = _parse_utc(source_row.get("fetched_utc"))
    if fetched and (now - fetched).days > 90:
        reasons.append("unverified")

    if not reasons:
        verdict = "fresh"
    elif "archived" in reasons:
        verdict = "archived"
    elif "stale" in reasons:
        verdict = "stale"
    elif "unverified" in reasons:
        verdict = "unverified"
    else:
        verdict = "fresh"

    return {"verdict": verdict, "age_days": age_days, "reasons": reasons}


def _trust_for(license_verdict):
    return "trusted" if license_verdict == "vendor" else "untrusted"


def export_full(conn, status_filter=None, kind_filter=None,
                source_kind=None, tag_filter=None,
                since=None, before=None):
    """Export all chunks as section 7.2 records with optional filters."""
    sql = "SELECT c.* FROM chunks c"
    joins = []
    where = ["1=1"]
    params = []

    if source_kind:
        joins.append("JOIN sources s ON s.source_id = c.source_id")
        kinds = [k.strip() for k in source_kind.split(",")]
        placeholders = ",".join("?" * len(kinds))
        where.append(f"s.kind IN ({placeholders})")
        params.extend(kinds)

    if tag_filter:
        joins.append("JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id")
        tags = [t.strip() for t in tag_filter.split(",")]
        placeholders = ",".join("?" * len(tags))
        where.append(f"ct.tag IN ({placeholders})")
        params.extend(tags)

    if status_filter:
        where.append("c.status = ?")
        params.append(status_filter)
    if kind_filter:
        kinds = [k.strip() for k in kind_filter.split(",")]
        placeholders = ",".join("?" * len(kinds))
        where.append(f"c.kind IN ({placeholders})")
        params.extend(kinds)

    if since:
        where.append("c.ingested_utc >= ?")
        params.append(since)
    if before:
        where.append("c.ingested_utc < ?")
        params.append(before)

    sql = sql + " " + " ".join(joins) + " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.source_id, c.ordinal"
    chunks = conn.execute(sql, params).fetchall()

    source_cache = {}
    records = []

    for chunk in chunks:
        cid = chunk["chunk_id"]
        sid = chunk["source_id"]

        if sid not in source_cache:
            src = conn.execute(
                "SELECT * FROM sources WHERE source_id = ?", (sid,)
            ).fetchone()
            source_cache[sid] = dict(src) if src else {}

        source = source_cache[sid]

        citations = [
            {"target_uri": r["target_uri"], "tag": r["tag"],
             "locator": r["locator"], "verified": bool(r["verified"])}
            for r in conn.execute(
                "SELECT target_uri, tag, locator, verified "
                "FROM citations WHERE chunk_id = ?", (cid,)
            ).fetchall()
        ]

        contradictions = [
            {"target_chunk": r["target_chunk"], "basis": r["basis"],
             "confidence": r["confidence"], "resolution": r["resolution"]}
            for r in conn.execute(
                "SELECT target_chunk, basis, confidence, resolution "
                "FROM claim_edges WHERE source_chunk = ? "
                "AND edge_type = 'contradicts'", (cid,)
            ).fetchall()
        ]

        artifacts = [
            {"name": r["name"], "type": r["artifact_type"],
             "implemented": bool(r["implemented"]),
             "evidence_path": r["evidence_path"], "snippet": r["snippet"]}
            for r in conn.execute(
                "SELECT name, artifact_type, implemented, evidence_path, snippet "
                "FROM artifacts WHERE chunk_id = ?", (cid,)
            ).fetchall()
        ]

        tags = [
            {"tag": r[0], "score": r[1]}
            for r in conn.execute(
                "SELECT tag, score FROM chunk_tags "
                "WHERE chunk_id = ? ORDER BY score DESC", (cid,)
            ).fetchall()
        ]

        staleness = _staleness_verdict(source)

        record = {
            "chunk_id": cid,
            "text": chunk["norm_text"],
            "kind": chunk["kind"],
            "status": chunk["status"],
            "word_count": chunk["word_count"],
            "source": {
                "source_id": sid,
                "uri": source.get("canonical_uri", ""),
                "kind": source.get("kind", ""),
                "license_verdict": source.get("license_verdict", ""),
                "liveness": source.get("liveness", ""),
                "fetched_utc": source.get("fetched_utc", ""),
                "upstream_mtime": source.get("upstream_mtime", ""),
            },
            "tags": tags,
            "citations": citations,
            "contradicted_by": contradictions,
            "artifacts": artifacts,
            "staleness": staleness,
            "trust": _trust_for(source.get("license_verdict", "")),
        }
        records.append(record)

    return records


def export_defects(conn):
    """Export uncited accepted claims and unresolved contradictions."""
    uncited = conn.execute(
        "SELECT c.chunk_id, c.norm_text, c.kind, s.canonical_uri "
        "FROM chunks c JOIN sources s USING(source_id) "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id AND ci.verified = 1 "
        "WHERE c.kind = 'claim' AND c.status = 'accepted' "
        "AND ci.citation_id IS NULL"
    ).fetchall()

    uncited_records = [
        {"chunk_id": r["chunk_id"], "text": r["norm_text"],
         "kind": r["kind"], "source_uri": r["canonical_uri"],
         "defect": "uncited_claim"}
        for r in uncited
    ]

    contradictions = conn.execute(
        "SELECT e.edge_id, e.basis, e.confidence, "
        "e.source_chunk, e.target_chunk, "
        "substr(a.norm_text, 1, 200) AS src_text, "
        "substr(b.norm_text, 1, 200) AS tgt_text "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE e.edge_type = 'contradicts' AND e.resolution IS NULL "
        "AND a.status = 'accepted' AND b.status = 'accepted'"
    ).fetchall()

    contradiction_records = [
        {"edge_id": r["edge_id"], "basis": r["basis"],
         "confidence": r["confidence"],
         "source_chunk": r["source_chunk"],
         "target_chunk": r["target_chunk"],
         "source_text": r["src_text"],
         "target_text": r["tgt_text"],
         "defect": "unresolved_contradiction"}
        for r in contradictions
    ]

    return {
        "uncited_claims": uncited_records,
        "unresolved_contradictions": contradiction_records,
        "counts": {
            "uncited": len(uncited_records),
            "contradictions": len(contradiction_records),
            "total_defects": len(uncited_records) + len(contradiction_records),
        },
    }


def export_artifacts(conn, implemented_only=False):
    """Export all artifacts with their source chunks."""
    sql = (
        "SELECT a.artifact_id, a.chunk_id, a.artifact_type, a.name, "
        "a.version, a.snippet, a.implemented, a.evidence_path, "
        "s.canonical_uri AS source_uri, s.license_verdict "
        "FROM artifacts a "
        "JOIN chunks c ON c.chunk_id = a.chunk_id "
        "JOIN sources s ON s.source_id = c.source_id"
    )
    if implemented_only:
        sql += " WHERE a.implemented = 1"
    sql += " ORDER BY a.artifact_type, a.name"

    rows = conn.execute(sql).fetchall()
    records = [
        {
            "artifact_id": r["artifact_id"],
            "chunk_id": r["chunk_id"],
            "type": r["artifact_type"],
            "name": r["name"],
            "version": r["version"],
            "snippet": r["snippet"],
            "implemented": bool(r["implemented"]),
            "evidence_path": r["evidence_path"],
            "source_uri": r["source_uri"],
            "trust": _trust_for(r["license_verdict"]),
        }
        for r in rows
    ]

    impl_count = sum(1 for r in records if r["implemented"])
    return {
        "artifacts": records,
        "counts": {
            "total": len(records),
            "implemented": impl_count,
            "unimplemented": len(records) - impl_count,
            "rate": round(impl_count / len(records), 3) if records else 0.0,
        },
    }


def export_sources(conn):
    """Export all sources with staleness verdicts."""
    rows = conn.execute(
        "SELECT * FROM sources ORDER BY canonical_uri"
    ).fetchall()

    records = []
    for r in rows:
        src = dict(r)
        chunk_count = conn.execute(
            "SELECT count(*) FROM chunks WHERE source_id = ?",
            (src["source_id"],),
        ).fetchone()[0]

        accepted = conn.execute(
            "SELECT count(*) FROM chunks WHERE source_id = ? AND status = 'accepted'",
            (src["source_id"],),
        ).fetchone()[0]

        staleness = _staleness_verdict(src)

        records.append({
            "source_id": src["source_id"],
            "uri": src["canonical_uri"],
            "kind": src["kind"],
            "title": src["title"],
            "license_spdx": src["license_spdx"],
            "license_verdict": src["license_verdict"],
            "liveness": src["liveness"],
            "fetched_utc": src["fetched_utc"],
            "upstream_mtime": src["upstream_mtime"],
            "bytes": src["bytes"],
            "staleness": staleness,
            "chunks_total": chunk_count,
            "chunks_accepted": accepted,
        })

    return {
        "sources": records,
        "counts": {
            "total": len(records),
            "by_kind": {},
            "by_liveness": {},
        },
    }


def export_summary(conn):
    """Produce a concise corpus overview."""
    source_count = conn.execute("SELECT count(*) FROM sources").fetchone()[0]

    chunk_rows = conn.execute(
        "SELECT status, count(*) AS c FROM chunks GROUP BY status"
    ).fetchall()
    by_status = {r["status"]: r["c"] for r in chunk_rows}
    total_chunks = sum(by_status.values())

    kind_rows = conn.execute(
        "SELECT kind, count(*) AS c FROM chunks WHERE status = 'accepted' "
        "GROUP BY kind"
    ).fetchall()
    by_kind = {r["kind"]: r["c"] for r in kind_rows}

    citation_count = conn.execute("SELECT count(*) FROM citations").fetchone()[0]
    verified_citations = conn.execute(
        "SELECT count(*) FROM citations WHERE verified = 1"
    ).fetchone()[0]

    uncited = conn.execute(
        "SELECT count(*) FROM chunks c "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id AND ci.verified = 1 "
        "WHERE c.kind = 'claim' AND c.status = 'accepted' "
        "AND ci.citation_id IS NULL"
    ).fetchone()[0]

    contradictions = conn.execute(
        "SELECT count(*) FROM claim_edges "
        "WHERE edge_type = 'contradicts' AND resolution IS NULL"
    ).fetchone()[0]

    artifact_total = conn.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    artifact_impl = conn.execute(
        "SELECT count(*) FROM artifacts WHERE implemented = 1"
    ).fetchone()[0]

    edge_rows = conn.execute(
        "SELECT edge_type, count(*) AS c FROM claim_edges GROUP BY edge_type"
    ).fetchall()
    edges = {r["edge_type"]: r["c"] for r in edge_rows}

    liveness_rows = conn.execute(
        "SELECT liveness, count(*) AS c FROM sources GROUP BY liveness"
    ).fetchall()
    by_liveness = {r["liveness"]: r["c"] for r in liveness_rows}

    return {
        "sources": {"total": source_count, "by_liveness": by_liveness},
        "chunks": {
            "total": total_chunks,
            "by_status": by_status,
            "accepted_by_kind": by_kind,
        },
        "citations": {
            "total": citation_count,
            "verified": verified_citations,
        },
        "defects": {
            "uncited_claims": uncited,
            "unresolved_contradictions": contradictions,
        },
        "artifacts": {
            "total": artifact_total,
            "implemented": artifact_impl,
            "rate": round(artifact_impl / artifact_total, 3) if artifact_total else 0.0,
        },
        "edges": edges,
    }


def _output(data, fmt, out=sys.stdout):
    if fmt == "jsonl":
        if isinstance(data, list):
            for item in data:
                out.write(json.dumps(item) + "\n")
        elif isinstance(data, dict) and any(
            isinstance(v, list) for v in data.values()
        ):
            for val in data.values():
                if isinstance(val, list):
                    for item in val:
                        out.write(json.dumps(item) + "\n")
        else:
            out.write(json.dumps(data) + "\n")
    else:
        json.dump(data, out, indent=2)
        out.write("\n")


def selftest():
    failures = []

    def t(name, cond):
        if not cond:
            failures.append(name)
            print(f"  FAIL: {name}")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        def add_source(sid, uri, verdict="vendor", liveness="live",
                       mtime=None, kind="local_md"):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes) "
                "VALUES (?, ?, ?, 'Test', 'MIT', ?, 'test', ?, ?, ?, ?, 100)",
                (sid, uri, kind, verdict, now, liveness,
                 mtime or now, _sha256(sid)),
            )

        def add_chunk(cid, sid, text, kind="prose", status="accepted", ordinal=0):
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, ordinal, kind, text, text, len(text.split()),
                 _sha256(text), status, now),
            )

        add_source("s1", "/test/s1", mtime="2026-08-01T00:00:00Z")
        add_source("s2", "/test/s2", verdict="index_only",
                   mtime="2024-01-01T00:00:00Z")

        add_chunk("c1", "s1", "numpy matrix multiplication library", ordinal=0)
        add_chunk("c2", "s2", "polars dataframe operations", kind="claim", ordinal=0)
        add_chunk("c3", "s1", "quarantined chunk here", status="quarantined", ordinal=1)
        conn.commit()

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, 1)",
            ("cit1", "c1", "https://numpy.org", "ref", "docs"),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, 'contradicts', 'test', 0.8, ?)",
            ("e1", "c1", "c2", now),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES (?, ?, 'library', 'numpy', 'matrix ops', 1, '/lib/numpy')",
            ("a1", "c1"),
        )
        conn.commit()

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c1", "database", 0.85, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c2", "data", 0.72, now),
        )
        conn.commit()

        records = export_full(conn)
        t("full export returns all chunks", len(records) == 3)
        t("full export has section 7.2 fields",
          all(k in records[0] for k in
              ("chunk_id", "text", "kind", "source", "citations",
               "contradicted_by", "artifacts", "staleness", "trust",
               "tags")))

        accepted = export_full(conn, status_filter="accepted")
        t("status filter works", len(accepted) == 2)

        prose = export_full(conn, kind_filter="prose")
        t("kind filter works", len(prose) == 2)

        prose_accepted = export_full(conn, status_filter="accepted", kind_filter="prose")
        t("combined filters work", len(prose_accepted) == 1)

        defects = export_defects(conn)
        t("defects export has uncited", "uncited_claims" in defects)
        t("defects export has contradictions",
          "unresolved_contradictions" in defects)
        t("uncited claim detected",
          defects["counts"]["uncited"] == 1)
        t("contradiction detected",
          defects["counts"]["contradictions"] == 1)

        arts = export_artifacts(conn)
        t("artifacts exported", arts["counts"]["total"] == 1)
        t("artifact implementation tracked",
          arts["counts"]["implemented"] == 1)

        impl_only = export_artifacts(conn, implemented_only=True)
        t("implemented filter works",
          impl_only["counts"]["total"] == 1)

        sources = export_sources(conn)
        t("sources exported", sources["counts"]["total"] == 2)
        t("source has staleness",
          "staleness" in sources["sources"][0])

        summary = export_summary(conn)
        t("summary has sources", summary["sources"]["total"] == 2)
        t("summary has chunks", summary["chunks"]["total"] == 3)
        t("summary has defects",
          summary["defects"]["uncited_claims"] == 1)
        t("summary has artifacts",
          summary["artifacts"]["total"] == 1)

        tagged = export_full(conn, tag_filter="database")
        t("tag filter works", len(tagged) == 1)
        t("tag filter returns correct chunk",
          tagged[0]["chunk_id"] == "c1")
        t("tags included in record",
          len(tagged[0]["tags"]) > 0 and tagged[0]["tags"][0]["tag"] == "database")

        by_source_kind = export_full(conn, source_kind="local_md")
        t("source-kind filter works", len(by_source_kind) == 3)

        since_recs = export_full(conn, since="2026-08-30T00:00:00Z")
        t("since filter works", len(since_recs) == 3)

        before_recs = export_full(conn, before="2020-01-01T00:00:00Z")
        t("before filter excludes all", len(before_recs) == 0)

        range_recs = export_full(
            conn, since="2026-01-01T00:00:00Z", before="2027-01-01T00:00:00Z",
        )
        t("date range filter works", len(range_recs) == 3)

        combined = export_full(
            conn, status_filter="accepted", tag_filter="database",
            kind_filter="prose",
        )
        t("combined tag+status+kind filter", len(combined) == 1)

        out_path = Path(tmp) / "export.jsonl"
        from io import StringIO
        buf_out = StringIO()
        _output(tagged, "jsonl", buf_out)
        with open(out_path, "w") as f:
            f.write(buf_out.getvalue())
        t("file output works", out_path.exists())

        from io import StringIO
        buf = StringIO()
        _output(records, "jsonl", buf)
        lines = buf.getvalue().strip().split("\n")
        t("jsonl output has one line per record", len(lines) == 3)

        buf2 = StringIO()
        _output(records, "json", buf2)
        parsed = json.loads(buf2.getvalue())
        t("json output is valid", len(parsed) == 3)

    status = "PASS" if not failures else "FAIL"
    checks = 27 - len(failures)
    print(f"selftest: {status} ({checks}/27 checks)")
    return not failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Corpus export")
    sub = parser.add_subparsers(dest="cmd")

    p_full = sub.add_parser("full", help="export all chunks as 7.2 records")
    p_full.add_argument("--db", default=str(DEFAULT_DB))
    p_full.add_argument("--format", choices=["json", "jsonl"], default="json",
                        dest="fmt")
    p_full.add_argument("--status", help="filter by chunk status")
    p_full.add_argument("--kind", help="filter by chunk kind (comma-separated)")
    p_full.add_argument("--source-kind",
                        help="filter by source kind (comma-separated)")
    p_full.add_argument("--tag",
                        help="filter by tag from chunk_tags (comma-separated)")
    p_full.add_argument("--since",
                        help="include chunks ingested on or after ISO date")
    p_full.add_argument("--before",
                        help="include chunks ingested before ISO date")
    p_full.add_argument("--out", help="write output to file instead of stdout")

    p_def = sub.add_parser("defects", help="export uncited claims and contradictions")
    p_def.add_argument("--db", default=str(DEFAULT_DB))
    p_def.add_argument("--format", choices=["json", "jsonl"], default="json",
                       dest="fmt")

    p_art = sub.add_parser("artifacts", help="export artifacts")
    p_art.add_argument("--db", default=str(DEFAULT_DB))
    p_art.add_argument("--implemented", action="store_true")
    p_art.add_argument("--format", choices=["json", "jsonl"], default="json",
                       dest="fmt")

    p_src = sub.add_parser("sources", help="export sources with staleness")
    p_src.add_argument("--db", default=str(DEFAULT_DB))
    p_src.add_argument("--format", choices=["json", "jsonl"], default="json",
                       dest="fmt")

    p_sum = sub.add_parser("summary", help="concise corpus overview")
    p_sum.add_argument("--db", default=str(DEFAULT_DB))
    p_sum.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="prove the module works")

    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif args.cmd == "full":
        conn = connect(args.db)
        records = export_full(
            conn, args.status, args.kind,
            source_kind=args.source_kind, tag_filter=args.tag,
            since=args.since, before=args.before,
        )
        conn.close()
        if args.out:
            with open(args.out, "w") as f:
                _output(records, args.fmt, out=f)
            print(f"  wrote {len(records)} record(s) to {args.out}")
        else:
            _output(records, args.fmt)
    elif args.cmd == "defects":
        conn = connect(args.db)
        data = export_defects(conn)
        conn.close()
        _output(data, args.fmt)
    elif args.cmd == "artifacts":
        conn = connect(args.db)
        data = export_artifacts(conn, args.implemented)
        conn.close()
        _output(data, args.fmt)
    elif args.cmd == "sources":
        conn = connect(args.db)
        data = export_sources(conn)
        conn.close()
        _output(data, args.fmt)
    elif args.cmd == "summary":
        conn = connect(args.db)
        data = export_summary(conn)
        conn.close()
        if hasattr(args, "as_json") and args.as_json:
            print(json.dumps(data, indent=2))
        else:
            print(f"corpus: {data['sources']['total']} sources, "
                  f"{data['chunks']['total']} chunks")
            print(f"  accepted: {data['chunks']['by_status'].get('accepted', 0)}")
            print(f"  quarantined: {data['chunks']['by_status'].get('quarantined', 0)}")
            print(f"  superseded: {data['chunks']['by_status'].get('superseded', 0)}")
            print(f"  citations: {data['citations']['total']} "
                  f"({data['citations']['verified']} verified)")
            d = data["defects"]
            print(f"  defects: {d['uncited_claims']} uncited, "
                  f"{d['unresolved_contradictions']} contradictions")
            a = data["artifacts"]
            print(f"  artifacts: {a['total']} total, {a['implemented']} implemented "
                  f"({a['rate']*100:.1f}%)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
