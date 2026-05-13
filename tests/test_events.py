import json
import tempfile
import unittest
from pathlib import Path

from ai_workbench_mcp.events import append_response_event, build_event, response_with_event


class EventEnvelopeTests(unittest.TestCase):
    def test_event_envelope_is_built_from_final_response_envelope(self) -> None:
        response = {
            "schema_version": 1,
            "operation": "workbench_select_model",
            "status": "selected",
            "ok": True,
            "artifacts": {"model_selection": Path("runs/run1/model_selection.json")},
            "summary": {
                "run_id": "run1",
                "project": "ai_workbench_mcp",
                "selected_tier": "local_coding",
            },
            "errors": [],
        }

        event = build_event(response)

        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["event_type"], "workbench.operation.completed")
        self.assertEqual(event["source"], "ai_workbench_mcp")
        self.assertEqual(event["operation"], response["operation"])
        self.assertEqual(event["status"], response["status"])
        self.assertTrue(event["ok"])
        self.assertEqual(event["run_id"], "run1")
        self.assertEqual(event["project"], "ai_workbench_mcp")
        self.assertEqual(event["summary"]["selected_tier"], "local_coding")
        self.assertEqual(event["artifacts"]["model_selection"], str(Path("runs/run1/model_selection.json")))
        self.assertTrue(event["event_id"])
        self.assertTrue(event["timestamp"])
        json.dumps(event)

    def test_append_response_event_writes_jsonl_line(self) -> None:
        response = {
            "schema_version": 1,
            "operation": "workbench_validate_run",
            "status": "passed",
            "ok": True,
            "artifacts": {"validation_report": "runs/run1/validation_report.json"},
            "summary": {"run_id": "run1", "project": "ai_workbench_mcp"},
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "nested" / "events.jsonl"

            written = append_response_event(event_path, response)
            event_lines = event_path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(written)
        self.assertEqual(len(event_lines), 1)
        event = json.loads(event_lines[0])
        self.assertEqual(event["operation"], "workbench_validate_run")
        self.assertEqual(event["run_id"], "run1")

    def test_response_with_event_adds_artifact_only_when_write_succeeds(self) -> None:
        response = {
            "schema_version": 1,
            "operation": "workbench_quality_gate",
            "status": "accepted",
            "ok": True,
            "artifacts": {"revision_decision": "runs/run1/revision_decision.json"},
            "summary": {"run_id": "run1", "project": "ai_workbench_mcp"},
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "events.jsonl"

            updated = response_with_event(response, event_path)

        self.assertIn("events", updated["artifacts"])
        self.assertNotIn("events", response["artifacts"])

    def test_event_write_failure_is_non_fatal(self) -> None:
        response = {
            "schema_version": 1,
            "operation": "workbench_open_run",
            "status": "opened",
            "ok": True,
            "artifacts": {"run_dir": "runs/run1"},
            "summary": {"run_id": "run1", "project": "ai_workbench_mcp"},
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            directory_path = Path(tmpdir)

            written = append_response_event(directory_path, response)
            updated = response_with_event(response, directory_path)

        self.assertFalse(written)
        self.assertEqual(updated, response)


if __name__ == "__main__":
    unittest.main()
