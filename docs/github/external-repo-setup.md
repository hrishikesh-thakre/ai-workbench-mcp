# Use AI Workbench PR Gate In Your Repo In 10 Minutes

This is the short setup path for adding AI Workbench PR gate output to an
external repository. You do not need to read the architecture docs first.

Goose remains the default execution surface: it runs the agent workflow and
uses the Workbench MCP tools. Workbench remains the acceptance and audit layer:
it records evidence, runs deterministic validation, makes the quality-gate
decision, and renders the PR-facing result.

## What You Are Adding

Install the package once and bootstrap the repository assets:

```bash
pipx install ai-workbench-mcp
ai-workbench-bootstrap --target .
```

Bootstrap writes the AI Workbench starter assets into the target repository,
including the PR gate workflow template:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

The bootstrapped workflow:

- installs AI Workbench MCP from the workflow default, unless you override the
  `ai_workbench_mcp_package` input
- looks for one real Workbench run directory
- renders `runs/pr_gate/pr_comment.md`
- renders `runs/pr_gate/pr_decision.json`
- uploads those files as the `workbench-pr-gate` artifact
- posts one sticky PR comment for same-repository pull requests
- creates or updates one completed check run for same-repository pull requests
- skips comment and check-run writes for fork pull requests

The template does not run Goose, create Workbench evidence, call provider APIs,
configure branch protection, or turn green CI into semantic acceptance.

## Bootstrap Path

1. From the root of the repository that should receive the PR gate, install and
   run the bootstrap command:

   ```bash
   pipx install ai-workbench-mcp
   ai-workbench-bootstrap --target .
   ```

2. Confirm the workflow now exists:

   ```text
   .github/workflows/ai-workbench-pr-gate.yml
   ```

3. Keep local Workbench evidence out of git:

   ```gitignore
   runs/
   ```

## First PR Flow

1. Produce a real Workbench run for the PR with the normal Goose-first flow:

   ```text
   Goose recipe or Goose task
     -> workbench_open_run
     -> workbench_select_model
     -> Goose executes the change
     -> workbench_record_execution
     -> workbench_validate_run
     -> workbench_quality_gate
   ```

2. Keep `runs/` ignored. Do not commit the raw evidence folder. Instead, make
   the run directory available before the workflow's
   `Render PR gate artifact` step. Common options are:

   - generate the run earlier in the same job
   - download a private CI artifact that contains the run folder
   - pass a run folder created by a trusted upstream workflow

3. Point the workflow at the run with either a direct path:

   ```text
   WORKBENCH_RUN_DIR=runs/<run_id>
   ```

   Or a parent directory plus run id:

   ```text
   WORKBENCH_RUNS_DIR=runs
   WORKBENCH_RUN_ID=<run_id>
   ```

   `WORKBENCH_RUN_DIR` takes precedence when it is set and the directory exists.
   You can set these as GitHub Actions variables, `workflow_dispatch` inputs, or
   `workflow_call` inputs. Leave `ai_workbench_mcp_package` unset to use the
   workflow default, or set it only when you intentionally want a different
   package spec.

4. Open or update the pull request. Read the sticky PR comment when it appears,
   and always inspect the uploaded `workbench-pr-gate` artifact. The artifact
   contains:

   ```text
   runs/pr_gate/pr_comment.md
   runs/pr_gate/pr_decision.json
   ```

   Same-repository PRs get a sticky comment and a completed check run when
   workflow permissions allow them. Fork PRs still upload the artifact but skip
   comment and check-run posting.

## Manual Fallback

If bootstrap is unavailable in your environment, copy the upstream workflow
template into your repository manually:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

Then continue from the `runs/` ignore rule and evidence steps above. Manual
copy-paste is a fallback path; the preferred setup is package install plus
bootstrap so future starter assets are created consistently.

## Acceptance Rule

A PR can be reported as `accept` only from real Workbench evidence. The run
folder must include acceptance-supporting:

```text
validation_report.json
revision_decision.json
```

`validation_report.json` proves deterministic validation ran.
`revision_decision.json` proves the Workbench quality gate made the acceptance
decision. The PR comment and `pr_decision.json` summarize the result without
embedding raw run evidence.

The same-repository check run is another summary surface. It maps `accept` to
`success`, `needs_review` to `action_required`, and `block` to `failure`.
Branch protection and merge enforcement are repository-owner choices outside
the bootstrap template.

Missing evidence, unreadable evidence, failed validation, revision-required
quality-gate decisions, and scaffold-only fallback evidence all block. Scaffold
fallback is useful for proving the workflow is wired, but it is not semantic
acceptance and must not be treated as permission to merge.

## Missing-Evidence Troubleshooting

If the PR comment or `pr_decision.json` reports `block`, `missing`,
`fallback_scaffold`, or `pr_gate.acceptance_evidence_missing`, recover by
pointing the workflow at a real Workbench acceptance run. Do not fix this by
using scaffold evidence as an acceptance shortcut.

1. Re-run bootstrap if the workflow or starter assets are missing:

   ```bash
   pipx install ai-workbench-mcp
   ai-workbench-bootstrap --target .
   ```

2. Confirm the run folder exists and has the two acceptance artifacts:

   ```bash
   WORKBENCH_RUN_DIR=runs/<run_id>
   test -f "$WORKBENCH_RUN_DIR/validation_report.json"
   test -f "$WORKBENCH_RUN_DIR/revision_decision.json"
   ```

3. Re-render the PR gate locally from a direct run directory:

   ```bash
   mkdir -p runs/pr_gate
   python -m ai_workbench_mcp.tools.pr_gate \
     --run-dir "$WORKBENCH_RUN_DIR" \
     --out runs/pr_gate/pr_comment.md \
     --json-out runs/pr_gate/pr_decision.json
   ```

4. Or re-render from a parent directory plus run id:

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

5. Use fallback rendering only to prove the workflow can write artifacts:

   ```bash
   WORKBENCH_FALLBACK_RUN_DIR=runs/ai_workbench_missing_evidence
   mkdir -p runs/pr_gate
   python -m ai_workbench_mcp.tools.pr_gate \
     --fallback-run-dir "$WORKBENCH_FALLBACK_RUN_DIR" \
     --out runs/pr_gate/pr_comment.md \
     --json-out runs/pr_gate/pr_decision.json
   ```

   This path is expected to block. Missing evidence and scaffold evidence are not semantic acceptance; they are visibility signals only.

## Quick Checklist

- `pipx install ai-workbench-mcp` and `ai-workbench-bootstrap --target .` have
  been run, or the workflow was copied manually as a fallback.
- The workflow template exists at `.github/workflows/ai-workbench-pr-gate.yml`.
- `runs/` is ignored and raw Workbench evidence is not committed.
- Goose or a trusted Workbench-producing job creates a real run for the PR.
- The run folder is present in CI before the PR gate render step.
- The workflow receives `WORKBENCH_RUN_DIR`, or `WORKBENCH_RUNS_DIR` plus
  `WORKBENCH_RUN_ID`.
- The run has `validation_report.json` and `revision_decision.json`.
- The PR decision is checked in `runs/pr_gate/pr_decision.json` or the uploaded
  `workbench-pr-gate` artifact.
- Fork PRs are artifact-only and should not rely on comments or check-run
  writes.

For the full workflow behavior, see
[`pr-gate-workflow-template.md`](pr-gate-workflow-template.md).
