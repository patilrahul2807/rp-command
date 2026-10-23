---
description: Validate project-config.json and the design-system registries for internal consistency — every page in config has a registry entry and vice versa, every referenced component/layout exists. Read-only; reports fixable issues, never repairs them automatically.
argument-hint: "(no arguments)"
allowed-tools: Read, Glob, Grep
---

# RP — config & registry validator

`/rp-validate` is **read-only**, exactly like `/rp-status` — it never writes a file, never
dispatches to the bridge, never delegates to a build agent. Its job is different from
`/rp-status`'s, though: `/rp-status` reports *what state things are in*; this command reports
*whether that state is internally consistent* — pass/fail per check, with an exact, fixable
description of anything that isn't. If nothing below can be read (no `project-config.json`), tell
the developer to run `/rp-start` first and stop.

## Why this exists as its own command, not a bolt-on to `/rp-status`

`/rp-status` is explicitly documented as "never writes anything" / pure reporting, and already
tolerates a known inconsistency (the ACF/Elementor `page-memory.json` field-name mismatch) by
reading defensively rather than flagging it. This command takes the opposite stance on exactly that
kind of finding: the same defensive-read discipline (never crash on a missing/malformed file, never
invent a value) but every gap becomes a **reported finding**, not a silently-tolerated read
pattern. Keeping this separate from `/rp-status` means `/rp-status`'s charter stays "report state"
and this command's charter is "judge whether that state is sound."

## What "validate" means here — structural/cross-reference checks, not strict JSON Schema

None of the registries (`component-registry.json`, `page-memory.json`, `acf-layout-registry.json`,
`design-tokens.json`) have a locked JSON Schema — they are prose-documented (field names described
in agent `.md` files, not enforced anywhere). So this command cannot validate "does this match a
schema" for those files. What it CAN validate, and does:


**`project-config.json` shape** — the documented required top-level keys are present
   (`figma`, `theme` (ACF only) or none (Elementor-only), `project`, `qa_breakpoints`,
   `output_structure`) per the schema in `acf-project-brief` SKILL.md. Missing a key is a finding,
   not a crash — report it and continue checking everything else.

**Every page in `project.pages` has a registry entry** — cross-reference against
   `design-system/page-memory.json`. A page slug present in `project.pages` but absent from
   `page-memory.json` is a finding: `"<slug> is listed in project.pages but has no page-memory.json
   entry — was it ever actually built, or was it added to config and never picked up?"`

**Every registry entry has a corresponding config page** — the reverse direction. A page in
   `page-memory.json` but missing from `project.pages` is a finding (usually means someone edited
   `project-config.json` by hand and dropped an entry, or the file drifted across a manual edit).

**Every component/layout a page claims to use actually exists in its registry** — for each page
   entry in `page-memory.json`/`progress.json` that lists `layouts_used`/`sections`/similar, check
   that each named component/layout has a corresponding entry in `component-registry.json`
   (Elementor) or `acf-layout-registry.json` (ACF). A page referencing a component the registry
   doesn't know about is a finding — it means the registry update step was skipped or failed
   silently during a build.

**`qa_breakpoints`** — if present, both `core` and `full` arrays are present, non-empty, and
   `core` is a subset in spirit (every `core` width should also make sense as a `full` width;
   flag, don't fail, if `core` contains a width `full` doesn't — that's unusual but not
   necessarily wrong).

## Read tolerantly — same discipline as `/rp-status`

Every file below might be missing (brand-new project), malformed (hand-edited, truncated), or use
either pipeline's documented field-name variant. Apply the exact same rule `/rp-status` uses:


A missing registry file is **not an error** for a brand-new project — only report it as a finding
  if `project-config.json` claims pages exist (`project.pages` non-empty) but the registry that
  should describe them is absent entirely.

A malformed/unparseable JSON file **is** always a finding (unlike a merely-missing file) — report
  the exact parse error and file path; do not guess its intended contents.

Check both documented field-name shapes for `page-memory.json` (ACF:
  `{slug, status, completed_at, qa_status, layouts_used, ...}`; Elementor: `{slug, title, date,
  status, sections}`) — do not assume one shape and report a false finding because the other
  pipeline's field names are absent.

## What to read


`project-config.json` — full contents.
`design-system/page-memory.json`, `design-system/component-registry.json`,
   `design-system/acf-layout-registry.json` (ACF projects only), `design-system/design-tokens.json`
   — whichever exist.

Per-page manifests: `pages/<slug>/progress.json` (ACF) or `pages/<slug>/checkpoint.md`
   (Elementor) for each page in `project.pages`, to cross-check per-section component/layout
   references against the registries (check 4 above).

**HTML→ACF projects** (`input_mode == "html_zip"` + `builder == "acf"`) — the spec/transplant
   pipeline's own cross-reference chain, whichever stages exist (absent = stage not reached,
   skip its checks):

`html_source` block well-formed (`archive_path` exists on disk; `status` is one of the
     three legal values; `approvals.page_inventory` present).

`spec/site-spec.json` parses; every `sections[].fragment` file exists under
     `spec/fragments/`; `meta.pages_count`/`sections_count` match the actual arrays.

`spec/acf-plan.json` parses; every plan layout references a spec section that exists;
     `approved: true` before any theme artifacts exist (theme built without sign-off = FAIL).

`acf-json/*.json` all parse; field keys globally unique; every plan layout appears exactly
     once; every clone reference resolves.

`template-parts/sections/*.php` — one partial per approved layout (extra/missing = FAIL).
`seed/pages-manifest.json` parses; every listed template/field-group file exists; every
     `seed/content/<slug>.json` row's `acf_fc_layout` names a real layout.

`deploy-state.json` (if present) — every recorded slug is in `project.pages` (or
     `pages: "all"`).

## Output format

```
========================================
RP CONFIG & REGISTRY VALIDATION
========================================
Project: <site_mode> | Builder: <project.builder>

Checks
  [PASS] project-config.json required keys present
  [FAIL] page "about" in project.pages but missing from page-memory.json
  [PASS] every page-memory.json entry has a matching project.pages entry
  [FAIL] page "services" references component "pricing-table" — not found in component-registry.json
  [PASS] qa_breakpoints.core / .full both present and non-empty
  ...

Summary: <n> passed, <n> failed

<if any FAIL>
Fixable issues found. These are reported, not auto-repaired — review each one:

"about" missing from page-memory.json: if the page was actually built, re-run
    `python3 scripts/checkpoint.py mark <slug> qa-passed` (Elementor) or the ACF
    registry-update step for it; if it wasn't, remove it from project.pages or build it properly.

"services" → "pricing-table": either the component was renamed/removed from the registry
    without updating the page's reference, or the registry update was skipped mid-build — check
    session.md around when "services" was last touched for context.
========================================
```

## Rules


**Never write** any file — this command reports, it does not repair. A developer or a build
  agent fixes the underlying issue; this command only tells them exactly what and where.

**Never invent or guess** a value to make a check pass — an ambiguous or unreadable file is a
  FAIL with the exact reason, never silently skipped as if it were fine.

**Never treat a missing registry as an error on a brand-new project** — zero pages, zero
  registries is a fully valid, passing state. Only flag a missing registry when config claims pages
  exist that the registry should describe.

**One finding per real issue** — do not duplicate the same missing-page finding once per registry
  file if multiple registries are missing the same page; group it into one finding naming all the
  registries it's missing from.

If every check passes: ✅ All checks passed — config and registries are internally consistent.
