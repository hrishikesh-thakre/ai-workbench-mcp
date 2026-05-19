# AI Workbench MCP Docs

This page is the public documentation map. New users should not need to read the historical proof and workstream folders before trying the package.

## Start Here

- [Package demo walkthrough](walkthroughs/package-demo.md): shortest first look at `ai-workbench-demo` and the three PR-gate outcomes.
- [How acceptance works](concepts/how-acceptance-works.md): the product model, MCP boundary, validation profiles, and quality gate.
- [External repo setup](github/external-repo-setup.md): shortest path for adding the PR gate workflow to another repository.
- [Goose acceptance demo](walkthroughs/goose-acceptance-demo.md): recording-ready public demo runbook.
- [Codex local/IDE workflow](codex/acceptance-workflow.md): second-host flow through the same MCP server.

## Operating References

- [START_HERE](ai/START_HERE.md), [DECISIONS](ai/DECISIONS.md), [PROJECT_MAP](ai/PROJECT_MAP.md), and [ROADMAP_STATUS](ai/ROADMAP_STATUS.md): maintainer orientation for the current release branch.
- [PR gate renderer](github/pr-gate.md) and [workflow template](github/pr-gate-workflow-template.md): GitHub-facing acceptance output from Workbench evidence.
- [Policy packs](policy-packs/index.md): the five first-class pack families and their accept/review/block behavior.
- [Model registry configuration](configuration/model-registry.md): local ignored model-tier overrides.

## Evidence And Analytics

- [Acceptance analytics](analytics/acceptance-analytics.md): `run_metrics.json`, `run_summary.md`, outcome buckets, routing feedback, and optional cost fields.
- [Evidence dashboard](analytics/evidence-dashboard.md): local static `run_dashboard.html`.
- [Event ledger](analytics/event-ledger.md): best-effort local `events.jsonl` operation records.
- [Golden-case harness](evals/golden-case-harness.md): local scoring for sanitized accepted evidence baselines.

## Publishing And Public Setup

- [PyPI publishing prep](publishing/pypi.md): package boundary and release checklist.
- [MCP Registry proof](publishing/mcp-registry-proof.md): registry publication record.
- [Repository topics](github/repository-topics.md), [launch issue creation record](github/create-launch-issues.md), and [launch issue seeds](github/launch-issues.md): public launch setup records.

## Historical/Internal Material

These folders remain useful for maintainers, but they are not first-run documentation:

- `docs/proof/`: sanitized proof summaries and demo records.
- `docs/dogfooding/`: Phase 5 and targeted evidence reports.
- `docs/agent-workstreams/`: internal agent handoff files and workstream notes.
- `docs/contracts/`: non-v1-stable contract baselines for downstream implementers.

Raw local `runs/` evidence remains ignored and should not be committed.
