# PR Gate Prototype

This repository uses GitHub Actions as a repo self-validation gate and now renders a Workbench PR gate summary. It is still a CI gate prototype: the workflow proves repo hygiene, emits PR-facing artifacts, and posts one guarded sticky PR comment for same-repository pull requests, but it does not enforce semantic acceptance yet.

The Markdown artifact remains the source of truth for the PR-facing surface:

```text
runs/pr_gate/pr_comment.md
runs/pr_gate/pr_decision.json
```

For pull requests opened from this repository, CI also posts or updates a single sticky comment marked with:

```text
<!-- ai-workbench-pr-gate -->
```

Fork pull requests still render and upload the artifacts, but skip comment posting because the workflow is intentionally guarded.

## What It Proves

- The package installs with development dependencies.
- The full test suite passes.
- The Workbench scaffold validation profile passes.
- The diff has no whitespace errors reported by `git diff --check`.
- Workbench can render a PR-facing acceptance summary from a prepared evidence folder.
- The workflow can upload the PR gate Markdown and JSON artifacts.
- Same-repository pull requests get a single updated PR gate comment rather than duplicate comments.

## What It Does Not Prove

- It does not run live Goose.
- It does not verify provider setup.
- It does not call the GitHub Checks API.
- It does not post comments for fork pull requests.
- It does not treat green CI as semantic acceptance.
- It does not replace deterministic validation and quality-gate evidence for an actual run.
- It does not embed raw model output, provider logs, or private run contents in the PR comment.

The scaffold validation folder used by CI normally renders `Block` because it has a `validation_report.json` but does not have a full Workbench acceptance lifecycle with `revision_decision.json`. That is intentional. Green CI alone is not accepted agent work.

Semantic PR acceptance comes later through real Workbench evidence folders, validation profiles, quality-gate decisions, and an enforcement policy. The current comment is a GitHub-native visibility layer for the existing artifact renderer.

## Local PR Gate Artifact

Render a local PR gate artifact from any Workbench evidence folder:

```bash
python tools/pr_gate.py \
  --run-dir examples/sample-runs/accepted-tiny-python-fix \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Use `--fail-on-block` only when you want the renderer to become an enforcing command. Without that flag, the command exits successfully after writing a deterministic `accept`, `needs_review`, or `block` artifact.

To mirror the sticky comment behavior locally with the GitHub CLI authenticated:

```bash
python tools/pr_gate_comment.py \
  --repo owner/name \
  --pr-number 123 \
  --comment runs/pr_gate/pr_comment.md \
  --decision runs/pr_gate/pr_decision.json
```

The comment helper uses GraphQL through `gh api graphql`, updates the existing marker comment when present, and creates one only when no marker comment exists.

## Local Mirror

Before pushing a PR, contributors can run the same checks locally:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/ci_scaffold
python tools/pr_gate.py --run-dir runs/ci_scaffold --out runs/pr_gate/pr_comment.md --json-out runs/pr_gate/pr_decision.json
git diff --check
```

The generated `runs/ci_scaffold` and `runs/pr_gate` directories are local artifacts and stay ignored.
