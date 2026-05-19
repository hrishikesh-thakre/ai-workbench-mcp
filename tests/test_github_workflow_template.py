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
            "workbench_self_acceptance",
            "workbench_self_acceptance_run_dir",
        ):
            self.assertIn(f"      {input_name}:", workflow)

        for env_name in (
            "AI_WORKBENCH_MCP_PACKAGE",
            "WORKBENCH_RUN_DIR",
            "WORKBENCH_RUNS_DIR",
            "WORKBENCH_RUN_ID",
            "WORKBENCH_FALLBACK_RUN_DIR",
            "WORKBENCH_SELF_ACCEPTANCE",
            "WORKBENCH_SELF_ACCEPTANCE_RUN_DIR",
            "WORKBENCH_PR_HEAD_REPO",
        ):
            self.assertIn(f"  {env_name}:", workflow)

        self.assertIn("ai-workbench-mcp==0.6.0a0", workflow)

    def test_render_job_uses_read_only_permissions_and_packaged_renderer(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        self.assertRegex(workflow, r"(?m)^permissions:\n  contents: read\n")
        self.assertIn("permissions:\n      contents: read", render)
        self.assertNotIn("pull-requests: write", render)
        self.assertNotIn("checks: write", render)
        self.assertIn('python -m pip install "$AI_WORKBENCH_MCP_PACKAGE"', render)
        self.assertIn('python -m pip install -e ".[dev]"', render)
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
        self.assertIn("name: workbench-acceptance-run", render)
        self.assertIn("path: ${{ env.WORKBENCH_SELF_ACCEPTANCE_RUN_DIR }}", render)

    def test_self_acceptance_mode_generates_real_acceptance_evidence(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")

        self.assertIn("Prepare self-acceptance evidence", render)
        self.assertIn("WORKBENCH_SELF_ACCEPTANCE", render)
        self.assertIn("WORKBENCH_SELF_ACCEPTANCE_RUN_DIR", render)
        self.assertIn('"${WORKBENCH_PR_HEAD_REPO}" == "${GITHUB_REPOSITORY}"', render)
        self.assertIn("Fork pull request detected; skipping source-repository self-acceptance.", render)
        self.assertIn('git checkout --detach "${PR_HEAD_SHA}"', render)
        self.assertIn("git diff --name-only", render)
        self.assertIn("git reset --mixed", render)
        self.assertIn("python -m ai_workbench_mcp.tools.model_select", render)
        self.assertIn("python -m ai_workbench_mcp.tools.model_handoff", render)
        self.assertIn("python -m ai_workbench_mcp.tools.run_log", render)
        self.assertIn("python -m ai_workbench_mcp.tools.validate_run", render)
        self.assertIn("--profile python_package_maintenance", render)
        self.assertIn("python -m ai_workbench_mcp.tools.quality_loop", render)
        self.assertIn("--mode auto", render)
        self.assertIn("--risk low", render)
        self.assertIn('Rendering from opt-in self-acceptance run ${WORKBENCH_SELF_ACCEPTANCE_RUN_DIR}', render)
        self.assertIn('--run-dir "${WORKBENCH_SELF_ACCEPTANCE_RUN_DIR}"', render)
        self.assertNotIn("--fallback-run-dir \"${WORKBENCH_SELF_ACCEPTANCE_RUN_DIR}\"", render)

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

    def test_same_repo_check_job_has_checks_permission_and_decision_mapping(self) -> None:
        workflow = read_workflow()
        check = job_block(workflow, "post-pr-check")

        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository",
            check,
        )
        self.assertIn("permissions:\n      contents: read\n      checks: write", check)
        self.assertIn("actions/download-artifact@v7", check)
        self.assertIn("name: workbench-pr-gate", check)
        self.assertIn("path: runs/pr_gate", check)
        self.assertIn("PR_GATE_CHECK_NAME: AI Workbench PR Gate", check)
        self.assertIn("PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", check)
        self.assertIn('decision_path = Path("runs/pr_gate/pr_decision.json")', check)
        self.assertIn('comment_path = Path("runs/pr_gate/pr_comment.md")', check)
        self.assertIn('"accept": "success"', check)
        self.assertIn('"needs_review": "action_required"', check)
        self.assertIn('"block": "failure"', check)
        self.assertIn("check_run_id", check)
        self.assertIn("--method GET", check)
        self.assertIn("--method PATCH", check)
        self.assertIn("--method POST", check)
        self.assertIn('"/repos/${GITHUB_REPOSITORY}/check-runs"', check)
        self.assertIn('"/repos/${GITHUB_REPOSITORY}/commits/${PR_HEAD_SHA}/check-runs"', check)
        self.assertIn("--input runs/pr_gate/check_run_update_payload.json", check)
        self.assertIn("--input runs/pr_gate/check_run_create_payload.json", check)

    def test_fork_pull_requests_are_artifact_only(self) -> None:
        workflow = read_workflow()
        render = job_block(workflow, "render-pr-gate")
        comment = job_block(workflow, "post-pr-comment")
        check = job_block(workflow, "post-pr-check")

        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("gh pr comment", workflow)
        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository",
            render,
        )
        self.assertIn("uploaded artifacts and skipped sticky comment/check run", render)
        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository",
            comment,
        )
        self.assertIn(
            "if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository",
            check,
        )

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
            "Checks API",
            "checks: write",
            "AI Workbench PR Gate",
            "| `needs_review` | `action_required` |",
            "Green CI is not semantic acceptance",
            "pipx install ai-workbench-mcp",
            "ai-workbench-bootstrap --target .",
            "WORKBENCH_RUN_DIR",
            "WORKBENCH_RUNS_DIR",
            "WORKBENCH_SELF_ACCEPTANCE",
            "workbench-acceptance-run",
            "pr_gate.acceptance_evidence_missing",
            "Missing evidence and scaffold evidence are not semantic acceptance",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
