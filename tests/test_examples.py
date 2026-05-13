import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TINY_EXAMPLE = ROOT / "examples" / "tiny-python-fix"
SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
DOCS_ONLY_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-docs-only-smoke"
NEEDS_REVIEW_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "needs-review-test-fix"
FOCUSED_WORKFLOWS = ROOT / "examples" / "focused-workflows" / "README.md"
SAMPLE_RUNS_README = ROOT / "examples" / "sample-runs" / "README.md"
ANALYTICS_GUIDE = ROOT / "docs" / "analytics" / "acceptance-analytics.md"
EVENT_LEDGER_GUIDE = ROOT / "docs" / "analytics" / "event-ledger.md"
MODEL_REGISTRY_GUIDE = ROOT / "docs" / "configuration" / "model-registry.md"
DOGFOODING_GUIDE = ROOT / "docs" / "dogfooding" / "phase5-dogfooding.md"
LAUNCH_ISSUES = ROOT / "docs" / "github" / "launch-issues.md"
README = ROOT / "README.md"
START_HERE = ROOT / "docs" / "ai" / "START_HERE.md"
PROJECT_MAP = ROOT / "docs" / "ai" / "PROJECT_MAP.md"
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
        for sample_run in (SAMPLE_RUN, DOCS_ONLY_SAMPLE_RUN, NEEDS_REVIEW_SAMPLE_RUN):
            with self.subTest(sample_run=sample_run.name):
                for artifact in REQUIRED_SAMPLE_ARTIFACTS:
                    self.assertTrue((sample_run / artifact).exists(), artifact)

                selection = json.loads((sample_run / "model_selection.json").read_text(encoding="utf-8"))

                self.assertEqual(selection["status"], "selected")

                combined = "\n".join(path.read_text(encoding="utf-8") for path in sample_run.iterdir() if path.is_file())
                self.assertNotIn("D:\\", combined)
                self.assertNotIn("C:\\Users", combined)
                self.assertNotIn("api_key", combined.lower())
                self.assertNotIn("token=", combined.lower())

    def test_accepted_sample_runs_are_accepted(self) -> None:
        for sample_run in (SAMPLE_RUN, DOCS_ONLY_SAMPLE_RUN):
            with self.subTest(sample_run=sample_run.name):
                report = json.loads((sample_run / "validation_report.json").read_text(encoding="utf-8"))
                decision = json.loads((sample_run / "revision_decision.json").read_text(encoding="utf-8"))

                self.assertEqual(report["overall_status"], "passed")
                self.assertTrue(report["sign_off_ready"])
                self.assertEqual(decision["final_status"], "accepted")

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
        self.assertEqual(metadata["recipe"], "workbench-docs-only-acceptance.yaml")
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

    def test_needs_review_sample_run_uses_test_fix_profile_and_revision_required_gate(self) -> None:
        metadata = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "task_metadata.json").read_text(encoding="utf-8"))
        selection = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "model_selection.json").read_text(encoding="utf-8"))
        report = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(metadata["prompt"], "bug_root_cause_investigation")
        self.assertEqual(metadata["recipe"], "workbench-test-fix-acceptance.yaml")
        self.assertEqual(selection["selected_tier"], "frontier")
        self.assertEqual(report["profile"], "test_fix")
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(decision["final_status"], "revision_required")
        self.assertTrue(decision["blocking_findings"])
        self.assertTrue(
            any(
                command["name"] == "full_test_suite" and command["status"] == "failed"
                for command in report["commands_run"]
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
        self.assertIn("examples/sample-runs/needs-review-test-fix", text)
        self.assertIn("docs/analytics/acceptance-analytics.md", text)
        self.assertIn("docs/analytics/event-ledger.md", text)
        self.assertIn("docs/configuration/model-registry.md", text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", text)
        self.assertIn("docs/github/launch-issues.md", text)
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

    def test_sample_runs_readme_and_analytics_guide_document_phase5_reports(self) -> None:
        sample_text = SAMPLE_RUNS_README.read_text(encoding="utf-8")
        guide_text = ANALYTICS_GUIDE.read_text(encoding="utf-8")
        event_guide_text = EVENT_LEDGER_GUIDE.read_text(encoding="utf-8")
        model_registry_text = MODEL_REGISTRY_GUIDE.read_text(encoding="utf-8")
        dogfooding_text = DOGFOODING_GUIDE.read_text(encoding="utf-8")
        launch_text = LAUNCH_ISSUES.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")
        start_here_text = START_HERE.read_text(encoding="utf-8")
        project_map_text = PROJECT_MAP.read_text(encoding="utf-8")

        self.assertIn("needs-review-test-fix", sample_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", sample_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", readme_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", start_here_text)
        self.assertIn("docs/analytics/event-ledger.md", readme_text)
        self.assertIn("docs/analytics/event-ledger.md", start_here_text)
        self.assertIn("docs/analytics/event-ledger.md", project_map_text)
        self.assertIn("docs/configuration/model-registry.md", readme_text)
        self.assertIn("docs/configuration/model-registry.md", start_here_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", sample_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", readme_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", start_here_text)
        self.assertIn("docs/github/launch-issues.md", readme_text)
        self.assertIn("docs/github/launch-issues.md", start_here_text)
        self.assertIn("--runs-dir examples/sample-runs", guide_text)
        self.assertIn("run_metrics.json", guide_text)
        self.assertIn("run_summary.md", guide_text)
        self.assertIn("routing_feedback_candidates", guide_text)
        self.assertIn("Advisory Routing Feedback", guide_text)
        self.assertIn("source_invalid", guide_text)
        self.assertIn("does not mutate `selected_tier`", guide_text)
        self.assertIn("Cost tracking is optional provider metadata", guide_text)
        self.assertIn("events.jsonl", event_guide_text)
        self.assertIn("best-effort and non-fatal", event_guide_text)
        self.assertIn("should stay local", event_guide_text)
        self.assertIn("not required sign-off artifacts", event_guide_text)
        self.assertIn("configs/model_registry.local.yaml", model_registry_text)
        self.assertIn("dictionaries merge recursively", model_registry_text)
        self.assertIn("selector reference", model_registry_text.lower())
        self.assertIn("does not record provider credentials", model_registry_text)
        self.assertIn("20-50 real Goose acceptance runs", dogfooding_text)
        self.assertIn("runs/dogfood-YYYYMMDD-<short-task-slug>", dogfooding_text)
        self.assertIn("routing_feedback_candidates", dogfooding_text)
        self.assertIn("does not change the selected tier", dogfooding_text)
        self.assertIn("command_failed:full_test_suite", dogfooding_text)
        self.assertIn("dogfooding: collect 20-50 Goose acceptance runs", launch_text)
        self.assertIn("analytics: promote routing feedback candidates", launch_text)
        self.assertIn("cost evidence: capture provider token and cost metadata", launch_text)
        self.assertIn("ci: prototype PR acceptance gate", launch_text)
        self.assertNotIn("before the v0.1 alpha announcement", launch_text)

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
