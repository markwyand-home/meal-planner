---
name: meal-planner-project
description: Household weekly meal planner — 4 dinners, grocery list to AnyList, dashboard page, Sunday schedule
metadata:
  type: project
---

The household meal planner (originally built 2026-07-26) builds four dinners a week
from the saved recipes, pushes a grocery list to AnyList, and republishes a dashboard
page. The project folder's CLAUDE.md is authoritative for the weekly workflow — read
it rather than relying on this note.

Two things that live outside the folder: the AnyList login at
`~/.meal-planner/anylist.env`, and the weekly scheduled task. The dashboard's artifact
URL is recorded as `DASHBOARD_URL` in CLAUDE.md; republish to that URL rather than
creating a new page each week.

Meal universe is the `Recipes/` folder only — never add outside recipes without
asking. Taste feedback goes in `data/preferences.json`. See [[windows-script-read-block]]
if scripts fail with permission errors.
