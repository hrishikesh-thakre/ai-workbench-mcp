import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.tools.run_analyze import run_analysis_payload


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_model_output(run_dir: Path, response_source: str = "goose") -> None:
    (run_dir / "model_output.md").write_text(
        "\n".join(
            [
                "# Model Output",
                "",
                "## Execution Metadata",
                "",
                f"- Response Source: `{response_source}`",
                "- Status: `response_captured`",
                "",
                "## Normalized Response",
                "",
                "Summary:",
                "Captured sample response.",
                "",
                "Files touched:",
                "- src/example.py",
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


def write_model_call_metadata(run_dir: Path) -> None:
    write_json(
        run_dir / "model_call_metadata.json",
        {
            "provider": "litellm",
            "tier": "local_coding",
            "model": "local-coding-tier",
            "usage_summary": {
                "prompt_tokens": 900,
                "completion_tokens": 400,
                "total_tokens": 1300,
                "cached_input_tokens": 100,
                "uncached_input_tokens": 800,
            },
            "estimated_cost_usd": 0.01234567,
            "pricing_source": "provider_reported",
            "duration_ms": 2300,
        },
    )


def write_sample_run(runs_dir: Path) -> Path:
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
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "run1",
            "project": "ai_workbench_mcp",
            "task_type": "implementation",
            "prompt": "implement_request_change_request",
            "recipe": "workbench-engineering-acceptance.yaml",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "local_coding",
            "task_type": "implementation",
            "risk": "medium",
            "complexity_band": "moderate",
            "prompt": "implement_request_change_request",
        },
    )
    write_json(
        run_dir / "validation_report.json",
        {
            "overall_status": "passed",
            "sign_off_ready": True,
            "confidence": 0.9,
            "profile": "run_signoff",
            "missing_context_notes": {"needs_review": [], "info": []},
        },
    )
    write_json(
        run_dir / "revision_decision.json",
        {
            "final_status": "accepted",
            "loop_type": "none",
        },
    )
    write_model_output(run_dir)
    return run_dir


def write_revision_required_run(runs_dir: Path) -> Path:
    run_dir = runs_dir / "run2"
    run_dir.mkdir(parents=True)
    (run_dir / "run_log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-12T11:00:00",
                "model_tier": "frontier",
                "decision": "model_response_captured",
                "prompt": "bug_root_cause_investigation",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "run2",
            "project": "ai_workbench_mcp",
            "task_type": "test",
            "prompt": "bug_root_cause_investigation",
            "recipe": "workbench-test-fix-acceptance.yaml",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "frontier",
            "task_type": "test",
            "risk": "medium",
            "complexity_band": "moderate",
            "prompt": "bug_root_cause_investigation",
        },
    )
    write_json(
        run_dir / "validation_report.json",
        {
            "overall_status": "failed",
            "sign_off_ready": False,
            "confidence": 0.4,
            "profile": "test_fix",
            "commands_run": [
                {
                    "name": "full_test_suite",
                    "status": "failed",
                    "exit_code": 1,
                }
            ],
            "artifact_checks": [],
            "review_checks": [
                {
                    "name": "model_output_status",
                    "status": "needs_review",
                }
            ],
            "missing_context_notes": {"needs_review": ["missing failing test output"], "info": []},
            "reason_codes": ["test_fix.required_test_failed"],
        },
    )
    write_json(
        run_dir / "revision_decision.json",
        {
            "final_status": "revision_required",
            "loop_type": "blocking_findings",
            "required": True,
            "reason_codes": ["quality_loop.validation_failed"],
        },
    )
    write_model_output(run_dir)
    return run_dir


def write_failed_run(runs_dir: Path) -> Path:
    run_dir = runs_dir / "run3"
    run_dir.mkdir(parents=True)
    (run_dir / "run_log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-12T12:00:00",
                "model_tier": "local_coding",
                "decision": "model_response_captured",
                "prompt": "implement_request_change_request",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "run3",
            "project": "ai_workbench_mcp",
            "task_type": "implementation",
            "prompt": "implement_request_change_request",
            "recipe": "workbench-engineering-acceptance.yaml",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "local_coding",
            "task_type": "implementation",
            "risk": "low",
            "complexity_band": "easy",
            "prompt": "implement_request_change_request",
        },
    )
    write_json(
        run_dir / "validation_report.json",
        {
            "overall_status": "failed",
            "sign_off_ready": False,
            "confidence": 0.3,
            "profile": "low_risk_coding",
            "commands_run": [
                {
                    "name": "full_test_suite",
                    "status": "failed",
                    "exit_code": 1,
                }
            ],
            "artifact_checks": [],
            "review_checks": [],
            "missing_context_notes": {"needs_review": [], "info": []},
        },
    )
    write_json(
        run_dir / "revision_decision.json",
        {
            "final_status": "failed",
            "loop_type": "none",
            "required": False,
        },
    )
    write_model_output(run_dir)
    return run_dir


def write_codex_sample_run(runs_dir: Path) -> Path:
    run_dir = runs_dir / "run4"
    run_dir.mkdir(parents=True)
    (run_dir / "run_log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-12T13:00:00",
                "model_tier": "local_coding",
                "decision": "model_response_captured",
                "prompt": "implement_request_change_request",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "run4",
            "project": "ai_workbench_mcp",
            "task_type": "implementation",
            "prompt": "implement_request_change_request",
            "recipe": "workbench-engineering-acceptance.yaml",
            "execution_host": "codex",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "local_coding",
            "task_type": "implementation",
            "risk": "medium",
            "complexity_band": "moderate",
            "prompt": "implement_request_change_request",
        },
    )
    write_json(
        run_dir / "validation_report.json",
        {
            "overall_status": "passed",
            "sign_off_ready": True,
            "confidence": 0.95,
            "profile": "run_signoff",
            "missing_context_notes": {"needs_review": [], "info": []},
        },
    )
    write_json(
        run_dir / "revision_decision.json",
        {
            "final_status": "accepted",
            "loop_type": "none",
        },
    )
    write_model_output(run_dir, response_source="codex")
    return run_dir


def write_tool_smoke_like_run(runs_dir: Path) -> Path:
    run_dir = runs_dir / "tool-smoke"
    run_dir.mkdir(parents=True)
    (run_dir / "run_log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-12T14:00:00",
                "model_tier": "local_coding",
                "decision": "model_selected",
                "prompt": "implement_request_change_request",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "tool-smoke",
            "project": "ai_workbench_mcp",
            "task_type": "implementation",
            "prompt": "implement_request_change_request",
            "execution_host": "codex",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "local_coding",
            "task_type": "implementation",
            "risk": "low",
            "complexity_band": "easy",
            "prompt": "implement_request_change_request",
        },
    )
    return run_dir


def write_fixture_repair_run_without_recipe(runs_dir: Path) -> Path:
    run_dir = runs_dir / "fixture-repair"
    run_dir.mkdir(parents=True)
    (run_dir / "run_log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-12T15:00:00",
                "model_tier": "local_coding",
                "decision": "model_response_captured",
                "prompt": "bug_root_cause_investigation",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        run_dir / "task_metadata.json",
        {
            "run_id": "fixture-repair",
            "project": "ai_workbench_mcp",
            "task_type": "test",
            "prompt": "bug_root_cause_investigation",
        },
    )
    write_json(
        run_dir / "model_selection.json",
        {
            "selected_tier": "local_coding",
            "task_type": "test",
            "risk": "low",
            "complexity_band": "easy",
            "prompt": "bug_root_cause_investigation",
            "validation_profile": "fixture_repair_proof",
        },
    )
    write_json(
        run_dir / "validation_report.json",
        {
            "overall_status": "passed",
            "sign_off_ready": True,
            "confidence": 1.0,
            "profile": "fixture_repair_proof",
            "artifact_checks": [
                {"name": "task_test_command", "status": "passed"},
                {"name": "changed_file_policy", "status": "passed"},
            ],
            "commands_run": [
                {"name": "task_test_command", "status": "passed"},
            ],
            "missing_context_notes": {"needs_review": [], "info": []},
        },
    )
    write_json(run_dir / "revision_decision.json", {"final_status": "accepted", "loop_type": "none"})
    write_model_output(run_dir)
    return run_dir


class RunAnalyzePayloadTests(unittest.TestCase):
    def test_run_analysis_payload_writes_metrics_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)
            written = json.loads((out_dir / "run_metrics.json").read_text(encoding="utf-8"))
            summary = (out_dir / "run_summary.md").read_text(encoding="utf-8")
            dashboard = (out_dir / "run_dashboard.html").read_text(encoding="utf-8")

        self.assertEqual(metrics, written)
        self.assertEqual(metrics["evidence_scope"], "all")
        self.assertEqual(metrics["excluded_runs_total"], 0)
        self.assertEqual(metrics["excluded_runs_by_reason"], {})
        self.assertEqual(metrics["runs_total"], 1)
        self.assertEqual(metrics["runs_passed"], 1)
        self.assertEqual(metrics["runs_failed"], 0)
        self.assertEqual(metrics["runs_needs_review"], 0)
        self.assertEqual(metrics["workflow_signoff_pass_rate"], 1.0)
        self.assertEqual(metrics["average_confidence"], 0.9)
        self.assertEqual(metrics["accepted_runs_total"], 1)
        self.assertEqual(metrics["acceptance_rate"], 1.0)
        self.assertEqual(metrics["accepted_runs_by_recipe"], {"workbench-engineering-acceptance.yaml": 1})
        self.assertEqual(metrics["accepted_runs_by_execution_host"], {"goose": 1})
        self.assertEqual(metrics["accepted_runs_by_response_source"], {"goose": 1})
        self.assertEqual(metrics["execution_host_counts"], {"goose": 1})
        self.assertEqual(metrics["response_source_counts"], {"goose": 1})
        self.assertEqual(metrics["accepted_runs_by_validation_profile"], {"run_signoff": 1})
        self.assertEqual(metrics["accepted_runs_by_selected_tier"], {"local_coding": 1})
        self.assertEqual(metrics["outcome_counts"], {"accepted": 1})
        self.assertEqual(metrics["review_required_runs_total"], 0)
        self.assertEqual(metrics["failed_runs_total"], 0)
        self.assertEqual(metrics["quality_gate_outcomes"], {"accepted": 1})
        self.assertEqual(metrics["response_captured_count"], 1)
        self.assertIn("## Acceptance Analytics", summary)
        self.assertIn("- Evidence scope: all", summary)
        self.assertIn("- Excluded runs total: 0", summary)
        self.assertIn("### Public Outcomes By Execution Host", summary)
        self.assertIn("| goose | 1 | 0 | 0 | 0 | 1 | 1.0 | 0.0 | 0.0 |", summary)
        self.assertIn("### Public Outcomes By Response Source", summary)
        self.assertIn("| workbench-engineering-acceptance.yaml | 1 | 0 | 0 | 0 | 1 | 1.0 | 0.0 | 0.0 |", summary)
        self.assertIn("| run1 | passed | implementation | false |", summary)
        self.assertIn("Workbench Evidence Dashboard", dashboard)
        self.assertIn("Accepted", dashboard)
        self.assertIn("Review Required", dashboard)
        self.assertIn("Failed", dashboard)
        self.assertIn("By Execution Host", dashboard)
        self.assertIn("By Response Source", dashboard)
        self.assertIn("Agent / Model", dashboard)
        self.assertIn("Policy", dashboard)
        self.assertIn("Failure Reasons", dashboard)
        self.assertIn("Cost / Time", dashboard)
        self.assertIn("workbench-engineering-acceptance.yaml", dashboard)
        self.assertIn("task_metadata.json", dashboard)

    def test_run_analysis_payload_tracks_run_cost_and_time_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            run_dir = write_sample_run(runs_dir)
            write_model_call_metadata(run_dir)
            report = json.loads((run_dir / "validation_report.json").read_text(encoding="utf-8"))
            report["commands_run"] = [
                {"name": "unit_tests", "status": "passed", "exit_code": 0, "duration_ms": 120},
                {"name": "lint", "status": "passed", "exit_code": 0, "duration_ms": 55},
            ]
            write_json(run_dir / "validation_report.json", report)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)
            summary = (out_dir / "run_summary.md").read_text(encoding="utf-8")
            dashboard = (out_dir / "run_dashboard.html").read_text(encoding="utf-8")

        self.assertEqual(metrics["total_tokens_tracked"], 1300)
        self.assertEqual(metrics["runs_with_token_data"], 1)
        self.assertEqual(metrics["total_estimated_cost_usd"], 0.01234567)
        self.assertEqual(metrics["runs_with_cost_data"], 1)
        self.assertEqual(metrics["runs_with_cost_data_ids"], ["run1"])
        self.assertEqual(metrics["cost_tracking"]["runs_with_cost_data_ids"], ["run1"])
        self.assertEqual(metrics["time_tracking"]["provider_calls_with_time_data"], 1)
        self.assertEqual(metrics["time_tracking"]["total_provider_duration_ms"], 2300)
        self.assertEqual(metrics["time_tracking"]["runs_with_provider_time_data"], 1)
        self.assertEqual(metrics["time_tracking"]["validation_runs_with_time_data"], 1)
        self.assertEqual(metrics["time_tracking"]["total_validation_duration_ms"], 175)
        self.assertEqual(metrics["run_cost_time"]["run1"]["provider_calls"], 1)
        self.assertEqual(metrics["run_cost_time"]["run1"]["providers"], {"litellm": 1})
        self.assertEqual(metrics["run_cost_time"]["run1"]["models"], {"local-coding-tier": 1})
        self.assertEqual(metrics["run_cost_time"]["run1"]["tiers"], {"local_coding": 1})
        self.assertTrue(metrics["run_cost_time"]["run1"]["has_token_data"])
        self.assertTrue(metrics["run_cost_time"]["run1"]["has_cost_data"])
        self.assertTrue(metrics["run_cost_time"]["run1"]["has_provider_time_data"])
        self.assertTrue(metrics["run_cost_time"]["run1"]["has_validation_time_data"])
        self.assertEqual(metrics["run_cost_time"]["run1"]["total_tokens"], 1300)
        self.assertEqual(metrics["run_cost_time"]["run1"]["estimated_cost_usd"], 0.01234567)
        self.assertEqual(metrics["run_cost_time"]["run1"]["provider_duration_ms"], 2300)
        self.assertEqual(metrics["run_cost_time"]["run1"]["validation_duration_ms"], 175)
        self.assertIn("## Time Tracking", summary)
        self.assertIn("| run1 | accepted | goose | goose | litellm | local-coding-tier | run_signoff | accepted | None recorded | 1300 | $0.01234567 | 2.30s | 175ms |", summary)
        self.assertIn("Cost And Time Evidence", dashboard)
        self.assertIn("local-coding-tier", dashboard)
        self.assertIn("$0.01234567", dashboard)
        self.assertIn("2.30s", dashboard)
        self.assertIn("175ms", dashboard)

    def test_run_analysis_payload_groups_goose_and_codex_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            write_codex_sample_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)

        self.assertEqual(metrics["runs_total"], 2)
        self.assertEqual(metrics["execution_host_counts"], {"goose": 1, "codex": 1})
        self.assertEqual(metrics["response_source_counts"], {"goose": 1, "codex": 1})
        self.assertEqual(metrics["accepted_runs_by_execution_host"], {"goose": 1, "codex": 1})
        self.assertEqual(metrics["accepted_runs_by_response_source"], {"goose": 1, "codex": 1})
        self.assertEqual(metrics["outcome_breakdown"]["by_execution_host"]["goose"]["accepted"], 1)
        self.assertEqual(metrics["outcome_breakdown"]["by_execution_host"]["codex"]["accepted"], 1)
        self.assertEqual(metrics["outcome_breakdown"]["by_response_source"]["codex"]["accepted"], 1)
        candidate_key = "workbench-engineering-acceptance.yaml|run_signoff|local_coding|medium|moderate"
        self.assertEqual(metrics["routing_feedback_candidates"][candidate_key]["total"], 2)
        self.assertNotIn("codex", candidate_key)

    def test_run_analysis_payload_default_all_counts_logged_tool_smoke_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            write_tool_smoke_like_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)

        self.assertEqual(metrics["evidence_scope"], "all")
        self.assertEqual(metrics["runs_total"], 2)
        self.assertEqual(metrics["excluded_runs_total"], 0)
        self.assertEqual(metrics["outcome_counts"], {"accepted": 1, "other": 1})
        self.assertEqual(metrics["other_runs_total"], 1)
        tool_smoke_key = "unknown|unknown|local_coding|low|easy"
        self.assertEqual(metrics["routing_feedback_candidates"][tool_smoke_key]["other"], 1)

    def test_run_analysis_payload_complete_scope_excludes_tool_smoke_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            write_tool_smoke_like_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
                evidence_scope="complete",
            )

            metrics = run_analysis_payload(args)
            written = json.loads((out_dir / "run_metrics.json").read_text(encoding="utf-8"))
            summary = (out_dir / "run_summary.md").read_text(encoding="utf-8")

        self.assertEqual(metrics, written)
        self.assertEqual(metrics["evidence_scope"], "complete")
        self.assertEqual(metrics["runs_total"], 1)
        self.assertEqual(metrics["excluded_runs_total"], 1)
        self.assertEqual(
            metrics["excluded_runs_by_reason"],
            {"missing_validation_report": 1, "missing_revision_decision": 1},
        )
        self.assertEqual(metrics["outcome_counts"], {"accepted": 1})
        self.assertNotIn("unknown|unknown|local_coding|low|easy", metrics["routing_feedback_candidates"])
        self.assertIn("- Evidence scope: complete", summary)
        self.assertIn("- Excluded runs total: 1", summary)

    def test_run_analysis_payload_maps_fixture_repair_proof_to_test_fix_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_fixture_repair_run_without_recipe(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
                evidence_scope="complete",
            )

            metrics = run_analysis_payload(args)

        candidate_key = "workbench-test-fix-acceptance.yaml|fixture_repair_proof|local_coding|low|easy"
        self.assertEqual(metrics["accepted_runs_by_recipe"], {"workbench-test-fix-acceptance.yaml": 1})
        self.assertEqual(metrics["routing_feedback_candidates"][candidate_key]["accepted"], 1)
        self.assertEqual(metrics["routing_feedback_candidates"][candidate_key]["total"], 1)

    def test_run_analysis_payload_summarizes_acceptance_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            write_revision_required_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)
            summary = (out_dir / "run_summary.md").read_text(encoding="utf-8")
            dashboard = (out_dir / "run_dashboard.html").read_text(encoding="utf-8")

        self.assertEqual(metrics["runs_total"], 2)
        self.assertEqual(metrics["accepted_runs_total"], 1)
        self.assertEqual(metrics["acceptance_rate"], 0.5)
        self.assertEqual(metrics["outcome_counts"], {"accepted": 1, "review_required": 1})
        self.assertEqual(metrics["review_required_runs_total"], 1)
        self.assertEqual(metrics["failed_runs_total"], 0)
        self.assertEqual(
            metrics["accepted_runs_by_recipe"],
            {"workbench-engineering-acceptance.yaml": 1},
        )
        self.assertEqual(
            metrics["quality_gate_outcomes"],
            {"accepted": 1, "revision_required": 1},
        )
        self.assertEqual(metrics["failure_reasons"]["command_failed:full_test_suite"], 1)
        self.assertEqual(metrics["failure_reasons"]["quality_gate:revision_required"], 1)
        self.assertEqual(metrics["failure_reasons"]["test_fix.required_test_failed"], 1)
        self.assertEqual(metrics["failure_reasons"]["quality_loop.validation_failed"], 1)
        self.assertEqual(
            metrics["acceptance_breakdown"]["by_recipe"]["workbench-test-fix-acceptance.yaml"],
            {
                "accepted": 0,
                "needs_review": 1,
                "failed": 0,
                "other": 0,
                "total": 1,
                "acceptance_rate": 0.0,
            },
        )
        self.assertEqual(
            metrics["outcome_breakdown"]["by_recipe"]["workbench-test-fix-acceptance.yaml"],
            {
                "accepted": 0,
                "review_required": 1,
                "failed": 0,
                "other": 0,
                "total": 1,
                "acceptance_rate": 0.0,
                "review_rate": 1.0,
                "failure_rate": 0.0,
            },
        )
        candidate_key = "workbench-test-fix-acceptance.yaml|test_fix|frontier|medium|moderate"
        self.assertEqual(metrics["routing_feedback_candidates"][candidate_key]["review_required"], 1)
        self.assertEqual(metrics["routing_feedback_candidates"][candidate_key]["review_rate"], 1.0)
        self.assertEqual(
            metrics["routing_feedback_candidates"][candidate_key]["top_failure_reasons"]["command_failed:full_test_suite"],
            1,
        )
        self.assertEqual(metrics["cost_tracking"]["total_estimated_cost_usd"], 0.0)
        self.assertEqual(metrics["cost_tracking"]["runs_with_cost_data"], 0)
        self.assertIn("| workbench-test-fix-acceptance.yaml | 0 | 1 | 0 | 0 | 1 | 0.0 | 1.0 | 0.0 |", summary)
        self.assertIn("Routing Feedback Candidates", dashboard)
        self.assertIn("command_failed:full_test_suite=1", dashboard)
        self.assertIn("No provider cost evidence was found", dashboard)

    def test_run_analysis_payload_keeps_failed_bucket_separate_from_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)
            write_revision_required_run(runs_dir)
            write_failed_run(runs_dir)
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            metrics = run_analysis_payload(args)

        self.assertEqual(metrics["runs_total"], 3)
        self.assertEqual(metrics["outcome_counts"], {"accepted": 1, "review_required": 1, "failed": 1})
        self.assertEqual(metrics["accepted_runs_total"], 1)
        self.assertEqual(metrics["review_required_runs_total"], 1)
        self.assertEqual(metrics["failed_runs_total"], 1)
        self.assertEqual(sum(metrics["outcome_counts"].values()), metrics["runs_total"])
        self.assertEqual(
            metrics["outcome_breakdown"]["by_validation_profile"]["low_risk_coding"]["failed"],
            1,
        )

    def test_run_analysis_payload_raises_for_missing_runs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = SimpleNamespace(
                runs_dir=str(Path(tmpdir) / "missing-runs"),
                task_type=None,
                since=None,
                out_dir=None,
                evals_dir=str(Path(tmpdir) / "evals"),
            )

            with self.assertRaises(FileNotFoundError) as raised:
                run_analysis_payload(args)

        self.assertIn("runs_dir_missing=", str(raised.exception))

    def test_dashboard_uses_relative_links_and_does_not_embed_sensitive_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            run_dir = write_sample_run(runs_dir)
            (run_dir / "model_output.md").write_text(
                "# Model Output\n\nRAW MODEL OUTPUT BODY SHOULD NOT APPEAR\n",
                encoding="utf-8",
            )
            write_json(
                run_dir / "task_metadata.json",
                {
                    "run_id": "run1",
                    "project": "ai_workbench_mcp",
                    "task_type": "implementation",
                    "prompt": "implement_request_change_request",
                    "recipe": "<script>alert('x')</script>",
                },
            )
            args = SimpleNamespace(
                runs_dir=str(runs_dir),
                task_type=None,
                since=None,
                out_dir=str(out_dir),
                evals_dir=str(tmp_path / "evals"),
            )

            run_analysis_payload(args)
            dashboard = (out_dir / "run_dashboard.html").read_text(encoding="utf-8")

        self.assertNotRegex(dashboard, re.compile(r"(?<![A-Za-z])[A-Za-z]:\\"))
        self.assertNotIn(str(tmp_path), dashboard)
        self.assertNotIn("RAW MODEL OUTPUT BODY SHOULD NOT APPEAR", dashboard)
        self.assertNotIn("<script>alert('x')</script>", dashboard)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", dashboard)
        self.assertIn("href=\"../runs/run1/model_output.md\"", dashboard)
        self.assertIn(">model_output.md</a>", dashboard)

    def test_cli_output_prints_dashboard_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            out_dir = tmp_path / "reports"
            write_sample_run(runs_dir)

            result = subprocess.run(
                [
                    sys.executable,
                    "tools/run_analyze.py",
                    "--runs-dir",
                    str(runs_dir),
                    "--out-dir",
                    str(out_dir),
                    "--evals-dir",
                    str(tmp_path / "evals"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("run_metrics=", result.stdout)
        self.assertIn("run_summary=", result.stdout)
        self.assertIn("run_dashboard=", result.stdout)


if __name__ == "__main__":
    unittest.main()
