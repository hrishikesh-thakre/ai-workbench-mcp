import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TINY_EXAMPLE = ROOT / "examples" / "tiny-python-fix"
SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
DOCS_ONLY_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-docs-only-smoke"
FOCUSED_WORKFLOWS = ROOT / "examples" / "focused-workflows" / "README.md"
README = ROOT / "README.md"
V02_RELEASE = ROOT / "docs" / "releases" / "v0.2.0-alpha.md"

REQUIRED_SAMPLE_ARTIFACTS = [
    "task_metadata.json",
    "final_prompt.md",
    "model_selection.json",
    "model_output.md",
    "validation_report.json",
    "revision_decision.json",
    "run_log.jsonl",
]


class PublicExamplesTests(unittest.TestCase):
    def test_tiny_python_fix_has_runnable_failing_validation_command(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TINY_EXAMPLE),
                "-p",
                "test_*.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED", result.stderr)

    def test_sample_run_contains_required_sanitized_artifacts(self) -> None:
        for sample_run in (SAMPLE_RUN, DOCS_ONLY_SAMPLE_RUN):
            with self.subTest(sample_run=sample_run.name):
                for artifact in REQUIRED_SAMPLE_ARTIFACTS:
                    self.assertTrue((sample_run / artifact).exists(), artifact)

                selection = json.loads((sample_run / "model_selection.json").read_text(encoding="utf-8"))
                report = json.loads((sample_run / "validation_report.json").read_text(encoding="utf-8"))
                decision = json.loads((sample_run / "revision_decision.json").read_text(encoding="utf-8"))

                self.assertEqual(selection["status"], "selected")
                self.assertEqual(report["overall_status"], "passed")
                self.assertTrue(report["sign_off_ready"])
                self.assertEqual(decision["final_status"], "accepted")

                combined = "\n".join(path.read_text(encoding="utf-8") for path in sample_run.iterdir() if path.is_file())
                self.assertNotIn("D:\\", combined)
                self.assertNotIn("C:\\Users", combined)
                self.assertNotIn("api_key", combined.lower())
                self.assertNotIn("token=", combined.lower())

    def test_docs_only_sample_run_uses_focused_prompt_profile_and_policy(self) -> None:
        metadata = json.loads((DOCS_ONLY_SAMPLE_RUN / "task_metadata.json").read_text(encoding="utf-8"))
        report = json.loads((DOCS_ONLY_SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((DOCS_ONLY_SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))
        run_log_entries = [
            json.loads(line)
            for line in (DOCS_ONLY_SAMPLE_RUN / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(metadata["prompt"], "documentation_accuracy_audit")
        self.assertEqual(report["profile"], "docs_only")
        self.assertEqual(report["confidence"], 1.0)
        self.assertEqual(decision["final_status"], "accepted")
        self.assertEqual(
            sum(1 for entry in run_log_entries if entry.get("decision") == "model_response_captured"),
            1,
        )
        self.assertTrue(
            any(
                check["name"] == "changed_file_policy" and check["status"] == "passed"
                for check in report["artifact_checks"]
            )
        )

    def test_readme_product_page_references_quickstart_tools_recipe_and_sample_run(self) -> None:
        text = README.read_text(encoding="utf-8")

        self.assertIn("evidence-backed accepted runs", text)
        self.assertIn("## 5-Minute Quickstart", text)
        self.assertIn("## Six MCP Tools", text)
        self.assertIn("## Workflow", text)
        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_select_model", text)
        self.assertIn("workbench_record_execution", text)
        self.assertIn("workbench_validate_run", text)
        self.assertIn("workbench_quality_gate", text)
        self.assertIn("workbench_analyze_runs", text)
        self.assertIn("recipes/workbench-engineering-acceptance.yaml", text)
        self.assertIn("recipes/workbench-mcp-tool-smoke.yaml", text)
        self.assertIn("examples/goose-tool-smoke", text)
        self.assertIn("examples/focused-workflows", text)
        self.assertIn("examples/sample-runs/accepted-tiny-python-fix", text)
        self.assertIn("examples/sample-runs/accepted-docs-only-smoke", text)
        self.assertIn("recipes/workbench-docs-only-acceptance.yaml", text)
        self.assertIn("recipes/workbench-python-package-maintenance.yaml", text)
        self.assertIn("recipes/workbench-test-fix-acceptance.yaml", text)
        self.assertIn("low_risk_coding", text)

    def test_goose_tool_smoke_documents_slow_local_model_path(self) -> None:
        text = (ROOT / "examples" / "goose-tool-smoke" / "README.md").read_text(encoding="utf-8")

        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_select_model", text)
        self.assertIn("workbench-mcp-tool-smoke.yaml", text)
        self.assertIn("--max-turns 4", text)
        self.assertIn("slow", text.lower())

    def test_focused_workflows_document_v02_recipe_commands(self) -> None:
        text = FOCUSED_WORKFLOWS.read_text(encoding="utf-8")

        self.assertIn("Focused v0.2 Workflows", text)
        self.assertIn("workbench-docs-only-acceptance.yaml", text)
        self.assertIn("workbench-python-package-maintenance.yaml", text)
        self.assertIn("workbench-test-fix-acceptance.yaml", text)
        self.assertIn("workbench-engineering-acceptance.yaml", text)
        self.assertIn("docs_only", text)
        self.assertIn("python_package_maintenance", text)
        self.assertIn("test_fix", text)
        self.assertIn("low_risk_coding", text)
        self.assertIn("Do not commit `runs/`", text)

    def test_v02_release_notes_document_focused_profiles_and_verification(self) -> None:
        text = V02_RELEASE.read_text(encoding="utf-8")

        self.assertIn("v0.2.0-alpha", text)
        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_analyze_runs", text)
        self.assertIn("workbench-docs-only-acceptance.yaml", text)
        self.assertIn("workbench-python-package-maintenance.yaml", text)
        self.assertIn("workbench-test-fix-acceptance.yaml", text)
        self.assertIn("docs_only", text)
        self.assertIn("python_package_maintenance", text)
        self.assertIn("test_fix", text)
        self.assertIn("low_risk_coding", text)
        self.assertIn("Goose focused docs-only six-tool smoke", text)
        self.assertIn("examples/sample-runs/accepted-docs-only-smoke", text)
        self.assertIn("quality gate accepted", text)
        self.assertIn("python -m pytest -q -p no:cacheprovider", text)
        self.assertIn("--profile scaffold", text)
        self.assertIn("Full sign-off profiles", text)
        self.assertIn("--changed-files README.md docs/ai/ROADMAP_STATUS.md", text)


if __name__ == "__main__":
    unittest.main()
