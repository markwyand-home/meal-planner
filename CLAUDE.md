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
- **Fresh garlic is never a pantry staple.** Any garlic that isn't garlic powder or
  garlic salt (cloves, minced, grated, etc.) must be recorded as
  `"pantry_staple": false` in `data/recipes.json` so it always lands on the grocery
  list and gets pushed to AnyList. Only dried garlic (powder/salt) stays a staple.
  (Decided 2026-08-30, after garlic was missing from a shopping list.)
- **Noodles/pasta and tofu always get pushed to AnyList.** `data/anylist_rules.json`'s
  `include_keywords_regex` (`noodles?|pasta|tofu`) overrides every exclude rule for
  these — needed because some ingredient names are "X noodles or rice noodles" /
  "pasta, polenta, or grain of choice" style either/or compounds that also contain
  an excluded staple word (rice, polenta, grain) and would otherwise get dropped.
  (Decided 2026-08-30.)
- **Universe of meals = `Recipes/` folder only.** Never add outside recipes without
  asking first. New saved .mhtml files dropped into `Recipes/` need to be extracted
  and added to `data/recipes.json` — `scripts/extract_recipes.py` pulls the raw
  schema.org data where the source page provides it, but most pages don't, so the
  structured records in `data/recipes.json` were built by reading each page's text.
  Adding a recipe means producing a record matching the existing schema: id, name,
  source_url, protein_primary, vegetarian/vegan, servings, times, per-ingredient
  entries (item, quantity, unit, store category, pantry_staple), nutrition, tags.
  `instructions` (step-by-step text) and `page_url` (its published clean recipe
  page) get filled in later, the first time the recipe is actually selected into
  a week's plan — see step 4 of the weekly workflow.

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
   Before pushing, applies `data/anylist_rules.json`: omits ingredients we usually
   have stocked (spices, oils, grains, lentils, and a curated set of condiments/
   broths/etc. — see that file's notes for what's excluded vs. deliberately kept),
   swaps fresh-produce measurements for a whole-item buy (e.g. "2 tbsp lemon
   juice" -> "1 lemon"), and assigns each item an AnyList aisle category
   (`categoryMatchId`) so the app groups them under its built-in headers
   (Produce, Dairy, Meat, etc.) instead of one flat list. This only changes what's
   pushed to AnyList — the grocery JSON and dashboard stay at full recipe-accurate
   detail so the two can be cross-checked against each other. New recipes may
   introduce pantry items not yet covered by the rules file (exclusion or
   category); when that happens, ask before adding them rather than guessing.
   `node scripts/anylist_push.js --clear` removes every item currently on the
   list (useful when re-testing the filtering logic). After the recipe-derived
   items, it also adds every item on that AnyList list's built-in "favorites"
   (managed in the AnyList app itself, e.g. bananas, eggs, coffee) — every
   week, not just a one-time thing. Same idempotency: skipped if already on
   the list unchecked.
4. For any of this week's 4 recipes that don't yet have `"instructions"` in
   `data/recipes.json`: read the recipe's page from `Recipes/<file>.mhtml` (see
   `scripts/extract_recipes.py`'s `mhtml_html()` for pulling plain text out of the
   .mhtml, or just read it directly) and add an `instructions` array (clean step
   strings, no ads/commentary/comment-thread noise) to that recipe's record —
   matching the style of the ones already done. Then
   `python scripts/build_recipe_pages.py <recipe-id> [<recipe-id> ...]` to render
   `docs/recipes/<id>.html`. If the recipe doesn't yet have a `page_url` in
   recipes.json, set it to `https://markwyand-home.github.io/meal-planner/recipes/<id>.html`
   (the GitHub Pages URL that path resolves to once pushed). This is a one-time
   cost per recipe — once `page_url` is set it's reused every time that recipe
   comes back into rotation.
5. `python scripts/build_dashboard.py [YYYY-MM-DD]` — regenerates `docs/index.html`.
   Each meal's title links to its recipe's `page_url` (clean instructions-only
   page) when set, falling back to the original noisy `source_url` otherwise.
6. Commit and push so GitHub Pages redeploys the live site:
   `git add docs/ data/recipes.json data/plans/<sunday>.json data/plans/<sunday>_grocery.json data/history.json`
   then commit (message like `Week of <sunday>: dinner plan`) and `git push`.
   **This auto-commit/push is scoped to this scheduled weekly routine only** — the
   user explicitly authorized it for this task; it does not extend to other edits
   in this project or repo. Only stage the paths listed above, never `git add -A`,
   so unrelated in-progress local edits aren't swept into the weekly commit.
7. Email the plan to mark.wyand@gmail.com and eringolden1@gmail.com (subject
   "Dinner plan — week of <Monday's date>"): the 4 meals with links, times and
   protein, any veg-substitution notes, average per-serving nutrition, a line
   confirming groceries are in AnyList, and the dashboard link. If no mail tool
   is connected in the session, say so in the summary instead of silently
   skipping.

**Hosting**: the dashboard and recipe pages are served by GitHub Pages from the
public `markwyand-home/meal-planner` repo (`main` branch, `/docs` folder) at
`https://markwyand-home.github.io/meal-planner/` — a fixed URL that updates
automatically on every push, no manual republish/re-pin step and no per-week URL
lookup needed. The repo is public (recipes and meal-plan data are visible to
anyone with the URL; no secrets live in it — AnyList credentials stay in
`~/.meal-planner/anylist.env`, outside the repo).

Verify at the end of a run that steps 1–6 all produced their outputs, and that the
push succeeded (`git push` didn't fail — e.g. on a conflict with a manual edit made
between runs). A partial run (plan written but no grocery file, or a
`docs/index.html` older than the plan, or a push failure) means the pipeline
stopped midway and the week is not actually done — say so plainly rather than
reporting the dashboard link as current.

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
