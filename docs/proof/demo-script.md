# Demo Script

Target length: 3-5 minutes  
Primary mode: committed sample evidence  
Optional mode: live Goose or Codex run after the environment is configured

## Opening

Say:

```text
AI coding agents can say "done", but Workbench only accepts a run after evidence, deterministic validation, and a quality-gate decision.
MCP connects Goose or Codex to the AI Workbench MCP tool server. The agent performs. Workbench accepts. MCP connects them.
```

Show:

- `README.md`
- `docs/concepts/how-acceptance-works.md`

Call out:

```text
MCP is the connection protocol.
AI Workbench MCP is the tool server.
Acceptance is decided by the selected validation profile and quality gate.
```

## Accepted Goose Evidence

Open:

```text
examples/sample-runs/accepted-tiny-python-fix/
```

Show the standard artifacts:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

Open:

```text
examples/sample-runs/accepted-tiny-python-fix/validation_report.json
examples/sample-runs/accepted-tiny-python-fix/revision_decision.json
```

Say:

```text
This run is accepted because deterministic validation passed and the quality gate accepted it.
```

Point to:

```text
overall_status = passed
sign_off_ready = true
final_status = accepted
```

## Codex Local/IDE Evidence

Open:

```text
examples/sample-runs/accepted-codex-tiny-python-fix/task_metadata.json
examples/sample-runs/accepted-codex-tiny-python-fix/model_output.md
```

Say:

```text
This uses the same Workbench server and evidence lifecycle, but the evidence records Codex as the host and source.
```

Point to:

```text
execution_host = codex
Response Source = codex
```

## Review-Required Evidence

Open:

```text
examples/sample-runs/needs-review-test-fix/validation_report.json
examples/sample-runs/needs-review-test-fix/revision_decision.json
```

Say:

```text
This is the same loop producing a different outcome. Workbench does not claim acceptance when deterministic validation fails.
```

Point to:

```text
overall_status = failed
sign_off_ready = false
final_status = revision_required
```

Explain that public analytics groups `revision_required` into the `review_required` bucket.

## Analytics

Run:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/demo-sample-analytics
```

Open:

```text
runs/demo-sample-analytics/run_summary.md
runs/demo-sample-analytics/run_dashboard.html
```

Call out:

```text
Accepted: 3
Review required: 1
Accepted by execution host: codex=1, goose=2
Response source counts: codex=1, goose=3
```

Say:

```text
Analytics summarizes recorded evidence. It does not decide acceptance for an individual run.
```

## Optional Live Segment

Use this only when the local environment is already configured.

For Goose:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/demo-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile_override=tiny_python_fix \
  --params complexity_score=4
```

For Codex:

```bash
python tools/codex_live_test_handoff.py --countdown-seconds 15
```

If Goose is configured with a different model or provider, keep the demo focused on the evidence and gate outcome. Do not claim a model comparison from a single run.

## Close

Say:

```text
AI Workbench MCP turns AI-agent output into accepted, validated, auditable work, starting with Goose and extending to Codex local/IDE through the same evidence lifecycle.
The agent performs. Workbench accepts. MCP connects them.
```

Non-claims:

- AI Workbench MCP does not prove software correctness.
- It does not replace CI, code review, security review, or human judgment.
- MCP does not decide acceptance; Workbench validation profiles and quality gates do.
