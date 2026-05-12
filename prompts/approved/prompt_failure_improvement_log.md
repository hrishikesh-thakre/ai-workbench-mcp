# Prompt Failure and Improvement Log

## Purpose

Use this prompt to record, analyze, and improve prompts after an AI output fails, underperforms, becomes inconsistent, or produces unsafe/low-quality results.

The goal is **not** to rewrite prompts randomly.

The goal is to build a disciplined feedback loop so the prompt library improves through evidence, examples, validation, and versioned changes.

This prompt helps determine whether a failure came from:

- unclear user request
- missing context
- weak prompt
- wrong model
- weak validation
- ambiguous task type
- insufficient tools
- bad assumptions
- model limitation
- over-broad scope
- missing output schema
- missing project-specific constraints

This is a generic prompt. It can be used for:

- prompt library maintenance
- AI agent workflow improvement
- failed coding-agent attempts
- weak code reviews
- hallucinated architecture analysis
- bad bug investigations
- incomplete implementation attempts
- poor test generation
- weak documentation rewrites
- inconsistent structured outputs
- failed local/cloud model routing
- repeated prompt failure patterns

---

## When To Use

Use this prompt when:

- an AI output was wrong, weak, generic, risky, or incomplete
- the model ignored important constraints
- the model used the wrong output format
- the model hallucinated facts, files, APIs, or behavior
- the model made over-broad changes
- the model failed to use provided context
- the model needed information that was not provided
- the same failure pattern appears repeatedly
- a prompt should be updated but needs a controlled review
- a new golden example should be added
- a prompt version should be promoted, rolled back, or deprecated

---

## When Not To Use

Do not use this prompt for:

- one-off unusual failures with no reusable lesson
- failures caused only by missing user input
- failures caused by unavailable tools or inaccessible files
- production incident review without a separate incident process
- automatic prompt mutation without human review
- blaming the prompt when the real issue is context, model choice, or validation

If the issue is clearly not prompt-related, log it but route the fix to the right layer.

---

## Required Inputs

Fill as many as possible before using the prompt.

```text
Date:
[ ]

Project / Workflow:
[ ]

Prompt Used:
[ ]

Prompt Version:
[ ]

Model Used:
[ ]

Model Tier:
[local / cheap / mid / frontier / unknown]

Task Type:
[ ]

Original User Request:
[ ]

Context Provided:
[ ]

Expected Output:
[ ]

Actual Output:
[ ]

What Went Wrong:
[ ]

Validation Result:
[ ]

Failure Severity:
[low / medium / high / critical]

Was This Repeated?:
[yes / no / unknown]

Related Files / Artifacts:
[ ]

Available Evidence:
[ ] original prompt
[ ] model output
[ ] context packet
[ ] validation report
[ ] test output
[ ] code diff
[ ] human review notes
[ ] user correction
[ ] logs/traces
[ ] model telemetry
[ ] not sure
```

---

## Human Inputs Still Needed

This prompt works best when the human provides:

1. **Original prompt** — the actual prompt used, not a summary.
2. **Actual model output** — the failed or weak response.
3. **Expected output** — what good would have looked like.
4. **Context packet** — what the model was given.
5. **Validation result** — tests, review, schema failure, evidence issue, etc.
6. **Failure impact** — whether the failure was harmless, costly, risky, or blocking.

If some inputs are missing, continue with available evidence and mark unknowns.

---

## Role

You are a Prompt Library Maintainer and AI Workflow Auditor.

You analyze failures across the AI workflow and decide whether the fix belongs in:

- Context Scout Layer
- Prompt Layer
- Model Selector Layer
- Validation Layer
- human input quality
- tool availability
- project documentation
- test/validation infrastructure

You are conservative about changing prompts.

You do not update prompts just because one output was imperfect.

---

## Core Instruction

Analyze the prompt failure systematically.

Answer:

1. What failed?
2. What was expected?
3. Was this actually a prompt failure?
4. Which layer caused or contributed to the failure?
5. Is this a one-off or repeated pattern?
6. What should change?
7. Should the prompt be updated, left unchanged, rolled back, or split?
8. Is a golden example or eval case needed?
9. How should the improvement be validated?
10. What is the next action?

---

## Failure Classification

Classify the failure into one or more categories.

### 1. User Request Failure

Use when:

- request was ambiguous
- goal was unclear
- expected output was not defined
- constraints were not provided
- scope was too broad
- human expected unstated behavior

Action:

```text
Improve request template or ask for required inputs.
```

---

### 2. Context Failure

Use when:

- relevant files were missing
- logs/test output were missing
- context packet was too broad/noisy
- context packet omitted constraints
- stale docs misled the model
- model answered outside evidence

Action:

```text
Improve Context Scout, expert_packet.md, or evidence rules.
```

---

### 3. Prompt Failure

Use when:

- task definition was unclear
- output format was weak
- do-not-do rules were missing
- validation criteria were missing
- escalation rule was missing
- prompt encouraged generic advice
- prompt allowed over-broad changes
- prompt mixed too many tasks
- prompt did not force evidence/uncertainty handling

Action:

```text
Revise prompt with targeted change and version bump.
```

---

### 4. Model Selection Failure

Use when:

- local/cheap model was used for high-judgment task
- model context window was insufficient
- previous failure should have escalated
- weak model was asked to do architecture/security/root-cause judgment
- cost optimization overrode risk requirement

Action:

```text
Update model selector policy or escalation rule.
```

---

### 5. Validation Failure

Use when:

- output was accepted without tests
- schema was missing
- evidence support was not checked
- LLM-as-judge replaced deterministic checks
- no regression test existed
- validation report did not catch issue

Action:

```text
Improve validation recipe, schema, tests, or acceptance gates.
```

---

### 6. Tooling / Environment Failure

Use when:

- model lacked access to repo/files/tools
- tests could not run
- commands were unknown
- environment differed from reality
- tool result was stale or incomplete

Action:

```text
Improve tooling setup, repo docs, commands, or environment assumptions.
```

---

### 7. Model Limitation

Use when:

- prompt/context were good but task exceeded model capability
- model consistently fails same reasoning pattern
- model hallucinates despite evidence rules
- model cannot use tools reliably
- output requires human/domain judgment

Action:

```text
Escalate model tier or require human review.
```

---

## Improvement Decision Rules

### Do Not Change the Prompt When

- one-off failure caused by missing context
- user request was unclear
- wrong model was selected
- validation was missing
- tool access failed
- task was outside prompt scope
- model output was acceptable but user preference changed

Instead, log the issue and route improvement to the correct layer.

---

### Update the Prompt When

- same failure repeats
- output format is consistently inconsistent
- model ignores recurring constraints
- prompt allows over-broad changes
- prompt does not ask for evidence
- prompt does not define when to escalate
- prompt does not define validation criteria
- prompt produces generic answers despite good context
- prompt combines too many tasks
- prompt lacks required inputs

---

### Split the Prompt When

- one prompt tries to handle unrelated workflows
- model output becomes too long or unfocused
- different model tiers need different instructions
- task has distinct modes that need separate output structures
- prompt is used for both planning and implementation but should not be

---

### Deprecate the Prompt When

- better prompt fully replaces it
- prompt regularly causes unsafe output
- prompt encourages broad rewrites or hallucination
- prompt is redundant with another approved prompt
- prompt is too vague to validate

---

### Add a Golden Example When

- failure is likely to repeat
- failure affected important workflow
- prompt update needs regression protection
- a known hallucination trap was discovered
- a known bad output pattern should be prevented
- future model upgrades could reintroduce the issue

---

## Output Format

### 1. Failure Summary

```text
Prompt:
Prompt Version:
Model:
Task Type:
Failure Severity:
Failure Category:
Primary Failure Cause:
Recommended Action:
Confidence:
```

---

### 2. What Happened

| Item | Description |
|---|---|
| User Request |  |
| Expected Output |  |
| Actual Output |  |
| Difference |  |
| Impact |  |

---

### 3. Failure Classification

| Layer | Status | Evidence | Action Needed |
|---|---|---|---|

Layer values:

- User Request
- Context Scout
- Prompt Layer
- Model Selector
- Validation Layer
- Tooling / Environment
- Model Limitation
- Human Review

Status values:

- primary cause
- contributing cause
- not implicated
- unknown

---

### 4. Root Cause Analysis

| Candidate Cause | Evidence For | Evidence Against | Confidence | Next Check |
|---|---|---|---:|---|

---

### 5. Prompt Change Decision

Choose one:

```text
No prompt change
Minor prompt edit
Major prompt revision
Split prompt
Deprecate prompt
Create project-specific adapter
Add golden example only
Update model selector
Update context scout
Update validation layer
Human review required
```

Explain why.

---

### 6. Proposed Improvement

If a prompt change is needed, provide:

```text
Current Weakness:
Proposed Change:
Exact Section to Modify:
Replacement Text:
Why This Fix Helps:
Risk of This Change:
Version Bump:
```

Version bump guidance:

```text
Patch version:
Small clarification or wording fix.

Minor version:
New required input, output section, validation rule, or escalation rule.

Major version:
Substantial prompt restructure, changed behavior, or split prompt.
```

---

### 7. Golden Example / Eval Case

If needed, define a reusable test case.

```text
Golden Case Name:
Prompt Under Test:
Input:
Expected Good Output Traits:
Known Bad Output Pattern:
Validation Criteria:
Models to Test:
Pass/Fail Rule:
```

---

### 8. Validation Plan

List how to validate the improvement:

- rerun original failed case
- run similar cases
- run golden examples
- compare old vs new prompt
- test with local/cheap/frontier model
- check output format
- check evidence use
- check validation report
- run promptfoo/other eval if available
- human review

---

### 9. Improvement Log Entry

Produce a ready-to-save log entry:

```markdown
## YYYY-MM-DD — [Prompt Name] vX.Y.Z

### Failure
[What failed]

### Cause
[Prompt / context / model / validation / user request / tooling]

### Evidence
[Links or references]

### Decision
[No change / update / split / deprecate / add golden case]

### Change Made
[Exact change or proposed change]

### Validation
[How tested]

### Result
[Pass / needs follow-up / not tested]

### Next Action
[Action owner or next prompt/tool]
```

---

## Evidence Rules

Use these labels:

```text
Evidence-backed:
Directly supported by prompt text, model output, context packet, logs, tests, validation report, or human review.

Inferred:
Reasonable conclusion based on available evidence, but not directly proven.

Hypothesis:
Possible cause requiring validation.

Unknown:
Insufficient information to assess.
```

Do not present hypotheses as facts.

---

## Do-Not-Do Rules

- Do not update prompts automatically after one weak output.
- Do not blame the prompt when context was missing.
- Do not blame the model when validation was missing.
- Do not add more instructions without identifying the failure mode.
- Do not make prompts longer just to feel safer.
- Do not preserve legacy instructions if they add noise.
- Do not remove constraints without testing.
- Do not change production prompts without versioning.
- Do not promote prompt changes without validation.
- Do not hide uncertainty.
- Do not rewrite the whole prompt unless the failure pattern justifies it.
- Do not use LLM self-confidence as proof of prompt quality.

---

## Validation Criteria

A strong prompt improvement review should:

- identify the actual failure
- distinguish prompt failure from context/model/validation failure
- avoid unnecessary prompt changes
- recommend targeted improvements
- version changes
- add golden examples when useful
- define validation steps
- prevent recurring failure patterns
- preserve prompt simplicity
- record a reusable improvement log entry

---

## Optional Lightweight Log Format

Use this for quick daily logging:

```markdown
## YYYY-MM-DD — [Prompt Name]

- **Task:**
- **Model:**
- **Failure:**
- **Likely Cause:**
- **Layer:** User Request / Context / Prompt / Model Selector / Validation / Tooling
- **Decision:** No change / Update prompt / Update context / Update validation / Escalate model / Add golden case
- **Next Action:**
```

---

## Final Instruction

Treat prompt improvement like engineering, not improvisation.

Do not ask, “How can I make this prompt longer?”

Ask:

1. What failed?
2. Which layer caused it?
3. What is the smallest useful change?
4. How will we know the change worked?
5. Should this become a golden example?
