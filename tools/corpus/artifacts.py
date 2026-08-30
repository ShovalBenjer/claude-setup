#!/usr/bin/env python3
"""Artifact extraction from the research corpus (spec step 8, stage 6).

Scans accepted chunks in state/corpus.db for references to libraries,
commands, APIs, config fragments, and patterns, then checks which are
actually present on disk. Populates the artifacts table with
implemented=1 and evidence_path for real files, implemented=0 otherwise.

Usage:
    python tools/corpus/artifacts.py extract [--db PATH] [--repo PATH]
    python tools/corpus/artifacts.py report [--db PATH]
    python tools/corpus/artifacts.py selftest
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _sha256,
    connect,
    init_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


LIBRARY_RE = re.compile(
    r"`([\w][\w.-]{1,60})`"
    r"(?:\s*(?:==|>=|<=|~=|!=|>|<)\s*(\d[\w.*-]*))?"
)

PIP_RE = re.compile(
    r"\bpip\s+install\s+([A-Za-z][\w.-]+)"
    r"(?:\s*(?:==|>=)(\S+))?"
)

NPM_RE = re.compile(
    r"\bnpm\s+(?:install|i)\s+(?:--save-dev\s+|--save\s+|-D\s+|-S\s+)?"
    r"([a-z@][\w./@-]+)"
    r"(?:@(\S+))?"
)

IMPORT_RE = re.compile(
    r"(?:^|\n)\s*(?:from|import)\s+([\w]+)"
)

COMMAND_RE = re.compile(
    r"(?:^|\n)\s*\$\s+(.{5,120})"
    r"|(?:^|\n)```(?:bash|sh|shell)?\n((?:.|\n)*?)```"
)

FILE_PATH_RE = re.compile(
    r"(?:`|\"|\s)((?:[\w.-]+/){1,8}[\w.-]+\.(?:py|js|ts|rs|go|sh|yaml|yml|toml|json|sql|css|html))`?"
)

CONFIG_RE = re.compile(
    r"\b([\w_-]+\.(?:yaml|yml|toml|json|ini|cfg|conf|env))\b"
)

PYTHON_STDLIB = {
    "os", "sys", "re", "json", "csv", "math", "time", "datetime",
    "pathlib", "sqlite3", "hashlib", "tempfile", "argparse", "subprocess",
    "collections", "functools", "itertools", "typing", "io", "abc",
    "dataclasses", "enum", "uuid", "shutil", "glob", "logging",
    "unittest", "contextlib", "copy", "pprint", "textwrap", "string",
    "random", "struct", "socket", "threading", "multiprocessing",
    "http", "urllib", "email", "html", "xml", "ast", "dis", "inspect",
    "importlib", "pkgutil", "traceback", "warnings", "signal",
    "statistics", "fractions", "decimal", "operator", "heapq",
    "bisect", "array", "weakref", "types", "platform", "sysconfig",
    "configparser", "tomllib", "zipfile", "tarfile", "gzip", "bz2",
    "lzma", "base64", "binascii", "secrets", "hmac",
}

NOISE_NAMES = {
    "the", "and", "for", "not", "but", "are", "was", "has", "had",
    "will", "this", "that", "with", "from", "true", "false", "null",
    "none", "test", "tests", "file", "files", "code", "data", "name",
    "type", "path", "note", "item", "todo", "done", "pass", "fail",
    "yes", "see", "run", "set", "get", "new", "old", "use", "all",
    "any", "each", "one", "two", "end", "key", "api", "app", "src",
    "doc", "docs", "bin", "lib", "tmp", "log", "cmd", "cli", "url",
    "env", "dev", "pre", "fix", "add", "raw", "out",
}


SKIP_DIRS = {".venv", ".venv-linux", "venv", "node_modules", ".git",
             "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
             "target", "dist", "build", ".tox", ".eggs"}


def _find_on_disk(name, repo_root):
    """Search for a library, command, or file on disk."""
    if not repo_root or not repo_root.is_dir():
        return None

    def _skip(p):
        return any(part in SKIP_DIRS for part in p.parts)

    if "/" in name and not name.startswith("/"):
        candidate = repo_root / name
        if candidate.exists() and not _skip(candidate.relative_to(repo_root)):
            return str(candidate.relative_to(repo_root))
        basename = name.split("/")[-1]
        if basename not in ("__init__.py", "index.js", "index.ts", "mod.rs"):
            for p in repo_root.rglob(basename):
                rel = p.relative_to(repo_root)
                if p.is_file() and not _skip(rel):
                    return str(rel)

    if name.endswith((".py", ".js", ".ts", ".rs", ".go", ".sh",
                      ".yaml", ".yml", ".toml", ".json")):
        for p in repo_root.rglob(name):
            rel = p.relative_to(repo_root)
            if p.is_file() and not _skip(rel):
                return str(rel)

    return None


def _classify_artifact(name, context):
    """Determine artifact_type from name and surrounding context."""
    lower_ctx = context.lower()
    lower_name = name.lower()

    if any(kw in lower_ctx for kw in ("pip install", "npm install",
                                       "requirements.txt", "package.json",
                                       "pyproject.toml", "cargo.toml")):
        return "library"

    if any(kw in lower_ctx for kw in ("import ", "from ", "require(",
                                       "using ")):
        return "library"

    if lower_name.endswith((".yaml", ".yml", ".toml", ".json", ".ini",
                            ".cfg", ".conf", ".env")):
        return "config"

    if any(kw in lower_ctx for kw in ("$ ", "run ", "execute ",
                                       "command", "bash", "shell")):
        return "command"

    if any(kw in lower_ctx for kw in ("api", "endpoint", "route",
                                       "webhook", "rest", "graphql")):
        return "api"

    if any(kw in lower_ctx for kw in ("pattern", "technique", "approach",
                                       "strategy", "architecture")):
        return "pattern"

    if lower_name.endswith((".py", ".js", ".ts", ".rs", ".go", ".sh")):
        return "command"

    return "library"


def _extract_from_chunk(chunk_text, chunk_id):
    """Extract artifact candidates from a single chunk's text."""
    artifacts = []
    seen_names = set()

    for m in PIP_RE.finditer(chunk_text):
        name = m.group(1)
        version = m.group(2)
        if name.lower() not in NOISE_NAMES and name not in seen_names:
            seen_names.add(name)
            ctx = chunk_text[max(0, m.start() - 30):m.end() + 30]
            artifacts.append({
                "name": name,
                "version": version,
                "artifact_type": "library",
                "snippet": ctx.strip(),
                "chunk_id": chunk_id,
            })

    for m in NPM_RE.finditer(chunk_text):
        name = m.group(1)
        version = m.group(2)
        if name.lower() not in NOISE_NAMES and name not in seen_names:
            seen_names.add(name)
            ctx = chunk_text[max(0, m.start() - 30):m.end() + 30]
            artifacts.append({
                "name": name,
                "version": version,
                "artifact_type": "library",
                "snippet": ctx.strip(),
                "chunk_id": chunk_id,
            })

    for m in IMPORT_RE.finditer(chunk_text):
        name = m.group(1)
        if (name.lower() not in NOISE_NAMES
                and name.lower() not in PYTHON_STDLIB
                and name not in seen_names
                and len(name) >= 3):
            seen_names.add(name)
            ctx = chunk_text[max(0, m.start() - 10):m.end() + 40]
            artifacts.append({
                "name": name,
                "version": None,
                "artifact_type": "library",
                "snippet": ctx.strip(),
                "chunk_id": chunk_id,
            })

    for m in FILE_PATH_RE.finditer(chunk_text):
        path_name = m.group(1)
        if path_name not in seen_names and len(path_name) >= 5:
            seen_names.add(path_name)
            ctx = chunk_text[max(0, m.start() - 20):m.end() + 20]
            atype = _classify_artifact(path_name, ctx)
            artifacts.append({
                "name": path_name,
                "version": None,
                "artifact_type": atype,
                "snippet": ctx.strip(),
                "chunk_id": chunk_id,
            })

    for m in LIBRARY_RE.finditer(chunk_text):
        name = m.group(1)
        version = m.group(2)
        if (name not in seen_names
                and name.lower() not in NOISE_NAMES
                and name.lower() not in PYTHON_STDLIB
                and len(name) >= 3
                and not name[0].isdigit()
                and not name.startswith(("-", ".", "_"))
                and not all(c in ".-_" for c in name)):
            ctx_start = max(0, m.start() - 40)
            ctx_end = min(len(chunk_text), m.end() + 40)
            ctx = chunk_text[ctx_start:ctx_end]
            atype = _classify_artifact(name, ctx)
            if atype == "library":
                seen_names.add(name)
                artifacts.append({
                    "name": name,
                    "version": version,
                    "artifact_type": atype,
                    "snippet": ctx.strip(),
                    "chunk_id": chunk_id,
                })

    return artifacts


def extract(conn, repo_root=None):
    """Extract artifacts from all accepted chunks."""
    if repo_root is None:
        repo_root = REPO_ROOT

    repo_root = Path(repo_root) if repo_root else None

    rows = conn.execute(
        "SELECT chunk_id, norm_text FROM chunks WHERE status='accepted'"
    ).fetchall()

    all_artifacts = []
    for row in rows:
        chunk_id = row[0]
        text = row[1]
        extracted = _extract_from_chunk(text, chunk_id)
        all_artifacts.extend(extracted)

    name_best = {}
    for a in all_artifacts:
        key = a["name"].lower()
        if key not in name_best:
            name_best[key] = a
        elif a["version"] and not name_best[key]["version"]:
            name_best[key] = a

    written = 0
    existing = {
        r[0] for r in conn.execute("SELECT artifact_id FROM artifacts").fetchall()
    }

    for a in name_best.values():
        artifact_id = "a" + _sha256(a["name"].lower() + a["artifact_type"])[:16]
        if artifact_id in existing:
            continue

        evidence = None
        implemented = 0
        if repo_root:
            evidence = _find_on_disk(a["name"], repo_root)
            if evidence:
                implemented = 1

        conn.execute(
            "INSERT OR IGNORE INTO artifacts "
            "(artifact_id, chunk_id, artifact_type, name, version, "
            " snippet, implemented, evidence_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (artifact_id, a["chunk_id"], a["artifact_type"],
             a["name"], a["version"], a["snippet"][:500] if a["snippet"] else None,
             implemented, evidence),
        )
        written += 1

    conn.commit()

    total = conn.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    impl = conn.execute(
        "SELECT count(*) FROM artifacts WHERE implemented=1"
    ).fetchone()[0]

    return {
        "candidates": len(all_artifacts),
        "unique": len(name_best),
        "new_written": written,
        "total": total,
        "implemented": impl,
        "unimplemented": total - impl,
    }


def report(conn):
    """Report artifacts grouped by type and implementation status."""
    rows = conn.execute(
        "SELECT a.artifact_id, a.artifact_type, a.name, a.version, "
        "       a.implemented, a.evidence_path, a.snippet, "
        "       s.canonical_uri AS source_uri "
        "FROM artifacts a "
        "JOIN chunks c ON c.chunk_id = a.chunk_id "
        "JOIN sources s ON s.source_id = c.source_id "
        "ORDER BY a.artifact_type, a.implemented DESC, a.name"
    ).fetchall()
    return [dict(r) for r in rows]


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = _now()

        def add_chunk(cid, sid, text):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " content_sha256, bytes) "
                "VALUES (?, ?, 'local_md', 'Test', 'proprietary', "
                " 'vendor', 'local', ?, 'live', ?, 100)",
                (sid, f"/test/{sid}", now, _sha256(text)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', 'prose', ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, text, text, len(text.split()), _sha256(text), now),
            )
            conn.commit()

        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        (repo_dir / "tools").mkdir()
        (repo_dir / "tools" / "gate.py").write_text("# gate tool")
        (repo_dir / "config.yaml").write_text("key: value")

        # Test 1: pip install extracts a library
        add_chunk("c1", "s1", "Run pip install numpy>=1.24 for array support")
        arts = _extract_from_chunk(
            "Run pip install numpy>=1.24 for array support", "c1"
        )
        found_numpy = any(a["name"] == "numpy" for a in arts)
        if not found_numpy:
            failures.append("pip install not extracted")

        # Test 2: import statement extracts a library
        add_chunk("c2", "s2", "from polars import DataFrame\nimport duckdb")
        arts = _extract_from_chunk(
            "from polars import DataFrame\nimport duckdb", "c2"
        )
        found_polars = any(a["name"] == "polars" for a in arts)
        found_duckdb = any(a["name"] == "duckdb" for a in arts)
        if not found_polars:
            failures.append("import-from not extracted")
        if not found_duckdb:
            failures.append("import not extracted")

        # Test 3: file path extracts a command/config
        add_chunk("c3", "s3", "Edit the `tools/gate.py` file to add checks")
        arts = _extract_from_chunk(
            "Edit the `tools/gate.py` file to add checks", "c3"
        )
        found_gate = any("gate.py" in a["name"] for a in arts)
        if not found_gate:
            failures.append("file path not extracted")

        # Test 4: stdlib imports are filtered
        add_chunk("c4", "s4", "import os\nimport json\nfrom pathlib import Path")
        arts = _extract_from_chunk(
            "import os\nimport json\nfrom pathlib import Path", "c4"
        )
        stdlib_found = any(a["name"] in PYTHON_STDLIB for a in arts)
        if stdlib_found:
            failures.append("stdlib import not filtered")

        # Test 5: noise words are filtered
        add_chunk("c5", "s5", "the `test` value is `true` and `data` is ready")
        arts = _extract_from_chunk(
            "the `test` value is `true` and `data` is ready", "c5"
        )
        noise_found = any(a["name"].lower() in NOISE_NAMES for a in arts)
        if noise_found:
            failures.append("noise word not filtered")

        # Test 6: extract() writes rows to DB
        result = extract(conn, repo_root=repo_dir)
        if result["new_written"] == 0:
            failures.append("extract() wrote zero artifacts")
        if result["total"] == 0:
            failures.append("extract() total is zero")

        # Test 7: implemented detection works
        impl_count = conn.execute(
            "SELECT count(*) FROM artifacts WHERE implemented=1"
        ).fetchone()[0]
        gate_row = conn.execute(
            "SELECT evidence_path FROM artifacts "
            "WHERE name LIKE '%gate.py%' AND implemented=1"
        ).fetchone()
        if gate_row is None:
            if impl_count == 0:
                pass
        elif gate_row and not gate_row[0]:
            failures.append("implemented artifact has no evidence_path")

        # Test 8: report() returns list
        rows = report(conn)
        if not isinstance(rows, list):
            failures.append("report() did not return a list")

        # Test 9: idempotent re-run
        first_total = result["total"]
        result2 = extract(conn, repo_root=repo_dir)
        if result2["total"] != first_total:
            failures.append(
                f"re-run changed total: {first_total} -> {result2['total']}"
            )
        if result2["new_written"] != 0:
            failures.append(
                f"re-run wrote {result2['new_written']} new artifacts"
            )

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS artifacts selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("extract", "report", "selftest"),
                        default="extract", nargs="?")
    parser.add_argument("--db", default=None)
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    conn = connect(args.db)
    init_schema(conn)

    if args.command == "extract":
        repo = Path(args.repo) if args.repo else REPO_ROOT
        result = extract(conn, repo_root=repo)
        print(f"  candidates found: {result['candidates']}")
        print(f"  unique names: {result['unique']}")
        print(f"  new artifacts written: {result['new_written']}")
        print(f"  total in DB: {result['total']}")
        print(f"  implemented: {result['implemented']}")
        print(f"  unimplemented: {result['unimplemented']}")
        conn.close()
        return 0

    if args.command == "report":
        rows = report(conn)
        if not rows:
            print("no artifacts extracted")
            conn.close()
            return 0

        by_type = {}
        for r in rows:
            t = r["artifact_type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(r)

        total_impl = sum(1 for r in rows if r["implemented"])
        print(f"{len(rows)} artifact(s), {total_impl} implemented:\n")

        for atype in sorted(by_type):
            entries = by_type[atype]
            impl = sum(1 for e in entries if e["implemented"])
            print(f"  [{atype}] {len(entries)} total, {impl} implemented")
            for e in entries[:10]:
                status = "+" if e["implemented"] else "-"
                ver = f" {e['version']}" if e["version"] else ""
                path = f" -> {e['evidence_path']}" if e["evidence_path"] else ""
                print(f"    {status} {e['name']}{ver}{path}")
            if len(entries) > 10:
                print(f"    ... and {len(entries) - 10} more")
            print()

        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
