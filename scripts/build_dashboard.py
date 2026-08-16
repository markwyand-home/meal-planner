"""Render docs/index.html from the meal-planner data files.

Reads data/plans/<week>.json, <week>_grocery.json, history.json,
preferences.json, recipes.json and writes docs/index.html, the page GitHub
Pages serves at https://markwyand-home.github.io/meal-planner/. The Sunday
session commits and pushes docs/ so the live page updates automatically.

Run: MEAL_PLANNER_HOME="<dir>" cat scripts/build_dashboard.py | python - [YYYY-MM-DD]
"""

import html
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

BASE = Path(os.environ.get("MEAL_PLANNER_HOME") or Path(__file__).resolve().parent.parent)
DATA = BASE / "data"

SECTION_LABEL = {"produce": "Produce", "dairy-eggs": "Dairy & Eggs", "bakery": "Bakery",
                 "frozen": "Frozen", "pantry": "Pantry", "spices": "Spices", "other": "Other"}
PROTEIN_LABEL = {"tofu": "Tofu", "tempeh": "Tempeh", "halloumi": "Halloumi", "paneer": "Paneer",
                 "chickpeas": "Chickpeas", "lentils": "Lentils", "beans": "Beans", "eggs": "Eggs",
                 "cheese": "Cheese", "nuts-seeds": "Nuts & Seeds", "meat": "Meat", "none": "Veg-forward"}
RATING_GLYPH = {"loved": "&#9733;&#9733;&#9733;", "liked": "&#9733;&#9733;", "ok": "&#9733;", "disliked": "&#9785;"}


def week_sunday(argdate=None):
    if argdate:
        return date.fromisoformat(argdate)
    today = date.today()
    return today + timedelta(days=(6 - today.weekday()) % 7)


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def fmt_day(d):
    return d.strftime("%B %d").replace(" 0", " ")


def main():
    sunday = week_sunday(sys.argv[1] if len(sys.argv) > 1 else None)
    wk = sunday.isoformat()
    plan = json.loads((DATA / "plans" / (wk + ".json")).read_text(encoding="utf-8"))
    grocery = json.loads((DATA / "plans" / (wk + "_grocery.json")).read_text(encoding="utf-8"))
    history = json.loads((DATA / "history.json").read_text(encoding="utf-8")) if (DATA / "history.json").exists() else {"weeks": []}
    prefs = json.loads((DATA / "preferences.json").read_text(encoding="utf-8")) if (DATA / "preferences.json").exists() else {"ratings": {}}
    recipes = {r["id"]: r for r in json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))["recipes"]}

    monday = sunday + timedelta(days=1)
    thursday = sunday + timedelta(days=4)
    span = fmt_day(monday) + " – " + fmt_day(thursday)

    meal_cards = []
    for i, m in enumerate(plan["meals"]):
        d = sunday + timedelta(days=1 + i)
        n = m["nutrition_per_serving"]
        est = ' <span class="est">est.</span>' if n.get("source") == "estimated" else ""
        veg_badge = ('<span class="chip chip-veg">Vegetarian</span>' if m["vegetarian"]
                     else '<span class="chip chip-meat">Contains meat</span>')
        sub = '<p class="subnote">Veg option: ' + esc(m["veg_sub_note"]) + '</p>' if m.get("veg_sub_note") else ""
        time_chip = '<span class="chip">' + str(m["total_min"]) + ' min</span>' if m.get("total_min") else ""
        rating = prefs.get("ratings", {}).get(m["id"], {}).get("rating")
        rating_html = '<span class="rating" title="' + esc(rating) + '">' + RATING_GLYPH.get(rating, "") + '</span>' if rating else ""
        recipe_link = recipes.get(m["id"], {}).get("page_url") or m["source_url"]
        meal_cards.append(f"""
      <article class="meal">
        <div class="dayrail"><span class="dow">{m["day"][:3]}</span><span class="dom">{d.strftime('%m/%d').lstrip('0')}</span></div>
        <div class="mealbody">
          <h3><a href="{esc(recipe_link)}" target="_blank" rel="noopener">{esc(m["name"])}</a>{rating_html}</h3>
          <div class="chips">
            <span class="chip chip-protein">{PROTEIN_LABEL.get(m["protein"], m["protein"])}</span>
            {veg_badge}{time_chip}
            <span class="chip">serves {m["servings"]}</span>
          </div>
          {sub}
          <dl class="nut"><div><dt>Cal</dt><dd>{n["calories"]}{est}</dd></div>
            <div><dt>Protein</dt><dd>{n["protein_g"]} g</dd></div>
            <div><dt>Carbs</dt><dd>{n["carbs_g"]} g</dd></div>
            <div><dt>Fat</dt><dd>{n["fat_g"]} g</dd></div></dl>
        </div>
      </article>""")

    avg = plan["nutrition_avg_per_serving"]

    grocery_html = []
    n_items = 0
    for key, items in grocery["sections"].items():
        rows = "".join(
            '<li><label><input type="checkbox"><span>' + esc(it["display"]) + '</span>'
            '<em>' + esc(", ".join(it["for"])) + '</em></label></li>' for it in items)
        n_items += len(items)
        grocery_html.append('<details open><summary>' + SECTION_LABEL.get(key, key) +
                            ' <span class="count">' + str(len(items)) + '</span></summary><ul>' + rows + '</ul></details>')

    hist_rows = []
    for wkh in reversed(history.get("weeks", [])[-8:]):
        names = " · ".join(esc(recipes[mid]["name"]) if mid in recipes else esc(mid) for mid in wkh["meals"])
        hist_rows.append('<tr><td class="wkdate">' + esc(wkh["week_of"]) + '</td><td>' + names + '</td></tr>')
    hist_html = ("<table class='hist'><tbody>" + "".join(hist_rows) + "</tbody></table>") if hist_rows else "<p class='muted'>First week — history will build from here.</p>"

    css = """
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
  body { font-family:var(--sans); color:var(--ink); margin:0; padding:0 16px 64px;
         -webkit-font-smoothing:antialiased; }
  main { max-width:720px; margin:0 auto; }
  header.week { padding:40px 0 8px; border-bottom:2px solid var(--ink); margin-bottom:24px; }
  .eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--leaf); font-weight:600; }
  h1 { font-family:var(--serif); font-weight:500; font-size:clamp(28px,6vw,40px); margin:6px 0 4px; text-wrap:balance; }
  .tagline { color:var(--muted); margin:0 0 16px; font-size:14px; }
  h2 { font-family:var(--serif); font-weight:500; font-size:22px; margin:40px 0 14px; }
  .meal { display:flex; gap:16px; background:var(--card); border:1px solid var(--line);
          border-radius:6px; padding:16px; margin-bottom:12px; }
  .dayrail { display:flex; flex-direction:column; align-items:center; min-width:44px;
             border-right:1px solid var(--line); padding-right:14px; }
  .dow { font-size:12px; letter-spacing:.1em; text-transform:uppercase; color:var(--leaf); font-weight:700; }
  .dom { font-size:13px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .mealbody { flex:1; min-width:0; }
  .meal h3 { font-family:var(--serif); font-size:19px; font-weight:500; margin:0 0 8px; text-wrap:balance; }
  .meal h3 a { color:var(--ink); text-decoration:none; border-bottom:1px solid var(--line); }
  .meal h3 a:hover, .meal h3 a:focus { border-bottom-color:var(--leaf); color:var(--leaf); outline:none; }
  .rating { color:var(--honey); font-size:14px; margin-left:8px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
  .chip { font-size:12px; padding:2px 9px; border-radius:999px; border:1px solid var(--line); color:var(--muted); }
  .chip-protein { background:var(--leaf-soft); color:var(--leaf); border-color:transparent; font-weight:600; }
  .chip-veg { color:var(--leaf); border-color:var(--leaf); }
  .chip-meat { background:var(--tomato-soft); color:var(--tomato); border-color:transparent; font-weight:600; }
  .subnote { font-size:13px; color:var(--tomato); margin:4px 0 6px; }
  dl.nut { display:flex; gap:22px; margin:10px 0 0; padding-top:10px; border-top:1px dashed var(--line); }
  dl.nut div { display:flex; flex-direction:column; }
  dl.nut dt { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  dl.nut dd { margin:0; font-variant-numeric:tabular-nums; font-size:15px; }
  .est { font-size:10px; color:var(--muted); font-style:italic; }
  .summary { display:flex; gap:0; background:var(--leaf-soft); border-radius:6px; padding:14px 6px; margin:18px 0 0; }
  .summary div { flex:1; text-align:center; }
  .summary dt { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--leaf); }
  .summary dd { margin:2px 0 0; font-family:var(--serif); font-size:20px; font-variant-numeric:tabular-nums; }
  details { background:var(--card); border:1px solid var(--line); border-radius:6px; margin-bottom:10px; padding:0 16px; }
  summary { font-weight:600; padding:12px 0; cursor:pointer; }
  summary .count { color:var(--muted); font-weight:400; font-size:13px; margin-left:6px; }
  details ul { list-style:none; margin:0 0 12px; padding:0; }
  details li { border-top:1px solid var(--line); }
  details label { display:flex; align-items:baseline; gap:10px; padding:8px 0; cursor:pointer; }
  details label em { margin-left:auto; font-style:normal; font-size:11px; color:var(--muted); text-align:right; max-width:45%; }
  details input[type=checkbox] { accent-color:var(--leaf); }
  details input[type=checkbox]:checked ~ span { text-decoration:line-through; color:var(--muted); }
  table.hist { width:100%; border-collapse:collapse; font-size:14px; }
  table.hist td { padding:8px 10px 8px 0; border-top:1px solid var(--line); vertical-align:top; }
  td.wkdate { color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }
  .muted { color:var(--muted); }
  footer { margin-top:48px; font-size:13px; color:var(--muted); border-top:1px solid var(--line); padding-top:14px; }
  footer strong { color:var(--ink); }
"""

    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>Wyand Dinner Plan — Week of " + esc(span) + "</title>\n"
            "<style>" + css + "</style>\n"
            "</head>\n<body>\n"
            '<main>\n  <header class="week">\n    <div class="eyebrow">Wyand dinner plan</div>\n'
            "    <h1>Week of " + esc(span) + "</h1>\n"
            '    <p class="tagline">Four dinners &middot; vegetarian-first &middot; no protein repeated</p>\n'
            "  </header>\n"
            + "".join(meal_cards) +
            '\n  <dl class="summary">\n'
            "    <div><dt>Avg cal / serv</dt><dd>" + str(avg["calories"]) + "</dd></div>\n"
            "    <div><dt>Protein</dt><dd>" + str(avg["protein_g"]) + " g</dd></div>\n"
            "    <div><dt>Carbs</dt><dd>" + str(avg["carbs_g"]) + " g</dd></div>\n"
            "    <div><dt>Fat</dt><dd>" + str(avg["fat_g"]) + " g</dd></div>\n"
            "  </dl>\n"
            '\n  <h2>Grocery list <span class="count muted" style="font-size:14px">(' + str(n_items) +
            " items — also pushed to AnyList)</span></h2>\n"
            + "".join(grocery_html) +
            '\n  <p class="muted" style="font-size:13px">' + esc(grocery["note"]) + "</p>\n"
            "\n  <h2>Recent weeks</h2>\n" + hist_html + "\n"
            "  <footer>\n    <strong>Rate a meal:</strong> tell Claude — e.g. “we loved the ratatouille, the tacos were just ok” —\n"
            "    and it updates the preferences that steer future weeks. Checkboxes above are for in-store use and don’t sync back.\n"
            "  </footer>\n</main>\n</body>\n</html>\n")

    out = BASE / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("dashboard written: " + str(out) + " (" + str(len(page)) + " chars)")


if __name__ == "__main__":
    main()
