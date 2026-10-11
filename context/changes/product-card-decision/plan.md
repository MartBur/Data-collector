# Product card with today's prices, a 30-day chart, and a shop link — Implementation Plan

## Overview

A signed-in user can open a tracked product from a name-only list, compare each shop's price for today, read a 30-day history with one line per shop, see the lowest price ever recorded, and follow a link to that product in that shop. The chart has a Y axis and a legend, shop links open in a new tab, and each name on `/products/` opens that product's card in the same tab.

## Current State Analysis

Sign-in, tracked products, shop pages, and daily promo prices already exist. The card does not.

- `prices.price_on_date` returns the latest amount stored for one shop page on one date, or nothing when that date has no row (`prices/recording.py`). Ordering is newest `recorded_at`, then highest id. A later read the same day stores another row only when the amount changes. Yesterday is never returned as today.
- `TIME_ZONE` is `Europe/Warsaw` (`DataCollector/settings.py`). Recording stamps `timezone.localdate()`.
- Each product has at most one page per shop, from Rossmann, DOZ, Super-Pharm, and Gemini (`prices/models.py`). The page URL is the outbound link.
- The only product screen is staff-only `/products/add/`. Home shows the username, a staff add link, and sign-out (`accounts/templates/accounts/home.html`). A signed-in non-staff user cannot open a product.
- Templates are standalone HTML documents. There is no shared stylesheet, no script, and no chart library.

## Desired End State

On 10 October 2026 a signed-in user sees every tracked product by name on the home page, with no prices. Opening one shows its name and one row per shop page, in the order the pages were added.

Rossmann and DOZ at 19.99 PLN today are both marked Cheapest. Gemini at 24.00 PLN is not. A shop with no row for today shows No price and still links to its stored product URL. The chart's dates are 11 September through 10 October. A Rossmann price on 10 September is outside the chart. A missing 9 October between 18.00 on 8 October and 19.99 on 10 October stays on the axis with no point, and the line still joins those two days. The lowest recorded price shows 10.00 PLN when that amount is the lowest daily price ever stored, including 1 August.

Verify with the phase test commands and by opening the card in a browser.

### Key Discoveries:

- The price for a shop on a date is already defined: latest stored amount that date, or no price (`prices/recording.py`).
- The card can read `Product`, `ShopPage`, and `PriceObservation`. It does not need a new table.
- Home is the signed-in landing page and currently renders no products (`accounts/views.py`, `accounts/templates/accounts/home.html`).
- Add-product tests use Django `TestCase`, `force_login`, and `assertContains` (`prices/tests/test_add_product.py`). The card tests should follow that.

## What We're NOT Doing

- The favorites start page and each favorite's lowest price for today (later slice).
- Changing or removing a tracked product.
- A favorites model, or treating the home list as a subset of tracked products.
- Description, availability, shipping added to the price, a horizon switch, a "worth buying now" badge, guest access, and adding a favorite from the card.
- A chart library, a new JavaScript dependency, or a shared design system.
- A new model, migration, or change to how prices are recorded.
- Hiding a shop that has no price today, labeling an older price as today, dropping empty days from the axis, or breaking the line at a gap.
- Choosing a single winner when two shops share today's lowest price.
- Naming which shop set the lowest recorded price.

## Implementation Approach

Add a pure read of one product's card figures, then a login-required page that renders those figures, then name links on the existing home page. The figures function is the place the six display rules are tested. The page and the home list only present them.

The chart is an inline SVG in the card template. Pages are already server-rendered documents with no static script, and one chart does not justify a frontend package. X positions are the 30 calendar slots, so a missing day still occupies its place while the line joins the priced days on either side.

Shop rows follow shop-page id order, the same order as the add confirmation. Home names are sorted by `name.casefold()`, then id, in Python, so SQLite and Postgres agree. New functions carry parameter and return annotations. The card view returns `HttpResponse`. No `Any`.

## Phase 1: Card figures

### Overview

Define the card's numbers for a product and a Warsaw date, with tests for the window, gaps, ties, a missing today, and the all-time low. No template in this phase.

### Changes Required:

#### 1. Card figures

**File**: `prices/card.py`

**Intent**: One function turns a product and a date into the shop rows, the 30-day series, and the lowest recorded price, so the page does not invent those rules.

**Contract**: `card_figures(product: Product, today: date) -> CardFigures`. `CardFigures` is a `TypedDict` with `dates: list[date]`, `shops: list[ShopRow]`, `series: list[ShopSeries]`, and `lowest_recorded: Decimal | None`. `ShopRow` has `label: str`, `url: str`, `today_amount: Decimal | None`, and `cheapest: bool`. `ShopSeries` has `label: str` and `amounts: list[Decimal | None]`.

`dates` is the 30 calendar dates from `today - 29 days` through `today`, ascending. For 10 October 2026 that is 11 September through 10 October. 10 September is absent.

`shops` and `series` follow `product.shop_pages.order_by("pk")`. `label` is the shop choice label. `url` is the stored page URL. `amounts` has one entry per `dates` entry. `today_amount` and each series entry use the same daily price as `price_on_date`: the latest row for that page and date, or `None` when that date has no row. A shop with `today_amount is None` has `cheapest` False. Among rows with an amount, `cheapest` is True for every row equal to the minimum. When no shop has a price today, every `cheapest` is False.

`lowest_recorded` is the minimum of those daily prices across every shop page and every stored date, including dates outside `dates` and including `today`. An earlier row superseded the same day is not a candidate. When the product has no observations, `lowest_recorded` is `None`. Zero shop pages yields empty `shops` and `series`, a 30-date `dates` list, and `lowest_recorded` None.

The function does not write and does not fetch shop pages. It may load the product's observations once, as long as the daily price matches `price_on_date`.

#### 2. Figure tests

**File**: `prices/tests/test_card.py`

**Intent**: Lock the display rules against the figures function before any HTML exists.

**Contract**: Django `TestCase`. Build products, shop pages, and observations directly. Cover at least:

- A price on `today - 30 days` is outside `dates`, and a price on `today - 29 days` is the first entry. `today` is the last.
- A page with amounts on day A and day C and no row on day B has `None` at B and the two amounts at A and C.
- Two shops at 19.99 today and a third at 24.00: both 19.99 rows are `cheapest`, the 24.00 row is not.
- A shop with no row for `today` has `today_amount` None and `cheapest` False while another shop with a price is cheapest.
- An amount of 10.00 on a date before the window, with higher prices inside the window, makes `lowest_recorded` 10.00.
- The same page on one date stores 5.00 and then a later 19.99. That day's price is 19.99, and 5.00 is not `lowest_recorded` when every other daily price is higher.
- A product with no observations has `lowest_recorded` None, no cheapest row, and thirty empty amounts per shop.

### Success Criteria:

#### Automated Verification:

- Card figure tests pass for the 30-date window, an empty gap day, tied cheapest shops, a shop with no price today, the all-time low outside the window, and a same-day amount change: `uv run python manage.py test prices.tests.test_card`

---

## Phase 2: Card page

### Overview

Serve the figures on a login-required product page: shop rows, cheapest marks, empty today, the all-time low, an SVG chart that connects across gaps, and a link to each shop.

### Changes Required:

#### 1. Card route

**File**: `prices/urls.py`, `prices/views.py`

**Intent**: Any signed-in user can open any tracked product. Anonymous visitors go to sign-in. An unknown id is a 404.

**Contract**: `path("<int:pk>/", product_card, name="product_card")` on the existing `prices` include, so the path is `/products/<pk>/`. `product_card(request: HttpRequest, pk: int) -> HttpResponse` is `@login_required` and does not check `is_staff`. It loads the product with `get_object_or_404` and calls `card_figures(product, timezone.localdate())`. The template receives the product and those figures.

#### 2. Card template

**File**: `prices/templates/prices/product_card.html`

**Intent**: Show the decision screen in the same standalone HTML style as the add page, with the chart drawn in the page.

**Contract**: A full HTML document. The visible text includes the product name and, for each shop row in figure order, the shop label, the amount as two decimals plus `PLN` (19.99 PLN), or the exact text `No price` when `today_amount` is None. Each row whose `cheapest` is True includes the exact text `Cheapest`. Each row has an anchor whose `href` is that row's stored URL.

When `lowest_recorded` is not None, the page includes the exact text `Lowest recorded price` and that amount in the same `PLN` form. When it is None, that label is absent. The label is not "today".

The chart is one inline SVG and does not use an external script or stylesheet. The x axis is the 30 `dates` slots, evenly spaced, including dates with no price. Label the first date and `today`; other dates need not be labeled. Each shop with two or more priced days has one line through only those days, in date order, at their slot positions, so the segment crosses a slot that has no point. A shop with one priced day has a point and no line. A shop with none has neither. Y uses the minimum and maximum priced amount in the window; equal amounts draw a horizontal line. Each priced point's markup includes that date as `YYYY-MM-DD` and the two-decimal amount. A date with no price for that shop does not appear as a point. Shops are distinguishable by stroke or marker, using inline attributes.

The page does not show a description, availability, shipping, a horizon control, or a buy-now badge.

#### 3. Card page tests

**File**: `prices/tests/test_product_card.py`

**Intent**: Prove the route's access rules and that the HTML states the same decisions as the figures.

**Contract**: Django `TestCase` and `force_login`, following `prices/tests/test_add_product.py`. Compute `today` once with `timezone.localdate()` and build observation dates from it. Cover anonymous `GET` redirecting to `/accounts/login/?next=/products/<pk>/`, a non-staff user receiving 200, an unknown id receiving 404, today's amount present, an older amount not labeled as today, the text `No price`, `Cheapest` on every tied shop and not on a higher price, `Lowest recorded price` with the older low, the stored shop URL as an href, and one shop line whose markup includes both dates around a gap and omits the gap date as a point.

### Success Criteria:

#### Automated Verification:

- Product card tests pass for the sign-in redirect, a non-staff user, an unknown product, today's price, a shop with no price, every tied cheapest shop, the lowest recorded price, the shop link, and a line across a gap: `uv run python manage.py test prices.tests.test_product_card`
- Prices tests still pass: `uv run python manage.py test prices`

#### Manual Verification:

- On a product with a missing day between two prices, the line crosses that day, the day stays on the axis, a shop with no price today shows no amount and still links to its page, and the lowest recorded price can be older than the chart
- The card shows the product name, shop prices, the chart, and shop links, and it shows no description and no availability

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 3: Home links

### Overview

The signed-in home page lists every tracked product by name and links each name to its card, with no prices. Every page has a Home link back to that main page.

### Changes Required:

#### 1. Home list

**File**: `accounts/views.py`, `accounts/templates/accounts/home.html`

**Intent**: Give every signed-in user an in-app way to open a card before the favorites start page exists, without showing today's lowest price.

**Contract**: `home` stays `@login_required` and `@never_cache`. It passes every `Product` sorted by `name.casefold()`, then `pk`. The template renders each name as a link to `prices:product_card` for that id. The list shows names only: no amounts, no `PLN`, no `Cheapest`, and no `No price`. An empty catalog renders the username and sign-out and no product links. The staff-only add link stays as it is.

#### 2. Home tests

**File**: `accounts/tests/test_home.py`

**Intent**: Prove the list is names in order, is usable by a non-staff user, and does not leak prices.

**Contract**: Django `TestCase`. With two products whose case-insensitive names sort opposite to their ids, the earlier name's link appears first and both hrefs point at `/products/<pk>/`. A non-staff user can open one of those links and see the product name. A product that has a stored price still does not put that amount, `PLN`, `Cheapest`, or `No price` on the home page. Zero products leaves the username and sign-out, and no `/products/<pk>/` link. A staff user still sees the add-product link.

#### 3. Home button

**File**: `accounts/templates/accounts/home_button.html`, and every app page template

**Intent**: From any screen, the user can return to the main page in the same tab.

**Contract**: One shared snippet renders `<a href="{% url 'home' %}">Home</a>`. It is included at the top of the sign-in page, the home page, the product card, `/products/`, and the add, change, and remove screens. The link has no `target` attribute. `accounts/tests/test_home.py` loads the sign-in page, home, `/products/`, add, a card, change, and the remove confirmation, and each response contains that Home link.

### Success Criteria:

#### Automated Verification:

- Home tests pass for name-only links in case-insensitive name order, a non-staff user opening a card from that list, and no prices on the home page: `uv run python manage.py test accounts.tests.test_home`
- The project test suite passes: `uv run python manage.py test`
- The Home link is present on the sign-in page, home, the product list, add, a card, change, and the remove confirmation: `uv run python manage.py test accounts.tests.test_home.HomeTests.test_home_button_is_on_every_page`

#### Manual Verification:

- Sign in as a non-staff user, open a product from the home list, and land on its card
- As a staff user, the add-product link is still on the home page
- From the sign-in page, a product card, and /products/, click Home and land on the main page

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 4: Chart axis, legend, and link targets

### Overview

Give the card chart a Y axis and a shop legend, open each shop page in a new tab, and make each product name on `/products/` open that product's card in the same tab.

### Changes Required:

#### 1. Y axis and legend

**File**: `prices/views.py`, `prices/templates/prices/product_card.html`

**Intent**: A reader can read the price scale and tell which line belongs to which shop.

**Contract**: The Y axis uses prices inside the 30-day window. Its first tick is that window's lowest price minus 50 PLN, and that tick is never below 0.00. Further ticks are every 10 PLN from that first tick up through a tick at or above the window's highest price. Prices of 80.00 and 90.00 start the axis at 30.00 and include 90.00. Prices of 18.00 and 19.99 start the axis at 0.00 and include 10.00 and 20.00. A chart with no prices has no Y ticks. Each shop that has at least one point in the window is named inside the chart, to the right of the plot, with a short sample of its line and its shop name. Shops with no point in the window stay out of the legend.

#### 2. Shop link and product-list name

**File**: `prices/templates/prices/product_card.html`, `prices/templates/prices/product_list.html`

**Intent**: Leaving for a shop does not replace the card, and a staff user can open a card from the tracked-product list.

**Contract**: Each shop anchor on the card keeps the stored page URL and opens it in a new tab (`target="_blank"` and `rel="noopener noreferrer"`). On `/products/`, the product name is a link to `prices:product_card` for that id and opens in the same tab. The change and remove controls stay as they are.

#### 3. Tests

**File**: `prices/tests/test_product_card.py`, `prices/tests/test_product_list.py`

**Intent**: Lock the axis floor, the legend, the new tab, and the same-tab name link.

**Contract**: The card tests assert `data-price="0.00"` when the window's lowest price is 18.00, and `data-price="30.00"` plus `data-price="90.00"` when the window's prices are 80.00 and 90.00. They assert `data-legend` for a drawn shop, and `target="_blank"` on a shop href. The product-list test asserts the name is an anchor to `/products/<pk>/` and that the list page has no `target="_blank"`.

### Success Criteria:

#### Automated Verification:

- Card and product-list tests pass for a Y axis that starts 50 below the lowest chart price and not below zero, a legend naming each drawn shop, a shop link that opens in a new tab, and a product name on /products/ that opens the card in the same tab: `uv run python manage.py test prices.tests.test_product_card prices.tests.test_product_list`

#### Manual Verification:

- On a product whose lowest chart price is above 50 PLN, the Y axis starts at that price minus 50, labels continue every 10 PLN, and each drawn line has its shop name and color under the chart
- On a product whose lowest chart price is below 50 PLN, the Y axis starts at 0.00
- A shop name on the card opens that shop page in a new tab, and a product name on /products/ opens the card in the same tab

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

### Implementation review amendment — adaptive Y-axis ticks

On 11 October 2026, implementation-review finding F1 replaced the fixed 10 PLN interval with an adaptive nice-number interval. The interval is at least 1 PLN, follows 1/2/5 times powers of ten, and permits at most 20 intervals. The axis-floor rule is unchanged.

---

## Testing Strategy

### Unit Tests:

- `prices/tests/test_card.py` owns the window, the empty day, the tie, the missing today, the all-time low, and the superseded same-day amount.
- Those tests call `card_figures` with an explicit date so they do not depend on the clock.

### Integration Tests:

- `prices/tests/test_product_card.py` owns auth, 404, the rendered phrases, SVG dates, the Y-axis floor, the shop legend, and the new-tab shop link.
- `prices/tests/test_product_list.py` owns the same-tab product-name link on `/products/`.
- `accounts/tests/test_home.py` owns the name list, its order, and the absence of prices.
- Page tests take `today` from `timezone.localdate()` once per test and build rows relative to that date.

### Manual Testing Steps:

1. Record or insert prices so one shop has a gap inside the last 30 Warsaw days, one shop has no row today, and the lowest daily price is older than the window.
2. Sign in as a non-staff user, open the product from home, and check the line, the empty day, No price, the shop link, and Lowest recorded price.
3. Sign in as staff and confirm the add-product link is still on home.
4. From the sign-in page, a product card, and `/products/`, click Home and confirm the main page opens in the same tab.
5. On a product whose prices in the chart are 80.00 and 90.00, confirm the Y axis starts at 30.00 and steps by 10.00, and that the legend names the shop.
6. On a product whose lowest chart price is below 50 PLN, confirm the Y axis starts at 0.00.
7. Click a shop name on the card and confirm the shop page opens in a new tab. On `/products/`, click a product name and confirm the card opens in the same tab.

## Performance Considerations

A card reads one product with at most three shop pages. History is one row per amount change per day. Loading that product's observations once is enough. No cache and no pagination.

## Migration Notes

No schema change and no backfill. The card reads products, shop pages, and observations that are already stored.

## References

- Product rules: `context/foundation/prd.md` (US-01, FR-003, FR-004, FR-005, FR-006, and the business-logic paragraph on the lowest recorded price)
- Slice: `context/foundation/roadmap.md` (S-03)
- Daily price rule: `prices/recording.py` `price_on_date`, and `context/archive/2026-09-23-calendar-day-landed-price/plan.md`
- Page pattern: `prices/views.py`, `prices/templates/prices/add_product.html`, `accounts/templates/accounts/home.html`
- This change has no `frame.md` and no `research.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Card figures

#### Automated

- [x] 1.1 Card figure tests pass for the 30-date window, an empty gap day, tied cheapest shops, a shop with no price today, the all-time low outside the window, and a same-day amount change: `uv run python manage.py test prices.tests.test_card` — f8fc8cf

### Phase 2: Card page

#### Automated

- [x] 2.1 Product card tests pass for the sign-in redirect, a non-staff user, an unknown product, today's price, a shop with no price, every tied cheapest shop, the lowest recorded price, the shop link, and a line across a gap: `uv run python manage.py test prices.tests.test_product_card` — 510c7bc
- [x] 2.2 Prices tests still pass: `uv run python manage.py test prices` — 510c7bc

#### Manual

- [x] 2.3 On a product with a missing day between two prices, the line crosses that day, the day stays on the axis, a shop with no price today shows no amount and still links to its page, and the lowest recorded price can be older than the chart — 510c7bc
- [x] 2.4 The card shows the product name, shop prices, the chart, and shop links, and it shows no description and no availability — 510c7bc

### Phase 3: Home links

#### Automated

- [x] 3.1 Home tests pass for name-only links in case-insensitive name order, a non-staff user opening a card from that list, and no prices on the home page: `uv run python manage.py test accounts.tests.test_home` — 9c95344
- [x] 3.2 The project test suite passes: `uv run python manage.py test` — 9c95344

#### Manual

- [x] 3.3 Sign in as a non-staff user, open a product from the home list, and land on its card — 9c95344
- [x] 3.4 As a staff user, the add-product link is still on the home page — 9c95344
- [x] 3.5 The Home link is present on the sign-in page, home, the product list, add, a card, change, and the remove confirmation: `uv run python manage.py test accounts.tests.test_home.HomeTests.test_home_button_is_on_every_page`
- [x] 3.6 From the sign-in page, a product card, and /products/, click Home and land on the main page

### Phase 4: Chart axis, legend, and link targets

#### Automated

- [x] 4.1 Card and product-list tests pass for a Y axis that starts 50 below the lowest chart price and not below zero, a legend naming each drawn shop, a shop link that opens in a new tab, and a product name on /products/ that opens the card in the same tab: `uv run python manage.py test prices.tests.test_product_card prices.tests.test_product_list`

#### Manual

- [x] 4.2 On a product whose lowest chart price is above 50 PLN, the Y axis starts at that price minus 50, labels continue every 10 PLN, and each drawn line has its shop name and color under the chart
- [x] 4.3 On a product whose lowest chart price is below 50 PLN, the Y axis starts at 0.00
- [x] 4.4 A shop name on the card opens that shop page in a new tab, and a product name on /products/ opens the card in the same tab
