"""Persistence layer: base paths, sqlite connection, schema DDL.

Split out of cli.py on 2026-07-09 to shrink the monofile. Public names are
re-imported by cli.py so existing call sites and importers keep working.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_BASE_DIR = Path.home() / ".intent"
SCHEMA_VERSION = 3


def base_paths(base_dir: Path) -> dict[str, Path]:
    return {
        "base": base_dir,
        "config": base_dir / "config.toml",
        "db": base_dir / "intent.db",
        "ledger": base_dir / "ledger" / "events.jsonl",
        "context_packs": base_dir / "context-packs",
        "golden": base_dir / "evals" / "golden",
        "replay": base_dir / "evals" / "replay",
        "mutants": base_dir / "evals" / "mutants",
        "reports": base_dir / "evals" / "reports",
        "logs": base_dir / "logs",
        "indexes_lexical": base_dir / "indexes" / "lexical",
        "indexes_vector": base_dir / "indexes" / "vector",
    }


class _ClosingConnection(sqlite3.Connection):
    """A connection whose `with` block releases the file, not just the transaction.

    `sqlite3.Connection.__exit__` commits or rolls back and deliberately leaves the
    handle open. That is correct for the stdlib and wrong for every call site in this
    package: all 24 of them are `with connect(base_dir) as conn:` and not one of them
    closes afterwards, so each read as if it released the database and none did.

    On Linux nothing shows, because unlink succeeds on an open file. On Windows the
    file stays locked, which is how this surfaced: two tests failed in TEARDOWN with
    WinError 32 on `beads.db` and `intent.db`, long after their assertions had passed.
    The leak was never Windows-specific; only the symptom was.

    The contract narrows to "the with-block owns the connection". A caller that needs
    the handle to outlive a transaction takes a bare `connect()` and closes it itself,
    which is what transitions.py already does around its BEGIN IMMEDIATE.
    """

    def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        # close() in a finally, so a commit that itself fails still releases the file
        # rather than turning one error into two.
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def connect(base_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(base_paths(base_dir)["db"], factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(base_dir: Path) -> dict[str, Any]:
    paths = base_paths(base_dir)
    for key, path in paths.items():
        if key in {"config", "db", "ledger"}:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
    if not paths["config"].exists():
        paths["config"].write_text(
            "\n".join(
                [
                    "[storage]",
                    f'base_dir = "{base_dir}"',
                    f'sqlite_path = "{paths["db"]}"',
                    f'raw_ledger = "{paths["ledger"]}"',
                    "",
                    "[foundry]",
                    "enabled = false",
                    'mode = "local_only"',
                    "",
                    "[privacy]",
                    'default_upload_policy = "redacted_only"',
                    "store_raw_local_only = true",
                    "",
                    "[eval]",
                    "llm_judge_sample_rate = 0.05",
                    "",
                ]
            )
        )
    paths["ledger"].touch(exist_ok=True)
    with connect(base_dir) as conn:
        apply_schema(conn)
    return {"status": "initialized", "base_dir": str(base_dir), "schema_version": SCHEMA_VERSION}


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists schema_meta (
          key text primary key,
          value text not null
        );
        create table if not exists events (
          event_id text primary key,
          event_type text not null,
          timestamp_utc text not null,
          actor text not null,
          session_id text,
          repo_path text,
          branch text,
          bead_id text,
          workflow_id text,
          raw_text_ref text not null,
          model_text text not null,
          redaction_state text not null,
          authority text not null,
          metadata_json text not null
        );
        create table if not exists intent_cards (
          intent_id text primary key,
          event_id text not null references events(event_id),
          goal text not null,
          constraints_json text not null,
          expectations_json text not null,
          affect_pressure_json text not null,
          proof_required_json text not null,
          decision_delta_json text not null,
          scope_json text not null,
          vectors_json text not null,
          created_at_utc text not null
        );
        create table if not exists context_packs (
          context_pack_id text primary key,
          task text not null,
          repo_path text,
          pack_json text not null,
          created_at_utc text not null
        );
        create table if not exists evidence (
          evidence_id text primary key,
          intent_id text not null,
          evidence_type text not null,
          status text not null,
          summary text not null,
          artifact_ref text,
          command text,
          created_at_utc text not null
        );
        create table if not exists graph_edges (
          edge_id text primary key,
          source_id text not null,
          target_id text not null,
          edge_type text not null,
          created_at_utc text not null
        );
        create table if not exists foundry_calls (
          call_id text primary key,
          endpoint_class text not null,
          deployment text,
          prompt_hash text,
          output_hash text,
          redaction_state text not null,
          token_input integer,
          token_output integer,
          created_at_utc text not null
        );
        create table if not exists eval_results (
          eval_id text primary key,
          eval_type text not null,
          status text not null,
          details_json text not null,
          created_at_utc text not null
        );
        create table if not exists hive_bindings (
          bead_id text primary key,
          intent_id text not null,
          context_pack_id text,
          evidence_id text,
          workflow_id text,
          created_at_utc text not null,
          updated_at_utc text not null
        );
        create table if not exists vector_index (
          item_id text primary key,
          item_type text not null,
          source_id text not null,
          vector_json text not null,
          text_hash text not null,
          updated_at_utc text not null
        );
        create table if not exists hive_bead_refs (
          bead_id text primary key,
          rig text,
          title text not null,
          status text,
          priority text,
          owner_role text,
          claimed_by text,
          source_db text not null,
          related_repo text,
          relation_json text not null,
          synced_at_utc text not null
        );
        create table if not exists retention_runs (
          run_id text primary key,
          dry_run integer not null,
          days integer not null,
          details_json text not null,
          created_at_utc text not null
        );
        create table if not exists state_transitions (
          transition_id text primary key,
          subject_id text not null,
          from_state text not null,
          to_state text not null,
          actor text not null,
          allowed_by_contract integer not null,
          evidence_ids_json text not null,
          judge_verdict_ids_json text not null,
          reason text,
          created_at_utc text not null
        );
        create table if not exists feedback_tickets (
          ticket_id text primary key,
          subject_id text not null,
          feedback_type text not null,
          source_url text,
          section_heading text,
          quoted_text text,
          surrounding_context text,
          note text not null,
          status text not null,
          actor text not null,
          evidence_ids_json text not null,
          created_at_utc text not null,
          updated_at_utc text not null
        );
        create index if not exists idx_events_repo on events(repo_path);
        create index if not exists idx_events_session on events(session_id);
        create index if not exists idx_intent_cards_event on intent_cards(event_id);
        create index if not exists idx_vector_index_type on vector_index(item_type);
        create index if not exists idx_hive_bead_refs_rig on hive_bead_refs(rig, status);
        create index if not exists idx_state_transitions_subject on state_transitions(subject_id);
        create index if not exists idx_feedback_tickets_subject on feedback_tickets(subject_id);
        """
    )
    conn.execute(
        "insert or replace into schema_meta(key, value) values (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()
