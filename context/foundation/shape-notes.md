---
project: "Data Collector"
context_type: greenfield
created: 2026-09-14
updated: 2026-09-14
product_type: web-app
target_scale:
  users: small
timeline_budget:
  mvp_weeks: 3
  hard_deadline: 2026-11-04
  after_hours_only: true
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  gray_areas_resolved:
    - topic: pain category
      decision: "missing capability (no price history / buy signal) + data trapped on shop pages + workflow friction (manual multi-tab search) + decision paralysis (buy now or not)"
    - topic: insight
      decision: "history plus promo and shipping on MY products, not a one-shot cheapest-today comparison"
    - topic: primary persona scope
      decision: "MVP primary is myself; a broader audience is a later target, not the first persona"
    - topic: auth strategy
      decision: "login; guests without a full account also exist; guest-visible capabilities not specified"
    - topic: MVP first flow
      decision: "login → preloaded favorites with today's lowest price → product card (name, shops + today's prices, no description, no availability) → history chart (one line per shop, fixed horizon) → outbound shop link; no guests in this flow; no add-favorite in first flow; ~3 weeks not 2"
    - topic: domain rule details
      decision: "today's price includes promo and shipping; show recorded historical minimum next to today (user decides); start=cheapest shop, card=shop comparison, chart=history backdrop"
  frs_drafted: 7
  quality_check_status: accepted
---

## Seed idea

Narzędzie dla siebie: obserwowane produkty, historia (1 pomiar na sklep dziennie), wykres, kiedy i gdzie kupić, z promocją i wysyłką. Nowy projekt, Python. Na start kilka produktów i 2–3 konkretne strony; pełna lista sklepów jeszcze nieustalona. Czas: kilkanaście–20+ h/tydz. do końca października, potem jeszcze więcej. Poza MVP: kurs dolara, YT, dowolne sklepy per produkt.

## Forward: tech-stack

User volunteered: Python. Not a PRD decision — pick up after `/10x-prd`.

## Vision & Problem Statement

When a product suddenly runs out (e.g. shampoo), I have to buy now. I open several shop sites, spend time hunting where it is available and where it is cheapest right now, and I still overpay because I did not buy when it was cheaper.

The useful difference is not a one-shot “cheapest today” list. I need history on my own watched products, with promo and shipping included, so I can tell whether to buy now and in which shop.

Pain categories (all apply): missing capability (no history / buy signal); prices trapped on shop pages; manual multi-tab search; decision paralysis under restock urgency.

At ~100× users the domain rule would stay the same (cheapest landed shop today vs recorded historical minimum); scale is not a reason to change the rule for this MVP.

## User & Persona

Primary: me. I reach for this when something I use has run out and I must restock the same day — I do not want to research several shops or guess whether today’s price is good.

### Secondary persona

A broader audience later. Not the MVP primary.

## Access Control

Login required to enter. Besides logged-in accounts, guests can use the product without a full account.

What a guest can see or do is not specified yet.

## Open Questions

1. **What can a guest do without a full account?** — Owner: user. Block: no (MVP primary is a logged-in self; first flow has no guests).
2. **How are favorite products preloaded for the first session?** — Owner: user.
3. **Keep login in MVP despite solo-use friction, or drop it?** — Owner: user. Block: no (FR-001 still written as login).
4. **What rule makes a product “worth buying now”?** — Owner: user. Block: no (FR-007 is nice-to-have). MVP does not auto-declare “buy now”; it shows today’s landed lowest vs the lowest recorded price and the user decides.

## Success Criteria

### Primary
- After login, the start page shows my already-listed favorite products, each with the lowest price recorded for that day.
- Opening a product shows its name, shops with today's prices (no description, no availability), a history chart with one line per shop and a fixed time horizon, and a click through to that product in that shop.

### Secondary
- A separate “worth buying now” signal, beyond seeing the lowest price of the day and the history chart.

### Guardrails
- Yesterday’s price must not be shown as today’s price.

## Business Logic

For a favorite product, the app points to the shop with the lowest price today, shows how today’s prices compare across the other shops, and whether that lowest price is low against the product’s history.

Inputs the user cares about: each shop’s price for today after promo and shipping, plus the prices already recorded for that product (the historical minimum is the lowest of those recorded prices).

Output: which shop is cheapest today on that landed basis, today’s landed prices side by side, and the lowest recorded price shown next to today’s so the user can judge — the product does not declare “buy now” in MVP.

The user meets this on the start page (cheapest shop / lowest landed price today), on the product card (comparison across shops), and on the chart (history as backdrop).

## Non-Functional Requirements

- A price labeled as “today” is the price for the current calendar day, not a previous day’s price.
- The product remains usable on a desktop computer in a mainstream browser (latest two major versions).

## Non-Goals

- No USD exchange-rate or YouTube subscriber tracking — out of this version; the product is restock prices for watched goods.
- No arbitrary shop URLs per product — only a small set of specific sites (a couple to three), not “any store”.
- No product description and no availability field on the card — name, landed prices, chart, and outbound link only.

## Functional Requirements

### Authentication
- FR-001: Logged-in user can sign in. Priority: must-have
  > Socrates: Counter-argument considered: for a single person, login only delays the urgent restock moment. Resolution: not decided yet — keep login as written until the user picks keep-vs-drop.

### Favorites and prices
- FR-002: Logged-in user can see their favorite products, each with the lowest price recorded for that day. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-003: Logged-in user can open a product card that shows the product name. Priority: must-have
  > Socrates: Counter-argument considered: the name is already on the list, so the card is an extra click. Resolution: kept; shop prices and the chart need a separate screen.
- FR-004: Logged-in user can see the shops for that product with each shop’s price for today, including promo and shipping. Priority: must-have
  > Socrates: No counter-argument; it stands as written.

### History and outbound
- FR-005: Logged-in user can see a price-history chart for the product with one line per shop and a fixed time horizon. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-006: Logged-in user can follow a shop offer to that product in that shop. Priority: must-have
  > Socrates: No counter-argument; it stands as written.
- FR-007: Logged-in user can see a separate “worth buying now” signal. Priority: nice-to-have
  > Socrates: Counter-argument considered: without a rule, “worth buying” is an empty FR. Resolution: stays nice-to-have; the rule is an open question.

## User Stories

### US-01: Restock decision from favorites to shop

- **Given** I am logged in and already have favorite products with recorded prices
- **When** I open the start page, open a product, view shop prices and the history chart, then click a shop offer
- **Then** I see each favorite with the lowest price for that day; the card shows the name and today’s shop prices; the chart shows one history line per shop on a fixed horizon; I land on that product in that shop

#### Acceptance Criteria
- Start page does not require adding a product in this session (list is preloaded)
- Product card has no description and no availability field
- Chart time horizon is not user-adjustable
- Yesterday’s price is not labeled as today’s

## Quality cross-check

All greenfield gate elements present: Access Control, one-sentence Business Logic, shape-notes artifact, 3-week timeline (no extra acknowledgment required), Non-Goals. Preserved behavior n/a.

Open questions remain (guests, preloaded favorites, login vs solo friction, auto buy-now signal) but they are not missing sections. They belong in `/10x-prd` Open Questions.
