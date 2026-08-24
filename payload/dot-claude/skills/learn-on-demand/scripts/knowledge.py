#!/usr/bin/env python3
"""Validate, index, and query a rights-aware private knowledge catalog.

Commercial books remain metadata-only unless the user creates an explicit
attestation for a local copy. Private chunks are written only to a database
under the user's home directory, never to this skill or a repository.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


CATALOG_SCHEMA = "knowledge-catalog.v1"
ATTESTATION_SCHEMA = "knowledge-attestations.v1"
RIGHTS_MODES = {
    "open_fulltext",
    "private_workspace",
    "user_owned_private",
    "metadata_only",
    "blocked",
}
SOURCE_TYPES = {
    "book",
    "official_docs",
    "standard",
    "research",
    "taxonomy",
    "local_project",
}
DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "references" / "catalog.json"
DEFAULT_DB = Path.home() / ".claude" / "private-knowledge" / "knowledge.db"
DEFAULT_MANIFEST = Path.home() / ".claude" / "private-knowledge" / "attestations.json"
TEXT_SUFFIXES = {".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)

    def text(self) -> str:
        return "\n".join(self.parts)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_catalog(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("catalog must be a JSON object")
    return data


def validate_catalog(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != CATALOG_SCHEMA:
        errors.append(f"schema_version must be {CATALOG_SCHEMA}")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return errors + ["sources must be a non-empty list"]

    seen: set[str] = set()
    for index, item in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = str(item.get("id", "")).strip()
        if not source_id:
            errors.append(f"{prefix}.id is required")
        elif source_id in seen:
            errors.append(f"duplicate source id: {source_id}")
        seen.add(source_id)

        for field in ("title", "canonical_url", "publisher_or_owner", "verified_at"):
            if not str(item.get(field, "")).strip():
                errors.append(f"{prefix}.{field} is required")
        url = str(item.get("canonical_url", ""))
        if url and not url.startswith("https://"):
            errors.append(f"{prefix}.canonical_url must use https")
        if item.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{prefix}.source_type must be one of {sorted(SOURCE_TYPES)}")
        if item.get("rights_mode") not in RIGHTS_MODES:
            errors.append(f"{prefix}.rights_mode must be one of {sorted(RIGHTS_MODES)}")
        if item.get("rights_mode") == "open_fulltext" and not item.get("license_url"):
            errors.append(f"{prefix}.license_url is required for open_fulltext")
        for field in ("domains", "topics", "intended_uses"):
            value = item.get(field)
            if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
                errors.append(f"{prefix}.{field} must be a list of non-empty strings")
        if item.get("availability") not in {"available", "announced", "evergreen", "dataset"}:
            errors.append(f"{prefix}.availability is invalid")
    return errors


def source_text(item: dict[str, Any]) -> str:
    fields: list[str] = []
    for key in ("subtitle", "edition", "summary", "selection_reason", "freshness_note"):
        value = item.get(key)
        if value:
            fields.append(str(value))
    for key in ("authors", "domains", "topics", "intended_uses", "resume_taxonomy_refs"):
        value = item.get(key, [])
        if isinstance(value, list):
            fields.extend(str(part) for part in value)
    return "\n".join(fields)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_html(raw: str) -> str:
    parser = TextExtractor()
    parser.feed(raw)
    return html.unescape(parser.text())


def extract_epub(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if name.lower().endswith((".xhtml", ".html", ".htm")):
                parts.append(extract_html(archive.read(name).decode("utf-8", errors="ignore")))
    return "\n".join(parts)


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("word/document.xml")
    root = ElementTree.fromstring(raw)
    return "\n".join(text for text in root.itertext() if text.strip())


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("PDF extraction requires the optional pypdf package") from exc
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_private_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    if suffix in {".html", ".htm"}:
        return extract_html(path.read_text(encoding="utf-8-sig", errors="replace"))
    if suffix == ".epub":
        return extract_epub(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    raise RuntimeError(f"unsupported private source type: {suffix or '<none>'}")


def chunks(text: str, size: int = 1800, overlap: int = 180) -> Iterable[str]:
    normalized = re.sub(r"[ \t]+", " ", text.replace("\x00", ""))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind("\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        piece = normalized[start:end].strip()
        if piece:
            yield piece
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        DROP TABLE IF EXISTS catalog_meta;
        DROP TABLE IF EXISTS source_meta;
        DROP TABLE IF EXISTS corpus_fts;
        CREATE TABLE catalog_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE source_meta (
            source_id TEXT PRIMARY KEY,
            metadata_json TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE corpus_fts USING fts5(
            source_id UNINDEXED,
            title,
            domains,
            topics,
            body,
            rights_mode UNINDEXED,
            source_type UNINDEXED,
            private_chunk UNINDEXED,
            tokenize='porter unicode61'
        );
        """
    )
    return connection


def load_attestations(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != ATTESTATION_SCHEMA:
        raise ValueError(f"manifest must use {ATTESTATION_SCHEMA}")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("manifest entries must be a list")
    return [entry for entry in entries if isinstance(entry, dict)]


def command_validate(args: argparse.Namespace) -> int:
    catalog = load_catalog(Path(args.catalog))
    errors = validate_catalog(catalog)
    print(json.dumps({"valid": not errors, "source_count": len(catalog.get("sources", [])), "errors": errors}, indent=2))
    return 0 if not errors else 1


def command_attest(args: argparse.Namespace) -> int:
    catalog = load_catalog(Path(args.catalog))
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError("catalog is invalid; run validate first")
    source_ids = {item["id"] for item in catalog["sources"]}
    if args.source_id not in source_ids:
        raise ValueError(f"unknown source id: {args.source_id}")
    basis = args.basis.strip()
    if len(basis) < 12:
        raise ValueError("--basis must state the ownership or private-use basis explicitly")
    source_path = Path(args.path).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"source file does not exist: {source_path}")

    manifest_path = Path(args.manifest)
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if not isinstance(manifest, dict) or manifest.get("schema_version") != ATTESTATION_SCHEMA:
            raise ValueError(f"manifest must use {ATTESTATION_SCHEMA}")
    else:
        manifest = {"schema_version": ATTESTATION_SCHEMA, "entries": []}
    entries = [
        entry
        for entry in manifest.get("entries", [])
        if not (entry.get("source_id") == args.source_id and entry.get("path") == str(source_path))
    ]
    entries.append(
        {
            "source_id": args.source_id,
            "path": str(source_path),
            "sha256": hash_file(source_path),
            "basis": basis,
            "attested_at": utc_now(),
            "private_only": True,
        }
    )
    manifest["entries"] = entries
    write_json(manifest_path, manifest)
    print(json.dumps({"attested": True, "source_id": args.source_id, "manifest": str(manifest_path)}, indent=2))
    return 0


def command_build(args: argparse.Namespace) -> int:
    catalog_path = Path(args.catalog)
    catalog = load_catalog(catalog_path)
    errors = validate_catalog(catalog)
    if errors:
        print(json.dumps({"built": False, "errors": errors}, indent=2))
        return 1

    by_id = {item["id"]: item for item in catalog["sources"]}
    connection = init_db(Path(args.db))
    metadata_rows = 0
    private_chunks = 0
    skipped: list[dict[str, str]] = []
    with connection:
        connection.executemany(
            "INSERT INTO catalog_meta(key, value) VALUES (?, ?)",
            [
                ("schema_version", CATALOG_SCHEMA),
                ("catalog_sha256", hash_file(catalog_path)),
                ("built_at", utc_now()),
            ],
        )
        for item in catalog["sources"]:
            connection.execute(
                "INSERT INTO source_meta(source_id, metadata_json) VALUES (?, ?)",
                (item["id"], json.dumps(item, ensure_ascii=False)),
            )
            connection.execute(
                """
                INSERT INTO corpus_fts(
                    source_id, title, domains, topics, body,
                    rights_mode, source_type, private_chunk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, '0')
                """,
                (
                    item["id"],
                    item["title"],
                    " ".join(item.get("domains", [])),
                    " ".join(item.get("topics", [])),
                    source_text(item),
                    item["rights_mode"],
                    item["source_type"],
                ),
            )
            metadata_rows += 1

        if args.include_private:
            for entry in load_attestations(Path(args.manifest)):
                source_id = str(entry.get("source_id", ""))
                source = by_id.get(source_id)
                source_path = Path(str(entry.get("path", "")))
                try:
                    if source is None:
                        raise RuntimeError("source id is absent from catalog")
                    if entry.get("private_only") is not True or not str(entry.get("basis", "")).strip():
                        raise RuntimeError("attestation is incomplete")
                    if not source_path.is_file():
                        raise RuntimeError("file is missing")
                    if hash_file(source_path) != entry.get("sha256"):
                        raise RuntimeError("file hash changed; re-attest before indexing")
                    text = extract_private_text(source_path)
                    for index, chunk in enumerate(chunks(text)):
                        connection.execute(
                            """
                            INSERT INTO corpus_fts(
                                source_id, title, domains, topics, body,
                                rights_mode, source_type, private_chunk
                            ) VALUES (?, ?, ?, ?, ?, 'user_owned_private', ?, '1')
                            """,
                            (
                                source_id,
                                source["title"],
                                " ".join(source.get("domains", [])),
                                " ".join(source.get("topics", [])),
                                chunk,
                                source["source_type"],
                            ),
                        )
                        private_chunks += 1
                except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
                    skipped.append({"source_id": source_id, "reason": str(exc)})
    connection.close()
    print(
        json.dumps(
            {
                "built": True,
                "db": str(Path(args.db)),
                "metadata_rows": metadata_rows,
                "private_chunks": private_chunks,
                "skipped_private_sources": skipped,
            },
            indent=2,
        )
    )
    return 0 if not skipped else 2


def command_revoke(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(json.dumps({"revoked": 0, "manifest": str(manifest_path), "private_chunks_deleted": 0}, indent=2))
        return 0
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != ATTESTATION_SCHEMA:
        raise ValueError(f"manifest must use {ATTESTATION_SCHEMA}")
    requested_path = str(Path(args.path).expanduser().resolve()) if args.path else None
    retained: list[dict[str, Any]] = []
    revoked = 0
    for entry in manifest.get("entries", []):
        matches = (
            isinstance(entry, dict)
            and entry.get("source_id") == args.source_id
            and (requested_path is None or entry.get("path") == requested_path)
        )
        if matches:
            revoked += 1
        elif isinstance(entry, dict):
            retained.append(entry)
    manifest["entries"] = retained
    write_json(manifest_path, manifest)

    deleted_chunks = 0
    db = Path(args.db)
    if db.exists():
        connection = sqlite3.connect(db)
        with connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM corpus_fts WHERE source_id = ? AND private_chunk = '1'",
                (args.source_id,),
            ).fetchone()
            deleted_chunks = int(row[0]) if row else 0
            connection.execute(
                "DELETE FROM corpus_fts WHERE source_id = ? AND private_chunk = '1'",
                (args.source_id,),
            )
        connection.close()
    print(
        json.dumps(
            {
                "revoked": revoked,
                "source_id": args.source_id,
                "manifest": str(manifest_path),
                "private_chunks_deleted": deleted_chunks,
            },
            indent=2,
        )
    )
    return 0


def fts_query(text: str) -> str:
    tokens = re.findall(r"[\w-]{2,}", text, flags=re.UNICODE)
    return " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[:24])


def indexed_catalog_sha256(db: Path) -> str | None:
    if not db.exists():
        return None
    try:
        connection = sqlite3.connect(db)
        row = connection.execute(
            "SELECT value FROM catalog_meta WHERE key = 'catalog_sha256'"
        ).fetchone()
        connection.close()
        return str(row[0]) if row else None
    except sqlite3.Error:
        return None


def command_query(args: argparse.Namespace) -> int:
    db = Path(args.db)
    catalog_path = Path(args.catalog)
    catalog_sha256 = hash_file(catalog_path)
    if indexed_catalog_sha256(db) != catalog_sha256:
        build_status = command_build(
            argparse.Namespace(
                catalog=str(catalog_path),
                db=str(db),
                manifest=args.manifest,
                include_private=Path(args.manifest).exists(),
            )
        )
        if build_status == 1:
            raise ValueError("catalog index rebuild failed")
    expression = fts_query(args.question)
    if not expression:
        raise ValueError("query must contain at least one searchable token")
    domains = {item.strip().lower() for item in (args.domain or []) if item.strip()}
    connection = sqlite3.connect(db)
    rows = connection.execute(
        """
        SELECT source_id, title, domains, topics, body, rights_mode,
               source_type, private_chunk, bm25(corpus_fts) AS score
        FROM corpus_fts
        WHERE corpus_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (expression, max(args.limit * 8, args.limit)),
    ).fetchall()
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        source_id, title, raw_domains, topics, body, rights, source_type, private, score = row
        meta_row = connection.execute(
            "SELECT metadata_json FROM source_meta WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        metadata = json.loads(meta_row[0]) if meta_row else {}
        if metadata.get("availability") == "announced" and not args.include_announced:
            continue
        domain_list = raw_domains.split()
        if domains and not domains.intersection(item.lower() for item in domain_list):
            continue
        kind = "private_chunk" if private == "1" else "metadata"
        key = (source_id, kind)
        if key in seen:
            continue
        seen.add(key)
        result: dict[str, Any] = {
            "source_id": source_id,
            "title": title,
            "domains": domain_list,
            "topics": topics.split(),
            "rights_mode": rights,
            "source_type": source_type,
            "match_kind": kind,
            "rank": score,
            "availability": metadata.get("availability"),
            "publication_date": metadata.get("publication_date"),
            "verified_at": metadata.get("verified_at"),
            "canonical_url": metadata.get("canonical_url"),
        }
        if private == "1" and args.include_private_snippets:
            result["private_snippet"] = body[: min(args.snippet_chars, 600)]
        results.append(result)
        if len(results) >= args.limit:
            break
    connection.close()
    print(json.dumps({"query": args.question, "result_count": len(results), "results": results}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    sub = root.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.set_defaults(func=command_validate)

    attest = sub.add_parser("attest")
    attest.add_argument("--source-id", required=True)
    attest.add_argument("--path", required=True)
    attest.add_argument("--basis", required=True)
    attest.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    attest.set_defaults(func=command_attest)

    build = sub.add_parser("build")
    build.add_argument("--db", default=str(DEFAULT_DB))
    build.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    build.add_argument("--include-private", action="store_true")
    build.set_defaults(func=command_build)

    revoke = sub.add_parser("revoke")
    revoke.add_argument("--source-id", required=True)
    revoke.add_argument("--path")
    revoke.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    revoke.add_argument("--db", default=str(DEFAULT_DB))
    revoke.set_defaults(func=command_revoke)

    query = sub.add_parser("query")
    query.add_argument("question")
    query.add_argument("--limit", type=int, default=8)
    query.add_argument("--domain", action="append")
    query.add_argument("--db", default=str(DEFAULT_DB))
    query.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    query.add_argument("--include-private-snippets", action="store_true")
    query.add_argument("--include-announced", action="store_true")
    query.add_argument("--snippet-chars", type=int, default=320)
    query.set_defaults(func=command_query)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
