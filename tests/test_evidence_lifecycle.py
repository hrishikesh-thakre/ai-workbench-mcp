import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workbench_mcp.core import open_run, record_execution, select_model
from ai_workbench_mcp.tools.model_handoff import parse_final_prompt


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))
            log_lines = (run_dir / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
            events = read_jsonl(run_dir / "events.jsonl")
            policy_selection_exists = (run_dir / "policy_pack_selection.json").exists()

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_open_run")
        self.assertEqual(response["status"], "opened")
        self.assertEqual(response["summary"]["run_id"], "run1")
        self.assertEqual(response["artifacts"]["final_prompt"], str(run_dir / "final_prompt.md"))
        self.assertEqual(response["artifacts"]["events"], str(run_dir / "events.jsonl"))
        self.assertEqual(prompt_summary.run_id, "run1")
        self.assertEqual(prompt_summary.project, "ai_workbench_mcp")
        self.assertEqual(prompt_summary.execution_host, "goose")
        self.assertEqual(prompt_summary.mode, "goose")
        self.assertEqual(prompt_summary.risk, "low")
        self.assertIn(task, prompt_summary.task)
        self.assertEqual(metadata["task"], task)
        self.assertEqual(metadata["execution_host"], "goose")
        self.assertEqual(metadata["recipe"], "workbench-engineering-acceptance.yaml")
        self.assertNotIn("policy_pack", metadata)
        self.assertNotIn("validation_profile", metadata)
        self.assertTrue(policy_selection_exists)
        self.assertEqual(selection["status"], "not_selected")
        self.assertIn("confidence", selection["reason"])
        self.assertEqual(response["summary"]["execution_host"], "goose")
        self.assertEqual(response["summary"]["recipe"], "workbench-engineering-acceptance.yaml")
        self.assertNotIn("policy_pack", response["summary"])
        self.assertNotIn("validation_profile", response["summary"])
        self.assertEqual(len(log_lines), 1)
        self.assertEqual(json.loads(log_lines[0])["decision"], "run_opened")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["operation"], "workbench_open_run")
        self.assertEqual(events[0]["summary"]["execution_host"], "goose")
        self.assertEqual(events[0]["summary"]["task"], task)

    def test_open_run_writes_codex_execution_host_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Open a Codex-local run.",
                run_dir=run_dir,
                risk="low",
                execution_host="codex",
            )
            prompt_summary = parse_final_prompt(run_dir / "final_prompt.md")
            final_prompt = (run_dir / "final_prompt.md").read_text(encoding="utf-8")
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["execution_host"], "codex")
        self.assertEqual(metadata["execution_host"], "codex")
        self.assertEqual(prompt_summary.execution_host, "codex")
        self.assertEqual(prompt_summary.mode, "codex")
        self.assertIn("- Execution Host: `codex`", final_prompt)
        self.assertIn("- Mode: `codex`", final_prompt)
        self.assertEqual(events[0]["summary"]["execution_host"], "codex")

    def test_open_run_manual_policy_pack_maps_to_validation_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Docs-only update for the public guide.",
                run_dir=run_dir,
                risk="low",
                changed_files=["docs/guide.md"],
                policy_pack="docs_only",
            )
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertEqual(response["artifacts"]["policy_pack_selection"], str(run_dir / "policy_pack_selection.json"))
        self.assertEqual(response["summary"]["policy_pack"], "docs_only")
        self.assertEqual(response["summary"]["validation_profile"], "docs_only")
        self.assertEqual(response["summary"]["policy_pack_selection_mode"], "manual_policy_pack")
        self.assertEqual(response["summary"]["policy_pack_selection_confidence"], 1.0)
        self.assertEqual(metadata["policy_pack"], "docs_only")
        self.assertEqual(metadata["validation_profile"], "docs_only")
        self.assertEqual(metadata["policy_pack_selection_mode"], "manual_policy_pack")
        self.assertEqual(metadata["policy_pack_selection_confidence"], 1.0)
        self.assertEqual(selection["status"], "selected")
        self.assertTrue(selection["ok"])
        self.assertEqual(selection["policy_pack"], "docs_only")
        self.assertEqual(selection["validation_profile"], "docs_only")
        self.assertEqual(selection["recommended_validation_profile"], "docs_only")
        self.assertEqual(selection["policy_pack_selection_mode"], "manual_policy_pack")

    def test_open_run_explicit_validation_profile_wins_over_auto_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Fix a bounded server helper.",
                run_dir=run_dir,
                risk="low",
                changed_files=["src/ai_workbench_mcp/server.py"],
                auto_select_policy_pack=True,
                validation_profile="docs_only",
            )
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertEqual(metadata["policy_pack"], "docs_only")
        self.assertEqual(metadata["validation_profile"], "docs_only")
        self.assertEqual(metadata["policy_pack_selection_mode"], "manual_validation_profile")
        self.assertEqual(selection["status"], "selected")
        self.assertTrue(selection["auto_select_policy_pack"])
        self.assertIsNone(selection["requested_policy_pack"])
        self.assertEqual(selection["requested_validation_profile"], "docs_only")
        self.assertEqual(selection["policy_pack_selection_mode"], "manual_validation_profile")

    def test_open_run_rejects_conflicting_explicit_policy_pack_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Open conflicting policy metadata.",
                run_dir=run_dir,
                risk="low",
                policy_pack="low_risk_bug_fix",
                validation_profile="docs_only",
            )
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertFalse(response["ok"])
        self.assertEqual(response["operation"], "workbench_open_run")
        self.assertEqual(response["errors"][0]["code"], "open_run_failed")
        self.assertIn("Conflicting policy_pack and validation_profile", response["errors"][0]["message"])
        self.assertEqual(selection["status"], "error")
        self.assertFalse(selection["ok"])
        self.assertTrue(selection["blocking"])
        self.assertIn("Conflicting policy_pack and validation_profile", selection["reason"])

    def test_open_run_auto_policy_selection_records_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Docs-only update for onboarding copy.",
                run_dir=run_dir,
                risk="low",
                changed_files=["docs/onboarding.md"],
                auto_select_policy_pack=True,
            )
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertEqual(metadata["policy_pack"], "docs_only")
        self.assertEqual(metadata["validation_profile"], "docs_only")
        self.assertEqual(metadata["policy_pack_selection_mode"], "auto_advisory")
        self.assertGreater(metadata["policy_pack_selection_confidence"], 0.0)
        self.assertEqual(selection["status"], "selected")
        self.assertEqual(selection["policy_pack"], "docs_only")
        self.assertEqual(selection["validation_profile"], "docs_only")
        self.assertEqual(selection["recommended_policy_pack"], "docs_only")
        self.assertEqual(selection["recommended_validation_profile"], "docs_only")
        self.assertEqual(selection["policy_pack_selection_mode"], "auto_advisory")

    def test_open_run_auto_policy_selection_records_not_selected_without_usable_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            with patch(
                "ai_workbench_mcp.core.policy_pack_select_tool.select_policy_pack_payload",
                return_value={
                    "schema_version": 1,
                    "operation": "workbench_select_policy_pack",
                    "status": "selected",
                    "ok": True,
                    "recommended_policy_pack": "docs_only",
                    "profile_selection_mode": "auto_advisory",
                    "confidence": 0.8,
                },
            ):
                response = open_run(
                    project="ai_workbench_mcp",
                    task="Docs-only update for onboarding copy.",
                    run_dir=run_dir,
                    risk="low",
                    changed_files=["docs/onboarding.md"],
                    auto_select_policy_pack=True,
                )
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertNotIn("policy_pack", metadata)
        self.assertNotIn("validation_profile", metadata)
        self.assertNotIn("policy_pack", response["summary"])
        self.assertNotIn("validation_profile", response["summary"])
        self.assertEqual(selection["status"], "not_selected")
        self.assertFalse(selection["ok"])
        self.assertFalse(selection["blocking"])
        self.assertIsNone(selection["validation_profile"])
        self.assertIn("did not return a usable", selection["reason"])

    def test_open_run_auto_policy_selection_requires_changed_files_for_mutating_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"

            response = open_run(
                project="ai_workbench_mcp",
                task="Change the MCP contract schema for tool responses.",
                run_dir=run_dir,
                risk="medium",
                auto_select_policy_pack=True,
            )
            metadata = json.loads((run_dir / "task_metadata.json").read_text(encoding="utf-8"))
            selection = json.loads((run_dir / "policy_pack_selection.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertNotIn("validation_profile", metadata)
        self.assertEqual(selection["status"], "not_selected")
        self.assertFalse(selection["blocking"])
        self.assertIn("Changed files are required", selection["reason"])

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
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(log_lines), 1)
        self.assertEqual(json.loads(log_lines[0])["decision"], "run_opened")
        self.assertEqual(len(events), 2)
        self.assertEqual([event["operation"] for event in events], ["workbench_open_run", "workbench_open_run"])

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
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_record_execution")
        self.assertEqual(response["status"], "response_captured")
        self.assertEqual(response["artifacts"]["model_output"], str(run_dir / "model_output.md"))
        self.assertEqual(response["artifacts"]["events"], str(run_dir / "events.jsonl"))
        self.assertEqual(response["summary"]["execution_host"], "goose")
        self.assertEqual(response["summary"]["response_source"], "goose")
        self.assertIn("- Execution Host: `goose`", model_output)
        self.assertIn("- Status: `response_captured`", model_output)
        self.assertIn("- Response Source: `goose`", model_output)
        self.assertIn("## Captured Response", model_output)
        self.assertEqual(len(log_entries), 2)
        self.assertEqual(log_entries[-1]["decision"], "model_response_captured")
        self.assertEqual(log_entries[-1]["status"], "in_progress")
        self.assertEqual(log_entries[-1]["files_touched"], ["src/ai_workbench_mcp/core.py"])
        self.assertEqual([event["operation"] for event in events], [
            "workbench_open_run",
            "workbench_select_model",
            "workbench_record_execution",
        ])
        self.assertEqual(events[-1]["summary"]["execution_host"], "goose")
        self.assertEqual(events[-1]["summary"]["response_source"], "goose")

    def test_record_execution_preserves_codex_host_and_response_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run1"
            open_run(
                project="ai_workbench_mcp",
                task="Record a Codex-local response.",
                run_dir=run_dir,
                risk="medium",
                execution_host="codex",
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
                response_text="Summary:\nCodex response captured.\n\nFiles touched:\n- src/example.py\n\nValidation run:\n- pytest -> not run\n\nRisks / follow-ups:\n- None.",
                files_touched=["src/example.py"],
                response_source="codex",
            )
            model_output = (run_dir / "model_output.md").read_text(encoding="utf-8")
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["execution_host"], "codex")
        self.assertEqual(response["summary"]["response_source"], "codex")
        self.assertIn("- Execution Host: `codex`", model_output)
        self.assertIn("- Response Source: `codex`", model_output)
        self.assertEqual(events[-1]["summary"]["execution_host"], "codex")
        self.assertEqual(events[-1]["summary"]["response_source"], "codex")

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
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(first["ok"])
        self.assertFalse(first["summary"]["duplicate_ignored"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["summary"]["duplicate_ignored"])
        self.assertEqual(len(log_entries), 2)
        self.assertEqual(log_entries[-1]["decision"], "model_response_captured")
        self.assertIn("First captured response.", model_output)
        self.assertNotIn("Second response should be ignored.", model_output)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[-1]["operation"], "workbench_record_execution")
        self.assertTrue(events[-1]["summary"]["duplicate_ignored"])

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
