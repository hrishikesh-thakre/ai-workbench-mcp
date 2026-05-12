import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from run_analyze import run_analysis_payload


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


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
                    "name": "unit_tests",
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
        },
    )
    write_json(
        run_dir / "revision_decision.json",
        {
            "final_status": "revision_required",
            "loop_type": "blocking_findings",
            "required": True,
        },
    )
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

        self.assertEqual(metrics, written)
        self.assertEqual(metrics["runs_total"], 1)
        self.assertEqual(metrics["runs_passed"], 1)
        self.assertEqual(metrics["runs_failed"], 0)
        self.assertEqual(metrics["runs_needs_review"], 0)
        self.assertEqual(metrics["workflow_signoff_pass_rate"], 1.0)
        self.assertEqual(metrics["average_confidence"], 0.9)
        self.assertEqual(metrics["accepted_runs_total"], 1)
        self.assertEqual(metrics["acceptance_rate"], 1.0)
        self.assertEqual(metrics["accepted_runs_by_recipe"], {"workbench-engineering-acceptance.yaml": 1})
        self.assertEqual(metrics["accepted_runs_by_validation_profile"], {"run_signoff": 1})
        self.assertEqual(metrics["accepted_runs_by_selected_tier"], {"local_coding": 1})
        self.assertEqual(metrics["quality_gate_outcomes"], {"accepted": 1})
        self.assertEqual(metrics["response_captured_count"], 1)
        self.assertIn("## Acceptance Analytics", summary)
        self.assertIn("| workbench-engineering-acceptance.yaml | 1 | 0 | 0 | 0 | 1 | 1.0 |", summary)
        self.assertIn("| run1 | passed | implementation | false |", summary)

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

        self.assertEqual(metrics["runs_total"], 2)
        self.assertEqual(metrics["accepted_runs_total"], 1)
        self.assertEqual(metrics["acceptance_rate"], 0.5)
        self.assertEqual(
            metrics["accepted_runs_by_recipe"],
            {"workbench-engineering-acceptance.yaml": 1},
        )
        self.assertEqual(
            metrics["quality_gate_outcomes"],
            {"accepted": 1, "revision_required": 1},
        )
        self.assertEqual(metrics["failure_reasons"]["command_failed:unit_tests"], 1)
        self.assertEqual(metrics["failure_reasons"]["quality_gate:revision_required"], 1)
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
        self.assertIn("| workbench-test-fix-acceptance.yaml | 0 | 1 | 0 | 0 | 1 | 0.0 |", summary)

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


if __name__ == "__main__":
    unittest.main()
