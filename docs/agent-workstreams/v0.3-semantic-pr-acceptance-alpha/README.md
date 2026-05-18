# v0.3 Semantic PR Acceptance Alpha Workstreams

Use these files as independent agent input packets. Each agent file repeats the same common packet and then adds a narrow file-ownership packet. The split is by files owned, not by product priority.

## Parallel Safety Summary

Safe to start in parallel from the same clean base:

| Stream | Can run in parallel with | Reason |
|---|---|---|
| `01-semantic-pr-gate-and-comment.md` | `02-policy-packs-product-assets.md`, `03-github-actions-copy-paste-template.md` | Owns PR gate code and tests. It should consume generic `reason_sources` and `reason_codes`, not edit policy definitions or workflows. |
| `02-policy-packs-product-assets.md` | `01-semantic-pr-gate-and-comment.md`, `03-github-actions-copy-paste-template.md` | Owns policy pack representation, validation loading, and validation tests. It should not edit PR rendering or workflow YAML. |
| `03-github-actions-copy-paste-template.md` | `01-semantic-pr-gate-and-comment.md`, `02-policy-packs-product-assets.md` | Owns a new workflow template and template docs. It must not change PR gate CLI flags; if it needs a new flag, ask Stream 01 to add it. |
| `05-public-narrative-issue-hygiene.md` | Parallel only in audit/draft mode | Public docs such as `README.md` and `docs/ai/*` are shared narrative surfaces. Final edits should wait until code streams land. |

Do not run in parallel:

| Stream | Wait for | Reason |
|---|---|---|
| `04-package-assets-or-bootstrap.md` | Stream 02 | Packaging must know whether policy packs remain embedded in validation profiles or move to first-class asset files. |
| `06-demo-pr-evidence.md` | Streams 01 and 03 | Demo artifacts should use the settled PR decision/comment shape and workflow invocation. |
| `07-contract-finalization-integration.md` | All previous streams | Contract docs are the final integration surface. Running this early will create avoidable merge churn. |

## Recommended Execution Order

1. Create one branch per stream from the same clean base.
2. Run Stream 01, Stream 02, and Stream 03 in parallel.
3. Merge Stream 01 first because it owns the PR decision/comment schema.
4. Merge Stream 02 second because it owns policy pack semantics and validation evidence.
5. Rebase and merge Stream 03 after confirming its template still calls the current PR gate CLI.
6. Run Stream 04 after policy pack asset paths are stable.
7. Run Stream 06 after PR gate artifacts and workflow paths are stable.
8. Run Stream 05 as the public narrative and issue hygiene sweep.
9. Run Stream 07 last to freeze the v0.3 alpha contract baseline and final docs.

## Practical Branch Rule

Use one branch per stream:

```text
codex/v0.3-01-semantic-pr-gate
codex/v0.3-02-policy-packs
codex/v0.3-03-github-actions-template
codex/v0.3-04-package-assets
codex/v0.3-05-public-hygiene
codex/v0.3-06-demo-pr-evidence
codex/v0.3-07-contract-finalization
```

Each branch may edit only the files listed in its ownership packet. If an agent discovers it must change a file owned by another stream, it should stop and write a short handoff note instead of crossing ownership boundaries.

Do not commit local `runs/` evidence. Commit only sanitized examples or docs. Rebase each branch before review, run the stream-specific tests, and run the full suite before merging schema-affecting branches.

## Agent Packets

- [01 Semantic PR gate and comment](01-semantic-pr-gate-and-comment.md)
- [02 Policy packs as product assets](02-policy-packs-product-assets.md)
- [03 GitHub Actions copy-paste template](03-github-actions-copy-paste-template.md)
- [04 Package assets or bootstrap](04-package-assets-or-bootstrap.md)
- [05 Public narrative and issue hygiene](05-public-narrative-issue-hygiene.md)
- [06 Demo PR evidence](06-demo-pr-evidence.md)
- [07 Contract finalization and integration](07-contract-finalization-integration.md)
