import asyncio
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
EXPECTED_TOOLS = {
    "workbench_open_run",
    "workbench_select_model",
    "workbench_select_policy_pack",
    "workbench_record_execution",
    "workbench_validate_run",
    "workbench_quality_gate",
    "workbench_analyze_runs",
}


def run_async_smoke_or_skip_platform_denial(coro: object) -> None:
    try:
        asyncio.run(coro)
    except PermissionError as exc:
        if sys.platform == "win32" and getattr(exc, "winerror", None) == 5:
            raise unittest.SkipTest(
                "Windows denied MCP stdio named-pipe creation in this environment."
            ) from exc
        raise


def payload_from_tool_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured

    content = getattr(result, "content", [])
    if content:
        text = getattr(content[0], "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed

    raise AssertionError(f"Could not decode MCP tool result: {result!r}")


class McpRuntimeSmokeTests(unittest.TestCase):
    def test_console_script_lists_workbench_tools(self) -> None:
        script = shutil.which("ai-workbench-mcp")
        if script is None:
            self.skipTest("ai-workbench-mcp console script is not installed")

        async def run_smoke() -> None:
            server = StdioServerParameters(command=script, args=[], env=os.environ.copy())

            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertEqual({tool.name for tool in listed.tools}, EXPECTED_TOOLS)

        run_async_smoke_or_skip_platform_denial(run_smoke())

    def test_stdio_server_lists_and_calls_workbench_tools(self) -> None:
        async def run_smoke() -> None:
            with tempfile.TemporaryDirectory() as tmpdir:
                runs_dir = Path(tmpdir) / "runs"
                run_dir = runs_dir / "mcp_smoke"
                reports_dir = runs_dir / "_reports"
                env = os.environ.copy()
                env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
                server = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "ai_workbench_mcp.server"],
                    env=env,
                )

                async with stdio_client(server) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        listed = await session.list_tools()
                        tool_names = {tool.name for tool in listed.tools}

                        self.assertEqual(tool_names, EXPECTED_TOOLS)

                        opened = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_open_run",
                                arguments={
                                    "project": "ai_workbench_mcp",
                                    "task": "Runtime-smoke the MCP server.",
                                    "run_dir": str(run_dir),
                                    "risk": "low",
                                },
                            )
                        )
                        self.assertEqual(opened["operation"], "workbench_open_run")
                        self.assertTrue(opened["ok"])

                        selected = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_select_model",
                                arguments={
                                    "project": "ai_workbench_mcp",
                                    "task_type": "implement",
                                    "risk": "low",
                                    "out": str(run_dir / "model_selection.json"),
                                    "prompt": "implement_request_change_request",
                                    "complexity_score": 8,
                                },
                            )
                        )
                        self.assertEqual(selected["operation"], "workbench_select_model")
                        self.assertTrue(selected["ok"])

                        policy_pack = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_select_policy_pack",
                                arguments={
                                    "task_text": "Runtime-smoke a docs-only policy selector.",
                                    "changed_files": ["docs/runtime-smoke.md"],
                                    "risk": "low",
                                },
                            )
                        )
                        self.assertEqual(policy_pack["operation"], "workbench_select_policy_pack")
                        self.assertTrue(policy_pack["ok"])
                        self.assertEqual(policy_pack["summary"]["recommended_policy_pack"], "docs_only")

                        recorded = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_record_execution",
                                arguments={
                                    "project": "ai_workbench_mcp",
                                    "run_dir": str(run_dir),
                                    "response_text": "\n".join(
                                        [
                                            "Summary:",
                                            "Runtime smoke completed.",
                                            "",
                                            "Files touched:",
                                            "- None.",
                                            "",
                                            "Validation run:",
                                            "- pytest -> not run in model response",
                                            "",
                                            "Risks / follow-ups:",
                                            "- None.",
                                        ]
                                    ),
                                    "files_touched": [],
                                },
                            )
                        )
                        self.assertEqual(recorded["operation"], "workbench_record_execution")
                        self.assertTrue(recorded["ok"])

                        validated = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_validate_run",
                                arguments={
                                    "project": "ai_workbench_mcp",
                                    "out_dir": str(run_dir),
                                    "profile": "run_signoff",
                                },
                            )
                        )
                        self.assertEqual(validated["operation"], "workbench_validate_run")
                        self.assertEqual(validated["status"], "passed")
                        self.assertTrue(validated["ok"])

                        gated = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_quality_gate",
                                arguments={
                                    "project": "ai_workbench_mcp",
                                    "run_dir": str(run_dir),
                                    "mode": "auto",
                                    "risk": "low",
                                },
                            )
                        )
                        self.assertEqual(gated["operation"], "workbench_quality_gate")
                        self.assertEqual(gated["status"], "accepted")
                        self.assertTrue(gated["ok"])

                        analyzed = payload_from_tool_result(
                            await session.call_tool(
                                "workbench_analyze_runs",
                                arguments={
                                    "runs_dir": str(runs_dir),
                                    "out_dir": str(reports_dir),
                                },
                            )
                        )
                        self.assertEqual(analyzed["operation"], "workbench_analyze_runs")
                        self.assertTrue(analyzed["ok"])
                        self.assertEqual(analyzed["summary"]["runs_total"], 1)

        run_async_smoke_or_skip_platform_denial(run_smoke())


if __name__ == "__main__":
    unittest.main()
