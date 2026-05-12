import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = ROOT / "recipes" / "workbench-engineering-acceptance.yaml"
TOOL_SMOKE_RECIPE_PATH = ROOT / "recipes" / "workbench-mcp-tool-smoke.yaml"


class WorkbenchRecipeTests(unittest.TestCase):
    def test_recipe_declares_workbench_mcp_extension_and_tools(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")

        self.assertIn('title: "Workbench Engineering Acceptance"', text)
        self.assertIn("cmd: \"ai-workbench-mcp\"", text)
        self.assertIn('name: "AI Workbench MCP"', text)
        self.assertIn('type: stdio', text)
        self.assertIn('timeout: 300', text)
        self.assertIn('- "workbench_open_run"', text)
        self.assertIn('- "workbench_select_model"', text)
        self.assertIn('- "workbench_record_execution"', text)
        self.assertIn('- "workbench_validate_run"', text)
        self.assertIn('- "workbench_quality_gate"', text)
        self.assertIn('- "workbench_analyze_runs"', text)

    def test_recipe_parameters_cover_acceptance_workflow_inputs(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")

        for key in (
            "project",
            "run_dir",
            "task",
            "task_type",
            "risk",
            "validation_strength",
            "validation_profile",
            "prompt",
            "complexity_score",
        ):
            self.assertIn(f"key: {key}", text)

    def test_recipe_instructions_call_tools_in_acceptance_order(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")
        ordered_tools = [
            "workbench_open_run",
            "workbench_select_model",
            "workbench_record_execution",
            "workbench_validate_run",
            "workbench_quality_gate",
            "workbench_analyze_runs",
        ]
        positions = [text.index(tool) for tool in ordered_tools]

        self.assertEqual(positions, sorted(positions))
        self.assertIn("Do not claim the run is accepted", text)
        self.assertIn("deterministic validation and the quality gate", text)
        self.assertIn("Call workbench_record_execution exactly once", text)
        self.assertIn("do not call workbench_record_execution again", text)
        self.assertIn('status="response_captured"', text)

    def test_tool_smoke_recipe_is_bounded_to_open_and_select(self) -> None:
        text = TOOL_SMOKE_RECIPE_PATH.read_text(encoding="utf-8")

        self.assertIn('title: "Workbench MCP Tool Smoke"', text)
        self.assertIn("cmd: \"ai-workbench-mcp\"", text)
        self.assertIn('- "workbench_open_run"', text)
        self.assertIn('- "workbench_select_model"', text)
        self.assertIn("Call exactly these two tools", text)
        self.assertIn("Do not edit tracked files", text)
        self.assertNotIn('- "workbench_record_execution"', text)
        self.assertNotIn('- "workbench_validate_run"', text)
        self.assertNotIn('- "workbench_quality_gate"', text)
        self.assertNotIn('- "workbench_analyze_runs"', text)


if __name__ == "__main__":
    unittest.main()
