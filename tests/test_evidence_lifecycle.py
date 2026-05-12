import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
TOOLS_DIR = ROOT / "tools"
for candidate in (SRC_DIR, TOOLS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from ai_workbench_mcp.core import open_run, record_execution, select_model
from model_handoff import parse_final_prompt


class EvidenceLifecycleTests(unittest.TestCase):
    def test_open_run_writes_model_handoff_compatible_final_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"
            task = "Add lifecycle evidence tests."

            response = open_run(
                project="ai_workbench_mcp",
                task=task,
                run_dir=run_dir,
                risk="low",
                recipe="workbench-engineering-acceptance.yaml",
            )
            prompt_summary = parse_final_prompt(run_dir / "final_prompt.md")
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            log_lines = (run_dir / "run_log.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_open_run")
        self.assertEqual(response["status"], "opened")
        self.assertEqual(response["summary"]["run_id"], "run1")
        self.assertEqual(response["artifacts"]["final_prompt"], str(run_dir / "final_prompt.md"))
        self.assertEqual(prompt_summary.run_id, "run1")
        self.assertEqual(prompt_summary.project, "ai_workbench_mcp")
        self.assertEqual(prompt_summary.mode, "goose")
        self.assertEqual(prompt_summary.risk, "low")
        self.assertIn(task, prompt_summary.task)
        self.assertEqual(metadata["task"], task)
        self.assertEqual(metadata["recipe"], "workbench-engineering-acceptance.yaml")
        self.assertEqual(response["summary"]["recipe"], "workbench-engineering-acceptance.yaml")
        self.assertEqual(len(log_lines), 1)
        self.assertEqual(json.loads(log_lines[0])["decision"], "run_opened")

    def test_open_run_repeated_call_does_not_duplicate_initial_log_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            first = open_run(
                project="ai_workbench_mcp",
                task="Open once.",
                run_dir=run_dir,
                risk="low",
            )
            second = open_run(
                project="ai_workbench_mcp",
                task="Open once.",
                run_dir=run_dir,
                risk="low",
            )
            log_lines = (run_dir / "run_log.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(log_lines), 1)
        self.assertEqual(json.loads(log_lines[0])["decision"], "run_opened")

    def test_open_run_rejects_invalid_risk(self) -> None:
        response = open_run(
            project="ai_workbench_mcp",
            task="Invalid risk.",
            run_dir="runs/invalid-risk",
            risk="urgent",
        )

        self.assertEqual(response["operation"], "workbench_open_run")
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "open_run_failed")
        self.assertIn("risk must be one of", response["errors"][0]["message"])

    def test_record_execution_writes_model_output_and_run_log_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"
            task = "Record raw response text."
            open_run(
                project="ai_workbench_mcp",
                task=task,
                run_dir=run_dir,
                risk="medium",
            )
            select_model(
                project="ai_workbench_mcp",
                task_type="implement",
                risk="medium",
                out=run_dir / "model_selection.json",
                prompt="implement_request_change_request",
                complexity_score=13,
            )

            response = record_execution(
                project="ai_workbench_mcp",
                run_dir=run_dir,
                response_text="\n".join(
                    [
                        "Summary:",
                        "Captured the response.",
                        "",
                        "Files touched:",
                        "- src/ai_workbench_mcp/core.py",
                        "",
                        "Validation run:",
                        "- pytest -> not run",
                        "",
                        "Risks / follow-ups:",
                        "- None.",
                    ]
                ),
                files_touched=["src/ai_workbench_mcp/core.py"],
                response_source="goose",
            )
            model_output = (run_dir / "model_output.md").read_text(encoding="utf-8")
            log_entries = [
                json.loads(line)
                for line in (run_dir / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_record_execution")
        self.assertEqual(response["status"], "response_captured")
        self.assertEqual(response["artifacts"]["model_output"], str(run_dir / "model_output.md"))
        self.assertIn("- Status: `response_captured`", model_output)
        self.assertIn("- Response source: goose", model_output)
        self.assertIn("## Captured Response", model_output)
        self.assertEqual(len(log_entries), 2)
        self.assertEqual(log_entries[-1]["decision"], "model_response_captured")
        self.assertEqual(log_entries[-1]["status"], "in_progress")
        self.assertEqual(log_entries[-1]["files_touched"], ["src/ai_workbench_mcp/core.py"])

    def test_record_execution_repeated_call_does_not_overwrite_or_duplicate_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"
            open_run(
                project="ai_workbench_mcp",
                task="Record only the first response.",
                run_dir=run_dir,
                risk="medium",
            )
            select_model(
                project="ai_workbench_mcp",
                task_type="implement",
                risk="medium",
                out=run_dir / "model_selection.json",
                prompt="implement_request_change_request",
                complexity_score=13,
            )

            first = record_execution(
                project="ai_workbench_mcp",
                run_dir=run_dir,
                response_text="Summary:\nFirst captured response.",
                files_touched=["src/ai_workbench_mcp/core.py"],
            )
            second = record_execution(
                project="ai_workbench_mcp",
                run_dir=run_dir,
                response_text="Summary:\nSecond response should be ignored.",
                files_touched=[],
            )
            model_output = (run_dir / "model_output.md").read_text(encoding="utf-8")
            log_entries = [
                json.loads(line)
                for line in (run_dir / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(first["ok"])
        self.assertFalse(first["summary"]["duplicate_ignored"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["summary"]["duplicate_ignored"])
        self.assertEqual(len(log_entries), 2)
        self.assertEqual(log_entries[-1]["decision"], "model_response_captured")
        self.assertIn("First captured response.", model_output)
        self.assertNotIn("Second response should be ignored.", model_output)

    def test_record_execution_rejects_invalid_status_values_before_writes(self) -> None:
        response = record_execution(
            project="ai_workbench_mcp",
            run_dir="runs/missing",
            response_text="Summary:\nNo write should happen.",
            model_output_status="invalid",
            run_status="done",
        )

        self.assertEqual(response["operation"], "workbench_record_execution")
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "record_execution_failed")
        self.assertIn("model_output_status must be one of", response["errors"][0]["message"])

        response = record_execution(
            project="ai_workbench_mcp",
            run_dir="runs/missing",
            response_text="Summary:\nNo write should happen.",
            run_status="done",
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "record_execution_failed")
        self.assertIn("run_status must be one of", response["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
