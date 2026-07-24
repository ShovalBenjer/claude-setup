"""Retrieval/recall/context domain: context packs, vector index, session brief, jira assess.

Split out of cli.py on 2026-07-10 to shrink the monofile. Command handlers are still
wired via cli.py's build_parser (set_defaults) and eval_smoke; cli.py re-imports the
public names it still references.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from intent_control_plane.mappers import (
    event_row_to_dict,
    evidence_row_to_dict,
    intent_row_to_dict,
)
from intent_control_plane.schema import base_paths, connect, initialize
from intent_control_plane.text_index import (
    cosine,
    cwd_terms,
    dedup_key,
    latest_rows,
    rank_by_relevance_and_recency,
    recent_session_terms,
    term_vector,
    terms,
    upsert_vector,
)
from intent_control_plane.util import stable_id, utc_now


def build_context_pack(
    base_dir: Path, repo: str | None, task: str, top_k: int
) -> dict[str, Any]:
    with connect(base_dir) as conn:
        rows = conn.execute(
            "select * from events where (? is null or repo_path = ?) order by timestamp_utc desc",
            (repo, repo),
        ).fetchall()
        ranked = rank_by_relevance_and_recency(rows, task, utc_now())
        included: list[dict[str, Any]] = []
        proof: list[dict[str, Any]] = []
        constraints: list[dict[str, Any]] = []
        seen_excerpts: set[str] = set()
        for row in ranked:
            if len(included) >= top_k:
                break
            if not row["model_text"]:
                continue
            excerpt = row["model_text"][:220]
            key = dedup_key(excerpt)
            if key in seen_excerpts:
                continue  # novelty: skip a near-duplicate excerpt (entropy minimization)
            seen_excerpts.add(key)
            event_id = row["event_id"]
            intent_row = conn.execute(
                "select * from intent_cards where event_id = ?", (event_id,)
            ).fetchone()
            intent = intent_row_to_dict(intent_row) if intent_row else None
            if intent:
                proof.extend(intent["proof_required"])
                constraints.extend(intent["constraints"])
            included.append(
                {
                    "source_event_id": event_id,
                    "authority": row["authority"],
                    "reason": "relevance_recency_novelty",
                    "excerpt": excerpt,
                    "citation": row["raw_text_ref"],
                }
            )
        context_pack_id = stable_id("ctx")
        pack = {
            "context_pack_id": context_pack_id,
            "requested_by": "cli",
            "task": task,
            "repo_path": repo,
            "bead_id": None,
            "included_items": included,
            "active_constraints": constraints,
            "open_loops": [],
            "stale_risks": [],
            "proof_checklist": proof or [{"type": "explicit_verification", "required": True}],
            "routing": {
                "owner_persona": "Workflow Clerk",
                "support_personas": ["Evidence Clerk"],
                "allowed_tools": ["rtk", "git", "uv", "bun"],
            },
        }
        conn.execute(
            "insert into context_packs values (?, ?, ?, ?, ?)",
            (context_pack_id, task, repo, json.dumps(pack, sort_keys=True), utc_now()),
        )
        conn.commit()
    return pack


def context_pack(args: argparse.Namespace) -> dict[str, Any] | str:
    initialize(args.base_dir)
    pack = build_context_pack(args.base_dir, args.repo, args.task, args.top_k)
    out_path = base_paths(args.base_dir)["context_packs"] / f"{pack['context_pack_id']}.json"
    out_path.write_text(json.dumps(pack, indent=2, sort_keys=True))
    if args.format == "markdown":
        return render_context_pack_markdown(pack)
    return pack


def render_context_pack_markdown(pack: dict[str, Any]) -> str:
    lines = [
        f"# Context Pack {pack['context_pack_id']}",
        "",
        f"Task: {pack['task']}",
        f"Repo: {pack['repo_path']}",
        "",
        "## Included Items",
    ]
    lines.extend(
        f"- {item['source_event_id']}: {item['excerpt']} ({item['citation']})"
        for item in pack["included_items"]
    )
    lines.append("")
    lines.append("## Proof Checklist")
    lines.extend(f"- {item['type']} required={item['required']}" for item in pack["proof_checklist"])
    return "\n".join(lines)


def rebuild_index(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    indexed = 0
    with connect(args.base_dir) as conn:
        rows = conn.execute("select event_id, model_text from events").fetchall()
        for row in rows:
            if row["model_text"]:
                upsert_vector(
                    conn,
                    f"event:{row['event_id']}",
                    "event",
                    row["event_id"],
                    row["model_text"],
                )
                indexed += 1
        intent_rows = conn.execute("select intent_id, goal from intent_cards").fetchall()
        for row in intent_rows:
            upsert_vector(
                conn,
                f"intent:{row['intent_id']}",
                "intent",
                row["intent_id"],
                row["goal"],
            )
            indexed += 1
        conn.commit()
    return {"status": "pass", "indexed": indexed}


def vector_search(args: argparse.Namespace) -> dict[str, Any]:
    initialize(args.base_dir)
    query_vector = term_vector(args.query)
    items: list[dict[str, Any]] = []
    with connect(args.base_dir) as conn:
        rows = conn.execute(
            "select * from vector_index where (? = 'all' or item_type = ?)",
            (args.type, args.type),
        ).fetchall()
        for row in rows:
            score = cosine(query_vector, json.loads(row["vector_json"]))
            if score <= 0:
                continue
            items.append(
                {
                    "item_id": row["item_id"],
                    "item_type": row["item_type"],
                    "source_id": row["source_id"],
                    "score": round(score, 4),
                }
            )
    items.sort(key=lambda item: item["score"], reverse=True)
    return {"status": "pass", "query": args.query, "items": items[: args.limit]}


def session_brief(args: argparse.Namespace) -> dict[str, Any] | str:
    initialize(args.base_dir)
    with connect(args.base_dir) as conn:
        events = [event_row_to_dict(row) for row in latest_rows(conn, args.cwd, args.limit)]
        evidence_rows = conn.execute(
            """
            select e.* from evidence e
            join intent_cards i on i.intent_id = e.intent_id
            join events ev on ev.event_id = i.event_id
            where (? is null or ev.repo_path = ?)
            order by e.created_at_utc desc
            limit ?
            """,
            (args.cwd, args.cwd, args.limit),
        ).fetchall()
        evidence = [evidence_row_to_dict(row) for row in evidence_rows]
        beads = [
            dict(row)
            for row in conn.execute(
                """
                select * from hive_bead_refs
                where (? is null or related_repo = ?)
                order by synced_at_utc desc
                limit ?
                """,
                (args.cwd, args.cwd, args.limit),
            ).fetchall()
        ]
    jira = None
    if args.jira_digest:
        jira = jira_assess(
            argparse.Namespace(
                base_dir=args.base_dir,
                digest=args.jira_digest,
                pointer=args.jira_pointer,
                cwd=args.cwd,
                session=args.session,
                task=args.task or args.cwd or "",
                limit=4,
            )
        )
    brief = {
        "status": "pass",
        "cwd": args.cwd,
        "session_id": args.session,
        "recent_events": events,
        "recent_evidence": evidence,
        "hive_beads": beads,
        "jira": jira,
        "agent_contract": [
            "Use recent_events as the session memory before answering.",
            "Keep unrelated Jira tickets out of the active task unless the user names the key.",
            "Attach proof before claiming completion.",
        ],
    }
    if args.format == "markdown":
        return render_session_brief(brief)
    return brief


def render_session_brief(brief: dict[str, Any]) -> str:
    lines = [
        "INTENT SESSION BRIEF:",
        f"- cwd: {brief.get('cwd') or '(unknown)'}",
        f"- session: {brief.get('session_id') or '(unknown)'}",
    ]
    jira = brief.get("jira")
    if jira:
        relation = jira.get("current_ticket_relation") or {}
        marker = "related" if relation.get("related") else "unverified"
        lines.append(
            f"- jira: {jira.get('related_count', 0)} related / {jira.get('unrelated_count', 0)} unrelated; pointer {jira.get('current_ticket') or '(unset)'} is {marker}"
        )
    if brief["recent_events"]:
        lines.append("- recent intent events:")
        for event in brief["recent_events"][:5]:
            excerpt = " ".join(event["model_text"].split())[:120]
            lines.append(f"  - {event['event_type']} {event['event_id']}: {excerpt}")
    if brief["recent_evidence"]:
        lines.append("- recent evidence:")
        lines.extend(
            f"  - {evidence['status']} {evidence['evidence_type']}: {evidence['summary'][:100]}"
            for evidence in brief["recent_evidence"][:5]
        )
    if brief["hive_beads"]:
        lines.append("- hive beads:")
        lines.extend(
            f"  - #{bead['bead_id']} [{bead.get('status')}] {bead.get('title', '')[:100]}"
            for bead in brief["hive_beads"][:5]
        )
    lines.append("- contract: attach proof before completion; keep unrelated Jira out of scope.")
    return "\n".join(lines)


def jira_assess(args: argparse.Namespace) -> dict[str, Any]:
    digest_path = Path(args.digest).expanduser()
    pointer_path = Path(args.pointer).expanduser() if args.pointer else None
    digest = json.loads(digest_path.read_text()) if digest_path.exists() else {}
    tickets = list(digest.get("flagged", []))
    pointer = pointer_path.read_text().strip() if pointer_path and pointer_path.exists() else ""
    explicit_key_match = re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", args.task or "")
    explicit_key = explicit_key_match.group(0) if explicit_key_match else None
    context = terms(args.task or "")
    context.update(cwd_terms(args.cwd))
    context.update(recent_session_terms(args.base_dir, args.cwd, args.session))
    assessed = [
        assess_ticket_relation(ticket, context, explicit_key)
        for ticket in tickets
    ]
    related = [item for item in assessed if item["related"]]
    unrelated = [item for item in assessed if not item["related"]]
    pointer_relation = None
    if pointer:
        pointer_relation = next(
            (item for item in assessed if item["key"] == pointer.upper()),
            {
                "key": pointer.upper(),
                "related": bool(explicit_key and pointer.upper() == explicit_key.upper()),
                "confidence": 0.0,
                "reason": "pointer_not_in_flagged_digest",
                "matched_terms": [],
            },
        )
    action = "safe_to_use_current_pointer" if pointer_relation and pointer_relation["related"] else "ask_before_jira_write_or_time_attribution"
    if not pointer:
        action = "no_current_ticket_pointer"
    return {
        "status": "pass",
        "cwd": args.cwd,
        "session_id": args.session,
        "current_ticket": pointer,
        "current_ticket_relation": pointer_relation,
        "related_count": len(related),
        "unrelated_count": len(unrelated),
        "related_tickets": related[: args.limit],
        "unrelated_tickets": unrelated[: args.limit],
        "agent_instruction": (
            "Treat only related_tickets as current-session Jira context. "
            "Do not move, comment, or attribute time to unrelated tickets without explicit user confirmation."
        ),
        "recommended_action": action,
    }


def ticket_text(ticket: dict[str, Any]) -> str:
    pieces = [
        str(ticket.get("key", "")),
        str(ticket.get("summary", "")),
        str(ticket.get("status", "")),
        str(ticket.get("type", "")),
    ]
    pieces.extend(str(reason) for reason in ticket.get("reasons", []) if reason)
    return " ".join(pieces)


def assess_ticket_relation(
    ticket: dict[str, Any],
    context_terms: set[str],
    explicit_ticket_key: str | None,
) -> dict[str, Any]:
    key = str(ticket.get("key", "")).upper()
    haystack_terms = terms(ticket_text(ticket))
    overlap = sorted(context_terms & haystack_terms)
    key_match = bool(explicit_ticket_key and key == explicit_ticket_key.upper())
    score = len(overlap) + (6 if key_match else 0)
    related = score >= 2 or key_match
    confidence = min(0.95, 0.25 + (score * 0.12)) if related else min(0.45, score * 0.1)
    reason = "explicit_ticket_key" if key_match else "semantic_overlap" if related else "insufficient_session_overlap"
    return {
        "key": key,
        "summary": ticket.get("summary", ""),
        "status": ticket.get("status", ""),
        "related": related,
        "confidence": round(confidence, 2),
        "reason": reason,
        "matched_terms": overlap[:12],
    }
