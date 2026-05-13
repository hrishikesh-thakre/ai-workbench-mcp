# CI Gate Prototype

This repository uses a small GitHub Actions workflow as a repo self-validation gate.

It is a CI gate prototype, not full semantic PR acceptance. It proves the public package and validation scaffold can run in a clean GitHub runner before changes are merged.

## What It Proves

- The package installs with development dependencies.
- The full test suite passes.
- The Workbench scaffold validation profile passes.
- The diff has no whitespace errors reported by `git diff --check`.

## What It Does Not Prove

- It does not run live Goose.
- It does not verify provider setup.
- It does not review PR semantics.
- It does not decide whether arbitrary AI-agent output should be accepted.
- It does not replace deterministic validation and quality-gate evidence for an actual run.

Semantic PR acceptance comes later. That future mode should use Workbench evidence folders, validation profiles, quality-gate decisions, and analytics instead of treating a green CI run as accepted agent work.

## Local Mirror

Before pushing a PR, contributors can run the same checks locally:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/ci_scaffold
git diff --check
```

The generated `runs/ci_scaffold` directory is local evidence and stays ignored.
