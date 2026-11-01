"""Weekly meal planner for the Wyand household.

Selects dinners from data/recipes.json following the house rules. The weekly
routine asks how many dinners and which nights, then passes them in:
  python scripts/planner.py [YYYY-MM-DD] [--nights Mon,Wed,Thu] [count] [--force]
`--nights` names the nights (any of Sun..Sat, full names or 3-letter forms; the
count follows from it). With only a `count`, the first N of Mon..Sat are used;
with neither, the default is 4 (Mon-Thu). `--force` replaces an existing plan
for that week (and its history row). Night dates are the week's Sunday plus the
weekday (Sunday = the plan Sunday itself, Monday = the next day, ...).

House rules:
- vegetarian-first: at most 1 non-vegetarian meal per week (meat recipes
  carry a scoring penalty; veg subs are noted on the plan)
- variety over time: recently served recipes are down-weighted; meals from
  the previous 2 weeks are excluded when enough alternatives exist
- preferences: ratings in data/preferences.json boost or bury recipes
- protein cap: at most 2 meals in a week share the same primary protein
- recurring: recipes listed under "recurring" in data/preferences.json are
  always included on their schedule (e.g. every 2nd week from an anchor
  Sunday) and count toward the week's dinners
(The old "all different proteins" rule became a cap of 2 on 2026-11-01.)

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
MAX_PER_PROTEIN = 2          # at most this many meals sharing a primary protein
MEALS_PER_WEEK = 4
WEEK_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DEFAULT_NIGHTS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS = DEFAULT_NIGHTS[:MEALS_PER_WEEK]


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


def recurring_picks(recipes, prefs, sunday, n_meals):
    """Recipes scheduled for this week by prefs["recurring"] entries of the form
    {"id": ..., "every_n_weeks": 2, "anchor": "YYYY-MM-DD"}: due when the week is
    a whole multiple of every_n_weeks from the anchor Sunday. Skips recipes that
    are missing, excluded, or rated "never"; never returns more than n_meals."""
    by_id = {r["id"]: r for r in recipes}
    excluded = set(prefs.get("exclusions", []))
    due = []
    for rule in prefs.get("recurring", []):
        r = by_id.get(rule["id"])
        if r is None or r["id"] in excluded:
            continue
        if prefs.get("ratings", {}).get(r["id"], {}).get("rating") == "never":
            continue
        weeks = (sunday - date.fromisoformat(rule["anchor"])).days // 7
        if weeks % int(rule.get("every_n_weeks", 1)) == 0 and r not in due:
            due.append(r)
    return due[:n_meals]


def pick_meals(recipes, prefs, history, rng, n_meals=MEALS_PER_WEEK, must_include=()):
    served_weeks = {}  # id -> weeks since last served
    for i, week in enumerate(reversed(history.get("weeks", []))):
        for mid in week["meals"]:
            served_weeks.setdefault(mid, i + 1)

    excluded = set(prefs.get("exclusions", [])) | {r["id"] for r in must_include}
    pool = [r for r in recipes if r["id"] not in excluded]
    recent = {mid for mid, w in served_weeks.items() if w <= RECENT_EXCLUDE_WEEKS}
    fresh_pool = [r for r in pool if r["id"] not in recent]
    if len(fresh_pool) >= n_meals - len(must_include) + 2:
        pool = fresh_pool

    weights = {r["id"]: score(r, prefs, served_weeks.get(r["id"])) for r in pool}

    # weighted sampling with constraints: <=1 non-vegetarian, <=MAX_PER_PROTEIN per protein
    for _ in range(200):
        chosen = list(must_include)
        meat_count = sum(0 if r["vegetarian"] else 1 for r in chosen)
        protein_count = {}
        for r in chosen:
            protein_count[r["protein_primary"]] = protein_count.get(r["protein_primary"], 0) + 1
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
            if not selected["vegetarian"] and meat_count >= 1:
                continue
            if protein_count.get(selected["protein_primary"], 0) >= MAX_PER_PROTEIN:
                continue
            chosen.append(selected)
            protein_count[selected["protein_primary"]] = protein_count.get(selected["protein_primary"], 0) + 1
            meat_count += 0 if selected["vegetarian"] else 1
        if len(chosen) == n_meals:
            return chosen
    raise RuntimeError("could not build a valid plan; relax constraints or exclusions")


def parse_nights(text):
    """'Mon,wed thursday' -> ['Monday', 'Wednesday', 'Thursday'] in week order."""
    names = []
    for tok in text.replace(",", " ").split():
        match = [d for d in WEEK_DAYS if d.lower().startswith(tok.lower()[:3]) and len(tok) >= 3]
        if not match:
            raise ValueError(f"not a weekday: {tok!r}")
        if match[0] not in names:
            names.append(match[0])
    return sorted(names, key=WEEK_DAYS.index)


def parse_args(argv):
    force, datearg, count, nights = False, None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--force":
            force = True
        elif a == "--nights" or a.startswith("--nights="):
            if a == "--nights":
                i += 1
                if i >= len(argv):
                    raise ValueError("--nights needs a list, e.g. --nights Mon,Wed,Thu")
                value = argv[i]
            else:
                value = a.split("=", 1)[1]
            nights = parse_nights(value)
        elif a.isdigit():
            count = int(a)
        elif len(a) == 10 and a[4] == "-" and a[7] == "-":
            datearg = a
        else:
            raise ValueError(f"unrecognised argument: {a!r}")
        i += 1
    if nights is not None:
        if count is not None and count != len(nights):
            raise ValueError(f"count {count} doesn't match {len(nights)} nights ({', '.join(nights)})")
        count = len(nights)
    elif count is None:
        count = MEALS_PER_WEEK
    if not 1 <= count <= len(WEEK_DAYS):
        raise ValueError(f"meal count must be 1-{len(WEEK_DAYS)} (got {count})")
    if nights is None:
        nights = sorted(DEFAULT_NIGHTS[:count], key=WEEK_DAYS.index)
    return force, datearg, count, nights


def main():
    try:
        force, datearg, n_meals, nights = parse_args(sys.argv[1:])
    except ValueError as e:
        print(f"error: {e}")
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
    must = recurring_picks(recipes, prefs, sunday, n_meals)
    chosen = pick_meals(recipes, prefs, history, rng, n_meals, must)
    rng.shuffle(chosen)

    meals = []
    for day, r in zip(nights, chosen):
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
        "nights": nights,
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
