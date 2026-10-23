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
starting over from Step 1. This is what makes ...
