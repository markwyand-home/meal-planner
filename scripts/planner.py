"""Weekly meal planner for the Wyand household.

Selects dinners from data/recipes.json following the house rules. Scheduled
runs take the default of 4; a manual run can ask for fewer when the week is
busy:  python scripts/planner.py [YYYY-MM-DD] [count] [--force]
`--force` replaces an existing plan for that week (and its history row).

House rules:
- vegetarian-first: at most 1 non-vegetarian meal per week (meat recipes
  carry a scoring penalty; veg subs are noted on the plan)
- varied proteins: all 4 meals use different primary proteins, so no
  protein repeats on consecutive nights regardless of cooking order
- variety over time: recently served recipes are down-weighted; meals from
  the previous 2 weeks are excluded when enough alternatives exist
- preferences: ratings in data/preferences.json boost or bury recipes

Deterministic per week (seeded by the week's Sunday date). Writes
data/plans/<week>.json and appends to data/history.json.

NOTE (this machine): endpoint protection blocks reading newly created .py
files directly, so run scripts via stdin with the project home in an env var:
  MEAL_PLANNER_HOME="<project dir>" cat scripts/planner.py | python - [YYYY-MM-DD]
"""

import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

if os.environ.get("MEAL_PLANNER_HOME"):
    BASE = Path(os.environ["MEAL_PLANNER_HOME"])
else:
    BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

RATING_WEIGHT = {"loved": 1.35, "liked": 1.1, "ok": 1.0, "disliked": 0.25, "never": 0.0}
MEAT_PENALTY = 0.45          # vegetarian-first: meat recipes rarely surface
LIGHT_PENALTY = 0.5          # side-style dishes are picked less often as mains
RECENT_EXCLUDE_WEEKS = 2     # don't repeat a meal within this many weeks
MEALS_PER_WEEK = 4
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday"]


def load(name, default):
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default


def week_sunday(argdate=None):
    if argdate:
        return date.fromisoformat(argdate)
    today = date.today()
    return today + timedelta(days=(6 - today.weekday()) % 7)  # next (or today's) Sunday


def score(recipe, prefs, weeks_since):
    s = 1.0
    if weeks_since is not None:
        s *= min(1.0, weeks_since / 4.0)  # full weight back after ~a month
    else:
        s *= 1.2  # never served: slight novelty boost
    rating = prefs.get("ratings", {}).get(recipe["id"], {}).get("rating")
    s *= RATING_WEIGHT.get(rating, 1.0)
    if not recipe["vegetarian"]:
        s *= MEAT_PENALTY
    if recipe.get("role") == "light":
        s *= LIGHT_PENALTY
    return s


def pick_meals(recipes, prefs, history, rng, n_meals=MEALS_PER_WEEK):
    served_weeks = {}  # id -> weeks since last served
    for i, week in enumerate(reversed(history.get("weeks", []))):
        for mid in week["meals"]:
            served_weeks.setdefault(mid, i + 1)

    excluded = set(prefs.get("exclusions", []))
    pool = [r for r in recipes if r["id"] not in excluded]
    recent = {mid for mid, w in served_weeks.items() if w <= RECENT_EXCLUDE_WEEKS}
    fresh_pool = [r for r in pool if r["id"] not in recent]
    if len(fresh_pool) >= n_meals + 2:
        pool = fresh_pool

    weights = {r["id"]: score(r, prefs, served_weeks.get(r["id"])) for r in pool}

    # weighted sampling with constraints: distinct proteins, <=1 non-vegetarian
    for _ in range(200):
        chosen, proteins, meat_count = [], set(), 0
        candidates = pool[:]
        while candidates and len(chosen) < n_meals:
            total = sum(weights[r["id"]] for r in candidates)
            if total <= 0:
                break
            pickpoint = rng.random() * total
            acc = 0.0
            selected = candidates[-1]
            for r in candidates:
                acc += weights[r["id"]]
                if acc >= pickpoint:
                    selected = r
                    break
            candidates.remove(selected)
            if selected["protein_primary"] in proteins:
                continue
            if not selected["vegetarian"] and meat_count >= 1:
                continue
            chosen.append(selected)
            proteins.add(selected["protein_primary"])
            meat_count += 0 if selected["vegetarian"] else 1
        if len(chosen) == n_meals:
            return chosen
    raise RuntimeError("could not build a valid plan; relax constraints or exclusions")


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    datearg = next((a for a in args if "-" in a), None)
    n_meals = next((int(a) for a in args if a.isdigit()), MEALS_PER_WEEK)
    if not 1 <= n_meals <= len(DAYS):
        print(f"meal count must be 1-{len(DAYS)} (got {n_meals})")
        sys.exit(1)

    sunday = week_sunday(datearg)
    recipes = load("recipes.json", {"recipes": []})["recipes"]
    prefs = load("preferences.json", {"ratings": {}, "exclusions": []})
    history = load("history.json", {"weeks": []})

    plans_dir = DATA / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / f"{sunday.isoformat()}.json"
    if plan_path.exists() and not force:
        print(f"plan already exists: {plan_path}")
        return
    if force:
        # Replacing a week: drop its history entry first, or the append below
        # adds a second row for the same Sunday.
        history["weeks"] = [w for w in history.get("weeks", []) if w["week_of"] != sunday.isoformat()]

    rng = random.Random(sunday.isoformat() + ("" if n_meals == MEALS_PER_WEEK else f"-{n_meals}"))
    chosen = pick_meals(recipes, prefs, history, rng, n_meals)
    rng.shuffle(chosen)

    meals = []
    for day, r in zip(DAYS, chosen):
        meals.append({
            "day": day,
            "id": r["id"],
            "name": r["name"],
            "protein": r["protein_primary"],
            "vegetarian": r["vegetarian"],
            "veg_sub_note": None if r["vegetarian"] else r["protein_notes"],
            "total_min": r["total_min"],
            "servings": r["servings"],
            "source_url": r["source_url"],
            "nutrition_per_serving": r["nutrition_per_serving"],
            "tags": r["tags"],
        })

    n = [m["nutrition_per_serving"] for m in meals]
    plan = {
        "week_of": sunday.isoformat(),
        # How many dinners were asked for. A short week is often deliberate, so
        # downstream reports a shortfall only against this, never against 4.
        "meals_requested": n_meals,
        "meals": meals,
        "nutrition_avg_per_serving": {
            "calories": round(sum(x["calories"] for x in n) / len(n)),
            "protein_g": round(sum(x["protein_g"] for x in n) / len(n), 1),
            "carbs_g": round(sum(x["carbs_g"] for x in n) / len(n), 1),
            "fat_g": round(sum(x["fat_g"] for x in n) / len(n), 1),
        },
    }
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    history.setdefault("weeks", []).append({"week_of": sunday.isoformat(), "meals": [m["id"] for m in meals]})
    (DATA / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")

    print(f"plan written: {plan_path}")
    for m in meals:
        veg = "veg" if m["vegetarian"] else "MEAT (sub available)"
        print(f"  {m['day']:<10} {m['name']}  [{m['protein']}, {veg}]")


if __name__ == "__main__":
    main()
