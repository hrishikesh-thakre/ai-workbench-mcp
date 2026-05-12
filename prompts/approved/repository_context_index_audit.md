# Repository Context Index Audit

## Purpose

Use this prompt to create a compact, human-readable, and AI-usable map of a codebase so future AI-assisted development work starts with better context.

The goal is **not** to review, rewrite, or redesign the code.

The goal is to identify:

- how the repository is structured
- where the main entry points are
- which modules are important
- how data or control flows through the system
- which files are likely high-risk or high-impact
- what context future agents should read first

This is a generic prompt. It can be used for:

- web applications
- APIs
- backend services
- frontend applications
- monoliths
- monorepos
- internal tools
- automation projects
- data applications
- libraries / SDKs
- local development projects

---

## When To Use

Use this prompt when:

- starting work on an unfamiliar repository
- preparing a codebase for AI-assisted development
- creating a Context Scout packet
- onboarding a new developer or agent
- debugging is slow because repository structure is unclear
- a project has grown and needs a clean structural map
- future prompts need compact repository context
- an agent needs to understand what to read before proposing changes

---

## When Not To Use

Do not use this prompt for:

- final architecture approval
- security certification
- full dependency audit
- performance optimization
- legal or compliance review
- automatic refactoring
- production release sign-off

This prompt maps the repository. It does not decide major architecture changes by itself.

---

## Required Inputs

Fill these before using the prompt.

```text
Project / Repository Name:
[ ]

Repository Path / Scope:
[ ]

Known Tech Stack:
[ ]

Primary Purpose of the Application:
[ ]

Known Areas of Interest:
[ ]

Known Exclusions:
[ ]

Target Consumer of the Index:
[Developer / AI agent / Reviewer / Future self / Other]

Available Evidence:
[ ] file tree
[ ] source code
[ ] package manifests
[ ] config files
[ ] test files
[ ] documentation
[ ] git history
[ ] logs
[ ] recent diffs
[ ] not sure
```

---

## Role

You are a senior codebase analysis expert.

Your task is to create a compact repository index that helps developers and AI agents understand the codebase quickly.

Be practical, concise, and evidence-driven.

---

## Core Instruction

Create a reusable repository index.

Prioritize:

- orientation
- important entry points
- core modules
- data/control flow
- risk areas
- test and documentation gaps
- future AI context recommendations

Avoid unnecessary depth.

Do not dump the full repository into the answer.

---

## Audit Tasks

### 1. Repository Structure

Map the main folders and explain their purpose.

Classify folders as:

- source code
- tests
- configuration
- documentation
- scripts
- generated output
- assets
- build/deployment
- data
- unknown

For each important folder, explain:

- what it likely contains
- why it matters
- whether future AI agents should usually include or exclude it

---

### 2. Entry Points

Identify important entry points such as:

- web app entry
- API/server bootstrap
- CLI entry
- background jobs
- scheduled tasks
- serverless functions
- admin/tooling entry points
- test entry points

For each entry point, provide:

- file path
- purpose
- what it connects to
- whether it is primary or secondary

---

### 3. Core Modules

Identify the most important modules, services, packages, or components.

For each, provide:

- path
- responsibility
- why it matters
- upstream/downstream dependencies if visible
- likely risk level

---

### 4. Data and Control Flow

Summarize how requests, events, or data move through the system.

Use a simple text flow when possible:

```text
Input → Route/API → Service → Data Layer → Output
```

or:

```text
User Action → UI Component → API Call → Business Logic → Storage → Response
```

If the flow is unclear, say so and list what evidence is missing.

---

### 5. Dependency and Coupling Signals

Identify:

- major internal dependencies
- shared utilities
- cross-cutting modules
- tightly coupled areas
- circular or suspicious dependencies if visible
- large modules that may need attention
- modules that appear to bypass intended boundaries

Do not invent a full dependency graph if code evidence is insufficient.

---

### 6. Change Hotspots

If git history, recent diffs, or commit information is available, identify:

- recently changed files
- frequently changed files
- files likely to be high-risk
- files that combine high churn with high responsibility
- files that may require extra review before future changes

If git history is unavailable, mark this section as:

```text
Needs evidence
```

---

### 7. Test and Documentation Coverage Signals

Identify:

- important modules with visible tests
- important modules without obvious tests
- useful documentation
- stale or missing documentation
- unclear setup instructions
- missing run/test/build commands

---

### 8. Noise and Exclusions

Identify files or folders that should usually be excluded from future AI context packets, such as:

- generated files
- build output
- vendor dependencies
- package manager caches
- large datasets
- binary files
- logs
- coverage output
- environment-specific artifacts
- secrets or credentials

---

### 9. Recommended Context for Future AI Work

List the files or folders future agents should read first for common task types:

- debugging
- feature work
- API changes
- UI changes
- data/model changes
- deployment/config changes
- tests
- documentation
- performance work
- security/privacy review

---

## Output Format

### 1. Executive Summary

Include:

```text
Repository Type:
Main Tech Stack:
Overall Structure Clarity Score: [0-100]
Most Important Entry Points:
Top 5 Critical Files / Modules:
Top 5 Risk Areas:
Recommended Next Actions:
Confidence:
```

---

### 2. Repository Map

| Path | Type | Purpose | Importance | Include in Future AI Context? | Notes |
|---|---|---|---|---|---|

Importance values:

- Critical
- High
- Medium
- Low
- Unknown

---

### 3. Entry Points

| Entry Point | File Path | Primary / Secondary | Purpose | Downstream Flow |
|---|---|---|---|---|

---

### 4. Core Modules

| Module | Path | Responsibility | Dependencies / Consumers | Risk |
|---|---|---|---|---|

Risk values:

- High
- Medium
- Low
- Unknown

---

### 5. Data / Control Flow

Provide a simple flow diagram or bullet sequence.

Example:

```text
User request
  → Route / Controller
  → Service / Business logic
  → Data access / External API
  → Response / UI update
```

---

### 6. Change Hotspots

| File / Area | Evidence | Why It Matters | Risk |
|---|---|---|---|

If no git or change data is available, write:

```text
Change hotspot analysis requires git history or recent diffs.
```

---

### 7. Test and Documentation Gaps

| Area | Gap | Impact | Recommendation |
|---|---|---|---|

---

### 8. Recommended AI Context Set

| Task Type | Files / Folders to Include | Files / Folders to Exclude | Notes |
|---|---|---|---|

Suggested task types:

- bug investigation
- feature implementation
- code review
- architecture review
- performance audit
- security/privacy review
- UI/UX change
- API/data contract change
- test generation
- documentation update

---

### 9. Noise / Exclusion List

| Path / Pattern | Reason to Exclude | Exception |
|---|---|---|

Examples:

```text
node_modules/
dist/
build/
.next/
coverage/
.git/
venv/
__pycache__/
large generated JSON files
binary assets
raw logs
```

---

### 10. Open Questions

List missing information that prevents a complete index.

Group open questions by:

- repository structure
- entry points
- data flow
- dependencies
- tests
- deployment
- documentation
- unknown ownership

---

## Evidence Rules

Use these labels throughout the report:

```text
Evidence-backed:
Directly supported by code, file tree, manifests, docs, logs, tests, diffs, or git history.

Inferred:
Reasonable conclusion based on available evidence, but not directly proven.

Hypothesis:
Possible explanation that needs validation.

Unknown:
Insufficient information to assess.
```

Do not present guesses as facts.

---

## Do-Not-Do Rules

- Do not rewrite code.
- Do not propose large refactors unless clearly asked.
- Do not include secrets, credentials, API keys, or sensitive environment values.
- Do not dump huge files into the index.
- Do not include generated, vendor, or build output unless directly relevant.
- Do not claim full dependency accuracy without parsing imports.
- Do not invent file paths or modules.
- Do not confuse repository mapping with architecture redesign.
- Do not over-index every file if a folder-level summary is enough.
- Do not ignore tests, docs, configuration, or scripts.
- Do not treat stale documentation as truth without noting uncertainty.

---

## Validation Criteria

A useful repository index should:

- identify the major folders and their purpose
- identify key entry points
- identify core modules
- summarize data/control flow
- flag high-risk or high-importance areas
- identify test and documentation gaps
- recommend what future AI agents should read first
- clearly list exclusions and noise folders
- separate evidence-backed findings from hypotheses
- avoid unnecessary detail

---

## Optional V2 Additions

Add these only if needed:

- JSON index output
- import/dependency graph
- git churn metrics
- file ownership analysis
- test coverage mapping
- index freshness score
- token count estimates
- CI-based auto-refresh
- module-level mini-indexes
- machine-readable context manifest

---

## Final Instruction

Create a compact repository index that helps future AI agents and developers orient themselves quickly.

Prioritize signal over completeness.

The best output is not the longest index. The best output is the index that helps the next task start with the right context and the least noise.
