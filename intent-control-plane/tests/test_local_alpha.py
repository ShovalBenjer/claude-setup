import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_intent(*args: str, base_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )
    cmd = [
        sys.executable,
        "-m",
        "intent_control_plane.cli",
        "--base-dir",
        str(base_dir),
        *args,
    ]
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class LocalAlphaTests(TestCase):
    def test_init_creates_local_layout_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"

            result = run_intent("init", base_dir=base_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((base_dir / "config.toml").exists())
            self.assertTrue((base_dir / "intent.db").exists())
            self.assertTrue((base_dir / "ledger" / "events.jsonl").exists())
            self.assertTrue((base_dir / "context-packs").is_dir())
            self.assertTrue((base_dir / "evals" / "golden").is_dir())
            with sqlite3.connect(base_dir / "intent.db") as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "select name from sqlite_master where type='table'"
                    )
                }
            self.assertGreaterEqual(
                tables,
                {
                    "events",
                    "intent_cards",
                    "context_packs",
                    "evidence",
                    "graph_edges",
                    "foundry_calls",
                    "eval_results",
                },
            )

    def test_capture_redacts_model_text_and_keeps_raw_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            run_intent("init", base_dir=base_dir)

            result = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s1",
                "--repo",
                "/repo",
                "--text",
                "Fix this. API key is sk-proj-abc1234567890 SECRET_TOKEN=oops",
                base_dir=base_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["redaction_state"], "redacted_for_model")
            self.assertNotIn("sk-proj", payload["model_text"])
            self.assertNotIn("SECRET_TOKEN=oops", payload["model_text"])
            events = (base_dir / "ledger" / "events.jsonl").read_text().splitlines()
            self.assertEqual(len(events), 1)
            raw_event = json.loads(events[0])
            self.assertIn("sk-proj-abc1234567890", raw_event["raw_text"])

    def test_extract_context_pack_evidence_and_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            artifact = Path(tmp) / "pytest.out"
            artifact.write_text("3 passed\n")
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s1",
                "--repo",
                "/repo",
                "--branch",
                "feat/test",
                "--text",
                "Fix routing but do not break OTP. Prove with tests and runtime smoke.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]

            extracted = run_intent("extract", "--event", event_id, base_dir=base_dir)
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            intent = json.loads(extracted.stdout)
            self.assertIn("Fix routing", intent["goal"])
            self.assertEqual(intent["constraints"][0]["hardness"], "must")
            self.assertIn("test", {item["type"] for item in intent["proof_required"]})

            context = run_intent(
                "context-pack",
                "--repo",
                "/repo",
                "--task",
                "routing OTP",
                "--format",
                "json",
                base_dir=base_dir,
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            pack = json.loads(context.stdout)
            self.assertEqual(pack["repo_path"], "/repo")
            self.assertTrue(pack["included_items"])
            self.assertIn(event_id, pack["included_items"][0]["source_event_id"])
            self.assertTrue(pack["proof_checklist"])

            evidence = run_intent(
                "evidence",
                "attach",
                "--intent",
                intent["intent_id"],
                "--type",
                "test",
                "--status",
                "pass",
                "--artifact",
                str(artifact),
                base_dir=base_dir,
            )
            self.assertEqual(evidence.returncode, 0, evidence.stderr)
            self.assertEqual(json.loads(evidence.stdout)["status"], "pass")

            doctor = run_intent("doctor", base_dir=base_dir)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertEqual(report["status"], "pass")
            self.assertTrue(report["checks"]["redaction_smoke"])

    def test_list_and_show_commands_inspect_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            artifact = Path(tmp) / "pytest.out"
            artifact.write_text("3 passed\n")
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s2",
                "--repo",
                "/repo",
                "--text",
                "Ship inspect commands. Prove with tests.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            intent_id = json.loads(
                run_intent("extract", "--event", event_id, base_dir=base_dir).stdout
            )["intent_id"]
            context_pack_id = json.loads(
                run_intent(
                    "context-pack",
                    "--repo",
                    "/repo",
                    "--task",
                    "inspect commands",
                    "--format",
                    "json",
                    base_dir=base_dir,
                ).stdout
            )["context_pack_id"]
            evidence_id = json.loads(
                run_intent(
                    "evidence",
                    "attach",
                    "--intent",
                    intent_id,
                    "--type",
                    "test",
                    "--status",
                    "pass",
                    "--artifact",
                    str(artifact),
                    base_dir=base_dir,
                ).stdout
            )["evidence_id"]

            events = json.loads(run_intent("list", "events", base_dir=base_dir).stdout)
            self.assertEqual(events["items"][0]["event_id"], event_id)
            intents = json.loads(run_intent("list", "intents", base_dir=base_dir).stdout)
            self.assertEqual(intents["items"][0]["intent_id"], intent_id)
            packs = json.loads(
                run_intent("list", "context-packs", base_dir=base_dir).stdout
            )
            self.assertEqual(packs["items"][0]["context_pack_id"], context_pack_id)
            evidence = json.loads(run_intent("list", "evidence", base_dir=base_dir).stdout)
            self.assertEqual(evidence["items"][0]["evidence_id"], evidence_id)

            shown_event = json.loads(
                run_intent("show", "event", event_id, base_dir=base_dir).stdout
            )
            self.assertEqual(shown_event["event_id"], event_id)
            shown_intent = json.loads(
                run_intent("show", "intent", intent_id, base_dir=base_dir).stdout
            )
            self.assertEqual(shown_intent["intent_id"], intent_id)
            shown_pack = json.loads(
                run_intent("show", "context-pack", context_pack_id, base_dir=base_dir).stdout
            )
            self.assertEqual(shown_pack["context_pack_id"], context_pack_id)
            shown_evidence = json.loads(
                run_intent("show", "evidence", evidence_id, base_dir=base_dir).stdout
            )
            self.assertEqual(shown_evidence["evidence_id"], evidence_id)

    def test_state_transitions_reject_illegal_ship_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s-state",
                "--repo",
                "/repo",
                "--text",
                "Implement lifecycle gates. Prove illegal ship paths are blocked.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            intent_id = json.loads(
                run_intent("extract", "--event", event_id, base_dir=base_dir).stdout
            )["intent_id"]

            contracted = run_intent(
                "state",
                "transition",
                "--subject",
                intent_id,
                "--from-state",
                "CAPTURED",
                "--to-state",
                "CONTRACTED",
                "--actor",
                "codex_executor",
                "--reason",
                "intent card extracted",
                base_dir=base_dir,
            )

            self.assertEqual(contracted.returncode, 0, contracted.stderr)
            transition = json.loads(contracted.stdout)
            self.assertTrue(transition["allowed_by_contract"])
            self.assertEqual(transition["subject_id"], intent_id)
            self.assertEqual(transition["from_state"], "CAPTURED")
            self.assertEqual(transition["to_state"], "CONTRACTED")

            illegal = run_intent(
                "state",
                "transition",
                "--subject",
                intent_id,
                "--from-state",
                "GENERATED",
                "--to-state",
                "SHIPPED",
                "--actor",
                "codex_executor",
                base_dir=base_dir,
            )

            self.assertNotEqual(illegal.returncode, 0)
            self.assertIn("illegal transition", illegal.stderr)

            transitions = json.loads(
                run_intent("list", "transitions", base_dir=base_dir).stdout
            )
            self.assertEqual(transitions["items"][0]["transition_id"], transition["transition_id"])
            shown = json.loads(
                run_intent(
                    "show",
                    "transition",
                    transition["transition_id"],
                    base_dir=base_dir,
                ).stdout
            )
            self.assertEqual(shown["transition_id"], transition["transition_id"])

    def test_feedback_tickets_track_structured_review_to_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s-feedback",
                "--repo",
                "/repo",
                "--text",
                "Review architecture plan feedback and close only with evidence.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            intent_id = json.loads(
                run_intent("extract", "--event", event_id, base_dir=base_dir).stdout
            )["intent_id"]
            evidence_id = json.loads(
                run_intent(
                    "evidence",
                    "attach",
                    "--intent",
                    intent_id,
                    "--type",
                    "test",
                    "--status",
                    "pass",
                    "--summary",
                    "feedback close proof",
                    base_dir=base_dir,
                ).stdout
            )["evidence_id"]

            added = run_intent(
                "feedback",
                "add",
                "--subject",
                intent_id,
                "--type",
                "architecture",
                "--source-url",
                "file:///plan.html",
                "--section",
                "Workflow accountability",
                "--quote",
                "loop is overrated",
                "--context",
                "architecture quality needs explicit ownership",
                "--note",
                "Require RCA, codebase architecture review, spec review, and proof before shipped.",
                "--actor",
                "shoval",
                base_dir=base_dir,
            )

            self.assertEqual(added.returncode, 0, added.stderr)
            ticket = json.loads(added.stdout)
            self.assertEqual(ticket["status"], "todo")
            self.assertEqual(ticket["feedback_type"], "architecture")

            updated = run_intent(
                "feedback",
                "update",
                "--ticket",
                ticket["ticket_id"],
                "--status",
                "done",
                "--evidence",
                evidence_id,
                base_dir=base_dir,
            )

            self.assertEqual(updated.returncode, 0, updated.stderr)
            closed = json.loads(updated.stdout)
            self.assertEqual(closed["status"], "done")
            self.assertEqual(closed["evidence_ids"], [evidence_id])

            tickets = json.loads(run_intent("list", "feedback", base_dir=base_dir).stdout)
            self.assertEqual(tickets["items"][0]["ticket_id"], ticket["ticket_id"])
            shown = json.loads(
                run_intent("show", "feedback", ticket["ticket_id"], base_dir=base_dir).stdout
            )
            self.assertEqual(shown["note"], ticket["note"])

    def test_eval_smoke_uses_golden_retrieval_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s3",
                "--repo",
                "/repo",
                "--text",
                "Remember OTP split-envelope constraints. Do not break verification routing.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            fixture_path = base_dir / "evals" / "golden" / "otp-routing.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "case_id": "otp-routing",
                        "repo_path": "/repo",
                        "task": "verification routing OTP",
                        "expected_event_ids": [event_id],
                    }
                )
            )

            result = run_intent("eval", "smoke", base_dir=base_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["passed"], 1)
            self.assertEqual(report["failed"], 0)
            eval_id = report["eval_id"]

            evals = json.loads(run_intent("list", "evals", base_dir=base_dir).stdout)
            self.assertEqual(evals["items"][0]["eval_id"], eval_id)
            shown_eval = json.loads(
                run_intent("show", "eval", eval_id, base_dir=base_dir).stdout
            )
            self.assertEqual(shown_eval["eval_id"], eval_id)
            self.assertEqual(shown_eval["status"], "pass")

    def test_hive_bind_links_bead_intent_context_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s4",
                "--repo",
                "/repo",
                "--text",
                "Bind this work to Hive bead 42. Prove with tests.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            intent_id = json.loads(
                run_intent("extract", "--event", event_id, base_dir=base_dir).stdout
            )["intent_id"]
            context_pack_id = json.loads(
                run_intent(
                    "context-pack",
                    "--repo",
                    "/repo",
                    "--task",
                    "Hive bead 42",
                    "--format",
                    "json",
                    base_dir=base_dir,
                ).stdout
            )["context_pack_id"]
            evidence_id = json.loads(
                run_intent(
                    "evidence",
                    "attach",
                    "--intent",
                    intent_id,
                    "--type",
                    "test",
                    "--status",
                    "pass",
                    "--summary",
                    "tests pass",
                    base_dir=base_dir,
                ).stdout
            )["evidence_id"]

            bound = json.loads(
                run_intent(
                    "hive",
                    "bind",
                    "--bead",
                    "42",
                    "--intent",
                    intent_id,
                    "--context-pack",
                    context_pack_id,
                    "--evidence",
                    evidence_id,
                    base_dir=base_dir,
                ).stdout
            )
            self.assertEqual(bound["bead_id"], "42")
            self.assertEqual(bound["intent_id"], intent_id)

            bindings = json.loads(run_intent("list", "bindings", base_dir=base_dir).stdout)
            self.assertEqual(bindings["items"][0]["bead_id"], "42")
            shown = json.loads(
                run_intent("show", "binding", "42", base_dir=base_dir).stdout
            )
            self.assertEqual(shown["context_pack_id"], context_pack_id)
            self.assertEqual(shown["evidence_id"], evidence_id)

    def test_jira_assess_separates_current_session_tickets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            digest = Path(tmp) / "reminders.json"
            pointer = Path(tmp) / "current-ticket"
            cwd = "/home/shovalbe/projects/intent-control-plane"
            digest.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-25T10:11:40+00:00",
                        "flagged": [
                            {
                                "key": "DEV-101",
                                "summary": "Intent control plane prompt capture and context pack evidence",
                                "status": "In Progress",
                                "reasons": ["needs implementation"],
                            },
                            {
                                "key": "DEV-202",
                                "summary": "Campaign report workbook variance for Liron",
                                "status": "To Do",
                                "reasons": ["stale"],
                            },
                        ],
                    }
                )
            )
            pointer.write_text("DEV-202")
            run_intent("init", base_dir=base_dir)
            run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s5",
                "--repo",
                cwd,
                "--text",
                "Continue local intent control plane prompt capture. Prove with tests.",
                base_dir=base_dir,
            )

            assessed = run_intent(
                "jira",
                "assess",
                "--digest",
                str(digest),
                "--pointer",
                str(pointer),
                "--cwd",
                cwd,
                "--session",
                "s5",
                "--task",
                "prompt capture evidence",
                base_dir=base_dir,
            )

            self.assertEqual(assessed.returncode, 0, assessed.stderr)
            report = json.loads(assessed.stdout)
            self.assertEqual(report["related_count"], 1)
            self.assertEqual(report["unrelated_count"], 1)
            self.assertEqual(report["related_tickets"][0]["key"], "DEV-101")
            self.assertEqual(report["unrelated_tickets"][0]["key"], "DEV-202")
            self.assertFalse(report["current_ticket_relation"]["related"])
            self.assertEqual(
                report["recommended_action"], "ask_before_jira_write_or_time_attribution"
            )

    def test_index_rebuild_search_and_session_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            cwd = "/home/shovalbe/projects/intent-control-plane"
            run_intent("init", base_dir=base_dir)
            captured = run_intent(
                "capture",
                "--event-type",
                "user_prompt",
                "--session",
                "s6",
                "--repo",
                cwd,
                "--text",
                "Build vector retrieval for Claude TUI session memory.",
                base_dir=base_dir,
            )
            event_id = json.loads(captured.stdout)["event_id"]
            run_intent("extract", "--event", event_id, base_dir=base_dir)

            rebuilt = run_intent("index", "rebuild", base_dir=base_dir)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
            self.assertGreaterEqual(json.loads(rebuilt.stdout)["indexed"], 2)

            search = run_intent(
                "index",
                "search",
                "--query",
                "vector session memory",
                "--type",
                "event",
                base_dir=base_dir,
            )
            self.assertEqual(search.returncode, 0, search.stderr)
            results = json.loads(search.stdout)["items"]
            self.assertEqual(results[0]["source_id"], event_id)

            brief = run_intent(
                "session",
                "brief",
                "--cwd",
                cwd,
                "--session",
                "s6",
                "--format",
                "markdown",
                base_dir=base_dir,
            )
            self.assertEqual(brief.returncode, 0, brief.stderr)
            self.assertIn("INTENT SESSION BRIEF", brief.stdout)
            self.assertIn(event_id, brief.stdout)

    def test_foundry_status_retention_and_hive_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            hive_db = Path(tmp) / "beads.db"
            old_pack = base_dir / "context-packs" / "old.json"
            run_intent("init", base_dir=base_dir)
            old_pack.parent.mkdir(parents=True, exist_ok=True)
            old_pack.write_text("{}")
            old_time = 1_700_000_000
            os.utime(old_pack, (old_time, old_time))

            with sqlite3.connect(hive_db) as conn:
                conn.execute(
                    """
                    create table beads (
                      id integer primary key,
                      rig text,
                      title text,
                      status text,
                      priority text,
                      owner_role text,
                      claimed_by text,
                      updated_at text
                    )
                    """
                )
                conn.execute(
                    """
                    insert into beads values (
                      7, 'intent-control-plane',
                      'Intent control plane vector and session brief work',
                      'open', 'high', 'architect', null, '2026-06-25T00:00:00Z'
                    )
                    """
                )
                conn.commit()

            foundry = run_intent("foundry", "status", "--record", base_dir=base_dir)
            self.assertEqual(foundry.returncode, 0, foundry.stderr)
            self.assertIn(json.loads(foundry.stdout)["status"], {"pass", "not_configured"})

            synced = run_intent(
                "hive",
                "sync",
                "--db",
                str(hive_db),
                "--rig",
                "intent-control-plane",
                "--cwd",
                "/home/shovalbe/projects/intent-control-plane",
                base_dir=base_dir,
            )
            self.assertEqual(synced.returncode, 0, synced.stderr)
            self.assertEqual(json.loads(synced.stdout)["related"], 1)

            dry_run = run_intent(
                "retention",
                "sweep",
                "--days",
                "30",
                "--dry-run",
                base_dir=base_dir,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertEqual(json.loads(dry_run.stdout)["candidate_count"], 1)
            self.assertTrue(old_pack.exists())

            swept = run_intent(
                "retention",
                "sweep",
                "--days",
                "30",
                base_dir=base_dir,
            )
            self.assertEqual(swept.returncode, 0, swept.stderr)
            self.assertEqual(json.loads(swept.stdout)["candidate_count"], 1)
            self.assertFalse(old_pack.exists())
