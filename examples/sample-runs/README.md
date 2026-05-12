# Sample Runs

This folder contains sanitized example evidence ledgers. These are committed
examples, not private local `runs/` history.

Current samples:

- `accepted-tiny-python-fix/`: v0.1 engineering acceptance lifecycle for a tiny Python fix.
- `accepted-docs-only-smoke/`: v0.2 focused docs-only acceptance lifecycle using `documentation_accuracy_audit` and `docs_only`.
- `needs-review-test-fix/`: synthetic test-fix lifecycle where validation fails and the quality gate requires revision.

Run analytics over the committed samples:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

See `docs/analytics/acceptance-analytics.md` for how to read `run_metrics.json`, `run_summary.md`, routing feedback candidates, and optional cost fields.

Rules for sample runs:

- No local machine paths.
- No provider secrets.
- No private target-repo names.
- Keep only enough evidence to explain the accepted run lifecycle.
