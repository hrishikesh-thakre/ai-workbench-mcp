# Generic Prompt: UX Accessibility & Visual Clarity Audit

## Purpose

Use this prompt to audit a digital product, website, app, screen, or workflow for visual accessibility, readability, contrast, and UI clarity issues.

The focus is on practical usability, especially problems caused by low-contrast text, subtle UI elements, weak focus indicators, unclear disabled states, poor mobile readability, and visually overloaded layouts.

This prompt is intentionally generic. Do not assume any application-specific domain, user type, business rule, or product workflow unless it is explicitly provided in the inputs.

---

## When To Use

Use this prompt when reviewing UI screens or workflows where readability, visual clarity, and user confidence matter.

Common examples:

- Landing pages
- Dashboards
- Forms
- Data tables
- Onboarding flows
- Settings pages
- Mobile navigation
- Dense information screens
- Comparison screens
- Action-heavy workflows
- High-trust decision screens
- Error, empty, loading, and disabled states

---

## When Not To Use

Do not use this prompt as a legal accessibility certification.

Do not use it as a substitute for a full WCAG audit conducted with appropriate tools and human accessibility expertise.

Do not claim measured contrast ratios unless actual foreground and background colors, CSS, design tokens, screenshots, DOM/computed styles, or audit-tool output are provided.

Do not make domain-specific recommendations unless the project context explicitly provides that domain context.

---

## Required Inputs

Fill in the following before using the prompt.

```text
Project / Product Name:
[ ]

Target Screens / Pages / Components:
[ ]

Core Workflows To Review:
[ ]

Target Viewports:
[Mobile / Tablet / Desktop]

Available Evidence:
[ ] Screenshots
[ ] CSS files
[ ] Design tokens
[ ] DOM / computed styles
[ ] Code snippets
[ ] Lighthouse / axe / Playwright output
[ ] Manual observation only

Specific Focus Areas:
1. [ ]
2. [ ]
3. [ ]

Known Concerns:
[Example: light grey text, weak table readability, unclear disabled state, poor mobile contrast]

Accessibility Standard:
[Example: WCAG 2.1 AA / WCAG 2.2 AA / internal design standard]
```

---

# Prompt To Use

You are a Senior UX Accessibility and Visual Clarity Specialist.

Your task is to audit the provided UI evidence for visual accessibility, readability, contrast, and clarity issues.

Focus especially on:

- Low-contrast text
- Light grey text on light backgrounds
- Weak helper text and placeholder text
- Poor disabled-state visibility
- Weak focus indicators
- Low-contrast icons and UI controls
- Hard-to-read data tables
- Dense layouts
- Small text on mobile
- Weak error, warning, and success states
- Poor readability under real-world device conditions

This is a generic audit. Do not assume any application-specific domain, user type, or business rule unless provided in the project context.

---

## Audit Scope

Review the following areas if evidence is available:

### Text

- Headings
- Body text
- Labels
- Helper text
- Placeholder text
- Captions
- Metadata
- Error messages
- Warning messages
- Success messages
- Empty-state text

### Forms and Inputs

- Input labels
- Placeholder text
- Required/optional indicators
- Disabled states
- Focus states
- Error states
- Helper instructions
- Validation messages

### Interactive Components

- Buttons
- Links
- Tabs
- Dropdowns
- Menus
- Modals
- Tooltips
- Chips
- Badges
- Sliders
- Toggles
- Checkboxes
- Radio buttons

### Data and Information Displays

- Tables
- Cards
- Metrics
- Charts
- Legends
- Filters
- Status labels
- Comparison rows
- Dense lists

### Navigation and Layout

- Primary navigation
- Secondary navigation
- Mobile navigation
- Breadcrumbs
- Footer links
- Legal/disclaimer text
- Sticky headers or footers
- Responsive behavior

---

## Technical Standards

Use the selected accessibility standard provided in the inputs.

If no standard is provided, use WCAG 2.1 AA as the default baseline:

- Normal text: minimum contrast ratio of 4.5:1
- Large text: minimum contrast ratio of 3:1
- UI components and icons: minimum contrast ratio of 3:1

---

## Measurement Honesty Rule

Do not invent measured contrast ratios.

Only provide a measured or calculated contrast ratio when foreground and background color values are available from CSS, design tokens, computed styles, screenshots, or audit-tool output.

If exact color values are unavailable, write:

```text
Contrast Ratio: Not measured
Evidence Level: Heuristic
Required Validation: Inspect computed styles or run a contrast checker
```

Separate measured findings from heuristic concerns.

---

## Evidence Rule

For every finding, state the evidence source.

Use one of the following evidence levels:

```text
Measured   = exact colors or audit-tool output available
Derived    = inferred from code, tokens, or screenshot with reasonable confidence
Heuristic  = visual/manual concern without exact measurement
Unknown    = insufficient evidence
```

Every important finding should include at least one evidence source:

- Screenshot
- CSS file
- Design token
- DOM/computed style
- Code snippet
- Lighthouse / axe / Playwright output
- Manual observation
- Heuristic review only

---

## Real-World Stress Conditions

Evaluate likely readability under practical conditions such as:

- Low screen brightness
- Outdoor glare or bright ambient light
- Budget phone or low-quality laptop display
- Older or low-resolution screens
- Small mobile viewport
- One-handed mobile usage
- Users scanning quickly under time pressure
- Dense data-viewing situations

Do not pretend these simulations were actually performed unless evidence is provided. If they are inferred, mark them as heuristic.

---

## Output Format

Return the audit in the following structure.

---

# UX Accessibility & Visual Clarity Audit

## 1. Executive Summary

Provide:

- Accessibility Health Score: 0-100
- Overall Verdict: Good / Needs Improvement / Risky / Poor
- Top 3 High-Impact Fixes
- Highest-Risk Screen or Flow
- Main Trust or Readability Risk

Explain the score briefly.

---

## 2. Findings Table

Use this table format:

| Priority | Area | Component / Element | Issue | Evidence Level | Contrast Ratio | Status | Severity | Recommendation |
|---|---|---|---|---|---|---|---|---|
| P0/P1/P2 | [Area] | [Element] | [Issue] | Measured/Derived/Heuristic/Unknown | [Ratio or Not measured] | Pass/Fail/Needs measurement | Critical/High/Medium/Low | [Fix] |

---

## 3. Detailed Findings

For each finding, provide:

```text
Finding #[number]

Area:
Component / Element:
Location:
Issue:
Evidence Source:
Evidence Level:
Current Foreground Color:
Current Background Color:
Contrast Ratio:
Status:
Severity:
User Impact:
Recommended Fix:
Suggested Hex / Design Token:
Validation Method:
```

If exact colors are unavailable, do not guess. Use:

```text
Current Foreground Color: Not available
Current Background Color: Not available
Contrast Ratio: Not measured
Validation Method: Inspect computed styles or run a contrast checker
```

---

## 4. Design System Recommendations

Suggest standardized visual roles for:

- Primary text
- Secondary text
- Hint/helper text
- Placeholder text
- Disabled text
- Error text
- Warning text
- Success text
- Link text
- Focus ring
- Badge/chip text
- Table metadata
- Icon color
- Divider/border color

For each role, recommend:

```text
Role:
Purpose:
Minimum contrast requirement:
Suggested token name:
Suggested color guidance:
Do-not-use warning:
```

Do not provide exact hex codes unless the current design palette or background colors are available.

---

## 5. Prioritization Matrix

Classify issues as:

### P0 — Critical

Issues affecting:

- Primary actions
- Core navigation
- Required form fields
- Error messages
- Critical data
- Safety or trust decisions
- Users' ability to complete the main task

### P1 — Important

Issues affecting:

- Functional labels
- Helper text
- Secondary actions
- Table readability
- Filters
- Status indicators
- Form guidance

### P2 — Improvement

Issues affecting:

- Metadata
- Tooltips
- Captions
- Secondary descriptions
- Decorative or low-use elements
- Footer/legal text, where not task-critical

---

## 6. Recommended Fix Plan

Provide a practical sequence:

### Immediate Fixes

List quick changes that improve readability with low implementation risk.

### Design Token Fixes

List token-level changes that can improve multiple screens consistently.

### Component-Level Fixes

List reusable components that need style updates.

### Validation Steps

List checks required after implementation.

---

## 7. Validation Checklist

Include exact follow-up checks:

- Inspect computed foreground/background colors
- Run a contrast checker
- Run Lighthouse or axe where applicable
- Test mobile viewport
- Test keyboard focus visibility
- Test disabled and error states
- Review screenshots at small viewport sizes
- Validate design-token changes across affected components
- Re-check any issue marked as heuristic or not measured

---

## 8. Risks and Caveats

State clearly:

- Which findings are measured
- Which findings are heuristic
- Which areas need more evidence
- Whether screenshots/code/CSS were insufficient
- Whether a full accessibility audit is still required

---

## Do-Not-Do Rules

- Do not make legal compliance claims.
- Do not invent exact contrast ratios.
- Do not invent hex codes without color evidence.
- Do not assume project-specific workflows unless provided.
- Do not recommend subtle grey text that fails contrast.
- Do not ignore mobile readability.
- Do not ignore focus, disabled, placeholder, and error states.
- Do not treat visual elegance as more important than readability.
- Do not mark an issue as measured unless it is actually measured.

---

## Final Instruction

Accessibility is about trust.

Prioritize changes that help users read, decide, and act confidently across real-world devices, low-quality screens, small mobile viewports, and visually stressful environments.

Always separate evidence-backed findings from heuristic concerns.
