# AI Workbench MCP

<!-- mcp-name: io.github.hrishikesh-thakre/ai-workbench-mcp -->

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Acceptance gates for AI coding-agent runs.

AI agents can produce code. AI Workbench MCP helps decide whether that work is accepted.

It records the task, captures agent output, runs deterministic validation, applies a quality gate, and creates an auditable run trail.

Works with Goose today. Designed as a host-agnostic acceptance layer for MCP-compatible agent workflows. Codex local/IDE is the first second-host target through explicit `execution_host` and `response_source` evidence metadata.

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

## Problem

AI coding agents can produce useful work, but "done" is not the same as accepted. A useful acceptance workflow needs reproducible evidence.

AI Workbench MCP provides that acceptance and audit layer, turning agent output into evidence-backed accepted runs.

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

## What MCP Does And Does Not Do

MCP is the connection protocol.

AI Workbench MCP is the tool server. MCP lets Goose, Codex local/IDE, or another compatible host call Workbench tools, but the protocol itself does not verify correctness, inspect code quality, or decide whether a run is accepted.

Workbench applies the acceptance policy by recording evidence, running deterministic validation, and applying the quality gate. See [how acceptance works](docs/concepts/how-acceptance-works.md) for the full distinction.

## Prompt DoD vs Acceptance Gate

A prompt definition-of-done tells the agent what to attempt and what evidence to report. Prompt instructions are not enforcement.

An acceptance gate checks the resulting evidence after the agent acts. It uses explicit validation profiles, command-backed checks, required artifacts, changed-file policies, and quality-gate rules. The same agent saying "done" is never enough for acceptance.

## What Decides Acceptance

Acceptance is decided by the selected validation profile and quality gate.

The validation profile runs deterministic checks such as tests, build or lint commands, artifact existence checks, and changed-file policy. The quality gate then accepts the run, requests review, requests revision, or leaves the run failed based on that evidence and the configured risk policy.

The agent performs. Workbench accepts. MCP connects them.

## 5-Minute Quickstart

Install the published MCP server package:

```bash
python -m pip install ai-workbench-mcp==0.2.0a0
```

For the full Goose recipe workflow in this checked-out repository, install from the repository root:

```bash
python -m pip install -e .
```

The published PyPI wheel is code/server only; full Goose recipe workflows require this checked-out repo because configs, prompts, recipes, examples, evals, and validation profiles are repo assets. See [the PyPI publishing prep guide](docs/publishing/pypi.md) for the packaging boundary and release checklist.

For a first local run, use this order:

1. Install from the checked-out repository with `python -m pip install -e .`.
2. Register `ai-workbench-mcp` in Goose.
3. Run the two-tool smoke to prove Goose can reach the MCP server.
4. Run one full acceptance recipe with a focused validation profile.
5. Inspect `validation_report.json` and `revision_decision.json` before calling the run accepted.

If Goose or a provider is not configured yet, use the committed sample evidence under `examples/sample-runs/` and the [Goose acceptance demo walkthrough](docs/walkthroughs/goose-acceptance-demo.md) first. That path shows the acceptance artifacts without creating private local evidence.

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

Choose the validation profile from the task shape:

| Task shape | Recipe | Validation profile |
|---|---|---|
| Documentation-only Markdown or example docs | `recipes/workbench-docs-only-acceptance.yaml` | `docs_only` |
| Low-risk bug fix with a focused regression command | `recipes/workbench-test-fix-acceptance.yaml` | `low_risk_bug_fix` |
| Bounded package, config, tool, recipe, or test maintenance | `recipes/workbench-python-package-maintenance.yaml` | `python_package_maintenance` |
| Repo-target failing test repair with a focused test command | `recipes/workbench-test-fix-acceptance.yaml` | `test_fix` |
| API or MCP contract change | `recipes/workbench-engineering-acceptance.yaml` | `api_contract_change` |
| Security or privacy-sensitive change | `recipes/workbench-engineering-acceptance.yaml` | `security_privacy_sensitive` |
| Intentionally broken demo fixture proof | `recipes/workbench-test-fix-acceptance.yaml` | `fixture_repair_proof` |
| General low-risk implementation with deterministic tests | `recipes/workbench-engineering-acceptance.yaml` | `low_risk_coding` |

See [focused v0.2 workflows](examples/focused-workflows/) for copy-ready commands.

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
  --params task="Fix the requested failing test signal with the smallest justified change, keep the repo test suite passing, and report the exact validation command." \
  --params task_test_command="python -m pytest tests/test_target.py -q" \
  --params risk=medium
```

The default `test_fix` profile is for repo-target repairs and requires the broader project suite. For intentionally broken demo fixtures, use the focused fixture proof profile instead:

```bash
goose run --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-fixture-repair-proof \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and do not edit unrelated files." \
  --params validation_profile=fixture_repair_proof \
  --params task_test_command="python -m unittest discover -s examples/tiny-python-fix -p test_*.py" \
  --params analytics_runs_dir=runs/goose-fixture-repair-proof \
  --params analytics_out_dir=runs/goose-fixture-repair-proof/_reports \
  --params risk=low
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

Read outcomes from the evidence, not from the agent's final prose:

- Accepted: `validation_report.json` has `overall_status="passed"` and `sign_off_ready=true`, and `revision_decision.json` has `final_status="accepted"`.
- Needs-review or revision: validation or quality-gate evidence is incomplete, risky, or failed, and the quality gate records a review or revision status such as `revision_required`.
- Blocked or failed: deterministic validation fails in a way that is not sign-off ready. Keep the evidence local, inspect the failing check, and do not call the run accepted.

## Codex Local/IDE

Codex uses the same `ai-workbench-mcp` server. The first Codex slice is local/IDE MCP support, not Codex cloud.

- [Codex setup](docs/codex/setup.md): configure Codex to call the existing MCP stdio server.
- [Codex acceptance workflow](docs/codex/acceptance-workflow.md): use the six-tool lifecycle with `execution_host="codex"` and `response_source="codex"`.
- [Codex AGENTS.md snippet](docs/codex/agents-snippet.md): reusable repository instruction block for Codex runs.
- [Codex cloud limitations](docs/codex/cloud-limitations.md): evidence persistence and export questions deferred to a later design pass.
- [Codex live-test handoff](docs/codex/live-test-handoff.md): batch/Python helper that runs safe preflight checks, shows a timer, prints a one-shot prompt, and checks the resulting Codex evidence folders.
- [Codex acceptance demo walkthrough](docs/walkthroughs/codex-acceptance-demo.md): bounded local/IDE proof path with loop and crash guardrails.

## Proof Pack

The v0.2 public proof pack is in [docs/proof/proof-pack-v0.2.md](docs/proof/proof-pack-v0.2.md).

It shows:

- accepted Goose evidence
- accepted Codex local/IDE evidence
- a fresh accepted Gemini Goose fixture proof summary
- a fresh accepted Codex local/IDE fixture proof summary
- review-required evidence
- analytics by execution host and response source
- a 3-5 minute demo script

The proof pack uses committed sanitized sample evidence under `examples/sample-runs/`. Raw local `runs/` evidence stays ignored.

## Sample Analytics Demo

To inspect the trust loop without provider setup, run analytics over the committed synthetic sample runs:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

The sample set includes accepted, docs-only accepted, and revision-required test-fix evidence. Read [the analytics guide](docs/analytics/acceptance-analytics.md) to interpret `run_metrics.json`, `run_summary.md`, outcome buckets, failure reasons, routing feedback candidates, and optional cost fields. Read [the evidence dashboard guide](docs/analytics/evidence-dashboard.md) to use the generated `run_dashboard.html` for local scanning and demos.

Core MCP operations also write best-effort local `events.jsonl` ledgers beside evidence artifacts. Read [the event ledger guide](docs/analytics/event-ledger.md) before using operation events in analytics or CI prototypes.

Run the committed golden-case eval smoke to score accepted sample evidence:

```bash
python tools/golden_eval.py --cases-dir evals/golden_cases --source-runs-dir examples/sample-runs --out-dir runs/golden_eval_smoke
```

The harness writes `model_eval_metadata.json` and `score_report.json` under one child folder per case. Read [the golden-case harness guide](docs/evals/golden-case-harness.md) before treating eval results as anything beyond local evidence-contract regression checks.

## Advisory Routing Feedback

`workbench_select_model` can optionally read `routing_feedback_candidates` from a previous analytics report. The feedback is advisory only: it records whether historical evidence supports the current tier, suggests escalation, or asks for more evidence, but it never changes `selected_tier`.

The implemented `prefer_current_tier` path is intentionally narrow: `docs_only_current_tier_when_accepted` applies only to low-risk, easy docs-only work that already selects `local_coding` and has enough accepted Workbench evidence. Other high-acceptance buckets stay advisory as `no_change` until a bounded policy is implemented for them.

Focused recipes pass `runs/_reports/run_metrics.json` as the default feedback source. Missing, invalid, or low-volume feedback is non-fatal and is recorded in `model_selection.json` under `routing_feedback`.

## Bring Your Own Models

The committed model registry lives at `configs/model_registry.yaml`. To customize model IDs or providers locally, copy `configs/model_registry.example.yaml` to `configs/model_registry.local.yaml` and edit the local file. The local override is ignored by git, recursively merges into the base registry, and is recorded in `model_selection.json` with repo-relative source metadata.

See [the model registry guide](docs/configuration/model-registry.md) for merge rules, required tier fields, selector-reference validation, and the advisory-only scope.

## Six MCP Tools

```text
workbench_open_run
  -> creates the run folder, task metadata, final prompt, context packet, and initial run log
     records execution_host, defaulting to goose

workbench_select_model
  -> recommends a model/runtime tier and writes model_selection.json

workbench_record_execution
  -> captures raw Goose/Codex/model response text into model_output.md and appends run_log.jsonl
     records response_source, defaulting to goose

workbench_validate_run
  -> runs deterministic validation and writes validation_report.json

workbench_quality_gate
  -> accepts, rejects, or requests review and writes revision_decision.json

workbench_analyze_runs
  -> summarizes accepted-run metrics by execution host, response source, recipe, validation profile, model tier, failure reason, and quality-gate outcome under runs/_reports
     and writes run_dashboard.html for local evidence scanning
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

For the detailed acceptance model, read [how acceptance works](docs/concepts/how-acceptance-works.md).

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
- [Codex tool smoke](examples/codex-tool-smoke/): two-tool local/IDE MCP smoke using `execution_host="codex"`.
- [Codex acceptance smoke](examples/codex-acceptance-smoke/): full six-tool local/IDE lifecycle using `response_source="codex"`.
- [Focused v0.2 workflows](examples/focused-workflows/): command examples for docs-only, low-risk bug-fix, package maintenance, test-fix, API/contract, security/privacy, and low-risk coding workflows.
- [How acceptance works](docs/concepts/how-acceptance-works.md): the MCP protocol, Workbench server, validation profile, and quality-gate distinction.
- [Docs-only acceptance recipe](recipes/workbench-docs-only-acceptance.yaml): focused documentation-only workflow using the `docs_only` validation profile.
- [Python package maintenance recipe](recipes/workbench-python-package-maintenance.yaml): focused package workflow using the `python_package_maintenance` validation profile.
- [Test-fix acceptance recipe](recipes/workbench-test-fix-acceptance.yaml): focused failing-test repair workflow using the `test_fix` validation profile.
- Core policy-pack profiles: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive` in `configs/validation_profiles.yaml`.
- `low_risk_coding` validation profile: bounded implementation profile for the engineering acceptance recipe.
- [Fresh Gemini fixture proof](docs/proof/gemini-fixture-accepted-run.md): sanitized live Goose proof summary using `fixture_repair_proof` with isolated analytics.
- [Fresh Codex fixture proof](docs/proof/codex-fixture-accepted-run.md): sanitized live Codex local/IDE proof summary using `fixture_repair_proof` with host/source evidence.
- [Sample accepted run](examples/sample-runs/accepted-tiny-python-fix/): sanitized committed evidence showing an accepted run folder.
- [Sample Codex accepted run](examples/sample-runs/accepted-codex-tiny-python-fix/): sanitized Codex local/IDE evidence showing `execution_host="codex"` and `response_source="codex"`.
- [Sample docs-only accepted run](examples/sample-runs/accepted-docs-only-smoke/): sanitized focused workflow evidence using `documentation_accuracy_audit` and `docs_only`.
- [Sample needs-review run](examples/sample-runs/needs-review-test-fix/): sanitized synthetic evidence showing failed validation and a revision-required quality gate.
- [Acceptance analytics guide](docs/analytics/acceptance-analytics.md): how to read `run_metrics.json`, `run_summary.md`, outcome buckets, routing feedback candidates, and optional cost fields.
- [Evidence dashboard guide](docs/analytics/evidence-dashboard.md): how to read the static `run_dashboard.html` generated by run analytics.
- [Event ledger guide](docs/analytics/event-ledger.md): how local `events.jsonl` operation telemetry is written and why it stays out of committed runs by default.
- [v0.2 contract baseline](docs/contracts/v0.2-contract-baseline.md): current non-v1-stable run evidence, MCP envelope, analytics, policy, and PR gate artifact shapes.
- [Golden-case harness guide](docs/evals/golden-case-harness.md): how to score sanitized accepted evidence baselines locally.
- [Phase 5 dogfooding protocol](docs/dogfooding/phase5-dogfooding.md): completed dogfooding protocol, evidence hygiene rules, and the path to bounded routing-policy experiments.
- [Model registry configuration](docs/configuration/model-registry.md): how to bring your own model tiers with a local ignored override.
- [CI gate prototype](docs/github/pr-gate.md): what the repo self-validation workflow proves and why semantic PR acceptance comes later.
- [Launch issue seeds](docs/github/launch-issues.md): public alpha issue backlog for dogfooding, routing feedback, cost evidence, policy packs, CI, and demo work.
- [PyPI publishing prep](docs/publishing/pypi.md): package build, twine, wheel smoke, and release boundary.
- [Repository topics](docs/github/repository-topics.md): recommended GitHub topics and setup commands.
- [Launch issue creation record](docs/github/create-launch-issues.md): created public issue links plus recovery-only creation commands.
- [Goose acceptance demo walkthrough](docs/walkthroughs/goose-acceptance-demo.md): recording-ready 3-5 minute public demo runbook.
- [Codex acceptance demo walkthrough](docs/walkthroughs/codex-acceptance-demo.md): local/IDE proof path that avoids nested Codex or foreground stdio-server loops.

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
- Phase 5 complete: accepted-artifact analytics, Codex local/IDE proof, PyPI/MCP Registry publication, and 31 complete dogfood evidence runs.
- Current: GitHub-native CI gate prototype with guarded sticky PR comments, fallback scaffold evidence labeling, and the first bounded docs-only advisory routing policy.
- Next: additional bounded routing-policy experiments, semantic PR acceptance enforcement, Checks API integration, first-class policy metadata, cost/time evidence, and stable contract packaging.
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
