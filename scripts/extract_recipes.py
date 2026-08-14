"""Extract structured recipe data from saved .mhtml pages.

Usage: python extract_recipes.py <project_dir>
Reads <project_dir>/Recipes/*.mhtml, writes <project_dir>/data/recipes_raw.json.
"""

import email
import json
import re
import sys
from html import unescape
from pathlib import Path
from html.parser import HTMLParser

BASE = Path(sys.argv[1])
RECIPES_DIR = BASE / "Recipes"
OUT = BASE / "data" / "recipes_raw.json"


def mhtml_html(path: Path) -> str:
    msg = email.message_from_bytes(path.read_bytes())
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


class LdJsonCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_ld = False
        self.chunks = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type", "").strip() == "application/ld+json":
            self.in_ld = True
            self.chunks = []

    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld:
            self.in_ld = False
            self.blocks.append("".join(self.chunks))

    def handle_data(self, data):
        if self.in_ld:
            self.chunks.append(data)


def find_recipe_objects(obj):
    if isinstance(obj, dict):
        t = obj.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if any(str(x).lower() == "recipe" for x in types):
            yield obj
        for v in obj.values():
            yield from find_recipe_objects(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_recipe_objects(item)


def clean(s):
    if not isinstance(s, str):
        return s
    return unescape(re.sub(r"\s+", " ", s)).strip()


def parse_duration(iso):
    if not iso or not isinstance(iso, str):
        return None
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", iso)
    if not m:
        return None
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    total = d * 1440 + h * 60 + mi
    return total or None


def extract(path: Path):
    html = mhtml_html(path)
    if not html:
        return None
    collector = LdJsonCollector()
    collector.feed(html)
    for block in collector.blocks:
        block = block.strip()
        if not block:
            continue
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", block))
            except json.JSONDecodeError:
                continue
        for recipe in find_recipe_objects(data):
            nutrition = recipe.get("nutrition") or {}
            if isinstance(nutrition, dict):
                nutrition = {
                    k: clean(v)
                    for k, v in nutrition.items()
                    if k != "@type" and isinstance(v, (str, int, float))
                }
            yields = recipe.get("recipeYield")
            if isinstance(yields, list):
                yields = ", ".join(str(y) for y in yields)
            url = recipe.get("url") or recipe.get("mainEntityOfPage")
            if isinstance(url, dict):
                url = url.get("@id")
            instructions = recipe.get("recipeInstructions")
            n_steps = len(instructions) if isinstance(instructions, list) else None
            return {
                "file": path.name,
                "name": clean(recipe.get("name")),
                "source_url": clean(url) if isinstance(url, str) else None,
                "ingredients": [clean(i) for i in recipe.get("recipeIngredient", []) if isinstance(i, str)],
                "yield": clean(str(yields)) if yields else None,
                "prep_min": parse_duration(recipe.get("prepTime")),
                "cook_min": parse_duration(recipe.get("cookTime")),
                "total_min": parse_duration(recipe.get("totalTime")),
                "nutrition": nutrition,
                "n_instruction_steps": n_steps,
                "keywords": clean(recipe.get("keywords")) if isinstance(recipe.get("keywords"), str) else None,
            }
    return None


def main():
    results, missing = [], []
    for path in sorted(RECIPES_DIR.glob("*.mhtml")):
        try:
            rec = extract(path)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {path.name}: {e}", file=sys.stderr)
            rec = None
        if rec and rec["ingredients"]:
            results.append(rec)
            print(f"OK    {path.name} -> {rec['name']} ({len(rec['ingredients'])} ing, nutrition={'yes' if rec['nutrition'] else 'no'})")
        else:
            missing.append(path.name)
            print(f"MISS  {path.name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"recipes": results, "missing": missing}, indent=2), encoding="utf-8")
    print(f"\n{len(results)} extracted, {len(missing)} missing -> {OUT}")


if __name__ == "__main__":
    main()
