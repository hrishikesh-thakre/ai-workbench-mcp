import sys
import types
import unittest
from unittest.mock import patch

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
                "workbench_open_run",
                "workbench_select_model",
                "workbench_select_policy_pack",
                "workbench_record_execution",
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
        self.assertEqual(len(created.tools), 7)


class ServerToolHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        fake = FakeMCP()
        server.register_tools(fake)
        self.tools = fake.tools

    def test_workbench_open_run_returns_core_envelope(self) -> None:
        expected = envelope("workbench_open_run", status="opened")

        with (
            patch("ai_workbench_mcp.server.core.open_run", return_value=expected) as open_run,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_open_run"](
                project="ai_workbench_mcp",
                task="Add lifecycle tools",
                run_dir="runs/run1",
                changed_files=["src/example.py"],
            )

        self.assertEqual(response, expected)
        open_run.assert_called_once_with(
            project="ai_workbench_mcp",
            task="Add lifecycle tools",
            run_dir="runs/run1",
            prompt="implement_request_change_request",
            risk="medium",
            context_profile=None,
            recipe=None,
            changed_files=["src/example.py"],
            docs=None,
            include_diff=False,
            execution_host="goose",
            auto_select_policy_pack=True,
            policy_pack=None,
            validation_profile=None,
        )

    def test_workbench_open_run_forwards_codex_execution_host(self) -> None:
        expected = envelope("workbench_open_run", status="opened")

        with (
            patch("ai_workbench_mcp.server.core.open_run", return_value=expected) as open_run,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_open_run"](
                project="ai_workbench_mcp",
                task="Open from Codex",
                run_dir="runs/run1",
                execution_host="codex",
            )

        self.assertEqual(response, expected)
        open_run.assert_called_once_with(
            project="ai_workbench_mcp",
            task="Open from Codex",
            run_dir="runs/run1",
            prompt="implement_request_change_request",
            risk="medium",
            context_profile=None,
            recipe=None,
            changed_files=None,
            docs=None,
            include_diff=False,
            execution_host="codex",
            auto_select_policy_pack=True,
            policy_pack=None,
            validation_profile=None,
        )

    def test_workbench_open_run_forwards_policy_selection_inputs(self) -> None:
        expected = envelope("workbench_open_run", status="opened")

        with (
            patch("ai_workbench_mcp.server.core.open_run", return_value=expected) as open_run,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_open_run"](
                project="ai_workbench_mcp",
                task="Open with policy metadata.",
                run_dir="runs/run1",
                auto_select_policy_pack=True,
                policy_pack="docs_only",
                validation_profile="docs_only",
            )

        self.assertEqual(response, expected)
        open_run.assert_called_once_with(
            project="ai_workbench_mcp",
            task="Open with policy metadata.",
            run_dir="runs/run1",
            prompt="implement_request_change_request",
            risk="medium",
            context_profile=None,
            recipe=None,
            changed_files=None,
            docs=None,
            include_diff=False,
            execution_host="goose",
            auto_select_policy_pack=True,
            policy_pack="docs_only",
            validation_profile="docs_only",
        )

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
            recipe=None,
            validation_profile=None,
            routing_feedback_path=None,
        )

    def test_workbench_select_policy_pack_returns_core_envelope(self) -> None:
        expected = envelope("workbench_select_policy_pack", status="selected")

        with (
            patch("ai_workbench_mcp.server.core.select_policy_pack", return_value=expected) as select_policy_pack,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_select_policy_pack"](
                task_text="Fix failing test for MCP contract response.",
                task_type="test",
                changed_files=["tests/test_contracts.py"],
                prompt="bug_root_cause_investigation",
                risk="medium",
            )

        self.assertEqual(response, expected)
        select_policy_pack.assert_called_once_with(
            task_text="Fix failing test for MCP contract response.",
            task_type="test",
            changed_files=["tests/test_contracts.py"],
            prompt="bug_root_cause_investigation",
            risk="medium",
        )

    def test_workbench_record_execution_returns_core_envelope(self) -> None:
        expected = envelope("workbench_record_execution", status="response_captured")

        with (
            patch("ai_workbench_mcp.server.core.record_execution", return_value=expected) as record_execution,
            patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
            patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")),
        ):
            response = self.tools["workbench_record_execution"](
                project="ai_workbench_mcp",
                run_dir="runs/run1",
                response_text="Summary:\nDone.",
                files_touched=["src/example.py"],
            )

        self.assertEqual(response, expected)
        record_execution.assert_called_once_with(
            project="ai_workbench_mcp",
            run_dir="runs/run1",
            response_text="Summary:\nDone.",
            files_touched=["src/example.py"],
            model_output_status="response_captured",
            run_status="in_progress",
            response_source="goose",
            validation=None,
            follow_up=None,
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
                task_test_command="python -m pytest tests/test_recipes.py -q -p no:cacheprovider",
            )

        self.assertEqual(response, expected)
        validate_run.assert_called_once_with(
            project="ai_workbench_mcp",
            out_dir="runs/run1",
            profile="scaffold",
            changed_files=["tools/validate_run.py"],
            task_test_command="python -m pytest tests/test_recipes.py -q -p no:cacheprovider",
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
                evidence_scope="complete",
            )

        self.assertEqual(response, expected)
        analyze_runs.assert_called_once_with(
            runs_dir="runs",
            task_type="implementation",
            since=None,
            out_dir="runs/_reports",
            evals_dir="evals/golden_cases",
            evidence_scope="complete",
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
