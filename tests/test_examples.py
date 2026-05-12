import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TINY_EXAMPLE = ROOT / "examples" / "tiny-python-fix"
SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
README = ROOT / "README.md"


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
        required = [
            "task_metadata.json",
            "final_prompt.md",
            "model_selection.json",
            "model_output.md",
            "validation_report.json",
            "revision_decision.json",
            "run_log.jsonl",
        ]
        for artifact in required:
            self.assertTrue((SAMPLE_RUN / artifact).exists(), artifact)

        selection = json.loads((SAMPLE_RUN / "model_selection.json").read_text(encoding="utf-8"))
        report = json.loads((SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(selection["status"], "selected")
        self.assertEqual(report["overall_status"], "passed")
        self.assertTrue(report["sign_off_ready"])
        self.assertEqual(decision["final_status"], "accepted")

        combined = "\n".join(path.read_text(encoding="utf-8") for path in SAMPLE_RUN.iterdir() if path.is_file())
        self.assertNotIn("D:\\", combined)
        self.assertNotIn("C:\\Users", combined)
        self.assertNotIn("api_key", combined.lower())
        self.assertNotIn("token=", combined.lower())

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
        self.assertIn("examples/sample-runs/accepted-tiny-python-fix", text)

    def test_goose_tool_smoke_documents_slow_local_model_path(self) -> None:
        text = (ROOT / "examples" / "goose-tool-smoke" / "README.md").read_text(encoding="utf-8")

        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_select_model", text)
        self.assertIn("workbench-mcp-tool-smoke.yaml", text)
        self.assertIn("--max-turns 4", text)
        self.assertIn("slow", text.lower())


if __name__ == "__main__":
    unittest.main()
