# Golden-Case Eval Harness

The golden-case harness scores Workbench evidence folders against sanitized accepted baselines. It is local evidence scoring only. It does not call providers, run Goose, benchmark models, review pull requests, or change routing policy.

Run the committed smoke cases:

```bash
python tools/golden_eval.py --cases-dir evals/golden_cases --source-runs-dir examples/sample-runs --out-dir runs/golden_eval_smoke
```

This writes one direct child folder per case:

```text
runs/golden_eval_smoke/<case_id>/
  model_eval_metadata.json
  score_report.json
```

`workbench_analyze_runs` can scan those reports:

```bash
python tools/run_analyze.py --runs-dir runs/golden_eval_smoke --out-dir runs/golden_eval_analytics --evals-dir evals/golden_cases
```

## Case Resolution

Batch mode evaluates each case against:

```text
<source-runs-dir>/<source_run_id>
```

Passing `--run-dir` overrides that source resolution for every selected case. Single-case mode writes reports directly to `--out-dir`; batch mode writes reports under `--out-dir/<case_id>/`.

## Exit Behavior

- Accepted single-case and batch smokes exit `0`.
- Valid scoring failures are written to `score_report.json` and still exit `0`.
- Invalid case JSON, invalid case schema, or a missing source run exits nonzero.

## Golden Case Hygiene

Committed golden cases contain short sanitized expectations only: metadata fields, required artifact filenames, and short required or forbidden output terms.

Do not put raw model output, run logs, local paths, private repo names, provider traces, secrets, or real cost values in committed golden case JSON.

## What It Scores

A case passes when the source run has the required artifacts, expected metadata, passed deterministic validation, an accepted quality gate, required output terms, and no forbidden output terms.

Stable failure modes include:

- `missing_artifact:<name>`
- `metadata_mismatch:<field>`
- `validation_not_passed`
- `quality_gate_not_accepted`
- `missing_output_term:<term>`
- `forbidden_output_term:<term>`
