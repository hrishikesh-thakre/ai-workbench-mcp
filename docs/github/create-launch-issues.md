# Create Launch Issues

These commands turn the prepared issue drafts into public GitHub issues. Do not run them until the maintainer is ready to open the launch backlog.

Prerequisite:

```bash
gh auth login
```

Create issues:

```bash
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "dogfooding: collect 20-50 Goose acceptance runs" --body-file docs/github/issue-drafts/dogfooding-collect-goose-runs.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "analytics: promote routing feedback candidates into policy experiments" --body-file docs/github/issue-drafts/analytics-routing-feedback-policy-experiments.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "cost evidence: capture provider token and cost metadata" --body-file docs/github/issue-drafts/cost-evidence-provider-metadata.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "policy packs: design first-class validation policy metadata" --body-file docs/github/issue-drafts/policy-packs-validation-metadata.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "ci: prototype PR acceptance gate" --body-file docs/github/issue-drafts/ci-pr-acceptance-gate.md
gh issue create --repo hrishikesh-thakre/ai-workbench-mcp --title "docs: record a five-minute Goose acceptance demo" --body-file docs/github/issue-drafts/docs-five-minute-goose-demo.md
```

The drafts are public-safe and do not include private run history.
