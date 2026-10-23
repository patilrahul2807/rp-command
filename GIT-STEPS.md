# rp-command — Git / GitHub steps

Repo: https://github.com/patilrahul2807/rp-command
Local folder: `D:\dev-connect\ai-agents`

---

## 1. Pehli vaar (navu computer)

### Git install

```
winget install --id Git.Git -e
```

Install pachi navu terminal (Git Bash athva PowerShell) kholo.

### Naam / email set karo (ek j vaar)

```
git config --global user.name "patilrahul2807"
git config --global user.email "tamaro-email@example.com"
```

### Repo download (clone)

```
cd /d/dev-connect
git clone https://github.com/patilrahul2807/rp-command.git ai-agents
cd ai-agents
```

### GitHub login

Pehli vaar `git push` karsho tyare GitHub login window khulshe →
**Sign in with your browser** → `patilrahul2807` thi authorize karo.
Login save thai jashe, pachi pharithi nahi puche.

Login pela thi karvu hoy to:

```
git credential-manager github login
```

> Claude ni andar thi login window nathi khulti — login hamesha **Git Bash / PowerShell window** ma karo.

---

## 2. Roj nu kaam — change kari ne GitHub par mokalvu

Folder ma jao:

```
cd /d/dev-connect/ai-agents
```

### Step 1: Latest code lo

```
git pull
```

### Step 2: Files ma change karo

(agents, skills, commands, scripts …)

### Step 3: Shu badlayu te juo

```
git status
git diff
```

### Step 4: Changes add karo

```
git add -A
```

### Step 5: Commit (change nu naam aapo)

```
git commit -m "Elementor recipes ma testimonial section umeryu"
```

### Step 6: GitHub par push

```
git push
```

### Step 7: Plugin update (Claude Code ma)

Push pachi, plugin vaparta darek computer par:

```
/plugin marketplace update rp-command
/plugin update rp-command@rp-command
/reload-plugins
```

---

## 3. Version / release (vaikalpik)

Moto change hoy to `plugins/rp-command/.claude-plugin/plugin.json` ma `"version"` vadharo
(`1.0.0` → `1.1.0`), commit + push karo, ane tag banavo:

```
git tag v1.1.0
git push --tags
```

---

## 4. Upyogi commands

| Kaam | Command |
|---|---|
| Itihas (history) jovo | `git log --oneline` |
| Ek file na change jovo | `git diff plugins/rp-command/commands/rp-start.md` |
| Commit pela no change radd karvo (ek file) | `git restore <file>` |
| Add karelu pachu levu (commit pela) | `git restore --staged <file>` |
| Remote check | `git remote -v` |
| GitHub sathe sarkhamani | `git status -sb` (`## main...origin/main` = sarkhu) |

---

## 5. Dhyan ma rakhjo

- Repo **public** che — passwords, Application Passwords, Figma tokens **kyarey commit na karo**.
  (`~/.rp-command/connection.json` home folder ma che, repo ma nathi — barabar che.)
- Project nu `.rp/` folder `.gitignore` ma che — client projects nu data repo ma nahi jay.
- `git push --force` na vaparo — GitHub par nu kaam bhunsai jai shake.
- Push error `rejected (fetch first)` aave to pela `git pull`, pachi `git push`.

---

## 6. Mushkeli aave to

| Error | Upay |
|---|---|
| `git: command not found` | Git install karo, terminal band kari ne pharithi kholo |
| `could not read Username ... terminal prompts disabled` | Claude ni bahar Git Bash ma `git push` chalavo (login window mate) |
| `Authentication failed` | `git credential-manager github logout` pachi pharithi login |
| `rejected ... non-fast-forward` | `git pull` pachi `git push` |
| Merge conflict | conflict vali file kholo, `<<<<<<<` / `>>>>>>>` vacche nu sachu rakho, pachi `git add -A`, `git commit`, `git push` |
