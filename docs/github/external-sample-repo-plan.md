# External Sample Repository Proof

Status: complete

Public repository:

```text
https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate
```

Proof records:

```text
https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/tree/main/proof-records
```

This page records the completed external sample repository proof and preserves
the proof target manifest for future repeats.

## Purpose

Prove that the AI Workbench PR gate can run in a repository outside
`ai-workbench-mcp` and render a deterministic PR-facing decision from Workbench
evidence:

- `accept`
- `needs_review`
- `block`

The proof should exercise the copy-paste GitHub workflow boundary, package
installation boundary, evidence input boundary, and privacy boundary. It should
not depend on this repository's local wrappers, ignored `runs/` ledger, or
private run history.

## Repository Boundary

For true external proof, the sample should live in a separate toy repository,
not under this repository's `examples/` tree.

Why:

- `examples/` proves committed fixture behavior inside this source repository.
- A separate toy repository proves the GitHub workflow can be copied into a
  target project and run through the packaged module entry points.
- It avoids mixing release/docs work in this repository with external proof
  branches and PRs.

The completed proof repository is public and separate from this source
repository.

## Minimal Toy Repository Shape

Use a tiny, boring target project so PR gate behavior is the only interesting
thing being tested:

```text
toy-ai-workbench-pr-gate/
  README.md
  pyproject.toml
  src/
    toycalc/
      __init__.py
      arithmetic.py
  tests/
    test_arithmetic.py
  .github/
    workflows/
      ai-workbench-pr-gate.yml
  workbench-evidence/
    README.md
    accept/
      validation_report.json
      revision_decision.json
      model_output.md
      run_log.jsonl
      task_metadata.json
    needs-review/
      validation_report.json
      revision_decision.json
      model_output.md
      run_log.jsonl
      task_metadata.json
    block/
      validation_report.json
      revision_decision.json
      model_output.md
      run_log.jsonl
      task_metadata.json
```

The Python package can be as small as one arithmetic helper and one focused
test file. The README should explain that the repository is a PR gate proof
target, not an AI Workbench source checkout.

Copy `.github/workflows/ai-workbench-pr-gate.yml` from this repository into the
toy repository. Keep the workflow package selection controlled by the workflow
default or by the `ai_workbench_mcp_package` input; do not hardcode a version in
the toy repo docs beyond what the copied workflow already declares.

## Evidence Strategy

The toy repo must not commit private `runs/` history. Use one of these evidence
paths instead:

1. Preferred live proof: generate a Workbench run locally or in a preparatory CI
   job, keep it under ignored `runs/<run_id>/`, and pass it to the PR gate
   workflow with `workbench_run_dir`, or with `workbench_runs_dir` plus
   `workbench_run_id`.
2. Public fixture proof: commit small, synthetic, sanitized evidence folders
   under `workbench-evidence/` in the toy repository. These fixtures may model
   `accept`, `needs_review`, and `block`, but must be labeled as synthetic
   evidence and not as private run exports.

In both paths, the PR gate decision must come from the same required artifacts:

```text
validation_report.json
revision_decision.json
```

`model_output.md`, `run_log.jsonl`, and `task_metadata.json` may be included
when sanitized, but the workflow comment must not expose raw provider logs,
secrets, private target names, or local absolute paths.

The toy repository should ignore transient evidence:

```text
runs/
.pytest_cache/
__pycache__/
```

Committed evidence should be intentionally small and reviewed. Before committing
any fixture, search it for:

- API keys, tokens, and provider credentials
- local machine paths
- private repository names or issue links
- raw model-loader logs
- unrelated Workbench source-repo paths

## Workflow Inputs

The copied workflow should be driven through the existing inputs:

| Input | External proof use |
|---|---|
| `ai_workbench_mcp_package` | Override only when testing a branch, wheel, or pre-release package. Otherwise use the workflow default. |
| `workbench_run_dir` | Point at one evidence directory, such as `workbench-evidence/accept` or an ignored `runs/<run_id>` folder produced earlier in the job. |
| `workbench_runs_dir` | Parent directory for run folders when using `workbench_run_id`. |
| `workbench_run_id` | Specific run folder name under `workbench_runs_dir`. |
| `workbench_fallback_run_dir` | Optional fallback path. It must remain a blocking missing/scaffold evidence path, not an acceptance shortcut. |

For manual proof, run the workflow four times with the evidence path changed
for each expected outcome and fallback case:

```text
workbench_run_dir=workbench-evidence/accept
workbench_run_dir=workbench-evidence/needs-review
workbench_run_dir=workbench-evidence/block
workbench_run_dir=workbench-evidence/does-not-exist
workbench_fallback_run_dir=workbench-evidence/scaffold-fallback
```

## Branch And Merge Hygiene

Keep external proof work isolated from this repository's release/docs stream:

- Create branches only in the future toy repository for toy-code and proof PRs.
- Do not add the toy project under `examples/` in this repository when the goal
  is external proof.
- Do not edit this repository's release notes, roadmap, README, workflow
  template, or tests as part of the external sample proof.
- Treat changes to the copied workflow in the toy repo as local adaptation only;
  upstream reusable workflow changes should be proposed separately in this
  repository.
- Keep generated `runs/` evidence ignored in both repositories.
- If a proof run discovers a renderer bug, file or patch that bug in this
  repository on a separate branch from toy-repo content changes.

## Acceptance Checklist

The external proof is complete when all of the following are true:

- The sample lives in a separate toy repository, not under
  `ai-workbench-mcp/examples/`.
- The toy repo contains a minimal Python package or script, focused tests, a
  README, and a copied `.github/workflows/ai-workbench-pr-gate.yml`.
- The workflow installs AI Workbench through its workflow default or the
  `ai_workbench_mcp_package` input.
- The workflow renders `accept` from real or synthetic sanitized evidence with
  acceptance-supporting `validation_report.json` and `revision_decision.json`.
- The workflow renders `needs_review` from real or synthetic sanitized evidence
  that requires review without blocker-severity evidence.
- The workflow renders `block` from real or synthetic sanitized evidence with
  missing evidence, failed validation, blocker-severity evidence, revision
  required, or scaffold-only fallback.
- The fallback path never produces `accept`.
- No committed evidence contains secrets, provider credentials, private run
  history, private repository names, raw provider logs, or local absolute paths.
- `runs/` remains ignored and is not committed.
- The package selector is not pinned in prose; use the workflow default or
  `ai_workbench_mcp_package`.
- The proof PR shows the uploaded `workbench-pr-gate` artifact containing
  `pr_comment.md` and `pr_decision.json`.
- Same-repository PRs get at most one marker-based sticky comment; fork PRs
  still render and upload artifacts while skipping comment posting.

## Completion Record

Completed on 2026-05-18 in:

```text
https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate
```

Recorded proof links:

| Proof case | Run |
|---|---|
| Same-repo PR initial run | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039196095` |
| Same-repo PR sticky-comment update run | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039299132` |
| Dispatch accept | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039415176` |
| Dispatch needs review | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039447479` |
| Dispatch block | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039474439` |
| Dispatch scaffold fallback block | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26039499619` |
| Node 24 action update smoke | `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/actions/runs/26043403995` |

The durable artifact copies are committed under:

```text
https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/tree/main/proof-records
```

The same-repository PR proof is:

```text
https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate/pull/1
```

The PR had exactly one `<!-- ai-workbench-pr-gate -->` sticky comment after the
second run, and the comment contained the `Accept` outcome. The trigger-only PR
was closed unmerged after durable proof records were committed, and its branch
was deleted.

## Repeat Notes

For a future repeat, copy this manifest into the toy repo's planning issue or
PR description, then copy the workflow template from this repository. Keep the
first proof PR intentionally small, such as a one-line README or arithmetic
helper change, so any `accept`, `needs_review`, or `block` outcome is
attributable to the supplied Workbench evidence rather than target-project
complexity.
