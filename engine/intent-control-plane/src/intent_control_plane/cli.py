from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from intent_control_plane import evolution, policy, project_map
from intent_control_plane.eval_cmds import (
    eval_kappa,
    eval_passk,
    eval_tier1,
    eval_trace_diff,
)
from intent_control_plane.mappers import (
    binding_row_to_dict,
    context_pack_row_to_dict,
    eval_row_to_dict,
    event_row_to_dict,
    evidence_row_to_dict,
    feedback_row_to_dict,
    intent_row_to_dict,
    transition_row_to_dict,
)
from intent_control_plane.retrieval import (
    build_context_pack,
    context_pack,
    jira_assess,
    rebuild_index,
    session_brief,
    vector_search,
)
from intent_control_plane.schema import (
    DEFAULT_BASE_DIR,
    SCHEMA_VERSION,
    base_paths,
    connect,
    initialize,
)
from intent_control_plane.text_index import (
    cwd_terms,
    terms,
    text_hash,
)
from intent_control_plane.util import redact, stable_id, utc_now

ILLEGAL_TRANSITIONS = {
    ("GENERATED", "SHIPPED"): "generated work must be judged and verified before shipping",
    ("JUDGED_FAIL", "SHIPPED"): "failed judge verdict cannot ship",
    ("UNRELATED_JIRA", "TIME_ATTRIBUTED"): "unrelated Jira work cannot receive time attribution",
    ("ZERO_OPACITY", "REPAIRED_BY_SOFTENING"): "zero-opacity claims must be repaired from sources, not softened",
}
















@contextmanager
def _ledger_lock(ledger: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock for the duration of one ledger append.

    This is not belt-and-braces around an already-atomic append. It was added because
    the append is NOT atomic on this platform, which was measured rather than assumed:
    24 threads each appending one line through `open(path, "ab")` produced 18 lines on
    disk and a file 246 bytes shorter than the bytes handed to `write`. Six rows were
    destroyed, not misfiled. The Windows CRT implements `_O_APPEND` as a seek-to-end
    followed by a write, and the two are separable, so a second writer that seeks in
    between lands on the same offset and overwrites.

    POSIX `O_APPEND` really is atomic, so there the lock only serialises the offset
    accounting. Both platforms pay one uncontended lock per prompt, which is nothing
    next to losing a prompt.

    The lock lives on a sidecar file rather than on the ledger itself. `msvcrt.locking`
    locks a byte range starting at the current file position, and the ledger handle's
    position is owned by the append; sharing one handle between the lock and the write
    would couple two things that must not move together.
    """
    lock_path = ledger.with_name(ledger.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # `sys.platform`, not `os.name`: mypy narrows on the former and type-checks each
    # branch against the right stdlib stubs. With `os.name` it checks both branches on
    # both platforms and reports fcntl.flock as missing on Windows, which is true and
    # irrelevant, and the usual response to that noise is a blanket ignore that also
    # hides real errors.
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    # LK_LOCK blocks, but gives up after 10 retries at 1s. A prompt is
                    # worth more than 10 seconds of patience, so keep asking.
                    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    continue
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def ledger_append(base_dir: Path, event: dict[str, Any]) -> str:
    """Append one event and return `<ledger path>:<byte offset of this row>`.

    The offset replaces a line number, for two reasons that are really one reason.

    Counting lines read the entire file on every append, so capturing N prompts cost
    O(N^2) bytes read. A 587-row backfill would have paid that in full.

    Worse, the count was a read-then-write with a gap in the middle. Two writers each
    counted N and each returned N+1, so two events cited one location and at least one
    citation was false. The fix is not a lock: it is to stop predicting where the row
    will land and instead measure where it did. `O_APPEND` puts our bytes at the end
    atomically no matter who else wrote meanwhile, and `tell()` afterwards reports the
    end of OUR write, so subtracting our own byte length yields our own true start.
    Another writer's row can land before ours or after it, and neither moves us.

    Binary mode is not incidental. Text mode on Windows rewrites `\\n` as `\\r\\n`, so a
    byte offset computed against a text handle drifts by one byte per preceding row,
    and the encoded length of a non-ASCII prompt differs from its length in characters
    on every platform. Both are silent, and both make the citation point into the
    middle of a row rather than at its start.
    """
    ledger = base_paths(base_dir)["ledger"]
    ledger.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(event, sort_keys=True) + "\n").encode("utf-8")
    with _ledger_lock(ledger), ledger.open("ab") as handle:
        handle.write(payload)
        handle.flush()
        end = handle.tell()
    return f"{ledger}:{end - len(payload)}"


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    """Decode `--metadata`, rejecting anything that is not a JSON object.

    The previous code hardcoded `{}` in the event dict and the literal string `"{}"` in
    the insert. That one literal is what blocked every per-turn field the trace model
    needs: the vendor prompt id, the transcript message uuid, the causal parents, the
    text hash, the per-session sequence number.

    A malformed value fails loudly here rather than being stored as a quoted string. A
    metadata column holding `"{not json"` is worse than an empty one, because a reader
    cannot tell a corrupt row from a row that legitimately carries a string.
    """
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"capture: --metadata is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(
            f"capture: --metadata must be a JSON object, got {type(parsed).__name__}"
        )
    return parsed


def capture(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    metadata = _parse_metadata(getattr(args, "metadata", None))
    model_text, redaction_state = redact(args.text)
    event_id = stable_id("evt")
    event = {
        "event_id": event_id,
        "event_type": args.event_type,
        "timestamp_utc": utc_now(),
        "actor": args.actor,
        "session_id": args.session,
        "repo_path": args.repo,
        "branch": args.branch,
        "bead_id": args.bead,
        "workflow_id": args.workflow,
        "raw_text": args.text,
        "redaction_state": redaction_state,
        "authority": args.authority,
        "metadata": metadata,
    }
    raw_text_ref = ledger_append(args.base_dir, event)
    with connect(args.base_dir) as conn:
        conn.execute(
            """
            insert into events (
              event_id, event_type, timestamp_utc, actor, session_id, repo_path,
              branch, bead_id, workflow_id, raw_text_ref, model_text,
              redaction_state, authority, metadata_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                args.event_type,
                event["timestamp_utc"],
                args.actor,
                args.session,
                args.repo,
                args.branch,
                args.bead,
                args.workflow,
                raw_text_ref,
                model_text,
                redaction_state,
                args.authority,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        conn.commit()
    return {
        "event_id": event_id,
        "raw_text_ref": raw_text_ref,
        "model_text": model_text,
        "redaction_state": redaction_state,
    }


def load_event(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row:
    row = conn.execute("select * from events where event_id = ?", (event_id,)).fetchone()
    if row is None:
        raise SystemExit(f"event not found: {event_id}")
    return cast(sqlite3.Row, row)


def extract_goal(text: str) -> str:
    normalized = " ".join(text.strip().split())
    return normalized[:120] if normalized else "No goal text captured"


def infer_constraints(text: str) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    lower = text.lower()
    for marker in ("do not", "don't", "never", "must not"):
        if marker in lower:
            start = lower.find(marker)
            constraints.append({"text": text[start : start + 120].strip(), "hardness": "must"})
            break
    return constraints


def infer_proof(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    proof: list[dict[str, Any]] = []
    if "test" in lower:
        proof.append({"type": "test", "required": True})
    if "runtime" in lower or "smoke" in lower or "deploy" in lower:
        proof.append({"type": "runtime_smoke", "required": True})
    if "log" in lower or "trace" in lower:
        proof.append({"type": "log_or_trace", "required": False})
    if not proof:
        proof.append({"type": "explicit_verification", "required": True})
    return proof


def extract_intent(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    with connect(args.base_dir) as conn:
        event = load_event(conn, args.event)
        existing = conn.execute(
            "select * from intent_cards where event_id = ?", (args.event,)
        ).fetchone()
        if existing is not None:
            return intent_row_to_dict(existing)
        text = event["model_text"]
        intent_id = stable_id("intent")
        constraints = infer_constraints(text)
        proof_required = infer_proof(text)
        expectations = [
            {"name": "runtime_proof_required", "weight": 0.95}
            if any(item["type"] == "runtime_smoke" for item in proof_required)
            else {"name": "explicit_evidence_required", "weight": 0.75}
        ]
        card = {
            "intent_id": intent_id,
            "event_id": args.event,
            "goal": extract_goal(text),
            "constraints": constraints,
            "expectations": expectations,
            "affect_pressure": {
                "urgency": 0.5,
                "frustration": 0.0,
                "trust_deficit": 0.5 if constraints or proof_required else 0.2,
                "ambiguity": 0.5,
            },
            "proof_required": proof_required,
            "decision_delta": {"amends": [], "supersedes": [], "contradicts": []},
            "scope": {
                "repos": [event["repo_path"]] if event["repo_path"] else [],
                "files": [],
                "endpoints": [],
                "personas": [],
                "beads": [event["bead_id"]] if event["bead_id"] else [],
            },
            "vectors": {
                "intent_vector_ref": None,
                "expectation_vector_ref": None,
                "proof_vector_ref": None,
            },
        }
        conn.execute(
            """
            insert into intent_cards (
              intent_id, event_id, goal, constraints_json, expectations_json,
              affect_pressure_json, proof_required_json, decision_delta_json,
              scope_json, vectors_json, created_at_utc
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent_id,
                args.event,
                card["goal"],
                json.dumps(card["constraints"], sort_keys=True),
                json.dumps(card["expectations"], sort_keys=True),
                json.dumps(card["affect_pressure"], sort_keys=True),
                json.dumps(card["proof_required"], sort_keys=True),
                json.dumps(card["decision_delta"], sort_keys=True),
                json.dumps(card["scope"], sort_keys=True),
                json.dumps(card["vectors"], sort_keys=True),
                utc_now(),
            ),
        )
        conn.commit()
        return card


















def list_records(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    limit = args.limit
    with connect(args.base_dir) as conn:
        if args.kind == "events":
            rows = conn.execute(
                "select * from events order by timestamp_utc desc limit ?", (limit,)
            ).fetchall()
            items = [event_row_to_dict(row) for row in rows]
        elif args.kind == "intents":
            rows = conn.execute(
                "select * from intent_cards order by created_at_utc desc limit ?", (limit,)
            ).fetchall()
            items = [intent_row_to_dict(row) for row in rows]
        elif args.kind == "context-packs":
            rows = conn.execute(
                "select * from context_packs order by created_at_utc desc limit ?", (limit,)
            ).fetchall()
            items = [
                {
                    "context_pack_id": row["context_pack_id"],
                    "task": row["task"],
                    "repo_path": row["repo_path"],
                    "created_at_utc": row["created_at_utc"],
                }
                for row in rows
            ]
        elif args.kind == "evidence":
            rows = conn.execute(
                "select * from evidence order by created_at_utc desc limit ?", (limit,)
            ).fetchall()
            items = [evidence_row_to_dict(row) for row in rows]
        elif args.kind == "evals":
            rows = conn.execute(
                "select * from eval_results order by created_at_utc desc limit ?", (limit,)
            ).fetchall()
            items = [eval_row_to_dict(row) for row in rows]
        elif args.kind == "bindings":
            rows = conn.execute(
                "select * from hive_bindings order by updated_at_utc desc limit ?", (limit,)
            ).fetchall()
            items = [binding_row_to_dict(row) for row in rows]
        elif args.kind == "transitions":
            rows = conn.execute(
                "select * from state_transitions order by created_at_utc desc limit ?",
                (limit,),
            ).fetchall()
            items = [transition_row_to_dict(row) for row in rows]
        elif args.kind == "feedback":
            rows = conn.execute(
                "select * from feedback_tickets order by updated_at_utc desc limit ?",
                (limit,),
            ).fetchall()
            items = [feedback_row_to_dict(row) for row in rows]
        else:
            raise SystemExit(f"unknown list kind: {args.kind}")
    return {"kind": args.kind, "count": len(items), "items": items}


def show_record(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    with connect(args.base_dir) as conn:
        if args.kind == "event":
            row = conn.execute("select * from events where event_id = ?", (args.id,)).fetchone()
            if row is None:
                raise SystemExit(f"event not found: {args.id}")
            return event_row_to_dict(row)
        if args.kind == "intent":
            row = conn.execute(
                "select * from intent_cards where intent_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"intent not found: {args.id}")
            return intent_row_to_dict(row)
        if args.kind == "context-pack":
            row = conn.execute(
                "select * from context_packs where context_pack_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"context-pack not found: {args.id}")
            return context_pack_row_to_dict(row)
        if args.kind == "evidence":
            row = conn.execute(
                "select * from evidence where evidence_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"evidence not found: {args.id}")
            return evidence_row_to_dict(row)
        if args.kind == "eval":
            row = conn.execute(
                "select * from eval_results where eval_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"eval not found: {args.id}")
            return eval_row_to_dict(row)
        if args.kind == "binding":
            row = conn.execute(
                "select * from hive_bindings where bead_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"binding not found for bead: {args.id}")
            return binding_row_to_dict(row)
        if args.kind == "transition":
            row = conn.execute(
                "select * from state_transitions where transition_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"transition not found: {args.id}")
            return transition_row_to_dict(row)
        if args.kind == "feedback":
            row = conn.execute(
                "select * from feedback_tickets where ticket_id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"feedback ticket not found: {args.id}")
            return feedback_row_to_dict(row)
    raise SystemExit(f"unknown show kind: {args.kind}")


















def foundry_status(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    env_names = {
        "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
        "azure_openai_api_key": "AZURE_OPENAI_API_KEY",
        "azure_openai_deployment": "AZURE_OPENAI_DEPLOYMENT",
        "azure_ai_foundry_endpoint": "AZURE_AI_FOUNDRY_ENDPOINT",
        "azure_ai_foundry_project": "AZURE_AI_FOUNDRY_PROJECT",
    }
    present = {name: bool(os.environ.get(env)) for name, env in env_names.items()}
    ready_for_redacted_calls = (
        (present["azure_openai_endpoint"] and present["azure_openai_deployment"])
        or present["azure_ai_foundry_endpoint"]
    )
    if args.record:
        with connect(args.base_dir) as conn:
            conn.execute(
                """
                insert into foundry_calls (
                  call_id, endpoint_class, deployment, prompt_hash, output_hash,
                  redaction_state, token_input, token_output, created_at_utc
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stable_id("foundry"),
                    "readiness",
                    os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
                    None,
                    text_hash(json.dumps(present, sort_keys=True)),
                    "no_payload",
                    0,
                    0,
                    utc_now(),
                ),
            )
            conn.commit()
    return {
        "status": "pass" if ready_for_redacted_calls else "not_configured",
        "mode": "local_only_until_enabled",
        "env_present": present,
        "policy": "Never upload raw prompts; only redacted model_text or derived vectors may leave local storage.",
    }


def hive_sync(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    hive_db = Path(args.db).expanduser()
    if not hive_db.exists():
        raise SystemExit(f"hive db not found: {hive_db}")
    context = cwd_terms(args.cwd)
    context.update(terms(args.rig or ""))
    synced = 0
    related = 0
    source = sqlite3.connect(hive_db)
    source.row_factory = sqlite3.Row
    try:
        rows = source.execute(
            """
            select id, rig, title, status, priority, owner_role, claimed_by
            from beads
            where (? is null or rig = ?)
            order by updated_at desc
            limit ?
            """,
            (args.rig, args.rig, args.limit),
        ).fetchall()
    finally:
        source.close()
    with connect(args.base_dir) as conn:
        for row in rows:
            overlap = sorted(context & terms(f"{row['rig']} {row['title']} {row['owner_role'] or ''}"))
            is_related = len(overlap) >= 1 if args.rig else len(overlap) >= 2
            if is_related:
                related += 1
            relation = {
                "related": is_related,
                "matched_terms": overlap[:12],
                "reason": "rig_or_repo_overlap" if is_related else "insufficient_overlap",
            }
            conn.execute(
                """
                insert or replace into hive_bead_refs (
                  bead_id, rig, title, status, priority, owner_role, claimed_by,
                  source_db, related_repo, relation_json, synced_at_utc
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["id"]),
                    row["rig"],
                    row["title"],
                    row["status"],
                    row["priority"],
                    row["owner_role"],
                    row["claimed_by"],
                    str(hive_db),
                    args.cwd if is_related else None,
                    json.dumps(relation, sort_keys=True),
                    utc_now(),
                ),
            )
            synced += 1
        conn.commit()
    return {"status": "pass", "synced": synced, "related": related, "db": str(hive_db)}


def retention_sweep(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    cutoff = datetime.now(UTC) - timedelta(days=args.days)
    paths = base_paths(args.base_dir)
    removed_files: list[str] = []
    candidate_files = [
        path
        for folder in (paths["context_packs"], paths["reports"], paths["replay"], paths["mutants"])
        for path in folder.glob("*")
        if path.is_file()
        and datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff
    ]
    if not args.dry_run:
        for path in candidate_files:
            path.unlink()
            removed_files.append(str(path))
    else:
        removed_files = [str(path) for path in candidate_files]
    run = {
        "status": "pass",
        "dry_run": args.dry_run,
        "days": args.days,
        "candidate_count": len(candidate_files),
        "files": removed_files[:50],
        "policy": "Raw prompt ledger is append-only; retention only sweeps generated artifacts.",
    }
    with connect(args.base_dir) as conn:
        conn.execute(
            "insert into retention_runs values (?, ?, ?, ?, ?)",
            (
                stable_id("ret"),
                1 if args.dry_run else 0,
                args.days,
                json.dumps(run, sort_keys=True),
                utc_now(),
            ),
        )
        conn.commit()
    return run


def attach_evidence(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    artifact_text = ""
    if args.artifact and Path(args.artifact).exists():
        artifact_text = Path(args.artifact).read_text(errors="replace")[:500]
    evidence_id = stable_id("ev")
    summary = args.summary or artifact_text.strip() or f"{args.type} {args.status}"
    payload = {
        "evidence_id": evidence_id,
        "intent_id": args.intent,
        "evidence_type": args.type,
        "status": args.status,
        "summary": summary,
        "artifact_ref": args.artifact,
        "command": args.command,
        "created_at_utc": utc_now(),
    }
    with connect(args.base_dir) as conn:
        conn.execute(
            "insert into evidence values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence_id,
                args.intent,
                args.type,
                args.status,
                summary,
                args.artifact,
                args.command,
                payload["created_at_utc"],
            ),
        )
        conn.commit()
    return payload


def eval_smoke(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    golden_dir = base_paths(args.base_dir)["golden"]
    fixture_paths = sorted(golden_dir.glob("*.json"))
    cases: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    for fixture_path in fixture_paths:
        fixture = json.loads(fixture_path.read_text())
        pack = build_context_pack(
            args.base_dir,
            fixture.get("repo_path"),
            fixture["task"],
            fixture.get("top_k", args.top_k),
        )
        retrieved = {item["source_event_id"] for item in pack["included_items"]}
        expected = set(fixture.get("expected_event_ids", []))
        missing = sorted(expected - retrieved)
        case_status = "pass" if not missing else "fail"
        if case_status == "pass":
            passed += 1
        else:
            failed += 1
        cases.append(
            {
                "case_id": fixture.get("case_id", fixture_path.stem),
                "status": case_status,
                "task": fixture["task"],
                "repo_path": fixture.get("repo_path"),
                "expected_event_ids": sorted(expected),
                "retrieved_event_ids": sorted(retrieved),
                "missing_event_ids": missing,
                "context_pack_id": pack["context_pack_id"],
            }
        )
    status = "pass" if failed == 0 else "fail"
    report = {
        "status": status,
        "eval_type": "smoke",
        "fixture_count": len(fixture_paths),
        "passed": passed,
        "failed": failed,
        "cases": cases,
    }
    eval_id = stable_id("eval")
    with connect(args.base_dir) as conn:
        conn.execute(
            "insert into eval_results values (?, ?, ?, ?, ?)",
            (eval_id, "smoke", status, json.dumps(report, sort_keys=True), utc_now()),
        )
        conn.commit()
    report["eval_id"] = eval_id
    return report


def hive_bind(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    now = utc_now()
    with connect(args.base_dir) as conn:
        existing = conn.execute(
            "select created_at_utc from hive_bindings where bead_id = ?", (args.bead,)
        ).fetchone()
        created_at = existing["created_at_utc"] if existing else now
        conn.execute(
            """
            insert or replace into hive_bindings (
              bead_id, intent_id, context_pack_id, evidence_id, workflow_id,
              created_at_utc, updated_at_utc
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                args.bead,
                args.intent,
                args.context_pack,
                args.evidence,
                args.workflow,
                created_at,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "select * from hive_bindings where bead_id = ?", (args.bead,)
        ).fetchone()
    return binding_row_to_dict(row)


def transition_block_reason(
    from_state: str,
    to_state: str,
    evidence_ids: list[str],
) -> str | None:
    direct_reason = ILLEGAL_TRANSITIONS.get((from_state, to_state))
    if direct_reason:
        return direct_reason
    if from_state.startswith("BLOCKED_") and to_state == "CLOSED_VERIFIED" and not evidence_ids:
        return "blocked work needs new evidence before it can close verified"
    return None


def record_transition(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    evidence_ids = list(args.evidence or [])
    judge_verdict_ids = list(args.verdict or [])
    block_reason = transition_block_reason(args.from_state, args.to_state, evidence_ids)
    if block_reason:
        raise SystemExit(
            f"illegal transition: {args.from_state} -> {args.to_state}: {block_reason}"
        )

    transition_id = stable_id("st")
    with connect(args.base_dir) as conn:
        conn.execute(
            """
            insert into state_transitions (
              transition_id, subject_id, from_state, to_state, actor,
              allowed_by_contract, evidence_ids_json, judge_verdict_ids_json,
              reason, created_at_utc
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transition_id,
                args.subject,
                args.from_state,
                args.to_state,
                args.actor,
                1,
                json.dumps(evidence_ids, sort_keys=True),
                json.dumps(judge_verdict_ids, sort_keys=True),
                args.reason,
                utc_now(),
            ),
        )
        conn.commit()
        row = conn.execute(
            "select * from state_transitions where transition_id = ?",
            (transition_id,),
        ).fetchone()
    return transition_row_to_dict(row)


def add_feedback(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    ticket_id = stable_id("fb")
    now = utc_now()
    with connect(args.base_dir) as conn:
        conn.execute(
            """
            insert into feedback_tickets (
              ticket_id, subject_id, feedback_type, source_url, section_heading,
              quoted_text, surrounding_context, note, status, actor,
              evidence_ids_json, created_at_utc, updated_at_utc
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                args.subject,
                args.type,
                args.source_url,
                args.section,
                args.quote,
                args.context,
                args.note,
                "todo",
                args.actor,
                "[]",
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "select * from feedback_tickets where ticket_id = ?",
            (ticket_id,),
        ).fetchone()
    return feedback_row_to_dict(row)


def update_feedback(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    with connect(args.base_dir) as conn:
        row = conn.execute(
            "select * from feedback_tickets where ticket_id = ?",
            (args.ticket,),
        ).fetchone()
        if row is None:
            raise SystemExit(f"feedback ticket not found: {args.ticket}")
        evidence_ids = json.loads(row["evidence_ids_json"])
        for evidence_id in args.evidence or []:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
        if args.status == "done" and not evidence_ids:
            raise SystemExit("feedback ticket cannot be done without evidence")
        conn.execute(
            """
            update feedback_tickets
            set status = ?, evidence_ids_json = ?, updated_at_utc = ?
            where ticket_id = ?
            """,
            (
                args.status,
                json.dumps(evidence_ids, sort_keys=True),
                utc_now(),
                args.ticket,
            ),
        )
        conn.commit()
        updated = conn.execute(
            "select * from feedback_tickets where ticket_id = ?",
            (args.ticket,),
        ).fetchone()
    return feedback_row_to_dict(updated)


def doctor(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    paths = base_paths(args.base_dir)
    checks: dict[str, bool] = {
        "sqlite_exists": paths["db"].exists(),
        "ledger_appendable": paths["ledger"].exists() and paths["ledger"].parent.is_dir(),
        "context_pack_dir": paths["context_packs"].is_dir(),
        "foundry_or_local_only": True,
        "redaction_smoke": redact("sk-proj-abc123 SECRET_TOKEN=oops")[1]
        == "redacted_for_model",
    }
    try:
        with connect(args.base_dir) as conn:
            version = conn.execute(
                "select value from schema_meta where key = 'schema_version'"
            ).fetchone()
            checks["schema_current"] = bool(version and version["value"] == str(SCHEMA_VERSION))
    except sqlite3.Error:
        checks["schema_current"] = False
    status = "pass" if all(checks.values()) else "fail"
    return {"status": status, "base_dir": str(args.base_dir), "checks": checks}


def init_command(args: argparse.Namespace) -> dict[str, Any]:
    return initialize(args.base_dir)


def output(value: dict[str, Any] | str) -> None:
    if isinstance(value, str):
        print(value)
        return
    print(json.dumps(value, sort_keys=True))


def repo_map(args: argparse.Namespace) -> dict[str, Any] | str:
    """Scan a projects root into a repo map (markdown or json).

    Wires project_map, previously reachable only via `python -m ...project_map`, into the
    `intent` CLI so the repo-estate map is a first-class, hook-callable subcommand.
    """
    root = Path(args.root).expanduser() if args.root else Path.home() / "projects"
    records = project_map.scan_projects(root)
    if args.format == "json":
        return {"root": str(root), "count": len(records), "records": records}
    return project_map.render_markdown(records)


SKILL_USAGE_DB = Path.home() / ".claude" / "cache" / "sessions.db"


def parse_skill_event(payload: dict[str, Any]) -> dict[str, str] | None:
    """Pure: extract {skill, session} from a PostToolUse payload if it is a Skill invocation.

    Returns None for non-Skill tools or a missing skill name, so the logger stays silent on
    everything that is not a real skill call.
    """
    tool = payload.get("tool_name") or payload.get("toolName") or ""
    if tool != "Skill":
        return None
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    skill = tool_input.get("skill") if isinstance(tool_input, dict) else None
    if not skill:
        return None
    session = payload.get("session_id") or payload.get("sessionId") or "unknown"
    return {"skill": str(skill), "session": str(session)}


def _write_skill_event(db: Path, session: str, skill: str) -> None:
    """Insert one skill_invoke row, creating the parent dir and table if the DB is fresh."""
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute(
        "create table if not exists session_events ("
        " id integer primary key autoincrement, session_id text not null,"
        " fired_at text not null, event_type text not null, detail text)"
    )
    conn.execute(
        "insert into session_events(session_id, fired_at, event_type, detail)"
        " values (?, ?, 'skill_invoke', ?)",
        (session, utc_now(), skill),
    )
    conn.commit()
    conn.close()


def log_skill(args: argparse.Namespace) -> dict[str, Any]:
    """Record a skill invocation into sessions.db session_events (feeds usage-ranked routing).

    Populates the skill_invoke event_type the Layer-7 schema defined but never wired. Fails
    closed with a status on any sqlite error rather than raising into the hook.
    """
    db = Path(args.db).expanduser() if getattr(args, "db", None) else SKILL_USAGE_DB
    session = args.session or "unknown"
    try:
        _write_skill_event(db, session, args.skill)
    except sqlite3.Error as exc:
        return {"status": "error", "error": str(exc), "skill": args.skill}
    return {"status": "logged", "skill": args.skill, "session": session}


def _nonneg_int(value: str) -> int:
    """argparse type: reject negative counts so bad telemetry cannot skew the bandit stats."""
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def policy_stats(args: argparse.Namespace) -> dict[str, Any]:
    """Per-strategy telemetry aggregates (n, pass_rate, avg tokens/latency)."""
    try:
        lines = policy.TELEMETRY_LOG.read_text(errors="ignore").splitlines()
    except OSError:
        lines = []
    return policy.strategy_stats(lines)


def policy_recommend(args: argparse.Namespace) -> dict[str, Any]:
    """Cost-aware Thompson recommendation over the known strategies, plus the stats it used.

    With --task-type, the stats are isolated to that kind of task, so the recommendation answers
    "which strategy wins for refactors" rather than the global average.
    """
    try:
        lines = policy.TELEMETRY_LOG.read_text(errors="ignore").splitlines()
    except OSError:
        lines = []
    task_type = getattr(args, "task_type", None)
    stats = policy.strategy_stats(lines, task_type=task_type)
    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    recommended = policy.recommend_strategy(
        stats, rng, candidates=list(policy.STRATEGIES), lam=args.lam, mu=args.mu
    )
    return {"recommended": recommended, "task_type": task_type or "all", "stats": stats}


def policy_table(args: argparse.Namespace) -> dict[str, Any]:
    """The cross-tab readout: which strategy wins for which kind of task (analysis over time)."""
    try:
        lines = policy.TELEMETRY_LOG.read_text(errors="ignore").splitlines()
    except OSError:
        lines = []
    return {"by_task_type": policy.strategy_by_task_type(lines)}


def telemetry_record(args: argparse.Namespace) -> dict[str, Any]:
    """Append one strategy-outcome row to the telemetry ledger (closes the data loop)."""
    row = policy.telemetry_row(
        args.strategy,
        args.status,
        args.task,
        subagent_tokens=args.tokens,
        duration_ms=args.ms,
        agent_count=args.agents,
        run_id=args.run_id,
        note=args.note,
        task_type=args.task_type,
    )
    policy.append_telemetry(row)
    return {"status": "recorded", "row": row}


def evolve(args: argparse.Namespace) -> dict[str, Any]:
    """Score the golden set, compare to the last baseline, record the delta (measure weekly)."""
    report = eval_smoke(argparse.Namespace(base_dir=args.base_dir, top_k=args.top_k))
    return evolution.run_evolution(args.base_dir, report)


def retrieve(args: argparse.Namespace) -> dict[str, Any]:
    """Typed retrieval over the ~/docs corpus: name + path + content snippet per hit.

    The docs-to-contract surface: reuses the router's FTS corpus so ~/docs is a first-class,
    queryable tool (not just a per-turn hook side effect).
    """
    from intent_control_plane.harness.router import CORPUS_DB, corpus_snippets

    db = Path(args.db).expanduser() if args.db else CORPUS_DB
    hits = corpus_snippets(args.query.lower(), db, limit=args.k)
    return {"query": args.query, "count": len(hits), "hits": hits}


def hud(args: argparse.Namespace) -> dict[str, Any]:
    """Compute brain fields for the statusline HUD and cache them for a fast render.

    Estate score + gap count (standards.score_repo) and the strategy recommendation are the
    slow-ish reads; caching them to ~/.claude/cache/hud.json lets the per-turn statusline read
    a small JSON instead of recomputing. Everything fails open to a dash, never crashes a hook.
    """
    from intent_control_plane import standards

    cwd = Path(args.cwd).expanduser() if args.cwd else Path.cwd()
    estate, gaps = "-", 0
    try:
        record = standards.score_repo(cwd)
        estate = str(record.get("score", "-"))
        gaps = sum(
            1 for d in record.get("dimensions", {}).values() if d.get("passed", 0) < d.get("total", 0)
        )
    except Exception:
        pass
    strategy, pass_rate = "-", 0.0
    try:
        stats = policy.strategy_stats(policy.TELEMETRY_LOG.read_text(errors="ignore").splitlines())
        strategy = policy.recommend_strategy(stats, random.Random(), candidates=list(policy.STRATEGIES))
        pass_rate = float(stats.get(strategy, {}).get("pass_rate", 0.0))
    except Exception:
        pass
    data: dict[str, Any] = {
        "repo": cwd.name,
        "estate": estate,
        "gaps": gaps,
        "strategy": strategy,
        "strategy_pass": round(pass_rate, 2),
        "updated_at": utc_now(),
    }
    out = Path(args.out).expanduser() if args.out else Path.home() / ".claude" / "cache" / "hud.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(out)  # atomic swap so the statusline never reads a truncated cache
    except OSError:
        pass  # the HUD cache is best-effort; a write failure must never crash the statusline hook
    return data


def gastown_list(args: argparse.Namespace) -> dict[str, Any]:
    """List the Gastown personas (name, role, skill count) parsed from the registry."""
    from intent_control_plane import gastown

    registry = Path(args.registry).expanduser() if args.registry else gastown.REGISTRY
    try:
        text = registry.read_text()
    except OSError as exc:
        raise SystemExit(f"gastown: cannot read registry {registry}: {exc}") from exc
    personas = gastown.parse_registry(text)
    return {
        "count": len(personas),
        "personas": [
            {"name": p["name"], "role": p["role"], "skills": len(p["skills"])} for p in personas
        ],
    }


def gastown_spec(args: argparse.Namespace) -> dict[str, Any]:
    """Emit a persona's spawnable agent-spec (system_prompt charter + allowed skills)."""
    from intent_control_plane import gastown

    registry = Path(args.registry).expanduser() if args.registry else gastown.REGISTRY
    try:
        text = registry.read_text()
    except OSError as exc:
        raise SystemExit(f"gastown: cannot read registry {registry}: {exc}") from exc
    personas = gastown.parse_registry(text)
    persona = gastown.find_persona(personas, args.persona)
    if persona is None:
        raise SystemExit(f"gastown: persona not found: {args.persona}")
    return gastown.persona_spec(persona)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intent")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.set_defaults(func=init_command)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--event-type", required=True)
    capture_parser.add_argument("--session")
    capture_parser.add_argument("--repo")
    capture_parser.add_argument("--branch")
    capture_parser.add_argument("--bead")
    capture_parser.add_argument("--workflow")
    capture_parser.add_argument("--actor", default="shoval")
    capture_parser.add_argument("--authority", default="raw_user_prompt")
    capture_parser.add_argument("--text", required=True)
    capture_parser.add_argument(
        "--metadata",
        help="JSON object stored on the event: prompt_id, message_uuid, parents, "
             "text_sha, seq, cwd. Must decode to an object.",
    )
    capture_parser.set_defaults(func=capture)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--event", required=True)
    extract_parser.set_defaults(func=extract_intent)

    context_parser = subparsers.add_parser("context-pack")
    context_parser.add_argument("--repo")
    context_parser.add_argument("--task", required=True)
    context_parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    context_parser.add_argument("--top-k", type=int, default=30)
    context_parser.set_defaults(func=context_pack)

    evidence_parser = subparsers.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    attach_parser = evidence_sub.add_parser("attach")
    attach_parser.add_argument("--intent", required=True)
    attach_parser.add_argument("--type", required=True)
    attach_parser.add_argument("--status", choices=["pass", "fail", "blocked"], required=True)
    attach_parser.add_argument("--artifact")
    attach_parser.add_argument("--command")
    attach_parser.add_argument("--summary")
    attach_parser.set_defaults(func=attach_evidence)

    eval_parser = subparsers.add_parser("eval")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", required=True)
    smoke_parser = eval_sub.add_parser("smoke")
    smoke_parser.add_argument("--top-k", type=int, default=30)
    smoke_parser.set_defaults(func=eval_smoke)
    for _name, _fn in (
        ("passk", eval_passk),
        ("kappa", eval_kappa),
        ("trace-diff", eval_trace_diff),
        ("tier1", eval_tier1),
    ):
        _p = eval_sub.add_parser(_name)
        _p.add_argument("--file", required=True, help="JSON input describing the eval")
        _p.set_defaults(func=_fn)

    index_parser = subparsers.add_parser("index")
    index_sub = index_parser.add_subparsers(dest="index_command", required=True)
    rebuild_parser = index_sub.add_parser("rebuild")
    rebuild_parser.set_defaults(func=rebuild_index)
    search_parser = index_sub.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--type", choices=["all", "event", "intent"], default="all")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.set_defaults(func=vector_search)

    session_parser = subparsers.add_parser("session")
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)
    brief_parser = session_sub.add_parser("brief")
    brief_parser.add_argument("--cwd")
    brief_parser.add_argument("--session")
    brief_parser.add_argument("--task", default="")
    brief_parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    brief_parser.add_argument("--limit", type=int, default=8)
    brief_parser.add_argument("--jira-digest")
    brief_parser.add_argument("--jira-pointer")
    brief_parser.set_defaults(func=session_brief)

    foundry_parser = subparsers.add_parser("foundry")
    foundry_sub = foundry_parser.add_subparsers(dest="foundry_command", required=True)
    status_parser = foundry_sub.add_parser("status")
    status_parser.add_argument("--record", action="store_true")
    status_parser.set_defaults(func=foundry_status)

    hive_parser = subparsers.add_parser("hive")
    hive_sub = hive_parser.add_subparsers(dest="hive_command", required=True)
    bind_parser = hive_sub.add_parser("bind")
    bind_parser.add_argument("--bead", required=True)
    bind_parser.add_argument("--intent", required=True)
    bind_parser.add_argument("--context-pack")
    bind_parser.add_argument("--evidence")
    bind_parser.add_argument("--workflow")
    bind_parser.set_defaults(func=hive_bind)
    sync_parser = hive_sub.add_parser("sync")
    sync_parser.add_argument("--db", default=str(Path.home() / ".hive" / "beads.db"))
    sync_parser.add_argument("--rig")
    sync_parser.add_argument("--cwd")
    sync_parser.add_argument("--limit", type=int, default=50)
    sync_parser.set_defaults(func=hive_sync)

    state_parser = subparsers.add_parser("state")
    state_sub = state_parser.add_subparsers(dest="state_command", required=True)
    transition_parser = state_sub.add_parser("transition")
    transition_parser.add_argument("--subject", required=True)
    transition_parser.add_argument("--from-state", required=True)
    transition_parser.add_argument("--to-state", required=True)
    transition_parser.add_argument("--actor", required=True)
    transition_parser.add_argument("--evidence", action="append", default=[])
    transition_parser.add_argument("--verdict", action="append", default=[])
    transition_parser.add_argument("--reason")
    transition_parser.set_defaults(func=record_transition)

    feedback_parser = subparsers.add_parser("feedback")
    feedback_sub = feedback_parser.add_subparsers(dest="feedback_command", required=True)
    feedback_add_parser = feedback_sub.add_parser("add")
    feedback_add_parser.add_argument("--subject", required=True)
    feedback_add_parser.add_argument(
        "--type",
        choices=["rca", "architecture", "spec", "ui", "proof", "bug", "copy"],
        required=True,
    )
    feedback_add_parser.add_argument("--source-url")
    feedback_add_parser.add_argument("--section")
    feedback_add_parser.add_argument("--quote")
    feedback_add_parser.add_argument("--context")
    feedback_add_parser.add_argument("--note", required=True)
    feedback_add_parser.add_argument("--actor", default="shoval")
    feedback_add_parser.set_defaults(func=add_feedback)
    feedback_update_parser = feedback_sub.add_parser("update")
    feedback_update_parser.add_argument("--ticket", required=True)
    feedback_update_parser.add_argument(
        "--status",
        choices=["todo", "in-progress", "done", "blocked"],
        required=True,
    )
    feedback_update_parser.add_argument("--evidence", action="append", default=[])
    feedback_update_parser.set_defaults(func=update_feedback)

    jira_parser = subparsers.add_parser("jira")
    jira_sub = jira_parser.add_subparsers(dest="jira_command", required=True)
    assess_parser = jira_sub.add_parser("assess")
    assess_parser.add_argument("--digest", required=True)
    assess_parser.add_argument("--pointer")
    assess_parser.add_argument("--cwd")
    assess_parser.add_argument("--session")
    assess_parser.add_argument("--task", default="")
    assess_parser.add_argument("--limit", type=int, default=6)
    assess_parser.set_defaults(func=jira_assess)

    retention_parser = subparsers.add_parser("retention")
    retention_sub = retention_parser.add_subparsers(dest="retention_command", required=True)
    sweep_parser = retention_sub.add_parser("sweep")
    sweep_parser.add_argument("--days", type=int, default=30)
    sweep_parser.add_argument("--dry-run", action="store_true")
    sweep_parser.set_defaults(func=retention_sweep)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.set_defaults(func=doctor)

    repo_map_parser = subparsers.add_parser("repo-map")
    repo_map_parser.add_argument("root", nargs="?", default=None)
    repo_map_parser.add_argument("--format", choices=["md", "json"], default="md")
    repo_map_parser.set_defaults(func=repo_map)

    log_skill_parser = subparsers.add_parser("log-skill")
    log_skill_parser.add_argument("--skill", required=True)
    log_skill_parser.add_argument("--session", default=None)
    log_skill_parser.add_argument("--db", default=None)
    log_skill_parser.set_defaults(func=log_skill)

    policy_parser = subparsers.add_parser("policy")
    policy_sub = policy_parser.add_subparsers(dest="policy_cmd", required=True)
    policy_sub.add_parser("stats").set_defaults(func=policy_stats)
    policy_sub.add_parser("table").set_defaults(func=policy_table)
    policy_rec = policy_sub.add_parser("recommend")
    policy_rec.add_argument("--lam", type=float, default=0.15, help="token-cost weight")
    policy_rec.add_argument("--mu", type=float, default=0.05, help="latency weight")
    policy_rec.add_argument("--seed", type=int, default=None, help="seed the sampler (determinism)")
    policy_rec.add_argument("--task-type", dest="task_type", default=None, help="isolate one kind of task")
    policy_rec.set_defaults(func=policy_recommend)

    telemetry_parser = subparsers.add_parser("telemetry")
    telemetry_sub = telemetry_parser.add_subparsers(dest="telemetry_cmd", required=True)
    tel_rec = telemetry_sub.add_parser("record")
    tel_rec.add_argument("--strategy", required=True, choices=list(policy.STRATEGIES))
    tel_rec.add_argument("--status", required=True, choices=["green", "red", "timeout"])
    tel_rec.add_argument("--task", required=True)
    tel_rec.add_argument("--tokens", type=_nonneg_int, default=0)
    tel_rec.add_argument("--ms", type=_nonneg_int, default=None)
    tel_rec.add_argument("--agents", type=_nonneg_int, default=1)
    tel_rec.add_argument("--run-id", dest="run_id", default=None)
    tel_rec.add_argument("--note", default="")
    tel_rec.add_argument("--task-type", dest="task_type", default="general", help="refactor/bugfix/feature/docs/wiring")
    tel_rec.set_defaults(func=telemetry_record)

    retrieve_parser = subparsers.add_parser("retrieve")
    retrieve_parser.add_argument("--query", required=True)
    retrieve_parser.add_argument("--k", type=int, default=3)
    retrieve_parser.add_argument("--db", default=None)
    retrieve_parser.set_defaults(func=retrieve)

    evolve_parser = subparsers.add_parser("evolve")
    evolve_parser.add_argument("--top-k", type=int, default=30)
    evolve_parser.set_defaults(func=evolve)

    hud_parser = subparsers.add_parser("hud")
    hud_parser.add_argument("--cwd", default=None)
    hud_parser.add_argument("--out", default=None)
    hud_parser.set_defaults(func=hud)

    gastown_parser = subparsers.add_parser("gastown")
    gastown_sub = gastown_parser.add_subparsers(dest="gastown_cmd", required=True)
    gl = gastown_sub.add_parser("list")
    gl.add_argument("--registry", default=None)
    gl.set_defaults(func=gastown_list)
    gs = gastown_sub.add_parser("spec")
    gs.add_argument("persona")
    gs.add_argument("--registry", default=None)
    gs.set_defaults(func=gastown_spec)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument(
        "kind",
        choices=[
            "events",
            "intents",
            "context-packs",
            "evidence",
            "evals",
            "bindings",
            "transitions",
            "feedback",
        ],
    )
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(func=list_records)

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument(
        "kind",
        choices=[
            "event",
            "intent",
            "context-pack",
            "evidence",
            "eval",
            "binding",
            "transition",
            "feedback",
        ],
    )
    show_parser.add_argument("id")
    show_parser.set_defaults(func=show_record)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 2
        raise
    output(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
