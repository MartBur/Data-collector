# Calendar-day landed price Implementation Plan

## Overview

Record each tracked product's current selling price, after promo and without adding shipping, once per shop per Warsaw calendar day. The job runs without the user opening a shop, a later read the same day is stored only when the amount changes, and a price labeled today is only that day's latest stored amount.

## Current State Analysis

The Django project has no product, shop, or price models, no management commands, and no test modules. `INSTALLED_APPS` is contrib-only. `TIME_ZONE` is already `Europe/Warsaw` with `USE_TZ = True`. `render.yaml` is a web service plus Postgres and has no cron service. Routes are admin-only.

FR-008 requires an unattended daily record of each listed product's price in each applicable shop. The fixed shop set is Rossmann, DOZ, Super-Pharm, and Gemini. List screens, the product card, and the favorites page are later slices. This change creates the records those slices will read, and Django admin is how a product and its shop pages are entered until the owner screen exists.

## Desired End State

A product entered in admin has at most one page URL per shop, and that URL's host belongs to the chosen shop. A local command can record every shop, and a separate local command can record one shop. The first successful read on a Warsaw date stores the promo price. A later read that Warsaw date stores a new row only when the amount differs. The next Warsaw date stores a row even when the amount equals the previous date. A timeout or a page with no price is tried once more and then left as a gap, while successes from the same run stay stored. Asking for a shop's price on a date returns the latest amount stored for that date, or nothing when that date has no row. Yesterday's amount is never returned as today.

### Key Discoveries:

- `TIME_ZONE = 'Europe/Warsaw'` and `USE_TZ = True` at `DataCollector/settings.py` lines 129–133. The calendar date is `timezone.localdate()`, not a UTC date.
- No custom app, model, migration, management command, or test package exists. The new app is a sibling of `DataCollector/` and is added to `INSTALLED_APPS`.
- The automated test command is `uv run python manage.py test`. There is no mypy or Ruff gate.
- FR-008 at `context/foundation/prd.md` line 99 says the recorded price is after promo and shipping. This plan stores the promo price only, by the decision in Key Decisions of the brief.
- Production cron is parked. This change does not edit `render.yaml`.

## What We're NOT Doing

- Adding shipping to the stored amount.
- Owner-facing screens for adding, editing, or removing a tracked product.
- Sign-in screens, the product card, the history chart, and the favorites start page.
- A second page URL for the same shop on one product.
- Copying an earlier day's price into a day that has no row.
- Filling a Warsaw date on which the command did not run.
- Render cron or any edit to `render.yaml`.
- Live HTTP inside the automated test suite.
- Product description, availability, or shops outside Rossmann, DOZ, Super-Pharm, and Gemini.

## Implementation Approach

Add one Django app, `prices`, that owns the product, the shop page, and the price observations. Admin is the entry point for listings. A recording function applies the calendar-day rules. Four readers turn a saved product-page document into a promo price. One fetch helper tries a page, retries once when the read times out or yields no price, and then reports a gap. Five management commands call that helper: one for every shop page, and one each for Rossmann, DOZ, Super-Pharm, and Gemini. Automated tests use saved HTML and fake fetches. A live page is checked by hand.

## Critical Implementation Details

- Stamp the observation with the Warsaw calendar date of the run. A price taken just after midnight in Poland is that Polish date even when UTC is still the previous date.
- The same-day comparison uses the latest amount already stored for that shop page on that Warsaw date. An equal amount on the next Warsaw date is a new row. An equal amount later on the same date is not.
- A gap does not delete an earlier observation for that date. The amount reported for the date stays the latest row that was stored.

## Phase 1: Product, shop page, and observations

### Overview

Admin can create a product and one page per shop, and the database can store many price observations for that page.

### Changes Required:

#### 1. Prices app and models

**File**: `prices/models.py`

**Intent**: Give later slices one place to read a tracked product, its single page on each shop, and every stored price observation.

**Contract**: `Product` has a name. `ShopPage` belongs to one product, has a shop limited to Rossmann, DOZ, Super-Pharm, and Gemini, and has one absolute product-page URL. A product cannot have two pages for the same shop. The URL host must match the shop (`rossmann.pl`, `doz.pl`, `superpharm.pl`, or `gemini.pl`, with or without `www`). `PriceObservation` belongs to one shop page, stores a PLN amount with two decimal places, the Warsaw date of the run, and the time it was recorded. Many observations may exist for one page on one date. Register `prices` in `INSTALLED_APPS` and add nothing else to `DataCollector/settings.py`.

#### 2. Admin entry

**File**: `prices/admin.py`

**Intent**: Let the owner enter a product and its shop pages before the list screen exists, and reject a second page for a shop or a URL on the wrong host.

**Contract**: Product and shop page are editable in Django admin. Saving a shop page enforces the one-page-per-shop rule and the host rule. Price observations are visible in admin so a later manual run can be checked.

### Success Criteria:

#### Automated Verification:

- Migration applies: `uv run python manage.py migrate`
- Model tests pass: `uv run python manage.py test prices.tests.test_models`

#### Manual Verification:

- Admin accepts one page per shop and rejects a second page for the same shop
- Admin rejects a URL whose host does not match the chosen shop

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Calendar-day write rules

### Overview

The recording rules decide when a read becomes a row, and what amount is reported for a Warsaw date. No shop site is contacted in this phase.

### Changes Required:

#### 1. Recording rules

**File**: `prices/recording.py`

**Intent**: Keep today's label honest: a date the job ran has its own row, a repeat of the same amount that day does not add a row, and a changed amount does.

**Contract**: Given a shop page, a PLN amount, and a Warsaw date, the first observation for that page on that date is stored. A later call for the same page and date stores a new observation only when the amount differs from the latest stored amount for that page and date. The reported price for a page on a date is that latest amount, or no price when the date has no row. Callers pass the Warsaw date. The function does not read another date to fill a hole.

### Success Criteria:

#### Automated Verification:

- Recording tests pass and cover first-of-day insert, same-day unchanged skip, same-day change insert, latest-of-day read, and next-day insert of an equal amount: `uv run python manage.py test prices.tests.test_recording`

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Four shop readers

### Overview

Each shop has a reader that returns the current promo price from a saved product page. A page with no price returns no price. Shipping is not added.

### Changes Required:

#### 1. Readers and fixtures

**File**: `prices/readers.py`

**Intent**: Turn one saved product page from each shop into the amount the recording rules will store.

**Contract**: One reader per shop accepts HTML and returns a two-decimal PLN amount or no price. When the page shows a crossed-out price and a lower current price, the amount is the current price. Shipping text is ignored. A page with no selling price returns no price. Fixtures are saved product pages, one per shop, under `prices/tests/fixtures/`. Tests assert the promo amount for each fixture and assert no price for a fixture that has no selling price.

### Success Criteria:

#### Automated Verification:

- Reader tests pass for saved HTML of Rossmann, DOZ, Super-Pharm, and Gemini, including a page with no price: `uv run python manage.py test prices.tests.test_readers`

#### Manual Verification:

- A live page that no longer matches its saved HTML is checked by hand before the fixture is updated

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Local record commands

### Overview

One command records every shop page. Four more commands each record one shop. All five use the same fetch, retry, and calendar-day rules.

### Changes Required:

#### 1. Fetch and commands

**File**: `prices/management/commands/`

**Intent**: Run the daily record locally for every shop, or for one shop, without a screen and without Render cron.

**Contract**: `record_prices` visits every shop page. `record_rossmann_prices`, `record_doz_prices`, `record_superpharm_prices`, and `record_gemini_prices` each visit only that shop. For each page, fetch the live URL, read it with that shop's reader, and pass the amount to the Phase 2 rules together with today's Warsaw date. If the fetch times out or the reader returns no price, try that page once more. A second failure leaves no new row for that page and does not remove an earlier row for today. Other pages in the run are still recorded. The command prints, for each page, whether it stored an amount, skipped an unchanged amount, or left a gap. Command tests use a fake fetch and saved outcomes, not the network. Overlapping runs of the same page take the compare-and-insert in one database transaction.

### Success Criteria:

#### Automated Verification:

- Command tests pass without network: all-shops and one single-shop command store a changed price, skip an unchanged same-day price, and leave a gap after one failed retry: `uv run python manage.py test prices.tests.test_commands`

#### Manual Verification:

- Run `uv run python manage.py record_prices` for a product entered in admin and confirm today's amount is stored
- Run `uv run python manage.py record_rossmann_prices` and confirm other shops are untouched
- Run that shop command again while the price is unchanged and confirm no extra row

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Model tests cover one page per product per shop and rejection of a host that does not match the shop.
- Recording tests cover the five calendar cases named in Phase 2, including Tuesday storing 10.00 PLN when Monday's latest amount was also 10.00 PLN, and a later Tuesday read of 10.00 PLN adding no row.
- Reader tests cover the promo amount on each shop's saved page, a crossed-out higher price being ignored, and a page with no selling price.

### Integration Tests:

- Command tests call `record_prices` and `record_rossmann_prices` with a fake fetch. They assert a changed amount is stored, an unchanged same-day amount is skipped, a timeout then a second timeout leaves a gap, and a successful other shop in the same run is stored.

### Manual Testing Steps:

1. In admin, add a product with one Rossmann URL and one DOZ URL. Confirm a second Rossmann URL is rejected, and a DOZ host marked as Rossmann is rejected.
2. Run `uv run python manage.py record_prices`. Confirm admin shows today's promo amount for each page that loaded, and a gap where a page failed twice.
3. Run `uv run python manage.py record_rossmann_prices` again without a price change. Confirm the Rossmann observation count for today stays the same and DOZ is unchanged.
4. When a shop's live page no longer matches its fixture, update the fixture only after checking the live promo price by hand.

## Performance Considerations

The job reads a few product pages, one after another, with a single retry. No parallel fetching or cache is required for this change.

## Migration Notes

There is no existing price data. The Phase 1 migration creates the product, shop page, and observation tables. Later slices read these tables. They do not create a second product model.

## References

- Roadmap item F-01: `context/foundation/roadmap.md`
- FR-008 and the shop set: `context/foundation/prd.md`
- Warsaw timezone: `DataCollector/settings.py` lines 129–133
- No `research.md` or `frame.md` for this change

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Product, shop page, and observations

#### Automated

- [ ] 1.1 Migration applies: `uv run python manage.py migrate`
- [ ] 1.2 Model tests pass: `uv run python manage.py test prices.tests.test_models`

#### Manual

- [ ] 1.3 Admin accepts one page per shop and rejects a second page for the same shop
- [ ] 1.4 Admin rejects a URL whose host does not match the chosen shop

### Phase 2: Calendar-day write rules

#### Automated

- [ ] 2.1 Recording tests pass and cover first-of-day insert, same-day unchanged skip, same-day change insert, latest-of-day read, and next-day insert of an equal amount: `uv run python manage.py test prices.tests.test_recording`

### Phase 3: Four shop readers

#### Automated

- [ ] 3.1 Reader tests pass for saved HTML of Rossmann, DOZ, Super-Pharm, and Gemini, including a page with no price: `uv run python manage.py test prices.tests.test_readers`

#### Manual

- [ ] 3.2 A live page that no longer matches its saved HTML is checked by hand before the fixture is updated

### Phase 4: Local record commands

#### Automated

- [ ] 4.1 Command tests pass without network: all-shops and one single-shop command store a changed price, skip an unchanged same-day price, and leave a gap after one failed retry: `uv run python manage.py test prices.tests.test_commands`

#### Manual

- [ ] 4.2 Run `uv run python manage.py record_prices` for a product entered in admin and confirm today's amount is stored
- [ ] 4.3 Run `uv run python manage.py record_rossmann_prices` and confirm other shops are untouched
- [ ] 4.4 Run that shop command again while the price is unchanged and confirm no extra row
