---
description: Start a website build — asks the builder, checks plugins, extracts the Figma/XD design, then runs the agents
argument-hint: [developer instructions, optional]
---

# /rp-start

You are the **orchestrator** for an rp-command website build. You run in the main session and
dispatch the phase agents yourself with the Agent tool (subagents cannot dispatch other agents).

Developer instructions given with the command: `$ARGUMENTS`

Load the skills `rp-core-rules` and `rp-dispatch` now and follow them for the whole run.
Talk to the user in the language they use (Gujarati / Hindi / English).

---

## Phase 0 — Preflight (no questions yet)

1. Confirm the `rp-wordpress` MCP tools exist. If not: tell the user to run
   `/rp-command:rp-connect <site-url> <username> <app-password>`, `/exit`, restart, and stop.
2. Through the bridge (`discover-tools` → `inspect-tool` → `dispatch-tool`) call:
   `rp/get-instructions`, `rp/get-site-context`, `rp/get-builder-info`.
   Note the active theme, which builders are installed/active, and whether ACF Pro is active
   (see `/rp-doctor` step 3 for how to check ACF).
3. If `.rp/project-config.json` already exists in the current folder, show its summary and ask
   whether to **resume** it or **start a new project** (resume → jump to the first phase whose
   output is missing).

## Phase 1 — Questions

Ask with **AskUserQuestion** (one call, up to 4 questions; the user can always pick "Other"):

1. **Builder** — "Website kaya builder ma banavvi che?"
   options: `ACF (custom theme + Flexible Content)`, `Elementor`, `Gutenberg (block theme)`, `Avada`.
   Mark the one already active on the site (from Phase 0) as "(Recommended)" and put it first.
2. **Design source** — `Figma link`, `Adobe XD file (.xd)`, `HTML folder`, `Screenshots / images only`.
3. **Pages** — `All frames/artboards in the design`, `Only the frame in the link`, `I will list the pages`.
4. **Developer instructions** — `None`, `I will type them` (if the command already had
   `$ARGUMENTS`, show them and offer `Use these`, `Add more`).

Then ask in plain text for anything still missing — one message, all at once:
- Figma: the file/frame URL, and a Figma token if `FIGMA_TOKEN` is not set
  (Figma → Settings → Security → Personal access tokens, read-only file content).
  If the Figma MCP tools are available in this session, they may be used instead of the token.
- XD: the full path of the `.xd` file, and (strongly recommended) a folder of artboard PNGs
  exported from XD (*File → Export → All Artboards → PNG*). XD files do not contain rendered
  artboards, so without the PNGs visual QA is limited.
- HTML: the folder path.
- Page list, if they chose to list them.
- Typed developer instructions, if chosen.

## Phase 2 — Plugin / theme readiness

Required per builder:

| Builder | Needs active |
|---|---|
| ACF | ACF Pro; a custom theme the agents may write to (`rp/update-theme-file`, child or parent scope) |
| Elementor | Elementor (Elementor Pro if the design needs theme-builder header/footer, forms, popups) |
| Gutenberg | WordPress 6.4+, a block theme active (agents create one if the user agrees) |
| Avada | Avada theme + Fusion Builder + Fusion Core |

For each missing item, tell the user exactly what to install. Installing and activating plugins
is **not** available over MCP (RP Connect withholds those abilities), and ACF Pro / Elementor Pro /
Avada are paid, so the user installs them in wp-admin. Ask with AskUserQuestion:
`I installed it — check again` / `Continue without it` / `Change builder`.
On "check again" re-run `rp/get-builder-info` (and the ACF check). Do not continue a pipeline
whose required plugin is missing unless the user explicitly chose to.

## Phase 3 — Project config

Write `.rp/project-config.json` in the current folder:

```json
{
  "site": {"url": "...", "theme": "...", "wp_version": "..."},
  "builder": "acf | elementor | gutenberg | avada",
  "design": {"source": "figma | xd | html | images", "input": "<url or path>", "frames_dir": "<path or null>"},
  "pages": ["Home", "About"],
  "developer_instructions": "<verbatim text, or empty>",
  "owner_instructions": "<from rp/get-instructions, or empty>",
  "theme": {"flexible_content_field": "page_builder", "existing_fc_layouts": [], "scope": "child"},
  "created": "<date>"
}
```

Keep `developer_instructions` verbatim — every agent reads it. Add `.rp/` to `.gitignore` if the
folder is a git repo.

## Phase 4 — Design extraction

The scripts live in this plugin's `scripts/` folder (`${CLAUDE_PLUGIN_ROOT}/scripts`; if that
variable is not expanded, find `figma_extract.py` under `~/.claude/plugins`). Use `python` or `python3`.

- **Figma:** `python <scripts>/figma_extract.py "<url>" .rp/design --token <token>`
  (or set `FIGMA_TOKEN`). Produces rendered frames, image fills, designer exports.
- **XD:** `python <scripts>/xd_extract.py "<file.xd>" .rp/design --frames-dir "<png folder>"`
- **HTML:** dispatch `html-project-extractor`, output to `.rp/design`.
- **Images only:** copy them to `.rp/design/frames/` and write a minimal `design.json` with one frame per image.

Then:
1. Read `.rp/design/design.json` summary and **look at** every `frames/*.png`.
2. Tell the user what was found: frames/pages, number of images, main colors and fonts.
   Ask them to confirm the frame → page mapping (frame names are often not page names).
3. Upload images: `python <scripts>/wp_upload_media.py .rp/design` → `.rp/design/media-map.json`.
   Report how many uploaded, any failures (401/403 → re-run `/rp-connect`), and `svg_pending`
   (SVGs are uploaded later by the builder agent, e.g. `rp/elementor-upload-svg`, or inlined).

## Phase 5 — Build (dispatch agents)

Follow the phase order for the chosen builder in the `rp-dispatch` skill. For every dispatch,
the Agent prompt must contain:

- the phase name and what to produce,
- input paths (`.rp/project-config.json`, `.rp/design/design.json`, `.rp/design/frames/`,
  `.rp/design/media-map.json`, plus the previous phase's output file),
- the output path (`.rp/phases/<nn>-<agent>.md` for reports, `.rp/plan.json` for the plan),
- the developer instructions **verbatim**,
- acceptance criteria.

Run independent agents in parallel (one message, several Agent calls) only where `rp-dispatch`
marks them parallel; otherwise sequentially. After each agent, read its report; if it reports a
blocker, stop and ask the user.

**Gate after planning:** show the user the plan (pages → sections → layouts/widgets, reuse vs.
new) and get approval with AskUserQuestion before any site write.

## Phase 6 — QA loop

Dispatch the pipeline's QA agent per page (see `rp-dispatch`). For failing sections dispatch
the targeted fixer, then QA again — at most 3 rounds per section (`section-qa-loop`).
Treat suspected false positives with `qa-false-positive-protocol`.

## Phase 7 — Report

Tell the user:
- pages built, each with its edit URL and live/preview URL,
- QA score per page and any sections still failing (with reason),
- anything skipped, and every place a developer instruction overrode a skill default,
- next step suggestions (e.g. menus, SEO via `maint-yoast-seo`).

Update `.rp/project-config.json` with `"status"` and the page ids so `/rp-start` can resume.
