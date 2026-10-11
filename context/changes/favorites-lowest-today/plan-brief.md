# Favorites lowest today — Plan Brief

> Full plan: `context/changes/favorites-lowest-today/plan.md`

## What & Why

After sign-in, the start page is where a restock decision starts. It should show every tracked product, the signed-in user's own favourites, which products are at their lowest stored price today, and which shop has the lowest price today or yesterday.

The home page already lists every product by name and links each name to its card. It does not show a price, and nothing records when the price-recording command last ran.

## Starting Point

`/` lists every tracked product in casefolded name order and shows no prices. The product card already shows today's shop prices, marks every tied cheapest shop, and opens a shop link in a new tab. There is no favourites model and no stored recording-finish time. A price for a shop on a date is the latest amount stored that Warsaw day.

## Desired End State

The signed-in home page shows four tables in two rows: All products, Favourites, Historical lowest today, and Lowest price today. A line above them reads `Last price update: 12.10.2026 08:00 - Warsaw time`, or `Last price update: none - Warsaw time` before any recording command has finished.

All products and Favourites show a name and an amount such as `19.99 PLN`, `10.00 PLN yesterday`, or `No price`. The name opens the card in this tab. The other two tables add the tied shop names, and each shop name opens that offer in a new tab. Favourites starts empty. The card's Add to favourites and Remove from favourites fill it for that account only.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Page layout | Four tables, two rows of two | The start page separates the full list, favourites, the historical-low set, and today's lowest shop price. |
| Favourites | Per signed-in user, toggled on the product card, starting empty | The favourites table can be empty while products exist, and each account keeps its own list. |
| All products and Favourites | Name plus the day's amount, no shop name; the name opens the card | Shop names and offer links belong on the two price tables. |
| Historical lowest today | Only when today's cheapest price equals the lowest stored daily price | The printed price is on offer today, so the shop link opens a page at that price. |
| Lowest price today | Amount plus every tied shop, each a new-tab link | Rossmann and DOZ both at 19.99 PLN are both named, and one link cannot open two offers. |
| Missing today | Yesterday's lowest, labeled yesterday; older than yesterday is `No price` | A previous calendar day is not shown as today, and a three-day-old 8.00 PLN stays off the today tables. |
| Sort | Casefolded name, then id | The restock case is a named product, and the home page already uses this order. |
| Empty table | Caption and one empty row | All four tables stay visible when they have nothing to list. |
| Last update | Finish time of the latest recording command, `dd.mm.yyyy hh:mm` Warsaw | An unchanged price does not write a new observation, so the observation time is not the run time. |

## Scope

**In scope:**

- The 2×2 home page, its phrases, shop links, and empty rows
- A finish time written when `record_prices` or a per-shop recording command completes
- A per-user favourite row and the card toggle

**Out of scope:**

- Preloading the tracked list into favourites
- A favourite control anywhere except the card
- Prices older than yesterday on the today tables
- A separate worth-buying badge, guest access, or changes to the card chart

## Architecture / Approach

`list_prices` returns, for each product and an injected Warsaw date, today's minimum or yesterday's minimum, the tied shops in page-id order, and whether today equals the lowest stored daily price. The home page groups that summary into four tables. `ShopRecordCommand.handle` writes a `PriceRecordingRun` after a run finishes, and the line shows the latest finish time. Phase 3 adds `Favourite` and fills the table phase 2 left empty.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Recording clock and price summary | Finish time and the list-price rules, tested without HTML | A superseded same-day row or a price outside 30 days is counted wrong |
| 2. Four-table start page | The 2×2 page, phrases, links, and update line; Favourites stays empty | The existing home test expects no prices on `/` |
| 3. Per-user favourites | Card toggle and a Favourites table for the signed-in user only | One account's rows leak to another account |

**Prerequisites:** Sign-in, tracked products with shop pages, and calendar-day prices are already in place. The product card exists so a name can open it.
**Estimated effort:** About 2–3 sessions across 3 phases.

## Open Risks & Assumptions

- A single-shop recording command moves the update line, because it shares `ShopRecordCommand.handle` with `record_prices`.
- Favourites stay empty until someone uses the card, including the list owner. Tracked products are not copied in.
- The historical comparison uses every stored daily price, including days older than the card's 30-day chart. The compared amount is the latest amount on each day, not a superseded row from earlier that day.
- "Today" remains the Warsaw calendar date already used by recording and the card.

## Success Criteria (Summary)

- A signed-in user sees the four tables, with `19.99 PLN` or `10.00 PLN yesterday` or `No price`, and shop names only on the historical and lowest-price tables.
- Historical lowest today includes a product only when today's cheapest price equals its lowest stored price, and each tied shop opens in a new tab.
- Each user adds and removes favourites from the card and sees only their own rows in Favourites.
