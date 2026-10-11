# Favorites lowest today Implementation Plan

## Overview

The signed-in home page becomes four tables: every tracked product, that user's favourites, products whose price today equals their lowest stored price, and each product's lowest shop price for today or yesterday. A line above the tables shows when a price-recording command last finished.

## Current State Analysis

- `/` is `accounts.views.home`, login-required and `never_cache`. It lists every `Product` by `name.casefold()`, then pk, and each name links to the product card. It shows no price (`accounts/views.py`, `accounts/templates/accounts/home.html`).
- There is no favourites model. `accounts` has no models. Any signed-in user sees the same product list. Staff also see Add a tracked product and Tracked products.
- A shop's price on a date is the latest `PriceObservation` for that shop page and date, or nothing. Ordering is newest `recorded_at`, then highest id (`prices/recording.py`). An unchanged amount does not create a new row. Yesterday is never returned as today.
- `card_figures` already computes today's minimum, marks every tied shop, and takes `lowest_recorded` as the minimum daily price across every stored date, including dates outside the 30-day chart (`prices/card.py`). The start page needs that price rule without the chart series.
- The card renders `19.99 PLN`, the exact text `No price`, and a shop link with `target="_blank"` and `rel="noopener noreferrer"` (`prices/templates/prices/product_card.html`).
- `TIME_ZONE` is `Europe/Warsaw`. Recording commands call `timezone.localdate()` and share `ShopRecordCommand.handle` (`prices/management/recording_command.py`). That includes `record_prices` and the four per-shop commands. Nothing stores when a command finished.
- Home tests currently require that a stored price does not appear on `/` (`accounts/tests/test_home.py`).

## Desired End State

A signed-in user opens `/` and sees this desktop layout:

| All products | Favourites |
| Historical lowest today | Lowest price today |

Above those tables, one line reads `Last price update: 12.10.2026 08:00 - Warsaw time` after a recording command has finished, or `Last price update: none - Warsaw time` before any finish. Username, staff links, the Home control, and sign-out stay.

All products and Favourites show the product name and an amount with no shop name. The name opens the product card in this tab. The amount is `19.99 PLN` when today has a price, `10.00 PLN yesterday` when only yesterday has one, and `No price` when neither day has one.

Historical lowest today lists a product only when today's cheapest price equals the lowest daily price stored for that product on any date. The row names every shop tied for that price, in shop-page id order, joined by ` and `. Each shop name opens that shop's stored product URL in a new tab. Soap at `8.00 PLN` at Gemini, when `8.00` is the lowest price stored for soap, appears as `8.00 PLN at Gemini`. Shampoo at `19.99 PLN` today, with `15.00 PLN` stored last month, does not appear in this table.

Lowest price today lists every tracked product. Rossmann and DOZ both at `19.99 PLN` today, with Gemini at `24.00 PLN`, show `19.99 PLN at Rossmann and DOZ`, and both shop names are links. A product with only yesterday's `10.00 PLN` at Rossmann shows `10.00 PLN at Rossmann yesterday`. A product whose latest price is older than yesterday shows `No price`, and that older amount is not shown. The product name on these rows still opens the card in this tab.

Favourites lists the signed-in user's own products, with the same name and amount as All products. It starts empty. On the product card, `Add to favourites` and `Remove from favourites` change that user's list. Another account does not see those rows. A table with no rows keeps its caption and one empty row.

Rows in every table stay in casefolded name order, then pk.

### Key Discoveries:

- The daily price is already `price_on_date`: latest amount that date, or nothing (`prices/recording.py`).
- `lowest_recorded` ignores a superseded same-day row and includes dates outside the 30-day window (`prices/card.py`). The historical table uses that same minimum.
- Home is the post-login page and already sorts names in Python so SQLite and Postgres agree (`accounts/views.py`).
- Shop links on the card already open a new tab (`prices/templates/prices/product_card.html`).
- `recorded_at` does not move when the recording command sees the same amount (`prices/recording.py`). The update line needs its own finish time.

## What We're NOT Doing

- Preloading tracked products as favourites. Every account starts with an empty Favourites table.
- Adding or removing a favourite anywhere except the product card.
- A shop name on All products or Favourites.
- A single winning shop when two shops share the lowest price.
- A per-shop historical low. DOZ at its own lowest price stays off Historical lowest today when the product's lowest stored price is lower.
- Using the 30-day chart window as the historical comparison.
- Showing a price older than yesterday on All products, Favourites, or Lowest price today, or labeling that older price as yesterday.
- Using yesterday on Historical lowest today.
- A separate "worth buying now" badge. Membership in Historical lowest today is that signal.
- Guest access, a description, availability, shipping added to the price, or a chart-horizon switch.
- A date on every row, or a heading that prints today's calendar date apart from the recording-finish line.
- Changing the card's shop list, `Cheapest` marker, lowest-recorded line, or chart.
- Deriving the update line from `PriceObservation.recorded_at`.
- An admin screen for the new tables.

## Implementation Approach

Add a pure summary of one date's list price for many products, and a recording-finish clock, before changing `/`. Then render the four tables from that summary, with Favourites always empty. Then add a per-user favourite row and a card control that fills Favourites.

The summary takes an injected `today` date, as `card_figures` does. The view passes `timezone.localdate()`. Daily amounts match `price_on_date`. Shop names on a tie follow `shop_pages` pk order, the same order as the card. Product rows keep `_home_product_key`.

New functions and model attributes carry parameter and return annotations. Views return `HttpResponse`. No `Any`.

Pages stay server-rendered documents. The 2×2 layout does not add a frontend package. A recording command that finishes stamps the clock inside the existing `ShopRecordCommand.handle`, so `record_prices` and each per-shop command share one path.

## Critical Implementation Details

### Timing & lifecycle

An unchanged price does not create a new `PriceObservation`, so the newest `recorded_at` can be older than the last recording run. Write the finish time only after `record_shop_pages` returns. A raise before that return leaves the previous finish time in place. The home line reads that finish time and does not read observations.

## Phase 1: Recording clock and price summary

### Overview

Store the finish time of a recording command, and compute each product's today-or-yesterday amount, tied shops, and historical-low flag. No home template in this phase.

### Changes Required:

#### 1. Recording finish time

**File**: `prices/models.py`

**Intent**: Keep a finish time that still moves when a command runs and every amount is unchanged.

**Contract**: New model `PriceRecordingRun` with `finished_at: DateTimeField`. The field is set by the caller, not `auto_now`. No backfill from observations.

#### 2. Clock helpers

**File**: `prices/recording_clock.py`

**Intent**: Give the command one write and the page one read.

**Contract**: `mark_recording_finished(finished_at: datetime) -> None` inserts one `PriceRecordingRun`. `latest_recording_finished_at() -> datetime | None` returns the row with the greatest `finished_at`, then the greatest pk, or `None` when the table is empty. `datetime` values are timezone-aware.

#### 3. Stamp the shared command

**File**: `prices/management/recording_command.py`

**Intent**: Every recording command, including a single-shop command, is a run of the price-recording script.

**Contract**: After `collect.record_shop_pages` returns, `handle` calls `mark_recording_finished(timezone.now())`. It does not catch an exception from `record_shop_pages` in order to stamp a failed run. Per-page gaps that the collector already turns into a printed `gap` still count as a finished run.

#### 4. List prices

**File**: `prices/list_prices.py`

**Intent**: One read answers the four tables without building the 30-day chart.

**Contract**: `list_prices(products: list[Product], today: date) -> dict[int, ListPrice]`. Every input product pk is a key. `ListPrice` is a `TypedDict` with `amount: Decimal | None`, `day: Literal["today", "yesterday", "none"]`, `shops: list[ShopOffer]`, and `matches_lowest_stored: bool`. `ShopOffer` has `label: str` and `url: str`.

For each shop page, the price on a date is the latest observation that date, or absent. `today` is the injected date. Yesterday is `today - one day`.

- When any shop has a price on `today`, `day` is `today`, `amount` is the minimum of those prices, and `shops` is every shop page whose today price equals that minimum, in pk order.
- When no shop has a price on `today` and any shop has a price on yesterday, `day` is `yesterday`, `amount` is yesterday's minimum, and `shops` is every shop page tied for that yesterday minimum, in pk order.
- Otherwise `day` is `none`, `amount` is `None`, and `shops` is empty. A price on `today - 2 days` or older does not fill `amount`.

`matches_lowest_stored` is True only when `day` is `today` and `amount` equals the minimum daily price across every shop page and every stored date, including `today` and dates older than 30 days. A superseded same-day row is not a candidate. A product with no observations has `matches_lowest_stored` False.

The function does not write and does not fetch shop HTML. It may load observations for the given products in one query.

#### 5. Tests

**File**: `prices/tests/test_list_prices.py`

**Intent**: Lock the summary before HTML exists.

**Contract**: Django `TestCase`. Build products, shop pages, and observations directly. Pass an explicit `today`. Cover at least:

- Rossmann `19.99` and DOZ `24.00` on `today`: `day` is `today`, `amount` is `19.99`, and `shops` contains only Rossmann.
- Rossmann and DOZ both `19.99` on `today`, Gemini `24.00`: both Rossmann and DOZ are in `shops`, Gemini is not, and Rossmann precedes DOZ when the Rossmann page has the lower pk.
- No row on `today`, Rossmann `10.00` yesterday: `day` is `yesterday`, `amount` is `10.00`, and the shop is Rossmann.
- No row on `today` or yesterday, DOZ `8.00` on `today - 3 days`: `day` is `none`, `amount` is `None`, and `shops` is empty.
- Rossmann `15.00` last month and `19.99` on `today`: `matches_lowest_stored` is False.
- Gemini `8.00` on `today` and no lower daily price: `matches_lowest_stored` is True.
- The same page stores `5.00` and then a later `19.99` on one date, with no other prices: that date's price is `19.99`, and `5.00` is not the lowest stored price.
- A `10.00` daily price older than 30 days, with `19.99` on `today`, keeps `matches_lowest_stored` False.

**File**: `prices/tests/test_recording_clock.py`

**Intent**: Lock the finish time before the home page shows it.

**Contract**: `latest_recording_finished_at()` is `None` when no run is stored. Two calls to `mark_recording_finished` with aware datetimes return the later one. A completed `record_prices` or `record_rossmann_prices` run, using the existing fetch fake from `prices/tests/test_commands.py`, inserts one `PriceRecordingRun`.

### Success Criteria:

#### Automated Verification:

- List-price tests pass for today's minimum, a tie, yesterday when today is empty, a gap older than yesterday, the historical-low flag, a superseded same-day amount, and a low older than 30 days: `uv run python manage.py test prices.tests.test_list_prices`
- Recording-clock tests pass for no finished run, the later finish time, and a completed `record_prices` or per-shop command: `uv run python manage.py test prices.tests.test_recording_clock`
- The recording-run migration applies: `uv run python manage.py migrate`
- The project test suite passes: `uv run python manage.py test`

---

## Phase 2: Four-table start page

### Overview

Render the four tables on `/` from `list_prices` and the recording clock. Favourites is a caption and one empty row. The card does not gain a favourite control yet.

### Changes Required:

#### 1. Home context

**File**: `accounts/views.py`

**Intent**: Pass the four groups and the update line without changing who can open `/`.

**Contract**: `home` stays `@never_cache` and `@login_required` and still returns `HttpResponse`. It loads every `Product`, calls `list_prices` with `timezone.localdate()`, and sorts each populated group with the existing casefold-then-pk key.

- All products and Lowest price today contain every product.
- Historical lowest today contains a product only when `matches_lowest_stored` is True.
- Favourites is empty in this phase. Do not read a favourite model.

The update line is `Last price update: none - Warsaw time` when `latest_recording_finished_at()` is `None`. Otherwise format `timezone.localtime(finished_at)` as `dd.mm.yyyy hh:mm` and wrap it as `Last price update: 12.10.2026 08:00 - Warsaw time`. An aware `2026-10-12 06:00 UTC` finish is `12.10.2026 08:00` in Warsaw. Use the active timezone, not a fixed offset in the view.

#### 2. Home template

**File**: `accounts/templates/accounts/home.html`

**Intent**: Show the 2×2 tables, the update line, and the existing account chrome.

**Contract**: Keep the Home include, the username, the staff-only add and tracked-list links, and the sign-out form. The update line sits above the tables.

The tables are in this order, each with a `<caption>` of exactly `All products`, `Favourites`, `Historical lowest today`, or `Lowest price today`. Visually they form two rows: All products beside Favourites, then Historical lowest today beside Lowest price today.

Each product row's name is a same-tab link to `prices:product_card`. On All products and Favourites the price text is:

- `today`: `19.99 PLN`
- `yesterday`: `10.00 PLN yesterday`
- `none`: `No price`

Those two tables do not show a shop label.

On Historical lowest today and Lowest price today the price text is:

- `today`: `19.99 PLN at Rossmann and DOZ`
- `yesterday`: `10.00 PLN at Rossmann yesterday` (Lowest price today only; the historical table has no yesterday rows)
- `none`: `No price`

Shop labels in that phrase are links to the stored shop URL with `target="_blank"` and `rel="noopener noreferrer"`. Labels are joined by ` and ` in the `shops` order. One shop is `19.99 PLN at Rossmann`, with no ` and `. Two decimals, matching the card's `.2f` format. The amount text is not itself a link.

A table with no products contains its caption and one row with a single empty cell, and no product link.

Replace `test_stored_price_does_not_appear_on_home`. A stored price for today is now visible on `/`.

#### 3. Home tests

**File**: `accounts/tests/test_home.py`

**Intent**: Lock the phrases, the table membership, and the update line.

**Contract**: Build rows relative to `timezone.localdate()`. Slice each table from its caption so a shop name in Lowest price today is not mistaken for a shop name in All products. Cover at least:

- `apple` still renders before `Zebra`, and each name links to its card.
- Rossmann `19.99` today: All products contains `19.99 PLN` and does not contain `Rossmann` in that table. Lowest price today contains `19.99 PLN at Rossmann`, and the Rossmann link has `target="_blank"` and `rel="noopener noreferrer"`.
- Rossmann and DOZ `19.99` today, Gemini `24.00`, with Rossmann's page created first: Lowest price today contains `19.99 PLN at Rossmann and DOZ` and does not present Gemini as one of those tied shops. All products contains `19.99 PLN` without those shop labels in that table.
- No price today, Rossmann `10.00` yesterday: All products contains `10.00 PLN yesterday`. Lowest price today contains `10.00 PLN at Rossmann yesterday`. The historical table does not contain that product.
- No price today or yesterday, and `8.00` three days ago: All products and Lowest price today contain `No price` for that product and do not contain `8.00`. The historical table does not contain that product.
- `15.00` more than 30 days ago and `19.99` today: the product is in All products and Lowest price today, and not in Historical lowest today.
- `8.00` today as the lowest stored daily price: Historical lowest today contains `8.00 PLN at Gemini`.
- With products present, Favourites has its caption, one empty row, and no product link.
- With no products, all four captions are present, none of the four tables has a product link, and the username and sign-out form remain. Staff still see Add a tracked product and Tracked products.
- No `PriceRecordingRun`: the page contains `Last price update: none - Warsaw time`.
- A run finished at `2026-10-12 06:00 UTC`: the page contains `Last price update: 12.10.2026 08:00 - Warsaw time`.

### Success Criteria:

#### Automated Verification:

- Home tests pass for name order, today's amount without a shop on All products, tied shop links on Lowest price today, yesterday labeled yesterday, No price for an older gap, historical membership, an empty Favourites table, the empty catalog, staff links, and the last-update line: `uv run python manage.py test accounts.tests.test_home`
- The project test suite passes: `uv run python manage.py test`

#### Manual Verification:

- Sign in and confirm the four tables sit in two rows of two, All products shows a name and an amount, and the name opens the card in this tab
- On a product whose lowest price today is shared by two shops, confirm both shop names appear and each opens that shop page in a new tab
- Confirm the line above the tables reads `Last price update: none - Warsaw time` before any recording command, and shows a Warsaw finish time after one completes

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Per-user favourites

### Overview

Let each signed-in user add or remove a product from the card, and list that user's products in Favourites with the same name and amount as All products.

### Changes Required:

#### 1. Favourite rows

**File**: `prices/models.py`

**Intent**: Store which signed-in user has marked which product, without copying the tracked list.

**Contract**: New model `Favourite` with a foreign key to `settings.AUTH_USER_MODEL` and a foreign key to `Product`, both `on_delete=CASCADE`, and a `UniqueConstraint` on `(user, product)`. No data migration. Existing products are not inserted.

#### 2. Card control

**File**: `prices/urls.py`
**File**: `prices/views.py`
**File**: `prices/templates/prices/product_card.html`

**Intent**: The product card is the only place that changes favourites.

**Contract**: POST `prices:toggle_favourite` at `products/<pk>/favourite/`, login-required, returns a redirect to that product's card. The view uses `request.user` only. A missing product is 404. When no `Favourite` exists for that user and product, the POST creates one. When one exists, the POST deletes it.

The card shows a CSRF form under the product name. The button reads `Add to favourites` when the row is absent and `Remove from favourites` when it is present. The shop list, chart, and price lines stay as they are.

#### 3. Favourites table

**File**: `accounts/views.py`
**File**: `accounts/templates/accounts/home.html`

**Intent**: Fill the table that phase 2 left empty.

**Contract**: Favourites lists `Favourite` rows for `request.user` only, using the same sort and the same amount phrase as All products, including `10.00 PLN yesterday` and `No price`. A favourite remains on All products. Another user's favourites do not appear. Zero favourites still renders the caption and one empty row.

#### 4. Tests

**File**: `prices/tests/test_favourite.py`
**File**: `accounts/tests/test_home.py`

**Intent**: Lock the toggle, the per-user table, and deletion.

**Contract**: Cover at least:

- A signed-in non-staff user POSTs once and then sees `Remove from favourites` on the card. A second POST shows `Add to favourites`.
- That product appears in the Favourites caption's table and still appears under All products, with the same amount phrase and a same-tab name link.
- A second signed-in user does not see the first user's product under Favourites, and still sees it under All products.
- Deleting the product removes the `Favourite` row.
- Staff and non-staff can both toggle. Anonymous POST redirects to sign-in.
- With products and no favourites, Favourites remains a caption and one empty row.

### Success Criteria:

#### Automated Verification:

- The favourite migration applies: `uv run python manage.py migrate`
- Favourite and home tests pass for add, remove, a second user, product deletion, and the Favourites table showing only that user's products with the same amount as All products: `uv run python manage.py test prices.tests.test_favourite accounts.tests.test_home`
- The project test suite passes: `uv run python manage.py test`

#### Manual Verification:

- On a product card, Add to favourites puts that product in Favourites and leaves it on All products; Remove from favourites clears it from Favourites
- Sign in as a second user and confirm the first user's favourites are absent
- With tracked products and no favourites, Favourites shows its title and one empty row

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- `prices/tests/test_list_prices.py` owns today's minimum, ties, yesterday, the older gap, the historical-low flag, a superseded same-day amount, and a low outside 30 days. It passes `today` in.
- `prices/tests/test_recording_clock.py` owns an empty clock, the later finish time, and a stamp from a completed recording command.

### Integration Tests:

- `accounts/tests/test_home.py` owns the four captions, phrases, links, empty rows, staff links, and the update line. Page tests build observations relative to `timezone.localdate()`.
- `prices/tests/test_favourite.py` owns the card POST, the button label, anonymous redirect, and cascade on product delete.

### Manual Testing Steps:

1. Sign in and confirm the 2×2 captions, a name that opens the card in this tab, and an amount with no shop name on All products.
2. Use a product with two shops at the same lowest price today. Confirm both names, the new tabs, and that Historical lowest today includes it only when that price equals the lowest stored daily price.
3. Use a product with no price today and a price yesterday. Confirm the yesterday label, and that a price from three days ago alone shows `No price`.
4. Run a recording command and confirm the line shows its Warsaw finish time to the minute. Before any run, confirm the none line.
5. Add and remove a favourite from the card with two different users.

## Performance Considerations

The tracked list is small: one person, a handful of products, at most three shop pages each. `list_prices` loads those products' observations once. No cache and no pagination.

## Migration Notes

Phase 1 adds `PriceRecordingRun`. Phase 3 adds `Favourite`. Neither backfills. Existing observations do not count as a recording run, so `/` shows `Last price update: none - Warsaw time` until a recording command finishes after this change. Existing products are not inserted as favourites.

## References

- Product rules: `context/foundation/prd.md` (US-01, FR-002, FR-009 as the card control, and the business-logic paragraph on the lowest stored price)
- Slice: `context/foundation/roadmap.md` (S-04)
- Daily price rule: `prices/recording.py` `price_on_date`, and `prices/card.py` `lowest_recorded`
- Recording commands: `prices/management/recording_command.py`
- Home and card patterns: `accounts/views.py`, `accounts/templates/accounts/home.html`, `prices/templates/prices/product_card.html`
- This change has no `frame.md` and no `research.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Recording clock and price summary

#### Automated

- [ ] 1.1 List-price tests pass for today's minimum, a tie, yesterday when today is empty, a gap older than yesterday, the historical-low flag, a superseded same-day amount, and a low older than 30 days: `uv run python manage.py test prices.tests.test_list_prices`
- [ ] 1.2 Recording-clock tests pass for no finished run, the later finish time, and a completed `record_prices` or per-shop command: `uv run python manage.py test prices.tests.test_recording_clock`
- [ ] 1.3 The recording-run migration applies: `uv run python manage.py migrate`
- [ ] 1.4 The project test suite passes: `uv run python manage.py test`

### Phase 2: Four-table start page

#### Automated

- [ ] 2.1 Home tests pass for name order, today's amount without a shop on All products, tied shop links on Lowest price today, yesterday labeled yesterday, No price for an older gap, historical membership, an empty Favourites table, the empty catalog, staff links, and the last-update line: `uv run python manage.py test accounts.tests.test_home`
- [ ] 2.2 The project test suite passes: `uv run python manage.py test`

#### Manual

- [ ] 2.3 Sign in and confirm the four tables sit in two rows of two, All products shows a name and an amount, and the name opens the card in this tab
- [ ] 2.4 On a product whose lowest price today is shared by two shops, confirm both shop names appear and each opens that shop page in a new tab
- [ ] 2.5 Confirm the line above the tables reads `Last price update: none - Warsaw time` before any recording command, and shows a Warsaw finish time after one completes

### Phase 3: Per-user favourites

#### Automated

- [ ] 3.1 The favourite migration applies: `uv run python manage.py migrate`
- [ ] 3.2 Favourite and home tests pass for add, remove, a second user, product deletion, and the Favourites table showing only that user's products with the same amount as All products: `uv run python manage.py test prices.tests.test_favourite accounts.tests.test_home`
- [ ] 3.3 The project test suite passes: `uv run python manage.py test`

#### Manual

- [ ] 3.4 On a product card, Add to favourites puts that product in Favourites and leaves it on All products; Remove from favourites clears it from Favourites
- [ ] 3.5 Sign in as a second user and confirm the first user's favourites are absent
- [ ] 3.6 With tracked products and no favourites, Favourites shows its title and one empty row
