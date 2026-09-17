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
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

BASE = Path(os.environ.get("MEAL_PLANNER_HOME") or Path(__file__).resolve().parent.parent)
DATA = BASE / "data"

EXPECTED_DINNERS = 4
PAGES_RECIPE_PREFIX = "https://markwyand-home.github.io/meal-planner/recipes/"

SECTION_LABEL = {"produce": "Produce", "dairy-eggs": "Dairy & Eggs", "bakery": "Bakery",
                 "frozen": "Frozen", "pantry": "Pantry", "spices": "Spices", "other": "Other"}
PROTEIN_LABEL = {"tofu": "Tofu", "tempeh": "Tempeh", "halloumi": "Halloumi", "paneer": "Paneer",
                 "chickpeas": "Chickpeas", "lentils": "Lentils", "beans": "Beans", "eggs": "Eggs",
                 "cheese": "Cheese", "nuts-seeds": "Nuts & Seeds", "meat": "Meat", "none": "Veg-forward"}
RATING_GLYPH = {"loved": "&#9733;&#9733;&#9733;", "liked": "&#9733;&#9733;", "ok": "&#9733;", "disliked": "&#9785;"}
RATING_WORD = {"loved": "Loved", "liked": "Liked", "ok": "Just ok", "disliked": "Disliked"}
NUM_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven"}

FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
               '<rect width="32" height="32" rx="7" fill="#2F6540"/>'
               '<path d="M8.5 23.5c0-8.5 5.5-13.5 15-14.5 1 9.5-4.5 15-12 15z" fill="#FAF7F0"/>'
               '<path d="M8.5 23.5c3.2-3.4 6.6-5.6 11-7.2" fill="none" stroke="#2F6540" '
               'stroke-width="1.7" stroke-linecap="round"/></svg>')


def week_sunday(argdate=None):
    if argdate:
        return date.fromisoformat(argdate)
    today = date.today()
    return today + timedelta(days=(6 - today.weekday()) % 7)


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def fmt_day(d):
    return d.strftime("%B %d").replace(" 0", " ")


def read_json(path, fallback=None):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


# --- AnyList parity -------------------------------------------------------
# Ported from scripts/anylist_push.js so the dashboard can show which items
# actually reach the phone. The grocery JSON itself stays recipe-accurate.

def load_anylist_rules():
    raw = read_json(DATA / "anylist_rules.json", {}) or {}
    return {
        "exclude_categories": set(raw.get("exclude_categories", [])),
        "exclude_items": {s.lower() for s in raw.get("exclude_items", [])},
        "exclude_re": [re.compile(p, re.I) for p in raw.get("exclude_keywords_regex", [])],
        "include_re": [re.compile(p, re.I) for p in raw.get("include_keywords_regex", [])],
        "produce_conversions": raw.get("produce_conversions", {}),
    }


def is_pantry_staple(item, section, rules):
    name = item["item"].lower()
    if any(r.search(name) for r in rules["include_re"]):
        return False
    if section in rules["exclude_categories"]:
        return True
    if name in rules["exclude_items"]:
        return True
    return any(r.search(name) for r in rules["exclude_re"])


def anylist_display(item, section, rules):
    if section != "produce":
        return item["display"]
    conv = rules["produce_conversions"].get(item["item"])
    if not conv:
        return item["display"]
    name = conv.get("name", item["item"])
    unit = conv.get("unit")
    qty = "1" if unit in (None, "count") else "1 " + unit
    return (qty + " " + name).strip()


def recipe_href(meal, recipes):
    """Same-tab relative link for our own recipe pages; source_url otherwise."""
    page_url = recipes.get(meal["id"], {}).get("page_url") or ""
    if page_url.startswith(PAGES_RECIPE_PREFIX):
        return "recipes/" + page_url[len(PAGES_RECIPE_PREFIX):], False
    if page_url:
        return page_url, True
    return meal.get("source_url", ""), True


CSS = """
  :root {
    --paper:#FAF7F0; --card:#FFFFFF; --ink:#242D26; --muted:#636B61; --line:#E4DFD3;
    --leaf:#2F6540; --leaf-soft:#EAF2EC; --tomato:#95401F; --tomato-soft:#F6E9E2;
    --honey:#8A6714; --serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }
  @media (prefers-color-scheme: dark) { :root {
    --paper:#161B17; --card:#1F2620; --ink:#E7E9E3; --muted:#9AA398; --line:#333B34;
    --leaf:#8CC29B; --leaf-soft:#24322A; --tomato:#E09A78; --tomato-soft:#3A2A22; --honey:#D3AC58;
  } }
  html { background:var(--paper); scrollbar-color:var(--line) var(--paper); }
  body { font-family:var(--sans); color:var(--ink); margin:0; padding:0 16px 64px;
         -webkit-font-smoothing:antialiased; }
  ::selection { background:var(--leaf-soft); color:var(--ink); }
  main { max-width:720px; margin:0 auto; }
  a { color:var(--leaf); text-underline-offset:3px; }
  :focus-visible { outline:2px solid var(--leaf); outline-offset:3px; border-radius:2px; }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden;
             clip:rect(0 0 0 0); white-space:nowrap; border:0; }

  header.week { padding:40px 0 8px; border-bottom:2px solid var(--ink); margin-bottom:20px; }
  h1 { font-family:var(--serif); font-weight:500; font-size:clamp(28px,6vw,40px); margin:0 0 6px; text-wrap:balance; }
  .tagline { color:var(--ink); margin:0 0 12px; font-size:15px; max-width:60ch; }
  .stamp { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 14px; margin:0 0 16px;
           font-size:12.5px; color:var(--muted); }
  .stamp time { font-variant-numeric:tabular-nums; }
  .jump { color:var(--leaf); font-weight:600; text-decoration:none; border-bottom:1px solid var(--line); }
  .jump:hover { border-bottom-color:var(--leaf); }

  .notice { border:1px solid var(--tomato); background:var(--tomato-soft); color:var(--tomato);
            border-radius:6px; padding:12px 14px; margin:0 0 16px; font-size:14px; max-width:62ch; }
  .notice strong { display:block; font-weight:700; margin-bottom:2px; }
  .notice p { margin:0; color:var(--ink); }

  h2 { font-family:var(--serif); font-weight:500; font-size:24px; margin:36px 0 14px; scroll-margin-top:16px; }
  h2:first-of-type { margin-top:0; }
  .h2count { font-size:14px; color:var(--muted); font-family:var(--sans); font-variant-numeric:tabular-nums; }

  .meal { display:flex; gap:16px; background:var(--card); border:1px solid var(--line);
          border-radius:6px; padding:16px; margin-bottom:12px; }
  .meal.tonight { border-color:var(--leaf); box-shadow:0 2px 10px -4px rgba(47,101,64,.35); }
  .dayrail { display:flex; flex-direction:column; align-items:center; min-width:46px;
             border-right:1px solid var(--line); padding-right:14px; }
  .dow { font-size:12px; letter-spacing:.1em; text-transform:uppercase; color:var(--leaf); font-weight:700; }
  .dom { font-size:13px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .tonight .dow, .tonight .dom { color:var(--leaf); font-weight:700; }
  .mealbody { flex:1; min-width:0; }
  .meal h3 { font-family:var(--serif); font-size:20px; font-weight:500; margin:0 0 8px; text-wrap:balance; }
  .meal h3 a { color:var(--ink); text-decoration:none; border-bottom:1px solid var(--line); }
  .meal h3 a:hover { border-bottom-color:var(--leaf); color:var(--leaf); }
  .rating { color:var(--honey); font-size:14px; margin-left:8px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
  .chip { font-size:12px; padding:2px 9px; border-radius:999px; border:1px solid var(--line); color:var(--muted); }
  .chip-tonight { font-size:12px; font-weight:700; letter-spacing:.04em; padding:2px 9px;
                  border-radius:999px; background:var(--leaf); color:var(--card); border-color:transparent; }
  .chip-protein { background:var(--leaf-soft); color:var(--leaf); border-color:transparent; font-weight:600; }
  .chip-veg { color:var(--leaf); border-color:var(--leaf); }
  .chip-meat { background:var(--tomato-soft); color:var(--tomato); border-color:transparent; font-weight:600; }
  .subnote { font-size:13px; color:var(--tomato); margin:4px 0 6px; max-width:62ch; }
  dl.nut { display:flex; gap:22px; margin:10px 0 0; padding-top:10px; border-top:1px dashed var(--line); }
  dl.nut div { display:flex; flex-direction:column; }
  dl.nut dt { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  dl.nut dd { margin:0; font-variant-numeric:tabular-nums; font-size:15px; }
  .est { font-size:11px; color:var(--muted); font-style:italic; }

  .summary { border-top:1px solid var(--line); border-bottom:1px solid var(--line);
             padding:12px 0 14px; margin:18px 0 0; }
  .summary-label { font-size:11px; letter-spacing:.08em; text-transform:uppercase;
                   color:var(--muted); margin-bottom:8px; }
  .summary dl { display:flex; gap:0; margin:0; }
  .summary dl div { flex:1; }
  .summary dt { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  .summary dd { margin:2px 0 0; font-family:var(--serif); font-size:19px; font-variant-numeric:tabular-nums; }

  details { background:var(--card); border:1px solid var(--line); border-radius:6px; margin-bottom:10px; padding:0 16px; }
  summary { font-weight:600; padding:12px 0; cursor:pointer; }
  summary .count { color:var(--muted); font-weight:400; font-size:13px; margin-left:6px;
                   font-variant-numeric:tabular-nums; }
  details ul { list-style:none; margin:0 0 12px; padding:0; }
  details li { border-top:1px solid var(--line); }
  details label { display:flex; align-items:flex-start; gap:12px; padding:10px 0; cursor:pointer; }
  details input[type=checkbox] { accent-color:var(--leaf); width:18px; height:18px; flex:none; margin:1px 0 0; }
  .gtext { min-width:0; }
  .gitem { display:block; font-size:15px; line-height:1.35; }
  .gfor { display:block; font-size:11.5px; color:var(--muted); margin-top:2px; }
  .tag { display:inline-block; font-size:11px; letter-spacing:.04em; text-transform:uppercase;
         font-weight:700; border-radius:3px; padding:1px 6px; margin-left:8px; vertical-align:1px; }
  .tag-off { border:1px solid var(--line); color:var(--muted); }
  .tag-buy { background:var(--leaf-soft); color:var(--leaf); }
  details input[type=checkbox]:checked ~ .gtext .gitem { text-decoration:line-through; color:var(--muted); }
  details input[type=checkbox]:checked ~ .gtext { opacity:.55; }
  .gtext, .gitem { transition:opacity .22s cubic-bezier(.2,.7,.3,1), color .22s cubic-bezier(.2,.7,.3,1); }
  @media (prefers-reduced-motion:reduce) { .gtext, .gitem { transition:none; } }

  table.hist { width:100%; border-collapse:collapse; font-size:14px; }
  table.hist td { padding:8px 10px 8px 0; border-top:1px solid var(--line); vertical-align:top; }
  td.wkdate { color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }
  .muted { color:var(--muted); }
  .note { font-size:13px; color:var(--muted); max-width:62ch; }
  footer { margin-top:48px; font-size:13px; color:var(--muted); border-top:1px solid var(--line);
           padding-top:14px; max-width:62ch; }
  footer strong { color:var(--ink); }

  @media (max-width:420px) {
    .summary dl { flex-wrap:wrap; gap:10px 0; }
    .summary dl div { flex:0 0 50%; }
  }
"""

SCRIPT = """
(function () {
  var root = document.querySelector('main');
  if (!root) return;
  var today = new Date();
  var iso = today.getFullYear() + '-' +
    String(today.getMonth() + 1).padStart(2, '0') + '-' +
    String(today.getDate()).padStart(2, '0');

  // Mark tonight's dinner at view time, not build time. The badge is real text
  // so it reaches the accessible name, not a CSS ::before a screen reader misses.
  var cards = root.querySelectorAll('.meal[data-date]');
  for (var i = 0; i < cards.length; i++) {
    var isTonight = cards[i].getAttribute('data-date') === iso;
    cards[i].classList.toggle('tonight', isTonight);
    var badge = cards[i].querySelector('[data-tonight]');
    if (badge) badge.hidden = !isTonight;
  }

  // Say so when the page is showing a week that has already passed.
  var stale = document.getElementById('stale-notice');
  if (stale) {
    var end = stale.getAttribute('data-plan-end');
    stale.hidden = !(end && iso > end);
  }

  // Keep checkboxes across a trip to AnyList and back.
  var week = root.getAttribute('data-week') || 'week';
  var key = 'meal-planner:groceries:' + week;
  var boxes = root.querySelectorAll('input[type=checkbox][data-key]');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch (e) { saved = {}; }
  for (var j = 0; j < boxes.length; j++) {
    if (saved[boxes[j].getAttribute('data-key')]) boxes[j].checked = true;
  }
  root.addEventListener('change', function (ev) {
    var box = ev.target;
    if (!box || box.type !== 'checkbox' || !box.hasAttribute('data-key')) return;
    var state = {};
    for (var k = 0; k < boxes.length; k++) {
      if (boxes[k].checked) state[boxes[k].getAttribute('data-key')] = 1;
    }
    try { localStorage.setItem(key, JSON.stringify(state)); } catch (e) { /* private mode */ }
  });
})();
"""


def fmt_stamp(dt):
    return dt.strftime("%a %b %d, %I:%M %p").replace(" 0", " ")


def head(title):
    favicon = "data:image/svg+xml," + quote(FAVICON_SVG, safe="")
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<meta name=\"theme-color\" content=\"#FAF7F0\" media=\"(prefers-color-scheme: light)\">\n"
            "<meta name=\"theme-color\" content=\"#161B17\" media=\"(prefers-color-scheme: dark)\">\n"
            "<link rel=\"icon\" href=\"" + favicon + "\">\n"
            "<title>" + esc(title) + "</title>\n"
            "<style>" + CSS + "</style>\n"
            "</head>\n<body>\n")


def render_empty(sunday, generated, reason):
    return (head("Wyand Dinner Plan — no plan for " + sunday.isoformat())
            + '<main data-week="' + esc(sunday.isoformat()) + '">\n'
            "  <header class=\"week\">\n"
            "    <h1>No plan for the week of " + esc(fmt_day(sunday + timedelta(days=1))) + "</h1>\n"
            '    <p class="tagline">Sunday\'s run has not produced a dinner plan for this week yet.</p>\n'
            '    <p class="stamp"><time datetime="' + esc(generated.isoformat(timespec="minutes")) + '">Checked '
            + esc(fmt_stamp(generated)) + "</time></p>\n"
            "  </header>\n"
            '  <div class="notice"><strong>Nothing to show</strong>'
            "<p>" + esc(reason) + " Run <code>python scripts/planner.py " + esc(sunday.isoformat())
            + "</code> and rebuild.</p></div>\n"
            "</main>\n</body>\n</html>\n")


def main():
    sunday = week_sunday(sys.argv[1] if len(sys.argv) > 1 else None)
    wk = sunday.isoformat()
    generated = datetime.now()
    out = BASE / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    plan = read_json(DATA / "plans" / (wk + ".json"))
    grocery = read_json(DATA / "plans" / (wk + "_grocery.json"))
    if plan is None or not plan.get("meals"):
        out.write_text(render_empty(sunday, generated, "No plan file exists for " + wk + "."), encoding="utf-8")
        print("dashboard written (empty state): " + str(out))
        return
    if grocery is None:
        grocery = {"sections": {}, "note": "", "week_of": wk}

    history = read_json(DATA / "history.json", {"weeks": []})
    prefs = read_json(DATA / "preferences.json", {"ratings": {}})
    recipes = {r["id"]: r for r in read_json(DATA / "recipes.json", {"recipes": []})["recipes"]}
    rules = load_anylist_rules()

    meals = plan["meals"]
    n_meals = len(meals)
    first_day = sunday + timedelta(days=1)
    # The span names the week the plan is for, not how many meals landed in it;
    # a short week is reported by the partial-plan notice instead.
    last_day = sunday + timedelta(days=max(EXPECTED_DINNERS, n_meals))
    span = fmt_day(first_day) + " – " + fmt_day(last_day)

    veg = sum(1 for m in meals if m["vegetarian"])
    proteins = [m["protein"] for m in meals]
    bits = [NUM_WORD.get(n_meals, str(n_meals)) + (" dinners" if n_meals != 1 else " dinner")]
    if veg == n_meals:
        bits.append("all vegetarian")
    elif veg == 0:
        bits.append("none vegetarian")
    else:
        bits.append(str(veg) + " of " + str(n_meals) + " vegetarian")
    if len(set(proteins)) == n_meals:
        bits.append("no protein repeated")
    else:
        repeated = sorted({PROTEIN_LABEL.get(p, p).lower() for p in proteins if proteins.count(p) > 1})
        bits.append("repeats " + ", ".join(repeated))
    tagline = " &middot; ".join(bits)

    meal_cards = []
    for i, m in enumerate(meals):
        d = sunday + timedelta(days=1 + i)
        n = m["nutrition_per_serving"]
        est = ' <span class="est">est.</span>' if n.get("source") == "estimated" else ""
        veg_badge = ('<span class="chip chip-veg">Vegetarian</span>' if m["vegetarian"]
                     else '<span class="chip chip-meat">Contains meat</span>')
        sub = '<p class="subnote">Veg option: ' + esc(m["veg_sub_note"]) + '</p>' if m.get("veg_sub_note") else ""
        time_chip = '<span class="chip">' + str(m["total_min"]) + ' min</span>' if m.get("total_min") else ""
        rating = prefs.get("ratings", {}).get(m["id"], {}).get("rating")
        rating_html = ""
        if rating:
            rating_html = ('<span class="rating" aria-hidden="true">' + RATING_GLYPH.get(rating, "") + '</span>'
                           '<span class="sr-only"> — rated ' + esc(RATING_WORD.get(rating, rating)) + '</span>')
        href, external = recipe_href(m, recipes)
        target = ' target="_blank" rel="noopener"' if external else ""
        tonight = " tonight" if d == generated.date() else ""
        meal_cards.append(f"""
      <article class="meal{tonight}" data-date="{d.isoformat()}">
        <div class="dayrail"><span class="dow">{m["day"][:3]}</span><span class="dom">{d.strftime('%m/%d').lstrip('0')}</span></div>
        <div class="mealbody">
          <h3><a href="{esc(href)}"{target}>{esc(m["name"])}</a>{rating_html}</h3>
          <div class="chips">
            <span class="chip chip-tonight" data-tonight hidden>Tonight</span>
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
    n_pushed = 0
    for key, items in grocery.get("sections", {}).items():
        rows = []
        section_pushed = 0
        for it in items:
            pushed = not is_pantry_staple(it, key, rules)
            buys = anylist_display(it, key, rules) if pushed else ""
            if pushed:
                section_pushed += 1
            if not pushed:
                tag = '<span class="tag tag-off">not in AnyList</span>'
            elif buys and buys != it["display"]:
                tag = '<span class="tag tag-buy">buy ' + esc(buys) + '</span>'
            else:
                tag = ""
            rows.append('<li><label><input type="checkbox" data-key="' + esc(it["display"]) +
                        '" aria-label="' + esc(it["display"]) + '">'
                        '<span class="gtext"><span class="gitem">' + esc(it["display"]) + tag + '</span>'
                        '<span class="gfor">' + esc(", ".join(it["for"])) + '</span></span></label></li>')
        n_items += len(items)
        n_pushed += section_pushed
        grocery_html.append('<details open><summary>' + SECTION_LABEL.get(key, key) +
                            ' <span class="count">' + str(section_pushed) + ' of ' + str(len(items)) +
                            ' in AnyList</span></summary><ul>' + "".join(rows) + '</ul></details>')

    hist_rows = []
    for wkh in reversed(history.get("weeks", [])[-8:]):
        names = " · ".join(esc(recipes[mid]["name"]) if mid in recipes else esc(mid) for mid in wkh["meals"])
        hist_rows.append('<tr><td class="wkdate">' + esc(wkh["week_of"]) + '</td><td>' + names + '</td></tr>')
    hist_html = ("<table class='hist'><tbody>" + "".join(hist_rows) + "</tbody></table>") if hist_rows \
        else "<p class='note'>First week — history will build from here.</p>"

    stamp = fmt_stamp(generated)
    plan_end = sunday + timedelta(days=6)
    stale_now = date.today() > plan_end

    notices = ('<div class="notice" id="stale-notice" role="status" data-plan-end="' + plan_end.isoformat() + '"'
               + ("" if stale_now else " hidden") + '>'
               '<strong>This is not the current week.</strong>'
               "<p>The plan below ran for the week of " + esc(fmt_day(first_day)) +
               ". Sunday's run has not replaced it yet.</p></div>\n")
    if n_meals != EXPECTED_DINNERS:
        notices += ('  <div class="notice"><strong>Partial plan.</strong>'
                    "<p>This week has " + str(n_meals) + " dinner" + ("s" if n_meals != 1 else "") +
                    ", not the usual " + str(EXPECTED_DINNERS) +
                    " — the Sunday run may not have finished.</p></div>\n")

    page = (head("Wyand Dinner Plan — Week of " + span)
            + '<main data-week="' + esc(wk) + '">\n  <header class="week">\n'
            + "    <h1>Week of " + esc(span) + "</h1>\n"
            + '    <p class="tagline">' + tagline + "</p>\n"
            + '    <p class="stamp"><time datetime="' + esc(generated.isoformat(timespec="minutes")) + '">Generated '
            + esc(stamp) + "</time>"
            + ('<a class="jump" href="#groceries">Grocery list &mdash; ' + str(n_pushed) + " of " + str(n_items)
               + " in AnyList</a>" if n_items else "")
            + "</p>\n  </header>\n  "
            + notices
            + "  <h2>Dinners</h2>"
            + "".join(meal_cards)
            + '\n  <section class="summary">\n    <div class="summary-label">Average per serving</div>\n    <dl>\n'
            + "      <div><dt>Cal</dt><dd>" + str(avg["calories"]) + "</dd></div>\n"
            + "      <div><dt>Protein</dt><dd>" + str(avg["protein_g"]) + " g</dd></div>\n"
            + "      <div><dt>Carbs</dt><dd>" + str(avg["carbs_g"]) + " g</dd></div>\n"
            + "      <div><dt>Fat</dt><dd>" + str(avg["fat_g"]) + " g</dd></div>\n"
            + "    </dl>\n  </section>\n"
            + '\n  <h2 id="groceries">Grocery list <span class="h2count">(' + str(n_pushed) + " of "
            + str(n_items) + " pushed to AnyList)</span></h2>\n"
            + "".join(grocery_html)
            + ('\n  <p class="note">' + esc(grocery.get("note", "")) + "</p>\n" if grocery.get("note") else "\n")
            + "\n  <h2>Recent weeks</h2>\n" + hist_html + "\n"
            + "  <footer>\n    <strong>Rate a meal:</strong> tell Claude — e.g. “we loved the ratatouille, the tacos were just ok” —\n"
            + "    and it updates the preferences that steer future weeks. Checkboxes stay on this device and don’t sync to AnyList.\n"
            + "  </footer>\n</main>\n<script>" + SCRIPT + "</script>\n</body>\n</html>\n")

    out.write_text(page, encoding="utf-8")
    print("dashboard written: " + str(out) + " (" + str(len(page)) + " chars, "
          + str(n_pushed) + "/" + str(n_items) + " grocery items pushed to AnyList)")


if __name__ == "__main__":
    main()
