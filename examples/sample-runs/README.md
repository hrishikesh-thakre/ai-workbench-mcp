# Sample Runs

This folder contains sanitized example evidence ledgers. These are committed
examples, not private local `runs/` history.

Use these samples for a no-provider first run or a public demo recording. They
show the evidence shape without requiring Goose, Codex, or a live model.

Current samples:

- `accepted-tiny-python-fix/`: v0.1 engineering acceptance lifecycle for a tiny Python fix.
- `accepted-codex-tiny-python-fix/`: sanitized Codex local/IDE lifecycle for the same tiny Python fix, with explicit `execution_host="codex"` and `response_source="codex"`.
- `accepted-docs-only-smoke/`: v0.2 focused docs-only acceptance lifecycle using `documentation_accuracy_audit` and `docs_only`.
- `needs-review-test-fix/`: synthetic test-fix lifecycle where validation fails and the quality gate requires revision.

Run analytics over the committed samples:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

First inspect individual runs, then inspect analytics:

- Accepted samples have `validation_report.json` with passed, sign-off-ready validation and `revision_decision.json` with `final_status="accepted"`.
- The needs-review sample shows failed deterministic validation and `final_status="revision_required"`.
- A blocked or failed local run should stay under ignored `runs/` unless it is intentionally sanitized for a public example.

See `docs/analytics/acceptance-analytics.md` for how to read `run_metrics.json`, `run_summary.md`, routing feedback candidates, and optional cost fields. See `docs/analytics/evidence-dashboard.md` for how to use the generated `run_dashboard.html`.

The Codex sample is intentionally committed as sample evidence, not as private run history. It proves that the same Workbench acceptance artifacts can identify a non-Goose execution host while keeping Goose as the default for older samples.

Accepted samples can also be scored by the local golden-case harness documented in `docs/evals/golden-case-harness.md`.

For real local runs, follow `docs/dogfooding/phase5-dogfooding.md`. Keep dogfood evidence in ignored `runs/` folders and promote only sanitized examples into this directory.

Rules for sample runs:

- No local machine paths.
- No provider secrets.
- No private target-repo names.
- Keep only enough evidence to explain the accepted run lifecycle.
