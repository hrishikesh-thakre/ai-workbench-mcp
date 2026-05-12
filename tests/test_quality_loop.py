import unittest
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from quality_loop import classify_review_output, determine_auto_trigger, main, read_json


class ClassifyReviewOutputTests(unittest.TestCase):
    def test_non_blocking_label_does_not_count_as_blocking(self) -> None:
        blocking, non_blocking = classify_review_output(
            "- Non-blocking: The response is structurally complete."
        )

        self.assertEqual(blocking, [])
        self.assertEqual(
            non_blocking,
            ["Non-blocking: The response is structurally complete."],
        )

    def test_blocking_label_counts_as_blocking(self) -> None:
        blocking, non_blocking = classify_review_output(
            "- Blocking: Missing validation evidence."
        )

        self.assertEqual(blocking, ["Blocking: Missing validation evidence."])
        self.assertEqual(non_blocking, [])

    def test_non_blocking_prefix_takes_precedence_over_must_fix_terms(self) -> None:
        blocking, non_blocking = classify_review_output(
            "- Non-blocking: Must fix later if the project raises its quality bar."
        )

        self.assertEqual(blocking, [])
        self.assertEqual(
            non_blocking,
            ["Non-blocking: Must fix later if the project raises its quality bar."],
        )

    def test_mixed_findings_classify_blocking_and_non_blocking_signals(self) -> None:
        blocking, non_blocking = classify_review_output(
            "\n".join(
                [
                    "- Blocking: Missing regression coverage for retry behavior.",
                    "- Consider adding an assertion for the output path.",
                    "- Nit: tighten the test name.",
                    "- revise_required because the decision file is not checked.",
                    "- must fix the missing validation evidence claim.",
                ]
            )
        )

        self.assertEqual(
            blocking,
            [
                "Blocking: Missing regression coverage for retry behavior.",
                "revise_required because the decision file is not checked.",
                "must fix the missing validation evidence claim.",
            ],
        )
        self.assertEqual(
            non_blocking,
            [
                "Consider adding an assertion for the output path.",
                "Nit: tighten the test name.",
            ],
        )

    def test_unrecognized_lines_do_not_create_findings(self) -> None:
        blocking, non_blocking = classify_review_output(
            "\n".join(
                [
                    "Summary: Review completed.",
                    "- Looks good overall.",
                    "",
                    "* Accepted.",
                ]
            )
        )

        self.assertEqual(blocking, [])
        self.assertEqual(non_blocking, [])

    def test_classifier_strips_list_markers_and_outer_whitespace(self) -> None:
        blocking, non_blocking = classify_review_output(
            "\n".join(
                [
                    "  * Blocking: Missing review of acceptance criteria.  ",
                    "\t- Non blocking: wording can be tighter. ",
                ]
            )
        )

        self.assertEqual(blocking, ["Blocking: Missing review of acceptance criteria."])
        self.assertEqual(non_blocking, ["Non blocking: wording can be tighter."])


class EvaluateReviewModeTests(unittest.TestCase):
    def test_evaluate_review_requires_revision_when_blocking_findings_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text("Summary: placeholder\n", encoding="utf-8")
            (run_dir / "review_output.md").write_text(
                "\n".join(
                    [
                        "- Blocking: Missing validation evidence.",
                        "- Non-blocking: Add one more regression test.",
                    ]
                ),
                encoding="utf-8",
            )

            argv = [
                "quality_loop.py",
                "--project",
                "ai_workbench",
                "--run-dir",
                str(run_dir),
                "--mode",
                "evaluate_review",
            ]

            with patch("quality_loop.load_project_config", return_value=SimpleNamespace(root=run_dir)):
                with patch.object(sys, "argv", argv):
                    exit_code = main()

            self.assertEqual(exit_code, 2)
            decision = read_json(run_dir / "revision_decision.json")
            self.assertEqual(decision["loop_type"], "alternate_model_review")
            self.assertEqual(decision["final_status"], "revision_required")
            self.assertEqual(decision["next_action"], "await_revision")
            self.assertEqual(decision["blocking_findings"], ["Blocking: Missing validation evidence."])
            self.assertEqual(
                decision["non_blocking_findings"],
                ["Non-blocking: Add one more regression test."],
            )

    def test_evaluate_review_accepts_when_only_non_blocking_findings_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text("Summary: placeholder\n", encoding="utf-8")
            (run_dir / "review_output.md").write_text(
                "\n".join(
                    [
                        "- Non blocking: Clarify the summary wording.",
                        "- Consider covering one more edge case later.",
                    ]
                ),
                encoding="utf-8",
            )

            argv = [
                "quality_loop.py",
                "--project",
                "ai_workbench",
                "--run-dir",
                str(run_dir),
                "--mode",
                "evaluate_review",
            ]

            with patch("quality_loop.load_project_config", return_value=SimpleNamespace(root=run_dir)):
                with patch.object(sys, "argv", argv):
                    exit_code = main()

            self.assertEqual(exit_code, 0)
            decision = read_json(run_dir / "revision_decision.json")
            self.assertEqual(decision["loop_type"], "alternate_model_review")
            self.assertEqual(decision["final_status"], "accepted")
            self.assertEqual(decision["next_action"], "none")
            self.assertEqual(decision["blocking_findings"], [])
            self.assertEqual(
                decision["non_blocking_findings"],
                [
                    "Non blocking: Clarify the summary wording.",
                    "Consider covering one more edge case later.",
                ],
            )

    def test_evaluate_review_accepts_when_review_contains_only_unclassified_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text("Summary: placeholder\n", encoding="utf-8")
            (run_dir / "review_output.md").write_text(
                "\n".join(
                    [
                        "Summary: Review completed.",
                        "- Looks good overall.",
                        "* Accepted.",
                    ]
                ),
                encoding="utf-8",
            )

            argv = [
                "quality_loop.py",
                "--project",
                "ai_workbench",
                "--run-dir",
                str(run_dir),
                "--mode",
                "evaluate_review",
            ]

            with patch("quality_loop.load_project_config", return_value=SimpleNamespace(root=run_dir)):
                with patch.object(sys, "argv", argv):
                    exit_code = main()

            self.assertEqual(exit_code, 0)
            decision = read_json(run_dir / "revision_decision.json")
            self.assertEqual(decision["final_status"], "accepted")
            self.assertEqual(decision["blocking_findings"], [])
            self.assertEqual(decision["non_blocking_findings"], [])


class DetermineAutoTriggerTests(unittest.TestCase):
    def test_two_candidate_outputs_trigger_pairwise_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text(
                "\n".join(
                    [
                        "Summary:",
                        "Candidate A.",
                        "",
                        "Files touched:",
                        "- a.py",
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
            (run_dir / "model_output_2.md").write_text("Summary:\nCandidate B.\n", encoding="utf-8")

            loop_type, reason, blocking, non_blocking = determine_auto_trigger(
                run_dir=run_dir,
                model_output_text=(run_dir / "model_output.md").read_text(encoding="utf-8"),
                report={"overall_status": "passed"},
                risk="low",
                config={
                    "enabled": True,
                    "same_model_retry": {"enabled": True},
                    "pairwise_compare": {"enabled": True},
                    "alternate_model_review": {"enabled": True},
                },
            )

        self.assertEqual(loop_type, "pairwise_compare")
        self.assertIn("Two candidate model outputs", reason)
        self.assertEqual(blocking, ["Compare candidate outputs: model_output.md, model_output_2.md"])
        self.assertEqual(non_blocking, [])

    def test_conflicting_reviews_trigger_pairwise_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            model_output_text = "\n".join(
                [
                    "Summary:",
                    "Candidate.",
                    "",
                    "Files touched:",
                    "- a.py",
                    "",
                    "Validation run:",
                    "- pytest -> passed",
                    "",
                    "Risks / follow-ups:",
                    "- None.",
                ]
            )
            (run_dir / "review_output.md").write_text("Recommend accept.\n", encoding="utf-8")
            (run_dir / "review_output_alt.md").write_text(
                "- Blocking: Missing validation evidence.\n",
                encoding="utf-8",
            )

            loop_type, reason, blocking, non_blocking = determine_auto_trigger(
                run_dir=run_dir,
                model_output_text=model_output_text,
                report={"overall_status": "passed"},
                risk="low",
                config={
                    "enabled": True,
                    "same_model_retry": {"enabled": True},
                    "pairwise_compare": {"enabled": True},
                    "alternate_model_review": {"enabled": True},
                },
            )

        self.assertEqual(loop_type, "pairwise_compare")
        self.assertIn("Review outputs conflict", reason)
        self.assertEqual(blocking, ["Resolve conflicting reviews: review_output.md, review_output_alt.md"])
        self.assertEqual(non_blocking, [])

    def test_medium_risk_local_coding_requires_alternate_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_selection.json").write_text(
                json.dumps(
                    {
                        "selected_tier": "local_coding",
                        "task_type": "implementation",
                        "workflow_mode": "implement",
                        "prompt": "implement_request_change_request",
                    }
                ),
                encoding="utf-8",
            )
            model_output_text = "\n".join(
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
            )

            loop_type, reason, blocking, non_blocking = determine_auto_trigger(
                run_dir=run_dir,
                model_output_text=model_output_text,
                report={"overall_status": "passed"},
                risk="medium",
                config={
                    "enabled": True,
                    "same_model_retry": {"enabled": True},
                    "alternate_model_review": {"enabled": True},
                },
            )

        self.assertEqual(loop_type, "alternate_model_review")
        self.assertIn("Medium-risk low-capability model output", reason)
        self.assertEqual(blocking, ["local_coding used for medium risk."])
        self.assertEqual(non_blocking, [])


if __name__ == "__main__":
    unittest.main()
