import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-workbench-pr-gate.yml"
DOC = ROOT / "docs" / "github" / "pr-gate-workflow-template.md"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def job_block(workflow: str, job_name: str) -> str:
    match = re.search(
        rf"^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Missing job block: {job_name}")
    return match.group("body")


class GitHubWorkflowTemplateTests(unittest.TestCase):
    def test_template_has_copy_paste_triggers_inputs_and_env(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        workflow = read_workflow()

        self.assertIn("name: AI Workbench PR Gate", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("workflow_call:", workflow)

        for input_name in (
            "ai_workbench_mcp_package",
            "workbench_run_dir",
            "workbench_runs_dir",
            "workbench_run_id",
            "workbench_fallback_run_dir",
        ):
            self.assertIn(f"      {input_name}:", workflow)

        for env_name in (
            "AI_WORKBENCH_MCP_PACKAGE",
            "WORKBENCH_RUN_DIR",
            "WORKBENCH_RUNS_DIR",
            "WORKBENCH_RUN_ID",
            "WORKBENCH_FALLBACK_RUN_DIR",
        ):
            self.assertIn(f"  {env_name}:", workflow)

        self.assertIn("ai-workbench-mcp==0.3.0a0", workflow)

    def test_render_job_uses_read_only_permissions_and_packaged_renderer(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        self.assertRegex(workflow, r"(?m)^permissions:\n  contents: read\n")
        self.assertIn("permissions:\n      contents: read", render)
        self.assertNotIn("pull-requests: write", render)
        self.assertIn('python -m pip install "$AI_WORKBENCH_MCP_PACKAGE"', render)
        self.assertIn("python -m ai_workbench_mcp.tools.pr_gate", render)
        self.assertNotIn("python tools/pr_gate.py", workflow)
        self.assertNotIn("tools/pr_gate.py", workflow)
        self.assertNotIn("tools/validate_run.py", workflow)
        self.assertNotIn("--fail-on-block", workflow)

    def test_renderer_uses_existing_flags_and_blocking_fallback(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        for flag in ("--run-dir", "--runs-dir", "--run-id", "--fallback-run-dir", "--out", "--json-out"):
            self.assertIn(flag, render)

        self.assertIn('[[ -n "${WORKBENCH_RUN_DIR}" && -d "${WORKBENCH_RUN_DIR}" ]]', render)
        self.assertIn(
            '[[ -n "${WORKBENCH_RUNS_DIR}" && -n "${WORKBENCH_RUN_ID}" && -d "${WORKBENCH_RUNS_DIR}/${WORKBENCH_RUN_ID}" ]]',
            render,
        )
        self.assertIn("runs/ai_workbench_missing_evidence", render)
        self.assertIn("blocking missing/scaffold fallback", render)

    def test_template_uploads_markdown_and_json_artifacts(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        self.assertIn("actions/upload-artifact@v6", render)
        self.assertIn("name: workbench-pr-gate", render)
        self.assertIn("if-no-files-found: error", render)
        self.assertIn("runs/pr_gate/pr_comment.md", render)
        self.assertIn("runs/pr_gate/pr_decision.json", render)

    def test_same_repo_comment_job_has_write_permission_and_sticky_comment_guard(self) -> None:
        workflow = read_workflow()
        comment = job_block(workflow, "post-pr-comment")

        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository",
            comment,
        )
        self.assertIn("permissions:\n      contents: read\n      pull-requests: write", comment)
        self.assertIn("actions/checkout@v5", comment)
        self.assertIn("actions/download-artifact@v7", comment)
        self.assertIn("name: workbench-pr-gate", comment)
        self.assertIn("GH_TOKEN: ${{ github.token }}", comment)
        self.assertIn("python -m ai_workbench_mcp.tools.pr_gate_comment", comment)
        self.assertIn('--repo "${{ github.repository }}"', comment)
        self.assertIn('--pr-number "${{ github.event.pull_request.number }}"', comment)
        self.assertIn("--comment runs/pr_gate/pr_comment.md", comment)
        self.assertIn("--decision runs/pr_gate/pr_decision.json", comment)

    def test_fork_pull_requests_are_artifact_only(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("gh pr comment", workflow)
        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository",
            render,
        )
        self.assertIn("uploaded artifacts and skipped sticky comment", render)

    def test_docs_explain_copy_paste_usage_and_acceptance_boundary(self) -> None:
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")

        for phrase in (
            ".github/workflows/ai-workbench-pr-gate.yml",
            "validation_report.json",
            "revision_decision.json",
            "pr_comment.md",
            "pr_decision.json",
            "same-repository pull requests",
            "Fork pull requests",
            "Green CI is not semantic acceptance",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
