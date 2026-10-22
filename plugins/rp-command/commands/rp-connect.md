---
description: Connect Claude Code to a WordPress site running the RP Connect plugin
argument-hint: <site-url> <username> <app-password> [staging-user] [staging-password]
---

# /rp-connect

Connect this Claude Code install to the WordPress site in `$ARGUMENTS`.

Arguments, in order: `site-url`, `username`, `app-password` (WordPress Application Password —
it contains spaces, so the user may have pasted it as several words: everything after the
username up to an optional staging pair is the password). Optional `staging-user`
`staging-password` are only for staging sites protected by HTTP Basic-Auth.

If any required argument is missing, ask for it. Tell the user where to get it:
WordPress admin → **RP Connect → MCP Connect → RP Plugin** tab shows this exact command
with the URL, username and a freshly generated Application Password.

## Steps

1. Normalise `site-url`: add `https://` if missing, strip a trailing `/`.

2. Check the endpoint answers (any HTTP status other than a connection error is fine):
   `curl -s -o /dev/null -w "%{http_code}" <site-url>/wp-json/mcp/mcp-adapter-default-server`
   - connection error / DNS failure → stop and report.
   - `404` → RP Connect is not active on that site. Stop and tell the user to install and
     activate the RP Connect plugin first.

3. Register the MCP server (user scope, so it works in every project). Remove an old one first:
   ```
   claude mcp remove rp-wordpress --scope user
   claude mcp add rp-wordpress --scope user \
     -e WP_API_URL=<site-url>/wp-json/mcp/mcp-adapter-default-server \
     -e WP_API_USERNAME=<username> \
     -e "WP_API_PASSWORD=<app-password>" \
     -- npx -y @automattic/mcp-wordpress-remote@latest
   ```
   (The remove may fail if none exists — that is fine.) Requires Node.js (`npx`); if `npx` is
   missing, tell the user to install Node.js LTS and stop.

4. Save the connection for the media-upload script to `~/.rp-command/connection.json`
   (the user's home folder, never inside the project):
   ```json
   {"site_url": "<site-url>", "username": "<username>", "app_password": "<app-password>",
    "staging_user": "<staging-user or empty>", "staging_password": "<staging-password or empty>"}
   ```

5. Tell the user, in their language:
   - Connected to `<site-url>` as `<username>`.
   - Now type `/exit`, start `claude` again, then run `/rp-command:rp-doctor` to verify,
     then `/rp-command:rp-start` to build a site.

Never print the app password back in full; show only the last 4 characters.
