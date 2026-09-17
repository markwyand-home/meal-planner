---
target: the dashboard
total_score: 21
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "file:G:\\My Drive\\Claude\\agents\\meal-planner\\docs\\index.html"
target_fingerprint: "sha256:e014c491771afee5ead12a7aa2071ba201f531fe9120ec61760f3b1711ecb34e"
target_path: "G:\\My Drive\\Claude\\agents\\meal-planner\\docs\\index.html"
timestamp: 2026-09-09T13-07-15Z
slug: docs-index-html
---
Method: dual-agent (A: a252ebdf081e69081 · B: adc804a4c2b88a532)

# Design Critique — docs/index.html (weekly dinner dashboard)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 1 | No generated-at date, no freshness signal, no AnyList push status. Live page shows week of Aug 31 on Sep 9, silently. |
| 2 | Match System / Real World | 2 | "0.46 cup sesame oil", "6 garlic", "pasta, polenta, or grain of choice" as one checkbox. Header always claims Mon-Thu. |
| 3 | User Control and Freedom | 2 | Meal links target="_blank"; recipe pages have no link back to the week. Dead end on phone. |
| 4 | Consistency and Standards | 3 | Heading order h1 to h3 to h3 to h2 to h2, confirmed by both detectors. Two inline font-size overrides. |
| 5 | Error Prevention | 2 | Nothing prevents shopping last week's list. Dark-mode CSS present with no toggle or JS. |
| 6 | Recognition Rather Than Recall | 2 | Rating glyphs have no legend. No "tonight" marker. |
| 7 | Flexibility and Efficiency | 2 | 19 grocery checkboxes reset on reload. No jump-to-groceries anchor. |
| 8 | Aesthetic and Minimalist Design | 3 | Restrained and handsome; noise is the full recipe title repeated in all 19 grocery rows. |
| 9 | Error Recovery | 1 | Stale dashboard and partial run — both declared failures in PRODUCT.md — have no visual representation. |
| 10 | Help and Documentation | 3 | Footer "Rate a meal: tell Claude..." is excellent contextual help. |
| **Total** | | **21/40** | **Acceptable (low end)** |

No heuristic scored n/a; Operate surface with real accelerator and help surface area.

## Design Specificity Verdict

**Authored, not generic — but the authorship stops at the surface.**

LLM assessment: The visual language is specific — warm paper ground, old-style serif headings, leaf/tomato/honey palette, the 44px MON / 8-31 day rail, protein chip leading every card. No SaaS template ships that; swapping content would look wrong. But the structure is category-interchangeable: hero, four uniform cards, stats strip, accordion, history table, footer. The product's core claim (variety across and within weeks) exists only as a hardcoded sentence. The history table is a flat date/names dump proving nothing about protein rotation. The nutrition strip is the heaviest element on the page despite being the least actionable content. Missed character: 23 recipes is a closed known corpus with no "cooked 4 times" or "new to rotation" note; servings shown raw ("serves 6") to a two-person household.

Deterministic scan: CLI detector found 2 findings in docs/index.html (flat-type-hierarchy, skipped-heading), 0 across all 15 recipe pages. Browser detector found 9: 7 line-length, 1 kicker-above-heading, 1 skipped-heading. After triage, 3 real: skipped-heading (both detectors, independently) and 2 genuinely over-long prose lines (94 and 111 chars, index.html:95 and :127).

False positives: flat-type-hierarchy is a parser limitation — h1 uses clamp(28px,6vw,40px) which the static scanner cannot resolve; live h1 computes to 40px, h1/h2 = 1.82:1, and the browser detector did not fire the rule. kicker-above-heading targets marketing eyebrows; this one is the only place the page names itself. 5 of 7 line-length hits are history-table cells containing dot-delimited lists, not running prose.

Visual overlays: injection succeeded and the detector ran in the page; overlay tab and temporary server have since been cleaned up.

## Overall Impression

The most important finding is not a design problem: this week's plan has 2 meals, not 4, and one of the two is meat (confirmed in data/plans/2026-08-30.json). The dashboard renders that under a confident header reading "Four dinners - vegetarian-first - no protein repeated," across a span always printed as Monday-Thursday. The page is lying, in its largest type, about the one thing the product exists to guarantee — and it cannot tell you it is a week stale. PRODUCT.md principle 3 says a partial run is a failed run and must be reported plainly; the dashboard is the one place that is not implemented.

Biggest opportunity: make the page report the truth about itself.

## What's Working

1. The day rail. A 44px left gutter with MON / 8/31 in leaf-green caps and a hairline separator. Gives every card an anchor the eye lands on first and makes the week read as a calendar. Cheap structure doing expensive work.
2. The recipe pages. 16px ingredients, 17px steps, numbered leaf circles, no ads. Zero detector findings across all 15. Best-realized surface in the project and correct for a phone at the stove.
3. The footer's rating instruction. Teaches the feedback loop in the user's own voice and admits the checkboxes do not sync. Honest and unbuyable off the shelf.

## Priority Issues

[P0] The header asserts things that are false.
Tagline is a hardcoded string (build_dashboard.py:184); span always "monday - thursday" (line 55). This week is 2 meals ending Tuesday, half of it meat.
Why it matters: the promise is "no decisions"; a header that misstates the week is the fastest way to lose trust.
Fix: derive both from plan["meals"] — len(meals) dinners, span from first to last actual meal date, veg claim as a count ("1 of 2 vegetarian") not a slogan.
Suggested command: /impeccable clarify

[P1] A stale dashboard looks identical to a current one.
No generated-at time anywhere on the page.
Why it matters: opening the bookmark midweek gives no way to tell whether Sunday's run happened. It has not, and the page is silent.
Fix: emit a time element "Generated Sun Aug 30, 6:47am" under the eyebrow; when the plan's Sunday is not the current week, render a tomato-bordered banner saying so.
Suggested command: /impeccable harden

[P1] "19 items — also pushed to AnyList" is wrong, in the exact scene the dashboard exists for.
Applying anylist_rules.json, 16 of 19 push; sesame oil, chicken broth, dried Italian herbs are filtered. Cross-checking dashboard against AnyList in the store is a named use case and the page gives no delta.
Fix: apply rules at build time, tag filtered rows "not in AnyList", change count to "16 of 19 pushed."
Suggested command: /impeccable clarify

[P1] No "tonight," and the recipe link is a one-way door.
Every meal renders identically; links open in a new tab; recipe pages offer only "Original recipe" in the footer.
Why it matters: the dominant scene is a phone at the stove on a weeknight; both failures land in it.
Fix: highlight today's card (leaf border, TONIGHT eyebrow); add "Week of Aug 31" back-link to recipe footer; drop target="_blank" for internal pages.
Suggested command: /impeccable layout

[P2] Light-mode contrast fails AA on the most product-specific elements.
chip-protein 4.44:1 at 12px, chip-meat 4.35:1, rating honey-on-white 3.16:1 — all below 4.5:1. Dark mode is fine; light mode is what you get in a bright store.
Fix: darken --leaf to ~#2F6540, --tomato to ~#95401F, --honey to ~#8A6714 in the light block only.
Suggested command: /impeccable audit

## Persona Red Flags

Casey (distracted mobile, one-handed) — worst hit. Checks off eight Produce items, switches to AnyList, returns: all 19 checkboxes blank. No JavaScript, no localStorage. Grocery list starts at y approx 853px on 375x812 — a full swipe before the first checkbox, no anchor link. Checkbox visuals 13x13px, hard to read at arm's length in a store. Nothing in the thumb zone.

Sam (screen reader / keyboard) — heading outline h1 to h3 to h3 to h2 to h2, so the four meals belong to no section. .meal h3 a:focus { outline: none } removes the focus ring and substitutes a colour change: focus indicated by colour alone. Every checkbox announces the whole label ("2 cup baby spinach Better Than Takeout Dan Dan Noodles") nineteen times. Ratings live in a title attribute with no text equivalent.

Riley (stress tester) — the page is already inside its own edge case: two meals under a "Four dinners" tagline. data/history.json contains two entries both dated 2026-08-23 with different menus (confirmed directly); the table renders both with no dedupe. "0.46 cup sesame oil" is consolidation arithmetic leaking to the surface. build_dashboard.py throws on a missing plan file rather than rendering an empty state; there is no zero-meal design.

## Minor Observations

- ~12 lines of dead CSS: :root[data-theme="dark"] and ["light"] blocks in both generators, no toggle, no JS to set the attribute.
- PROTEIN_LABEL map and the entire CSS block duplicated verbatim across build_dashboard.py and build_recipe_pages.py. They will drift.
- "Avg cal / serv" wraps to two lines at 375px, breaking the four-tile baseline.
- No favicon, no theme-color, no Open Graph, for a page meant to live on a phone home screen.
- Card border 1.33:1 against card fill; in light mode the card affordance is carried only by the paper/white difference.
- Recipe pages have no step-completion state and no screen-wake — the one place a little JS would pay for itself.
- The .est estimated-quantity marker exists but never fires in this render; untested path.

## Questions to Consider

- What if the default view were tonight's meal, full-bleed, with everything else below the fold?
- The history table is the only evidence variety is working. What if it were a protein grid, so a repeat is visible rather than inferable?
- Why does a two-person household see "serves 6"? What if quantities read as "two dinners + two lunches"?
- What is the confident version of the stale state — should the page refuse to show a plan it cannot vouch for?
