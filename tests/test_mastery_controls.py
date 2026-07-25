from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PROOF_PATH = (
    ROOT
    / "dot-claude"
    / "skills"
    / "prove-implementation"
    / "scripts"
    / "implementation_proof.py"
)
LOOP_PATH = (
    ROOT
    / "dot-claude"
    / "skills"
    / "prove-implementation"
    / "scripts"
    / "loop_audit.py"
)
KNOWLEDGE_PATH = (
    ROOT
    / "dot-claude"
    / "skills"
    / "learn-on-demand"
    / "scripts"
    / "knowledge.py"
)
HOOK_ROOT = ROOT / "dot-claude" / "hooks"
PREPUSH_PATH = HOOK_ROOT / "pre_push_gate.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proof = load_module("implementation_proof", PROOF_PATH)
loop_audit = load_module("loop_audit", LOOP_PATH)
knowledge = load_module("knowledge", KNOWLEDGE_PATH)
prepush = load_module("pre_push_gate", PREPUSH_PATH)


def populated_record() -> dict:
    record = proof.make_template("Choose a bounded bulk-processing implementation", "medium")
    record["acceptance_criteria"][0].update(
        {
            "text": "Processes all inputs and preserves order",
            "oracle": "A deterministic test compares output with the reference implementation",
        }
    )
    for candidate in record["candidates"]:
        candidate["time_complexity"] = "O(n)"
        candidate["space_complexity"] = "O(1)"
        candidate["risks"] = ["Representative input distribution may drift"]
        candidate["when_it_wins"] = "Under the measured constraints recorded by the benchmark"
    record["selected"] = {
        "candidate_id": "simple",
        "rationale": "It satisfies the oracle with the smallest operational surface.",
        "evidence": ["check:C1"],
    }
    record["claims"] = [
        {
            "claim": "The selected implementation passes the declared behavior oracle.",
            "status": "verified",
            "evidence": ["check:C1"],
        }
    ]
    return record


class ImplementationProofTests(unittest.TestCase):
    def test_execution_backed_check_validates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "proof.json"
            record = populated_record()
            path.write_text(json.dumps(record), encoding="utf-8")
            args = argparse.Namespace(
                path=str(path),
                check_id="C1",
                cwd=str(directory),
                timeout=10.0,
                command=[sys.executable, "-c", "print('oracle passed')"],
            )
            self.assertEqual(proof.command_run_check(args), 0)
            self.assertEqual(proof.validate(proof.load(path)), [])

    def test_run_check_cli_accepts_command_after_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "proof.json"
            path.write_text(json.dumps(populated_record()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROOF_PATH),
                    "run-check",
                    str(path),
                    "--check-id",
                    "C1",
                    "--cwd",
                    str(directory),
                    "--",
                    sys.executable,
                    "-c",
                    "print('cli oracle passed')",
                ],
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertEqual(proof.validate(proof.load(path)), [])

    def test_launch_failure_replaces_stale_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "proof.json"
            record = populated_record()
            record["verification"]["checks"][0].update(
                {
                    "status": "pass",
                    "command": "stale-success",
                    "exit_code": 0,
                    "ran_at": "2026-07-25T00:00:00+00:00",
                    "output_sha256": "a" * 64,
                    "output_digest": "stale",
                }
            )
            path.write_text(json.dumps(record), encoding="utf-8")
            args = argparse.Namespace(
                path=str(path),
                check_id="C1",
                cwd=str(directory),
                timeout=1.0,
                command=[str(directory / "missing-executable")],
            )
            self.assertEqual(proof.command_run_check(args), 2)
            updated = proof.load(path)["verification"]["checks"][0]
            self.assertEqual(updated["status"], "fail")
            self.assertIsNone(updated["exit_code"])
            self.assertTrue(any("is failing" in error for error in proof.validate(proof.load(path))))

    def test_timeout_replaces_stale_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "proof.json"
            record = populated_record()
            record["verification"]["checks"][0]["status"] = "pass"
            path.write_text(json.dumps(record), encoding="utf-8")
            args = argparse.Namespace(
                path=str(path),
                check_id="C1",
                cwd=str(directory),
                timeout=0.01,
                command=[sys.executable, "-c", "import time; time.sleep(1)"],
            )
            self.assertEqual(proof.command_run_check(args), 2)
            updated = proof.load(path)["verification"]["checks"][0]
            self.assertEqual(updated["status"], "fail")
            self.assertEqual(updated["output_digest"], "execution_error:TimeoutExpired")

    def test_profile_parent_repo_is_not_implicitly_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = proof.capture_repo_state(Path(raw))
            self.assertIsNone(state["git_commit"])
            self.assertIsNone(state["diff_sha256"])

    def test_untracked_source_content_is_bound_inside_explicit_repo(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            commands = [
                ["git", "init"],
                ["git", "config", "user.email", "proof@example.invalid"],
                ["git", "config", "user.name", "Proof Test"],
            ]
            for command in commands:
                subprocess.run(command, cwd=directory, capture_output=True, check=True)
            tracked = directory / "tracked.txt"
            tracked.write_text("anchor\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=directory, check=True)
            subprocess.run(
                ["git", "commit", "-m", "anchor"],
                cwd=directory,
                capture_output=True,
                check=True,
            )
            untracked = directory / "new_code.py"
            untracked.write_text("VALUE = 1\n", encoding="utf-8")
            first = proof.capture_repo_state(directory)
            untracked.write_text("VALUE = 2\n", encoding="utf-8")
            second = proof.capture_repo_state(directory)
            self.assertTrue(first["git_commit"])
            self.assertTrue(first["diff_sha256"])
            self.assertNotEqual(first["diff_sha256"], second["diff_sha256"])

    def test_failed_check_invalidates_record(self) -> None:
        record = populated_record()
        check = record["verification"]["checks"][0]
        check.update(
            {
                "status": "fail",
                "command": "false",
                "exit_code": 1,
                "ran_at": "2026-07-25T00:00:00+00:00",
                "output_sha256": "0" * 64,
                "output_digest": "sha256:0; bytes:0",
                "repo_state": {
                    "cwd": "C:/tmp",
                    "captured_at": "2026-07-25T00:00:00+00:00",
                    "git_commit": None,
                    "diff_sha256": None,
                },
            }
        )
        errors = proof.validate(record)
        self.assertTrue(any("is failing" in item for item in errors))

    def test_rejected_or_negative_strong_claim_needs_no_benchmark(self) -> None:
        record = populated_record()
        check = record["verification"]["checks"][0]
        check.update(
            {
                "status": "pass",
                "command": "python -m unittest",
                "exit_code": 0,
                "ran_at": "2026-07-25T00:00:00+00:00",
                "output_sha256": "1" * 64,
                "output_digest": "sha256:1; bytes:10",
                "repo_state": {
                    "cwd": "C:/tmp",
                    "captured_at": "2026-07-25T00:00:00+00:00",
                    "git_commit": None,
                    "diff_sha256": None,
                },
            }
        )
        record["claims"] = [
            {
                "claim": "This is not production-ready.",
                "status": "verified",
                "evidence": ["check:C1"],
            },
            {
                "claim": "A globally optimal implementation was not established.",
                "status": "rejected",
                "evidence": [],
            },
        ]
        errors = proof.validate(record)
        self.assertFalse(any("passing benchmark" in item for item in errors), errors)

    def test_multiline_typescript_await_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bulk.ts"
            path.write_text(
                """
                export async function load(ids: string[]) {
                  for (
                    const id of ids
                  ) {
                    const response = await fetch(`/items/${id}`);
                    await response.json();
                  }
                }
                """,
                encoding="utf-8",
            )
            records, errors = loop_audit.audit_script(path)
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 1)
            self.assertIn("await_inside_iteration", records[0]["flags"])
            self.assertIn("possible_io_inside_iteration", records[0]["flags"])
            self.assertTrue(records[0]["content_sha256"])


class KnowledgeCatalogTests(unittest.TestCase):
    def test_catalog_validates(self) -> None:
        catalog = ROOT / "dot-claude" / "skills" / "learn-on-demand" / "references" / "catalog.json"
        if not catalog.exists():
            self.skipTest("catalog transformation is still in progress")
        errors = knowledge.validate_catalog(knowledge.load_catalog(catalog))
        self.assertEqual(errors, [])

    def test_query_rebuilds_a_stale_catalog_index(self) -> None:
        source_catalog = (
            ROOT
            / "dot-claude"
            / "skills"
            / "learn-on-demand"
            / "references"
            / "catalog.json"
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            catalog = directory / "catalog.json"
            db = directory / "knowledge.db"
            manifest = directory / "attestations.json"
            data = knowledge.load_catalog(source_catalog)
            catalog.write_text(json.dumps(data), encoding="utf-8")
            build_args = argparse.Namespace(
                catalog=str(catalog),
                db=str(db),
                manifest=str(manifest),
                include_private=False,
            )
            self.assertEqual(knowledge.command_build(build_args), 0)
            old_hash = knowledge.indexed_catalog_sha256(db)
            data["sources"][0]["selection_reason"] += " Freshness sentinel."
            catalog.write_text(json.dumps(data), encoding="utf-8")
            query_args = argparse.Namespace(
                catalog=str(catalog),
                db=str(db),
                manifest=str(manifest),
                question="software engineering",
                domain=[],
                limit=2,
                include_private_snippets=False,
                include_announced=False,
                snippet_chars=100,
            )
            self.assertEqual(knowledge.command_query(query_args), 0)
            self.assertNotEqual(knowledge.indexed_catalog_sha256(db), old_hash)
            self.assertEqual(
                knowledge.indexed_catalog_sha256(db),
                knowledge.hash_file(catalog),
            )


def run_hook(name: str, payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(HOOK_ROOT / name)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        timeout=10,
        check=True,
    )
    return json.loads(result.stdout.decode("utf-8"))


class HookTests(unittest.TestCase):
    def test_test_prefix_detection_does_not_exempt_ordinary_source(self) -> None:
        for path in (
            "src/latest_model.py",
            "src/contest_runner.py",
            "src/attest_service.ts",
        ):
            self.assertFalse(prepush.is_test(path), path)
            self.assertTrue(prepush.is_source(path), path)
        self.assertTrue(prepush.is_test("tests/test_model.py"))
        self.assertTrue(prepush.is_test("src/model_test.py"))
        for path in (
            "include/engine.hpp",
            "src/worker.mjs",
            "src/worker.cjs",
            "src/page.vue",
            "src/page.svelte",
            "notebooks/train.ipynb",
            "wrangler.toml",
            "wrangler.jsonc",
            "tsconfig.json",
            "schema.prisma",
            "api.graphql",
        ):
            self.assertTrue(prepush.is_source(path), path)

    def test_utf8_hebrew_completion_and_non_completion(self) -> None:
        blocked = run_hook(
            "completion_gate.py",
            {"last_assistant_message": "הושלם והקוד עובד."},
        )
        self.assertEqual(blocked.get("decision"), "block")
        ordinary = run_hook(
            "completion_gate.py",
            {"last_assistant_message": "מדריך לעובדים חדשים."},
        )
        self.assertEqual(ordinary, {})

    def test_completion_gate_is_scoped_and_loop_guarded(self) -> None:
        self.assertEqual(
            run_hook(
                "completion_gate.py",
                {"last_assistant_message": "The best next step is to ask the user."},
            ),
            {},
        )
        self.assertEqual(
            run_hook(
                "completion_gate.py",
                {"last_assistant_message": "Done.", "stop_hook_active": True},
            ),
            {},
        )
        self.assertEqual(
            run_hook(
                "completion_gate.py",
                {"last_assistant_message": "Implemented. pytest: 10 passed."},
            ),
            {},
        )

    def test_command_substitution_cannot_bypass_safety_gate(self) -> None:
        result = run_hook(
            "safety_gate.py",
            {"tool_input": {"command": 'echo "$(cat .env)"'}},
        )
        self.assertEqual(
            result.get("hookSpecificOutput", {}).get("permissionDecision"),
            "deny",
        )
        self.assertEqual(
            run_hook(
                "safety_gate.py",
                {"tool_input": {"command": r'rg -n "\\.env" README.md'}},
            ),
            {},
        )

    def test_common_destructive_and_secret_read_variants_are_denied(self) -> None:
        commands = (
            "git checkout .",
            "git checkout -f main",
            "git checkout --force .",
            "git switch --discard-changes main",
            "git branch --delete --force old",
            r"cmd /c rd /s /q C:\Users\shova",
            "head .env",
            "tail .env",
            "sed -n '1p' .env",
            "awk '{print}' .env",
            "base64 .env",
            "node -e \"console.log(require('fs').readFileSync('.env','utf8'))\"",
            "ruby -e \"puts File.read('.env')\"",
        )
        for command in commands:
            result = run_hook(
                "safety_gate.py",
                {"tool_input": {"command": command}},
            )
            self.assertEqual(
                result.get("hookSpecificOutput", {}).get("permissionDecision"),
                "deny",
                command,
            )

    def test_only_plain_current_branch_push_is_auto_inspected(self) -> None:
        result = run_hook(
            "pre_push_gate.py",
            {
                "cwd": str(ROOT),
                "tool_input": {"command": f'git -C "{ROOT}" push origin otherbranch'},
            },
        )
        self.assertEqual(
            result.get("hookSpecificOutput", {}).get("permissionDecision"),
            "ask",
        )
        self.assertEqual(
            run_hook(
                "pre_push_gate.py",
                {"cwd": str(ROOT), "tool_input": {"command": "git status"}},
            ),
            {},
        )

    def test_profile_parent_repo_push_never_auto_allows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_hook(
                "pre_push_gate.py",
                {"cwd": raw, "tool_input": {"command": "git push"}},
            )
        self.assertEqual(
            result.get("hookSpecificOutput", {}).get("permissionDecision"),
            "ask",
        )


if __name__ == "__main__":
    unittest.main()
