---
description: Connect this project to a client WordPress site's RP Connect MCP bridge (asks for username + application password, wires it up, and verifies).
argument-hint: "<site-url>  e.g. https://clientsite.com"
allowed-tools: Bash(claude mcp add:*), Bash(claude mcp list:*), Bash(claude mcp remove:*), Bash(curl:*), Bash(printf:*), Bash(base64:*), Bash(tr:*)
---

# Connect to a client site (RP Connect MCP bridge)

You are wiring **this project folder** to one client WordPress site that runs the **RP Connect**
WP plugin. Work carefully and **never print the application password back to the user**.

## Inputs


Site URL: `$1` — if empty, ask the user for it.
Normalise it: strip a trailing slash; if it has no scheme, assume `https://`. Confirm the
  normalised URL with the user before continuing.

Then ask the user (one message, plain language):

"Paste the WordPress **username** and the **Application Password** for `<site>`.Create the Application Password on the site under **Users → Profile → Application Passwords**.(It will look like `abcd efgh ijkl mnop` — paste it as shown; I'll handle the formatting.)"

Wait for their answer. Do not proceed without both values.

### Detect browser/password protection (don't ask unless it's there)

Some **staging** sites sit behind a **server-level HTTP Basic-Auth gate** (the browser
username/password popup — e.g. WP Engine / Kinsta / htpasswd "password protection"). That
gate occupies the standard `Authorization` header, so the WordPress Application Password
must travel in a fallback header instead. **Live/production sites almost never have this**,
so **detect it — do not ask the user unless it's actually present:**

```bash
# Unauthenticated probe of the site root. A server-level Basic-Auth gate answers with a
# "WWW-Authenticate: Basic" challenge; a normal WordPress site (live or staging) does not.
PROT_HDRS=$(curl -s -D - -o /dev/null --max-time 15 "<SITE_URL>/")
printf '%s\n' "$PROT_HDRS" | grep -iq '^www-authenticate: *basic' && echo PROTECTED || echo OPEN
```


**OPEN → regular flow (the default).** Do **not** mention or ask for browser credentials.
  Use the standard single-header wire-up below. This covers all live sites and unprotected
  staging.

**PROTECTED → staging behind a browser popup.** Only now, tell the user and ask:
  > "`<site>` is behind a browser username/password popup (staging password protection).
  > Paste that **browser username and password** too — it's separate from the WordPress login."

  Then build the gate token and use the two-header wire-up (requires RP Connect **v0.2.6+**,
  which reads the app password from `X-RP-Authorization`):
  ```bash
  GATE_B64=$(printf '%s' "BROWSER_USER:BROWSER_PASS" | base64 | tr -d '\n')
  ```

## Wire it up


The MCP endpoint is the **RP Connect server** (registered by the RP Connect WP plugin):
   `<site-url>/wp-json/mcp/rp-connect-server`

Build the Basic auth token. WordPress ignores the cosmetic spaces in an application password,
   so **remove spaces** from the password first, then base64-encode `username:password`. Use the
   command for the developer's OS (no Python required — `base64` ships on macOS/Linux, and Windows
   has a built-in PowerShell encoder):
   ```bash
   # macOS / Linux (and Git Bash on Windows)
   B64=$(printf '%s' "USERNAME:PASSWORD_NO_SPACES" | base64 | tr -d '\n')
   ```
   ```powershell
   # Windows PowerShell (run if base64 is unavailable)
   $B64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("USERNAME:PASSWORD_NO_SPACES"))
   ```
   (Substitute the real username and the de-spaced password. Do not echo `$B64` or the password.)

Register the server at **local scope** (private to this project, stored in your local Claude
   config — never committed to any repo). If a server named `rp-command` already exists for this
   project, remove it first so re-running `/rp-command` updates the credentials cleanly:
   ```bash
   # OPEN site (live, or unprotected staging) — the default:
   claude mcp remove rp-command 2>/dev/null || true
   claude mcp add --transport http --scope local rp-command \
     "<SITE_URL>/wp-json/mcp/rp-connect-server" \
     --header "Authorization: Basic $B64"
   ```
   Only for a **PROTECTED** site (detected above), put the gate credentials on
   `Authorization` (to pass the gate) and the WordPress app password on
   `X-RP-Authorization` (which RP Connect v0.2.6+ authenticates from):
   ```bash
   claude mcp remove rp-command 2>/dev/null || true
   claude mcp add --transport http --scope local rp-command \
     "<SITE_URL>/wp-json/mcp/rp-connect-server" \
     --header "Authorization: Basic $GATE_B64" \
     --header "X-RP-Authorization: Basic $B64"
   ```

## Verify the connection

Run a one-shot MCP `initialize` against the endpoint with the same Basic auth and report the
result (this does NOT depend on the MCP client picking up the new server yet):

```bash
curl -s -o rp-init.json -w '%{http_code}' \
  -H "Authorization: Basic $B64" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -X POST --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"rp-command","version":"1"}}}' \
  "<SITE_URL>/wp-json/mcp/rp-connect-server"
```
(Writes to `rp-init.json` in the current folder — a relative path that works on macOS, Linux,
and Windows alike. `curl` ships with macOS, Linux, and Windows 10+.)

If the site is behind browser protection, verify with the two-header form instead
(gate on `Authorization`, WordPress app password on `X-RP-Authorization`):
```bash
curl -s -o rp-init.json -w '%{http_code}' \
  -H "Authorization: Basic $GATE_B64" \
  -H "X-RP-Authorization: Basic $B64" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -X POST --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"rp-command","version":"1"}}}' \
  "<SITE_URL>/wp-json/mcp/rp-connect-server"
```

Interpret the HTTP code:

**200** → success. Read `rp-init.json` and report the `result.serverInfo.name`
  (expect "RP Connect"). Tell the user: **connected**, the `rp-command` MCP
  server is wired for this project, and they should **restart Claude Code / reload MCP servers**
  so the tools (`mcp__rp-command__*`) load. Then suggest running **`/rp-doctor`**.

**401** → the username/application password is wrong, or the RP Connect plugin requires a
  different user. Ask them to re-check the credentials and re-run `/rp-command`. **If the body
  of `rp-init.json` is an HTML login page (not JSON)**, the request was blocked by the site's
  **browser/password protection** before reaching WordPress — redo the wire-up with the
  `X-RP-Authorization` two-header form above (needs RP Connect v0.2.6+).

**404** → the endpoint isn't there. The RP Connect WP plugin may be inactive, or a standalone
  "MCP Adapter" plugin is conflicting. Ask them to confirm RP Connect is active on `<site>`.

**000 / connection error** → the site URL is unreachable (wrong URL, site down, or VPN needed).


## Rules


Never write the password or the Basic token into any file in the project or repo.
Use `local` scope only. Do not use `project` scope (that writes a committable `.mcp.json`).
Clean up the temp file when done: `rm -f rp-init.json` (on Windows PowerShell: `Remove-Item rp-init.json -ErrorAction SilentlyContinue`).
