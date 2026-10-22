# rp-command

Claude Code plugin that builds WordPress websites from a Figma or Adobe XD design, through the
**RP Connect** WordPress plugin. Builders: **ACF** (custom theme + Flexible Content),
**Elementor**, **Gutenberg** (block theme), **Avada**.

## Setup (once)

1. On the WordPress site: install and activate **RP Connect**. In *RP Connect → MCP Connect →
   RP Plugin* copy the commands shown there.
2. In Claude Code:
   ```
   /plugin marketplace add https://github.com/patilrahul2807/rp-command.git
   /plugin install rp-command@rp-command
   /reload-plugins
   /rp-command:rp-connect <site-url> <username> <app-password>
   /exit
   ```
3. Start `claude` again, then:
   ```
   /rp-command:rp-doctor
   ```

Needs Node.js (for `npx @automattic/mcp-wordpress-remote`) and Python 3 (design extraction scripts).

## Build a site

```
/rp-command:rp-start [developer instructions]
```

The command:

1. checks the connection and what is installed on the site (`rp/get-builder-info`, ACF Pro),
2. asks: builder (ACF / Elementor / Gutenberg / Avada), design source (Figma / XD / HTML /
   images), pages, developer instructions,
3. checks the required plugins/theme and tells you what to install if something is missing,
4. extracts the design — frames, texts, colors, fonts, images (`scripts/figma_extract.py`,
   `scripts/xd_extract.py`) — and uploads the images to the media library (`scripts/wp_upload_media.py`),
5. shows you the plan for approval,
6. dispatches the builder's agents in order (see `skills/rp-dispatch`), each following its skills
   **and** your developer instructions,
7. runs visual QA against the design frames and fixes failing sections (max 3 rounds),
8. reports page URLs, QA scores and anything left open.

Project state lives in `.rp/` in the folder you run it from, so `/rp-start` can resume.

| Command | What it does |
|---|---|
| `/rp-command:rp-connect` | registers the `rp-wordpress` MCP server and saves media-upload credentials to `~/.rp-command/connection.json` |
| `/rp-command:rp-doctor` | read-only health check |
| `/rp-command:rp-start` | the full build flow above |

## Figma / XD notes

- **Figma:** needs a personal access token (`FIGMA_TOKEN` or asked for during `/rp-start`).
- **XD:** pass the local `.xd` file **and** a folder of artboards exported as PNG
  (*File → Export → All Artboards*) — `.xd` files contain no rendered artboards.
