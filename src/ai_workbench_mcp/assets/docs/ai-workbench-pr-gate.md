# AI Workbench PR Gate Bootstrap

This repository has been bootstrapped with the AI Workbench PR gate assets.

## Installed Files

- `.github/workflows/ai-workbench-pr-gate.yml`
- `docs/ai-workbench-pr-gate.md`
- `configs/`, `prompts/`, and `recipes/`

The workflow renders PR-facing Workbench artifacts from an existing Workbench run. It does not run Goose, create provider credentials, call model APIs, or treat green CI as semantic acceptance.

## Evidence Rule

A PR can report `accept` only when the referenced Workbench run includes deterministic validation and quality-gate evidence:

```text
validation_report.json
revision_decision.json
```

Missing evidence, scaffold-only fallback evidence, failed validation, or a revision-required quality-gate decision must block or require review.

## Local Evidence

Keep local Workbench evidence out of git:

```gitignore
runs/
```

Use Goose or another MCP host to create a run, then point the workflow at the
run with `WORKBENCH_RUN_DIR` or with `WORKBENCH_RUNS_DIR` plus
`WORKBENCH_RUN_ID`.

## Local Renderer Smoke

You can verify that the renderer is wired without claiming semantic acceptance:

```bash
mkdir -p runs/pr_gate
python -m ai_workbench_mcp.tools.pr_gate \
  --fallback-run-dir runs/ai_workbench_missing_evidence \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

That fallback command should produce `pr_comment.md` and `pr_decision.json`
with a `block` outcome. Missing evidence and scaffold evidence are not semantic
acceptance.

Do not commit `runs/`.
