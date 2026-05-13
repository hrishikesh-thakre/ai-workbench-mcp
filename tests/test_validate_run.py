import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]

from ai_workbench_mcp.tools.validate_run import validate_captured_response_format, validate_run_payload


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
        self.assertEqual(report["summary"]["commands_passed"], 6)
        self.assertEqual(report["summary"]["commands_failed"], 0)
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
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=["README.md", "docs/ai/ROADMAP_STATUS.md", "examples/focused-workflows/README.md"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "passed")
        self.assertEqual(checks["changed_file_policy"]["status"], "passed")
        self.assertIn("Changed-file source: cli_changed_files", checks["changed_file_policy"]["details"])

    def test_docs_only_profile_rejects_source_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "docs-only-forbidden"
            self.write_signoff_artifacts(run_dir)
            args = SimpleNamespace(
                project="ai_workbench_mcp",
                profile="docs_only",
                changed_files=["README.md", "tools/validate_run.py"],
                out_dir=str(run_dir),
                report_name="validation_report.json",
            )

            report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(checks["changed_file_policy"]["status"], "failed")
        self.assertIn("Forbidden changed file: tools/validate_run.py", checks["changed_file_policy"]["details"])

    def test_docs_only_profile_accepts_empty_run_log_file_scope(self) -> None:
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

            report = validate_run_payload(args)

        checks = {check["name"]: check for check in report["artifact_checks"]}
        self.assertEqual(report["overall_status"], "passed")
        self.assertEqual(checks["changed_file_policy"]["status"], "passed")
        self.assertIn("Changed-file source: run_log_files_touched", checks["changed_file_policy"]["details"])
        self.assertIn("Checked 0 changed files.", checks["changed_file_policy"]["details"])


if __name__ == "__main__":
    unittest.main()
