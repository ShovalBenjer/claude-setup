#!/usr/bin/env python3
"""Cache-to-action proposal path for the research corpus (spec step 10, section 5.2).

Retrieves actionable artifacts (commands, configs, oneliners, patterns)
from the corpus and returns proposals with trust flags. Never auto-executes.
Artifacts from index-only sources are display-only, enforced by test.

Usage:
    python tools/corpus/cache2action.py propose --query TEXT [--db PATH] [--repo PATH]
    python tools/corpus/cache2action.py verify [--db PATH] [--repo PATH]
    python tools/corpus/cache2action.py selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _sha256,
    connect,
    init_schema,
)

ACTIONABLE_TYPES = ("command", "oneliner", "config", "pattern", "api")

UNTRUSTED_VERDICTS = frozenset({
    "index_only",
    "link_only",
    "blocked",
})


def _resolve_evidence(evidence_path, repo_root):
    """Check if an evidence_path still exists on disk."""
    if not evidence_path:
        return False
    path_str = evidence_path.split(":")[0]
    path_str = path_str.replace("~", str(Path.home()))
    p = Path(path_str)
    if p.is_absolute():
        return p.exists()
    return (repo_root / p).exists()


def _trust_level(conn, chunk_id):
    """Determine trust level for an artifact based on its source's license_verdict."""
    row = conn.execute(
        "SELECT s.license_verdict FROM chunks c "
        "JOIN sources s USING(source_id) WHERE c.chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if not row:
        return "unknown"
    verdict = row[0]
    if verdict in UNTRUSTED_VERDICTS:
        return "display_only"
    return "actionable"


def propose(conn, query_text, repo_root=None):
    """Find actionable artifacts matching a query, with trust flags.

    Returns a list of proposal dicts. Never executes anything.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    else:
        repo_root = Path(repo_root)

    words = query_text.lower().split()
    if not words:
        return []

    fts_query = " OR ".join(words)
    matching_chunks = conn.execute(
        "SELECT c.chunk_id "
        "FROM chunks_fts f JOIN chunks c ON f.rowid = c.rowid "
        "WHERE f.norm_text MATCH ? LIMIT 200",
        (fts_query,),
    ).fetchall()

    chunk_ids = {r[0] for r in matching_chunks}
    if not chunk_ids:
        return []

    placeholders = ",".join("?" * len(chunk_ids))
    artifacts = conn.execute(
        f"SELECT artifact_id, chunk_id, artifact_type, name, version, "
        f"snippet, implemented, evidence_path "
        f"FROM artifacts WHERE chunk_id IN ({placeholders}) "
        f"AND artifact_type IN ({','.join('?' * len(ACTIONABLE_TYPES))})",
        list(chunk_ids) + list(ACTIONABLE_TYPES),
    ).fetchall()

    proposals = []
    for row in artifacts:
        aid, cid, atype, name, version, snippet, implemented, evidence = row
        trust = _trust_level(conn, cid)
        evidence_valid = _resolve_evidence(evidence, repo_root) if evidence else False

        proposal = {
            "artifact_id": aid,
            "name": name,
            "type": atype,
            "version": version,
            "snippet": snippet,
            "implemented": bool(implemented),
            "evidence_path": evidence,
            "evidence_valid": evidence_valid,
            "trust": trust,
            "executable": trust == "actionable" and bool(implemented),
        }
        proposals.append(proposal)

    proposals.sort(key=lambda p: (
        not p["executable"],
        not p["implemented"],
        not p["evidence_valid"],
        p["trust"] == "display_only",
    ))

    return proposals


def verify_evidence(conn, repo_root=None):
    """Check all implemented artifacts for evidence path validity.

    Returns (valid, invalid, missing) counts and lists of invalid artifacts.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    else:
        repo_root = Path(repo_root)

    artifacts = conn.execute(
        "SELECT artifact_id, name, artifact_type, evidence_path "
        "FROM artifacts WHERE implemented = 1"
    ).fetchall()

    valid = []
    invalid = []
    missing = []

    for aid, name, atype, evidence in artifacts:
        if not evidence:
            missing.append({"artifact_id": aid, "name": name, "type": atype})
            continue
        if _resolve_evidence(evidence, repo_root):
            valid.append({"artifact_id": aid, "name": name, "type": atype,
                          "evidence_path": evidence})
        else:
            invalid.append({"artifact_id": aid, "name": name, "type": atype,
                            "evidence_path": evidence})

    return valid, invalid, missing


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        (repo_dir / "real_script.sh").write_text("#!/bin/bash\necho hello")

        def add_source(sid, kind="local_md", verdict="vendor"):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " content_sha256, bytes) "
                "VALUES (?, ?, ?, 'Test', 'MIT', ?, 'test', ?, 'live', ?, 100)",
                (sid, f"/test/{sid}", kind, verdict, now, _sha256(sid)),
            )

        def add_chunk(cid, sid, text):
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', 'prose', ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, text, text, len(text.split()), _sha256(text), now),
            )

        def add_artifact(aid, cid, atype, name, implemented, evidence=None):
            conn.execute(
                "INSERT OR IGNORE INTO artifacts "
                "(artifact_id, chunk_id, artifact_type, name, version, "
                " snippet, implemented, evidence_path) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, ?)",
                (aid, cid, atype, name, f"snippet for {name}", implemented, evidence),
            )

        add_source("s_vendor1", verdict="vendor")
        add_source("s_vendor2", verdict="vendor")
        add_source("s_index", verdict="index_only")
        add_chunk("c_vendor1", "s_vendor1",
                  "run the deploy script to start the service")
        add_chunk("c_vendor2", "s_vendor2",
                  "use numpy for matrix multiplication")
        add_chunk("c_index1", "s_index",
                  "run the deploy script for production setup")
        conn.commit()

        add_artifact("a_cmd1", "c_vendor1", "command", "deploy.sh",
                     1, str(repo_dir / "real_script.sh"))
        add_artifact("a_lib1", "c_vendor2", "library", "numpy", 1, None)
        add_artifact("a_cmd2", "c_index1", "command", "deploy-prod.sh", 1, None)
        conn.commit()

        # Test 1: propose returns results for matching query
        results = propose(conn, "deploy script", repo_root=repo_dir)
        if not results:
            failures.append("propose returned no results for 'deploy script'")

        # Test 2: vendor-sourced artifact is actionable
        vendor_results = [r for r in results if r["name"] == "deploy.sh"]
        if not vendor_results:
            failures.append("deploy.sh not found in results")
        elif vendor_results[0]["trust"] != "actionable":
            failures.append(f"vendor artifact trust is {vendor_results[0]['trust']}, expected actionable")

        # Test 3: index-only sourced artifact is display_only
        index_results = [r for r in results if r["name"] == "deploy-prod.sh"]
        if not index_results:
            failures.append("deploy-prod.sh not found in results")
        elif index_results[0]["trust"] != "display_only":
            failures.append(f"index_only artifact trust is {index_results[0]['trust']}, expected display_only")

        # Test 4: display_only artifact is NOT executable
        if index_results and index_results[0]["executable"]:
            failures.append("display_only artifact should not be executable")

        # Test 5: vendor artifact with valid evidence is executable
        if vendor_results and not vendor_results[0]["executable"]:
            failures.append("vendor implemented artifact should be executable")

        # Test 6: evidence_valid reflects disk state
        if vendor_results and not vendor_results[0]["evidence_valid"]:
            failures.append("evidence_valid should be True for existing file")

        # Test 7: verify_evidence counts correctly
        valid, invalid, missing = verify_evidence(conn, repo_root=repo_dir)
        if len(valid) != 1:
            failures.append(f"expected 1 valid evidence, got {len(valid)}")
        if len(missing) != 2:
            failures.append(f"expected 2 missing evidence, got {len(missing)}")

        # Test 8: empty query returns empty list
        empty = propose(conn, "", repo_root=repo_dir)
        if empty:
            failures.append("empty query should return empty list")

        # Test 9: non-matching query returns empty
        nomatch = propose(conn, "xyznonexistent", repo_root=repo_dir)
        if nomatch:
            failures.append("non-matching query should return empty list")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS cache2action selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_propose = sub.add_parser("propose", help="Propose actionable artifacts")
    p_propose.add_argument("--query", required=True)
    p_propose.add_argument("--db", default=None)
    p_propose.add_argument("--repo", default=None)

    p_verify = sub.add_parser("verify", help="Verify evidence paths")
    p_verify.add_argument("--db", default=None)
    p_verify.add_argument("--repo", default=None)

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    db = getattr(args, "db", None)
    conn = connect(db)

    if args.command == "propose":
        repo = Path(args.repo) if args.repo else Path.cwd()
        results = propose(conn, args.query, repo_root=repo)
        if not results:
            print("  no matching artifacts")
        else:
            for p in results:
                trust_tag = f"[{p['trust']}]"
                impl_tag = "implemented" if p["implemented"] else "referenced"
                ev_tag = "evidence:valid" if p["evidence_valid"] else "evidence:missing"
                print(f"  {trust_tag} {p['type']:8s} {p['name']}")
                print(f"    {impl_tag}, {ev_tag}")
                if p["snippet"]:
                    print(f"    snippet: {p['snippet'][:80]}")
                if p["evidence_path"]:
                    print(f"    path: {p['evidence_path']}")
                print()
        print(f"  {len(results)} proposal(s), "
              f"{sum(1 for p in results if p['executable'])} executable")
        conn.close()
        return 0

    if args.command == "verify":
        repo = Path(args.repo) if args.repo else Path.cwd()
        valid, invalid, missing = verify_evidence(conn, repo_root=repo)
        print(f"  valid: {len(valid)}")
        print(f"  invalid: {len(invalid)}")
        print(f"  missing: {len(missing)}")
        if invalid:
            print("\n  invalid evidence paths:")
            for item in invalid:
                print(f"    {item['name']} ({item['type']}): {item['evidence_path']}")
        conn.close()
        return 1 if invalid else 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
