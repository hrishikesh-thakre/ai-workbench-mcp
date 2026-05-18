# Use AI Workbench PR Gate In Your Repo In 10 Minutes

This is the short setup path for adding AI Workbench PR gate output to an
external repository. You do not need to read the architecture docs first.

Goose remains the default execution surface: it runs the agent workflow and
uses the Workbench MCP tools. Workbench remains the acceptance and audit layer:
it records evidence, runs deterministic validation, makes the quality-gate
decision, and renders the PR-facing result.

## What You Are Adding

Copy the PR gate workflow template into your repository:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

The template:

- installs AI Workbench MCP from the workflow default, unless you override the
  `ai_workbench_mcp_package` input
- looks for one real Workbench run directory
- renders `runs/pr_gate/pr_comment.md`
- renders `runs/pr_gate/pr_decision.json`
- uploads those files as the `workbench-pr-gate` artifact
- posts one sticky PR comment for same-repository pull requests

The template does not run Goose, create Workbench evidence, call provider APIs,
or turn green CI into semantic acceptance.

## Minimal Path

1. Copy the upstream PR gate workflow template into your repository at:

   ```text
   .github/workflows/ai-workbench-pr-gate.yml
   ```

2. Keep local Workbench evidence out of git:

   ```gitignore
   runs/
   ```

3. Produce a real Workbench run for the PR with the normal Goose-first flow:

   ```text
   Goose recipe or Goose task
     -> workbench_open_run
     -> workbench_select_model
     -> Goose executes the change
     -> workbench_record_execution
     -> workbench_validate_run
     -> workbench_quality_gate
   ```

4. Make that run directory available before the workflow's
   `Render PR gate artifact` step. Common options are:

   - generate the run earlier in the same job
   - download a private CI artifact that contains the run folder
   - pass a run folder created by a trusted upstream workflow

5. Point the workflow at the run with either a direct path:

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

6. Open or update a pull request and inspect the uploaded
   `workbench-pr-gate` artifact. Same-repository PRs also get a sticky comment
   when workflow permissions allow it.

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

Missing evidence, unreadable evidence, failed validation, revision-required
quality-gate decisions, and scaffold-only fallback evidence all block. Scaffold
fallback is useful for proving the workflow is wired, but it is not semantic
acceptance and must not be treated as permission to merge.

## Quick Checklist

- The workflow template is copied to `.github/workflows/ai-workbench-pr-gate.yml`.
- `runs/` is ignored and raw Workbench evidence is not committed.
- Goose or a trusted Workbench-producing job creates a real run for the PR.
- The run folder is present in CI before the PR gate render step.
- The workflow receives `WORKBENCH_RUN_DIR`, or `WORKBENCH_RUNS_DIR` plus
  `WORKBENCH_RUN_ID`.
- The run has `validation_report.json` and `revision_decision.json`.
- The PR decision is checked in `runs/pr_gate/pr_decision.json` or the uploaded
  `workbench-pr-gate` artifact.

For the full workflow behavior, see
[`pr-gate-workflow-template.md`](pr-gate-workflow-template.md).
