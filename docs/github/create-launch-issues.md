# Create Launch Issues

The prepared launch issue drafts have already been created as public GitHub issues. Do not rerun the creation commands unless recreating after duplicate checks.

Verified state:

| Issue | Public link | Draft file |
|---|---|---|
| `#1` dogfooding: collect 20-50 Goose acceptance runs | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/1 | `docs/github/issue-drafts/dogfooding-collect-goose-runs.md` |
| `#2` analytics: promote routing feedback candidates into policy experiments | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/2 | `docs/github/issue-drafts/analytics-routing-feedback-policy-experiments.md` |
| `#3` cost evidence: capture provider token and cost metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/3 | `docs/github/issue-drafts/cost-evidence-provider-metadata.md` |
| `#4` policy packs: design first-class validation policy metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/4 | `docs/github/issue-drafts/policy-packs-validation-metadata.md` |
| `#5` ci: prototype PR acceptance gate | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/5 | `docs/github/issue-drafts/ci-pr-acceptance-gate.md` |
| `#6` docs: record a five-minute Goose acceptance demo | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/6 | `docs/github/issue-drafts/docs-five-minute-goose-demo.md` |

Read-only duplicate check:

```bash
gh issue list --repo hrishikesh-thakre/ai-workbench-mcp --state all --limit 50 --json number,title,state
```

## Recovery Reference

The commands below are kept as recovery/reference guidance only. Do not rerun them unless recreating the launch backlog in this or another repository after duplicate checks.

Prerequisite:

```bash
gh auth login
```

Recovery creation commands:

```bash
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "dogfooding: collect 20-50 Goose acceptance runs" --body-file docs/github/issue-drafts/dogfooding-collect-goose-runs.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "analytics: promote routing feedback candidates into policy experiments" --body-file docs/github/issue-drafts/analytics-routing-feedback-policy-experiments.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "cost evidence: capture provider token and cost metadata" --body-file docs/github/issue-drafts/cost-evidence-provider-metadata.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "policy packs: design first-class validation policy metadata" --body-file docs/github/issue-drafts/policy-packs-validation-metadata.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "ci: prototype PR acceptance gate" --body-file docs/github/issue-drafts/ci-pr-acceptance-gate.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "docs: record a five-minute Goose acceptance demo" --body-file docs/github/issue-drafts/docs-five-minute-goose-demo.md
```

The drafts are public-safe and do not include private run history.
