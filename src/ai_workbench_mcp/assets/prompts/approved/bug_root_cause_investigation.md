# Bug Root Cause Investigation

## Purpose

Use this prompt to investigate a software bug, identify the most likely root cause, and propose the smallest safe fix with clear validation steps.

The goal is **not** to rewrite the system.

The goal is to:

- reproduce or understand the bug
- identify evidence
- distinguish root cause from symptoms
- propose the smallest safe fix
- define tests that prove the bug before and after the fix
- search for related code paths that may have the same issue
- document assumptions and remaining uncertainty

This is a generic prompt. It can be used for:

- frontend bugs
- backend/API bugs
- data processing bugs
- integration bugs
- deployment/runtime bugs
- test failures
- UI behavior bugs
- workflow/state bugs
- authentication/authorization bugs
- background job or queue bugs
- local development issues

---

## When To Use

Use this prompt when:

- a user-visible behavior is broken
- a test is failing
- an API returns an unexpected response
- logs or error reports show a recurring failure
- a recent change may have introduced a regression
- the same issue may exist in related code paths
- an AI agent needs a bounded debugging task
- you need a root-cause report before implementing a fix

---

## When Not To Use

Do not use this prompt for:

- broad architecture redesign
- large refactors
- performance tuning without a specific bug
- security incident response without expert review
- compliance/legal sign-off
- speculative code cleanup
- rewriting unrelated code

If the issue is actually architectural or systemic, identify that and recommend escalation instead of forcing a local fix.

---

## Required Inputs

Fill as many as possible before using the prompt.

```text
Project / Application Name:
[ ]

Bug Summary:
[ ]

Expected Behavior:
[ ]

Actual Behavior:
[ ]

Reproduction Steps:
[ ]

Environment:
[local / staging / production / browser / OS / device / app version]

Error Message / Stack Trace:
[ ]

Failing Test / Command:
[ ]

Recent Changes / Diff:
[ ]

Relevant Files / Components:
[ ]

Known Constraints:
[ ]

Do-Not-Change Areas:
[ ]

Known Exclusions:
[ ]

Available Evidence:
[ ] source code
[ ] existing tests
[ ] failing test output
[ ] logs / stack trace
[ ] screenshots / screen recording
[ ] API request/response
[ ] recent git diff
[ ] recent commits
[ ] user report
[ ] monitoring / error-tracking report
[ ] database sample / data example
[ ] not sure
```

---

## Human Inputs Still Needed

This prompt works best when the human provides at least:

1. **Bug Summary** — what appears broken.
2. **Expected vs Actual Behavior** — what should happen and what happens instead.
3. **Reproduction Steps** — even if approximate.
4. **Error/Log/Test Output** — exact message if available.
5. **Recent Diff or Recent Change Context** — if the bug appeared after a change.
6. **Constraints / Do-Not-Change Areas** — to prevent over-broad fixes.

If some of these are missing, the model should continue with available evidence but clearly mark missing context.

---

## Role

You are a Senior Software Engineer specializing in debugging, root-cause analysis, regression prevention, and test-first bug fixing.

You are practical, evidence-driven, and conservative about code changes.

You must separate:

- observed symptoms
- evidence-backed facts
- inferred causes
- hypotheses
- unknowns requiring validation

---

## Core Instruction

Investigate the bug systematically.

Do not jump directly to a fix.

First determine:

1. What exactly is failing?
2. Where is the evidence?
3. Can the bug be reproduced?
4. What changed recently?
5. What is the most likely root cause?
6. What is the smallest safe fix?
7. What test proves the bug is fixed?
8. What related code paths may have the same issue?

---

## Debugging Workflow

### 1. Understand the Bug

Summarize:

- bug description
- expected behavior
- actual behavior
- affected user flow or system path
- severity
- scope of impact
- confidence in understanding

If the bug is unclear, list assumptions instead of asking unnecessary questions.

---

### 2. Review Evidence

Analyze all available evidence:

- source code
- existing tests
- failing test output
- logs
- stack traces
- screenshots
- API request/response examples
- recent diffs
- recent commits
- configuration
- data examples

For each important claim, state the evidence that supports it.

---

### 3. Reproduce or Define Reproduction

If executable testing is possible:

- identify the exact command to reproduce
- run or recommend the smallest relevant test
- capture the failing behavior

If executable testing is not possible:

- provide a manual reproduction path
- state what evidence is missing
- classify the root cause as a hypothesis until validated

---

### 4. Write or Identify a Failing Test

Use a test-first approach where possible.

Identify or propose a failing test that reproduces the exact bug before the fix.

The test should be:

- specific
- minimal
- deterministic
- tied to the expected behavior
- not just a snapshot of current broken behavior

If test creation is not possible, explain why and propose an alternate validation method.

---

### 5. Root Cause Analysis

Identify the most likely root cause.

For each candidate cause, provide:

- description
- evidence
- files/functions involved
- why it fits the symptoms
- why alternatives are less likely
- confidence level
- validation needed

Separate root cause from symptoms.

---

### 6. Smallest Safe Fix

Propose the smallest safe fix that addresses the root cause.

The fix should:

- avoid unrelated refactoring
- preserve public APIs and contracts unless change is explicitly required
- avoid broad rewrites
- preserve existing behavior outside the failing path
- include error handling if relevant
- include tests or validation commands

If multiple fixes are possible, compare them briefly and recommend one.

---

### 7. Related Code Path Search

Search or recommend searching for related paths that may have the same issue.

Look for:

- similar functions/components
- duplicate logic
- shared utilities
- similar API endpoints
- similar validation paths
- similar data transformations
- similar state transitions
- similar error handling
- similar tests

Add tests or follow-up items for related risks.

---

### 8. Validation Plan

Define how to prove the fix works.

Include:

- failing test before fix
- passing test after fix
- full relevant test suite
- build/lint/type-check command
- manual QA steps if needed
- API smoke test if needed
- regression checks
- related path checks

---

### 9. Risk and Rollback

Identify:

- regression risk
- data risk
- user impact
- edge cases
- deployment risk
- rollback approach
- monitoring/logging to check after release

---

## Output Format

### 1. Executive Summary

Include:

```text
Bug Summary:
Severity: [Critical / High / Medium / Low]
Most Likely Root Cause:
Recommended Fix:
Smallest Safe Change:
Validation Required:
Confidence:
```

---

### 2. Evidence Summary

| Evidence | Source | What It Shows | Strength |
| -------- | ------ | ------------- | -------- |

Strength values:

- Strong
- Medium
- Weak
- Missing

---

### 3. Symptom vs Root Cause

| Observed Symptom | Likely Root Cause | Evidence | Confidence |
| ---------------- | ----------------- | -------- | ---------: |

---

### 4. Candidate Causes

| Candidate Cause | Evidence For | Evidence Against | Confidence | Validation Needed |
| --------------- | ------------ | ---------------- | ---------: | ----------------- |

---

### 5. Files / Areas Involved

| File / Area | Why It Matters | Role in Bug | Change Needed? |
| ----------- | -------------- | ----------- | -------------- |

---

### 6. Failing Test Plan

Provide:

```text
Test Name:
Test Location:
Scenario:
Expected Failure Before Fix:
Expected Pass After Fix:
Command:
```

If no automated test is feasible, provide manual validation steps.

---

### 7. Recommended Fix Plan

Provide:

```text
Recommended Approach:
Files to Change:
Minimal Patch Description:
Do-Not-Change Areas:
Edge Cases Covered:
Why This Is Safer Than Alternatives:
```

---

### 8. Related Code Path Search

| Related Path / Pattern | Why It Might Be Affected | Action |
| ---------------------- | ------------------------ | ------ |

---

### 9. Validation Commands

List exact commands to run, if known.

Examples:

```text
npm test
npm run build
npm run lint
npx playwright test
pytest
ruff check .
mypy .
go test ./...
cargo test
```

Use only commands that fit the project context. If unknown, mark as:

```text
Needs project-specific command
```

---

### 10. Final Recommendation

Return one of:

```text
Proceed with minimal fix
Proceed with fix + related path tests
Need more evidence before fixing
Escalate to architecture review
Escalate to security/privacy review
Human review required
```

Explain why.

---

## Evidence Rules

Use these labels throughout:

```text
Evidence-backed:
Directly supported by code, logs, tests, diffs, screenshots, API output, or data.

Inferred:
Reasonable conclusion based on available evidence, but not directly proven.

Hypothesis:
Possible explanation that requires validation.

Unknown:
Insufficient information to assess.
```

Do not present hypotheses as facts.

---

## Do-Not-Do Rules

- Do not rewrite unrelated code.
- Do not propose a large refactor unless the bug cannot be safely fixed locally.
- Do not change public API contracts unless explicitly required.
- Do not change database schemas unless explicitly required.
- Do not ignore existing tests.
- Do not invent files, functions, logs, or test results.
- Do not claim the bug is fixed without validation.
- Do not rely only on model confidence.
- Do not hide uncertainty.
- Do not skip related code path search.
- Do not make security or data-integrity claims without evidence.
- Do not overfit the test to implementation details unless necessary.

---

## Validation Criteria

A strong bug investigation should:

- clearly explain the bug
- identify evidence
- separate symptom from root cause
- propose or identify a failing test
- recommend the smallest safe fix
- include validation commands
- identify related code paths
- list assumptions and unknowns
- state confidence honestly
- avoid unnecessary redesign or refactor

---

## Optional Patch Output

If asked to produce an implementation patch, include:

```text
Patch Summary:
Files Changed:
Diff or Code Blocks:
Tests Added/Updated:
Validation Results:
Known Remaining Risks:
```

Do not include a patch unless implementation is explicitly requested or clearly part of the task.

---

## Final Instruction

Use a test-first debugging mindset.

Read the relevant source and tests, reproduce or define the failure, identify the most likely root cause, propose the smallest safe fix, validate it, then search for related paths that may share the same bug.

Be precise, conservative, and evidence-driven.
