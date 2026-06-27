# AI Workbench

<!-- mcp-name: io.github.hrishikesh-thakre/ai-workbench-mcp -->

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

AI Workbench supervises AI coding agents, captures evidence, validates work,
applies acceptance policy, and produces auditable PR-ready reports.

The PyPI package remains `ai-workbench-mcp` for this public alpha because the
`ai-workbench` package name is already occupied. The product and CLI are
**AI Workbench**:

```bash
pip install ai-workbench-mcp
ai-workbench --help
```

Current source metadata targets unpublished `ai-workbench-mcp==0.8.0a0`.
This public alpha consolidates local supervision, evidence capture, validation,
acceptance policy, and PR reporting into one product surface.

## Public Alpha Warning

The supervisor is the preferred automated evidence path, but daemon, Codex hook,
and OpenCode adapter coverage are alpha mechanisms. AI Workbench checks evidence
quality and acceptance readiness; it does not prove the work is absolutely
correct. High-risk work still requires human review.

## Architecture

- AI Workbench supervisor captures local evidence.
- AI Workbench validation writes `validation_report.json`.
- AI Workbench quality gate writes `revision_decision.json`.
- AI Workbench PR/report surfaces render `accept`, `needs_review`, or `block`.

Agent output is a proposal. Workbench accepts evidence.

MCP is the connection protocol. AI Workbench MCP is the tool server.
Acceptance is decided by the selected validation profile and quality gate.
The agent performs. Workbench accepts. MCP connects them.

## Quick Start

Register a project once and start the local supervisor:

```bash
pip install ai-workbench-mcp
ai-workbench supervisor setup --project-dir . --task-type code_change
ai-workbench supervisor start
```

Run Codex, OpenCode, Goose, or another supported local workflow in the project.
Then inspect the latest report:

```bash
ai-workbench supervisor status
ai-workbench reports show latest --project-dir .
```

Render PR-ready artifacts from a finalized run:

```bash
ai-workbench pr-gate --run-dir runs/<run_id>
```

The canonical local run ledger is:

```text
runs/<run_id>/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
  metadata.json
  transcript.jsonl
  commands.jsonl
  workspace/
  validation/
  artifacts/
```

`validation_report.json` and `revision_decision.json` are the final acceptance
authority. Supporting supervisor reports are local evidence, not a substitute
for those Workbench artifacts.

## Codex Hooks

Install project-local Codex hooks:

```bash
ai-workbench setup codex --project-dir . --task-type code_change
```

Restart Codex or start a new session, open `/hooks`, review the project hook,
and trust it once. Until a hook event is observed, supervisor status reports
Codex coverage as configured but unverified.

## Goose MCP

AI Workbench still exposes the same MCP tool lifecycle. Register the server with
Goose or another MCP host using:

```bash
ai-workbench mcp serve
```

The seven MCP tools remain:

```text
workbench_open_run
workbench_select_policy_pack
workbench_select_model
workbench_record_execution
workbench_validate_run
workbench_quality_gate
workbench_analyze_runs
```

## PR Gate

Workbench PR acceptance consumes real Workbench run evidence:

```bash
ai-workbench pr-gate \
  --run-dir runs/<run_id> \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Outcomes are exactly:

- `accept`
- `needs_review`
- `block`

Missing, unreadable, or scaffold-only evidence blocks. A green CI run, uploaded
artifact, sticky PR comment, or model self-claim is not acceptance evidence.

## Bootstrap Assets

To add starter configs, prompts, recipes, docs, and the GitHub PR-gate workflow
to a repository:

```bash
ai-workbench bootstrap --target .
```

The bootstrap keeps `runs/` ignored.

## Package Demo

For a package-only synthetic demo:

```bash
ai-workbench demo --target ./workbench-first-run
```

This shows `accept`, `needs_review`, and `block` PR-gate outcomes with fixture
evidence. It is not a real target-repository acceptance run.

## Development

```bash
python -m pip install -e ".[dev,publish]"
python -m pytest -q -p no:cacheprovider
python -m ruff check . --no-cache
python -m mypy --no-sqlite-cache --no-incremental
ai-workbench demo --target runs/package_demo_smoke
ai-workbench validate --project ai_workbench_mcp --profile scaffold --run-dir runs/scaffold-smoke
```

Do not commit `runs/`. Committed sample evidence must be sanitized and live
under `examples/`.

## Docs

- [Supervisor docs](docs/supervisor/automated-evidence-supervisor.md)
- [Evidence folder contract](docs/supervisor/evidence-folder-contract.md)
- [Transcript schema](docs/supervisor/transcript-schema.md)
- [Workspace hygiene](docs/supervisor/workspace-hygiene.md)
- [Confidence rules](docs/supervisor/confidence-rules.md)
- [How acceptance works](docs/concepts/how-acceptance-works.md)
- [Contract baseline](docs/contracts/v0.2-contract-baseline.md)
- [Package demo walkthrough](docs/walkthroughs/package-demo.md)
- [Codex setup](docs/codex/setup.md)
- [Codex live-test handoff](docs/codex/live-test-handoff.md)
- [Codex acceptance walkthrough](docs/walkthroughs/codex-acceptance-demo.md)
- [Acceptance analytics](docs/analytics/acceptance-analytics.md)
- [Evidence dashboard](docs/analytics/evidence-dashboard.md)
- [Event ledger](docs/analytics/event-ledger.md)
- [Golden-case harness](docs/evals/golden-case-harness.md)
- [Model registry](docs/configuration/model-registry.md)
- [Dogfooding guide](docs/dogfooding/phase5-dogfooding.md)
- [Goose demo walkthrough](docs/walkthroughs/goose-acceptance-demo.md) - recording-ready 3-5 minute public demo runbook
- [Policy packs](docs/policy-packs/)
- [PR gate](docs/github/pr-gate.md)
- [Launch issues](docs/github/launch-issues.md)
- [Repository topics](docs/github/repository-topics.md)
- [Create launch issues](docs/github/create-launch-issues.md)
- [Publishing guide](docs/publishing/pypi.md)
- [Gemini fixture proof](docs/proof/gemini-fixture-accepted-run.md)
- [Codex fixture proof](docs/proof/codex-fixture-accepted-run.md)

Recipes:

- [Engineering acceptance](recipes/workbench-engineering-acceptance.yaml)
- [MCP tool smoke](recipes/workbench-mcp-tool-smoke.yaml)
- [Docs-only acceptance](recipes/workbench-docs-only-acceptance.yaml)
- [Python package maintenance](recipes/workbench-python-package-maintenance.yaml)
- [Test-fix acceptance](recipes/workbench-test-fix-acceptance.yaml)

Sample evidence:

- [Accepted tiny Python fix](examples/sample-runs/accepted-tiny-python-fix)
- [Accepted Codex tiny Python fix](examples/sample-runs/accepted-codex-tiny-python-fix)
- [Accepted docs-only smoke](examples/sample-runs/accepted-docs-only-smoke)
- [Needs-review test fix](examples/sample-runs/needs-review-test-fix)

## License

Apache-2.0. See [LICENSE](LICENSE). MIT-origin attribution for the consolidated
Prove It code is retained in [NOTICE](NOTICE).
