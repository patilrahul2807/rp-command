# rp-command

Claude Code plugin: Figma / XD / HTML → WordPress (ACF, Elementor, Gutenberg, Avada) build, QA and
maintenance agents. All site reads/writes go through the **RP Connect** bridge — the
`rp-wordpress` MCP server (`discover-tools` → `inspect-tool` → `dispatch-tool` with `rp/*` abilities).

## Layout

- `commands/` — `rp-connect`, `rp-doctor`, `rp-start` (entry point; it orchestrates)
- `agents/` — one subagent per pipeline phase (`acf-*`, `elementor-*`, `gutenberg-*`, `avada-*`, `figma-html-*`, `html-*`, `maint-*`, `qa`, `visual-regression-auditor`)
- `skills/` — knowledge loaded by agents; `rp-core-rules` and `rp-dispatch` are the backbone
- `scripts/` — `figma_extract.py`, `xd_extract.py`, `wp_upload_media.py` (stdlib-only Python)
- `hooks/`, `eval/` — reserved

## Rules

- `/rp-start` runs in the main session and dispatches agents; agents never dispatch agents.
- Every agent loads `rp-core-rules` first and follows `developer_instructions` from `.rp/project-config.json`.
- ACF fields: `default_value` is always `""`.
- Never claim a check passed unless it was actually run.
