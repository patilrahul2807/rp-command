---
description: Read-only project status report — pages, per-section build state, component reuse counts, last build date, and drift vs the live site. Never writes anything.
argument-hint: "[page-slug]  (omit to report every page in project.pages)"
allowed-tools: Read, Glob, Grep, mcp__rp-command__rp-bridge-discover-tools, mcp__rp-command__rp-bridge-inspect-tool, mcp__rp-command__rp-bridge-dispatch-tool
---

# RP — status report

`/rp-status [page-slug]` is **read-only** — it never writes to a file, never dispatches a
destructive ability, and never delegates to a build agent. It only reads the local registries/
manifests and (optionally) does one cheap live-site check, then prints a compact report. If nothing
below can be read (no `project-config.json`), tell the developer to run `/rp-start` first and stop.

## Known schema inconsistency — read tolerantly, do not guess

`design-system/page-memory.json` is documented with **two different field sets for the same file**
across the two pipelines: `acf-project-orchestrator.md` uses
`{slug, status, completed_at, qa_status, layouts_used, new_layouts_created, reused_layouts,
scss_files, php_templates}`; `scripts/checkpoint.py` uses
`{slug, title, date, status, sections}`. Neither file states a reconciled shape, and this command
does not attempt to invent one. **Read every field independently and defensively** — for each page
entry, check for each documented field name from BOTH shapes; show whatever is present, print `—`
for anything absent. Never crash on a missing field, and never present a guessed/interpolated value
as if it were read from the file. Print this note once, in the report footer, so the developer
knows the report's per-pipeline field coverage may differ rather than silently varying without
explanation:
```
NOTE: page-memory.json field names differ between the ACF and Elementor pipeline docs — this
report shows whichever documented fields are present per page; missing fields show as "—", not a
guess.
```

Apply the same defensive-read principle to every file below — a missing or malformed registry is a
`—`/`not found` in the report, never a script error and never an invented number.

## What to read


**`project-config.json`** — `project.pages`, `project.builder`, `site_mode`. If the argument
   `[page-slug]` was given, restrict everything below to that one page; otherwise report every slug
   in `project.pages`.

**`design-system/page-memory.json`** — per page: `status`, and whichever of `completed_at`/
   `date`, `qa_status`, `layouts_used`/`sections` are present (see schema note above).

**`design-system/component-registry.json`** — component names, reuse counts, and pages using
   each (field names are prose-documented, not schema-locked — read whatever keys are present per
   entry; if a `component_library` sub-map exists (the `{hash: {template_id, name}}` shape from
   `template_reuse.py`), report its entry count separately from any top-level component list, since
   the two are not documented as the same structure).

**`design-system/acf-layout-registry.json`** (ACF projects only) — layout names + reuse.
**`design-system/design-tokens.json`** — count of colors/fonts/spacing tokens recorded.
**Per-page build state:**
**ACF page:** `pages/<slug>/progress.json` if present — per section: `backend_status`,

     `frontend_status`, `qa_status`, and `element_id`/`backup_id` if present. If the file doesn't
     exist, report the page as "no per-section manifest — status from page-memory.json only."

**Elementor page:** `pages/<slug>/checkpoint.md` if present — count `[x]` vs `[ ]` per
     section under its `## Phase 2..N — Sections` heading, and read the pipeline-phase checkboxes
     (`figma-extracted`, `plan-created`, `phase-1-foundation-complete`, `all-sections-complete`,
     `globals-verified`, `qa-passed`) directly from the markdown — do not parse this with a script;
     `checkpoint.md` is intentionally regex-parsed by hand per its own documented format (unifying
     it onto JSON is explicitly a separate, later task — do not attempt that here either).

**HTML→Elementor page** (`pages/<slug>/qa/section-qa-state.json` present — this file is written
     by `html-to-native-elementor`, the single HTML→Elementor route; a Figma-sourced page never has
     one, so its absence just means "not this route," never an error): read the same
     `pages/<slug>/checkpoint.md` checkboxes as above, plus these fidelity-specific phase marks —
     `html-source-extracted`, `html-reference-captured`, `html-assets-resolved`, `html-kit-verified`,
     `html-foundation-locked`, `html-sections-in-progress`, `html-sections-locked`,
     `html-full-page-passed`, `html-functional-passed`, `page-created` — via the same hand-parsed
     checkbox convention, no script involved. Then read `section-qa-state.json` itself for the
     per-section detail table: each entry's `status` (`locked`/`blocked`/`pending`/`in_progress`),
     `iterations`, and per-width `similarity_pct` (report the lowest width's value as the headline
     number, since that is the binding one against the 98% lock threshold). A `blocked` section is
     the most important line in the whole report for this route — always surface it, never bury it
     under passing sections.

**HTML→ACF project** (`project.input_mode == "html_zip"` AND `project.builder == "acf"` —
     the spec/transplant pipeline): report the pipeline-stage state, whole-site not per-section.
     Read, tolerantly: `html_source.status` (`pending-analysis`/`pages-detected`/
     `homepage-confirmed`) + `approvals.pages.<slug>.status`; then stage evidence —
     `spec/site-spec.json` exists (parsed), `spec/acf-plan.json` `approved: true` (planned/
     signed-off), theme dir + `seed/pages-manifest.json` (assembled), `deploy-state.json`
     (deploy progress: slugs → post_ids present), `qa/report.md` (QA verdicts + any
     `qa-blocked` pages), newest `qa/accuracy/<run>/causes-summary.json` (final audit headline:
     findings by severity). Report the first incomplete stage as "next step". Absent files are
     `—` ("stage not reached"), never errors.

**`session.md`** (project root) — the most recent dated heading, for a one-line "last build
   activity" timestamp per the report footer.

**`pages/<slug>/metrics.json`** (only if `[page-slug]` was given — this is per-section detail,
   not a summary-view field) — if present, surface `wall_clock.total_seconds`/`total_days`,
   `qa_pass_rate.rate`, and each section's `drift_at_first_pass` vs `final_pixel_gate` diff_pixels
   (shows whether the fix loop did meaningful work or the section passed clean on the first try).
   If absent, say `no metrics.json — page was built before backlog 9.4, or is still in progress`,
   never fabricate a value. Never treat a `null` field inside metrics.json as 0 or "unknown" —
   print it as `—` exactly like every other unavailable field in this report.

## Optional live-site drift check (only if the developer asks for it, or passes `--drift`)

This is the ONE place `/rp-status` may call the bridge, and only for a **read-only** ability:

```
mcp__rp-command__rp-bridge-dispatch-tool
{ "ability_name": "rp/list-pages", "parameters": {} }
```

Compare the returned page list/ids against `page-memory.json`'s pages. Report, per page:

**In sync** — page exists live and `page-memory.json` says `complete`.
**DRIFT: page missing from config** — exists live but not in `page-memory.json`/`project.pages`.
**DRIFT: page missing live** — `page-memory.json` says `complete` but `list-pages` doesn't return
  it (deleted or renamed in wp-admin since the last build).

Do not attempt a deeper per-post diff here (`rp/get-post-state`/`rp/diff-post-states`) — that is
wired into the build/publish workflow, not a status report. `/rp-status`'s drift check is a cheap
existence check only, never a full content diff.

If the bridge tools are unavailable, skip this section entirely and note `drift check skipped — not
connected` rather than failing the whole report.

## Output format

Print a single compact report, in this shape:

```
========================================
RP PROJECT STATUS
========================================
Project: <site_mode> | Builder: <project.builder> | ACF: <acf_present>/<acf_role>

Pages
  <slug>       <status>       <builder>    <n> sections   last: <date-or-—>
  <slug>       <status>       <builder>    <n> sections   last: <date-or-—>
  ...

Design System
  Components registered:      <n>   (reused <n> times across <n> pages)
  ACF layouts registered:     <n>   (ACF projects only)
  Design tokens:              <n> colors, <n> fonts, <n> spacing/radius
  Reusable template library:  <n> entries (component_library, if present)

Per-section detail (only if a single [page-slug] was given as the argument)
  <section-name>   backend/build: <status>   frontend/style: <status>   qa: <status>
  ...

Per-section detail — HTML→Elementor fidelity route (only if [page-slug] was given AND
qa/section-qa-state.json exists for it — omit this block entirely otherwise)
  <section-id>   status: <locked|blocked|pending|in_progress>   similarity: <lowest-width-pct-or-—>%   iterations: <n>
  ...

Build telemetry (only if a single [page-slug] was given AND metrics.json exists for it)
  Wall clock:      <total_seconds-or-total_days-or-—>
  QA pass rate:    <rate-or-—>  (<sections_passed>/<sections_total>)
  <section-name>   first-pass diff: <n>px   final diff: <n>px   iterations: <n-or-—>
  ...

<drift section — only if requested>
  <slug>   <in sync | DRIFT: reason>

Last build activity: <most recent session.md dated heading + its last bullet>

NOTE: page-memory.json field names differ between the ACF and Elementor pipeline docs — this
report shows whichever documented fields are present per page; missing fields show as "—", not a
guess.
========================================
```

## Rules


**Never write** any file, never dispatch a destructive ability, never delegate to a build agent
  (`page-builder`, `foundation-builder`, `acf-backend`, etc.) — this command's entire job is
  reading and reporting.

**Never invent a value** for a field that isn't present in the file being read — show `—`.
**Never treat a missing registry file as an error** — an empty/not-yet-created `design-system/`
  folder is normal for a brand-new project; report zero counts, not a failure.

If `[page-slug]` was given but doesn't exist in `project.pages`, say so plainly and list the
  slugs that DO exist — don't silently report on the wrong page.
