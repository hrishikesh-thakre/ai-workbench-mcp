# performance_latency_hotspot_audit.md

## Purpose

Conduct a rigorous performance audit of an application or service to identify cold-start delays, request-latency hotspots, slow execution paths, expensive I/O, inefficient data access, and other contributors to poor wall-time performance.

The goal is to produce a practical optimization report grounded in measurements, not assumptions.

---

## When To Use

Use this prompt when reviewing an application, service, API, worker, script, batch process, or user-facing workflow where performance problems are suspected or need to be validated.

Common triggers:

- Cold starts feel slow.
- First request after startup is slow.
- p90 / p95 / p99 latency is high.
- Some endpoints or workflows are much slower than expected.
- Build, startup, initialization, or request handling has become heavier over time.
- User-facing flows feel slow under normal usage.
- Profiling data, logs, traces, or benchmark results need interpretation.

---

## When Not To Use

Do not use this prompt as a replacement for actual profiling, tracing, benchmarking, or load testing.

Do not invent latency numbers, p95 values, flame-graph findings, database timings, or root causes unless evidence is provided.

If measurement data is missing, provide a measurement plan first and clearly mark all findings as hypotheses.

---

## Required Inputs

Project / Application Name:
[ ]

Application Type:
[web app / API service / backend worker / batch process / mobile app / desktop app / data pipeline / other]

Primary Performance Concern:
[cold start / request latency / slow page load / slow job / slow query / memory pressure / throughput / unknown]

Target Workflows / Endpoints / Jobs:
[ ]

Environment:
[local / staging / production-like / production / CI]

Runtime / Framework / Language:
[ ]

Deployment Context:
[serverless / container / VM / local process / edge / mobile / desktop / other]

Available Evidence:
[ ] startup logs
[ ] request logs
[ ] trace output
[ ] profiler output
[ ] flame graph
[ ] benchmark results
[ ] load-test results
[ ] database query logs
[ ] application metrics
[ ] code snippets
[ ] configuration files
[ ] no measurements yet

Known Constraints:
[ ]

Explicit Exclusions:
[Anything that should not be considered, such as future-state infrastructure, unavailable services, out-of-scope components, or intentionally deferred optimizations.]

---

## Role

You are a Senior Performance Engineer.

Your task is to analyze the provided evidence, identify the most likely wall-time contributors, separate measured facts from hypotheses, and recommend the smallest practical optimizations that can be validated.

---

## Audit Objectives

Evaluate:

1. Cold-start wall time.
2. First-request latency after startup.
3. Warm request latency.
4. p50 / p90 / p95 / p99 latency where data is available.
5. Slow endpoints, functions, jobs, queries, external calls, or I/O operations.
6. Initialization work that can be deferred, cached, parallelized, removed, or precomputed.
7. Request-path work that can be reduced, moved out of band, batched, indexed, cached, streamed, or made lazy.
8. Whether observed latency is caused by application code, data access, network calls, runtime startup, dependency loading, configuration, external services, or infrastructure.

---

## Measurement Honesty Rule

Do not invent measurements.

If exact timing data is available, cite it in the finding.

If exact timing data is unavailable, write:

- Measurement Status: Not measured
- Evidence Level: Hypothesis
- Required Validation: [specific measurement/profiling step]

Clearly separate:

- Measured facts
- Evidence-backed inferences
- Hypotheses
- Recommendations requiring validation

---

## Methodology

Analyze the current running path from startup to request completion.

Consider:

- process startup
- dependency import/load time
- configuration loading
- database/client initialization
- network/client initialization
- file-system reads
- data loading/parsing
- cache warmup or lazy initialization
- middleware chain
- request parsing
- validation/transformation
- database queries
- external service calls
- serialization/deserialization
- response generation
- logging/telemetry overhead
- background work triggered by request

For each suspected bottleneck, explain whether it affects:

- cold start only
- first request only
- every request
- specific endpoint/workflow only
- high-percentile tail latency
- memory pressure or CPU pressure indirectly

---

## Output Format

### 1. Executive Summary

Provide:

- Overall Performance Health: [Good / Acceptable / Needs Improvement / Risky / Poor]
- Main Bottleneck Category: [startup / data access / external call / CPU / I/O / serialization / framework overhead / unknown]
- Top 3 Optimization Opportunities
- Highest-Impact Measurement Gap
- Recommended Next Action

---

### 2. Evidence Summary

List the evidence provided:

| Evidence Type | Provided? | Notes |
|---|---:|---|
| Startup timing | Yes/No | |
| Request latency percentiles | Yes/No | |
| Endpoint-level timings | Yes/No | |
| Traces/profiles | Yes/No | |
| Query timings | Yes/No | |
| External call timings | Yes/No | |
| Logs | Yes/No | |
| Code/config snippets | Yes/No | |

---

### 3. Performance Metrics Summary

If available, report:

| Metric | Value | Source | Confidence |
|---|---:|---|---:|
| Cold start wall time | | | |
| First request latency | | | |
| Warm p50 | | | |
| Warm p90 | | | |
| Warm p95 | | | |
| Warm p99 | | | |
| Slowest endpoint/job | | | |

If metrics are not available, mark them as `Not measured` and provide a measurement plan.

---

### 4. Hotspot Findings Table

| Priority | Area | Hotspot | Evidence | Estimated Impact | Confidence | Recommendation |
|---|---|---|---|---|---:|---|

Priority definitions:

- P0: Large latency contributor on critical path or high-user-impact path.
- P1: Meaningful contributor with clear optimization path.
- P2: Smaller improvement or requires more measurement.
- P3: Nice-to-have cleanup or future investigation.

---

### 5. Detailed Hotspot Analysis

For each hotspot provide:

- Hotspot Name:
- Location:
- Affected Flow / Endpoint / Job:
- Cold Start / Warm Path / Tail Latency Impact:
- Evidence Source:
- Evidence Level: Measured / Inferred / Hypothesis
- Current Behavior:
- Why It Is Slow:
- Estimated Impact:
- Root Cause:
- Recommended Fix:
- Alternative Fixes:
- Risk / Tradeoff:
- Effort: Low / Medium / High
- Confidence: 0.0 to 1.0
- Validation Step:

---

### 6. Root Cause Summary

Group findings into root-cause categories:

- unnecessary startup work
- repeated request-path work
- blocking I/O
- expensive database access
- inefficient data loading/parsing
- external service latency
- serialization overhead
- excessive logging/telemetry
- poor concurrency or batching
- missing indexes or inefficient queries
- oversized dependencies or imports
- memory pressure / garbage collection
- unknown / needs measurement

---

### 7. Recommendations

Provide actionable recommendations in this format:

| Recommendation | Target | Expected Impact | Effort | Risk | Validation |
|---|---|---:|---|---|---|

Prefer recommendations that are:

- measurable
- low-risk
- close to the current architecture
- focused on the current running path
- reversible
- validated by profiling or tests

Avoid vague recommendations such as “optimize the code” or “add caching” unless the exact target and validation method are specified.

---

### 8. Follow-Up Validation Plan

Provide a concrete validation plan:

1. Baseline measurement command or method.
2. Change to apply.
3. Re-measurement method.
4. Success threshold.
5. Regression checks.
6. Rollback criteria.

Example format:

| Step | Action | Output | Success Criteria |
|---|---|---|---|
| 1 | Capture baseline | baseline report | p95 and cold start recorded |
| 2 | Apply fix | code/config change | no functional regression |
| 3 | Re-test | comparison report | p95 improves by target amount |
| 4 | Validate | tests/build/smoke | all pass |

---

## Do-Not-Do Rules

- Do not invent measurements.
- Do not claim a root cause without evidence.
- Do not recommend future-state infrastructure unless explicitly allowed.
- Do not assume a specific database, queue, cache, framework, cloud provider, or deployment platform unless stated in the inputs.
- Do not optimize non-critical paths before identifying the current running path.
- Do not propose broad rewrites before low-risk measurement-backed fixes.
- Do not ignore p95/p99 tail latency.
- Do not ignore cold start if it is part of the stated concern.
- Do not conflate throughput, latency, cold start, and user-perceived performance.

---

## Escalation Rule

Recommend deeper profiling or expert review when:

- evidence is insufficient
- results conflict across sources
- the bottleneck crosses multiple services or systems
- the change affects architecture or deployment topology
- the suspected fix has high regression risk
- performance is safety-critical, financial-impacting, or user-trust-critical

---

## Final Instruction

Focus on wall-time reduction that can be proven. A good performance audit should make the next optimization obvious, measurable, and reversible.
