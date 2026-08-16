"""Render a clean, instructions-only HTML page for one or more recipes.

Reads data/recipes.json and writes docs/recipes/<id>.html for each recipe that
has an "instructions" field. No commentary, ads, or comment threads — just the
ingredients and steps, sized for reading on a phone while cooking. GitHub Pages
serves these at https://markwyand-home.github.io/meal-planner/recipes/<id>.html
— the Sunday session records that URL into recipes.json's "page_url" field
(first time only; it's reused on every later commit), which the dashboard
links to instead of the noisy source_url.

Run: MEAL_PLANNER_HOME="<dir>" cat scripts/build_recipe_pages.py | python - [recipe-id ...]
No ids given -> builds a page for every recipe that has instructions.
"""

import html
import json
import os
import sys
from pathlib import Path

BASE = Path(os.environ.get("MEAL_PLANNER_HOME") or Path(__file__).resolve().parent.parent)
DATA = BASE / "data"
OUT_DIR = BASE / "docs" / "recipes"

CSS = """
  :root {
    --paper:#FAF7F0; --card:#FFFFFF; --ink:#242D26; --muted:#6B7369; --line:#E4DFD3;
    --leaf:#3E7B4F; --leaf-soft:#EAF2EC; --tomato:#B0512E; --tomato-soft:#F6E9E2;
    --honey:#B58A2E; --serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }
  @media (prefers-color-scheme: dark) { :root {
    --paper:#161B17; --card:#1F2620; --ink:#E7E9E3; --muted:#9AA398; --line:#333B34;
    --leaf:#8CC29B; --leaf-soft:#24322A; --tomato:#D98B66; --tomato-soft:#3A2A22; --honey:#D3AC58;
  } }
  :root[data-theme="dark"] {
    --paper:#161B17; --card:#1F2620; --ink:#E7E9E3; --muted:#9AA398; --line:#333B34;
    --leaf:#8CC29B; --leaf-soft:#24322A; --tomato:#D98B66; --tomato-soft:#3A2A22; --honey:#D3AC58;
  }
  :root[data-theme="light"] {
    --paper:#FAF7F0; --card:#FFFFFF; --ink:#242D26; --muted:#6B7369; --line:#E4DFD3;
    --leaf:#3E7B4F; --leaf-soft:#EAF2EC; --tomato:#B0512E; --tomato-soft:#F6E9E2; --honey:#B58A2E;
  }
  html { background:var(--paper); }
  body { font-family:var(--sans); color:var(--ink); margin:0; padding:0 20px 56px;
         -webkit-font-smoothing:antialiased; }
  main { max-width:640px; margin:0 auto; }
  header { padding:32px 0 16px; border-bottom:2px solid var(--ink); margin-bottom:24px; }
  .eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--leaf); font-weight:600; }
  h1 { font-family:var(--serif); font-weight:500; font-size:clamp(26px,7vw,36px); margin:6px 0 12px; text-wrap:balance; }
  .meta { display:flex; flex-wrap:wrap; gap:8px; }
  .chip { font-size:12px; padding:3px 10px; border-radius:999px; border:1px solid var(--line); color:var(--muted); }
  .chip-protein { background:var(--leaf-soft); color:var(--leaf); border-color:transparent; font-weight:600; }
  .chip-veg { color:var(--leaf); border-color:var(--leaf); }
  .chip-meat { background:var(--tomato-soft); color:var(--tomato); border-color:transparent; font-weight:600; }
  h2 { font-family:var(--serif); font-weight:500; font-size:20px; margin:32px 0 12px; }
  ul.ing { list-style:none; margin:0; padding:0; }
  ul.ing li { padding:9px 0; border-top:1px solid var(--line); font-size:16px; line-height:1.4; }
  ul.ing li:last-child { padding-bottom:0; }
  ol.steps { margin:0; padding:0; list-style:none; counter-reset:step; }
  ol.steps li { counter-increment:step; display:flex; gap:14px; padding:16px 0; border-top:1px solid var(--line); }
  ol.steps li:last-child { padding-bottom:0; }
  ol.steps li::before {
    content:counter(step); flex:none; width:28px; height:28px; border-radius:50%;
    background:var(--leaf-soft); color:var(--leaf); font-weight:700; font-size:14px;
    display:flex; align-items:center; justify-content:center;
  }
  ol.steps p { margin:0; font-size:17px; line-height:1.55; padding-top:2px; }
  .notes { margin-top:32px; padding:14px 16px; background:var(--leaf-soft); border-radius:6px;
           font-size:14px; color:var(--ink); }
  .notes strong { color:var(--leaf); }
  footer { margin-top:40px; font-size:13px; color:var(--muted); border-top:1px solid var(--line); padding-top:14px; }
  footer a { color:var(--muted); }
"""

PROTEIN_LABEL = {"tofu": "Tofu", "tempeh": "Tempeh", "halloumi": "Halloumi", "paneer": "Paneer",
                 "chickpeas": "Chickpeas", "lentils": "Lentils", "beans": "Beans", "eggs": "Eggs",
                 "cheese": "Cheese", "nuts-seeds": "Nuts & Seeds", "meat": "Meat", "none": "Veg-forward"}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def render(recipe):
    veg_badge = ('<span class="chip chip-veg">Vegetarian</span>' if recipe["vegetarian"]
                 else '<span class="chip chip-meat">Contains meat</span>')
    time_chip = f'<span class="chip">{recipe["total_min"]} min</span>' if recipe.get("total_min") else ""
    protein_chip = f'<span class="chip chip-protein">{PROTEIN_LABEL.get(recipe["protein_primary"], recipe["protein_primary"])}</span>'
    ing_html = "".join(f"<li>{esc(ing['raw'])}</li>" for ing in recipe["ingredients"])
    steps_html = "".join(f"<li><p>{esc(step)}</p></li>" for step in recipe["instructions"])
    notes_html = (f'<div class="notes"><strong>Notes:</strong> {esc(recipe["notes"])}</div>'
                  if recipe.get("notes") else "")
    source_html = (f'<a href="{esc(recipe["source_url"])}" target="_blank" rel="noopener">Original recipe &rarr;</a>'
                   if recipe.get("source_url") else "")

    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>" + esc(recipe["name"]) + "</title>\n"
            "<style>" + CSS + "</style>\n"
            "</head>\n<body>\n"
            "<main>\n  <header>\n    <div class=\"eyebrow\">Recipe</div>\n"
            "    <h1>" + esc(recipe["name"]) + "</h1>\n"
            "    <div class=\"meta\">" + protein_chip + veg_badge + time_chip +
            f'<span class="chip">serves {recipe["servings"]}</span></div>\n'
            "  </header>\n"
            "  <h2>Ingredients</h2>\n  <ul class=\"ing\">" + ing_html + "</ul>\n"
            "  <h2>Instructions</h2>\n  <ol class=\"steps\">" + steps_html + "</ol>\n"
            + notes_html +
            "\n  <footer>" + source_html + "</footer>\n</main>\n</body>\n</html>\n")


def main():
    recipes = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))["recipes"]
    by_id = {r["id"]: r for r in recipes}
    ids = sys.argv[1:] or [r["id"] for r in recipes if r.get("instructions")]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid in ids:
        r = by_id.get(rid)
        if not r:
            print(f"SKIP  {rid}: not found in recipes.json")
            continue
        if not r.get("instructions"):
            print(f"SKIP  {rid}: no instructions extracted yet")
            continue
        out = OUT_DIR / f"{rid}.html"
        out.write_text(render(r), encoding="utf-8")
        print(f"built  {out}")


if __name__ == "__main__":
    main()
