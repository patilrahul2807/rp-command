---
name: rp-dispatch
description: "Phase order and agent dispatch for every rp-command builder pipeline (ACF, Elementor, Gutenberg, Avada, HTML). Used by /rp-start running in the main session."
---

# Skill: rp-dispatch

The main session (`/rp-start`) is the orchestrator. It dispatches each phase agent with the
Agent tool. Agents never dispatch other agents.

Common inputs for every agent: `.rp/project-config.json`, `.rp/design/design.json`,
`.rp/design/frames/*.png`, `.rp/design/media-map.json`, and the previous phase's output.
Each agent writes its report to `.rp/phases/<nn>-<agent>.md`.

`∥` = may run in parallel (one message, several Agent calls). `→` = sequential.

## ACF (custom theme + Flexible Content)

1. `acf-section-analyzer` — one section spec per design section → `.rp/specs/*.json`
2. `acf-planner` — reuse vs. new layouts, layout list, page → rows map → `.rp/plan.json`
3. **Gate:** user approves the plan
4. `acf-theme-setup` — theme scaffold, Theme Settings options page
5. `acf-backend` → `acf-field-creator` — clone source groups once, then FC layouts
6. `acf-frontend-developer` ∥ `acf-scss-writer` — one template + one SCSS partial per layout
7. `acf-template-builder` — `content-page.php` FC loop, header/footer from options
8. Push theme files with `rp/update-theme-file` (child/parent per `theme.scope`); compile SCSS
   locally (`npx sass`) and push the CSS
9. `acf-page-assembler` — create pages, fill FC rows with real text and media ids
10. QA: `acf-visual-comparator` per page → fixes by `acf-frontend-developer` / `acf-scss-writer`
    scoped to failing layouts → re-QA (max 3)

## Elementor

1. `elementor-section-detector` — section boundaries per frame
2. `elementor-planner` (or `elementor-strict-planner` if the developer asked for strict mode) → `.rp/plan.json`
3. **Gate:** user approves the plan
4. `elementor-foundation-builder` — Kit colors, typography, container width, breakpoints
5. `elementor-page-builder` (strict: `elementor-strict-section-builder`, one section at a time)
6. `elementor-overlap-gradient` — only for sections the plan flagged
7. `elementor-globals-enforcer` → `elementor-globals-verifier`
8. QA: `qa` (visual capture vs. frames) → `elementor-style-refiner` / `elementor-targeted-fixer` → re-QA (max 3)

## Gutenberg (block theme)

1. `gutenberg-planner` — templates, parts, patterns, custom blocks → `.rp/plan.json`
2. **Gate:** user approves the plan
3. `gutenberg-foundation-builder` — theme.json (`rp/gutenberg-manage-theme-json`)
4. `gutenberg-theme-builder` ∥ `gutenberg-block-author` (only if custom blocks are planned)
5. `gutenberg-page-builder` — pages from core blocks + patterns; validate with `rp/gutenberg-validate-blocks`
6. `gutenberg-globals-enforcer`
7. QA: `qa` → fixes by `gutenberg-page-builder` scoped to failing sections → re-QA (max 3)

## Avada

1. `avada-planner` → `.rp/plan.json`
2. **Gate:** user approves the plan
3. `avada-foundation-builder` — global options (`rp/avada-manage-global-options`)
4. `avada-page-builder` — per page, elements validated with `rp/avada-validate-element`; header/footer via `rp/avada-manage-layouts`
5. `rp/avada-clear-cache`
6. QA: `qa` → `avada-targeted-fixer` → re-QA (max 3)

## HTML source

Run `html-project-extractor` → `html-parser` first, then continue with the chosen builder:
ACF → `html-acf-planner` → `html-acf-builder` → `html-php-writer` → `html-theme-assembler` → `html-deployer` → `html-qa`;
Elementor → `html-to-native-elementor` / `html-elementor-fidelity-builder` → `html-qa`.

## Dispatch prompt template

```
Phase: <nn> <agent>
Goal: <what to produce>
Inputs: .rp/project-config.json, .rp/design/design.json, .rp/design/frames/, .rp/design/media-map.json, <previous output>
Output: <path>
Scope: <pages / sections>
Developer instructions (verbatim, they override skill defaults except rp-core-rules):
<text>
Acceptance: <criteria>
```
