# Calendar-day landed price — Plan Brief

> Full plan: `context/changes/calendar-day-landed-price/plan.md`

## What & Why

A tracked product needs one current selling price per shop for each Warsaw calendar day, recorded without the user opening the shop. Later screens are false if yesterday is labeled today. This change stores those prices and the rules that decide which amount is today.

## Starting Point

The Django app has admin, sessions, and `TIME_ZONE = Europe/Warsaw`. It has no product models, no price tables, no management commands, and no shop readers. The shop set is Rossmann, DOZ, Super-Pharm, and Gemini. List screens and the product card are later slices.

## Desired End State

Admin holds each product and at most one page per shop. A local command records every page, and each shop has its own local command. The first successful read on a Warsaw date stores the promo price. A later read that same date stores another row only when the amount changes. The next date stores a row even when the amount is unchanged. The price reported for a date is the latest amount stored that date. A date with no row has no price, and yesterday is not returned in its place.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Listings in this change | Product and shop-page models, entered in Django admin | The daily job needs pages before the owner list screen exists |
| Shops fetched | Rossmann, DOZ, Super-Pharm, and Gemini | The named set is what later screens compare |
| Same Warsaw day | Store a new row only when the amount changes; the reported price is the latest stored amount | A repeat of 12.00 adds nothing, and a move from 10.00 to 12.00 keeps both |
| Next Warsaw day | Always store the first read, even when it equals yesterday | Tuesday's 10.00 stays Tuesday's row when Monday was also 10.00 |
| Page identity | One URL per shop per product; a second URL for that shop is rejected | One shop has one source, so each run is another read of the same page |
| Failed page | Retry once, then leave a gap; keep successes from the same run | A timeout or a page with no price does not wipe DOZ when DOZ returned 19.00 |
| Stored amount | Promo price only; shipping is not added | A 20.00 promo price with 9.99 shipping is stored as 20.00 |
| Missed day | No row and no backfill | Wednesday's 12.00 is not written onto Tuesday |
| Tests | Saved HTML in the suite; a live page is a manual check | The suite stays repeatable when a shop is down |
| Where it runs | Local commands only: one for all shops, one per shop | Render cron stays in a later deploy change |

## Scope

**In scope:**

- `prices` app, admin, and migrations
- Calendar-day insert rules and the latest-amount read
- Four HTML readers and saved fixtures
- `record_prices`, `record_rossmann_prices`, `record_doz_prices`, `record_superpharm_prices`, and `record_gemini_prices`

**Out of scope:**

- Shipping added to the amount
- Sign-in, list screens, product card, chart, and favorites page
- A second URL for the same shop
- Render cron and `render.yaml`
- Live HTTP in automated tests

## Architecture / Approach

Admin writes products and shop pages. The record commands fetch those URLs, retry once, and pass a promo price into the calendar-day rules. Those rules append an observation or skip it. A later screen asks for the latest observation on a Warsaw date and receives that amount or no price.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Product, shop page, and observations | Admin entry and the tables | A second URL for one shop slips through |
| 2. Calendar-day write rules | Insert, skip, and latest-of-day read | An unchanged Tuesday is skipped because it matches Monday |
| 3. Four shop readers | Promo price from saved HTML | A shop layout does not match the fixture |
| 4. Local record commands | All-shops command and one command per shop | A failed retry deletes an earlier price from today |

**Prerequisites:** The Django project, `Europe/Warsaw`, and the four shop names. Sign-in and the list screen are not required.

**Estimated effort:** About four sessions, one per phase.

## Open Risks & Assumptions

- Each shop's HTML will drift. The suite keeps passing until someone checks a live page and updates the fixture.
- The stored amount is the promo price, not promo plus shipping. Later slices must show this amount as today's price.
- A product page that hides the price behind a script or a block becomes a gap after one retry.
- Two URLs on the same shop for one product cannot both be tracked.

## Success Criteria (Summary)

- A product in admin has one page per shop, and the wrong host or a second page for that shop is rejected.
- Today's reported price is the latest amount stored for that Warsaw date, and a day that did not run has no price.
- `record_prices` and each single-shop command can be run locally, and an unchanged same-day rerun adds no row.
