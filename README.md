# AI Workbench MCP

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

`ai-workbench-mcp` is a Goose-compatible MCP extension that turns AI coding work into evidence-backed accepted runs.

Goose executes the work. AI Workbench records what happened, validates it, runs a quality gate, and decides whether the result should be trusted.

## Problem

AI coding agents can produce useful work, but "done" is not the same as accepted. A useful acceptance workflow needs reproducible evidence:

- what task was requested
- which model/runtime was selected
- what the agent produced
- which deterministic checks ran
- whether the quality gate accepted, rejected, or requested review
- where the audit trail lives

AI Workbench MCP provides that acceptance and audit layer.

## Why Goose + Acceptance Gates

Goose already owns the agent execution surface: CLI, desktop, providers, recipes, MCP hosting, and the agent loop.

AI Workbench MCP stays complementary:

- opens run evidence folders
- recommends model/runtime tiers
- records model or Goose output
- runs deterministic validation
- makes quality-gate decisions
- summarizes accepted-run analytics

It does not provide a chat UI, editor fork, provider marketplace, or general agent runner.

## 5-Minute Quickstart

Install from the repository root:

```bash
python -m pip install -e .
```

Register the MCP server in Goose:

```bash
goose configure
```

Choose:

- `Add Extension`
- `Command-line Extension`
- Name: `AI Workbench MCP`
- Command: `ai-workbench-mcp`
- Timeout: `300`

On slower local models, start with the two-tool smoke to verify Goose can reach the MCP server:

```bash
goose run --no-session --max-turns 4 --recipe ./recipes/workbench-mcp-tool-smoke.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tool-smoke \
  --params task="Local Goose MCP tool smoke. Do not edit tracked files." \
  --params risk=low \
  --params complexity_score=4
```

Then run the full sample recipe smoke after Goose has a provider configured:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=tiny_python_fix \
  --params complexity_score=4
```

For bounded documentation-only changes, use the focused v0.2 recipe:

```bash
goose run --recipe ./recipes/workbench-docs-only-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-docs-only \
  --params task="Update the public docs for the requested documentation-only change." \
  --params risk=low
```

For bounded Python package maintenance, use:

```bash
goose run --recipe ./recipes/workbench-python-package-maintenance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-package-maintenance \
  --params task="Make the requested bounded Python package maintenance change and keep the full test suite passing." \
  --params task_type=implement \
  --params risk=medium
```

For bounded test-fix work, use:

```bash
goose run --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-test-fix \
  --params task="Fix the requested failing test signal with the smallest justified change and report the exact validation command." \
  --params risk=medium
```

For a general low-risk implementation task with deterministic test coverage, use the engineering recipe with the low-risk coding profile:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-low-risk-coding \
  --params task="Make the requested bounded low-risk code change and keep deterministic tests passing." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=low_risk_coding \
  --params complexity_score=8
```

Inspect the evidence folder:

```text
runs/goose-tiny-python-fix/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Do not commit `runs/`. It is the local evidence ledger.

## Sample Analytics Demo

To inspect the trust loop without provider setup, run analytics over the committed synthetic sample runs:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

The sample set includes accepted, docs-only accepted, and revision-required test-fix evidence. Read [the analytics guide](docs/analytics/acceptance-analytics.md) to interpret `run_metrics.json`, `run_summary.md`, outcome buckets, failure reasons, routing feedback candidates, and optional cost fields.

## Six MCP Tools

```text
workbench_open_run
  -> creates the run folder, task metadata, final prompt, context packet, and initial run log

workbench_select_model
  -> recommends a model/runtime tier and writes model_selection.json

workbench_record_execution
  -> captures raw Goose/model response text into model_output.md and appends run_log.jsonl

workbench_validate_run
  -> runs deterministic validation and writes validation_report.json

workbench_quality_gate
  -> accepts, rejects, or requests review and writes revision_decision.json

workbench_analyze_runs
  -> summarizes accepted-run metrics by recipe, validation profile, model tier, failure reason, and quality-gate outcome under runs/_reports
```

## Workflow

```text
Goose recipe
  -> workbench_open_run
  -> workbench_select_model
  -> Goose performs the task
  -> workbench_record_execution
  -> workbench_validate_run
  -> workbench_quality_gate
  -> workbench_analyze_runs
```

A run is accepted only when deterministic validation and the quality gate support acceptance.

## Approved Prompt Catalog

Approved prompts live in `prompts/approved/`. The public library contains 12 reusable Workbench prompts:

| Prompt | Use |
|---|---|
| `bug_root_cause_investigation.md` | Investigate a bug, identify likely root cause, and define the smallest safe fix. |
| `code_review_patch_risk_audit.md` | Review a patch or AI-generated change set for correctness, regression, contract, and validation risk. |
| `data_acquisition_surface_audit.md` | Audit data acquisition, ingestion, scraping, upload, webhook, and external data surfaces. |
| `documentation_accuracy_audit.md` | Check documentation against actual code, commands, behavior, and configuration. |
| `implement_request_change_request.md` | Implement a bounded PRD, feature request, bug-fix request, or change request. |
| `navigation_page_title_ia_audit.md` | Audit navigation, page titles, labels, routing, and information architecture. |
| `performance_latency_hotspot_audit.md` | Identify performance and latency hot spots with concrete validation steps. |
| `prompt_failure_improvement_log.md` | Analyze prompt failures and record improvements for future runs. |
| `repository_context_index_audit.md` | Build or audit a repository context map for agent orientation. |
| `security_privacy_risk_review.md` | Review security and privacy risk in code, data flows, APIs, logs, and AI features. |
| `test_case_development_meaningful_coverage.md` | Develop meaningful test coverage for features, bug fixes, APIs, and workflows. |
| `ux_visual_accessibility_audit.md` | Audit UX, visual clarity, accessibility, and task completion quality. |

Focused v0.2 recipes use the most specific prompt by default: docs-only uses `documentation_accuracy_audit.md`, test-fix uses `bug_root_cause_investigation.md`, and a later test-creation workflow should use `test_case_development_meaningful_coverage.md`.

## Examples

- [Tiny Python fix](examples/tiny-python-fix/): a deliberately broken one-function project for recipe smoke tests.
- [Goose tool smoke](examples/goose-tool-smoke/): two-tool live smoke for slow local models.
- [Goose recipe smoke](examples/goose-recipe-smoke/): exact command for a low-risk Goose acceptance run.
- [Focused v0.2 workflows](examples/focused-workflows/): command examples for docs-only, package maintenance, test-fix, and low-risk coding workflows.
- [Docs-only acceptance recipe](recipes/workbench-docs-only-acceptance.yaml): focused documentation-only workflow using the `docs_only` validation profile.
- [Python package maintenance recipe](recipes/workbench-python-package-maintenance.yaml): focused package workflow using the `python_package_maintenance` validation profile.
- [Test-fix acceptance recipe](recipes/workbench-test-fix-acceptance.yaml): focused failing-test repair workflow using the `test_fix` validation profile.
- `low_risk_coding` validation profile: bounded implementation profile for the engineering acceptance recipe.
- [Sample accepted run](examples/sample-runs/accepted-tiny-python-fix/): sanitized committed evidence showing an accepted run folder.
- [Sample docs-only accepted run](examples/sample-runs/accepted-docs-only-smoke/): sanitized focused workflow evidence using `documentation_accuracy_audit` and `docs_only`.
- [Sample needs-review run](examples/sample-runs/needs-review-test-fix/): sanitized synthetic evidence showing failed validation and a revision-required quality gate.
- [Acceptance analytics guide](docs/analytics/acceptance-analytics.md): how to read `run_metrics.json`, `run_summary.md`, outcome buckets, routing feedback candidates, and optional cost fields.
- [Phase 5 dogfooding protocol](docs/dogfooding/phase5-dogfooding.md): how to collect real Goose acceptance runs before changing routing policy.
- [Launch issue seeds](docs/github/launch-issues.md): public alpha issue backlog for dogfooding, routing feedback, cost evidence, policy packs, CI, and demo work.

## Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -q -p no:cacheprovider
```

Run scaffold validation:

```bash
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/scaffold-smoke
```

## Roadmap

- `v0.1.0-alpha`: first public Goose MCP acceptance workflow.
- `v0.2.0-alpha`: focused recipe library and validation policy profiles.
- `v0.3`: accepted-artifact routing feedback.
- `v0.4`: accepted-artifact analytics.
- `v0.5`: CI mode for PR acceptance.
- `v1.0`: stable MCP contracts and recipe API.

## GitHub Topics

Suggested repository topics:

```text
goose
mcp
model-context-protocol
ai-agents
agentic-ai
coding-agents
developer-tools
validation
evals
quality-gates
audit-trail
```

## License

Apache-2.0. See [LICENSE](LICENSE).
