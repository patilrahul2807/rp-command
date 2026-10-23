---
description: Check the RP Connect MCP connection for this project, report what abilities the connected site exposes, and diff against the last known-good ability contract.
allowed-tools: Bash(claude mcp list:*), Bash(claude mcp get:*), Bash(claude mcp add:*), mcp__rp-command__rp-bridge-discover-tools, Read, Write
---
# RP Connect connection doctor
Verify this project is correctly connected to a client site's RP Connect MCP bridge and report
its capabilities. Do the checks in order and stop at the first that fails, giving a clear fix.
## 1. Is the server registered?
```bash
claude mcp list
```
Confirm an `rp-command` server is listed. If it is **not**, tell the user to run
**`/rp-command <site-url>`** first, and stop.
## 2. Are the MCP tools loaded?
Check whether the tool `mcp__rp-command__rp-bridge-discover-tools` is available to you.
- If it is **not available** (but step 1 showed the server registered), the MCP client hasn't
  loaded it yet. Tell the user to **restart Claude Code (or reload MCP servers)** and run
  `/rp-doctor` again. Stop.
## 2b. Is the Playwright MCP connected? (REQUIRED for builds & QA)
Every build/QA pipeline in this plugin drives a real browser through the **Playwright MCP**
(`mcp__playwright__browser_*` tools — screenshots, viewport resizing, visual comparison). Without
it, `/rp-start`, `/rp-build`, and every visual-QA step will refuse to run. Check it here so the
developer learns it now, not mid-build.
Two checks, both must pass:
1. **Registered + connected.** In the `claude mcp list` output from step 1, look for a `playwright`
   server line and confirm its status is `✔ Connected` (not `! Needs authentication`, not a
   failed/✘ state, and not absent entirely).
2. **Tools loaded.** Confirm the tool `mcp__playwright__browser_navigate` (a representative browser
   tool) is actually available to you this session.
Report the result:
- **Both pass** → `✅ Playwright MCP connected — browser tools available.`
- **Server absent from `claude mcp list`** → **auto-install it, then tell the user to restart.**
  `/rp-doctor` is the plugin's setup/repair command, so it is the right place to fix this rather
  than just report it. Run:
  ```bash
  claude mcp add playwright npx @playwright/mcp@latest
  ```
  - **If the command succeeds** → tell the user:
    ```
    ✅ Playwright MCP installed (registered as `playwright`).
    ⚠️ Its browser tools are NOT loaded into this session yet — restart Claude Code (or reload MCP
    servers), then run /rp-doctor again to confirm it comes up ✔ Connected.
    ```
    The tools cannot load in the current session — a restart is mandatory before any build. Do not
    claim Playwright is ready this session; it isn't until after the restart.
  - **If the command fails** (e.g. `npx`/Node not installed, or the name is already taken) → report
    the raw error verbatim and give the manual fix. Do not retry blindly. If the failure is
    "already exists", that means the server is registered but wasn't in the `claude mcp list` output
    you read — re-run `claude mcp list` and treat it as the "listed but not connected" case below.
- **Server listed but not `✔ Connected`** (needs auth / failed health check) → do **not** re-add it
  (that won't fix a health problem and may error on the duplicate name). Tell the user the server is
  registered but unhealthy, and to fix that specific server's connection, then re-run `/rp-doctor`.
- **Server connected but `mcp__playwright__browser_navigate` not available** → the client hasn't
  loaded its tools yet; tell the user to **restart Claude Code (or reload MCP servers)** and re-run
  `/rp-doctor`.
This step may **install** Playwright, but it can never make it *usable this session* (a restart is
always required after an install). Carry the Playwright status into the final verdict (below);
continue the remaining checks either way so the developer gets the full picture in one pass. A build
cannot proceed while Playwright is anything other than ✅ connected **with tools loaded**.
## 2c. Local environment tools (env preflight)
Builds/QA shell out to local tools. Check each and report **available/missing individually** — a
missing tool is only fatal for the workflow that uses it, so report per-tool rather than failing the
whole doctor:
```bash
for t in node npx python3 php jq unzip; do
  command -v "$t" >/dev/null 2>&1 && echo "OK   $t -> $(command -v "$t")" || echo "MISS $t"
done
command -v sass >/dev/null 2>&1 && echo "OK   sass" || echo "MISS sass (ACF SCSS builds)"
( cd "${CLAUDE_PLUGIN_ROOT}/scripts" 2>/dev/null && npm ls fig-kiwi >/dev/null 2>&1 \
  && echo "OK   fig-kiwi (scripts/)" ) || echo "MISS fig-kiwi (cd scripts && npm install — local .fig only)"
```
Map each to the workflow that needs it:
- **node / npx** — Figma local extraction, Sass, image tooling.
- **python3** — `validate_spec.py`, `extraction_provenance.py`, `unit_normalize.py`, `visual_compare.py`, `validate_plugin_integrity.py`.
- **php** — the ACF code-review gate (`php -l`); only when `acf_code_gate: true`.
- **jq / unzip** — Figma ZIP handling.
- **sass** — ACF SCSS compilation.
- **fig-kiwi (scripts/)** — local `.fig` parsing (`parse-fig.mjs`); not needed for the Figma-URL path.
Pin dependency versions rather than fetching unspecified "latest" during a build (`scripts/package.json`
already pins the Node deps). Report each tool's status; do not hard-block the whole doctor on an optional miss.
## 2d. Fast-build pipeline smoke test (local-only, optional)
If `python3` is available (per 2c above), run the Elementor fast-build pipeline's own regression
test — this catches a broken recipe, compiler, or validator BEFORE a real build hits it, rather than
relying on someone remembering to run it manually:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tests/test_fast_build_smoke.py"
```
- **All pass** → `✅ Fast-build smoke test passed (N recipes, compiler, validator, checkpoint script).`
- **Any failure** → report the failing test name and assertion message verbatim; this means the
  recipe library, `compile_elementor_blueprint.py`, `validate_elementor_tree.py`, or
  `scripts/checkpoint.py` has a real regression — do not proceed to a build on this project until
  it's fixed (a broken recipe or compiler affects every future Elementor build, not just this one).
- Skip entirely (report `⚠️ Skipped — python3 not available`) if 2c already reported `python3`
  missing — don't fail the whole doctor run over an optional local check's own missing dependency.
## 2e. Plugin integrity check (static wiring validator, local-only, optional)
If `python3` is available (per 2c above), run the static wiring checker — this catches an
`Agent(...)` call whose target agent doesn't exist, a referenced skill/script that's missing, a
stale pre-plugin relative skills path, or a hardcoded kit ID/sample value left in an executable
instruction, all **before** a build hits it mid-run instead of at connect time:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_plugin_integrity.py" "${CLAUDE_PLUGIN_ROOT}"
```
- **Exit 0, no output beyond a clean summary** → `✅ Plugin integrity check passed (no broken Agent()/skill/script references).`
- **Exit 0 with WARN lines** → report them; these are non-fatal (e.g. a stale-looking pattern that
  may be intentional) but worth a developer's eye — do not block on them.
- **Exit 1 with ERROR lines** → report each verbatim (file + reason); this means a real agent/skill
  wiring defect exists in the plugin itself (independent of any specific site) — treat as a blocker
  for building until fixed, since it means some later Agent() dispatch is guaranteed to fail.
- Skip entirely (report `⚠️ Skipped — python3 not available`) if 2c already reported `python3`
  missing.
## 3. Probe capabilities (the real agent path)
Call `mcp__rp-command__rp-bridge-discover-tools` with no arguments — **always live, never from
`cache/abilities.json`** (this command is the developer's explicit "give me the truth right now"
check; it is also what refreshes that cache — see step 5). From its result, report:
- ✅ **Connected** — and the bridge contract version (`bridge`).
- **Ability count** (`ability_count`) and a short sample of distinct ability **categories**.
- Whether **site instructions** are set (`site_instructions` non-empty) — these are the site
  owner's rules from RP Connect's AI Memory, which all agents must follow. If present, summarise
  them in one line.
- A reminder of the two builder paths available (Elementor / ACF) and the maintenance tasks.
### If the call fails — diagnose the exact cause, don't just say "connection failed"
The MCP client surfaces the underlying HTTP status in the error (same codes `/rp-command`'s own
verification step already interprets — this is the same failure taken from the other side, when a
build session hits it instead of the initial connect):
- **401 Unauthorized** — the stored Basic-auth credentials are wrong, or the Application Password
  was revoked/deleted on the site since this project connected (WordPress app passwords don't
  expire on their own — the only ways they stop working are revocation, the user account being
  deleted, or a typo in the original setup). Tell the user exactly:
  ```
  ❌ Authentication failed (401). The stored credentials no longer work.
  Fix: run `/rp-command <site-url>` again with a fresh Application Password.
  Create one on the site under Users → Profile → Application Passwords, then re-run /rp-command.
  ```
  Do not guess *why* it was revoked — just give the fix.
- **404 / route-not-found** — the RP Connect endpoint doesn't exist at that URL. Tell the user:
  ```
  ❌ Endpoint not found (404). RP Connect may have been deactivated on the site, or the site URL
  changed. Confirm the plugin is active, then re-run `/rp-command <site-url>` with the correct URL.
  ```
- **000 / connection error / timeout** — the site itself is unreachable (down, wrong URL, VPN
  needed, DNS issue). Tell the user:
  ```
  ❌ Could not reach the site at all. Check the site is up and the URL is correct — this is not a
  credentials problem, the request never got a response.
  ```
- **Any other error** (500, malformed response, etc.) — report the raw status/message verbatim; do
  not force it into one of the three buckets above if it genuinely doesn't fit.
Never tell the user to "re-run `/rp-command`" for a 404 or connection-error case — that command
only fixes credentials/registration, not a deactivated plugin or an unreachable site; pointing the
user at the wrong fix wastes a round-trip.
## 4. Ability-contract version handshake — diff against the last known-good baseline
Read `cache/ability-baseline.json` with the **Read** tool (not `cat`).
**If it does not exist yet** (first-ever connect, or a fresh clone of this project): nothing to
diff against. Write it now from this run's `discover-tools` result:
```json
{ "bridge": "<bridge>", "ability_count": <n>, "ability_names": ["rp/<id>", ...], "recorded_at": "<iso-8601 now>" }
```
Report `📋 First connection recorded — N abilities baselined for future drift checks.` and stop
here (no diff to show on a first run).
**If it exists:** diff this run's `abilities[].name` list against the recorded `ability_names`:
- **New abilities** (in this run, not in the baseline) — list them; this is informational, not a
  problem (a new server version usually just adds capability).
- **Removed abilities** (in the baseline, not in this run) — list them **prominently**; any agent
  or skill that names one of these abilities will now fail at dispatch time instead of at connect
  time. This is the actual value of this check — surfacing that *before* a build starts, not
  mid-build.
- **Bridge contract version changed** (`bridge` field differs from the baseline) — report this
  regardless of whether the ability list changed; a version bump can mean the response *shape*
  changed even if names stayed the same.
- If nothing changed: `✅ Ability contract unchanged since <recorded_at> (N abilities).`
**This handshake does NOT detect a changed *schema* on an existing, still-present ability** — that
would require calling `inspect-tool` per ability (expensive against ~249 abilities) on every doctor
run. Out of scope here by design; an agent that hits a schema mismatch on a specific ability during
a real dispatch should report that failure with the exact ability name and expected vs. received
shape, at the point of use — not something this coarse, cheap, connect-time check tries to catch
speculatively for every ability up front.
After reporting the diff (or the "unchanged" line), **overwrite** `cache/ability-baseline.json`
with this run's fresh catalogue (same shape as the first-run write above) — `/rp-doctor` is the
only thing that ever updates this file, so the next drift check always compares against the most
recent explicit doctor run, not a run from days/weeks ago.
## 5. Refresh the session ability-catalog cache
This run's `discover-tools` result is also the freshest possible copy of the ability catalogue —
write it to `cache/abilities.json` (same file every other agent reads per `rp-dispatch` §3),
adding a `cached_at` (ISO-8601, now) field. This makes `/rp-doctor` double as a manual cache-warm/
refresh action: running it always gives every subsequent agent invocation this session a fresh
cache entry, without waiting for the 6h TTL to expire naturally.
## Output
Finish with a one-line verdict that includes the RP Connect bridge status, the Playwright MCP
status, the fast-build smoke test result, **and** the plugin integrity check result, e.g.:
`✅ Connected to <site> — 219 abilities across N categories. Ability contract unchanged. Playwright MCP connected. Fast-build smoke test passed. Plugin integrity check passed. Ready to build/maintain.`
or, if the handshake found removed abilities:
`⚠️ Connected to <site> — 219 abilities, but 2 abilities were REMOVED since the last check: rp/foo, rp/bar. Review before building.`
or, if the bridge is fine but Playwright MCP is missing:
`⚠️ Connected to <site> — 219 abilities, but Playwright MCP is NOT connected. Builds and visual QA are blocked until it is added (see step 2b). Maintenance-only bridge tasks can still run.`
or, if the smoke test failed:
`⚠️ Connected to <site> — bridge and Playwright OK, but the fast-build smoke test FAILED (<test name>): <assertion message>. Fix before building Elementor pages via the fast-build path.`
or, if the integrity check found an ERROR:
`⚠️ Connected to <site> — bridge and Playwright OK, but the plugin integrity check FAILED: <file>: <reason>. This is a plugin wiring defect, not a site issue — fix before building.`
or a single, specific next step if any earlier check failed.
