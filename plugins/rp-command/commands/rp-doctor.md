---
description: Verify the RP Connect connection and report what the site has installed
---

# /rp-doctor

Check the `rp-wordpress` MCP connection and report the site's readiness. Read-only — change nothing.

## Steps

1. **MCP server present?** Look for tools from the `rp-wordpress` MCP server
   (`discover-tools`, `inspect-tool`, `dispatch-tool`). If none:
   - tell the user to run `/rp-command:rp-connect <site-url> <username> <app-password>`,
     then `/exit` and restart `claude`; stop here.

2. **Bridge works?** Call `discover-tools`. Count the `rp/*` abilities returned.
   An auth error means the Application Password is wrong or revoked → re-run `/rp-connect`.

3. **Site facts** (dispatch each through `dispatch-tool`; inspect the schema first if unsure):
   - `rp/get-instructions` — owner instructions for agents (keep them; `/rp-start` uses them)
   - `rp/get-site-context` — WP/PHP version, active theme
   - `rp/get-builder-info` — installed / active / version of Elementor, Gutenberg, Avada (Fusion Builder) and others
   - Is ACF Pro active? `rp/get-builder-info` does not cover ACF; check the active plugin list in
     the server instructions / site context for `advanced-custom-fields-pro`, or call
     `rp/acf-manage-field-groups` with `{"action":"list"}` — an "ACF not active" error means no.

4. **Media upload ready?** Check `~/.rp-command/connection.json` exists (do not print the password).
   If missing, `/rp-start` cannot upload design images → tell the user to re-run `/rp-connect`.

5. **Local tools:** `python --version` (or `python3`), `node --version`.

## Report

A short table:

| Check | Status |
|---|---|
| MCP connection | ✅ / ❌ |
| Abilities available | N |
| WordPress / PHP | x / y |
| Active theme | name |
| ACF Pro | active / installed-inactive / missing |
| Elementor (+ Pro) | … |
| Gutenberg (block theme?) | … |
| Avada + Fusion Builder | … |
| Media upload credentials | ✅ / ❌ |
| Python / Node | versions |

End with: "Ready — run `/rp-command:rp-start`" or the list of what to fix first.
