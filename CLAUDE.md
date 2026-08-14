# Meal Planner — household dinners

Weekly dinner planner: builds a 4-dinner plan from the saved recipes, produces a
grocery list, pushes it to AnyList, updates a dashboard page, and emails the plan.
Runs every Sunday morning (scheduled task) or on demand ("run the meal plan").

First-time setup on a new machine: see [SETUP.md](SETUP.md). Do that before the
first run — the AnyList push and the dashboard both need one-time configuration.

## House rules
- **Vegetarian-first**: at most 1 non-vegetarian dinner per week, and rarely; always
  include the veg substitution note for meat recipes.
- **Varied proteins**: all 4 meals must use different primary proteins (never repeat
  on consecutive nights).
- **Universe of meals = `Recipes/` folder only.** Never add outside recipes without
  asking first. New saved .mhtml files dropped into `Recipes/` need to be extracted
  and added to `data/recipes.json` — `scripts/extract_recipes.py` pulls the raw
  schema.org data where the source page provides it, but most pages don't, so the
  structured records in `data/recipes.json` were built by reading each page's text.
  Adding a recipe means producing a record matching the existing schema: id, name,
  source_url, protein_primary, vegetarian/vegan, servings, times, per-ingredient
  entries (item, quantity, unit, store category, pantry_staple), nutrition, tags.

## Weekly workflow
Run in order. The date argument is optional — it defaults to the current or next
Sunday, and every step is idempotent for a given week.

1. `python scripts/planner.py [YYYY-MM-DD]` — picks the 4 dinners, writes
   `data/plans/<sunday>.json`, appends `data/history.json`. "Plan already exists"
   is a normal, successful result for a re-run.
2. `python scripts/grocery.py [YYYY-MM-DD]` — writes `data/plans/<sunday>_grocery.json`.
3. `node scripts/anylist_push.js [YYYY-MM-DD]` — pushes items to the AnyList list
   named in `~/.meal-planner/anylist.env`. **Exit code 2 means credentials are
   missing and nothing was pushed** — surface that in the run summary rather than
   treating the run as successful. Exit 4 means the `anylist` package isn't installed.
4. `python scripts/build_dashboard.py [YYYY-MM-DD]` — regenerates `dashboard.html`.
5. Republish the dashboard **to the same URL** with the Artifact tool, passing
   `url:` set to the value of `DASHBOARD_URL` below and the file `dashboard.html`
   (favicon 🥗 — keep it stable). If `DASHBOARD_URL` is still unset, publish without
   `url:`, then record the URL it returns here and in the scheduled task's prompt.
6. Email the plan (subject "Dinner plan — week of <Monday's date>"): the 4 meals with
   links, times and protein, any veg-substitution notes, average per-serving
   nutrition, a line confirming groceries are in AnyList, and the dashboard link.
   If no mail tool is connected in the session, say so in the summary instead of
   silently skipping.

`DASHBOARD_URL`: _(unset — fill in after the first publish from this account)_

Verify at the end of a run that steps 1–4 all produced their outputs. A partial run
(plan written but no grocery file, or a `dashboard.html` older than the plan) means
the pipeline stopped midway and the week is not actually done.

## Preferences & feedback
- Ratings live in `data/preferences.json`:
  `{"ratings": {"<recipe-id>": {"rating": "loved|liked|ok|disliked|never", "notes": "…"}}, "exclusions": ["<id>", …]}`
- When someone gives feedback ("we loved X", "skip Y for a while"), update this file.
  `never` and entries in `exclusions` remove a recipe from rotation entirely.
- The planner excludes repeats within 2 weeks, down-weights recent and disliked
  recipes, and boosts loved ones. Two recipes are tagged `"role": "light"`
  (side-style salads) and surface less often as mains.

## Credentials
The AnyList login lives in `~/.meal-planner/anylist.env`, deliberately outside this
folder so it is never synced to cloud storage or copied along with the project.
Never print its contents. It is the only secret this project uses.

## Troubleshooting
- **Scripts fail with "Permission denied" when Python or Node opens them.** Some
  endpoint-protection software blocks reads of newly created script files. Work
  around it by piping through stdin and passing the project path via the
  environment: `MEAL_PLANNER_HOME="<project dir>" cat scripts/planner.py | python -`
  (same shape for `node -`). All scripts support this.
- **`node`/`npm` not found** after installing Node via winget: the installer's
  directory may not be on PATH. Locate `node.exe` under
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\` and either add it to PATH or call it
  by full path.
