import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

from ai_workbench_mcp.tools.validate_run import (
    load_validation_profile,
    validate_captured_response_format,
    validate_changed_file_policy,
    validate_run_payload,
)


class ValidateCapturedResponseFormatTests(unittest.TestCase):
    def write_signoff_artifacts(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "model_selection.json").write_text('{"status":"selected"}\n', encoding="utf-8")
        (run_dir / "run_log.jsonl").write_text(
            json.dumps({"decision": "model_response_captured", "files_touched": []}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "model_output.md").write_text(
            "\n".join(
                [
                    "# Model Output",
                    "",
                    "## Execution Metadata",
                    "",
                    "- Status: `response_captured`",
                    "",
                    "## Normalized Response",
                    "",
                    "Summary:",
                    "Docs-only validation policy test.",
                    "",
                    "Files touched:",
                    "- README.md",
                    "",
                    "Validation run:",
                    "- python -m pytest tests/test_recipes.py -q -p no:cacheprovider -> passed",
                    "",
                    "Risks / follow-ups:",
                    "- None.",
                ]
            ),
            encoding="utf-8",
        )

    def test_validate_run_payload_writes_scaffold_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "payload-scaffold"
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="scaffold",
                changed_files=[],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            report = validate_run_payload(args)
            written = json.loads((run_dir / "validation_report.json").read_text(encoding="utf-8"))

        self.assertEqual(report, written)
        self.assertEqual(report["run_id"], "payload-scaffold")
        self.assertEqual(report["project"], "ai_workbench_mcp")
        self.assertEqual(report["profile"], "scaffold")
        self.assertEqual(report["overall_status"], "passed")
        self.assertTrue(report["sign_off_ready"])
        self.assertEqual(report["summary"]["commands_passed"], 11)
        self.assertEqual(report["summary"]["commands_failed"], 0)
        command_names = [command["name"] for command in report["commands_run"]]
        self.assertIn("model_registry_override_support", command_names)
        self.assertIn("event_ledger_import_smoke", command_names)
        self.assertIn("golden_eval_help", command_names)
        self.assertIn("codex_live_handoff_help", command_names)
        self.assertIn("codex_live_result_check_help", command_names)
        self.assertEqual(report["summary"]["checks_passed"], 3)

    def test_response_captured_without_preferred_sections_needs_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_output = Path(tmpdir) / "model_output.md"
            model_output.write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Execution Metadata",
                        "",
                        "- Status: `response_captured`",
                        "",
                        "## Captured Response",
                        "",
                        "Updated docs and validated the help commands.",
                        "Validation run: all 12 documented --help commands passed.",
                    ]
                ),
                encoding="utf-8",
            )

            check = validate_captured_response_format(model_output)

            self.assertEqual(check.status, "needs_review")
            self.assertIn("Missing required response section: Summary:", check.details)
            self.assertIn("Missing required response section: Files touched:", check.details)

    def test_response_captured_with_normalized_response_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_output = Path(tmpdir) / "model_output.md"
            model_output.write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Execution Metadata",
                        "",
                        "- Status: `response_captured`",
                        "",
                        "## Captured Response",
                        "",
                        "raw response",
                        "",
                        "## Normalized Response",
                        "",
                        "Summary:",
                        "Updated docs.",
                        "",
                        "Files touched:",
                        "- AGENTS.md",
                        "",
                        "Validation run:",
                        "- python tools/validate_run.py --help -> passed",
                        "",
                        "Risks / follow-ups:",
                        "- Re-run the audit.",
                    ]
                ),
                encoding="utf-8",
            )

            check = validate_captured_response_format(model_output)

            self.assertEqual(check.status, "passed")
        self.assertEqual(
            check.summary,
            "Captured model response matches the preferred structured format.",
        )

    def test_docs_only_profile_accepts_documentation_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-allowed"
            self.write_signoff_artifacts(run_dir)
            changed_files = ["README.md", "docs/ai/ROADMAP_STATUS.md", "examples/focused-workflows/README.md"]
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=changed_files,
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=changed_files,
            ):
                report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "passed")
        self.assertEqual(checks["changed_file_policy"]["status"], "passed")
        self.assertIn("Changed-file source: cli_changed_files", checks["changed_file_policy"]["details"])
        self.assertIn("Actual changed-file evidence required: true", checks["changed_file_policy"]["details"])
        self.assertIn("Non-empty changed-file evidence required: true", checks["changed_file_policy"]["details"])

    def test_docs_only_profile_rejects_source_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-forbidden"
            self.write_signoff_artifacts(run_dir)
            changed_files = ["README.md", "tools/validate_run.py"]
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=changed_files,
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=changed_files,
            ):
                report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(checks["changed_file_policy"]["status"], "failed")
        self.assertIn("Forbidden changed file: tools/validate_run.py", checks["changed_file_policy"]["details"])

    def test_docs_only_profile_rejects_claimed_files_without_actual_worktree_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-no-actual-diff"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=["docs/walkthroughs/goose-acceptance-demo.md"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=[],
            ):
                report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(report["confidence"], 0.4)
        self.assertEqual(checks["changed_file_policy"]["status"], "failed")
        self.assertIn(
            "Claimed changed file has no worktree diff: docs/walkthroughs/goose-acceptance-demo.md",
            checks["changed_file_policy"]["details"],
        )

    def test_docs_only_profile_rejects_empty_changed_file_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-no-changes"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=[],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=[],
            ):
                report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(checks["changed_file_policy"]["status"], "failed")
        self.assertIn("Changed-file source: run_log_files_touched", checks["changed_file_policy"]["details"])
        self.assertIn(
            "Changed-file evidence is required but no changed files were reported or discovered.",
            checks["changed_file_policy"]["details"],
        )

    def test_docs_only_profile_rejects_unreported_actual_worktree_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-unreported-diff"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=["README.md"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=["README.md", "src/foo.py"],
            ):
                report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(checks["changed_file_policy"]["status"], "failed")
        self.assertIn("Unreported worktree diff file: src/foo.py", checks["changed_file_policy"]["details"])
        self.assertIn("Forbidden changed file: src/foo.py", checks["changed_file_policy"]["details"])

    def test_focused_profile_accepts_exact_reported_worktree_diff(self) -> None:
        profile = load_validation_profile("low_risk_coding")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            run_dir = project_root / "runs" / "focused-exact-diff"
            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=["src/ai_workbench_mcp/tools/validate_run.py", "tests/test_validate_run.py"],
            ):
                check = validate_changed_file_policy(
                    profile,
                    ["src/ai_workbench_mcp/tools/validate_run.py", "tests/test_validate_run.py"],
                    "cli_changed_files",
                    project_root=project_root,
                    run_dir=run_dir,
                )

        self.assertIsNotNone(check)
        self.assertEqual(check.status, "passed")
        self.assertIn("Checked 2 changed files.", check.details)

    def test_focused_profile_rejects_unreported_actual_worktree_diff(self) -> None:
        profile = load_validation_profile("low_risk_coding")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            run_dir = project_root / "runs" / "focused-underreported-diff"
            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=["src/ai_workbench_mcp/tools/validate_run.py", "tests/test_validate_run.py"],
            ):
                check = validate_changed_file_policy(
                    profile,
                    ["src/ai_workbench_mcp/tools/validate_run.py"],
                    "cli_changed_files",
                    project_root=project_root,
                    run_dir=run_dir,
                )

        self.assertIsNotNone(check)
        self.assertEqual(check.status, "failed")
        self.assertIn("Unreported worktree diff file: tests/test_validate_run.py", check.details)

    def test_profile_defaults_to_model_selection_validation_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "selection-profile"
            self.write_signoff_artifacts(run_dir)
            (run_dir / "model_selection.json").write_text(
                json.dumps({"status": "selected", "validation_profile": "docs_only"}) + "\n",
                encoding="utf-8",
            )
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile=None,
                changed_files=["README.md"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            with patch(
                "ai_workbench_mcp.tools.validate_run.parse_git_status_changed_files",
                return_value=["README.md"],
            ):
                report = validate_run_payload(args)

        self.assertEqual(report["profile"], "docs_only")
        self.assertEqual(report["profile_source"], "model_selection")
        self.assertEqual(report["overall_status"], "passed")

    def test_test_fix_profile_requires_task_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "test-fix-missing-command"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="test_fix",
                changed_files=["examples/tiny-python-fix/calculator.py"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertEqual(checks["task_test_command"]["status"], "failed")
        self.assertIn("Task-specific test command is required", checks["task_test_command"]["summary"])

    def test_test_fix_task_test_command_failure_blocks_signoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "test-fix-focused-failure"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="test_fix",
                changed_files=["examples/tiny-python-fix/calculator.py"],
                task_test_command='python -m unittest discover -s examples/tiny-python-fix -p "test_*.py"',
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            def fake_subprocess_run(command: str | list[str], **kwargs):
                command_text = " ".join(command) if isinstance(command, list) else command
                if isinstance(command, list) and command[:2] == ["git", "status"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=" M examples/tiny-python-fix/calculator.py\n",
                    )
                return_code = 1 if "unittest discover" in command_text else 0
                return SimpleNamespace(returncode=return_code)

            with patch("ai_workbench_mcp.tools.validate_run.subprocess.run", side_effect=fake_subprocess_run):
                report = validate_run_payload(args)

        command_names = [command["name"] for command in report["commands_run"]]
        focused_command = next(command for command in report["commands_run"] if command["name"] == "task_test_command")
        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(command_names[0], "task_test_command")
        self.assertEqual(focused_command["status"], "failed")
        self.assertEqual(report["overall_status"], "failed")
        self.assertEqual(checks["task_test_command"]["status"], "passed")

    def test_task_test_command_rejects_shell_control_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "test-fix-invalid-command"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="test_fix",
                changed_files=["examples/tiny-python-fix/calculator.py"],
                task_test_command="python -m pytest tests/test_recipes.py -q && echo unsafe",
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        command_names = [command["name"] for command in report["commands_run"]]
        self.assertNotIn("task_test_command", command_names)
        self.assertEqual(report["overall_status"], "failed")
        self.assertEqual(checks["task_test_command"]["status"], "failed")
        self.assertIn("shell control syntax", checks["task_test_command"]["summary"])


if __name__ == "__main__":
    unittest.main()
