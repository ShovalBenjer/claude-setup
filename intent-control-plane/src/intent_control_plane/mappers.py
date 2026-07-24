"""sqlite Row to dict mappers.

Split out of cli.py on 2026-07-09. Pure functions, no cli dependency.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any


def intent_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "intent_id": row["intent_id"],
        "event_id": row["event_id"],
        "goal": row["goal"],
        "constraints": json.loads(row["constraints_json"]),
        "expectations": json.loads(row["expectations_json"]),
        "affect_pressure": json.loads(row["affect_pressure_json"]),
        "proof_required": json.loads(row["proof_required_json"]),
        "decision_delta": json.loads(row["decision_delta_json"]),
        "scope": json.loads(row["scope_json"]),
        "vectors": json.loads(row["vectors_json"]),
    }


def event_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "timestamp_utc": row["timestamp_utc"],
        "actor": row["actor"],
        "session_id": row["session_id"],
        "repo_path": row["repo_path"],
        "branch": row["branch"],
        "bead_id": row["bead_id"],
        "workflow_id": row["workflow_id"],
        "raw_text_ref": row["raw_text_ref"],
        "model_text": row["model_text"],
        "redaction_state": row["redaction_state"],
        "authority": row["authority"],
        "metadata": json.loads(row["metadata_json"]),
    }


def context_pack_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(row["pack_json"])
    return data


def evidence_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "evidence_id": row["evidence_id"],
        "intent_id": row["intent_id"],
        "evidence_type": row["evidence_type"],
        "status": row["status"],
        "summary": row["summary"],
        "artifact_ref": row["artifact_ref"],
        "command": row["command"],
        "created_at_utc": row["created_at_utc"],
    }


def eval_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    details = json.loads(row["details_json"])
    return {
        "eval_id": row["eval_id"],
        "eval_type": row["eval_type"],
        "status": row["status"],
        "created_at_utc": row["created_at_utc"],
        "details": details,
    }


def binding_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "bead_id": row["bead_id"],
        "intent_id": row["intent_id"],
        "context_pack_id": row["context_pack_id"],
        "evidence_id": row["evidence_id"],
        "workflow_id": row["workflow_id"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }


def transition_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "transition_id": row["transition_id"],
        "subject_id": row["subject_id"],
        "from_state": row["from_state"],
        "to_state": row["to_state"],
        "actor": row["actor"],
        "allowed_by_contract": bool(row["allowed_by_contract"]),
        "evidence_ids": json.loads(row["evidence_ids_json"]),
        "judge_verdict_ids": json.loads(row["judge_verdict_ids_json"]),
        "reason": row["reason"],
        "created_at_utc": row["created_at_utc"],
    }


def feedback_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "ticket_id": row["ticket_id"],
        "subject_id": row["subject_id"],
        "feedback_type": row["feedback_type"],
        "source_url": row["source_url"],
        "section_heading": row["section_heading"],
        "quoted_text": row["quoted_text"],
        "surrounding_context": row["surrounding_context"],
        "note": row["note"],
        "status": row["status"],
        "actor": row["actor"],
        "evidence_ids": json.loads(row["evidence_ids_json"]),
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }
