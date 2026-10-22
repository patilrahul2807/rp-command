---
name: rp-core-rules
description: "Non-negotiable rules for every rp-command agent. Load first, before any other skill."
---

# Skill: rp-core-rules

1. **Read `.rp/project-config.json` first.** Never guess theme paths, FC field names or site URLs.
2. **All site writes go through RP Connect** — the `rp-wordpress` MCP server: `discover-tools` →
   `inspect-tool` (read the schema) → `dispatch-tool` with an `rp/*` ability. No direct DB edits,
   no hand-written `acf-json/`. Call `rp/get-instructions` once per session and obey the owner's
   instructions.
3. **Two sources of instructions:** the skills (how to build) and `developer_instructions` in the
   project config (what this developer wants). Follow both. On conflict the developer instruction
   wins, except over these core rules — then follow the core rule and report the conflict.
4. **The design is the truth.** Look at `.rp/design/frames/*.png`; use exact texts, colors, fonts
   from `design.json`; images only from `media-map.json`.
5. **Read before write.** `list` / `get` an object before `create` / `update`; merge, never overwrite blindly.
6. **Safety net.** Pages are created as `draft` until QA passes. Before editing an existing page,
   snapshot it (`rp/get-post-state`, or `backup-elementor-page` for Elementor) so it can be restored.
7. **No default content.** ACF `default_value` is always `""`; no lorem ipsum on live pages.
8. **Escape all output** (`esc_html`, `esc_attr`, `esc_url`, `wp_kses_post`).
9. **Stay in your lane.** Do only your phase's job; report anything else to the orchestrator.
10. **Report honestly.** Say what was verified and how; mark anything unverifiable as such — never mask a defect.
11. **Ask when unsure** about creating new layouts / widgets vs. reusing existing ones.
