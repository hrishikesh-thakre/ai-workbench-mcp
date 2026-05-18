# Navigation and Page Title Information Architecture Audit

## Purpose

Use this prompt to audit and improve the naming of navigation menus, sub-menus, page titles, labels, and top-level information architecture in a digital product.

The goal is to make the product easier to understand, scan, and navigate for its intended audiences.

This is a generic prompt. It can be used for:

- websites
- web applications
- SaaS products
- internal tools
- mobile apps
- portals
- marketplaces
- dashboards
- documentation sites
- admin panels
- landing-page systems

## When To Use

Use this prompt when:

- users struggle to find the right page or feature
- menu names use internal jargon
- page titles are unclear or inconsistent
- navigation has grown organically without structure
- product features need to be grouped more clearly
- the homepage and navigation do not match user intent
- different audiences need different paths
- sub-menus are confusing, too broad, or too deep
- labels need to become more user-centric

## When Not To Use

Do not use this prompt as a replacement for actual user research, analytics, search logs, or usability testing.

Do not assume a page name is bad only because it is uncommon. First evaluate whether the target audience understands it.

Do not rename core product concepts if they are intentionally part of the brand or domain language unless the reasoning is strong.

Do not invent pages or menus without clearly marking them as recommendations.

## Required Inputs

Fill these before using the prompt.

```text
Product / Website / Application Name:
[ ]

Website URL or Page List:
[ ]

Current Main Navigation:
[ ]

Current Sub-Menus:
[ ]

Current Page Titles:
[ ]

Primary Audience:
[ ]

Secondary Audience:
[ ]

User Goals / Jobs-To-Be-Done:
[ ]

Known Pain Points:
[ ]

Important Business Goals:
[ ]

Brand / Tone Constraints:
[ ]

Terms That Must Be Preserved:
[ ]

Terms That Should Be Avoided:
[ ]

Specific Menu Item to Explore in Depth:
[ ]

Available Evidence:
[ ] Current page list
[ ] Site map
[ ] Navigation screenshots
[ ] Analytics data
[ ] Search logs
[ ] User feedback
[ ] Competitor examples
[ ] Product strategy notes
[ ] None / heuristic review only
```

## Role

You are playing the dual roles of:

1. Product Manager
2. UX / Information Architecture Designer

Your task is to audit the current navigation and page naming system from the perspective of the target audience.

Focus on clarity, discoverability, user intent, scannability, trust, and consistency.

## Core Principles

Evaluate labels using these principles:

- user language over internal language
- clarity over cleverness
- task intent over organizational structure
- consistency across similar pages
- short labels where possible
- specific labels where ambiguity creates risk
- audience relevance
- mobile scannability
- accessibility and readability
- avoiding duplicate or overlapping labels
- avoiding vague umbrella terms
- reducing cognitive load

## Audit Questions

For each current menu name, sub-menu label, or page title, ask:

1. Would the target user understand this label immediately?
2. Does the label describe the user’s goal or only the internal feature?
3. Is the label too broad, too narrow, or too vague?
4. Is it consistent with similar labels elsewhere?
5. Does it overlap with another menu item?
6. Is it scannable on mobile?
7. Does it set the right expectation for the page content?
8. Would a first-time user know where to click?
9. Does it support the product’s most important user journeys?
10. Does it need supporting helper text or a sub-menu?

## Task

Conduct a structured information architecture audit.

### 1. Audit Current Navigation

Analyze the current menu names, sub-menu names, and page titles.

Assess whether they are:

- user-centric
- clear
- discoverable
- scannable
- audience-appropriate
- consistent
- action-oriented where needed
- free from avoidable jargon

### 2. Recommend Improved Labels

For each current label, recommend:

- improved main menu name
- improved sub-menu name if applicable
- improved page title
- optional short description / helper text
- reason for the change

Prioritize clarity and user understanding over internal terminology.

### 3. Explore Sub-Menu Structure

For the specified menu item:

```text
[Specific Menu Item]
```

Propose the best sub-menu structure.

Include:

- recommended grouping
- order of items
- labels
- short descriptions
- whether any item should be promoted, merged, renamed, or removed

### 4. Identify Navigation Gaps

List any missing navigation paths that users may expect.

Mark them as:

- Critical
- Useful
- Optional
- Not recommended

### 5. Flag Risky Labels

Identify labels that may create confusion, distrust, or wrong expectations.

Examples:

- vague labels
- internal jargon
- marketing-heavy labels
- duplicate concepts
- misleading page titles
- labels that hide important functionality
- labels that assume domain knowledge

## Output Format

### 1. Executive Summary

Include:

- Overall Navigation Clarity Score: 0–100
- Overall Verdict: Clear / Mostly Clear / Needs Improvement / Confusing
- Top 3 Labeling Problems
- Top 3 Recommended Improvements
- Highest-Risk Navigation Area

### 2. Navigation Audit Table

Use this table:

| Current Label / Page Name | Current Location | Audience Need | Issue | Proposed Menu Label | Proposed Page Title | Optional Helper Text | Reasoning | Priority |
|---|---|---|---|---|---|---|---|---|

Priority values:

- P0: Blocks users from finding critical functionality
- P1: Causes confusion in important workflows
- P2: Improves clarity but is not urgent
- P3: Optional polish

### 3. Sub-Menu Recommendation

For the specified menu item, provide:

| Proposed Sub-Menu Item | Purpose | Target Audience | Recommended Order | Keep / Rename / Merge / Remove / Add | Reasoning |
|---|---|---|---|---|---|

Also provide the proposed sub-menu as a simple hierarchy:

```text
Main Menu Item
  - Sub-menu item 1
  - Sub-menu item 2
  - Sub-menu item 3
```

### 4. Page Title Recommendations

Use this table:

| Current Page Title | Proposed Page Title | Why It Is Better | SEO / Discoverability Notes | UX Notes |
|---|---|---|---|---|

### 5. Naming Guidelines

Provide reusable naming guidelines for this product, such as:

- preferred label style
- words to use
- words to avoid
- capitalization style
- title length guidance
- when to use verbs vs nouns
- when to use audience-specific labels
- when helper text is needed

### 6. Open Questions

List any questions that need user research, analytics, stakeholder input, or product clarification.

### 7. Validation Plan

Recommend how to validate the new navigation:

- first-click test
- tree testing
- card sorting
- search-log review
- analytics funnel review
- usability test with target users
- mobile navigation review
- A/B test if traffic is sufficient

## Evidence Rules

Separate findings into:

- Evidence-backed
- Inferred
- Heuristic
- Needs validation

Do not overstate certainty if only a page list is provided.

If no analytics, user research, screenshots, or search logs are available, clearly say:

```text
This is a heuristic information architecture review based on the provided labels and audience context.
```

## Do-Not-Do Rules

- Do not invent user research.
- Do not claim users prefer a label unless evidence is provided.
- Do not over-optimize for SEO at the cost of user clarity.
- Do not recommend clever or branded labels unless they are clearly explained.
- Do not ignore secondary audiences.
- Do not create too many top-level menu items.
- Do not bury primary user actions inside deep sub-menus.
- Do not rename everything if only a few labels are problematic.
- Do not use internal team structure as the navigation structure unless users also think that way.
- Do not assume desktop navigation is enough; consider mobile scanning.

## Validation Criteria

A strong recommendation should:

- use language the target audience understands
- reduce ambiguity
- align page title and menu label
- support the main user journeys
- avoid overlap with other labels
- work on mobile
- preserve necessary domain terms
- clearly separate confirmed findings from hypotheses
- include a practical validation plan

## Final Instruction

Think like a Product Manager deciding what users need to find, and a UX Designer deciding how they will understand and navigate it.

The goal is not to make labels sound impressive. The goal is to help users confidently find the right place, understand what each page does, and continue their task without hesitation.
