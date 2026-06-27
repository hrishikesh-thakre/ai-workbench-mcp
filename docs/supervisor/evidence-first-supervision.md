# Evidence-First Supervision

The core principle behind AI Workbench is simple: agent output is a proposal,
not proof.

## The Problem

AI agents are increasingly capable, but their outputs are not consistently
trustworthy for serious engineering work. Common failure modes:

- Agent ignores explicit instructions
- Agent analyzes truncated or partial data
- Agent treats a guard pass as proof the conclusion is correct
- Agent uses weak heuristics and claims completeness
- Agent overstates confidence
- Agent says "no files changed" even when files were edited
- Agent produces polished but unsupported sign-off claims

The bottleneck has moved from generation to acceptance.

## The Principle

AI-generated work is accepted only when deterministic evidence supports the
claim. Workbench treats model output as a proposal and uses evidence,
validation, policy, and review state to decide whether a run is `accept`,
`needs_review`, or `block`.

Acceptance depends on:

- Evidence artifacts
- Reproducible commands
- Workspace state
- Validation results
- Risk-tiered policy checks
- Confidence discipline
- Explicit unresolved risks
- Human approval for high-risk work

## Automated Evidence

The preferred implementation path is the supervisor daemon:

- register the project once
- capture workspace state before a supported session when possible
- capture tool events through supported adapters
- capture final workspace state and diff summary
- run conservative validation
- write Workbench acceptance artifacts

This removes the adoption blocker of asking the user to remember manual
before/after commands for every session.

Automated evidence is still truthful evidence, not forced acceptance:

- late capture is marked with `late_snapshot=true`
- transcript reconstruction is marked `FALLBACK_ONLY`
- missing validation blocks code-change acceptance
- failed validation blocks code-change acceptance
- untrusted/unobserved Codex hooks are reported as unverified coverage
- OpenCode and Codex coverage are reported separately

## What This Is Not

This is not proof that the work is absolutely correct. Workbench checks
evidence quality and validation state; it does not prove the implementation is
bug-free or mathematically correct.

## The Tagline

> Don't trust agent output. Accept evidence.
