import json
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SCRIPT = ROOT / "tools" / "codex_live_test_handoff.py"
RESULT_CHECK_SCRIPT = ROOT / "tools" / "check_codex_live_result.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def write_minimal_codex_live_run(root: Path, *, accepted: bool = True) -> tuple[Path, Path]:
    tool_run_dir = root / "codex-live-check-tool-smoke"
    acceptance_run_dir = root / "codex-live-check-tiny-python-fix"
    tool_run_dir.mkdir(parents=True)
    acceptance_run_dir.mkdir(parents=True)

    write_json(tool_run_dir / "task_metadata.json", {"execution_host": "codex"})
    write_json(tool_run_dir / "model_selection.json", {"status": "selected"})
    write_jsonl(
        tool_run_dir / "events.jsonl",
        [
            {"operation": "workbench_open_run", "summary": {"execution_host": "codex"}},
            {"operation": "workbench_select_model", "summary": {}},
        ],
    )

    write_json(
        acceptance_run_dir / "task_metadata.json",
        {"execution_host": "codex", "recipe": "workbench-test-fix-acceptance.yaml"},
    )
    (acceptance_run_dir / "final_prompt.md").write_text(
        "- Execution Host: `codex`\n- Mode: `codex`\n",
        encoding="utf-8",
    )
    write_json(
        acceptance_run_dir / "model_selection.json",
        {
            "status": "selected",
            "validation_profile": "fixture_repair_proof",
            "recipe": "workbench-test-fix-acceptance.yaml",
        },
    )
    (acceptance_run_dir / "model_output.md").write_text(
        "- Execution Host: `codex`\n- Response Source: `codex`\n",
        encoding="utf-8",
    )
    write_json(
        acceptance_run_dir / "validation_report.json",
        {
            "profile": "fixture_repair_proof",
            "commands_run": [
                {
                    "name": "task_test_command",
                    "command": 'python -m unittest discover -s examples/tiny-python-fix -p "test_*.py"',
                    "status": "passed",
                },
                {"name": "recipe_policy_discovery_tests", "status": "passed"},
                {"name": "validate_run_help", "status": "passed"},
            ],
            "artifact_checks": [
                {"name": "task_test_command", "status": "passed"},
                {"name": "changed_file_policy", "status": "passed"},
            ],
            "overall_status": "passed",
            "sign_off_ready": True,
            "confidence": 1.0,
        },
    )
    write_json(
        acceptance_run_dir / "revision_decision.json",
        {"final_status": "accepted" if accepted else "revision_required"},
    )
    write_jsonl(
        acceptance_run_dir / "events.jsonl",
        [
            {"operation": "workbench_open_run", "summary": {"execution_host": "codex"}},
            {"operation": "workbench_select_model", "summary": {}},
            {
                "operation": "workbench_record_execution",
                "summary": {"execution_host": "codex", "response_source": "codex"},
            },
            {"operation": "workbench_validate_run", "summary": {}},
            {"operation": "workbench_quality_gate", "summary": {}},
        ],
    )
    return tool_run_dir, acceptance_run_dir


class CodexLiveHandoffTests(unittest.TestCase):
    def test_handoff_helper_writes_prompt_without_launching_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "handoff"
            result = subprocess.run(
                [
                    sys.executable,
                    str(HANDOFF_SCRIPT),
                    "--countdown-seconds",
                    "0",
                    "--skip-codex-cli-check",
                    "--stamp",
                    "20260513-120000",
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            prompt_path = out_dir / "codex_live_prompt_20260513-120000.txt"
            prompt_exists = prompt_path.exists()
            prompt = prompt_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("This helper does not launch Codex or start the MCP stdio server.", result.stdout)
        self.assertIn("READY: Start Codex now", result.stdout)
        self.assertIn("SKIP codex mcp list", result.stdout)
        self.assertIn(
            "After Codex finishes, run: python tools/check_codex_live_result.py --stamp 20260513-120000",
            result.stdout,
        )
        self.assertIn(
            "Analyze only this live batch with: python tools/run_analyze.py --runs-dir runs/codex-live-20260513-120000 --out-dir runs/codex-live-20260513-120000/_reports --evidence-scope complete",
            result.stdout,
        )
        self.assertTrue(prompt_exists)
        self.assertIn("runs/codex-live-20260513-120000/tool-smoke", prompt)
        self.assertIn("runs/codex-live-20260513-120000/tiny-python-fix", prompt)
        self.assertIn('execution_host="codex"', prompt)
        self.assertIn('response_source="codex"', prompt)
        self.assertIn('task_type="test"', prompt)
        self.assertIn('validation_profile="fixture_repair_proof"', prompt)
        self.assertIn('recipe="workbench-test-fix-acceptance.yaml"', prompt)
        self.assertIn('profile="fixture_repair_proof"', prompt)
        self.assertIn('task_test_command="python -m unittest discover -s examples/tiny-python-fix -p test_*.py"', prompt)
        self.assertIn("OS-appropriate shell inspection commands", prompt)
        self.assertIn('response_text="Summary:', prompt)
        self.assertIn("Do not ask Codex to launch another Codex session.", prompt)
        self.assertIn("Do not start ai-workbench-mcp directly", prompt)
        self.assertLess(
            prompt.index("Open the acceptance run with workbench_open_run"),
            prompt.index("Fix examples/tiny-python-fix/calculator.py"),
        )

    def test_handoff_helper_refuses_existing_run_directories(self) -> None:
        existing_run_dir = ROOT / "runs" / "codex-live-existing"
        created = not existing_run_dir.exists()
        existing_run_dir.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(HANDOFF_SCRIPT),
                        "--countdown-seconds",
                        "0",
                        "--skip-codex-cli-check",
                        "--stamp",
                        "existing",
                        "--out-dir",
                        str(Path(tmpdir) / "handoff"),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
        finally:
            if created:
                shutil.rmtree(existing_run_dir, ignore_errors=True)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL refusing to reuse existing run directories", result.stdout)

    def test_result_checker_accepts_completed_codex_live_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_run_dir, acceptance_run_dir = write_minimal_codex_live_run(Path(tmpdir))
            result = subprocess.run(
                [
                    sys.executable,
                    str(RESULT_CHECK_SCRIPT),
                    "--tool-run-dir",
                    str(tool_run_dir),
                    "--acceptance-run-dir",
                    str(acceptance_run_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertIn("execution_host: codex", result.stdout)
        self.assertIn("response_source: codex", result.stdout)
        self.assertIn("recipe: workbench-test-fix-acceptance.yaml", result.stdout)
        self.assertIn("validation_profile: fixture_repair_proof", result.stdout)
        self.assertIn("quality_gate: accepted", result.stdout)

    def test_result_checker_rejects_unaccepted_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_run_dir, acceptance_run_dir = write_minimal_codex_live_run(Path(tmpdir), accepted=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(RESULT_CHECK_SCRIPT),
                    "--json",
                    "--tool-run-dir",
                    str(tool_run_dir),
                    "--acceptance-run-dir",
                    str(acceptance_run_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ok"])
        failed_checks = {check["name"] for check in payload["checks"] if check["status"] == "failed"}
        self.assertEqual(failed_checks, {"acceptance_quality_gate_accepted"})

    def test_result_checker_rejects_missing_acceptance_recipe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_run_dir, acceptance_run_dir = write_minimal_codex_live_run(Path(tmpdir))
            write_json(acceptance_run_dir / "task_metadata.json", {"execution_host": "codex"})
            write_json(
                acceptance_run_dir / "model_selection.json",
                {"status": "selected", "validation_profile": "fixture_repair_proof"},
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(RESULT_CHECK_SCRIPT),
                    "--json",
                    "--tool-run-dir",
                    str(tool_run_dir),
                    "--acceptance-run-dir",
                    str(acceptance_run_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ok"])
        failed_checks = {check["name"] for check in payload["checks"] if check["status"] == "failed"}
        self.assertEqual(
            failed_checks,
            {"acceptance_metadata_recipe", "acceptance_model_selection_recipe"},
        )


if __name__ == "__main__":
    unittest.main()
