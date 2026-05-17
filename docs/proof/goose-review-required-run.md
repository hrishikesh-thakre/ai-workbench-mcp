# Review-Required Run Proof

Evidence folder:

```text
examples/sample-runs/needs-review-test-fix/
```

## Claim

AI Workbench MCP does not rubber-stamp agent output. When deterministic validation fails, the quality gate blocks acceptance and records a review or revision path.

## Task Class

The sample represents a test-fix workflow where deterministic validation fails.

## Evidence Summary

| Field | Value |
|---|---|
| Execution host | `goose` by default for historical samples |
| Response source | `goose` |
| Recipe | `workbench-test-fix-acceptance.yaml` |
| Validation profile | `test_fix` |
| Public outcome bucket | `review_required` |
| Quality-gate status | `revision_required` |

Standard artifacts:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

## Blocking Evidence

`validation_report.json` records:

```text
overall_status = failed
sign_off_ready = false
confidence = 0.4
commands_failed = 1
```

The failed deterministic command is:

```bash
python -m pytest -q -p no:cacheprovider
```

The review checks also record:

```text
captured_response_format = needs_review
```

The missing-context note is:

```text
Review the failed full_test_suite output before another implementation pass.
```

`revision_decision.json` records:

```text
final_status = revision_required
accepted_pass = 0
loop_type = blocking_findings
```

Blocking findings:

```text
Required validation command full_test_suite failed.
The run cannot be accepted until deterministic validation passes.
```

## Interpretation

This is the most important negative proof. The agent can provide a captured response, but Workbench refuses acceptance because the deterministic validation evidence does not support sign-off.

In public analytics, `revision_required` is grouped into the `review_required` bucket so users can distinguish non-accepted evidence that still has a clear next action from hard failed runs.
