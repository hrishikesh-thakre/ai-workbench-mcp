"""Goose-compatible MCP server for AI Workbench core tools."""

from __future__ import annotations

from typing import Any

from . import core
from .contracts import JsonObject, error_envelope


def _tool_error(operation: str, exc: Exception) -> JsonObject:
    return error_envelope(
        operation=operation,
        code="mcp_tool_failed",
        message=str(exc),
    )


def register_tools(mcp: Any) -> Any:
    """Register Workbench tools on a FastMCP-like server instance."""

    @mcp.tool()
    def workbench_select_model(
        project: str,
        task_type: str,
        risk: str,
        out: str,
        validation_strength: str = "medium",
        prompt: str | None = None,
        complexity_score: int | None = None,
        test_complexity_level: int | None = None,
        instruction_following: str = "normal",
        task_text: str | None = None,
        code_files: list[str] | None = None,
    ) -> JsonObject:
        """Select a Workbench model tier and write model_selection.json."""

        try:
            return core.select_model(
                project=project,
                task_type=task_type,
                risk=risk,
                out=out,
                validation_strength=validation_strength,
                prompt=prompt,
                complexity_score=complexity_score,
                test_complexity_level=test_complexity_level,
                instruction_following=instruction_following,
                task_text=task_text,
                code_files=code_files,
            )
        except Exception as exc:
            return _tool_error("workbench_select_model", exc)

    @mcp.tool()
    def workbench_validate_run(
        project: str,
        out_dir: str,
        profile: str | None = None,
        changed_files: list[str] | None = None,
        report_name: str = "validation_report.json",
    ) -> JsonObject:
        """Run deterministic Workbench validation over a run directory."""

        try:
            return core.validate_run(
                project=project,
                out_dir=out_dir,
                profile=profile,
                changed_files=changed_files,
                report_name=report_name,
            )
        except Exception as exc:
            return _tool_error("workbench_validate_run", exc)

    @mcp.tool()
    def workbench_quality_gate(
        project: str,
        run_dir: str,
        mode: str = "auto",
        risk: str | None = None,
        validation_report: str | None = None,
        review_prompt: str | None = None,
        review_output: str | None = None,
    ) -> JsonObject:
        """Run the Workbench quality gate for a run directory."""

        try:
            return core.quality_gate(
                project=project,
                run_dir=run_dir,
                mode=mode,
                risk=risk,
                validation_report=validation_report,
                review_prompt=review_prompt,
                review_output=review_output,
            )
        except Exception as exc:
            return _tool_error("workbench_quality_gate", exc)

    @mcp.tool()
    def workbench_analyze_runs(
        runs_dir: str = "runs",
        task_type: str | None = None,
        since: str | None = None,
        out_dir: str | None = None,
        evals_dir: str = "evals/golden_cases",
    ) -> JsonObject:
        """Analyze local Workbench run ledgers and write report artifacts."""

        try:
            return core.analyze_runs(
                runs_dir=runs_dir,
                task_type=task_type,
                since=since,
                out_dir=out_dir,
                evals_dir=evals_dir,
            )
        except Exception as exc:
            return _tool_error("workbench_analyze_runs", exc)

    return mcp


def create_server() -> Any:
    """Create the FastMCP server. Import is lazy so tests do not require mcp."""

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("AI Workbench MCP")
    return register_tools(mcp)


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
