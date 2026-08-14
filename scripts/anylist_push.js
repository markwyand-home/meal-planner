/**
 * Push the week's grocery list into AnyList.
 *
 * Credentials come from ~/.meal-planner/anylist.env (ANYLIST_EMAIL /
 * ANYLIST_PASSWORD), never printed. Target list from ANYLIST_LIST
 * (default "Groceries"). That file lives outside the project folder so it is
 * never synced to cloud storage or copied with the project.
 *
 * Run:  node scripts/anylist_push.js [YYYY-MM-DD]
 * The project folder is found from the script's location; override with
 * MEAL_PLANNER_HOME if you run it from elsewhere or pipe it via stdin.
 *
 * Idempotent: items already on the list (same name, unchecked) are skipped.
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

(async () => {
  const env = loadEnv(CRED_FILE);
  const email = env.ANYLIST_EMAIL, password = env.ANYLIST_PASSWORD;
  const listName = env.ANYLIST_LIST || "Groceries";
  if (!email || !password) {
    console.error(`AnyList credentials missing in ${CRED_FILE} (ANYLIST_EMAIL / ANYLIST_PASSWORD). ` +
      "See SETUP.md. Skipping push.");
    process.exit(2);
  }

  const week = weekSunday(process.argv[2]);
  const groceryPath = path.join(BASE, "data", "plans", `${week}_grocery.json`);
  const grocery = JSON.parse(fs.readFileSync(groceryPath, "utf-8"));

  const any = new AnyList({ email, password });
  await any.login();
  await any.getLists();
  const list = any.getListByName(listName);
  if (!list) {
    console.error(`List "${listName}" not found in AnyList. Available lists: ` +
      any.lists.map(l => l.name).join(", "));
    process.exit(3);
  }

  const existing = new Set(list.items.filter(i => !i.checked).map(i => i.name.toLowerCase()));
  let added = 0, skipped = 0;
  for (const [section, items] of Object.entries(grocery.sections)) {
    for (const it of items) {
      const name = it.display;
      if (existing.has(name.toLowerCase())) { skipped++; continue; }
      const item = any.createItem({ name });
      item.details = `${grocery.week_of} meal plan: ${it.for.join(", ")}`;
      await list.addItem(item);
      added++;
    }
  }
  console.log(`AnyList "${listName}": ${added} items added, ${skipped} already on list.`);
  process.exit(0);
})().catch(e => { console.error("AnyList push failed:", e.message); process.exit(1); });
