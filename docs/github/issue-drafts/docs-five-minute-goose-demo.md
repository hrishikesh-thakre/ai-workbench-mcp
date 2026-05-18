# Goal

Record a short public demo that shows Goose executing work while Workbench records evidence, validates, gates, and analyzes the run.

# Background

The demo should make the acceptance-gate value obvious without requiring private code, private credentials, or broad product setup.

The written public path exists in `docs/walkthroughs/goose-acceptance-demo.md`, and proof material under `docs/proof/` covers accepted evidence, review-required evidence, and v0.3 PR gate outcomes. If the public issue requires a video, the remaining work should be limited to recording and linking that artifact.

# Acceptance Criteria

- The demo uses public sample code or a sanitized toy task.
- It shows the six-tool acceptance lifecycle.
- It inspects the evidence folder.
- It ends by running analytics over sample or dogfood evidence.
- It references the written walkthrough.
- It does not publish raw local `runs/` evidence, provider secrets, private target-repo paths, or raw provider logs.

# References

- `docs/walkthroughs/goose-acceptance-demo.md`
- `docs/proof/proof-pack-v0.2.md`
- `docs/proof/pr-gate-outcome-demos.md`
