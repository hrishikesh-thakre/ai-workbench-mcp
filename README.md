# AI Workbench MCP

<!-- mcp-name: io.github.hrishikesh-thakre/ai-workbench-mcp -->

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Acceptance gates for AI coding-agent runs.

AI agents can produce code. AI Workbench MCP helps decide whether that work is accepted by recording evidence, running deterministic validation, applying a quality gate, and rendering auditable outcomes.

Works with Goose today. Designed as a host-agnostic acceptance layer for MCP-compatible agent workflows. Codex local/IDE is the first second-host target through explicit `execution_host="codex"` and `response_source="codex"` evidence metadata.

Current source metadata targets unpublished `ai-workbench-mcp==0.7.0a0` for the next release-candidate pass. `ai-workbench-mcp==0.6.0a0` remains the latest published PyPI and MCP Registry package, and the external PR-gate workflow stays pinned to that published version until a future release is explicitly approved.

## Before

The agent says: "Done."

## After

AI Workbench shows:

- what task was requested
- what agent/model/runtime was used
- what output was produced
- what validation ran
- whether the quality gate accepted, rejected, or requested review
- where the evidence lives

```text
runs/example/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

AI Workbench turns agent output into evidence-backed accepted runs.

## 5-Minute Quickstart

Try the source package demo first. It does not require Goose, provider credentials, a target repository, or committed `runs/` evidence.

```bash
python -m pip install -e .
ai-workbench-demo --target ./workbench-first-run
```

Module fallback:

```bash
python -m ai_workbench_mcp.tools.demo --target ./workbench-first-run
```

Expected outputs:

```text
./workbench-first-run/ai-workbench-demo/accepted/pr_decision.json      -> accept
./workbench-first-run/ai-workbench-demo/needs-review/pr_decision.json  -> needs_review
./workbench-first-run/ai-workbench-demo/blocked/pr_decision.json       -> block
```

The demo uses synthetic fixture evidence to show the PR-gate renderer. It is not a real target-repo acceptance run and is not a shortcut around validation or the quality gate.

To add the published `0.6.0a0` PR gate assets to a repository:

```bash
python -m pip install ai-workbench-mcp==0.6.0a0
ai-workbench-bootstrap --target .
```

That command writes starter configs, prompts, recipes, `.github/workflows/ai-workbench-pr-gate.yml`, `docs/ai-workbench-pr-gate.md`, and keeps `runs/` ignored. See [Use AI Workbench PR Gate in your repo in 10 minutes](docs/github/external-repo-setup.md).

## What MCP Does And Does Not Do

MCP is the connection protocol.

AI Workbench MCP is the tool server. MCP lets Goose, Codex local/IDE, or another compatible host call Workbench tools, but the protocol itself does not verify correctness, inspect code quality, or decide whether a run is accepted.

Acceptance is decided by the selected validation profile and quality gate. The agent performs. Workbench accepts. MCP connects them. See [how acceptance works](docs/concepts/how-acceptance-works.md).

## Prompt DoD vs Acceptance Gate

A prompt definition-of-done tells the agent what to attempt and what evidence to report. Prompt instructions are not enforcement.

An acceptance gate checks the resulting evidence after the agent acts. It uses explicit validation profiles, command-backed checks, required artifacts, changed-file policies, and quality-gate rules. The same agent saying "done" is never enough for acceptance.

## What Decides Acceptance

The validation profile runs deterministic checks such as tests, build or lint commands, artifact existence checks, and changed-file policy. The quality gate then accepts the run, requests review, requests revision, or leaves the run failed based on that evidence and the configured risk policy.

For a PR gate to report `accept`, the referenced run must include acceptance-supporting `validation_report.json` and `revision_decision.json`. Scaffold-only evidence is visibility evidence, not semantic acceptance evidence, and blocks with `pr_gate.acceptance_evidence_missing`.

## Seven MCP Tools

```text
workbench_open_run
  -> creates the run folder, task metadata, final prompt, context packet, and initial run log
workbench_select_policy_pack
  -> recommends an advisory policy pack and matching validation profile from task metadata
workbench_select_model
  -> recommends a model/runtime tier and writes model_selection.json
workbench_record_execution
  -> captures Goose/Codex/model output into model_output.md and records response_source
workbench_validate_run
  -> runs deterministic validation and writes validation_report.json
workbench_quality_gate
  -> accepts, rejects, or requests review and writes revision_decision.json
workbench_analyze_runs
  -> summarizes accepted-run metrics and writes run_dashboard.html for local scanning
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

## Goose And Codex

Goose remains the default execution surface. Register the MCP server with `goose configure`, choose a command-line extension, and use `ai-workbench-mcp` as the command. Start with `recipes/workbench-mcp-tool-smoke.yaml`, then use `recipes/workbench-engineering-acceptance.yaml` or a focused recipe such as `recipes/workbench-docs-only-acceptance.yaml`, `recipes/workbench-python-package-maintenance.yaml`, or `recipes/workbench-test-fix-acceptance.yaml`.

Codex local/IDE uses the same `ai-workbench-mcp` server, not a separate Codex server. Read [Codex setup](docs/codex/setup.md), [Codex acceptance workflow](docs/codex/acceptance-workflow.md), [Codex AGENTS.md snippet](docs/codex/agents-snippet.md), [Codex cloud limitations](docs/codex/cloud-limitations.md), [Codex live-test handoff](docs/codex/live-test-handoff.md), and the [Codex acceptance demo walkthrough](docs/walkthroughs/codex-acceptance-demo.md). The handoff helper checks the resulting Codex evidence folders.

## Policy Packs

The five first-class policy packs are `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`. Their catalog metadata lives in `configs/policy_packs.yaml`, maps each pack to a validation profile, and is documented in [docs/policy-packs/](docs/policy-packs/).

Other useful starter profiles include `python_package_maintenance`, `fixture_repair_proof`, and `low_risk_coding`. For copy-ready commands, see [examples/focused-workflows](examples/focused-workflows/).

## Examples And Demos

- [Tiny Python fix](examples/tiny-python-fix/): deliberately broken one-function fixture.
- [Goose tool smoke](examples/goose-tool-smoke/): slow-local-model two-tool smoke.
- [Goose recipe smoke](examples/goose-recipe-smoke/): low-risk Goose acceptance run.
- [Codex tool smoke](examples/codex-tool-smoke/) and [Codex acceptance smoke](examples/codex-acceptance-smoke/): local/IDE host proof.
- [Sample accepted run](examples/sample-runs/accepted-tiny-python-fix/), [sample Codex accepted run](examples/sample-runs/accepted-codex-tiny-python-fix/), [sample docs-only accepted run](examples/sample-runs/accepted-docs-only-smoke/), and [sample needs-review run](examples/sample-runs/needs-review-test-fix/): sanitized committed evidence.
- [PR gate outcome demos](docs/proof/pr-gate-outcome-demos.md): sanitized fixtures for `accept`, `needs_review`, and `block`.
- [Fresh Gemini fixture proof](docs/proof/gemini-fixture-accepted-run.md) and [Fresh Codex fixture proof](docs/proof/codex-fixture-accepted-run.md): live proof summaries using `fixture_repair_proof`.
- [Goose acceptance demo walkthrough](docs/walkthroughs/goose-acceptance-demo.md): recording-ready 3-5 minute public demo runbook.

## Docs Map

Start with [docs/README.md](docs/README.md) for the public documentation map.

Frequently used docs:

- [Acceptance model](docs/concepts/how-acceptance-works.md)
- [PR gate renderer](docs/github/pr-gate.md) and [copy-paste workflow template](docs/github/pr-gate-workflow-template.md)
- [External repo setup](docs/github/external-repo-setup.md) and [external sample repo proof](docs/github/external-sample-repo-plan.md)
- [Acceptance analytics](docs/analytics/acceptance-analytics.md), [evidence dashboard](docs/analytics/evidence-dashboard.md), and [event ledger](docs/analytics/event-ledger.md)
- [v0.2 contract baseline](docs/contracts/v0.2-contract-baseline.md)
- [Golden-case harness](docs/evals/golden-case-harness.md)
- [Model registry configuration](docs/configuration/model-registry.md)
- [PyPI publishing prep](docs/publishing/pypi.md)
- [Repository topics](docs/github/repository-topics.md), [launch issue creation record](docs/github/create-launch-issues.md), and [launch issue seeds](docs/github/launch-issues.md)

Historical/internal proof and planning material is intentionally not the first path for new users. It remains available under [docs/proof/](docs/proof/) and [docs/dogfooding/](docs/dogfooding/), including [Phase 5 dogfooding protocol](docs/dogfooding/phase5-dogfooding.md) and [v0.4 policy-pack validation report](docs/dogfooding/v0.4-policy-pack-validation-report.md).

## Approved Prompt Catalog

Approved prompts live in `prompts/approved/`. The catalog includes `bug_root_cause_investigation.md`, `code_review_patch_risk_audit.md`, `data_acquisition_surface_audit.md`, `documentation_accuracy_audit.md`, `implement_request_change_request.md`, `navigation_page_title_ia_audit.md`, `performance_latency_hotspot_audit.md`, `prompt_failure_improvement_log.md`, `repository_context_index_audit.md`, `security_privacy_risk_review.md`, `test_case_development_meaningful_coverage.md`, and `ux_visual_accessibility_audit.md`.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider
python -m ruff check . --no-cache
python -m mypy --no-sqlite-cache --no-incremental
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/scaffold-smoke
```

Do not commit `runs/`. It is the local evidence ledger. The root `tools/` scripts remain backward-compatible shims; new package-oriented docs should prefer `python -m ai_workbench_mcp.tools.<name>` or a console script when one exists.

## Roadmap

- `v0.1.0-alpha`: first public Goose MCP acceptance workflow.
- `v0.2.0-alpha`: focused recipe library and validation policy profiles.
- Phase 5 complete: accepted-artifact analytics, Codex local/IDE proof, PyPI/MCP Registry publication, and 31 complete dogfood evidence runs.
- Current: v0.7 version-boundary reset and release-candidate prep on top of the published v0.6 external PR-gate adoption package.
- Next after v0.7: stable contract fixture hardening, then Checks API integration, fork-comment strategy, and cost/time evidence.
- `v1.0`: stable MCP contracts and recipe API.

## License

Apache-2.0. See [LICENSE](LICENSE).
