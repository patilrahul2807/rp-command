# rp-command — Plugin install ane vaparvana steps

Aa file ma WordPress site thi lai ne website banva sudhi na badha steps che.

---

## Bhag 1 — Ek j vaar karvanu (Setup)

### Step 1: Computer ma jaruri software

| Software | Shu mate | Check karva |
|---|---|---|
| Claude Code | plugin chalavva | `claude --version` |
| Node.js (LTS) | WordPress sathe connection (`npx`) | `node --version` |
| Python 3 | Figma / XD mathi design kadhva | `python --version` |

Koi na hoy to install karo:
- Node.js: https://nodejs.org (LTS version)
- Python: https://www.python.org/downloads (install vakhte **"Add python.exe to PATH"** tick karjo)

### Step 2: WordPress ma RP Connect plugin

1. WordPress admin → **Plugins → Add New → Upload Plugin** → `rp-connect.zip` upload karo.
2. **Activate** karo.
3. Admin menu ma **RP Connect → MCP Connect** kholo.
4. **RP Plugin** tab ma je commands dekhay che te copy karo — ema tamari site no URL,
   username ane navo **Application Password** pela thi bharelo hoy che.

> Application Password ek j vaar dekhay che. Kyak surakshit jagya e sachvi rakho.

### Step 3: Claude Code ma plugin install

Claude Code kholo ane ek pachi ek aa commands chalavo:

```
/plugin marketplace add https://github.com/patilrahul2807/rp-command.git
/plugin install rp-command@rp-command
/reload-plugins
```

### Step 4: WordPress site sathe connect

```
/rp-command:rp-connect https://tamari-site.com admin "xxxx xxxx xxxx xxxx xxxx xxxx"
```

- `https://tamari-site.com` → tamari site no URL
- `admin` → WordPress username
- `"xxxx ..."` → Application Password (quotes ma)

**Staging site** jema browser login (Basic-Auth) puche che, ema chhelle staging user ane password pan aapo:

```
/rp-command:rp-connect https://staging.site.com admin "xxxx xxxx xxxx" staginguser stagingpass
```

Pachi:

```
/exit
```

ane `claude` pharithi chalu karo (navu connection tyare j load thay che).

### Step 5: Connection check

```
/rp-command:rp-doctor
```

Aa table batavshe:
- MCP connection ✅ / ❌
- WordPress / PHP version, active theme
- ACF Pro, Elementor, Gutenberg, Avada — installed / active che ke nahi
- Python / Node

Badhu ✅ hoy to setup puru. ❌ hoy to te j line ma lakhelu fix karo.

---

## Bhag 2 — Darek navi website mate

### Step 1: Project folder

Darek website mate alag folder banavo ane te folder ma Claude chalu karo:

```
mkdir D:\projects\client-site
cd D:\projects\client-site
claude
```

(Project ni badhi mahiti `.rp/` folder ma save thashe.)

### Step 2: Design taiyar rakho

| Design | Shu joie |
|---|---|
| **Figma** | Figma file / frame no link + **Figma token** (Figma → Settings → Security → Personal access tokens → "File content: Read") |
| **Adobe XD** | `.xd` file no path + artboards ni PNG (XD ma **File → Export → All Artboards → PNG**) ek folder ma |
| **HTML** | HTML project nu folder |
| **Images** | screenshots nu folder |

> XD file ma page ni images hoti nathi, etle PNG export jaruri che — nahi to design sathe sarkhamani (QA) barabar nahi thay.

### Step 3: Build chalu karo

```
/rp-command:rp-start
```

Developer ni khas suchnao hoy to command sathe j lakho:

```
/rp-command:rp-start Header sticky rakhjo, buttons rounded 8px, mobile ma menu hamburger
```

### Step 4: Prashno na javab aapo

Claude puchshe:

1. **Builder** — ACF / Elementor / Gutenberg / Avada
2. **Design kya thi** — Figma / XD / HTML / Images
3. **Kaya pages** — badha frames / link valo frame / hu list aapish
4. **Developer instructions** — kai nahi / hu lakhish

Pachi Figma link + token, athva XD file path + PNG folder, je jaruri hoy te mangshe.

### Step 5: Plugin check

Builder mate jaruri plugin site par na hoy to Claude kaheshe:

| Builder | Jaruri |
|---|---|
| ACF | ACF Pro + custom theme |
| Elementor | Elementor (header/footer, forms mate Elementor Pro) |
| Gutenberg | WordPress 6.4+ ane block theme |
| Avada | Avada theme + Fusion Builder + Fusion Core |

Aa plugins **tamare wp-admin ma jate install karva padshe** (Claude plugin install nathi kari shaktu, ane
ACF Pro / Elementor Pro / Avada paid che). Install kari ne **"I installed it — check again"** pasand karo.

### Step 6: Design extraction

Claude jate:
- design mathi pages, text, colors, fonts, images kadhshe,
- shu malyu te batavshe (keta pages, keti images, mukhya colors / fonts),
- frame → page nu naam confirm karavshe,
- badhi images WordPress Media Library ma upload karshe.

### Step 7: Plan approve karo

Kayo page, kaya sections, kaya layouts / widgets — teno plan batavshe.
**Tame approve karo pachi j site par kai lakhashe.**

### Step 8: Build + QA

- Agents ek pachi ek kaam karshe (setup → layouts → pages).
- Darek page design sathe sarkhavshe, kharab section ne vadhu ma vadhu 3 vaar fix karshe.
- Pages pela **Draft** ma banshe.

### Step 9: Report

Chhelle malshe:
- darek page nu edit link ane preview link
- darek page no QA score
- je sections haji barabar nathi te ane karan
- kya developer instruction e default niyam badlyo

Badhu barabar lage to wp-admin ma pages **Publish** karo.

### Ek page ek command ma: `/rp-build`

`/rp-start` ek vaar thai jay (config + design taiyar), pachi darek page alag thi banavi shakay:

```
/rp-command:rp-build home
/rp-command:rp-build about-us --full-qa
/rp-command:rp-build contact --publish-live
```

| Flag | Shu kare |
|---|---|
| `--full-qa` | vadhu QA: visual regression + WordPress checklist |
| `--publish-live` | QA pass thay pachi puchi ne page **Publish** kare (vagar flag page Draft j rahe) |
| `--strict-sections` | (Elementor, Figma/XD) darek section alag build + QA — risky design mate |

- Darek step pachi gate check thay; pehlo gate fail thay tyan j atki ne karan kahe.
- Adhuru rahelu page e j command thi pharithi chalavo — je step baki che tyan thi chalu thashe.
- Pages `pages` list na order ma j bane: aagal nu page approve na thay tya sudhi pachhi nu page chalu nahi thay.
- Pehli vaar Playwright MCP install karshe — pachi Claude restart kari ne pharithi chalavo.

### Adhuru kaam pharithi chalu karvu

E j project folder ma pharithi:

```
/rp-command:rp-start
```

Claude `.rp/project-config.json` joi ne puchshe — **resume** karvu ke **navo project**.

---

## Plugin update

```
/plugin marketplace update rp-command
/plugin update rp-command@rp-command
/reload-plugins
```

---

## Mushkeli aave to

| Samasya | Upay |
|---|---|
| `rp-doctor` ma MCP ❌ | `/rp-command:rp-connect ...` pharithi chalavo, `/exit`, `claude` pharithi |
| 401 / 403 error | Application Password khoto / revoke thayo — WordPress ma navo banavo ane `rp-connect` pharithi |
| 404 `/wp-json/mcp/...` | RP Connect plugin active nathi |
| `npx` not found | Node.js install karo |
| `python` not found | Python install karo ("Add to PATH" sathe) |
| Figma 403 | Token khoto che athva file ni access nathi |
| Images upload na thay | `~/.rp-command/connection.json` nathi — `rp-connect` pharithi chalavo |
| SVG icons upload na thaya | WordPress SVG rokhe che; builder agent te alag rite mukshe (report ma "svg_pending") |
