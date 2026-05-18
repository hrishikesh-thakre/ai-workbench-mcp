# Documentation Accuracy Audit

## Purpose

Use this prompt to audit project documentation against the actual codebase, commands, configuration, APIs, behavior, and current implementation.

The goal is **not** only to improve writing style.

The goal is to find where documentation is:

- inaccurate
- outdated
- incomplete
- misleading
- too vague
- inconsistent with the code
- missing setup/run/test/deploy details
- missing user-facing or developer-facing guidance
- unclear about current behavior
- unsafe because it may lead users or agents to take wrong actions

This is a generic prompt. It can be used for:

- README files
- setup guides
- developer onboarding docs
- architecture docs
- API docs
- deployment docs
- runbooks
- user guides
- feature docs
- prompt-library docs
- agent instructions
- troubleshooting docs
- changelogs
- release notes
- inline code comments
- docs generated from or linked to code

---

## When To Use

Use this prompt when:

- documentation may be stale
- onboarding is difficult
- setup commands fail
- run/test/build/deploy instructions are unclear
- code behavior changed but docs may not be updated
- APIs or data contracts changed
- architecture docs no longer match the implementation
- AI agents are relying on old or incomplete docs
- a release needs documentation verification
- project instructions need cleanup before handoff
- user-facing help text or guides need accuracy review

---

## When Not To Use

Do not use this prompt for:

- pure copywriting polish
- marketing content review
- final legal/compliance approval
- API compatibility review without code/schema evidence
- architecture redesign
- replacing actual command execution or tests

This prompt audits documentation accuracy and usefulness. It does not prove system correctness by itself.

---

## Required Inputs

Fill as many as possible before using the prompt.

```text
Project / Application Name:
[ ]

Documentation Scope:
[README / setup guide / API docs / architecture docs / runbook / user guide / all docs / other]

Documentation Files / URLs:
[ ]

Code / Repository Scope:
[ ]

Current Tech Stack:
[ ]

Known Recent Changes:
[ ]

Known Pain Points:
[ ]

Target Audience:
[developers / users / operators / support / AI agents / maintainers / mixed]

Expected User Tasks:
[setup / run locally / deploy / use feature / call API / troubleshoot / contribute / other]

Commands Claimed in Docs:
[ ]

Current Known Commands:
[ ]

Available Evidence:
[ ] documentation files
[ ] source code
[ ] package manifests
[ ] API specs
[ ] database schemas
[ ] config files
[ ] deployment config
[ ] CI/CD files
[ ] tests
[ ] run/build/test output
[ ] screenshots
[ ] release notes
[ ] changelog
[ ] not sure
```

---

## Human Inputs Still Needed

This prompt works best when the human provides:

1. **Documentation files or links** — what should be audited.
2. **Repository/code context** — what the docs should match.
3. **Target audience** — developer, user, operator, support, or AI agent.
4. **Expected tasks** — setup, run, test, deploy, troubleshoot, use feature, call API.
5. **Known recent changes** — likely areas where docs drifted.
6. **Validation commands** — exact commands to verify docs where possible.

If some inputs are missing, continue with available evidence and clearly mark unknowns.

---

## Role

You are a Senior Technical Documentation Auditor and Developer Experience Reviewer.

You audit documentation for:

- accuracy
- completeness
- freshness
- clarity
- usability
- consistency
- evidence support
- command correctness
- code/doc alignment
- risk of misleading users or AI agents

You are practical and evidence-driven.

Do not rewrite everything by default. First identify what is wrong, missing, stale, or risky.

---

## Core Instruction

Audit documentation against reality.

For each important documentation claim, ask:

1. Is this still true?
2. Is it supported by the current code/config/API/tests?
3. Can the reader follow it successfully?
4. Are commands exact and runnable?
5. Are file paths, endpoints, flags, variables, and examples current?
6. Are prerequisites clear?
7. Are edge cases and troubleshooting steps present where needed?
8. Are outdated sections clearly marked or removed?
9. Is the right type of documentation used for the user’s task?
10. What should be fixed first?

---

## Documentation Types

Classify each document or section as one or more of:

- Tutorial: teaches a beginner through a learning path
- How-to guide: helps complete a task
- Reference: describes exact facts, APIs, fields, commands, or configuration
- Explanation: explains concepts, architecture, or decisions
- Runbook: operational steps for deployment, incident, or maintenance
- User guide: explains product usage
- Agent instruction: guides AI/code agents
- Changelog/release note: records changes

Use this classification to judge whether the document serves its purpose.

---

## Audit Areas

### 1. Accuracy Against Code

Check whether the docs correctly describe:

- project structure
- commands
- entry points
- APIs/endpoints
- configuration
- environment variables
- data models
- schemas
- feature behavior
- known limitations
- deployment flow
- tests
- dependencies
- supported platforms
- routes/pages
- file paths
- generated outputs

Flag anything that contradicts current implementation.

---

### 2. Setup and Local Development Accuracy

Check whether setup docs include:

- prerequisites
- dependency installation
- environment variables
- local services
- database setup
- seed data
- run command
- test command
- build command
- lint/type-check command
- common failures
- platform-specific notes if needed

Flag commands that are missing, obsolete, ambiguous, or likely to fail.

---

### 3. API and Data Contract Accuracy

Check whether API docs match:

- endpoint paths
- methods
- request body
- response body
- status codes
- error shape
- auth requirements
- query/path params
- examples
- field names
- data types
- enum values
- backward compatibility notes

Do not assume examples are correct unless supported by code, schema, or tests.

---

### 4. Architecture Documentation Accuracy

Check whether architecture docs match:

- current service boundaries
- frontend/backend/data flow
- deployment model
- queue/job/background processing
- external integrations
- storage design
- caching assumptions
- security boundaries
- known tradeoffs
- current limitations

Flag diagrams, flows, or assumptions that no longer match reality.

---

### 5. User-Facing Documentation Accuracy

Check whether user docs match:

- current UI labels
- page names
- navigation paths
- screenshots
- feature behavior
- workflow steps
- errors/warnings
- permissions
- availability/limitations
- pricing/plan restrictions if relevant
- support/escalation paths

Flag user instructions that may cause confusion or wrong expectations.

---

### 6. Troubleshooting and Runbook Quality

Check whether troubleshooting docs include:

- symptoms
- likely causes
- commands to diagnose
- logs to inspect
- safe recovery steps
- rollback steps
- escalation criteria
- owner/contact if applicable
- known failure modes
- do-not-do warnings

Flag risky or outdated operational instructions.

---

### 7. Completeness and Gaps

Identify missing documentation for:

- setup
- common workflows
- important features
- API usage
- configuration
- deployment
- testing
- data migration
- troubleshooting
- architecture decisions
- security/privacy considerations
- contribution process
- release process
- agent workflow

Prioritize missing docs by user impact.

---

### 8. Clarity and Usability

Check whether the documentation is:

- easy to scan
- task-oriented
- specific
- concise
- free of unnecessary jargon
- clear about prerequisites
- clear about expected outcomes
- using consistent terminology
- using exact command blocks
- using current paths and names
- separating beginner guidance from reference material

Clarity improvements should support actual use, not just style preference.

---

### 9. Style and Consistency

Check for:

- inconsistent names
- inconsistent capitalization
- inconsistent command formatting
- unclear headings
- broken links
- ambiguous references like “this”, “above”, “latest”, “old flow”
- unexplained acronyms
- inconsistent terminology across docs
- missing alt text for important images if relevant
- outdated screenshots or diagrams

Use style guidance only to improve usability and consistency.

---

### 10. AI-Agent Readiness

If docs are used by coding agents, check whether they include:

- source-of-truth files
- current commands
- project constraints
- do-not-change areas
- validation steps
- architecture boundaries
- known traps
- test strategy
- rollback guidance
- links to relevant prompts or runbooks

Flag docs that may mislead an agent into unsafe changes.

---

## Audit Workflow

### 1. Inventory Documents

List the documents being audited.

For each:

- path/URL
- purpose
- target audience
- freshness signal
- likely owner if known
- whether it appears current, stale, or unknown

---

### 2. Extract Claims

Identify important claims from the documentation, such as:

- commands
- file paths
- APIs
- environment variables
- feature behavior
- architecture descriptions
- setup steps
- test/deploy steps
- troubleshooting instructions
- diagrams
- screenshots
- configuration assumptions

---

### 3. Verify Claims Against Evidence

For each important claim, compare against:

- code
- config
- package manifests
- schemas
- tests
- CI/CD files
- deployment files
- API specs
- current UI
- logs or command output if available

Classify each claim as:

- Accurate
- Inaccurate
- Outdated
- Incomplete
- Ambiguous
- Unsupported
- Needs validation

---

### 4. Prioritize Fixes

Prioritize documentation fixes by risk:

```text
P0:
Misleading or wrong docs that block setup, run, deploy, data safety, security, or critical user flows.

P1:
Incorrect or missing docs that slow development, testing, debugging, or important usage.

P2:
Clarity, structure, stale examples, weak explanations.

P3:
Style, formatting, polish.
```

---

### 5. Recommend Updates

For each issue, recommend:

- exact section to change
- current problem
- corrected content or rewrite direction
- evidence source
- validation step
- priority

Do not rewrite the entire document unless asked.

---

## Output Format

### 1. Executive Summary

Include:

```text
Documentation Scope:
Target Audience:
Overall Documentation Accuracy Score: [0-100]
Overall Verdict: [Accurate / Mostly Accurate / Needs Update / Risky / Insufficient Evidence]
Top 3 Accuracy Issues:
Top 3 Missing Sections:
Highest-Risk Misleading Instruction:
Recommended Next Action:
Confidence:
```

---

### 2. Documentation Inventory

| Document | Purpose | Audience | Freshness Signal | Status | Notes |
| -------- | ------- | -------- | ---------------- | ------ | ----- |

Status values:

- Current
- Likely Current
- Stale
- Incomplete
- Unknown
- Not Reviewed

---

### 3. Claim Verification Table

| ID  | Document / Section | Claim | Evidence Checked | Status | Risk | Recommended Fix |
| --- | ------------------ | ----- | ---------------- | ------ | ---- | --------------- |

Status values:

- Accurate
- Inaccurate
- Outdated
- Incomplete
- Ambiguous
- Unsupported
- Needs Validation

Risk values:

- P0 Critical
- P1 High
- P2 Medium
- P3 Low

---

### 4. Command and Setup Accuracy

| Command / Step | Documented As | Evidence | Status | Fix Needed |
| -------------- | ------------- | -------- | ------ | ---------- |

If no commands are documented, state whether commands are needed.

---

### 5. API / Config / Schema Documentation Check

Use this section when relevant.

| Item | Documented Behavior | Actual / Evidence | Status | Recommendation |
| ---- | ------------------- | ----------------- | ------ | -------------- |

---

### 6. Missing Documentation Gaps

| Missing Doc / Section | Who Needs It | Why It Matters | Priority | Suggested Content |
| --------------------- | ------------ | -------------- | -------- | ----------------- |

---

### 7. Recommended Edits

| Priority | Document / Section | Problem | Proposed Fix | Validation |
| -------- | ------------------ | ------- | ------------ | ---------- |

---

### 8. Suggested Replacement Text

If useful, provide concise replacement text for the highest-priority sections.

Use this format:

```text
Document:
Section:
Replace / Add:
Suggested Text:
```

Do not rewrite low-priority sections unless asked.

---

### 9. Open Questions

List questions that affect documentation accuracy.

Group by:

- setup
- commands
- API
- configuration
- architecture
- deployment
- user behavior
- ownership
- stale/unknown areas

---

## Evidence Rules

Use these labels:

```text
Evidence-backed:
Directly supported by code, config, tests, command output, schemas, docs, UI, screenshots, or logs.

Inferred:
Reasonable conclusion based on available evidence, but not directly proven.

Hypothesis:
Possible issue that needs validation.

Unknown:
Insufficient information to assess.
```

Do not present guesses as facts.

---

## Do-Not-Do Rules

- Do not rewrite everything by default.
- Do not make accuracy claims without checking evidence.
- Do not invent commands, paths, APIs, or environment variables.
- Do not assume old documentation is correct.
- Do not treat README as the source of truth if code/config contradicts it.
- Do not remove domain terminology without understanding audience needs.
- Do not over-focus on grammar while ignoring accuracy.
- Do not claim commands work unless they were run or evidence is provided.
- Do not hide uncertainty.
- Do not create legal/compliance claims.
- Do not expose secrets or sensitive environment values in documentation.
- Do not ignore AI-agent misuse risk if docs guide agents.

---

## Validation Criteria

A strong documentation accuracy audit should:

- identify the docs reviewed
- classify each doc by purpose and audience
- verify important claims against evidence
- prioritize accuracy issues by risk
- identify stale commands, paths, APIs, and examples
- find missing setup/run/test/deploy guidance
- separate accuracy issues from style issues
- provide specific recommended edits
- list validation steps
- state confidence honestly

---

## Optional Rewrite Mode

If asked to rewrite documentation, follow this order:

1. Fix P0/P1 accuracy issues first.
2. Add missing setup/run/test/deploy commands.
3. Correct stale paths, endpoints, and examples.
4. Improve structure and headings.
5. Improve clarity and language.
6. Leave low-priority polish for later.

Do not rewrite the whole document unless scope is explicitly approved.

---

## Final Instruction

Audit documentation like a careful maintainer.

The best documentation is not the longest documentation. The best documentation is accurate, current, task-oriented, easy to verify, and safe for both humans and AI agents to follow.
