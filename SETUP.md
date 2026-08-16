# Setup on a new machine

One-time steps. Takes about ten minutes, most of it waiting on installers.
Do these in order; step 5 depends on 1–4 being done.

## 0. Put the folder somewhere permanent

Anywhere you like — for example `C:\Users\<you>\meal-planner` or a personal
OneDrive/Dropbox folder. The scripts locate the project from their own location,
so no path is hardcoded. Avoid a folder your employer syncs or manages.

## 1. Python

Needs Python 3.9 or newer. Check with `python --version`.
If it's missing, install from python.org or `winget install Python.Python.3.13`.
No packages to install — the scripts use only the standard library.

## 2. Node.js (only needed for the AnyList push)

Check with `node --version`. If missing:

```bash
winget install OpenJS.NodeJS.LTS
```

Then **open a new terminal** so PATH updates. If `node` still isn't found, the
binary is under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_*\`.

## 3. The AnyList library

From inside the project folder:

```bash
npm install anylist
```

This is an unofficial, reverse-engineered client — it is not published or supported
by AnyList, and an app-side change could break it. If that happens, the push fails
loudly and the grocery list is still available in `data/plans/` and on the dashboard.

## 4. AnyList credentials

Create the file `~/.meal-planner/anylist.env` — that is
`C:\Users\<you>\.meal-planner\anylist.env` on Windows. It is deliberately outside
the project folder so it never syncs anywhere or travels with a copy of the project.

```
ANYLIST_EMAIL=you@example.com
ANYLIST_PASSWORD=your-anylist-password
ANYLIST_LIST=Current Grocery List
```

`ANYLIST_LIST` must exactly match a list that already exists in your AnyList app.
Create and edit this file yourself; the scripts read it and never print its values.

## 5. First run

```bash
python scripts/planner.py
python scripts/grocery.py
node scripts/anylist_push.js
python scripts/build_dashboard.py
```

Expect: a plan and grocery JSON under `data/plans/`, a line reporting how many items
were added to AnyList, and a regenerated `docs/index.html`. Open that file in a
browser to confirm it shows the right week.

If a script fails with "Permission denied" when Python or Node tries to open it,
your endpoint protection is blocking reads of new script files. Pipe them instead:

```bash
MEAL_PLANNER_HOME="<project dir>" cat scripts/planner.py | python -
```

## 6. Host the dashboard on GitHub Pages

The dashboard and recipe pages are static HTML committed to `docs/` and served by
GitHub Pages — no manual publish step, and the URL never changes once set up.

- The `markwyand-home/meal-planner` repo must be **public** (GitHub Pages on a
  private repo needs a paid plan; a public repo gets it for free). If it's private,
  make it public first: `gh repo edit markwyand-home/meal-planner --visibility public --accept-visibility-change-consequences`.
  Nothing secret lives in the repo — AnyList credentials stay in
  `~/.meal-planner/anylist.env`, outside it.
- Enable Pages once, sourced from `main` branch, `/docs` folder:
  ```bash
  echo '{"build_type":"legacy","source":{"branch":"main","path":"/docs"}}' | gh api repos/markwyand-home/meal-planner/pages -X POST --input -
  ```
- Commit and push `docs/` (see weekly workflow step 6 in `CLAUDE.md`). The live
  site is then always at `https://markwyand-home.github.io/meal-planner/` —
  nothing to record anywhere, unlike the old per-account artifact URL.

## 7. Weekly schedule

Ask Claude to create a scheduled task that runs Sundays at ~6:47am and follows the
weekly workflow in `CLAUDE.md`. The prompt must be self-contained: scheduled runs
start with no memory of any earlier conversation. Include the project's full path,
the instruction to read `CLAUDE.md` first, and the dashboard URL from step 6.

Two limits worth knowing: the task only runs while the Claude desktop app is open
(if it's closed at the scheduled time, it runs at next launch), and the emailing
step needs a mail tool connected in that session. Trigger it once manually with
"Run now" to pre-approve the tools it needs, so a later run doesn't stall waiting
on a permission prompt.

## 8. Memory files (optional)

`memory/` holds two notes from the original setup. If you want Claude to carry them
forward, ask it to add them to this project's memory, and it will place them in the
right per-project location. The Windows script-read-block note only matters if you
hit the permission problem described in step 5 — otherwise skip it.

## What isn't included

- **Credentials.** Re-entered in step 4 by hand.
- **`node_modules`.** Reinstalled in step 3.
- **The old scheduled task.** Recreated in step 7.
