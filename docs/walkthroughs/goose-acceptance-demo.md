# Goose Acceptance Demo Walkthrough

This is a recording-ready runbook for a 3-5 minute public demo. Use the sample evidence path for a reliable recording, then mention the optional live Goose path if the environment is already configured.

Do not show private run folders, provider credentials, raw provider logs, local absolute paths, or unreviewed `runs/` evidence.

Core wording:

```text
MCP is the connection protocol.
AI Workbench MCP is the tool server.
Acceptance is decided by the selected validation profile and quality gate.
The agent performs. Workbench accepts. MCP connects them.
```

## Demo Modes

Use the sample-only path as the primary public demo. It requires no provider, no live Goose execution, and no private evidence:

```text
examples/sample-runs/accepted-tiny-python-fix/
examples/sample-runs/accepted-docs-only-smoke/
examples/sample-runs/needs-review-test-fix/
```

Use the optional live Goose path only after Goose already has a provider configured and the local MCP server has been registered. The live path can be useful for a longer walkthrough, but it is not required for the public recording.

## 0:00-0:30: Open With The Boundary

Say:

```text
AI coding agents can say "done", but Workbench only accepts a run after evidence, deterministic validation, and a quality-gate decision.
MCP connects Goose to the AI Workbench MCP tool server. Goose performs the task. Workbench decides whether the evidence is accepted, review-required, or failed.
```

Show the README sections:

- `What MCP Does And Does Not Do`
- `Prompt DoD vs Acceptance Gate`
- `What Decides Acceptance`

## 0:30-1:15: Show The Evidence Ledger

Open the accepted sample folder:

```text
examples/sample-runs/accepted-tiny-python-fix/
```

Show the standard evidence files:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

Explain that Workbench records the requested task, selected tier, captured agent output, deterministic validation result, quality-gate decision, and run log in a local evidence folder.

## 1:15-2:00: Show Accepted Evidence

Open:

- `examples/sample-runs/accepted-tiny-python-fix/validation_report.json`
- `examples/sample-runs/accepted-tiny-python-fix/revision_decision.json`

Call out:

- `overall_status="passed"`
- `sign_off_ready=true`
- `final_status="accepted"`

Say:

```text
The prompt can describe done, but the prompt does not enforce done. This run is accepted because deterministic validation passed and the quality gate accepted the evidence.
```

## 2:00-2:45: Show Review-Required Evidence

Open:

- `examples/sample-runs/needs-review-test-fix/validation_report.json`
- `examples/sample-runs/needs-review-test-fix/revision_decision.json`

Call out:

- `overall_status="failed"`
- `sign_off_ready=false`
- `final_status="revision_required"`

Say:

```text
This is the same acceptance loop producing a different outcome. Workbench does not claim success when deterministic validation fails. The result becomes revision-required instead of accepted.
```

Use "review-required" when explaining the public outcome bucket, and point to `revision_required` as the exact quality-gate status written by the current sample evidence.

## 2:45-3:30: Show Analytics And Dashboard

Run analytics over committed sample evidence:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/demo-sample-analytics
```

Show:

- `runs/demo-sample-analytics/run_metrics.json`
- `runs/demo-sample-analytics/run_summary.md`
- `runs/demo-sample-analytics/run_dashboard.html`

Explain that analytics summarizes already-recorded evidence. It does not decide whether a single run is accepted, does not embed raw model output, and does not embed raw provider logs.

## 3:30-4:00: Optional Golden-Case Baseline

If there is time, run the local golden-case smoke:

```bash
python tools/golden_eval.py --cases-dir evals/golden_cases --source-runs-dir examples/sample-runs --out-dir runs/demo-golden-eval
```

Show that sanitized accepted evidence can become a local regression baseline without provider calls or live Goose execution. Do not present this as a model benchmark or provider evaluation.

## Optional Live Goose Path

Use this path only when the presenter wants to show Goose creating fresh evidence.

Install from the checked-out repository:

```bash
python -m pip install -e .
```

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

Run the tiny Python fix recipe:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/demo-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=tiny_python_fix \
  --params complexity_score=4
```

Then open:

- `runs/demo-tiny-python-fix/validation_report.json`
- `runs/demo-tiny-python-fix/revision_decision.json`

Do not commit `runs/demo-tiny-python-fix/`. It is local evidence.

## Close With The Wedge

Say:

```text
AI Workbench MCP turns AI-agent output into accepted, validated, auditable work, starting with Goose. The agent performs. Workbench accepts. MCP connects them.
```

Non-claims:

- AI Workbench MCP does not prove software correctness.
- It does not replace CI, code review, security review, or human judgment.
- MCP does not decide acceptance; Workbench validation profiles and quality gates do.
