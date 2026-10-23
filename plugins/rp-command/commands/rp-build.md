---
description: One-command end-to-end build for a single page — chains extraction, validation, planning, foundation, section build, verification, QA, and checkpointing, stopping at the first failing gate with a clear reason.
argument-hint: <page-slug> [--full-qa] [--publish-live] [--strict-sections]
allowed-tools: Read, Glob, Grep, Bash(python3 scripts/*.py:*), Bash(claude mcp list:*), Bash(claude mcp add:*), Agent, mcp__rp-command__rp-bridge-discover-tools, mcp__rp-command__rp-bridge-inspect-tool, mcp__rp-command__rp-bridge-dispatch-tool
---

# RP — one-command end-to-end build

`/rp-build <page-slug>` chains the pipeline for one page, using the **existing hard gates** —
this command does not invent a new build path, a new validation rule, or a new ability. It only
sequences the same steps a developer would otherwise run one agent at a time, and stops at the
first gate that fails instead of pushing forward on a broken foundation.

**The manual per-agent path stays available for debugging** — nothing here disables invoking any
agent individually; this command is a convenience wrapper, not a replacement pipeline.

**`--strict-sections` (Elementor only):** use the pre-fast-build strict
per-section pipeline (per-section build→enforce→QA→refine→re-QA loop via
`elementor-section-orchestrator`) instead of the default whole-page
single-dispatch fast-build pipeline (`elementor-fast-build-qa`). Use when a
design has unusually high per-section risk, or when debugging a
fast-build QA-blocked page section-by-section.

**`--strict-sections` is rejected whenever `project.input_mode == "html_zip"`, unconditionally — no
flag combination makes it valid.** `elementor-strict-planner`/`elementor-section-orchestrator`
hard-require real `pages/<page-slug>/figma/spec.md`/`ir.json`/`tokens.json` files that no HTML-ZIP
route produces — not the recipe-first path, not any future HTML→Elementor route this project adds,
regardless of which other flag accompanies it. Before Step 1 runs, check
`project.input_mode == "html_zip"` AND `--strict-sections` was passed; if both are true, STOP and
report: "`--strict-sections` is Figma-only — this project's `input_mode` is `html_zip`, which has no
`figma/` extraction to walk section-by-section. HTML→Elementor always runs
`html-to-native-elementor`, which already gates section-by-section on its own." Do not let this
combination reach `elementor-strict-planner`/`elementor-section-orchestrator` under any
circumstance.

**HTML→Elementor has exactly ONE route — no flags, no rollout marker.** When
`project.builder == "elementor"` AND `project.input_mode == "html_zip"`, the build is
`Agent(html-to-native-elementor, …)` and nothing else. There is no recipe-first alternative and no
measurement-first alternative to choose between, so there is no flag to choose with and no default
to compute. See Step 1's `html_zip` branch below.

The retired selectors are listed here only so an old command line gets a clear answer instead of a
silent misroute — if `--html-fidelity` or `--html-fast` is passed, do **not** fail the build: say
"`--html-fidelity`/`--html-fast` no longer exist — HTML→Elementor always runs
`html-to-native-elementor`", then continue on that single route. The former
`HTML_ELEMENTOR_FIDELITY_STATUS` marker is gone with them; if you find a reference to it anywhere,
it is stale documentation, not a switch to read.

## Preconditions (run before anything below)

0. **Playwright MCP gate (HARD GATE).** This command runs Playwright-driven verification and QA
   (`mcp__playwright__browser_*`) at multiple steps. Before anything else, confirm it is connected:
   run `claude mcp list` and check a `playwright` server is listed with status `✔ Connected`, **and**
   that the tool `mcp__playwright__browser_navigate` is available this session.
   - **If the `playwright` server is absent entirely** → auto-install it with
     `claude mcp add playwright npx @playwright/mcp@latest`, then **STOP** — its tools cannot load
     until Claude Code is restarted, so this build cannot continue this session. On success, tell
     the developer: "✅ Playwright MCP installed — restart Claude Code (or reload MCP servers), run
     `/rp-doctor` to confirm, then re-run `/rp-build`." On failure, report the raw error and the
     manual command.
   - **If it is listed but not `✔ Connected`, or its tools aren't loaded** → do not re-add it;
     **stop** and tell the developer to fix/reload it (point at `/rp-doctor` step 2b) and re-run.
   (This gate is intentionally redundant with `/rp-start` step −2 — `/rp-build` can run warm,
   without `/rp-start` re-running this session, so it must re-check rather than assume.)
1. If `mcp__rp-command__*` tools are not available, tell the developer to run `/rp-command
   <site-url>` then `/rp-doctor`, and stop.
2. **Proactively verify the connection is actually healthy — do not assume tool availability means
   the credentials still work.** Call `mcp__rp-command__rp-bridge-discover-tools` once, live
   (this is the same call the pipeline needs first anyway per `rp-dispatch` §0, so this check adds
   no extra round-trip — it just moves that first call here, before anything else, instead of
   letting it fail organically several steps into a build). If it fails, diagnose it exactly the
   same way `/rp-doctor`'s own failure-handling does (401 → stale/revoked credentials, re-run
   `/rp-command`; 404 → plugin deactivated or wrong URL; connection error → site unreachable) and
   **stop before any build step runs** — a build failing on step 6 because of a credential problem
   that was true from the start wastes far more of the developer's time than catching it here.
   **If it succeeds, WRITE the result to `cache/abilities.json`** (with an added `cached_at`
   ISO-8601 timestamp, same shape `/rp-doctor` writes) — every agent this command dispatches below
   runs as a SEPARATE subagent with no shared memory of this call, so without this write each one
   would independently find the cache missing/stale and re-discover live itself, silently
   reintroducing the exact round-trip this step exists to avoid. Every subsequent
   `Agent(elementor-*, ...)` call in this command inherits a warm cache from this one write.
3. Run the **`/rp-start`** discovery gate first (or confirm it has already run this session —
   `project-config.json` exists). `/rp-build` never substitutes for the discovery gate; it assumes
   `site_mode`, `builder`, `acf_present`, `acf_role`, and `figma_source` are already resolved and
   written to `project-config.json`. If they are not, stop and run `/rp-start` first.
4. Read `project-config.json` and branch on `project.builder` — the three pipelines below are
   genuinely different (ACF has a self-orchestrating agent; Elementor and Gutenberg are both
   agent-by-agent, and Gutenberg additionally has no orchestrator skill or style-refiner the way
   Elementor does), so do not try to force one code path to cover more than one.

---

## Builder = `acf`

The ACF pipeline already has a single self-planning orchestrator that internally sequences
extraction → design-similarity → backend → frontend → QA → registry updates, with its own resume
logic (`pages/<page-slug>/progress.json`) and its own confirmation checkpoints.
`/rp-build` for ACF is a thin invocation of that existing agent — it does not re-implement any of
its steps:

```
Agent(acf-project-orchestrator, "<page-slug>")
```

**`input_mode: "html_zip"` — do NOT invoke `acf-project-orchestrator`.** HTML-ZIP-to-ACF runs
the **spec/transplant pipeline** instead (shared extraction, then verbatim-fidelity conversion).
`acf-project-orchestrator` and its subagents stay Figma-only. Sequence — each step gated; on the
first failed gate STOP and report:

1. **Extraction (ACF only — the Elementor html_zip path no longer shares this step;
   `html-to-native-elementor` unzips and confirms the homepage itself).**
   Branch on `html_source.status`:
   - `pending-analysis` → `Agent(html-project-extractor, "start")` → relay its page-inventory
     report and STOP (the developer confirms the homepage next turn).
   - `pages-detected` → relay the inventory from `project-config.json`, get the homepage
     confirmation, then `Agent(html-project-extractor, "--confirm-homepage <slug>")`.
   - `homepage-confirmed` → continue.
   For `builder: "acf"` the extractor's **per-page blueprint generation is skipped**
   (`html-parser` owns section discovery below — see the extractor's ACF note); only the
   project-wide artifacts are required: `source/html/{manifest,pages,tokens,assets,shared-regions}.json`
   + `_extracted/`.
   Then `Agent(html-visual-reference-builder, "<slug>")` for each selected page (reference
   screenshots for QA).
2. **Parse** — `Agent(html-parser, "<selected pages>")`: reads `_extracted/` + the extraction
   JSONs, writes `spec/site-spec.json` + byte-verbatim `spec/fragments/` +
   `docs/spec-review.md`. **GATE (developer): spec review** — present the review summary + open
   questions; corrections are applied by re-running the parser, never by hand-editing the spec.
3. **Plan** — `Agent(html-acf-planner)`: classifies every section (Global/Local/Options/CPT) with
   reuse verdicts, writes `spec/acf-plan.json` + `docs/acf-review-table.md`. **GATE (developer):
   classification sign-off** — confirmations/overrides go back to the planner; it marks the plan
   `approved: true`.
4. **Build (local, no bridge)** — in order: `Agent(html-acf-builder)` →
   `Agent(html-php-writer)` → `Agent(html-theme-assembler)`. Each validates its own output;
   relay failures, never patch inline. Result: the theme dir + `seed/` manifests.
5. **Deploy** — `Agent(html-deployer)` with `deploy_mode`, `pages`, `publish` from
   `project-config.json` (asked at `/rp-start` — if absent, ask now, once). Idempotent; resumes
   from `deploy-state.json`.
6. **QA loop** — `Agent(html-qa)`: pixel gate first, diff-only analysis, DOM false-positive
   rescue, ranked root causes; route HIGH/MED to `html-php-writer`/`html-theme-assembler`,
   re-deploy deltas via `html-deployer`, re-invoke on affected pages. **Capped at 3 iterations
   per page** — still failing → report blocked with the open issues, do not keep looping.
7. **Final audit** — after QA passes and the publish decision is applied,
   `Agent(html-fingerprint-auditor)` ONCE → `qa/accuracy/<run>/` scorecard + `causes-viewer.html`
   (the designer handoff). It never fixes and never loops. On QA pass per page, set
   `approvals.pages.<slug>.status = "approved"` in `project-config.json` (this is what
   `checkpoint.py page-can-start` reads).

The spec is the source of truth: downstream agents never re-read raw HTML; fragments are
transplanted byte-verbatim, never re-typed. All site writes go through the bridge via
`html-deployer`; nothing here calls raw REST or `wp` CLI, and nothing deletes on the client site.
After deploy, append the build to `session.md` and update `design-system/page-memory.json`.

Let `acf-project-orchestrator` run its full flow, including its own developer confirmations (the
deduplication plan, ACF field review, template review). If it stops for a confirmation, this
command's job is done for that turn — do not bypass or auto-answer those prompts.

If `acf-project-orchestrator` reports a QA failure or aborts, relay its exact output and stop. Do
not retry silently.

**Staging-first:** `acf-page-assembler`/`acf-setup` now create pages as `status:
"draft"` by default (see those agents for the opt-in publish step). If invoking
`acf-project-orchestrator` without `--publish-live`, the page it builds stays a draft — report the
edit URL and stop, same as the Elementor Step 9 below. Pass `--publish-live` through if the
developer wants this build to end with an explicit publish confirmation.

---

## Builder = `elementor`

No single orchestrator agent exists for Elementor — the pipeline is explicit agent-by-agent, each
with its own hard gate. Run the steps below **in order**, checking the stated gate before advancing
to the next. On the first gate that fails, **stop immediately** and report exactly which gate
failed and why — do not skip ahead or silently retry a different step.

### Step 0 — Resume check

```
python3 scripts/checkpoint.py read <page-slug>
```

Read `NEXT_RECOMMENDED`. If it is not the first pipeline phase (`figma-extracted`), this page was
already partially built — jump straight to the step below matching `NEXT_RECOMMENDED` instead of
starting over from Step 1. This is what makes `/rp-build` safe to re-run after a crash or a
previous stop: idempotent, per `scripts/checkpoint.py`'s own resume contract.

### Step 1 — Design source extraction

Branch on `project.input_mode` — **not** a fourth `project.builder` value, an orthogonal source
selector (see `rp-dispatch` §0.5 and CLAUDE.md's roster note).

**`input_mode` is `figma_url` or `figma_zip`** (the original path, unchanged): use whichever
extractor matches `project.figma_source` (`url` → `elementor-figma-design-extractor`, `zip` →
`elementor-figma-local-extractor`):

```
Agent(elementor-figma-design-extractor, "<figma-url> <page-slug>")   # figma_source = url
Agent(elementor-figma-local-extractor, "<page-slug>")                 # figma_source = zip
```

**Gate:** the extractor's own PHASE 7 parity check (Step 8 / Step 7.3 in the respective agent
files) must report `PARITY CHECK PASSED`. If it fails, stop — report the missing/invalid artifact
exactly as the parity check printed it. Do not proceed to Step 2 on a failed parity check.

**`input_mode` is `html_zip`** — **one route, one agent, no alternatives.** The whole page is
built by:

```
Agent(html-to-native-elementor, "<page-slug>")
```

That agent owns the job end to end and needs no extraction layer in front of it: it unzips the
archive itself, finds the real source root, serves it on `http://127.0.0.1:8899`, derives the design
system from the **rendered** original into the Elementor Kit (backing the Kit up first), creates the
page, then runs its own gated section loop — measure the original → build with native widgets →
screenshot-score at every breakpoint → fix → lock at ≥98% — followed by a whole-page pass, functional
verification, and an honest per-section × per-breakpoint report. Its own file
(`agents/html-to-native-elementor.md`) is the authority on that sequence; do not restate, reorder, or
second-guess it here.

Consequences for the rest of this command, all of them deliberate:

- **`html-project-extractor` and `html-visual-reference-builder` are NOT called on this path.** They
  serve the ACF HTML pipeline (`builder: "acf"`, spec C) and the retired recipe-first Elementor route.
  The native agent does its own unzipping, page discovery, and source capture, so invoking them here
  would extract the same archive a second way and produce a `pages/<slug>/design/` blueprint nothing
  reads. There is likewise no `pages/<page-slug>/figma/` directory for this path.
- **Skip Steps 1.5, 2, 3, 4, 5, 6, 7 and 8 entirely.** Those belong to the Figma recipe-first
  sequence; the native agent has already done the equivalent work (planning, foundation/Kit, build,
  globals discipline, QA) inside its own gates. Running them would rebuild the same page a second way.
- **Multi-page archives:** if the developer did not say which page, the agent asks, then offers the
  rest afterwards.
- **The homepage guard is intact and the agent owns it.** Because `html-project-extractor` does not
  run on this path, `html-to-native-elementor`'s **Step 1a** presents the page inventory, asks the
  developer to confirm the homepage by explicit slug, hard-stops until they answer, and only then
  writes `html_source.homepage_confirmed` / `build_sequence` / `project.allow_homepage_build` — the
  same fields, shape and precondition as the extractor's Mode B. Its Step 1b then runs
  `python3 scripts/checkpoint.py homepage-build-allowed <page-slug>` before any homepage write. Do
  not pre-answer that question here, and do not write those config fields on the agent's behalf.
- **On success**, go straight to **Step 9 (Publish — staging-first)**. The agent leaves the page as a
  `draft` and reports its edit URL and permalink.
- **If it reports a `BLOCKED` line**, stop and relay its measured blocker plus the artifact paths it
  names, verbatim. Do not retry it and do not substitute another agent — there is no fallback route
  to fall back to.

Mark: `python3 scripts/checkpoint.py mark <page-slug> figma-extracted --agent html-to-native-elementor --note 'html_zip source; html-to-native-elementor owns extraction through QA'`

### Step 1.5 — Section detection (fast-build default; skipped on `--strict-sections` AND on `input_mode: "html_zip"`, see Step 1 above)

```
Agent(elementor-section-detector, "<page-slug>")
```

**Gate:** `pages/<page-slug>/figma/sections.json` exists and is non-empty. If
`--strict-sections` was passed, skip this step — the strict path uses
`spec.md`'s section list directly, as it always has.

Mark: `python3 scripts/checkpoint.py mark <page-slug> sections-detected --agent section-detector`

### Step 2 — Validate the extracted spec (Figma path only — skipped on `input_mode: "html_zip"`, see Step 1 above)

```
python3 scripts/validate_spec.py --builder elementor --page-dir pages/<page-slug>/figma
```

**Gate:** `"valid": true`. If `false`, stop and report every entry in `errors` — this is
intentionally a harder gate than the extractor's own parity check (it also validates `tokens.json`
color/typography shape, which the parity check only checks for the presence of the top-level
`design_system`/`theme_style` keys, not their contents). Fix the offending artifact and re-run this
step; do not advance to planning with an invalid spec.

Mark: `python3 scripts/checkpoint.py mark <page-slug> figma-extracted --agent figma-extractor --note 'validate_spec.py passed'`

### Step 3 — Overlap/gradient detection

**Fast-build default:** already covered by Step 1.5 — `elementor-section-detector`
sets `overlap`/`gradient` per section directly from `design-tokens.json`, no
separate agent call. Skip this step entirely unless `--strict-sections` was
passed.

**`--strict-sections` path (unchanged):**
```
Agent(elementor-overlap-gradient, "<page-slug> --detect")
```
Verify `pages/<page-slug>/figma/overlap-gradient.json` exists rather than
re-running it if the extractor already produced it. Only invoke directly if
missing.

Mark: `python3 scripts/checkpoint.py mark <page-slug> overlap-gradient-detected --agent overlap-gradient` (strict path only)

### Step 4 — Plan

```
Agent(elementor-planner, "<page-slug>")                  # fast-build default
Agent(elementor-strict-planner, "<page-slug>")            # --strict-sections
```

**Gate — one consolidated developer approval (fast-build default, `elementor-planner`).**
The planner selects a recipe per section (via `skills/elementor-recipes`) and
presents ALL sections in ONE `AskUserQuestion` call — not one round per
section. Once approved, the planner writes `blueprint.json` (not `plan.md`).

**`--strict-sections` path (`elementor-strict-planner` — a separate, narrower agent, not a mode
flag on `elementor-planner`):** walks the spec section-by-section, waiting for confirmation after
each one, and writes the legacy `plan.md`/`ir.json` pair.

Mark: `python3 scripts/checkpoint.py mark <page-slug> plan-created --agent planner`

Page creation (`rp/create-page`) is **not** a separate step here — it happens inside Step 5/6
below as part of foundation-builder's and page-builder's own build flow (see their Build Order /
Option B), using the `post_id` the planner's `blueprint.json` (fast-build) or `plan.md`
(`--strict-sections`) should already reference if the page exists, or creating it fresh on first
build.

### Step 5 — Foundation (Phase 1 — globals, header, footer)

```
Agent(elementor-foundation-builder, "<page-slug>")
```

**Gate:** foundation-builder must print `foundation-builder: PHASE_1_COMPLETE — <page-slug>`. If it
instead prints a `BLOCKED` line, stop — report the exact step and iteration count it failed at
(foundation-builder already caps itself at 3 iterations per step and saves failure artifacts under
`pages/<page-slug>/qa/foundation-failure-<step>-<timestamp>/`; surface that path to the developer).

### Step 6 — Whole-page build + capped QA (Phase 2..N, fast-build default)

```
Agent(elementor-page-builder, "<page-slug>")
```
No `--section` flag — `elementor-page-builder` reads `blueprint.json` and
assembles + dispatches the ENTIRE page (every section) in one `rp/build-page`
call (Option A, per that agent's own Build Order).

Mark: `python3 scripts/checkpoint.py mark <page-slug> body-built --agent page-builder`

Then run the capped QA driver:
```
Follow skills/elementor-fast-build-qa/SKILL.md directly: one whole-page QA
pass, then AT MOST 2 targeted correction passes via elementor-targeted-fixer
(a narrow patch agent applying qa's ranked root_causes — not the full
page-builder).
```

**Gate:** the skill's own terminal line `fast-build-qa: PASS — <page-slug>
(pass <n>)`. If it instead reports `BLOCKED — 2 correction passes
exhausted`, stop — report the artifacts path
(`pages/<page-slug>/qa/fast-build-FAILED/`).

**`--strict-sections` path (unchanged):** there is no separate
`section-orchestrator` agent to spawn — `elementor-section-orchestrator` is a
**skill**, not a registered subagent type. Follow its documented per-section
loop directly: build → enforce globals → QA → (style-refiner if needed) →
re-QA → checkpoint, per section, capped at 3 iterations each, refusing to
start section N+1 until section N is `qa-passed`. Do this for every section
in `spec.md` (excluding header/footer, already built in Step 5).

**Gate (strict path):** the skill's own terminal output line
`section-orchestrator: COMPLETE — <slug> all sections passed`. If it instead
reports `BLOCKED — <section-id> after 3 iterations`, stop — report the
artifacts path (`pages/<page-slug>/qa/section-<id>-FAILED/`).

### Step 7 — Final globals verification

```
Agent(elementor-globals-verifier, "<page-slug>")
```

**Gate:** report at `pages/<page-slug>/qa/globals-verify.md` shows no failing token. This is a
read-only re-check across the whole page — on the fast-build default, a page-wide regression here
(e.g. one section's custom CSS accidentally overriding a global) would not be caught by Step 6's
whole-page QA pass alone (that pass checks visual fidelity, not globals-reference usage); on
`--strict-sections`, likewise not caught by the per-section gate alone. If it fails, delegate the
fix to page-builder / style-refiner for the specific violating element(s), then re-run this step —
do not re-run the whole build/section loop.

Mark: `python3 scripts/checkpoint.py mark <page-slug> globals-verified --agent globals-verifier`

### Step 8 — Full-page QA

**Fast-build default:** Step 6 already performed the whole-page QA pass (via
`elementor-fast-build-qa`) — this step is a no-op unless `--full-qa` was
explicitly passed, in which case run the deeper multi-category audit below in
addition (not instead of) Step 6's pass/fail verdict.

**`--strict-sections` path:** Step 6's per-section QA (moderate strictness,
≤5px at the qa_breakpoints.core widths) is the QA already performed — a
redundant full-page pass is not run unless `--full-qa` was passed.

If `--full-qa` was given:
```
Agent(visual-regression-auditor, "<page-slug>")
```
This runs the full multi-breakpoint, multi-category audit (`qa-visual-capture` + `qa-false-positive-
protocol` + `qa-html-report`). It **reports** bugs; it does not fix them. If it returns any
CRITICAL/MAJOR finding, stop and report the HTML report path — do not mark `qa-passed` until the
developer has reviewed it and either accepted or asked for fixes (which route back through
page-builder/style-refiner, then Step 8 re-runs).

Mark: `python3 scripts/checkpoint.py mark <page-slug> qa-passed --agent rp-build --note '<summary>'`

### Step 9 — Publish (staging-first)

The page was created as `status: "draft"` back in Step 5/6 (per `elementor-page-builder`'s own
`rp/create-page` default) — or, on the `html_zip` path, by `html-to-native-elementor`'s own Step 3,
which likewise ends on a draft. Either way it has been buildable and QA-able this whole time without
ever being publicly reachable. **Staging-first is the default; direct-to-live is an explicit opt-in.**

- **Default (no `--publish-live` flag):** stop here. Report:
  ```
  rp-build: page is ready — <page-slug> is a DRAFT at <edit_url>. Review it, then either:
    - dispatch rp/update-page {page_id: <id>, status: "publish"} yourself, or
    - re-run with --publish-live to have this command publish it after your explicit confirmation.
  ```
  Do not dispatch `rp/update-page` with `status: "publish"` unless the developer has explicitly
  asked for it in this turn or via `--publish-live`.
- **If `--publish-live` was given:** ask for one explicit confirmation ("Publish `<page-slug>` live
  now? This makes it publicly reachable at `<permalink>`.") before dispatching
  `rp/update-page { page_id: <id>, status: "publish" }`. Never publish without that confirmation,
  even with the flag present — the flag opts the developer INTO being asked, it does not bypass the
  ask itself.

### Done

Print a one-line summary:
```
rp-build: COMPLETE — <page-slug> — N sections built, globals verified, QA passed, <draft|published>.
```

---

## Builder = `gutenberg`

The Gutenberg pipeline is agent-by-agent, like Elementor's, not a self-orchestrating agent like
ACF's. Two real gaps vs. Elementor, stated once here rather than at every step: **no
fingerprint-veto gate** exists (block-type correctness relies on careful ladder application only),
and **no `gutenberg-section-orchestrator` skill or `gutenberg-style-refiner` agent** exist — the
per-section loop below is driven directly by this command, not delegated to a skill the way
Elementor's Step 6 delegates to `elementor-section-orchestrator`. Also: **only `input_mode:
"prompt"` works** — there is no Figma/screenshot extractor, so there is no Step 1/2/3 extraction-
and-validate phase the way Elementor has; the plan is authored directly from the developer's
description inside Step 1 below.

### Step 0 — Resume check

`gutenberg-planner`/`gutenberg-foundation-builder`/`gutenberg-page-builder` have no
`scripts/checkpoint.py`-style shared resume file yet (that mechanism is Elementor/ACF-specific). Check
for existing progress directly: if `pages/<page-slug>/plan.md` exists, ask the developer whether to
resume (skip to the first section not yet built) or re-plan from scratch. If theme.json already has
the presets `plan.md` references (check via `rp/gutenberg-manage-theme-json` `action: "read"`),
Step 2 (Foundation) may already be satisfied — confirm before re-running it.

### Step 1 — Plan

```
Agent(gutenberg-planner, "<page-slug>")
```

**Gate — developer approval, per section**, exactly like Elementor's Step 4: the planner walks
each section and **waits for confirmation** before the next. Since no extractor exists, the planner
will ask the developer to describe the page directly (prompt mode) — relay its questions and wait,
do not answer on the developer's behalf. Once every section is confirmed, the planner writes
`plan.md` and records `gutenberg.input_mode: "prompt"` in `project-config.json`.

### Step 2 — Foundation (theme.json + Global Styles)

```
Agent(gutenberg-foundation-builder, "<page-slug>")
```

**Gate:** foundation-builder must print `gutenberg-foundation-builder: PHASE_1_COMPLETE —
<page-slug>` (or the explicit content-only-mode SKIPPING line, if `gutenberg.fse_mode:
"content-only"` — that is a normal successful outcome, not a failure, treat it as clearing this
gate too). If it instead prints a `BLOCKED` line, stop — report the exact step and iteration count,
and the artifacts path it saved.

### Step 3 — Section build loop

There is no orchestrator skill to delegate to (unlike Elementor's Step 6) — drive the loop directly.
For each section in `plan.md`, in order:

```
Agent(gutenberg-page-builder, "<page-slug> --section <id>")
```

**Gate, per section:** the page-builder's own Step 5 (`rp/gutenberg-validate-blocks` post-write —
`valid: true`) and Step 6 (`gutenberg-globals-enforcer --phase 2` — 0 violations) must both pass
before moving to the next section. If either fails after the page-builder's own fix/rollback
attempt, stop — report which section, which gate, and the exact error/violation. There is no
`style-refiner` to delegate a fix-and-retry loop to (unlike Elementor) — a stuck failure here is a
manual-intervention stop, not an automatic-retry step.

### Step 4 — Whole-page check

No Gutenberg-specific whole-page QA gate exists (unlike Elementor's Step 7
`elementor-globals-verifier`) — the closest available check is re-running
`gutenberg-globals-enforcer --phase 2` once more across the whole page (not just the
most-recently-built section) to catch a cross-section regression (e.g. a later section's
non-preset value accidentally matching an earlier section's expectation). If `--full-qa` was
passed, also run `Agent(visual-regression-auditor, "<page-slug>")` — it reports, it does not fix;
route any finding back through `gutenberg-page-builder` for the specific section, then re-run this
step.

### Step 5 — Publish (staging-first)

Same convention as Elementor/ACF — the page was created as `status: "draft"` inside
`gutenberg-page-builder`'s own `rp/create-page`/`rp/build-page` call. Default: stop and report the
draft edit URL, same message shape as Elementor's Step 9. With `--publish-live`: ask for one
explicit confirmation before dispatching `rp/update-page {page_id, status: "publish"}`. Never
publish without that confirmation, flag or not.

### Done

```
rp-build: COMPLETE (Gutenberg) — <page-slug> — N sections built, phase-2 enforcer clean, <draft|published>.
```

---

## Builder = anything else (not `acf`, `elementor`, or `gutenberg`)

Stop immediately — do not guess a pipeline. If `project-config.json` has an unrecognized
`project.builder` value, tell the developer plainly: *"`project.builder` is '<value>' but there is
no build pipeline for it (only 'acf', 'elementor', and 'gutenberg' are implemented). Correct it in
project-config.json and re-run."* Never fall through to any of the three branches above on an
unrecognized value — that would silently run the wrong pipeline against a page it wasn't planned
for.

---

## Stopping rules (apply to all builders)

- **Never** skip a failing gate to "keep going" — every gate exists because a later step depends on
  its precondition being true. A partial success reported as a full success is worse than a clean
  stop with an exact reason.
- **Never** re-run a step that already passed just because a later step failed, unless that later
  step's own failure artifacts explicitly point back to it (e.g. Step 7's globals-verifier failing
  because Step 5's kit globals were wrong — then Step 5 needs the fix, not a re-run of Step 6's
  section loop, which built correctly against what was in the kit at the time).
- **Never** bypass a developer-confirmation gate (the ACF dedup plan, the Elementor or Gutenberg
  `plan.md` approval, any `⚠`-marked destructive-ability confirmation). This command sequences
  agents; it does not remove the human checkpoints those agents already require.
- On any stop, print the exact gate name, the reason, and the artifact path (if any) so the
  developer can fix it and re-run `/rp-build <page-slug>` — which resumes from Step 0's checkpoint
  read (ACF/Elementor) or its own `plan.md`/theme.json existence check (Gutenberg, which has no
  shared `scripts/checkpoint.py` state yet) rather than starting over.