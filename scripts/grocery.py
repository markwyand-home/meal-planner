"""Build the weekly grocery list from a meal plan.

Aggregates every non-pantry-staple ingredient across the week's 4 recipes,
merges duplicate items (same normalized name + unit), and groups by store
section. Writes data/plans/<week>_grocery.json and prints a readable list.

Run: MEAL_PLANNER_HOME="<project dir>" cat scripts/grocery.py | python - [YYYY-MM-DD]
"""

import json
import os
import re
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


# Units whose noun reads naturally after the ingredient ("6 basil leaves"), versus
# the majority that read before it ("4 cloves garlic", "1 can coconut milk").
SUFFIX_UNITS = {"leaf", "sprig"}
PLURAL = {"cup": "cups", "bag": "bags", "pint": "pints", "package": "packages",
          "bunch": "bunches", "piece": "pieces", "clove": "cloves", "can": "cans",
          "head": "heads", "stalk": "stalks", "slice": "slices", "leaf": "leaves",
          "sprig": "sprigs", "ear": "ears"}
VULGAR = {1: "⅛", 2: "¼", 3: "⅜", 4: "½",
          5: "⅝", 6: "¾", 7: "⅞"}


def fmt_qty(q, unit):
    """Quantity in kitchen register: 0.46 -> 1/2, and units pluralized."""
    if q is None:
        return ""
    whole, rem = divmod(round(q * 8), 8)
    qty = (str(whole) if whole else "") + VULGAR.get(rem, "")
    qty = qty or "0"
    if unit in (None, "count"):
        return qty
    plural = whole > 1 or (whole == 1 and rem)
    return f"{qty} {PLURAL[unit] if plural and unit in PLURAL else unit}"


# Items are stored singular so two recipes' "lime" and "limes" consolidate into one
# line; the plural is produced here instead. Names that are already plural or mass
# nouns ("chickpeas", "capers") are left alone.
IRREGULAR_ITEM = {"sweet potato": "sweet potatoes", "potato": "potatoes",
                  "tomato": "tomatoes", "avocado": "avocados"}


def plural_item(name):
    if name in IRREGULAR_ITEM:
        return IRREGULAR_ITEM[name]
    if not re.fullmatch(r"[a-z][a-z \-']*", name) or name.endswith("s"):
        return name
    if re.search(r"(ch|sh|x|z)$", name):
        return name + "es"
    if re.search(r"[^aeiou]y$", name):
        return name[:-1] + "ies"
    return name + "s"


def fmt_display(item, q, unit, qualifier=None):
    if q is None:
        return f"{item}, {qualifier}" if qualifier else item
    if unit in SUFFIX_UNITS:
        noun = PLURAL[unit] if (q > 1 and unit in PLURAL) else unit
        return f"{fmt_qty(q, None)} {item} {noun}"
    if unit in (None, "count") and q > 1:
        item = plural_item(item)
    return (fmt_qty(q, unit) + " " + item).strip()


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
                                        "has_qty": False, "category": ing["category"], "sources": [],
                                        "qualifier": ing.get("qualifier")})
            if not e["qualifier"] and ing.get("qualifier"):
                e["qualifier"] = ing["qualifier"]
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
            "display": fmt_display(e["item"], qty, e["unit"], e["qualifier"]),
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
