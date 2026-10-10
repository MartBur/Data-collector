# Add a tracked product with two or three shop pages — Implementation Plan

## Overview

A staff user can add one tracked product together with the two or three shop pages that carry its price, see that product confirmed, and start another add. Other signed-in users cannot change the list. This is roadmap slice S-02 (FR-012). The price record and the later product card read these pages; this slice does not record a price or show one.

## Current State Analysis

`Product` stores only a name, and `ShopPage` stores one absolute URL per shop for that product. The shop is one of Rossmann, DOZ, Super-Pharm, or Gemini. The URL host must match the shop, with or without `www`. Nothing in the schema limits a product to two or three pages: one page per shop means at most four, and tests already save both a single page and all four.

There is no list-owner field. Any active user can sign in. The signed-in home page shows the username and sign-out. Creating a product today is Django admin, which requires staff. `prices/views.py` is an empty stub, and the project URLs do not include a prices route.

## Desired End State

A staff user opens an add page from home, enters a name and two or three shop pages, and submits. The product and those pages are stored, or nothing is stored. The page then shows the saved name and each saved shop page, and presents an empty form for another product. Refreshing that confirmation does not create a second product.

`Alpecin` is refused when ` alpecin ` is already stored. `https://rossmann.pl/Produkt/szampon/` is refused when another product already has `https://www.rossmann.pl/Produkt/szampon`. A non-staff user does not see the add link, and opening the add address returns 403.

### Key Discoveries:

- `Product.name` is a 255-character field with no uniqueness (`prices/models.py`). `ShopPage` is unique on `(product, shop)`, and `clean()` rejects a host that is not the shop's host via `canonical_host` (`prices/models.py`).
- Tests lock the schema at one page per shop, including all four shops and a single page (`prices/tests/test_models.py`). `objects.create()` does not call `clean()`, so the host rule runs only through `full_clean()` (admin and forms).
- The daily recorder loads every `ShopPage` and does not need a new hook when a page is added (`prices/management/recording_command.py`).
- Home is login-only and has no staff branch (`accounts/views.py`, `accounts/templates/accounts/home.html`). Templates already receive `user` from the auth context processor (`DataCollector/settings.py`).
- F-01 said later slices reuse these tables and do not create a second product model. S-01 left list-owner checks out of sign-in and left admin as the staff tool.

## What We're NOT Doing

- Changing or removing a tracked product or its shop pages (S-05, FR-013).
- The product card, today's prices, the 30-day chart, and the outbound shop link as a decision screen (S-03).
- Favorites or the lowest price for the day (S-04). Deciding whether the owner's products are that account's favorites stays on S-04.
- Recording a price, calling the shop readers, or running the daily command on add.
- A schema change that forbids one page or four pages. Admin keeps its current inline and can still save one or four pages.
- A database `LOWER(name)` unique index, a stored casefold column, or a data rewrite of existing names.
- A catalog of older products on the add page.
- A new user model, group, or list-owner flag. Staff (`is_staff`) is the list owner.
- Shops outside Rossmann, DOZ, Super-Pharm, and Gemini, or a URL whose host is not the chosen shop.
- Description, availability, or shipping on this screen.
- Guest access to the add page. An anonymous request still goes to sign-in.
- Deploy, CI, and error tracking.

## Implementation Approach

Keep the add flow in the `prices` app and link to it from home only when `user.is_staff`. Reuse `Product` and `ShopPage`. Put the name rule and the same-page rule on `clean()`, next to the existing host rule, so the add form and admin share them. Enforce "two or three" only on the add form, because the model and the current tests allow one page and four pages.

A successful submit redirects back to the add URL with the new product's id. The next GET shows that product and an unbound form. A failed submit renders the same page again with the submitted values and the errors, and writes nothing.

Annotate every new function, method, and attribute. Do not annotate `DataCollector/urls.py`. Views return `HttpResponse` or a subclass. Do not use `Any`.

## Critical Implementation Details

- **Name and page identity run in Python, on `clean()`.** Compare names with `strip().casefold()`. A database `LOWER()` index does not fold Polish letters the same way on SQLite and Postgres, so do not add one. Store the trimmed spelling the owner typed, not the casefolded key. Compare a shop page by shop, scheme (casefolded), `canonical_host`, path with one trailing slash removed, and the query string. Drop the fragment. `http` and `https` stay different. Query `a=1&b=2` and `b=2&a=1` stay different. Path letter case stays different. Only one trailing slash is removed, so `/p/1//` does not match `/p/1`. An empty path and `/` are the same. `objects.create()` still bypasses `clean()`, matching the host rule.
- **Save is one transaction, then a redirect.** Create the product and its pages inside `transaction.atomic()`. If any `full_clean()` fails, the product is not left behind. Redirect only after commit, to `/products/add/?added=<pk>`. Two browser tabs can both pass `clean()` before either commits; do not add a lock for that. A refresh is a GET and must not insert again.
- **The first two shop rows are required and the third is optional.** An empty third row means two pages. A third row with only a shop or only a URL is an error. Filling row 3 and leaving row 2 empty is an error. This is not "any two slots."

## Phase 1: Name and shop-page identity

### Overview

Refuse a second product with the same name, and refuse a second product that points at the same shop page. Do not change how many pages a product may store.

### Changes Required:

#### 1. Product name

**File**: `prices/models.py`

**Intent**: Keep the owner's spelling, without surrounding spaces, and refuse another product that would read as the same name.

**Contract**: `Product.clean()` strips surrounding whitespace on `name` and assigns that stripped value back to the instance so a later save stores it. Empty after strip is a `ValidationError` on `name`. Other products clash when their stripped `casefold()` names are equal, excluding the current `pk` so editing a product does not clash with itself. Internal spaces are not collapsed: `Alpecin  shampoo` and `Alpecin shampoo` are different. No new field and no migration.

#### 2. Shop-page identity

**File**: `prices/models.py`

**Intent**: One shop page belongs to one product, including when the owner drops `www` or a trailing slash.

**Contract**: Add a key function used by `ShopPage.clean()` after the existing host check. Return `None` when the URL has no host or no scheme, and skip the duplicate check in that case (the host check already reports a bad URL). Otherwise return this tuple:

```python
def shop_page_key(shop: str, url: str) -> tuple[str, str, str, str, str] | None:
    parsed = urlparse(url)
    host = canonical_host(url)
    if host is None or parsed.scheme == "":
        return None
    path = "/" if parsed.path == "" else parsed.path
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return (shop, parsed.scheme.casefold(), host, path, parsed.query)
```

`clean()` raises `ValidationError` on `url` when any other `ShopPage` row (exclude the current `pk`) has the same key. `https://www.rossmann.pl/Produkt/szampon` and `https://rossmann.pl/Produkt/szampon/` clash. The same path with a different query, or `http` versus `https`, does not. A difference only in the fragment does. Do not change `prices/admin.py`.

#### 3. Model tests

**File**: `prices/tests/test_models.py`

**Intent**: Lock the new rules and keep the existing one-page and four-page cases.

**Contract**: Extend `ShopPageModelTests` (or a sibling class on `Product`) so `full_clean()` covers: folded duplicate name ` alpecin ` against `Alpecin`; internal double space allowed; blank name rejected; the Rossmann `www` and trailing-slash pair rejected on the second product; a different query allowed; `http` versus `https` allowed; a fragment-only difference rejected. Existing tests that save four shops on one product, and tests that `objects.create()` a single page, stay as they are and pass.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test` passes
- `uv run python manage.py makemigrations --check --dry-run` reports no changes

#### Manual Verification:

- Admin refuses a second product whose name matches an existing one after trimming and case folding
- Admin refuses a second product's shop page when only www or a trailing slash differs
- Admin still saves a product with one shop page and a product with four shop pages

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Staff add screen

### Overview

Give the staff user a page that saves a product with two or three shop pages and confirms that save. Refuse everyone else.

### Changes Required:

#### 1. Add form

**File**: `prices/forms.py`

**Intent**: Collect the name and the shop pages, and refuse an incomplete set before any row is written.

**Contract**: A form with `name` plus shop and URL for rows 1, 2, and 3. Shop choices are `Shop.choices` only. Rows 1 and 2 are required. Row 3 is absent when both of its fields are empty. A half-filled row 3, or a filled row 3 with row 2 empty, is an error and saves nothing. Filled rows must use distinct shops. Each URL must pass `shop_url_host_is_valid` for its shop. `save()` runs in `transaction.atomic()`, `full_clean()`s the `Product` and each new `ShopPage`, and stores them. A model `ValidationError` is shown on `name` or on that row's URL. No `PriceObservation` is created and the collector is not called.

#### 2. Add view, template, and route

**File**: `prices/views.py`, `prices/urls.py`, `prices/templates/prices/add_product.html`, `DataCollector/urls.py`

**Intent**: Staff can submit the form, see the product they just saved, and refresh safely. Anyone else cannot use the page.

**Contract**: Mount `prices.urls` so the page is `/products/add/` with the name `prices:add_product`. Do not add type annotations in `DataCollector/urls.py`. The view is login-required: an anonymous request redirects to `/accounts/login/`. An authenticated non-staff user gets 403 (`PermissionDenied`) on GET and POST and writes nothing. Invalid POST returns 200 with the bound form and its errors. Valid POST redirects to `/products/add/?added=<pk>`. That GET shows the product's stored name and each page's shop label and URL, plus an unbound form. A missing or unknown `added` id shows only the empty form and does not 404. The template follows the minimal document in `accounts/templates/accounts/home.html`: a POST form, `{% csrf_token %}`, no new CSS framework. The confirmation lists only the product identified by `added`, not older products. Button label: `Add product`.

#### 3. Home link

**File**: `accounts/templates/accounts/home.html`

**Intent**: The staff user can reach the add page from the only screen they have after sign-in.

**Contract**: When `user.is_staff`, show a link to `prices:add_product` with the text `Add a tracked product`. Other signed-in users see the same home page as today, without that link. Do not change `accounts/views.py`.

#### 4. Screen tests

**File**: `prices/tests/test_add_product.py`

**Intent**: Prove the gate, the two-or-three rule, the confirmation redirect, and that a failed submit leaves no product.

**Contract**: Use `django.test.TestCase` and `get_user_model().objects.create_user`, the same way `accounts/tests/test_sign_in.py` does. Cover: anonymous GET redirects to sign-in; non-staff GET and POST return 403 and create no `Product`; staff GET returns 200; staff POST with two valid pages redirects to `?added=<pk>`, stores those two pages, the follow-up GET contains the name and both URLs, and the form in the response context is unbound; three valid pages store three; a blank second row stores nothing and returns 200; a half-filled third row stores nothing; the same shop on two rows stores nothing; a URL on the wrong host stores nothing; ` alpecin ` against an existing `Alpecin` returns 200, keeps the submitted name on the bound form, and does not add a product; the Rossmann `www` / trailing-slash pair against another product stores nothing; staff home contains `Add a tracked product` and non-staff home does not; the successful save creates no `PriceObservation`.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test prices.tests.test_add_product` passes
- `uv run python manage.py test` passes

#### Manual Verification:

- A staff user adds a product with two shop pages, sees that name and those pages, sees an empty form, and a refresh does not create a second product
- A non-staff user sees no add link on home and gets 403 at `/products/add/`
- A staff user who submits a folded duplicate name stays on the filled form and no second product is saved

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Name folding, blank names, and internal spaces, through `Product.full_clean()`.
- Shop-page key: `www`, one trailing slash, query string, scheme, and fragment, through `ShopPage.full_clean()`.
- Existing one-page and four-page cases stay green.

### Integration Tests:

- Anonymous, non-staff, and staff access to `/products/add/`.
- Successful save of two pages and of three pages, then the confirmation GET.
- Rejected submits (incomplete rows, duplicate shop, wrong host, folded name, same page) create no `Product` and no `PriceObservation`.
- Home link visibility for staff and non-staff.

### Manual Testing Steps:

1. Sign in as a staff user, open Add a tracked product, save a name with Rossmann and DOZ URLs, and confirm the name and both URLs. Refresh and confirm a second product was not created. The form is empty.
2. Sign in as a non-staff user. Home has no add link. Open `/products/add/` and confirm 403.
3. As staff, submit a name that matches an existing product except for case or surrounding spaces. The form still shows what was typed, and the product count does not increase.
4. As staff, in admin, save a product with one shop page and another with four. Both save. A second product that reuses a page with only `www` or a trailing slash removed does not save.

## Performance Considerations

One staff user and a small product table. The name check loads existing names and folds them in Python. No cache and no extra index.

## Migration Notes

No schema migration. Existing rows are not rewritten. A product that already has one shop page, or four, stays valid. The new checks run on `full_clean()`, as the host check already does. A local database that already contains two names that fold together will fail the next admin save of either row; it does not fail migrate.

## References

- PRD FR-012 and the list-owner rule: `context/foundation/prd.md`
- Roadmap S-02: `context/foundation/roadmap.md`
- Product and shop-page rules: `prices/models.py`
- Page count locked by tests: `prices/tests/test_models.py`
- Sign-in client pattern: `accounts/tests/test_sign_in.py`
- F-01 decision that later slices reuse these tables: `context/archive/2026-09-23-calendar-day-landed-price/plan.md`
- No `research.md` or `frame.md` for this change

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Name and shop-page identity

#### Automated

- [x] 1.1 `uv run python manage.py test` passes
- [x] 1.2 `uv run python manage.py makemigrations --check --dry-run` reports no changes

#### Manual

- [x] 1.3 Admin refuses a second product whose name matches an existing one after trimming and case folding
- [x] 1.4 Admin refuses a second product's shop page when only www or a trailing slash differs
- [x] 1.5 Admin still saves a product with one shop page and a product with four shop pages

### Phase 2: Staff add screen

#### Automated

- [ ] 2.1 `uv run python manage.py test prices.tests.test_add_product` passes
- [ ] 2.2 `uv run python manage.py test` passes

#### Manual

- [ ] 2.3 A staff user adds a product with two shop pages, sees that name and those pages, sees an empty form, and a refresh does not create a second product
- [ ] 2.4 A non-staff user sees no add link on home and gets 403 at `/products/add/`
- [ ] 2.5 A staff user who submits a folded duplicate name stays on the filled form and no second product is saved
