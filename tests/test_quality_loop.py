import unittest
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from ai_workbench_mcp.tools.quality_loop import (
    classify_review_output,
    determine_auto_trigger,
    main,
    quality_gate_payload,
    read_json,
)


def quality_args(
    run_dir: Path,
    *,
    mode: str = "auto",
    risk: str | None = None,
    review_output: Path | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        project="ai_workbench_mcp",
        run_dir=str(run_dir),
        mode=mode,
        risk=risk,
        validation_report=None,
        review_prompt=None,
        review_output=str(review_output) if review_output is not None else None,
    )


def write_structured_model_output(run_dir: Path) -> None:
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


def write_passed_validation_report(run_dir: Path) -> None:
    (run_dir / "validation_report.json").write_text(
        json.dumps({"overall_status": "passed", "confidence": 1.0}),
        encoding="utf-8",
    )


def write_promotion_artifacts(run_dir: Path) -> None:
    (run_dir / "model_output.md").write_text("original model output\n", encoding="utf-8")
    (run_dir / "validation_report.json").write_text(
        json.dumps({"overall_status": "failed", "source": "first"}),
        encoding="utf-8",
    )
    (run_dir / "model_output_2.md").write_text("revised model output\n", encoding="utf-8")


def write_second_pass_report(run_dir: Path, status: str) -> None:
    (run_dir / "validation_report_2.json").write_text(
        json.dumps({"overall_status": status, "source": "second"}),
        encoding="utf-8",
    )


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
    def test_quality_gate_payload_evaluate_review_requires_revision_when_blocking_findings_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text("Summary: placeholder\n", encoding="utf-8")
            review_output = run_dir / "review_output.md"
            review_output.write_text(
                "\n".join(
                    [
                        "- Blocking: Missing validation evidence.",
                        "- Non-blocking: Add one more regression test.",
                    ]
                ),
                encoding="utf-8",
            )

            decision = quality_gate_payload(quality_args(run_dir, mode="evaluate_review", review_output=review_output))
            written = read_json(run_dir / "revision_decision.json")

        self.assertEqual(decision, written)
        self.assertEqual(decision["final_status"], "revision_required")
        self.assertEqual(decision["blocking_findings"], ["Blocking: Missing validation evidence."])
        self.assertEqual(decision["non_blocking_findings"], ["Non-blocking: Add one more regression test."])

    def test_quality_gate_payload_evaluate_review_accepts_non_blocking_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text("Summary: placeholder\n", encoding="utf-8")
            review_output = run_dir / "review_output.md"
            review_output.write_text(
                "\n".join(
                    [
                        "- Non blocking: Clarify the summary wording.",
                        "- Consider covering one more edge case later.",
                    ]
                ),
                encoding="utf-8",
            )

            decision = quality_gate_payload(quality_args(run_dir, mode="evaluate_review", review_output=review_output))

        self.assertEqual(decision["final_status"], "accepted")
        self.assertEqual(decision["blocking_findings"], [])
        self.assertEqual(
            decision["non_blocking_findings"],
            [
                "Non blocking: Clarify the summary wording.",
                "Consider covering one more edge case later.",
            ],
        )

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

            with patch(
                "ai_workbench_mcp.tools.quality_loop.load_project_config",
                return_value=SimpleNamespace(root=run_dir),
            ):
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

            with patch(
                "ai_workbench_mcp.tools.quality_loop.load_project_config",
                return_value=SimpleNamespace(root=run_dir),
            ):
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

            with patch(
                "ai_workbench_mcp.tools.quality_loop.load_project_config",
                return_value=SimpleNamespace(root=run_dir),
            ):
                with patch.object(sys, "argv", argv):
                    exit_code = main()

            self.assertEqual(exit_code, 0)
            decision = read_json(run_dir / "revision_decision.json")
            self.assertEqual(decision["final_status"], "accepted")
            self.assertEqual(decision["blocking_findings"], [])
            self.assertEqual(decision["non_blocking_findings"], [])


class PromoteRevisionModeTests(unittest.TestCase):
    def test_quality_gate_payload_promote_revision_promotes_when_second_pass_validation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_promotion_artifacts(run_dir)

            def validation_stub(args: SimpleNamespace) -> dict[str, object]:
                self.assertEqual(args.profile, "run_signoff")
                self.assertEqual(args.report_name, "validation_report_2.json")
                self.assertEqual(Path(args.out_dir), run_dir)
                write_second_pass_report(run_dir, "passed")
                return {"overall_status": "passed"}

            with patch(
                "ai_workbench_mcp.tools.quality_loop.validate_run_payload",
                side_effect=validation_stub,
            ) as validate_payload:
                decision = quality_gate_payload(quality_args(run_dir, mode="promote_revision"))
            written = read_json(run_dir / "revision_decision.json")
            promoted_report = read_json(run_dir / "validation_report.json")
            promoted_output = (run_dir / "model_output.md").read_text(encoding="utf-8")
            archived_output = (run_dir / "model_output_1.md").read_text(encoding="utf-8")
            archived_report = read_json(run_dir / "validation_report_1.json")

        self.assertEqual(validate_payload.call_count, 1)
        self.assertEqual(decision, written)
        self.assertEqual(decision["final_status"], "accepted")
        self.assertEqual(decision["accepted_pass"], 2)
        self.assertEqual(promoted_output, "revised model output\n")
        self.assertEqual(promoted_report["overall_status"], "passed")
        self.assertEqual(promoted_report["source"], "second")
        self.assertEqual(archived_output, "original model output\n")
        self.assertEqual(archived_report["source"], "first")

    def test_quality_gate_payload_promote_revision_does_not_promote_when_second_pass_validation_is_not_passed(self) -> None:
        for status in ("failed", "needs_review"):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as tmpdir:
                    run_dir = Path(tmpdir)
                    write_promotion_artifacts(run_dir)

                    def validation_stub(args: SimpleNamespace) -> dict[str, object]:
                        write_second_pass_report(run_dir, status)
                        return {"overall_status": status}

                    with patch(
                        "ai_workbench_mcp.tools.quality_loop.validate_run_payload",
                        side_effect=validation_stub,
                    ):
                        decision = quality_gate_payload(quality_args(run_dir, mode="promote_revision"))
                    written = read_json(run_dir / "revision_decision.json")
                    canonical_report = read_json(run_dir / "validation_report.json")

                    self.assertEqual(decision, written)
                    self.assertEqual(decision["final_status"], "revision_required")
                    self.assertEqual(decision["next_action"], "await_revision")
                    self.assertEqual(decision["blocking_findings"], [f"validation_report_2.json status: {status}"])
                    self.assertEqual((run_dir / "model_output.md").read_text(encoding="utf-8"), "original model output\n")
                    self.assertEqual(canonical_report["source"], "first")
                    self.assertFalse((run_dir / "model_output_1.md").exists())
                    self.assertFalse((run_dir / "validation_report_1.json").exists())

    def test_promote_revision_cli_missing_second_output_preserves_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            argv = [
                "quality_loop.py",
                "--project",
                "ai_workbench",
                "--run-dir",
                str(run_dir),
                "--mode",
                "promote_revision",
            ]

            with patch(
                "ai_workbench_mcp.tools.quality_loop.load_project_config",
                return_value=SimpleNamespace(root=run_dir),
            ):
                with patch.object(sys, "argv", argv):
                    exit_code = main()
            decision = read_json(run_dir / "revision_decision.json")

        self.assertEqual(exit_code, 1)
        self.assertEqual(decision["final_status"], "revision_required")
        self.assertEqual(decision["next_action"], "await_revision")
        self.assertIn("Missing second-pass output", decision["blocking_findings"][0])


class DetermineAutoTriggerTests(unittest.TestCase):
    def test_quality_gate_payload_auto_accepts_low_risk_structured_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_structured_model_output(run_dir)
            write_passed_validation_report(run_dir)

            decision = quality_gate_payload(quality_args(run_dir, risk="low"))
            written = read_json(run_dir / "revision_decision.json")
            review_prompt_exists = (run_dir / "review_prompt.md").exists()

        self.assertEqual(decision, written)
        self.assertEqual(decision["loop_type"], "none")
        self.assertEqual(decision["final_status"], "accepted")
        self.assertFalse(decision["required"])
        self.assertEqual(decision["reason_codes"], ["quality_gate.accepted"])
        self.assertEqual(decision["reason_sources"][0]["severity"], "info")
        self.assertFalse(review_prompt_exists)

    def test_quality_gate_payload_auto_writes_review_prompt_for_alternate_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_structured_model_output(run_dir)
            write_passed_validation_report(run_dir)
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

            decision = quality_gate_payload(quality_args(run_dir, risk="medium"))
            revision_decision_exists = (run_dir / "revision_decision.json").exists()
            review_prompt_exists = (run_dir / "review_prompt.md").exists()

        self.assertEqual(decision["loop_type"], "alternate_model_review")
        self.assertEqual(decision["final_status"], "review_required")
        self.assertEqual(decision["blocking_findings"], ["local_coding used for medium risk."])
        self.assertEqual(decision["reason_codes"], ["quality_loop.medium_risk_low_capability_review"])
        self.assertTrue(revision_decision_exists)
        self.assertTrue(review_prompt_exists)

    def test_quality_gate_payload_auto_records_validation_failed_reason_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_structured_model_output(run_dir)
            (run_dir / "validation_report.json").write_text(
                json.dumps({"overall_status": "failed", "confidence": 0.4}),
                encoding="utf-8",
            )

            decision = quality_gate_payload(quality_args(run_dir, risk="low"))

        self.assertEqual(decision["loop_type"], "alternate_model_review")
        self.assertEqual(decision["final_status"], "review_required")
        self.assertEqual(decision["reason_codes"], ["quality_loop.validation_failed"])
        self.assertEqual(decision["reason_sources"][0]["severity"], "review")

    def test_quality_gate_payload_auto_records_api_contract_reason_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_structured_model_output(run_dir)
            write_passed_validation_report(run_dir)
            (run_dir / "final_prompt.md").write_text("Update the API contract for the MCP tool response.\n", encoding="utf-8")

            decision = quality_gate_payload(quality_args(run_dir, risk="low"))

        self.assertEqual(decision["loop_type"], "alternate_model_review")
        self.assertEqual(decision["final_status"], "review_required")
        self.assertEqual(decision["reason_codes"], ["quality_loop.api_contract_review_required"])

    def test_quality_gate_payload_auto_records_security_privacy_reason_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_structured_model_output(run_dir)
            write_passed_validation_report(run_dir)
            (run_dir / "model_selection.json").write_text(
                json.dumps({"prompt": "security_privacy_risk_review"}),
                encoding="utf-8",
            )

            decision = quality_gate_payload(quality_args(run_dir, risk="low"))

        self.assertEqual(decision["loop_type"], "alternate_model_review")
        self.assertEqual(decision["final_status"], "review_required")
        self.assertEqual(decision["reason_codes"], ["quality_loop.security_privacy_review_required"])

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
