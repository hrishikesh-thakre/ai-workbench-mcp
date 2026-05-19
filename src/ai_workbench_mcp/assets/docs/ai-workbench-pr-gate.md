# AI Workbench PR Gate Bootstrap

This repository has been bootstrapped with the AI Workbench PR gate assets.

## Installed Files

- `.github/workflows/ai-workbench-pr-gate.yml`
- `docs/ai-workbench-pr-gate.md`
- `configs/`, `prompts/`, and `recipes/`

The workflow renders PR-facing Workbench artifacts from an existing Workbench run. It does not run Goose, create provider credentials, call model APIs, or treat green CI as semantic acceptance.

For source repositories that can validate themselves with the bundled Workbench
profiles, the workflow also has an opt-in self-acceptance mode:

```text
WORKBENCH_SELF_ACCEPTANCE=true
```

When enabled on a same-repository pull request and no explicit run directory is
configured, the workflow creates `runs/pr_gate_acceptance`, runs deterministic
validation and the quality gate, renders from that real run directory, and
uploads the full run as the `workbench-acceptance-run` artifact. It does not run
for fork pull requests. Leave this disabled unless the checked-out repository
can run the packaged validation profile successfully.

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

An explicit run directory takes precedence over opt-in self-acceptance mode.

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
