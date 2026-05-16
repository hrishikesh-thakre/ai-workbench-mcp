# v0.2 Public Proof Pack

Status: assembled from sanitized committed sample evidence  
Package version: `0.2.0a0`  
Last reviewed: 2026-05-16

## Purpose

This proof pack shows that AI Workbench MCP can turn AI coding-agent output into evidence-backed run outcomes.

The proof is intentionally narrow:

- Goose is the default execution host.
- Codex local/IDE is represented as the first second-host proof.
- Acceptance is based on deterministic validation and the quality gate.
- Analytics summarize recorded evidence by outcome, execution host, and response source.

Core boundary:

```text
The agent performs. Workbench accepts. MCP connects them.
```

## What This Proves

This proof pack supports these claims:

- AI Workbench MCP exposes a six-tool acceptance lifecycle through one MCP server.
- Workbench records standard evidence artifacts for each run.
- A run can be accepted only when validation passes and the quality gate accepts it.
- The same evidence shape can represent Goose and Codex local/IDE runs.
- Analytics can show accepted and review-required outcomes by host/source.
- The system does not rubber-stamp failed deterministic validation.

## What This Does Not Prove

This proof pack does not claim:

- broad community adoption
- mature routing optimization
- Codex cloud support
- universal correctness verification
- replacement for CI, code review, security review, or human judgment
- reliable model comparison from the current small sample set

Routing feedback remains advisory until enough real dogfood evidence exists.

## Evidence Set

Committed sanitized evidence lives under:

```text
examples/sample-runs/
```

The public proof uses:

| Proof | Evidence folder | Outcome |
|---|---|---|
| Goose accepted run | `examples/sample-runs/accepted-tiny-python-fix/` | accepted |
| Codex local/IDE accepted run | `examples/sample-runs/accepted-codex-tiny-python-fix/` | accepted |
| Review-required run | `examples/sample-runs/needs-review-test-fix/` | revision_required public bucket: review_required |
| Docs-only accepted run | `examples/sample-runs/accepted-docs-only-smoke/` | accepted |

Each sample keeps only sanitized evidence. Raw local run ledgers remain under ignored `runs/` folders.

Recent live proof summary:

| Proof | Raw evidence policy | Outcome |
|---|---|---|
| Fresh Gemini fixture proof | Ignored local `runs/gemini-fixture-proof/` ledger; sanitized summary only | accepted |
| Fresh Codex fixture proof | Ignored local `runs/codex-live-20260516-fixture-proof/` ledger; sanitized summary only | accepted |

See `docs/proof/gemini-fixture-accepted-run.md` and `docs/proof/codex-fixture-accepted-run.md`.

## Standard Evidence Artifacts

The proof runs use the standard Workbench evidence ledger:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

For accepted evidence, the decisive fields are:

```text
validation_report.json: overall_status = passed
validation_report.json: sign_off_ready = true
revision_decision.json: final_status = accepted
```

For review-required evidence, deterministic validation or quality-gate findings explain why acceptance was blocked.

## Proof Run Summaries

### Goose Accepted

See `docs/proof/goose-accepted-run.md`.

The Goose sample proves the default host path can produce accepted evidence. The run fixes the tiny Python calculator example, records captured output, runs a unittest command, and receives an accepted quality-gate decision.

### Gemini Fixture Accepted

See `docs/proof/gemini-fixture-accepted-run.md`.

The fresh live proof used Goose `1.34.1` with the configured `gemini_oauth / gemini-3-flash-preview` default and no provider/model overrides. It ran `workbench-test-fix-acceptance.yaml` with `fixture_repair_proof`, repaired only `examples/tiny-python-fix/calculator.py`, passed the focused unittest and changed-file policy checks, received `final_status=accepted`, and analyzed only the isolated proof parent.

### Codex Local/IDE Accepted

See `docs/proof/codex-local-run.md`.

The Codex sample proves the shared Workbench server can represent a non-Goose host without forking into a Codex-specific server. The evidence records:

```text
execution_host = codex
response_source = codex
```

### Codex Fixture Accepted

See `docs/proof/codex-fixture-accepted-run.md`.

The fresh live proof used Codex local/IDE with the `aiWorkbench` MCP server, recorded `execution_host=codex` and `response_source=codex`, repaired only `examples/tiny-python-fix/calculator.py`, passed the focused unittest and changed-file policy checks under `fixture_repair_proof`, received `final_status=accepted`, and analyzed only the isolated proof parent.

### Review Required

See `docs/proof/goose-review-required-run.md`.

The review-required sample proves Workbench does not claim acceptance when deterministic validation fails. The failed full test suite produces a `revision_required` quality-gate decision.

## Analytics Proof

Run:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/proof-sample-analytics
```

Expected current proof signal:

```text
Runs total: 4
Accepted: 3
Review required: 1
Failed: 0
Accepted by execution host: codex=1, goose=2
Response source counts: codex=1, goose=3
```

See `docs/proof/analytics-proof.md`.

Do not commit `runs/proof-sample-analytics/`. The committed proof documents summarize the output.

## Demo Path

Use `docs/proof/demo-script.md` for a 3-5 minute public walkthrough.

Recommended primary demo mode:

- show committed sanitized sample evidence
- run analytics over `examples/sample-runs`
- show accepted and review-required outcomes
- explain the MCP and Workbench boundary

Live Goose or Codex runs are optional. If a live run is recorded, keep the output under ignored `runs/` and promote only intentionally sanitized examples.

## Install And Registry Proof

PyPI package:

```bash
python -m pip install ai-workbench-mcp==0.2.0a0
```

MCP Registry proof:

- `server.json`
- `docs/publishing/mcp-registry-proof.md`
- `docs/publishing/pypi.md`

The current PyPI wheel installs the server code and console script. Full Goose recipe workflows still require a checked-out repository because recipes, prompts, configs, examples, evals, and validation profiles are repo assets.

## Next Evidence To Collect

The next useful proof is not another architecture pass. Collect:

- additional Codex local/IDE runs across focused workflow types
- additional provider-backed Goose runs across focused recipe types
- additional dogfood runs until there are at least 20 complete evidence folders

Do not mutate routing policy from the current small sample set.
