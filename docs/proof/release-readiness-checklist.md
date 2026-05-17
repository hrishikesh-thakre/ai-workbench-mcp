# Proof Pack Release Readiness Checklist

Use this checklist before sharing the v0.2 proof pack publicly.

## Proof Artifacts

- [x] Accepted Goose sample evidence exists.
- [x] Accepted Codex local/IDE sample evidence exists.
- [x] Review-required sample evidence exists.
- [x] Analytics proof documents host/source outcome breakdowns.
- [x] Demo script exists.
- [x] README links to the proof pack.
- [x] PyPI package path is documented.
- [x] MCP Registry proof is documented.

## Validation

Run before committing proof-pack changes:

```bash
python -m pytest -q -p no:cacheprovider
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/proof-final-scaffold
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/proof-final-analytics
git diff --check
git status --short
```

Expected:

- tests pass
- scaffold validation passes
- sample analytics writes `run_metrics.json`, `run_summary.md`, and `run_dashboard.html`
- no generated `runs/` files are staged
- no private paths, secrets, or raw provider logs are committed

## Public Claims Allowed

- AI Workbench MCP is an acceptance layer for AI coding-agent runs.
- Goose is the default host.
- Codex local/IDE is represented through host/source evidence metadata.
- Acceptance is based on validation profiles and quality gates.
- Analytics summarizes accepted and review-required evidence.

## Public Claims To Avoid

- broad adoption
- optimized model routing
- Codex cloud support
- automatic correctness verification
- replacement for CI, code review, security review, or human judgment
- mature PR acceptance gate

## Next Evidence After This Pack

- Phase 5 evidence collection is complete; use `docs/dogfooding/phase5-final-report.md` as the closeout baseline.
- Collect new evidence only for bounded routing-policy experiments, PR-gate behavior, policy-pack gaps, or additional host/source proof.
- Keep routing feedback advisory until a policy experiment branch proves a candidate change with fresh isolated evidence.
