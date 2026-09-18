---
target: the dashboard
total_score: 24
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 4
target_identity: "file:G:\\My Drive\\Claude\\agents\\meal-planner\\docs\\index.html"
target_fingerprint: "sha256:98aa12353752f5451e955da53e805182ebd424841f47fe20f179c89c632723be"
target_path: "G:\\My Drive\\Claude\\agents\\meal-planner\\docs\\index.html"
timestamp: 2026-09-09T13-36-28Z
slug: docs-index-html
closed: true
---
Method: dual-agent (A: a9a833e415a9e04a5 · B: a49cda10a054f7c4e)

# Design Critique — docs/index.html (re-run after clarify/layout/audit/harden pass)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 (was 1) | Generated stamp, stale + partial notices, AnyList counts present. With no card matching today, page never says "no dinner tonight." |
| 2 | Match System / Real World | 2 (=) | "0.46 cup sesame oil", "6 garlic", "0.5 red bell pepper". "Other" holds tofu and ground chicken. ISO dates in history. |
| 3 | User Control and Freedom | 2 (=) | Recipe back-links now exist; grocery list has no uncheck-all, no swap-a-meal path. |
| 4 | Consistency and Standards | 3 (=) | Palette and type carry cleanly into recipe pages; three list grammars on one page. |
| 5 | Error Prevention | 3 (was 2) | Partial/stale notices and staples footnote prevent real mistakes. |
| 6 | Recognition Rather Than Recall | 3 (was 2) | Per-item "for" line excellent; staples footnote ~1,900px below the first tag it explains. |
| 7 | Flexibility and Efficiency | 1 (was 2) | Checkbox state persists, but 3,644px page with no collapse-all, no hide-checked, no back-to-top. |
| 8 | Aesthetic and Minimalist Design | 3 (=) | Calm and well-spaced; 12 unused nutrition figures and two stacked red boxes above the first meal. |
| 9 | Error Recovery | 2 (was 1) | Both notices name the problem plainly and offer no recovery; empty state hands the reader a shell command. |
| 10 | Help and Documentation | 2 (was 3) | No visible legend for star ratings, no inline meaning for "not in AnyList". |
| **Total** | | **24/40** (was 21/40) | **Acceptable (60%)** |

No heuristic scored n/a.

## Design Specificity Verdict

Authored in voice and palette; still generic in structure.

LLM assessment: Content that genuinely cannot exist elsewhere — the tagline is the house rules rendered as a sentence; the per-item "not in AnyList" / "buy 1 bag baby spinach" tags implement PRODUCT.md principle 4 in the layout; the footer speaks in the household's voice. Against that, the skeleton is stock admin panel: five content types all rendered as the same 6px-radius 1px-bordered rectangle. "Recent weeks" remains a bare ISO-date table — the one place the closed 23-recipe corpus could show personality. Sharpest observation: PRODUCT.md names no nutrition goal at all, yet twelve nutrition figures get their own dashed rule and outrank the vegetarian substitution note, the thing a vegetarian-first house needs on its one meat night.

Deterministic scan: CLEAN. Zero findings on docs/index.html (was 2) and zero across all 15 recipe pages (was 0). Verified not a false negative — a control file with deliberate 9px text and #eee-on-#fff returned exit 2 with low-contrast and undersized-ui-text, confirming the detector fires.

Browser detector: 2 findings. cream-palette flags the warm paper #FAF7F0 — the committed visual world; a pinned aesthetic outranks a saturated-pattern warning, dismissed. body-text-viewport-edge flags a 141-char paragraph 16px from the screen edge at 375px — real but minor.

Measured, both themes at 375px: lowest contrast of 31 text roles is 5.16:1 light / 5.91:1 dark; nothing below 4.5:1. Smallest functional text 11px; nothing below. No horizontal overflow at 375 or 1024. Heading outline h1 → h2 → h3 → h3 → h2 → h2, no skips. Zero outline:none rules anywhere. Grocery rows 58-79px, checkboxes 18x18px. Every accessibility target from the previous run verified fixed.

## Overall Impression

The mechanical floor is clean and the honesty problem is solved: the page reports its own state accurately, and the AnyList parity layer, view-time staleness and checkbox persistence were all verified working. Score moved 21 to 24.

What the fixes did not touch is now what holds it back: the page still answers the weeknight question last, and the composition still contributes nothing the typeface and palette do not. Two of the fixes also introduced new defects (Tonight marker, h1 span).

## What's Working

1. The "for" attribution on every grocery row. "1 shallot / Better Than Takeout Dan Dan Noodles" turns a flat list into something reason-able in the aisle — skip a meal, know what to drop.
2. The AnyList parity layer (is_pantry_staple / anylist_display ported from anylist_push.js into build_dashboard.py). Per-item and per-section, the page says what reached the phone. Makes an invisible filter auditable — the trust mechanism the positioning depends on.
3. View-time state. Tonight and staleness computed from the browser clock, not build time, so a Wednesday visit is honest about what Sunday produced.

## Priority Issues

[P1] The "Tonight" marker is invisible to a screen reader — introduced by the last pass.
Implemented as .tonight .chips::before { content:"Tonight" }. Confirmed: the string appears exactly once in the file, inside the CSS. No DOM text node, so it is absent from the accessible name. The page's single most important state is CSS-only.
Fix: emit a real <span class="tonight-badge" hidden>Tonight</span> and have the script unhide it; give #stale-notice role="status" so its appearance is announced.

[P1] The h1 relabels the week — introduced by the last pass.
Span derived from len(meals) (build_dashboard.py:321), so a 2-meal week renders "Week of August 31 – September 1" — a two-day span — directly above a banner announcing the plan is partial. Header contradicts the notice beneath it.
Fix: span the intended week (Monday–Thursday) and let the partial banner carry the shortfall, rather than silently shrinking the week to fit the data.

[P1] The weeknight question is still answered last, and "nothing tonight" is not answered at all.
Measured at 375x812: header plus banners = 503px; first meal title at y=520; second meal fully below the fold. Today nothing matches and the page says nothing.
Fix: a line under the h1 the script fills with tonight's meal, time and link — or "No dinner planned for tonight" when nothing matches.

[P1] The store hierarchy is inverted.
Recipe measurement renders at 15px, purchase form as an 11px tag. In the aisle the buy is a bag, not two cups — the un-actionable number is first.
Fix: swap them when they differ; purchase form at 15px, recipe measurement demoted into the "for" line.

[P2] Machine quantities break the domestic register.
"0.46 cup sesame oil", "6 garlic", "0.5 red bell pepper". Loudest tell that a script rather than a household wrote the page; "6 garlic" is ambiguous (cloves or heads).
Fix: vulgar fractions, pluralized units, a noun on bare counts.

## Persona Red Flags

Casey (one-handed phone) — the only navigation affordance, the jump link, measures 185x18px at the top of the screen: under the 44pt minimum and out of the thumb zone. Grocery section runs 2,292px with no collapse-all and no back-to-top. Credit: checkbox state verified surviving a reload; row tap targets 310x58-79px.

Sam (screen reader) — the Tonight bug above. The rating glyphs are done correctly (aria-hidden plus .sr-only word), which makes the Tonight omission an oversight rather than a pattern. Day rail is still two unlabeled spans.

Riley (stress tester) — the h1/banner contradiction; duplicated 2026-08-23 history rows still render with no comment; data-key is the raw display string, so an identical item in two sections would share one checkbox; render_empty() tells a household member to run python scripts/planner.py.

## Minor Observations

- "Meat" (protein chip) and "Contains meat" sit adjacent saying the same thing.
- Day rail prints "9/01" — lstrip('0') strips only the month's leading zero.
- localStorage keys accumulate one per week forever, unpruned.
- Recipe pages have ingredient lists but no checkboxes while the dashboard does — same act, two grammars.
- The pantry-staples note appears once, after all four sections, far from the tags it explains.
- theme-color for both schemes is a genuinely nice mobile touch most static pages skip.

## Questions to Consider

- What if the page opened with one sentence — "Tonight: Sheet Pan Ratatouille, 45 minutes" — and everything else lived below it?
- Has anyone in this house ever changed a meal because of a calorie count? If not, why do twelve nutrition figures outweigh the vegetarian substitution note?
- history.json and preferences.json are already loaded. What would this page feel like if it were allowed to remember — "fourth time this year," "Erin rated this loved in June"?
- Should a stale, partial week render the full dashboard at all, or collapse to one honest card saying what happened and what to do next?
