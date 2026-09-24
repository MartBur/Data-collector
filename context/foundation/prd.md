---
project: "Data Collector"
version: 6
status: draft
created: 2026-09-16
context_type: greenfield
product_type: web-app
target_scale:
  users: small
  qps: low
  data_volume: small
timeline_budget:
  mvp_weeks: 3
  hard_deadline: 2026-11-04
  after_hours_only: true
---

## Vision & Problem Statement

When a product suddenly runs out (e.g. shampoo), I have to buy now. I open several shop sites, spend time hunting where it is available and where it is cheapest right now, and I still overpay because I did not buy when it was cheaper.

The useful difference is not a one-shot "cheapest today" list. I need history on my own watched products, at the current selling price after promo, so I can tell whether to buy now and in which shop.

Pain categories (all apply): missing capability (no history / buy signal); prices trapped on shop pages; manual multi-tab search; decision paralysis under restock urgency.

At ~100× users the domain rule would stay the same (cheapest shop today at the price after promo vs recorded historical minimum); scale is not a reason to change the rule for this MVP.

## User & Persona

Primary: me. I reach for this when something I use has run out and I must restock the same day — I do not want to research several shops or guess whether today's price is good.

### Secondary persona

A broader audience later. Not the MVP primary.

## Success Criteria

### Primary
- After login, the start page shows my already-listed favorite products, each with the lowest price recorded for that day.
- Opening a product shows its name, shops with today's prices (no description, no availability), a history chart with one line per shop over a 30-day horizon, and a click through to that product in that shop.

### Secondary
- A separate "worth buying now" signal — raised when today's lowest price after promo is the lowest in that product's recorded history — beyond seeing the lowest price of the day and the history chart.

### Guardrails
- Yesterday's price must not be shown as today's price.

## User Stories

### US-01: Restock decision from favorites to shop

- **Given** I am logged in and already have favorite products with recorded prices
- **When** I open the start page, open a product, view shop prices and the history chart, then click a shop offer
- **Then** I see each favorite with the lowest price for that day; the card shows the name and today's shop prices; the chart shows one history line per shop over the last 30 days; I land on that product in that shop

#### Acceptance Criteria
- Start page does not require adding a product in this session (list is preloaded)
- Product card has no description and no availability field
- Chart shows a 30-day horizon; switching the horizon is not part of this flow
- Yesterday's price is not labeled as today's

## Functional Requirements

### Authentication
- FR-001: Logged-in user can sign in. Priority: must-have
  > Socrates: Counter-argument considered: for a single person, login only delays the urgent restock moment. Resolution: login stays — favorites are per account, and different users have different favorite items.

### Tracked list management
- FR-012: List owner can add a product to the tracked list together with the two or three shop pages that carry its price. Priority: must-have
  > Note: replaces the earlier plan to maintain listings outside the product. FR-002, FR-004 and FR-008 all read listings, so this is the must-have source of them.
- FR-013: List owner can change or remove a tracked product and its shop pages. Priority: must-have
  > Note: added with FR-012 — the list was described as a managed list, so changing and removing entries carry the same priority as adding them.

### Favorites and prices
- FR-002: Logged-in user can see their favorite products, each with the lowest price recorded for that day. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-003: Logged-in user can open a product card that shows the product name. Priority: must-have
  > Socrates: Counter-argument considered: the name is already on the list, so the card is an extra click. Resolution: kept; shop prices and the chart need a separate screen.
- FR-004: Logged-in user can see the shops for that product with each shop's price for today, at the current selling price after promo. Priority: must-have
  > Socrates: No counter-argument on the shop comparison; it stands as written. Updated 2026-09-23: shipping is not shown and is not added to the price.
- FR-009: Logged-in user can add a listed product to their favorites from that product's page. Priority: nice-to-have
  > Note: added after shaping. The must-have start page reads a preloaded list, so self-service favoriting was kept out of must-have scope.

### History and outbound
- FR-005: Logged-in user can see a price-history chart for the product with one line per shop over a 30-day horizon. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-010: Logged-in user can switch the price-history chart to a 7-day, 1-year, or all-recorded-data horizon. Priority: nice-to-have
  > Note: added after shaping. The 30-day horizon satisfies Success Criteria on its own; the selector was kept out of must-have scope to protect the three-week budget.
- FR-006: Logged-in user can follow a shop offer to that product in that shop. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-007: Logged-in user can see a separate "worth buying now" signal, raised when today's lowest price after promo for that product is the lowest in its recorded history. Priority: nice-to-have
  > Socrates: Counter-argument considered: without a rule, "worth buying" is an empty FR. Resolution: the rule is now defined (lowest in recorded history), but the signal stays nice-to-have — three weeks is tight, and the price comparison plus the chart already support the decision.

### Browsing all products
- FR-011: Guest or logged-in user can see all listed products and open any listed product's page. Priority: nice-to-have
  > Note: added after shaping. One shared view serves two purposes — it is the guest entry point, and it is how a logged-in user reaches a product that is not yet one of their favorites (so FR-009 depends on it).

### Price recording
- FR-008: System can record, once per calendar day and without user action, each listed product's price in each shop that applies to it, at the current selling price after promo. Priority: must-have
  > Note: added after shaping — the read-side requirements (FR-002, FR-004, FR-005) had no write-side source. The listings it reads come from FR-012. Updated 2026-09-23: the recorded amount is that selling price. Shipping is not added.

## Non-Functional Requirements

- A price labeled as "today" is the price for the current calendar day, not a previous day's price.
- The product remains usable on a desktop computer in a mainstream browser (latest two major versions).

## Business Logic

For a favorite product, the app points to the shop with the lowest price today, shows how today's prices compare across the other shops, and whether that lowest price is low against the product's history.

Inputs the user cares about: each shop's price for today at the current selling price after promo, plus the prices already recorded for that product (the historical minimum is the lowest of those recorded prices). Which shops apply is decided per product — two or three specific shop pages per item, chosen by me, from this fixed set: Rossmann (https://www.rossmann.pl/), DOZ (https://www.doz.pl/), Super-Pharm (https://www.superpharm.pl/), and Gemini (https://gemini.pl/).

Output: which shop is cheapest today at that price, today's prices after promo side by side, and the lowest recorded price shown next to today's so the user can judge. A product counts as worth buying now when today's lowest price after promo is the lowest in that product's recorded history — but the explicit signal for that is nice-to-have (FR-007), so the must-have MVP shows the two numbers next to each other and leaves the call to the user.

The user meets this on the start page (cheapest shop / lowest price after promo today), on the product card (comparison across shops), and on the chart (history as backdrop).

## Access Control

The must-have MVP is entered by signing in: the start page is a logged-in user's own favorites (FR-001, FR-002). Anonymous access is nice-to-have (FR-011).

Favorites are per account. The tracked-product list is the one I curate with the most-needed items — maintained inside the product, but only from my own privileged account — and a given user's favorites are a subset of it, so not every listed item is that user's favorite. Different users having different favorites is why login stays in the MVP.

- **List owner (me)** — everything a logged-in user can do, plus adding a tracked product with its two or three shop pages, and changing or removing any tracked entry. One privileged account.
- **Logged-in user** — start page opens on their own favorites with the day's lowest price; can open any listed product's page (name, today's shop prices after promo, 30-day history chart, outbound shop offer); can add a listed product to their favorites from its page; can switch the chart horizon. Cannot change the tracked list.
- **Guest (no full account)** — can see all listed products and open any listed product's page with the same content; cannot add favorites and cannot switch the chart horizon.

The all-products view is shared between the roles: it is the guest entry point, and it is also how a logged-in user reaches a product that is not yet one of their favorites.

## Non-Goals

- No USD exchange-rate or YouTube subscriber tracking — out of this version; the product is restock prices for watched goods.
- No arbitrary shop URLs per product — the pages I add for an item are two or three specific shop pages from Rossmann, DOZ, Super-Pharm, and Gemini, not any shop on the web.
- No shared curation — other logged-in users cannot add, change, or remove tracked products or their shop pages; the list stays mine (FR-012, FR-013).
- No product description and no availability field on the card — name, prices after promo, chart, and outbound link only.
- No shipping amount on the recorded or shown price — the price is the current selling price after promo.
- No self-service favoriting in the must-have flow — the start page reads a preloaded list; adding favorites from a product page (FR-009) is nice-to-have.
- No horizon switching in the must-have flow — the 30-day chart (FR-005) is enough for a restock decision; the selector (FR-010) is nice-to-have.
- No anonymous browsing in the must-have flow — the MVP primary is a logged-in me; guest access to the all-products view and product pages (FR-011) is nice-to-have.

## Open Questions

(none)
