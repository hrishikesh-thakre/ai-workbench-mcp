# GitHub PR Gate Workflow Template

This page documents the copy-paste workflow template at:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

The template renders PR-facing AI Workbench artifacts in any repository that can install the published Python package. It does not run Goose, create a Workbench run by itself, or treat CI status as acceptance.

## What The Template Does

- Installs `ai-workbench-mcp==0.3.0a0` by default.
- Looks for a real Workbench run directory when one is provided.
- Renders `runs/pr_gate/pr_comment.md` and `runs/pr_gate/pr_decision.json`.
- Uploads those files as the `workbench-pr-gate` artifact.
- Posts or updates one sticky PR comment for same-repository pull requests.
- Skips sticky comment posting for fork pull requests.
- Falls back to a blocking missing-evidence or scaffold-evidence result when no real run directory is available.

Green CI is not semantic acceptance. The PR gate can report `accept` only when the referenced Workbench run contains deterministic validation and quality-gate evidence, especially `validation_report.json` and `revision_decision.json`.

## Evidence Inputs

The workflow supports the same evidence selection surface as the existing PR gate renderer:

| Input or variable | Use |
|---|---|
| `workbench_run_dir` / `WORKBENCH_RUN_DIR` | Direct path to one Workbench run folder. Takes precedence when the directory exists. |
| `workbench_runs_dir` / `WORKBENCH_RUNS_DIR` | Parent folder containing run folders. Use with `workbench_run_id`. |
| `workbench_run_id` / `WORKBENCH_RUN_ID` | Run folder name under `workbench_runs_dir`. |
| `workbench_fallback_run_dir` / `WORKBENCH_FALLBACK_RUN_DIR` | Optional scaffold evidence folder used only when no real run directory exists. Defaults to `runs/ai_workbench_missing_evidence`. |
| `ai_workbench_mcp_package` / `AI_WORKBENCH_MCP_PACKAGE` | pip package spec. Defaults to `ai-workbench-mcp==0.3.0a0`. |

You can set inputs through `workflow_dispatch` or `workflow_call`. For normal pull requests, set repository variables or edit the workflow after copying it into the target repository.

If neither a direct run directory nor a `runs_dir` plus `run_id` pair exists, the template calls the renderer with `--fallback-run-dir`. When the fallback path does not exist, the renderer still writes a deterministic `block` decision with missing evidence. When the fallback path contains scaffold evidence, the renderer still blocks because scaffold evidence is visibility evidence, not Workbench acceptance evidence.

## Required Run Artifacts

A real acceptance run should include:

```text
validation_report.json
revision_decision.json
model_output.md
run_log.jsonl
```

Only `validation_report.json` and `revision_decision.json` are required to make the acceptance decision. Raw model output is not embedded in the PR comment.

## Comment Safety

The workflow is split into two jobs:

- `render-pr-gate` has `contents: read` and uploads artifacts.
- `post-pr-comment` has `contents: read` plus `pull-requests: write`, and only runs for same-repository pull requests.

Fork pull requests render and upload `pr_comment.md` and `pr_decision.json`, but skip sticky comments. The template uses the packaged sticky-comment helper, which adds the `<!-- ai-workbench-pr-gate -->` marker and updates the existing marker comment instead of creating duplicates.

## Local Equivalent

The workflow calls the packaged modules rather than repo-local wrappers:

```bash
python -m ai_workbench_mcp.tools.pr_gate \
  --run-dir "$WORKBENCH_RUN_DIR" \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Fallback rendering uses:

```bash
python -m ai_workbench_mcp.tools.pr_gate \
  --fallback-run-dir "$WORKBENCH_FALLBACK_RUN_DIR" \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Same-repository comment posting uses:

```bash
python -m ai_workbench_mcp.tools.pr_gate_comment \
  --repo "$GITHUB_REPOSITORY" \
  --pr-number "$PR_NUMBER" \
  --comment runs/pr_gate/pr_comment.md \
  --decision runs/pr_gate/pr_decision.json
```

Do not commit private `runs/` evidence. A target repository can produce or download a Workbench run earlier in its own workflow, then point this template at that local evidence directory.
