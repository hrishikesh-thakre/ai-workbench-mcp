# Evidence Dashboard

`workbench_analyze_runs` writes a static `run_dashboard.html` beside `run_metrics.json` and `run_summary.md`.

Generate it from the committed sample runs:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-dashboard
```

This creates:

- `run_metrics.json`: machine-readable analytics and routing feedback candidates.
- `run_summary.md`: Markdown summary for text review.
- `run_dashboard.html`: single-file local dashboard for scanning the same evidence.

## What It Shows

The dashboard is a local report for acceptance evidence. It shows:

- accepted, review-required, failed, and total run counts
- evidence scope and excluded-run count
- acceptance rate and average confidence
- outcome and quality-gate counts
- common failure reasons
- breakdowns by recipe, execution host, response source, validation profile, selected tier, and quality-gate outcome
- routing feedback candidates for later model-selection policy work
- optional provider cost and time evidence status
- per-run outcome, agent/model, policy/profile/gate, failure reason, token, cost, provider-time, validation-time, and evidence-link fields
- relative links to standard run evidence files

## Run Evidence Table

The run table is meant for fast review without opening every artifact first:

- `Outcome` uses the public buckets from analytics: `accepted`, `review_required`, `failed`, or `other`.
- `Agent / Model` shows execution host, response source, selected provider/model when available, and selected tier.
- `Policy` shows validation profile, quality-gate outcome, risk, and complexity.
- `Failure Reasons` shows deterministic validation and quality-gate reasons for non-accepted runs.
- `Cost / Time` shows tokens, estimated provider cost, provider-call duration, and validation-command duration only when evidence exists.
- `Evidence Links` points to standard artifacts by relative path.

## What It Does Not Show

The dashboard does not embed raw model output, raw provider logs, or run artifact bodies. It links to standard evidence files by relative path so a reviewer can open them deliberately.

Cost fields are shown only when real provider cost or token metadata exists. Empty or zero cost values mean no provider cost evidence was found, not free execution. Time fields are shown only when validation reports or provider-call metadata record explicit durations.

## Hygiene Boundary

`run_dashboard.html` is generated local evidence under ignored `runs/` by default. Do not commit generated dashboards unless a future sanitized sample intentionally demonstrates one.

The generator escapes run metadata before rendering HTML and keeps artifact links relative. This keeps the report useful for local review without turning it into a private run-history archive.

## Relationship To Analytics

Use `run_dashboard.html` for fast scanning and demos. Use `run_metrics.json` for automation, routing feedback candidates, and future policy work. Use `run_summary.md` when you need a compact text report.
