# GitHub PR Gate Workflow Template

This page documents the copy-paste workflow template at:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

Most external repositories should install the package and bootstrap the workflow
instead of copying this file by hand:

```bash
pipx install ai-workbench-mcp
ai-workbench-bootstrap --target .
```

Use this page when you need to review the bootstrapped workflow behavior or use
the manual copy-paste fallback. The template renders PR-facing AI Workbench
artifacts in any repository that can install the published Python package. It
does not run Goose, create a Workbench run by itself, or treat CI status as
acceptance.

## What The Template Does

- Installs `ai-workbench-mcp==0.6.0a0` by default.
- Looks for a real Workbench run directory when one is provided.
- Renders `runs/pr_gate/pr_comment.md` and `runs/pr_gate/pr_decision.json`.
- Uploads those files as the `workbench-pr-gate` artifact.
- Posts or updates one sticky PR comment for same-repository pull requests.
- Creates or updates one completed check run for same-repository pull requests.
- Skips sticky comment and check-run posting for fork pull requests.
- Falls back to a blocking missing-evidence or scaffold-evidence result when no real run directory is available.

Green CI is not semantic acceptance. The PR gate can report `accept` only when the referenced Workbench run contains deterministic validation and quality-gate evidence, especially `validation_report.json` and `revision_decision.json`.

## First PR Usage

After bootstrapping the workflow, the first PR should point at one real
Workbench run produced for that PR:

1. Keep `runs/` ignored and do not commit raw evidence.
2. Produce or attach the run folder before the `Render PR gate artifact` step.
3. Set `WORKBENCH_RUN_DIR`, or set `WORKBENCH_RUNS_DIR` plus
   `WORKBENCH_RUN_ID`.
4. Read the sticky PR comment when same-repository permissions allow it, and
   inspect the uploaded `workbench-pr-gate` artifact for `pr_comment.md` and
   `pr_decision.json`.

## Evidence Inputs

The workflow supports the same evidence selection surface as the existing PR gate renderer:

| Input or variable | Use |
|---|---|
| `workbench_run_dir` / `WORKBENCH_RUN_DIR` | Direct path to one Workbench run folder. Takes precedence when the directory exists. |
| `workbench_runs_dir` / `WORKBENCH_RUNS_DIR` | Parent folder containing run folders. Use with `workbench_run_id`. |
| `workbench_run_id` / `WORKBENCH_RUN_ID` | Run folder name under `workbench_runs_dir`. |
| `workbench_fallback_run_dir` / `WORKBENCH_FALLBACK_RUN_DIR` | Optional scaffold evidence folder used only when no real run directory exists. Defaults to `runs/ai_workbench_missing_evidence`. |
| `ai_workbench_mcp_package` / `AI_WORKBENCH_MCP_PACKAGE` | pip package spec. Defaults to `ai-workbench-mcp==0.6.0a0`. |

You can set inputs through `workflow_dispatch` or `workflow_call`. For normal pull requests, set repository variables or edit the workflow after copying it into the target repository.

If neither a direct run directory nor a `runs_dir` plus `run_id` pair exists, the template calls the renderer with `--fallback-run-dir`. When the fallback path does not exist, the renderer still writes a deterministic `block` decision with missing evidence. When the fallback path contains scaffold evidence, the renderer still blocks because scaffold evidence is visibility evidence, not Workbench acceptance evidence.

## Missing-Evidence Recovery

When `pr_decision.json` reports `evidence_source` as `missing` or
`fallback_scaffold`, or includes `pr_gate.acceptance_evidence_missing`, the
workflow did not receive semantic Workbench acceptance evidence. Recover by
providing a real run directory with `validation_report.json` and
`revision_decision.json`.

Bootstrap the workflow assets again if the target repository is missing them:

```bash
pipx install ai-workbench-mcp
ai-workbench-bootstrap --target .
```

Render from an explicit run directory:

```bash
WORKBENCH_RUN_DIR=runs/<run_id>
mkdir -p runs/pr_gate
python -m ai_workbench_mcp.tools.pr_gate \
  --run-dir "$WORKBENCH_RUN_DIR" \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Or render from a parent directory plus run id:

```bash
WORKBENCH_RUNS_DIR=runs
WORKBENCH_RUN_ID=<run_id>
mkdir -p runs/pr_gate
python -m ai_workbench_mcp.tools.pr_gate \
  --runs-dir "$WORKBENCH_RUNS_DIR" \
  --run-id "$WORKBENCH_RUN_ID" \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Fallback rendering is only a wiring check:

```bash
WORKBENCH_FALLBACK_RUN_DIR=runs/ai_workbench_missing_evidence
mkdir -p runs/pr_gate
python -m ai_workbench_mcp.tools.pr_gate \
  --fallback-run-dir "$WORKBENCH_FALLBACK_RUN_DIR" \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

That fallback command should still produce `block`. Missing evidence and scaffold evidence are not semantic acceptance.

## Required Run Artifacts

A real acceptance run should include:

```text
validation_report.json
revision_decision.json
model_output.md
run_log.jsonl
```

Only `validation_report.json` and `revision_decision.json` are required to make the acceptance decision. Raw model output is not embedded in the PR comment.

## Write Surface Safety

The workflow is split into two jobs:

- `render-pr-gate` has `contents: read` and uploads artifacts.
- `post-pr-comment` has `contents: read` plus `pull-requests: write`, and only runs for same-repository pull requests.
- `post-pr-check` has `contents: read` plus `checks: write`, and only runs for same-repository pull requests.

Fork pull requests render and upload `pr_comment.md` and `pr_decision.json`, but skip sticky comments and check runs. The template uses the packaged sticky-comment helper, which adds the `<!-- ai-workbench-pr-gate -->` marker and updates the existing marker comment instead of creating duplicates. The template does not use `pull_request_target`, `issues: write`, or write-token workarounds for forks.

## Checks API Prototype

The same-repository check-run job reads the uploaded artifacts and creates or updates a completed GitHub check run named `AI Workbench PR Gate` on the pull request head SHA. It uses `pr_decision.json` for machine-readable status and includes the rendered `pr_comment.md` as check output text.

Outcome mapping:

| Workbench outcome | Check-run conclusion |
|---|---|
| `accept` | `success` |
| `needs_review` | `action_required` |
| `block` | `failure` |

The check run is optional PR presentation, not a new acceptance source. `accept` still requires deterministic Workbench evidence. The workflow does not configure branch protection or merge enforcement; if an adopting repository later makes the check required, only `accept` maps to a successful conclusion.

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

Same-repository check-run posting uses the GitHub Checks API through `gh api`
with a payload built from `runs/pr_gate/pr_decision.json` and
`runs/pr_gate/pr_comment.md`.

Do not commit private `runs/` evidence. A target repository can produce or download a Workbench run earlier in its own workflow, then point this template at that local evidence directory.
