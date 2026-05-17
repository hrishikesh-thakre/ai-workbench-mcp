# PR Gate Prototype

This repository uses GitHub Actions as a repo self-validation gate and now renders an artifact-only Workbench PR gate summary. It is still a CI gate prototype: the workflow proves repo hygiene and emits PR-facing artifacts, but it does not post or enforce semantic acceptance yet.

The current PR gate is not a comment bot and does not post to GitHub. It writes deterministic artifacts that can be inspected from the workflow run:

```text
runs/pr_gate/pr_comment.md
runs/pr_gate/pr_decision.json
```

The comment artifact is the proposed PR-facing surface. Posting it back to pull requests is deferred until the artifact renderer and decision schema are credible.

## What It Proves

- The package installs with development dependencies.
- The full test suite passes.
- The Workbench scaffold validation profile passes.
- The diff has no whitespace errors reported by `git diff --check`.
- Workbench can render a PR-facing acceptance summary from a prepared evidence folder.
- The workflow can upload the PR gate Markdown and JSON artifacts without PR write permissions.

## What It Does Not Prove

- It does not run live Goose.
- It does not verify provider setup.
- It does not post a PR comment.
- It does not call the GitHub Checks API.
- It does not treat green CI as semantic acceptance.
- It does not replace deterministic validation and quality-gate evidence for an actual run.

The scaffold validation folder used by CI normally renders `Block` because it has a `validation_report.json` but does not have a full Workbench acceptance lifecycle with `revision_decision.json`. That is intentional. Green CI alone is not accepted agent work.

Semantic PR acceptance comes later through real Workbench evidence folders, validation profiles, quality-gate decisions, and eventually a guarded PR comment posting path.

## Local PR Gate Artifact

Render a local PR gate artifact from any Workbench evidence folder:

```bash
python tools/pr_gate.py \
  --run-dir examples/sample-runs/accepted-tiny-python-fix \
  --out runs/pr_gate/pr_comment.md \
  --json-out runs/pr_gate/pr_decision.json
```

Use `--fail-on-block` only when you want the renderer to become an enforcing command. Without that flag, the command exits successfully after writing a deterministic `accept`, `needs_review`, or `block` artifact.

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
