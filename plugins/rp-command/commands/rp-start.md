---
description: Start (or resume) an RP WordPress project — runs the discovery gate first, before any build, so every build is based on real project facts, not assumptions. Design sources: Figma (URL or ZIP) or an HTML ZIP (option 3 — HTML to Elementor / HTML to ACF).
allowed-tools: Read, Glob, Write, Bash(ls:*), Bash(cat:*), Bash(claude mcp list:*), Bash(claude mcp add:*), mcp__rp-command__rp-bridge-discover-tools, mcp__rp-command__rp-bridge-inspect-tool, mcp__rp-command__rp-bridge-dispatch-tool
---
# RP — start here
This is the **first action** for any RP WordPress work. Run it before acting on a build
request. Its job is to recognise an existing project (and resume it) or set up a new one — so the
developer is never re-briefed, and a build never starts on guesses.
> Preconditions: this project must already be connected (`mcp__rp-command__*` tools available). If
> they are **not**, tell the developer to run **`/rp-command <site-url>`** then `/rp-doctor`, and stop.
> **Exception:** the **Figma to HTML** builder (Branch C below) needs no WordPress site or bridge
> connection at all — this precondition does not apply to it.
---
## Step −2 — Playwright MCP gate (HARD GATE — do this before anything else)
Every build pipeline this command routes into drives a real browser through the **Playwright MCP**
(`mcp__playwright__browser_*` tools) for screenshots, viewport resizing, and visual QA. Without it,
a build cannot verify what it produces. **Do not proceed past this step unless Playwright MCP is
connected.**
Check both:
1. Run `claude mcp list` and confirm a `playwright` server is listed with status `✔ Connected`.
2. Confirm the tool `mcp__playwright__browser_navigate` is actually available to you this session.
- **Both pass** → continue silently to Step −1.
- **Server absent from `claude mcp list`** → **auto-install it, then STOP** (a restart is required
  before its tools load — the build cannot continue this session regardless). Run:
  ```bash
  claude mcp add playwright npx @playwright/mcp@latest
  ```
  - **Install succeeds** → tell the developer:
    ```
    ✅ Playwright MCP installed. ⚠️ Restart required before it works.
    Restart Claude Code (or reload MCP servers), run /rp-doctor to confirm it comes up ✔ Connected,
    then run /rp-start again.
    ```
    **STOP here** — do not run the discovery gate, do not read `project-config.json`, do not route
    to any pipeline. The browser tools are not available in this session.
  - **Install fails** → report the raw error and give the manual command; **STOP**.
- **Server listed but not `✔ Connected`** (needs auth / unhealthy) → do **not** re-add it. Say the
  server is registered but its connection needs fixing, point the developer at `/rp-doctor` step
  2b, and **STOP**.
- **Server connected but `mcp__playwright__browser_navigate` not available** → its tools haven't
  loaded yet; tell the developer to **restart Claude Code (or reload MCP servers)** and re-run, and
  **STOP**.
---
## Step −1 — Warm or cold? (do this first)
Check the **current project folder** for `project-config.json`.
- **Found → WARM START.** Go to **§ Warm start** below. **Do NOT ask any discovery questions.**
- **Not found → COLD START.** Go to **§ Cold start** below.
---
## Warm start — resume an existing project
The project is already configured. Resume it without re-asking anything.
1. **Read local state** (developer's machine only — never the server):
   - `project-config.json` — the saved answers (`site_mode`, `builder`, `acf_present`, `acf_role`,
     `figma_source`, framework, breakpoints, fonts, …).
   - `design-system/*.json` if present — `page-memory.json`, `component-registry.json`,
     `acf-layout-registry.json`, `design-tokens.json` (what already exists).
   - `session.md` if present — the human-readable build log (what was built, when, by which agent).
2. **Drift check (cheap, existence-only):** dispatch `rp/list-pages` and reconcile against
   `page-memory.json`. If they disagree (e.g. a page was deleted/renamed in wp-admin), **flag it in
   one line** before doing anything else. This is a page-existence check only — it does NOT detect
   content changes on a page that still exists. Before the first *write* to any specific page this
   session, the `rp-dispatch` §1.4 item 6 **content**-drift check runs separately, right before
   that page's first write.
3. **Confirm in one line** — a sanity check, not re-discovery. For example:
   > "Found this project — **Elementor**, no ACF, homepage built 2026-06-18 (per `session.md`).
   >  What would you like to build next?"
   If the developer already stated the task, restate it and proceed.
4. **Route** straight to the right pipeline via the **`rp-dispatch`** skill, passing the loaded
   `builder` / `acf_role`. Reuse-first: check the registries and reuse existing components, fields,
   layouts, and media — never duplicate what already exists.
   - If the config has `input_mode: "html_zip"`, resume is **state-machine driven, never
     guessed**: read `html_source.status` (`pending-analysis` → extraction hasn't run;
     `pages-detected` → homepage awaits confirmation; `homepage-confirmed` → build can proceed)
     plus `approvals` and `python3 scripts/checkpoint.py` gates, then re-enter `/rp-build` at
     the first incomplete step. For `builder: "acf"` the per-stage artifacts double as evidence
     (spec on disk? `spec/acf-plan.json` approved? theme assembled? `deploy-state.json`
     present?) — but the config state machine is authoritative when they disagree.
> Warm start asks **zero** discovery questions. The only thing it asks is "what's next?" (and only
> if the developer hasn't already said).
---
## Cold start — a new folder
No config yet. Ask the gate question **first**, before anything else.
> **Skip-if-obvious rule:** never ask a question the developer's input has already answered.
> A Figma URL/ZIP handed over → Q3 is answered (option 1/2). An HTML zip in the folder or
> "convert this HTML" → this is a NEW project (Q1) with `input_mode: "html_zip"` (Q3 option 3) —
> only the **builder** question (Q2) still needs asking, plus a one-line confirmation of what
> was inferred. Confirm inferences; don't re-ask them.
### Q1 — Project type (always first)
> "Before we start — is this an **existing** WordPress project, a **new** one from scratch, or a
> **static Figma-to-HTML page** (no WordPress site at all)?"
Branch on the answer. **Figma to HTML** → skip straight to **Branch C** below — it needs none of
the WordPress-specific setup (bridge connection, ACF, Playwright-driven site verification) Branch
A/B assume.
### Branch A — NEW project
1. **Q2 — Builder:** "Which builder — **Elementor**, **ACF** (flexible-content theme), or
   **Gutenberg (block theme · FSE)**?"
   - Elementor / ACF → proceed as below.
   - **Gutenberg → proceed, with the real caveats stated up front (not a stop anymore):**
     "The Gutenberg pipeline (planner → foundation-builder → page-builder, Priority 12.1–12.3) is
     real and executable — but two things are worth knowing before you commit: (1) **only prompt-
     mode input works today** — describe the page in words; there's no Figma/screenshot extractor
     yet, so Q3 below is skipped for Gutenberg. (2) There's no fingerprint-veto gate (unlike
     Elementor's) and no whole-page QA/section-orchestrator yet — block-type correctness relies on
     careful ladder application, and you'll invoke `gutenberg-page-builder` per section yourself
     rather than one orchestrated pass. If that's fine, let's continue." Write
     `builder: "gutenberg"` to `project-config.json` and continue to Q4/Q5 below (skip Q3 — see its
     own note).
2. **Q3 — Design source** (Elementor/ACF only — Gutenberg has no extractor yet, skip straight to
   Q4/Q5 for it): ask exactly this, substituting the option-3 label for the chosen builder
   (`"HTML to Elementor"` when `builder = elementor`, `"HTML to ACF"` when `builder = acf`):
   > "How is the design provided?
   >
   > 1. Figma URL + token
   >    You'll give a Figma file/frame URL and a personal access token; extraction goes
   >    through the Figma API/MCP.
   > 2. Figma ZIP export
   >    You'll provide a local .fig ZIP export plus a full-page PNG; extraction is fully
   >    offline, zero API calls.
   > 3. HTML to Elementor / HTML to ACF
   >    Provide the HTML ZIP file in the project root. The agent will use the ZIP file as
   >    the source and automatically build all website pages from it.
   > 4. Type something
   >    Describe the design/requirements in your own words — a written-brief build with
   >    no Figma or HTML source."
   Record the answer as `project.input_mode`:
   - **1** → `input_mode: "figma_url"`, `figma_source: "url"` → continue to item 4 below (Figma
     hard gate) exactly as before.
   - **2** → `input_mode: "figma_zip"`, `figma_source: "zip"` → continue to item 4 below (Figma
     hard gate) exactly as before.
   - **3** → `input_mode: "html_zip"` (do **not** write `figma_source`). Look for exactly one
     `.zip` in the project root (`ls *.zip`, this command's own `allowed-tools` covers `ls`). Zero
     or more than one → ask the developer for the exact filename rather than guessing. Write
     `project-config.json` with:
     ```json
     {
       "html_source": {
         "archive_path": "./<the-zip-filename>",
         "status": "pending-analysis",
         "homepage_candidate": null,
         "homepage_confirmed": false
       },
       "approvals": { "page_inventory": { "status": "not-started" } }
     }
     ```
     Then tell the developer what happens next, per builder:
     - `builder = elementor` → "HTML-ZIP-to-Elementor is built by **one agent —
       `html-to-native-elementor`** — and there is no alternative route. It owns the whole job
       end to end: it unzips the archive itself, serves the original locally, derives the design
       system from the *rendered* source (palette, fonts, per-tag typography, container width and
       the template's own breakpoints) into the Elementor Kit, creates the page, then builds it
       section by section out of **native Elementor widgets only** — measuring the original,
       scoring each section against it at every breakpoint, and locking it at ≥98% before starting
       the next. Zero `html` widgets is a hard gate, so the result stays fully editable in the
       Elementor UI. Next step: this session will invoke
       `Agent(html-to-native-elementor, "<the-zip-filename>")`; if the archive holds several pages
       it will ask which one to build first, and the homepage guard stays in force until you
       confirm."
     - `builder = acf` → "HTML-ZIP-to-ACF runs shared HTML extraction (`html-project-extractor`
       — page inventory + homepage confirmation, same checkpoint as the Elementor path), then the
       spec/transplant pipeline: `html-parser` (verbatim spec + fragments, **spec review gate**)
       → `html-acf-planner` (**classification sign-off gate**) → `html-acf-builder` →
       `html-php-writer` → `html-theme-assembler` → `html-deployer` (bridge deploy) → `html-qa`
       (pixel-gated fix loop) → `html-fingerprint-auditor` (final accuracy report). Source markup
       is transplanted byte-verbatim — never re-typed."
     **Continue next — skip item 4 (the Figma hard gate is Figma-only).** After the brief finishes
     and hands off to `rp-dispatch`, the very first dispatched step depends on the builder:
     `builder = acf` → `Agent(html-project-extractor, "start")`; `builder = elementor` →
     `Agent(html-to-native-elementor, "<the-zip-filename>")`, which does its own unzipping and
     runs the page-inventory/homepage confirmation itself in its Step 1a. See `rp-dispatch` §0.5
     and `/rp-build`'s html_zip Step 1 for the exact sequencing.
     - **`builder = elementor`:** **always skip item 3 (Q4).** Never ask about ACF fields/CPTs when
       Elementor is the builder. Write `acf_present: false`, `acf_role: "none"` and go to item 5
       (brief). Elementor builds are native-widgets-only — ACF is not offered as a side option. If
       the developer wants ACF, they must choose the **ACF** builder at Q2, not Elementor.
     - **`builder = acf` + option 3:** skip Q4 (ACF builder sets `acf_r...
