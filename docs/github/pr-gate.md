# Semantic PR Acceptance Gate

The v0.3 PR gate is a GitHub-facing presentation of Workbench acceptance
evidence. It renders a deterministic PR decision from a Workbench run folder and
reports exactly one outcome:

- `accept`
- `needs_review`
- `block`

It does not accept a PR from green CI alone. It can report `accept` only when the
referenced run has deterministic validation evidence and a quality-gate decision,
especially `validation_report.json` and `revision_decision.json`.

The current machine-readable contract is recorded in the
[v0.3 contract baseline](../contracts/v0.3-contract-baseline.md). The
[v0.2 contract baseline](../contracts/v0.2-contract-baseline.md) remains the
compatibility reference for older committed sample runs.

## What It Decides

The renderer maps Workbench evidence to:

- `accept`: validation passed, `sign_off_ready=true`, and the quality gate
  accepted the run.
- `needs_review`: validation or the quality gate requires review and no
  blocker-severity reason source exists.
- `block`: required evidence is missing or unreadable, validation failed,
  revision is required, blocker-severity evidence exists, the state is unknown,
  or only scaffold fallback evidence exists.

Scaffold-only evidence is visibility evidence, not semantic acceptance evidence.
It always blocks with `pr_gate.acceptance_evidence_missing`.

## Evidence Inputs

Render from one explicit Workbench run:

```bash
python tools/pr_gate.py \
  --run-dir examples/sample-runs/accepted-tiny-python-fix \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Resolve a run by parent folder and run id:

```bash
python tools/pr_gate.py \
  --runs-dir examples/sample-runs \
  --run-id accepted-tiny-python-fix \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Render a blocking fallback when no full acceptance run is available:

```bash
python tools/pr_gate.py \
  --fallback-run-dir runs/ci_scaffold \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Use `--fail-on-block` only when you want the renderer to become an enforcing
command. Without that flag, the command exits successfully after writing a
deterministic artifact.

## Outputs

The renderer writes:

```text
runs/pr_gate/pr_comment.md
runs/pr_gate/pr_decision.json
```

`pr_decision.json` includes the outcome, run id, evidence source, validation
status, quality-gate status, reason, reason codes, required next action, and an
evidence table showing whether these artifacts are present:

```text
validation_report.json
revision_decision.json
model_output.md
run_log.jsonl
```

Only `validation_report.json` and `revision_decision.json` are required to make
the acceptance decision. `model_output.md` and `run_log.jsonl` remain useful
evidence but are not embedded in the PR comment.

## PR Comment Surface

The Markdown comment is designed to answer the merge-facing questions quickly:

```text
# AI Workbench PR Gate: Accept|Needs Review|Block

Decision: Accept|Needs Review|Block
Why: <reason>
Required next action: <required_next_action>
Evidence present: validation_report yes|no, revision_decision yes|no
```

The comment then shows run metadata, validation and quality-gate status, evidence
presence, and reason codes. It does not embed raw model output, provider logs, or
private run contents.

For pull requests opened from the same repository, the comment helper posts or
updates a single sticky comment marked with:

```text
<!-- ai-workbench-pr-gate -->
```

Fork pull requests can still render and upload artifacts, but the template skips
comment posting.

## Sticky Comment Helper

To mirror same-repository sticky comment behavior locally with the GitHub CLI
authenticated:

```bash
python tools/pr_gate_comment.py \
  --repo owner/name \
  --pr-number 123 \
  --comment runs/pr_gate/pr_comment.md \
  --decision runs/pr_gate/pr_decision.json
```

The helper uses GraphQL through `gh api graphql`, updates the existing marker
comment when present, and creates one only when no marker comment exists. The
comment is a presentation surface only; it does not replace the underlying
Workbench evidence artifacts.

## Workflow Template

The reusable copy-paste workflow lives at:

```text
.github/workflows/ai-workbench-pr-gate.yml
```

Read [the workflow template guide](pr-gate-workflow-template.md) before copying
it into a target repository.

The template:

- installs `ai-workbench-mcp==0.2.0a0` by default
- accepts `workbench_run_dir`, or `workbench_runs_dir` plus `workbench_run_id`
- falls back to a blocking missing/scaffold result when no real run directory is
  available
- uploads `pr_comment.md` and `pr_decision.json` as the `workbench-pr-gate`
  artifact
- posts one same-repository marker comment when workflow permissions allow it

The template does not run Goose, create a Workbench run, call the GitHub Checks
API, define merge enforcement policy, or turn CI status into acceptance.

## Local Mirror

Before pushing a PR, contributors can run the visibility checks and fallback
artifact path locally:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/ci_scaffold
python tools/pr_gate.py --fallback-run-dir runs/ci_scaffold --out runs/pr_gate/pr_comment.md --json-out runs/pr_gate/pr_decision.json
git diff --check
```

This is the repository's historical CI gate prototype path. It is still a repo self-validation gate for package and hygiene checks plus fallback artifact rendering, but it blocks when only scaffold evidence is available. Older docs said "Semantic PR acceptance comes later"; in v0.3, semantic PR acceptance is the alpha surface, while this local mirror still does not run live Goose.

The generated `runs/ci_scaffold` and `runs/pr_gate` directories are local
artifacts and stay ignored.

For semantic PR acceptance, point the renderer or workflow template at the
actual Workbench run produced for the PR. Inspect `validation_report.json`,
`revision_decision.json`, and `pr_decision.json` before calling the PR accepted.
