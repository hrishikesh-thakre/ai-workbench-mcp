# Goose Acceptance Demo Walkthrough

This is a skeleton for a 3-5 minute public demo. Use public sample code only.

Core wording:

```text
MCP is the connection protocol.
AI Workbench MCP is the tool server.
Acceptance is decided by the selected validation profile and quality gate.
The agent performs. Workbench accepts. MCP connects them.
```

## 1. Install From Source

The PyPI package has not been published yet, so use a checked-out repository:

```bash
python -m pip install -e .
```

The current wheel is code/server only. Full Goose recipe workflows need the checked-out repo because configs, prompts, recipes, examples, evals, and validation profiles are repo assets.

## 2. Register The MCP Server In Goose

Run:

```bash
goose configure
```

Choose:

- `Add Extension`
- `Command-line Extension`
- Name: `AI Workbench MCP`
- Command: `ai-workbench-mcp`
- Timeout: `300`

## 3. Run A Toy Acceptance Task

Use the tiny Python fix recipe:

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

## 4. Inspect Evidence

Show the run folder:

```text
runs/demo-tiny-python-fix/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Explain that Goose executes, MCP connects Goose to the Workbench tool server, and Workbench records evidence before deciding whether the result is accepted.

## 5. Show Validation And Quality Gate

Open:

- `validation_report.json`
- `revision_decision.json`

Call out that acceptance requires deterministic validation and a quality-gate decision. Prompt instructions and Goose prose are not acceptance evidence by themselves.

## 6. Show Accepted And Review-Required Evidence

Use committed sample evidence for repeatable public screenshots:

```text
examples/sample-runs/accepted-tiny-python-fix/
examples/sample-runs/accepted-docs-only-smoke/
examples/sample-runs/needs-review-test-fix/
```

For an accepted sample, open:

- `examples/sample-runs/accepted-tiny-python-fix/validation_report.json`
- `examples/sample-runs/accepted-tiny-python-fix/revision_decision.json`

Point out `overall_status="passed"`, `sign_off_ready=true`, and `final_status="accepted"`.

For the review-required or failed path, open:

- `examples/sample-runs/needs-review-test-fix/validation_report.json`
- `examples/sample-runs/needs-review-test-fix/revision_decision.json`

Point out the failed deterministic validation evidence and the revision-required quality-gate outcome.

## 7. Run Analytics And Dashboard

Use committed sample evidence for a repeatable public demo:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/demo-sample-analytics
```

Show:

- `run_metrics.json`
- `run_summary.md`
- `run_dashboard.html`

## 8. Run Golden-Case Eval Smoke

```bash
python tools/golden_eval.py --cases-dir evals/golden_cases --source-runs-dir examples/sample-runs --out-dir runs/demo-golden-eval
```

Show that accepted sample evidence can become a local regression baseline without provider calls or live Goose execution.

## 9. Close With The Wedge

Use this wording:

```text
AI Workbench MCP turns AI-agent output into accepted, validated, auditable work, starting with Goose. The agent performs. Workbench accepts. MCP connects them.
```
