# Analytics Proof

Source evidence:

```text
examples/sample-runs/
```

Command:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/proof-sample-analytics
```

Do not commit `runs/proof-sample-analytics/`. It is generated local report output.

## Current Proof Signal

The committed sample evidence currently summarizes as:

| Metric | Value |
|---|---:|
| Runs total | 4 |
| Accepted | 3 |
| Review required | 1 |
| Failed | 0 |
| Acceptance rate | 0.75 |

Accepted runs by execution host:

| Execution host | Accepted |
|---|---:|
| `codex` | 1 |
| `goose` | 2 |

Scanned runs by execution host:

| Execution host | Runs |
|---|---:|
| `codex` | 1 |
| `goose` | 3 |

Accepted runs by response source:

| Response source | Accepted |
|---|---:|
| `codex` | 1 |
| `goose` | 2 |

Scanned runs by response source:

| Response source | Runs |
|---|---:|
| `codex` | 1 |
| `goose` | 3 |

## Why This Matters

Analytics does not decide whether an individual run is accepted. It summarizes already-recorded evidence:

- validation reports
- quality-gate decisions
- task metadata
- model selection metadata
- captured response source
- run logs

This proves Workbench can report cross-host outcomes without changing the core acceptance lifecycle.

## Routing Boundary

`routing_feedback_candidates` is report-ready input for future policy work. The current sample set is too small and synthetic to justify routing-policy changes.

Use analytics now to show evidence shape and failure reasons. Use dogfooding later to propose bounded routing experiments.

## Dashboard

The same command writes:

```text
run_metrics.json
run_summary.md
run_dashboard.html
```

`run_dashboard.html` links to evidence artifacts by relative path and does not embed raw model output or provider logs.
