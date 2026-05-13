import json
import inspect
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workbench_mcp.contracts import error_envelope, response_envelope
from ai_workbench_mcp.core import (
    model_selection_file_response,
    model_selection_response,
    quality_gate_response,
    quality_gate,
    run_analysis_file_response,
    run_analysis_response,
    analyze_runs,
    select_model,
    validate_run,
    validation_response,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ContractEnvelopeTests(unittest.TestCase):
    def test_response_envelope_has_stable_common_fields(self) -> None:
        response = response_envelope(
            operation="workbench_example",
            status="completed",
            ok=True,
            artifacts={"report": Path("runs/example/report.json")},
            summary={"count": 1},
        )

        self.assertEqual(
            list(response),
            ["schema_version", "operation", "status", "ok", "artifacts", "summary", "errors"],
        )
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["operation"], "workbench_example")
        self.assertEqual(response["status"], "completed")
        self.assertTrue(response["ok"])
        self.assertEqual(response["artifacts"]["report"], str(Path("runs/example/report.json")))
        self.assertEqual(response["errors"], [])
        self.assertEqual(json.loads(json.dumps(response))["summary"]["count"], 1)

    def test_error_envelope_marks_response_not_ok(self) -> None:
        response = error_envelope(
            operation="workbench_validate_run",
            code="missing_artifact",
            message="validation_report.json was not found.",
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errors"][0]["code"], "missing_artifact")


class OperationContractTests(unittest.TestCase):
    def test_model_selection_response_summarizes_selected_model(self) -> None:
        response = model_selection_response(
            {
                "run_id": "run1",
                "project": "ai_workbench_mcp",
                "status": "selected",
                "selected_tier": "local_coding",
                "selected_model": {"provider": "goose", "model": "example-model"},
                "risk": "medium",
                "validation_strength": "strong",
                "complexity_score": 8,
                "complexity_band": "easy",
                "matched_rule": "bounded_work_local_default",
                "reason": "Recoverable bounded coding work can start locally.",
                "routing_feedback": {
                    "status": "advisory",
                    "recommendation": "prefer_current_tier",
                    "candidate_key": "recipe|profile|local_coding|medium|easy",
                },
            },
            artifacts={"model_selection": "runs/run1/model_selection.json"},
        )

        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertEqual(response["status"], "selected")
        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["selected_tier"], "local_coding")
        self.assertEqual(response["summary"]["provider"], "goose")
        self.assertEqual(response["summary"]["model"], "example-model")
        self.assertEqual(response["summary"]["routing_feedback_status"], "advisory")
        self.assertEqual(response["summary"]["routing_feedback_recommendation"], "prefer_current_tier")

    def test_validation_response_requires_passed_signoff_for_ok(self) -> None:
        response = validation_response(
            {
                "run_id": "run1",
                "project": "ai_workbench_mcp",
                "profile": "run_signoff",
                "overall_status": "needs_review",
                "sign_off_ready": False,
                "confidence": 0.75,
                "summary": {
                    "commands_passed": 2,
                    "commands_failed": 0,
                    "checks_passed": 3,
                    "checks_needs_review": 1,
                    "checks_failed": 0,
                },
            }
        )

        self.assertEqual(response["operation"], "workbench_validate_run")
        self.assertEqual(response["status"], "needs_review")
        self.assertFalse(response["ok"])
        self.assertEqual(response["summary"]["checks_needs_review"], 1)

    def test_quality_gate_response_only_accepts_accepted_decision(self) -> None:
        response = quality_gate_response(
            {
                "loop_type": "alternate_model_review",
                "required": True,
                "reason": "Validation failed.",
                "next_action": "manual_review_handoff",
                "accepted_pass": 0,
                "final_status": "review_required",
                "blocking_findings": ["validation failed"],
                "non_blocking_findings": [],
                "authoritative_model_output": "model_output.md",
                "authoritative_validation_report": "validation_report.json",
            }
        )

        self.assertEqual(response["operation"], "workbench_quality_gate")
        self.assertEqual(response["status"], "review_required")
        self.assertFalse(response["ok"])
        self.assertEqual(response["summary"]["blocking_findings"], 1)

    def test_run_analysis_response_reports_completed_metrics(self) -> None:
        response = run_analysis_response(
            {
                "runs_total": 4,
                "runs_passed": 3,
                "runs_failed": 0,
                "runs_needs_review": 1,
                "workflow_signoff_pass_rate": 0.75,
                "workflow_needs_review_rate": 0.25,
                "average_confidence": 0.9,
            }
        )

        self.assertEqual(response["operation"], "workbench_analyze_runs")
        self.assertEqual(response["status"], "completed")
        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["runs_total"], 4)

    def test_file_wrapper_reads_json_artifact_and_records_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"
            artifact.write_text(
                json.dumps(
                    {
                        "status": "selected",
                        "selected_tier": "frontier",
                        "selected_model": {"provider": "litellm", "model": "openai/gpt-5.5"},
                    }
                ),
                encoding="utf-8",
            )

            response = model_selection_file_response(artifact)

        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["selected_tier"], "frontier")
        self.assertEqual(response["artifacts"]["model_selection"], str(artifact))

    def test_select_model_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"

            with patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")):
                response = select_model(
                    project="ai_workbench_mcp",
                    task_type="implement",
                    risk="medium",
                    out=artifact,
                    prompt="implement_request_change_request",
                    complexity_score=13,
                )
            written = json.loads(artifact.read_text(encoding="utf-8"))
            events = read_jsonl(Path(tmpdir) / "events.jsonl")

        self.assertEqual(written["selected_tier"], "local_coding")
        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertEqual(response["status"], "selected")
        self.assertEqual(response["summary"]["selected_tier"], "local_coding")
        self.assertEqual(response["summary"]["provider"], "goose")
        self.assertEqual(response["summary"]["model"], "unsloth/gemma-4-E4B-it-GGUF:Q4_K_M")
        self.assertEqual(response["summary"]["risk"], "medium")
        self.assertEqual(response["summary"]["validation_strength"], "medium")
        self.assertEqual(response["summary"]["complexity_band"], "moderate")
        self.assertEqual(response["summary"]["matched_rule"], "easy_moderate_local_coding")
        self.assertEqual(written["routing_feedback"]["status"], "not_provided")
        self.assertEqual(response["summary"]["routing_feedback_status"], "not_provided")
        self.assertEqual(response["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_select_model")
        self.assertEqual(events[0]["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))

    def test_event_write_failure_does_not_change_core_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"

            with patch("ai_workbench_mcp.events.append_response_event", side_effect=OSError("readonly")):
                response = select_model(
                    project="ai_workbench_mcp",
                    task_type="implement",
                    risk="medium",
                    out=artifact,
                    prompt="implement_request_change_request",
                    complexity_score=13,
                )

        self.assertTrue(response["ok"])
        self.assertEqual(response["status"], "selected")
        self.assertEqual(response["artifacts"]["model_selection"], str(artifact))
        self.assertNotIn("events", response["artifacts"])

    def test_select_model_rejects_invalid_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = select_model(
                project="ai_workbench_mcp",
                task_type="implement",
                risk="urgent",
                out=Path(tmpdir) / "model_selection.json",
            )

        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "model_selection_failed")
        self.assertIn("risk must be one of", response["errors"][0]["message"])

    def test_validate_run_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = validate_run(
                    project="ai_workbench_mcp",
                    out_dir=tmpdir,
                    profile="scaffold",
                )
            written = json.loads((Path(tmpdir) / "validation_report.json").read_text(encoding="utf-8"))
            events = read_jsonl(Path(tmpdir) / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_validate_run")
        self.assertEqual(response["status"], "passed")
        self.assertEqual(response["artifacts"]["validation_report"], str(Path(tmpdir) / "validation_report.json"))
        self.assertEqual(written["overall_status"], "passed")
        self.assertEqual(response["summary"]["project"], "ai_workbench_mcp")
        self.assertEqual(response["summary"]["profile"], "scaffold")
        self.assertTrue(response["summary"]["sign_off_ready"])
        self.assertEqual(response["summary"]["commands_passed"], 9)
        self.assertEqual(response["summary"]["commands_failed"], 0)
        command_names = [command["name"] for command in written["commands_run"]]
        self.assertIn("model_registry_override_support", command_names)
        self.assertIn("event_ledger_import_smoke", command_names)
        self.assertIn("golden_eval_help", command_names)
        self.assertEqual(response["summary"]["checks_passed"], 3)
        self.assertEqual(response["summary"]["checks_needs_review"], 0)
        self.assertEqual(response["summary"]["checks_failed"], 0)
        self.assertEqual(response["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_validate_run")
        self.assertEqual(events[0]["status"], "passed")

    def test_quality_gate_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Captured Response",
                        "",
                        "Summary:",
                        "Implemented a bounded change.",
                        "",
                        "Files touched:",
                        "- tools/example.py",
                        "",
                        "Validation run:",
                        "- pytest -> passed",
                        "",
                        "Risks / follow-ups:",
                        "- None.",
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "validation_report.json").write_text(
                json.dumps({"overall_status": "passed", "confidence": 1.0}),
                encoding="utf-8",
            )
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = quality_gate(
                    project="ai_workbench_mcp",
                    run_dir=run_dir,
                    mode="auto",
                    risk="low",
                )
            written = json.loads((run_dir / "revision_decision.json").read_text(encoding="utf-8"))
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_quality_gate")
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["artifacts"]["revision_decision"], str(run_dir / "revision_decision.json"))
        self.assertEqual(written["final_status"], "accepted")
        self.assertEqual(response["summary"]["loop_type"], "none")
        self.assertFalse(response["summary"]["required"])
        self.assertEqual(response["summary"]["accepted_pass"], 1)
        self.assertEqual(response["summary"]["blocking_findings"], 0)
        self.assertEqual(response["summary"]["non_blocking_findings"], 0)
        self.assertEqual(response["artifacts"]["events"], str(run_dir / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_quality_gate")
        self.assertEqual(events[0]["status"], "accepted")

    def test_analyze_runs_direct_call_writes_artifacts_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_dir = root / "runs"
            run_dir = runs_dir / "run1"
            run_dir.mkdir(parents=True)
            (run_dir / "run_log.jsonl").write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-12T10:00:00",
                        "model_tier": "local_coding",
                        "decision": "model_response_captured",
                        "prompt": "implement_request_change_request",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "model_selection.json").write_text(
                json.dumps(
                    {
                        "selected_tier": "local_coding",
                        "task_type": "implementation",
                        "risk": "medium",
                        "complexity_band": "moderate",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "validation_report.json").write_text(
                json.dumps({"overall_status": "passed", "confidence": 0.9}),
                encoding="utf-8",
            )
            out_dir = root / "reports"
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = analyze_runs(
                    runs_dir=runs_dir,
                    out_dir=out_dir,
                    evals_dir=root / "evals",
                )
            written = json.loads((out_dir / "run_metrics.json").read_text(encoding="utf-8"))
            events = read_jsonl(out_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_analyze_runs")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["artifacts"]["run_metrics"], str(out_dir / "run_metrics.json"))
        self.assertEqual(response["artifacts"]["run_summary"], str(out_dir / "run_summary.md"))
        self.assertEqual(response["artifacts"]["dashboard"], str(out_dir / "run_dashboard.html"))
        self.assertEqual(written["runs_total"], 1)
        self.assertEqual(response["summary"]["runs_total"], 1)
        self.assertEqual(response["summary"]["runs_passed"], 1)
        self.assertEqual(response["summary"]["runs_failed"], 0)
        self.assertEqual(response["summary"]["runs_needs_review"], 0)
        self.assertEqual(response["summary"]["workflow_signoff_pass_rate"], 1.0)
        self.assertEqual(response["summary"]["average_confidence"], 0.9)
        self.assertEqual(response["artifacts"]["events"], str(out_dir / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_analyze_runs")
        self.assertEqual(events[0]["status"], "completed")

    def test_run_analysis_file_response_records_dashboard_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metrics = root / "run_metrics.json"
            summary = root / "run_summary.md"
            dashboard = root / "run_dashboard.html"
            metrics.write_text(json.dumps({"runs_total": 1, "runs_passed": 1}), encoding="utf-8")
            summary.write_text("# Summary\n", encoding="utf-8")
            dashboard.write_text("<!doctype html>\n", encoding="utf-8")

            response = run_analysis_file_response(metrics, summary, dashboard)

        self.assertTrue(response["ok"])
        self.assertEqual(response["artifacts"]["run_metrics"], str(metrics))
        self.assertEqual(response["artifacts"]["run_summary"], str(summary))
        self.assertEqual(response["artifacts"]["dashboard"], str(dashboard))


if __name__ == "__main__":
    unittest.main()
