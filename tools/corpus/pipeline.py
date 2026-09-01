#!/usr/bin/env python3
"""Corpus ingestion pipeline: runs all stages end-to-end in the correct order.

Orchestrates the full spec section 6 pipeline: ingest (stages 0-4), then
contradiction detection (stage 5), artifact extraction (stage 6), embedding
fit (step 5), and health check. Each stage is idempotent so the pipeline
can be re-run safely.

Usage:
  python tools/corpus/pipeline.py run [--db PATH] [--skip-embed] [--json]
  python tools/corpus/pipeline.py selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "state" / "corpus.db"

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_stage(name, fn, *args, **kwargs):
    """Run a stage, return (result, elapsed_seconds, error_or_none)."""
    t0 = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        elapsed = round(time.monotonic() - t0, 2)
        return result, elapsed, None
    except Exception as e:
        elapsed = round(time.monotonic() - t0, 2)
        return None, elapsed, str(e)


def run_pipeline(db_path=None, skip_embed=False):
    """Run the full corpus pipeline. Returns a structured report."""
    dp = Path(db_path) if db_path else DEFAULT_DB
    stages = []

    from research import connect, init_schema, status
    from research import ingest as do_ingest

    if not dp.exists():
        conn = connect(str(dp))
        init_schema(conn)
        conn.close()

    conn = connect(str(dp))
    pre = status(conn)
    conn.close()

    conn = connect(str(dp))
    result, elapsed, err = _run_stage("ingest", do_ingest, conn, ledger_path=None)
    conn.commit()
    post_ingest = status(conn)
    conn.close()
    stages.append({
        "name": "ingest",
        "elapsed_s": elapsed,
        "error": err,
        "result": {
            "sources_before": pre.get("sources", 0),
            "sources_after": post_ingest.get("sources", 0),
            "chunks_after": post_ingest.get("chunks", 0),
        } if not err else None,
    })

    from contradict import detect as do_contradict

    conn = _connect(dp)
    result, elapsed, err = _run_stage("contradict", do_contradict, conn)
    if not err:
        conn.commit()
    conn.close()
    stages.append({
        "name": "contradiction_detection",
        "elapsed_s": elapsed,
        "error": err,
        "result": result if not err else None,
    })

    from artifacts import extract as do_extract

    conn = _connect(dp)
    result, elapsed, err = _run_stage("artifacts", do_extract, conn)
    if not err:
        conn.commit()
    conn.close()
    stages.append({
        "name": "artifact_extraction",
        "elapsed_s": elapsed,
        "error": err,
        "result": result if not err else None,
    })

    if not skip_embed:
        try:
            from embed import fit as do_fit
            conn = _connect(dp)
            result, elapsed, err = _run_stage("embed", do_fit, conn, dp)
            conn.close()
            stages.append({
                "name": "embedding_fit",
                "elapsed_s": elapsed,
                "error": err,
                "result": result if not err else None,
            })
        except ImportError as e:
            stages.append({
                "name": "embedding_fit",
                "elapsed_s": 0,
                "error": f"numpy not available: {e}",
                "result": None,
            })
    else:
        stages.append({
            "name": "embedding_fit",
            "elapsed_s": 0,
            "error": None,
            "result": "skipped",
        })

    from health import check as do_health

    health_report, health_code = do_health(dp)
    stages.append({
        "name": "health_check",
        "elapsed_s": 0,
        "error": None,
        "result": health_report,
    })

    total_elapsed = sum(s["elapsed_s"] for s in stages)
    errors = [s for s in stages if s["error"]]

    report = {
        "timestamp": _now(),
        "db": str(dp),
        "total_elapsed_s": round(total_elapsed, 2),
        "stages": stages,
        "errors": len(errors),
        "health_verdict": health_report.get("verdict", "UNKNOWN"),
    }

    return report


def _print_report(report):
    """Human-readable pipeline report."""
    print(f"corpus pipeline: {report['health_verdict']} ({report['total_elapsed_s']}s)")
    print()
    for stage in report["stages"]:
        status = "OK" if not stage["error"] else "ERROR"
        print(f"  {stage['name']}: {status} ({stage['elapsed_s']}s)")
        if stage["error"]:
            print(f"    error: {stage['error']}")
        elif stage["result"] and isinstance(stage["result"], dict):
            for k, v in stage["result"].items():
                if k not in ("defects", "chunks", "staleness", "embedding", "artifacts"):
                    print(f"    {k}: {v}")
    if report["errors"]:
        print(f"\n  {report['errors']} stage(s) had errors")


def selftest():
    failures = []

    def t(name, cond):
        if not cond:
            failures.append(name)
            print(f"  FAIL: {name}")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"

        from research import connect, init_schema

        conn = connect(str(db_path))
        init_schema(conn)
        conn.close()

        report = run_pipeline(db_path, skip_embed=True)

        t("report has timestamp", "timestamp" in report)
        t("report has stages", len(report["stages"]) == 5)
        t("ingest ran", report["stages"][0]["name"] == "ingest")
        t("contradiction ran", report["stages"][1]["name"] == "contradiction_detection")
        t("artifacts ran", report["stages"][2]["name"] == "artifact_extraction")
        t("embed skipped", report["stages"][3]["result"] == "skipped")
        t("health ran", report["stages"][4]["name"] == "health_check")
        t("no errors on empty db", report["errors"] == 0)
        t("health verdict present", report["health_verdict"] in ("HEALTHY", "DEFECTS", "NO_CORPUS"))

        report2 = run_pipeline(db_path, skip_embed=True)
        t("re-run is idempotent", report2["errors"] == 0)

    status = "PASS" if not failures else "FAIL"
    checks = 10 - len(failures)
    print(f"selftest: {status} ({checks}/10 checks)")
    return not failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Corpus ingestion pipeline")
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="run full pipeline")
    p_run.add_argument("--db", default=str(DEFAULT_DB))
    p_run.add_argument("--skip-embed", action="store_true")
    p_run.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="prove the module works")

    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif args.cmd == "run" or args.cmd is None:
        db = args.db if hasattr(args, "db") else str(DEFAULT_DB)
        skip = args.skip_embed if hasattr(args, "skip_embed") else False
        as_json = args.as_json if hasattr(args, "as_json") else False
        report = run_pipeline(db, skip_embed=skip)
        if as_json:
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)


if __name__ == "__main__":
    main()
