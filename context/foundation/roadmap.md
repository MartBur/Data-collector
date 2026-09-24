---
project: Data Collector
version: 1
status: draft
created: 2026-09-22
updated: 2026-09-24
prd_version: 5
main_goal: speed
top_blocker: decisions
milestone_id: restock-from-history
milestone_seq: 1
milestone_status: open
---

# Roadmap: Data Collector

> Derived from context/foundation/prd.md (v5) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Milestone

**M-1: Restock from history** — Status: open

- **Intent:** A logged-in owner can open a watched product and tell whether to buy now and in which shop: today's landed prices, a 30-day history, and a link into that shop. The start page shows each favorite's lowest price for that day.
- **Source materials:** `context/foundation/prd.md` (v5)
- **Done when:** every F-NN and S-NN below is `done`.
- **Scope anchors:** US-01, FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, FR-012, FR-013

## Vision recap

When a product runs out, the user has to buy the same day, hunts across several shop sites, and still overpays because they did not buy when it was cheaper. The useful difference is history on their own watched products, with promo and shipping included, so they can tell whether to buy now and in which shop. At a much larger audience the same rule would stay; scale is not a reason to change it in this version.

## North star

**S-03: user can open a watched product, compare today's landed shop prices, read a 30-day history, and follow a link into the shop** — Placed as soon as sign-in, a tracked product, and a recorded price exist, because the speed goal still puts this proof ahead of list editing and ahead of the start page.

> North star here means the smallest end-to-end slice that proves the core product hypothesis — the belief that history plus promo and shipping, on products the user already watches, is enough to decide whether to buy now and in which shop. It is placed as early as its prerequisites allow, because the other slices only matter if this works.

## At a glance

| ID   | Change ID                   | Outcome (user can …)                                                                                          | Prerequisites    | PRD refs                                 | Status   |
| ---- | --------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------------------------------- | -------- |
| F-01 | calendar-day-landed-price   | (foundation) a tracked product can receive one landed shop price per calendar day, and "today" is only that day | —                | FR-008                                   | in-progress |
| S-01 | account-sign-in             | sign in                                                                                                       | —                | FR-001                                   | ready    |
| S-02 | add-tracked-product         | add a tracked product together with its two or three shop pages                                               | S-01             | FR-012                                   | proposed |
| S-03 | product-card-decision       | open a product, compare today's landed shop prices, read a 30-day chart, and open the shop                    | S-01, S-02, F-01 | US-01, FR-003, FR-004, FR-005, FR-006    | proposed |
| S-04 | favorites-lowest-today      | see favorite products, each with the lowest price recorded for that day                                      | S-01, S-02, F-01 | US-01, FR-002                            | proposed |
| S-05 | edit-tracked-product        | change or remove a tracked product and its shop pages                                                         | S-02             | FR-013                                   | proposed |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme            | Chain                          | Note                                                                                                      |
| ------ | ---------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------- |
| A      | Tracked list     | `S-01` → `S-02` → `S-05`       | Speed: the owner can curate the list without waiting on price capture.                                   |
| B      | Restock decision | `F-01` → `S-03` → `S-04`       | Joins stream A at `S-02`. The card is the north star, so it is read before the start page; the two can be planned in parallel. |

## Baseline

What's already in place in the codebase as of 2026-09-22 (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** partial — server-rendered templates and static files are configured; no app screens; routes are admin-only (`DataCollector/urls.py`)
- **Backend / API:** partial — web app scaffold only; installed apps are built-in; no app views (per tech-stack.md: Django)
- **Data:** partial — production Postgres driver and local SQLite are wired; no product models or app migrations (per tech-stack.md: PostgreSQL)
- **Auth:** partial — built-in accounts and sessions exist; the only login surface is admin (per tech-stack.md: framework auth)
- **Deploy / infra:** partial — `render.yaml` exists; no CI workflows (per tech-stack.md: Render + GitHub Actions)
- **Observability:** absent — no error tracking, metrics, or application logging

## Foundations

### F-01: Calendar-day landed price

- **Outcome:** (foundation) each tracked product can receive one landed shop price per calendar day without the user acting, and a price labeled today is only that calendar day's record.
- **Change ID:** calendar-day-landed-price
- **PRD refs:** FR-008
- **Unlocks:** S-03, S-04
- **Prerequisites:** —
- **Parallel with:** S-01, S-02, S-05
- **Blockers:** —
- **Unknowns:**
  - Which timezone bounds the calendar day for "today"? — Owner: user. Block: no.
- **Risk:** This is the only deep investment, because the card and the start page are false if yesterday is labeled today. Prices are read from Rossmann, DOZ, Super-Pharm, and Gemini. The screens that read the price still come later.
- **Status:** in-progress

## Slices

### S-01: Sign in

- **Outcome:** user can sign in
- **Change ID:** account-sign-in
- **PRD refs:** FR-001
- **Prerequisites:** —
- **Parallel with:** F-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Sign-in stays in this version so favorites are per account. It is first because every later slice assumes a logged-in owner, and it does not wait on the shop decision.
- **Status:** ready

### S-02: Add a tracked product

- **Outcome:** user can add a tracked product together with the two or three shop pages that carry its price
- **Change ID:** add-tracked-product
- **PRD refs:** FR-012
- **Prerequisites:** S-01
- **Parallel with:** F-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** The tracked list is the source of the shop pages the price record and the card read. It sits before the card so the north star has a product to open. Those pages come from Rossmann, DOZ, Super-Pharm, and Gemini, and this slice becomes plannable once sign-in is done.
- **Status:** proposed

### S-03: Product card with history and shop link

- **Outcome:** user can open a watched product, compare today's landed shop prices, read a 30-day history with one line per shop, and follow a link to that product in that shop
- **Change ID:** product-card-decision
- **PRD refs:** US-01, FR-003, FR-004, FR-005, FR-006
- **Prerequisites:** S-01, S-02, F-01
- **Parallel with:** S-04, S-05
- **Blockers:** —
- **Unknowns:** —
- **Risk:** This is the north star. It is as early as sign-in, a tracked product, and a recorded price allow. Today's prices and the chart read Rossmann, DOZ, Super-Pharm, and Gemini.
- **Status:** proposed

### S-04: Favorites with today's lowest price

- **Outcome:** user can see their favorite products, each with the lowest price recorded for that day
- **Change ID:** favorites-lowest-today
- **PRD refs:** US-01, FR-002
- **Prerequisites:** S-01, S-02, F-01
- **Parallel with:** S-03, S-05
- **Blockers:** —
- **Unknowns:**
  - Are the list owner's tracked products the preloaded favorites for that account? — Owner: user. Block: no.
  - Which timezone bounds the calendar day for "today"? — Owner: user. Block: no.
- **Risk:** Same data prerequisites as the card, sequenced just after it so the decision screen is not delayed by the list. The shop names do not block this slice; it shows one number for the day, not each shop page.
- **Status:** proposed

### S-05: Change or remove a tracked product

- **Outcome:** user can change or remove a tracked product and its shop pages
- **Change ID:** edit-tracked-product
- **PRD refs:** FR-013
- **Prerequisites:** S-02
- **Parallel with:** F-01, S-03, S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Changing and removing are required, but they are off the path that proves the buy decision, so they follow the card. They become plannable once a product can be added.
- **Status:** proposed

## Backlog Handoff

| Roadmap ID | Change ID                 | Suggested issue title                                              | Ready for `/10x-plan` | Notes                                      | Issue |
| ---------- | ------------------------- | ------------------------------------------------------------------ | --------------------- | ------------------------------------------ | ----- |
| F-01       | calendar-day-landed-price | Record one landed shop price per calendar day                     | yes                   | Run `/10x-plan calendar-day-landed-price`  | [#5](https://github.com/MartBur/Data-collector/issues/5) |
| S-01       | account-sign-in           | Signed-in user can sign in                                        | yes                   | Run `/10x-plan account-sign-in`            | [#6](https://github.com/MartBur/Data-collector/issues/6) |
| S-02       | add-tracked-product       | List owner can add a product with its shop pages                  | no                    | Waits on S-01. Shop set is named           | [#7](https://github.com/MartBur/Data-collector/issues/7) |
| S-03       | product-card-decision     | Open a product, compare today's prices and 30-day history, go to the shop | no          | Waits on S-01, S-02, and F-01. Shop set is named | [#8](https://github.com/MartBur/Data-collector/issues/8) |
| S-04       | favorites-lowest-today    | Start page shows each favorite's lowest price for that day        | no                    | Waits on S-01, S-02, and F-01              | [#9](https://github.com/MartBur/Data-collector/issues/9) |
| S-05       | edit-tracked-product      | List owner can change or remove a tracked product                 | no                    | Waits on S-02                              | [#10](https://github.com/MartBur/Data-collector/issues/10) |

## Open Roadmap Questions

1. **Which timezone bounds the calendar day for a price labeled today?** — Owner: user. Block: no. Planning may assume the owner's local day (Europe/Warsaw) until this is overridden. A previous calendar day must not be labeled today.

Settled 2026-09-23: the fixed shop set is Rossmann (https://www.rossmann.pl/), DOZ (https://www.doz.pl/), Super-Pharm (https://www.superpharm.pl/), and Gemini (https://gemini.pl/). Each tracked item still uses two or three pages from this set. Issue: [#11](https://github.com/MartBur/Data-collector/issues/11).

## Parked

- **USD exchange-rate or YouTube subscriber tracking** — Why parked: PRD Non-Goals; this version is restock prices for watched goods.
- **Arbitrary shop URLs per product** — Why parked: PRD Non-Goals; each item is two or three pages from Rossmann, DOZ, Super-Pharm, and Gemini.
- **Shared curation of the tracked list** — Why parked: PRD Non-Goals; only the list owner adds, changes, or removes entries (FR-012, FR-013).
- **Product description and availability on the card** — Why parked: PRD Non-Goals; the card is name, landed prices, chart, and outbound link.
- **Self-service favoriting from a product page (FR-009)** — Why parked: PRD Non-Goals and speed; the start page reads a preloaded list.
- **Chart horizon other than 30 days (FR-010)** — Why parked: PRD Non-Goals and speed; the 30-day chart is enough for the restock decision.
- **Anonymous browsing of all products (FR-011)** — Why parked: PRD Non-Goals and speed; the primary path is a logged-in owner.
- **Separate "worth buying now" signal (FR-007)** — Why parked: nice-to-have, cut to protect the speed goal; the card shows today's lowest landed price next to history and the user decides.
- **Production deploy, CI, and error tracking** — Why parked: speed; the restock decision can be proven locally. A deploy file already exists and is partial; finishing hosting is not required to plan the first slices.

## Milestone History

(none — this is the first milestone)

## Done

(none yet)
