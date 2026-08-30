/**
 * Push the week's grocery list into AnyList.
 *
 * Credentials come from ~/.meal-planner/anylist.env (ANYLIST_EMAIL /
 * ANYLIST_PASSWORD), never printed. Target list from ANYLIST_LIST
 * (default "Groceries"). That file lives outside the project folder so it is
 * never synced to cloud storage or copied with the project.
 *
 * Run:  node scripts/anylist_push.js [YYYY-MM-DD]
 *       node scripts/anylist_push.js --clear   (removes every item from the list)
 * The project folder is found from the script's location; override with
 * MEAL_PLANNER_HOME if you run it from elsewhere or pipe it via stdin.
 *
 * Idempotent: items already on the list (same name, unchecked) are skipped.
 *
 * Before pushing, applies data/anylist_rules.json: drops likely-already-stocked
 * pantry items (spices, oils, grains, lentils, condiments, etc. — see that file
 * for the exact list) and, for fresh-produce ingredients, swaps the recipe
 * measurement ("2 tbsp lemon juice") for a whole-item buy ("1 lemon"). This only
 * affects what gets pushed to AnyList — data/plans/<week>_grocery.json and the
 * dashboard keep the full, recipe-accurate list untouched for cross-checking.
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

const BASE = process.env.MEAL_PLANNER_HOME ||
  (typeof __dirname !== "undefined" ? path.resolve(__dirname, "..") : process.cwd());

const CRED_FILE = path.join(os.homedir(), ".meal-planner", "anylist.env");

// The `anylist` package may sit next to the project or in a shared install.
const LIB_CANDIDATES = [
  path.join(BASE, "node_modules", "anylist"),
  path.join(os.homedir(), ".meal-planner", "node_modules", "anylist"),
  path.join(os.homedir(), "AppData", "Local", "meal-planner-anylist", "node_modules", "anylist"),
  "anylist",
];
let AnyList = null;
for (const candidate of LIB_CANDIDATES) {
  try { AnyList = require(candidate); break; } catch (e) { /* try next */ }
}
if (!AnyList) {
  console.error("Could not find the `anylist` package. Run:  npm install anylist\n" +
    "in the project folder (or ~/.meal-planner).");
  process.exit(4);
}

// minimal .env parser (no extra deps)
function loadEnv(file) {
  const env = {};
  if (!fs.existsSync(file)) return env;
  for (const line of fs.readFileSync(file, "utf-8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return env;
}

function weekSunday(arg) {
  if (arg) return arg;
  const d = new Date();
  d.setDate(d.getDate() + ((7 - d.getDay()) % 7));
  return d.toISOString().slice(0, 10);
}

function loadRules() {
  const rulesPath = path.join(BASE, "data", "anylist_rules.json");
  if (!fs.existsSync(rulesPath)) {
    return {
      exclude_categories: new Set(), exclude_keywords_regex: [], exclude_items: new Set(),
      include_keywords_regex: [], produce_conversions: {}, section_category_defaults: {}, item_category_map: {},
    };
  }
  const raw = JSON.parse(fs.readFileSync(rulesPath, "utf-8"));
  return {
    exclude_categories: new Set(raw.exclude_categories || []),
    exclude_keywords_regex: (raw.exclude_keywords_regex || []).map(p => new RegExp(p, "i")),
    exclude_items: new Set((raw.exclude_items || []).map(s => s.toLowerCase())),
    include_keywords_regex: (raw.include_keywords_regex || []).map(p => new RegExp(p, "i")),
    produce_conversions: raw.produce_conversions || {},
    section_category_defaults: raw.section_category_defaults || {},
    item_category_map: Object.fromEntries(Object.entries(raw.item_category_map || {}).map(([k, v]) => [k.toLowerCase(), v])),
  };
}

// include_keywords_regex overrides everything else below: an ingredient
// matching it (e.g. "chinese egg noodles or rice noodles", which also
// contains the excluded word "rice") is never treated as a pantry staple.
function isPantryStaple(it, category, rules) {
  const name = it.item.toLowerCase();
  if (rules.include_keywords_regex.some(re => re.test(name))) return false;
  if (rules.exclude_categories.has(category)) return true;
  if (rules.exclude_items.has(name)) return true;
  return rules.exclude_keywords_regex.some(re => re.test(name));
}

function fmtQty(q, unit) {
  if (q === null || q === undefined) return "";
  q = Math.round((q + 1e-9) * 100) / 100;
  const qStr = Math.abs(q - Math.round(q)) < 0.01 ? String(Math.round(q)) : String(q);
  if (unit === "count" || !unit) return qStr;
  return `${qStr} ${unit}`;
}

// For fresh produce, swap the recipe measurement for a whole-item buy (e.g.
// "2 tbsp lemon juice" -> "1 lemon"). See data/anylist_rules.json.
function applyProduceConversion(it, category, rules) {
  if (category !== "produce") return it;
  const conv = rules.produce_conversions[it.item];
  if (!conv) return it;
  const name = conv.name || it.item;
  const display = (fmtQty(1, conv.unit) + " " + name).trim();
  return { ...it, item: name, quantity: 1, unit: conv.unit, display };
}

// AnyList categoryMatchId for the app's built-in aisle headers. See
// data/anylist_rules.json's _category_note for the valid ids and reasoning.
function categoryFor(it, section, rules) {
  return rules.section_category_defaults[section]
    || rules.item_category_map[it.item.toLowerCase()]
    || "other";
}

(async () => {
  const env = loadEnv(CRED_FILE);
  const email = env.ANYLIST_EMAIL, password = env.ANYLIST_PASSWORD;
  const listName = env.ANYLIST_LIST || "Groceries";
  if (!email || !password) {
    console.error(`AnyList credentials missing in ${CRED_FILE} (ANYLIST_EMAIL / ANYLIST_PASSWORD). ` +
      "See SETUP.md. Skipping push.");
    process.exit(2);
  }

  const any = new AnyList({ email, password });
  await any.login();
  await any.getLists();
  const list = any.getListByName(listName);
  if (!list) {
    console.error(`List "${listName}" not found in AnyList. Available lists: ` +
      any.lists.map(l => l.name).join(", "));
    process.exit(3);
  }

  if (process.argv[2] === "--clear") {
    const toRemove = [...list.items];
    for (const item of toRemove) await list.removeItem(item);
    console.log(`AnyList "${listName}": removed ${toRemove.length} items.`);
    process.exit(0);
  }

  const week = weekSunday(process.argv[2]);
  const groceryPath = path.join(BASE, "data", "plans", `${week}_grocery.json`);
  const grocery = JSON.parse(fs.readFileSync(groceryPath, "utf-8"));
  const rules = loadRules();

  const existing = new Set(list.items.filter(i => !i.checked).map(i => i.name.toLowerCase()));
  let added = 0, skipped = 0, staples = 0;
  const staplesOmitted = [], converted = [];
  for (const [section, items] of Object.entries(grocery.sections)) {
    for (const raw of items) {
      if (isPantryStaple(raw, section, rules)) { staples++; staplesOmitted.push(raw.display); continue; }
      const it = applyProduceConversion(raw, section, rules);
      if (it.display !== raw.display) converted.push(`${raw.display}  ->  ${it.display}`);
      const name = it.display;
      if (existing.has(name.toLowerCase())) { skipped++; continue; }
      const item = any.createItem({ name, categoryMatchId: categoryFor(raw, section, rules) });
      item.details = `${grocery.week_of} meal plan: ${raw.for.join(", ")}`;
      await list.addItem(item);
      existing.add(name.toLowerCase());
      added++;
    }
  }
  console.log(`AnyList "${listName}": ${added} items added, ${skipped} already on list, ${staples} pantry staples omitted.`);
  if (staplesOmitted.length) console.log(`  Omitted: ${staplesOmitted.join(", ")}`);
  if (converted.length) console.log(`  Converted to whole-item: ${converted.join("; ")}`);
  process.exit(0);
})().catch(e => { console.error("AnyList push failed:", e.message); process.exit(1); });
