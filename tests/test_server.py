import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_workbench_mcp import server


class FakeMCP:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def envelope(operation: str, status: str = "ok", ok: bool = True) -> dict[str, object]:
    return {
        "schema_version": 1,
        "operation": operation,
        "status": status,
        "ok": ok,
        "artifacts": {},
        "summary": {},
        "errors": [],
    }


class ServerRegistrationTests(unittest.TestCase):
    def test_register_tools_registers_expected_tool_names(self) -> None:
        fake = FakeMCP()

        returned = server.register_tools(fake)

        self.assertIs(returned, fake)
        self.assertEqual(
            set(fake.tools),
            {
                "workbench_select_model",
                "workbench_validate_run",
                "workbench_quality_gate",
                "workbench_analyze_runs",
            },
        )

    def test_create_server_imports_mcp_lazily(self) -> None:
        with patch.dict(sys.modules, {"mcp": None}):
            self.assertIn("register_tools", dir(server))

    def test_create_server_registers_tools_with_fastmcp(self) -> None:
        class FakeFastMCP(FakeMCP):
            def __init__(self, name: str) -> None:
                super().__init__()
                self.name = name

        mcp_module = types.ModuleType("mcp")
        server_module = types.ModuleType("mcp.server")
        fastmcp_module = types.ModuleType("mcp.server.fastmcp")
        fastmcp_module.FastMCP = FakeFastMCP

        with patch.dict(
            sys.modules,
            {
                "mcp": mcp_module,
                "mcp.server": server_module,
                "mcp.server.fastmcp": fastmcp_module,
            },
        ):
            created = server.create_server()

        self.assertEqual(created.name, "AI Workbench MCP")
        self.assertEqual(len(created.tools), 4)


class ServerToolHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        fake = FakeMCP()
        server.register_tools(fake)
        self.tools = fake.tools

    def test_workbench_select_model_returns_core_envelope(self) -> None:
        expected = envelope("workbench_select_model", status="selected")

        with (
            patch("ai_workbench_mcp.server.core.select_model", return_value=expected) as select_model,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_select_model"](
                project="ai_workbench_mcp",
                task_type="implement",
                risk="medium",
                out="runs/run1/model_selection.json",
                code_files=["src/example.py"],
            )

        self.assertEqual(response, expected)
        select_model.assert_called_once_with(
            project="ai_workbench_mcp",
            task_type="implement",
            risk="medium",
            out="runs/run1/model_selection.json",
            validation_strength="medium",
            prompt=None,
            complexity_score=None,
            test_complexity_level=None,
            instruction_following="normal",
            task_text=None,
            code_files=["src/example.py"],
        )

    def test_workbench_validate_run_returns_core_envelope(self) -> None:
        expected = envelope("workbench_validate_run", status="passed")

        with (
            patch("ai_workbench_mcp.server.core.validate_run", return_value=expected) as validate_run,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_validate_run"](
                project="ai_workbench_mcp",
                out_dir="runs/run1",
                profile="scaffold",
                changed_files=["tools/validate_run.py"],
            )

        self.assertEqual(response, expected)
        validate_run.assert_called_once_with(
            project="ai_workbench_mcp",
            out_dir="runs/run1",
            profile="scaffold",
            changed_files=["tools/validate_run.py"],
            report_name="validation_report.json",
        )

    def test_workbench_quality_gate_returns_core_envelope(self) -> None:
        expected = envelope("workbench_quality_gate", status="accepted")

        with (
            patch("ai_workbench_mcp.server.core.quality_gate", return_value=expected) as quality_gate,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_quality_gate"](
                project="ai_workbench_mcp",
                run_dir="runs/run1",
                mode="auto",
                risk="low",
            )

        self.assertEqual(response, expected)
        quality_gate.assert_called_once_with(
            project="ai_workbench_mcp",
            run_dir="runs/run1",
            mode="auto",
            risk="low",
            validation_report=None,
            review_prompt=None,
            review_output=None,
        )

    def test_workbench_analyze_runs_returns_core_envelope(self) -> None:
        expected = envelope("workbench_analyze_runs", status="completed")

        with (
            patch("ai_workbench_mcp.server.core.analyze_runs", return_value=expected) as analyze_runs,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_analyze_runs"](
                runs_dir="runs",
                task_type="implementation",
                out_dir="runs/_reports",
            )

        self.assertEqual(response, expected)
        analyze_runs.assert_called_once_with(
            runs_dir="runs",
            task_type="implementation",
            since=None,
            out_dir="runs/_reports",
            evals_dir="evals/golden_cases",
        )

    def test_handler_exception_returns_error_envelope(self) -> None:
        with patch("ai_workbench_mcp.server.core.select_model", side_effect=RuntimeError("boom")):
            response = self.tools["workbench_select_model"](
                project="ai_workbench_mcp",
                task_type="implement",
                risk="medium",
                out="runs/run1/model_selection.json",
            )

        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertEqual(response["status"], "error")
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "mcp_tool_failed")
        self.assertEqual(response["errors"][0]["message"], "boom")


if __name__ == "__main__":
    unittest.main()
