---
description: One-command end-to-end build for a single page — chains extraction, validation, planning, foundation, section build, verification, QA, and checkpointing, stopping at the first failing gate with a clear reason.
argument-hint: <page-slug> [--full-qa] [--publish-live] [--strict-sections]
allowed-tools: Read, Glob, Grep, Bash(python:*), Bash(python3:*), Bash(claude mcp list:*), Bash(claude mcp add:*), Agent, mcp__rp-wordpress
---

# RP — one-command end-to-end build

`/rp-build <page-slug>` chains the pipeline for one page, using the **existing hard gates** —
this command does not invent a new build path, a new validation rule, or a new ability. It only
sequences the same steps a developer would otherwise run one agent at a time, and stops at the
first gate that fails instead of pushing forward on a broken foundation.

**The manual per-agent path stays available for debugging** — nothing here disables invoking any
agent individually; this command is a convenience wrapper, not a replacement pipeline.

Arguments: `$ARGUMENTS`

Paths used below:
- Project config: `.rp/project-config.json` (written by `/rp-command:rp-start`)
- Design: `.rp/design/design.json`, `.rp/design/frames/`, `.rp/design/media-map.json`
- Scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/` (written `<scripts>` below; if the variable is not
  expanded, find `checkpoint.py` under `~/.claude/plugins`). Use `python` or `python3`.
- Checkpoints: `python <scripts>/checkpoint.py read|mark|reset|page-can-start <page-slug> …`
- Agents never dispatch agents — this command (main session) dispatches every `Agent(...)` below.
  Every dispatch prompt follows the template in the `rp-dispatch` skill and carries
  `developer_instructions` from the config **verbatim**.

**`--strict-sections` (Elementor only):** use the strict per-section pipeline (per-section
build→enforce→QA→refine→re-QA loop via `elementor-strict-planner` + `elementor-strict-section-builder`,
following the `elementor-section-orchestration` skill) instead of the default whole-page
single-dispatch fast-build pipeline (`elementor-fast-build-qa` skill). Use when a design has
unusually high per-section risk, or when debugging a fast-build QA-blocked page section-by-section.

**`--strict-sections` is rejected whenever `design.source == "html"`, unconditionally — no
flag combination makes it valid.** `elementor-strict-planner` / `elementor-strict-section-builder`
hard-require a real extracted design (`.rp/design/design.json` with frames and frame PNGs) that no
HTML route produces. Before Step 1 runs, check `design.source == "html"` AND `--strict-sections`
was passed; if both are true, STOP and report: "`--strict-sections` is Figma/XD-only — this
project's design source is `html`, which has no design extraction to walk section-by-section.
HTML→Elementor always runs `html-to-native-elementor`, which already gates section-by-section on
its own." Do not let this combination reach `elementor-strict-planner` /
`elementor-strict-section-builder` under any circumstance.

**HTML→Elementor has exactly ONE route — no flags, no rollout marker.** When
`builder == "elementor"` AND `design.source == "html"`, the build is
`Agent(html-to-native-elementor, …)` and nothing else. There is no recipe-first alternative and no
measurement-first alternative to choose between, so there is no flag to choose with and no default
to compute. See the Elementor Step 1 `html` branch below.

If `--html-fidelity` or `--html-fast` is passed, do **not** fail the build: say
"`--html-fidelity`/`--html-fast` do not exist — HTML→Elementor always runs
`html-to-native-elementor`", then continue on that single route.

---

## Preconditions (run before anything below)

0. **Playwright MCP gate (HARD GATE).** This command runs Playwright-driven verification and QA
   (`mcp__playwright__browser_*`) at multiple steps. Before anything else, confirm it is connected:
   run `claude mcp list` and check a `playwright` server is listed with status `✔ Connected`, **and**
   that the tool `mcp__playwright__browser_navigate` is available this session.
   - **If the `playwright` server is absent entirely** → auto-install it with
     `claude mcp add playwright --scope user -- npx @playwright/mcp@latest`, then **STOP** — its
     tools cannot load until Claude Code is restarted, so this build cannot continue this session.
     On success, tell the developer: "✅ Playwright MCP installed — restart Claude Code (or reload
     MCP servers), run `/rp-command:rp-doctor` to confirm, then re-run `/rp-command:rp-build`."
     On failure, report the raw error and the manual command.
   - **If it is listed but not `✔ Connected`, or its tools aren't loaded** → do not re-add it;
     **stop** and tell the developer to fix/reload it and re-run.
   (`/rp-build` can run warm, without `/rp-start` re-running this session, so it must re-check
   rather than assume.)

1. If the `rp-wordpress` MCP tools (`discover-tools`, `inspect-tool`, `dispatch-tool`) are not
   available, tell the developer to run `/rp-command:rp-connect <site-url> <username> <app-password>`,
   restart, then `/rp-command:rp-doctor`, and stop.

2. **Proactively verify the connection is actually healthy — do not assume tool availability means
   the credentials still work.** Call the bridge's `discover-tools` once, live (this is the same
   call the pipeline needs first anyway, so it adds no extra round-trip — it just moves that first
   call here, before anything else). If it fails, diagnose it the same way `/rp-doctor` does
   (401 → stale/revoked Application Password, re-run `/rp-connect`; 404 → RP Connect deactivated
   or wrong URL; connection error → site unreachable) and **stop before any build step runs**.
   **If it succeeds, WRITE the result to `.rp/cache/abilities.json`** (with an added `cached_at`
   ISO-8601 timestamp) — every agent dispatched below runs as a SEPARATE subagent with no shared
   memory of this call; tell each one in its dispatch prompt to read this cache instead of
   re-discovering live.

3. Confirm the **`/rp-start`** discovery gate has run — `.rp/project-config.json` exists with
   `builder`, `design.source`, `design.input`, `pages` and `site` resolved. `/rp-build` never
   substitutes for the discovery gate. If any is missing, stop and run `/rp-command:rp-start` first.

4. **Page order gate:** `python <scripts>/checkpoint.py page-can-start <page-slug>`.
   `CAN_START=no BLOCKED_BY=<slug>` → stop: an earlier page is not approved yet; report which.

5. Read `.rp/project-config.json` and branch on `builder` — the four pipelines below are genuinely
   different; do not try to force one code path to cover more than one.

Throughout: after every step that passes its gate, run
`python <scripts>/checkpoint.py mark <page-slug> <phase> done` with the phase named in the step.
On a failed gate: `… mark <page-slug> <phase> failed --note "<reason>"`, then stop.

---

## Builder = `acf`

### `design.source` = `figma` / `xd` / `images`

Agents cannot dispatch agents, so this command sequences the ACF phases itself (the order from
`rp-dispatch` → ACF). Start at `NEXT_RECOMMENDED` from `checkpoint.py read <page-slug>`.

1. **design-extracted** — `.rp/design/design.json` exists and has a frame for this page; if not,
   run the extractor exactly as `/rp-start` Phase 4 does (Figma / XD script), then upload media.
2. **extraction-validated** — GATE: the page's frame has a PNG in `frames/`, `media-map.json`
   has no `failed` uploads, every image referenced by the frame has an attachment id.
3. **sections-analyzed** — `Agent(acf-section-analyzer, "<page-slug>")` → `.rp/specs/<page-slug>/*.json`.
4. **planned** — `Agent(acf-planner, "<page-slug>")` → `.rp/plan.json` (reuse vs. new layouts).
5. **plan-approved** — GATE (developer): show the layout list, reuse verdicts and new fields;
   do not continue without approval. Corrections go back to `acf-planner`, never hand-edits.
6. **theme-setup** — `Agent(acf-theme-setup)` (skip with `skipped` if the theme and Theme Settings
   options page already exist from an earlier page).
7. **fields-created** — `Agent(acf-backend)` → `Agent(acf-field-creator, "<page-slug>")`.
8. **templates-built** — `Agent(acf-frontend-developer, "<page-slug>")` ∥ `Agent(acf-scss-writer, "<page-slug>")`,
   then `Agent(acf-template-builder)`.
9. **theme-pushed** — push changed theme files with `rp/update-theme-file`; compile SCSS locally
   (`npx sass`) and push the CSS. Each push returns a `backup_id` — record them in the checkpoint note.
10. **page-assembled** — `Agent(acf-page-assembler, "<page-slug>")`: page created as `status: "draft"`.
11. **qa-passed** — `Agent(acf-visual-comparator, "<page-slug>")`; failing layouts →
    `acf-frontend-developer` / `acf-scss-writer` scoped to them → re-push → re-QA.
    **Capped at 3 iterations** — still failing → report blocked with the open issues.
12. **checkpointed** — see "Finish" below.

### `design.source` = `html` — the spec/transplant pipeline

`acf-*` design agents stay Figma/XD-only. Sequence — each step gated; on the first failed gate
STOP and report:

1. **html-extracted** — branch on `html_source.status` in the config:
   - missing / `pending-analysis` → `Agent(html-project-extractor, "start")` → relay its
     page-inventory report and STOP (the developer confirms the homepage next turn).
   - `pages-detected` → relay the inventory, get the homepage confirmation, then
     `Agent(html-project-extractor, "--confirm-homepage <slug>")`.
   - `homepage-confirmed` → continue.
   For ACF the extractor's per-page blueprint generation is skipped (`html-parser` owns section
   discovery); only the project-wide artifacts are required:
   `.rp/source/html/{manifest,pages,tokens,assets,shared-regions}.json` + `.rp/source/html/_extracted/`.
2. **reference-captured** — `Agent(html-visual-reference-builder, "<page-slug>")` (reference
   screenshots for QA).
3. **spec-parsed** — `Agent(html-parser, "<page-slug>")`: writes `.rp/spec/site-spec.json` +
   byte-verbatim `.rp/spec/fragments/` + `.rp/docs/spec-review.md`.
4. **spec-approved** — GATE (developer): spec review summary + open questions; corrections are
   applied by re-running the parser, never by hand-editing the spec.
5. **acf-planned** — `Agent(html-acf-planner)`: classifies every section (Global / Local / Options /
   CPT) with reuse verdicts → `.rp/spec/acf-plan.json` + `.rp/docs/acf-review-table.md`.
6. **plan-approved** — GATE (developer): classification sign-off; the planner marks the plan
   `approved: true`.
7. **theme-built** (local, no bridge) — `Agent(html-acf-builder)` → `Agent(html-php-writer)` →
   `Agent(html-theme-assembler)`. Each validates its own output; relay failures, never patch inline.
8. **deployed** — `Agent(html-deployer)` with `deploy_mode`, `pages`, `publish` from the config
   (if absent, ask now, once). Idempotent; resumes from `.rp/deploy-state.json`.
9. **qa-passed** — `Agent(html-qa, "<page-slug>")`: pixel gate first, diff-only analysis, DOM
   false-positive rescue, ranked root causes; route HIGH/MED to `html-php-writer` /
   `html-theme-assembler`, re-deploy deltas via `html-deployer`, re-QA. **Capped at 3 iterations.**
10. **audited** — `Agent(html-fingerprint-auditor)` ONCE → `.rp/qa/accuracy/<run>/` scorecard +
    `causes-viewer.html` (the designer handoff). It never fixes and never loops.
11. **checkpointed** — see "Finish".

The spec is the source of truth: downstream agents never re-read raw HTML; fragments are
transplanted byte-verbatim, never re-typed. All site writes go through the bridge; nothing here
calls raw REST or `wp` CLI, and nothing deletes on the client site.

---

## Builder = `elementor`

The pipeline is explicit agent-by-agent, each with its own hard gate. Run the steps **in order**,
checking the stated gate before advancing. On the first gate that fails, **stop immediately** and
report exactly which gate failed and why — do not skip ahead or silently retry a different step.

### Step 0 — Resume check

```
python <scripts>/checkpoint.py read <page-slug>
```

Read `NEXT_RECOMMENDED`. If it is not the first phase, this page was already partially built —
jump straight to the step matching `NEXT_RECOMMENDED` instead of starting over. `complete` →
report the page is already built and stop (suggest `checkpoint.py reset` to rebuild).

### Step 1 — Extraction (`design-extracted`)

- `design.source == "html"` → **the single HTML route:** `Agent(html-to-native-elementor, "<page-slug>")`
  (it unzips, confirms the homepage and gates section-by-section itself). Mark `html-native-built`,
  then jump to **Step 7**.
- `figma` / `xd` / `images` → ensure `.rp/design/design.json` has this page's frame; if not,
  run the extractor as `/rp-start` Phase 4 does, then `wp_upload_media.py`.

### Step 2 — Extraction validation (`extraction-validated`)

GATE: the frame has a PNG in `frames/`; `media-map.json` has no failed uploads; every image in the
frame resolves to an attachment id; texts are present (not empty). SVGs in `svg_pending` are allowed
(the builder uploads them with `rp/elementor-upload-svg`).

### Step 3 — Planning (`planned`, `plan-approved`)

- Default: `Agent(elementor-section-detector, "<page-slug>")` → `Agent(elementor-planner, "<page-slug>")`.
- `--strict-sections`: `Agent(elementor-strict-planner, "<page-slug>")` (one spec + acceptance
  criteria per section).
- GATE (developer): show sections → widgets → globals used; continue only on approval.

### Step 4 — Foundation (`foundation-built`)

`Agent(elementor-foundation-builder)` — Kit colors, typography, container width, breakpoints.
If an earlier page already built the foundation and the design tokens did not change, mark
`skipped`. GATE: `rp/elementor-get-global-settings` shows the planned globals.

### Step 5 — Build (`sections-built`)

Back up first if the page already exists (`rp/backup-elementor-page`).

- **Default (fast build):** `Agent(elementor-page-builder, "<page-slug>")` — whole page in a single
  dispatch, native widgets only, page `status: "draft"`. Then, only for sections the plan flagged,
  `Agent(elementor-overlap-gradient, "<page-slug> <sections>")`.
- **`--strict-sections`:** for each planned section in order:
  `Agent(elementor-strict-section-builder, "<page-slug> <section>")` → `Agent(elementor-globals-enforcer, "<section>")`
  → `Agent(qa, "<page-slug> <section>")` → on fail `Agent(elementor-style-refiner, "<section>")` → re-QA.
  Max 3 rounds per section (`section-qa-loop`); a section still failing → stop, report blocked.

GATE: every widget passed `rp/elementor-validate-widget`; the page's element tree has one top-level
container per planned section.

### Step 6 — Globals (`globals-verified`)

`Agent(elementor-globals-enforcer, "<page-slug>")` → `Agent(elementor-globals-verifier, "<page-slug>")`.
GATE: zero hard-coded colors / fonts left (the verifier's report lists none).

### Step 7 — Page verification (`page-verified`)

With Playwright: open the page preview URL (draft preview, logged in) at desktop / tablet / mobile.
GATE: HTTP 200, no PHP warnings/notices on the page, no console errors from the page's own code,
every planned section rendered (count matches the plan), no broken images.

### Step 8 — QA (`qa-passed`)

`Agent(qa, "<page-slug>")` following `elementor-fast-build-qa` (strict mode: section QA already ran;
this is the whole-page pass). With `--full-qa` also `Agent(visual-regression-auditor, "<page-slug>")`
and the `qa-wp-checklist`.
Failing sections → `Agent(elementor-targeted-fixer, "<page-slug> <sections>")` (only those sections)
→ re-QA. Treat suspected false positives with `qa-false-positive-protocol`.
**Capped at 3 iterations** — still failing → report blocked with the open issues.

### Step 9 — Checkpoint (`checkpointed`)

See "Finish".

---

## Builder = `gutenberg`

Same gate discipline as Elementor (resume with `checkpoint.py read`, stop at the first failure).
No `--strict-sections`, no style-refiner.

1. **design-extracted / extraction-validated** — as Elementor Steps 1–2 (`design.source == "html"`:
   run `html-project-extractor` → `html-parser` first and use the spec as the design).
2. **planned** — `Agent(gutenberg-planner, "<page-slug>")`; **plan-approved** — GATE (developer).
3. **theme-json-built** — `Agent(gutenberg-foundation-builder)` (`rp/gutenberg-manage-theme-json`);
   `skipped` if unchanged since an earlier page.
4. **theme-built** — `Agent(gutenberg-theme-builder)` ∥ `Agent(gutenberg-block-author)` (only if the
   plan has custom blocks).
5. **page-built** — `Agent(gutenberg-page-builder, "<page-slug>")`, page `draft`. GATE:
   `rp/gutenberg-validate-blocks` reports no invalid blocks.
6. **globals-enforced** — `Agent(gutenberg-globals-enforcer, "<page-slug>")`.
7. **page-verified** — as Elementor Step 7.
8. **qa-passed** — `Agent(qa, "<page-slug>")` (+ `--full-qa` extras) → fixes by
   `gutenberg-page-builder` scoped to failing sections → re-QA, max 3.
9. **checkpointed** — see "Finish".

---

## Builder = `avada`

1. **design-extracted / extraction-validated** — as Elementor Steps 1–2.
2. **planned** — `Agent(avada-planner, "<page-slug>")`; **plan-approved** — GATE (developer).
3. **globals-built** — `Agent(avada-foundation-builder)` (`rp/avada-manage-global-options`);
   `skipped` if unchanged since an earlier page.
4. **page-built** — `Agent(avada-page-builder, "<page-slug>")`, page `draft`; every element passed
   `rp/avada-validate-element`.
5. **cache-cleared** — `rp/avada-clear-cache` for the page.
6. **page-verified** — as Elementor Step 7.
7. **qa-passed** — `Agent(qa, "<page-slug>")` (+ `--full-qa` extras) → `Agent(avada-targeted-fixer, …)`
   → re-QA, max 3.
8. **checkpointed** — see "Finish".

---

## Finish (all builders)

**Staging-first:** every pipeline above creates the page as `status: "draft"`.

- Without `--publish-live`: report the edit URL and preview URL and stop. The page stays a draft.
- With `--publish-live`: show the QA result and ask the developer to confirm (AskUserQuestion:
  `Publish now` / `Keep as draft`). Only on `Publish now` set the page to `publish` through the
  bridge, then re-run the Step 7 page verification on the live URL.

Then:
1. On QA pass set `approvals.pages.<page-slug>.status = "approved"` in `.rp/project-config.json`
   (this is what `checkpoint.py page-can-start` reads for the next page).
2. `python <scripts>/checkpoint.py mark <page-slug> checkpointed done`.
3. Append the build to `.rp/session.md` (date, page, builder, flags, QA score, page id, URLs,
   backups, developer-instruction overrides) and update `.rp/design-system/page-memory.json`
   (sections, layouts/widgets used, so the next page can reuse them).
4. Report to the developer: gates passed, QA score, URLs, anything skipped or still open, and the
   next page that can start.

If any agent reports a failure or aborts, relay its exact output and stop. Do not retry silently,
and never auto-answer a developer confirmation that an agent or gate asked for.
