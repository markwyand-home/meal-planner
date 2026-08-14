"""Build the weekly grocery list from a meal plan.

Aggregates every non-pantry-staple ingredient across the week's 4 recipes,
merges duplicate items (same normalized name + unit), and groups by store
section. Writes data/plans/<week>_grocery.json and prints a readable list.

Run: MEAL_PLANNER_HOME="<project dir>" cat scripts/grocery.py | python - [YYYY-MM-DD]
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

BASE = Path(os.environ.get("MEAL_PLANNER_HOME") or Path(__file__).resolve().parent.parent)
DATA = BASE / "data"

SECTION_ORDER = ["produce", "dairy-eggs", "bakery", "frozen", "pantry", "spices", "other"]
SECTION_LABEL = {
    "produce": "Produce", "dairy-eggs": "Dairy & Eggs", "bakery": "Bakery",
    "frozen": "Frozen", "pantry": "Pantry", "spices": "Spices", "other": "Other",
}


def week_sunday(argdate=None):
    if argdate:
        return date.fromisoformat(argdate)
    today = date.today()
    return today + timedelta(days=(6 - today.weekday()) % 7)


def fmt_qty(q, unit):
    if q is None:
        return ""
    q = round(q + 1e-9, 2)
    q = int(q) if abs(q - int(q)) < 0.01 else q
    if unit == "count" or unit is None:
        return f"{q}"
    return f"{q} {unit}"


def main():
    sunday = week_sunday(sys.argv[1] if len(sys.argv) > 1 else None)
    plan = json.loads((DATA / "plans" / f"{sunday.isoformat()}.json").read_text(encoding="utf-8"))
    recipes = {r["id"]: r for r in json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))["recipes"]}

    merged = {}  # (item, unit) -> {qty, sources, category}
    for meal in plan["meals"]:
        r = recipes[meal["id"]]
        for ing in r["ingredients"]:
            if ing["pantry_staple"]:
                continue
            key = (ing["item"], ing["unit"])
            e = merged.setdefault(key, {"item": ing["item"], "unit": ing["unit"], "quantity": 0.0,
                                        "has_qty": False, "category": ing["category"], "sources": []})
            if ing["quantity"] is not None:
                e["quantity"] += ing["quantity"]
                e["has_qty"] = True
            if r["name"] not in e["sources"]:
                e["sources"].append(r["name"])

    sections = {}
    for e in merged.values():
        qty = e["quantity"] if e["has_qty"] else None
        sections.setdefault(e["category"], []).append({
            "item": e["item"], "quantity": qty, "unit": e["unit"], "for": e["sources"],
            "display": (fmt_qty(qty, e["unit"]) + " " + e["item"]).strip(),
        })
    for items in sections.values():
        items.sort(key=lambda x: x["item"])

    out = {
        "week_of": plan["week_of"],
        "meals": [m["name"] for m in plan["meals"]],
        "sections": {k: sections[k] for k in SECTION_ORDER if k in sections},
        "note": "Pantry staples (salt, pepper, oils, soy sauce, common vinegars, sugar, flour, butter, eggs, rice, garlic) are excluded - check you have them.",
    }
    out_path = DATA / "plans" / f"{sunday.isoformat()}_grocery.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"grocery list written: {out_path}\n")
    total = 0
    for k in SECTION_ORDER:
        if k not in sections:
            continue
        print(f"-- {SECTION_LABEL[k]} --")
        for it in sections[k]:
            total += 1
            print(f"  {it['display']}   ({', '.join(it['for'])})")
    print(f"\n{total} items")


if __name__ == "__main__":
    main()
