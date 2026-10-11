# Product card with today's prices, a 30-day chart, and a shop link — Plan Brief

> Full plan: `context/changes/product-card-decision/plan.md`

## What & Why

A signed-in user needs one screen to decide whether to restock a watched product and in which shop. The card shows the product name, each shop's price for today, a 30-day line per shop, the lowest price ever recorded, and a link to that product in that shop.

## Starting Point

Sign-in, tracked products, shop pages, and Warsaw daily promo prices are already stored. Home shows only the username and a staff add link. There is no product page and no chart.

## Desired End State

On 10 October 2026 the home page lists every tracked product by name and shows no prices. The card's chart runs from 11 September through 10 October. Rossmann and DOZ at 19.99 PLN today are both marked Cheapest. A shop with no price today shows No price and still links to its page. A missing day stays on the axis, and the line joins the priced days around it. Lowest recorded price can be 10.00 PLN from before the chart.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| 30-day window | 30 calendar dates ending today | On 10 October the chart starts 11 September, so 10 September is outside | Plan |
| Missing chart day | Connect the line; the day stays on the axis with no point | A continuous line was chosen over a break or a dropped day | Plan |
| Cheapest shop | Mark every shop tied for today's lowest price | A shop with no price today is not a candidate | Plan |
| Shop with no price today | Show the shop, no amount, keep the link | Yesterday's price is not labeled today | Plan |
| Opening the card | Name-only links on the signed-in home | Today's lowest price on that list is the next slice | Plan |
| Lowest recorded price | All-time minimum of each day's latest amount | The number can be older than the chart and is labeled as the lowest recorded price | Plan |
| Drawing the chart | Inline SVG in the page | The app has no chart library or script files | Plan |
| Shop order on the card | Shop-page insert order | The add confirmation already lists pages that way | Plan |
| Home name order | Case-insensitive name, then id | The list is for finding a product | Plan |
| Y-axis floor | Lowest chart price minus 50 PLN, never below 0 | Ticks then continue every 10 PLN through the highest chart price | Plan |
| Chart legend | Shop name and a sample of its line, inside the chart to the right of the plot | A reader can tell which line is which shop | Plan |
| Shop link | Opens the shop page in a new tab | The card stays open | Plan |
| Product list name | Same-tab link to that product's card | `/products/` is the staff list, and the name is how a staff user opens the card | Plan |

## Scope

**In scope:**

- A login-required card for any tracked product
- Today's shop prices, Cheapest on every tied shop, No price when today is missing, and the stored shop URL
- A 30-date SVG with one line per shop, connecting across empty days
- The lowest recorded price, including dates outside the chart
- Name-only links to those cards on the signed-in home page
- A Home link to the main page on every screen
- A Y axis, a shop legend, new-tab shop links, and a same-tab product name on `/products/`

**Out of scope:**

- Favorites, and today's lowest price on the home list
- Changing or removing a product
- Description, availability, shipping, a horizon switch, a buy-now badge, guest access, and favoriting from the card
- A chart library, a new table, or a change to price recording

## Architecture / Approach

Home loads every product, sorted by case-insensitive name, then id. The card view loads one product and calls `card_figures(product, timezone.localdate())`. That function reuses the existing daily-price rule and returns shop rows, thirty amounts per shop, and the all-time low. The template draws the rows and an inline SVG. No new tables.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Card figures | Tested numbers for the window, gaps, ties, and the all-time low | A raw minimum would treat a superseded same-day amount as the low |
| 2. Card page | The login-required screen and SVG | The line can look like a price existed on an empty day |
| 3. Home links | Name-only links, plus a Home control on every page | Prices leaking onto home would take over the next slice |
| 4. Chart reading | Y axis, legend, and the two link targets | A 50 PLN offset below a cheap price would go negative |

**Prerequisites:** Sign-in, add-product, and calendar-day prices are done. `TIME_ZONE` is already `Europe/Warsaw`. No new packages.
**Estimated effort:** About 2 sessions across 3 phases for one person after hours.

## Open Risks & Assumptions

- The line across a gap can be read as a price on the empty day. The empty day has no point, and the manual check confirms that.
- A later slice may show favorites as a subset of tracked products. This list is every tracked product, with no prices, so that slice can add the day's lowest price here.
- Which timezone bounds "today" stays an open, non-blocking question. This plan uses Europe/Warsaw, which settings already use.
- A same-day price change means the earlier amount is not that day's price. The all-time low follows the latest amount for each day.

## Success Criteria (Summary)

- A signed-in user opens a product from the home list by name.
- The card shows today's shop prices, marks every cheapest shop, links to each shop page, and shows No price when today has no row.
- The chart is 30 dates through today, one line per shop connecting across empty days, and the lowest recorded price is shown even when it is older than the chart.
- The Y axis starts 50 PLN below the lowest chart price and not below zero, each line is named, a shop link opens a new tab, and a product name on `/products/` opens the card in the same tab.
