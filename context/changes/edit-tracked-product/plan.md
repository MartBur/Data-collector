# Change or remove a tracked product — Implementation Plan

## Overview

A staff list owner can open a list of tracked products, add one with one to three shop pages, change its name and shop pages, and remove a shop page or the whole product. Recorded prices stay when a shop's URL is corrected, and they are deleted only with the shop page or the product, after a confirm step when any price would disappear.

## Current State Analysis

Sign-in and add are on `main`. The list owner is a signed-in `is_staff` user. `add_product` at `/products/add/` rejects anyone else with 403, and anonymous users are sent to login (`prices/views.py`). Home shows "Add a tracked product" only for staff (`accounts/templates/accounts/home.html`).

`AddProductForm` requires two shop rows and allows an optional third (`prices/forms.py`). A blank second row is rejected by `test_blank_second_row_stores_nothing`. The model allows one page or four; admin does not enforce a count (`prices/admin.py`). `Product.clean` and `ShopPage.clean` already ignore the row being edited, so a rename or a URL update can be validated without clashing with itself (`prices/models.py`).

`ShopPage` cascades from `Product`, and `PriceObservation` cascades from `ShopPage`. Deleting a page deletes its prices. Updating a page's `url` in place keeps those rows on the same primary key. Nothing in the owner UI edits or deletes a product today. There is no favorites model.

## Desired End State

A staff user follows "Tracked products" from home to `/products/`. The list shows every product name and its shops. Add accepts one, two, or three packed shop rows and rejects zero and a gap. Change opens a product, saves a new name and one to three shop pages, and returns to the list. Remove on a shop page deletes that page down to one remaining page. Remove on the last page leaves the product as it is. Remove on the product deletes it. When the action would delete at least one recorded price, a confirm page names the product and the shops and states that those prices will be deleted. A same-shop URL change keeps that page's prices and skips confirm.

### Key Discoveries:

- Staff gate and the add redirect live in `prices/views.py` (`add_product`, lines 41–65). Reuse that gate for the list, change, and remove.
- Price rows belong to `ShopPage` and cascade on delete (`prices/models.py`, lines 136–140). A same-shop URL correction has to update that row. Replacing the row deletes the prices.
- The add form's second row is required (`prices/forms.py`, lines 55–63). One-page add means those fields become optional and `clean` requires one to three packed rows.
- `test_blank_second_row_stores_nothing` (`prices/tests/test_add_product.py`, lines 121–123) locks the old two-page minimum. That payload becomes the valid one-page add.
- S-02 left admin able to store one or four pages (`context/archive/2026-10-10-add-tracked-product/plan-brief.md`). This plan does not change admin.

## What We're NOT Doing

- Favorites, today's lowest price, or the product card (S-03, S-04).
- A new user model, group, or list-owner flag. Staff remains the list owner.
- Tightening Django admin. Admin may still save one page or four.
- Soft delete, or keeping `PriceObservation` rows after their shop page is deleted.
- A confirm step when the action would delete zero prices.
- Typing the product name to confirm.
- Four shop pages, or zero shop pages, on the owner add and change forms.
- Arbitrary shop URLs, or shops outside Rossmann, DOZ, Super-Pharm, and Gemini.
- Moving the add success screen off `/products/add/?added=<pk>`.
- Description, availability, or shipping.

## Implementation Approach

Keep the work in the `prices` app and the staff check already used by add. Loosen the add form to one, two, or three packed rows, then reuse that row contract on change. The list is the entry point and the page change and remove return to. Match an edited shop to the existing `ShopPage` for that product and update its URL on that row. Delete a page only when its shop is absent from the submitted set, and create a page only for a shop that is new. Ask for confirmation only when a page about to be deleted has at least one `PriceObservation`. The list is small; sort it in Python by stripped casefolded name, then primary key.

## Critical Implementation Details

- **State sequencing** — On change, update a kept shop's URL on the existing `ShopPage` before any delete, inside one transaction that runs only after the confirm gate. Delete-all-and-recreate would drop prices on a same-shop URL change. Switching the only shop is allowed: the submitted set still has one page, the old page is deleted, and the new page is created in that same transaction. An empty submitted set is a validation error and writes nothing.

## Phase 1: Accept one shop page on add

### Overview

Add stores a product with one, two, or three shop pages. Zero pages, a half-filled row, and a gap still store nothing. Four pages still cannot be submitted through the three-row form.

### Changes Required:

#### 1. Add form row rules

**File**: `prices/forms.py`

**Intent**: Let the owner create a product that has a single shop page, which is now a valid product, while keeping the packed-row and host rules.

**Contract**: `shop_1`, `url_1`, `shop_2`, and `url_2` are optional at the field level, as `shop_3` and `url_3` already are. `clean` accepts one, two, or three filled rows packed from row 1. Zero filled rows add the error "Enter at least one shop page." on `shop_1` and save nothing. A half-filled row still errors. A filled row after an empty earlier row errors and saves nothing, including a filled third row with an empty second row. Distinct shops and `shop_url_host_is_valid` stay. `save` still creates no `PriceObservation` and still rolls back on `ValidationError`.

#### 2. Add tests

**File**: `prices/tests/test_add_product.py`

**Intent**: Lock the new one-page success and keep the gap and empty cases rejected.

**Contract**: Replace `test_blank_second_row_stores_nothing`: a staff POST with only row 1 filled creates one `Product`, one `ShopPage`, and zero `PriceObservation` rows, then redirects to `?added=<pk>`. A staff POST with no shop rows stores nothing and the form error is "Enter at least one shop page." A filled third row with an empty second row still stores nothing. Two-row and three-row posts still store those pages. Anonymous and non-staff behavior stays.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test prices.tests.test_add_product` passes
- A staff POST with only the first shop row filled creates one product, one shop page, and zero price observations
- A staff POST with no shop row stores nothing and reports "Enter at least one shop page."
- A staff POST with the third row filled and the second row empty stores nothing
- A staff POST with two filled rows, and a staff POST with three filled rows, still stores those pages
- A half-filled shop row stores nothing

#### Manual Verification:

- A staff user adds a product with one shop page and sees that name and page on the add confirmation
- A staff user submits Add with no shop page, sees "Enter at least one shop page.", and the product is absent from the database

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Staff product list

### Overview

Staff get a list of tracked products from home. Each row shows the product name and its shops. Change and Remove arrive in later phases.

### Changes Required:

#### 1. List view and route

**File**: `prices/views.py`

**File**: `prices/urls.py`

**Intent**: Give the owner one page that shows every tracked product before they can change or remove one.

**Contract**: `product_list(request: HttpRequest) -> HttpResponse` is login-required and raises `PermissionDenied` when `user.is_staff` is false. Route `prices:product_list` at `""` under the existing `products/` include, so the path is `/products/`. Load every `Product`. Sort in Python by `name.strip().casefold()`, then `pk`. For each product, shop pages are ordered by `pk` and shown with `get_shop_display()`. An empty list renders the sentence "No tracked products."

#### 2. Home link and template

**File**: `accounts/templates/accounts/home.html`

**File**: `prices/templates/prices/product_list.html`

**Intent**: Staff can open the list from the signed-in home page.

**Contract**: When `user.is_staff`, home shows a link with the text `Tracked products` and `href="/products/"`, in addition to the existing add link. Other signed-in users do not see that link. The list template shows each product name and each shop's display name. It does not show prices, a description, or availability.

#### 3. List tests

**File**: `prices/tests/test_product_list.py`

**Intent**: Lock who can open the list and the order of names.

**Contract**: Anonymous `GET /products/` redirects to login. Non-staff `GET` returns 403. Staff `GET` returns 200 and lists every product. Names sort by stripped casefold, with `pk` breaking a tie. Each product's shops appear in `pk` order. Staff home contains `Tracked products` and `href="/products/"`. Non-staff home does not.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test prices.tests.test_product_list` passes
- Anonymous GET `/products/` redirects to the login page
- Non-staff GET `/products/` returns 403
- Staff GET `/products/` lists every product by stripped casefolded name, then pk, each with its shop display names in pk order
- Staff home links to `/products/` with the text "Tracked products"; non-staff home does not

#### Manual Verification:

- A staff user opens home, follows "Tracked products", and sees each product name with its shops
- With no products, the list shows "No tracked products."

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Change a tracked product

### Overview

Staff can change a product's name and its one to three shop pages. A same-shop URL change keeps that page's prices. Dropping or switching a shop deletes that shop's prices, and asks first when any price would be deleted. The owner returns to the list.

### Changes Required:

#### 1. Change form

**File**: `prices/forms.py`

**Intent**: Reuse the one-to-three row rules for an existing product, and write shop pages so kept prices stay on the same row.

**Contract**: A change form is built from a `Product` and pre-fills rows from `shop_pages.order_by("pk")`. It uses the same packed one-to-three rules and the same messages as add. Saving a one-page product with a new name and the same shop URL succeeds. Clearing every row adds "Enter at least one shop page." and writes nothing. `save` runs in one `transaction.atomic()` after validation. For each filled row whose shop already has a `ShopPage` on this product, set that row's `url` on that existing page and call `full_clean`. Delete `ShopPage` rows whose shop is not in the filled set. Create a `ShopPage` for a filled shop that the product did not have. Model errors attach to `name` or that row's URL and roll the transaction back. A same-shop URL change keeps the page primary key and its `PriceObservation` rows.

#### 2. Change view, confirm, and route

**File**: `prices/views.py`

**File**: `prices/urls.py`

**File**: `prices/templates/prices/change_product.html`

**Intent**: Let staff save a correction, and stop a save that would delete prices until they confirm.

**Contract**: `change_product(request: HttpRequest, pk: int) -> HttpResponse` uses the same login and staff gate as add. Unknown `pk` returns 404. Route `prices:change_product` at `<int:pk>/change/`. When the product has more than three shop pages, GET and POST write nothing and the page tells the owner the product has more shops than this form can save. Otherwise GET renders the pre-filled form. A valid POST whose deleted pages include at least one `PriceObservation` writes nothing and renders a confirm step that includes the product name, each shop whose prices would be deleted, the exact sentence "recorded prices will be deleted", the submitted values as hidden fields, and a confirm control. Cancel links to `prices:product_list` and writes nothing. A valid POST with that confirm flag, or a valid POST that would delete zero prices, saves and redirects to `/products/`. A rename, or a same-shop URL change that drops no shop, saves with no confirm step. Switching the only shop is a normal save: the new set still has one page; confirm only when the old page has a price.

#### 3. Change tests

**File**: `prices/tests/test_change_product.py`

**Intent**: Lock price retention, the confirm gate, and the one-page save.

**Contract**: Cover the automated success criteria below. Non-staff POST returns 403. A missing product returns 404. Build prices with `PriceObservation` rows on the shop page under test.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test prices.tests.test_change_product` passes
- Replacing a shop page URL with another URL for the same shop keeps that page's primary key and its price observations
- Switching a shop that has prices writes nothing until confirm is posted, then deletes the old page's prices and leaves the new page with none
- A rename that keeps the same shops and URLs saves with no confirm step and keeps every price observation
- Clearing every shop row stores nothing
- A one-page product can be renamed and saved, and switching its only shop is allowed when the new set still has one page
- Change on a product with four shop pages writes nothing
- Non-staff POST returns 403, and a successful change redirects to `/products/`

#### Manual Verification:

- A staff user changes a same-shop URL, lands on the list, and that shop's recorded prices are still present
- A staff user switches a shop that has prices, sees the product name, the shop name, and "recorded prices will be deleted", and cancel leaves the stored pages unchanged

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Remove a page or the product

### Overview

From the list, staff can remove one shop page or the whole product. The last remaining page cannot be removed. Prices on a deleted page or product go with it, after confirm when any price exists. The list is updated on return.

### Changes Required:

#### 1. Remove actions

**File**: `prices/views.py`

**File**: `prices/urls.py`

**File**: `prices/templates/prices/product_list.html`

**Intent**: Put both remove actions where the owner already sees the product, and refuse to leave a product with no shop page.

**Contract**: The list shows `Change` linking to `prices:change_product`, a `Remove product` POST, and a `Remove` POST beside each shop. `remove_shop_page(request: HttpRequest, pk: int, page_pk: int) -> HttpResponse` and `remove_product(request: HttpRequest, pk: int) -> HttpResponse` accept POST only, use the staff gate, and return 404 when the page does not belong to that product. Routes: `<int:pk>/shop-pages/<int:page_pk>/remove/` named `prices:remove_shop_page`, and `<int:pk>/remove/` named `prices:remove_product`. Removing the product's only shop page deletes nothing and redirects to `/products/?kept=<pk>`. The list then shows "A tracked product must keep one shop page." and that product's page and prices are unchanged. Otherwise, when the pages to delete have at least one `PriceObservation`, the response writes nothing and shows a confirm page with the product name, each affected shop name, and the exact sentence "recorded prices will be deleted". Confirm is a POST of the same action. When those pages have zero prices, or confirm is posted, delete and redirect to `/products/`. Deleting a page deletes its prices through the existing cascade. Deleting the product deletes its pages and their prices. GET does not delete.

#### 2. Remove tests

**File**: `prices/tests/test_remove_product.py`

**Intent**: Lock the last-page rejection, the confirm gate, and the cascade.

**Contract**: Cover the automated success criteria below. A page primary key from another product returns 404 and deletes nothing. Non-staff POST returns 403.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test prices.tests.test_remove_product` passes
- Removing one page from a three-page product deletes that page and its prices, leaves the other pages, and redirects to `/products/`
- Removing a page that has no prices skips confirm and deletes the page
- Removing a page that has prices writes nothing until confirm is posted, and the confirm page includes the product name, the shop name, and "recorded prices will be deleted"
- Removing the only page leaves the product and its prices unchanged, redirects to `/products/?kept=<pk>`, and the list shows "A tracked product must keep one shop page."
- Removing the whole product deletes the product, its pages, and their prices, after confirm when any of those pages has a price
- Non-staff POST returns 403, and a shop page that belongs to another product returns 404 and deletes nothing

#### Manual Verification:

- A staff user removes one shop from a three-shop product and sees the other shops still on the list
- A staff user tries to remove the only shop and still sees that product with its page and the sentence "A tracked product must keep one shop page."
- A staff user removes a whole product and no longer sees it on the list

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Form `clean` for one packed row, zero rows, a gap, a half-filled row, a repeated shop, and a URL on the wrong host.
- `ShopPage` primary key stability when only `url` changes, and cascade when the page is deleted.

### Integration Tests:

- Staff, non-staff, and anonymous access for add, list, change, and both remove POSTs.
- Confirm versus immediate write, decided by whether a doomed page has a `PriceObservation`.
- Redirect targets: add stays on `?added=`, change and remove land on `/products/`.

### Manual Testing Steps:

1. Sign in as staff, add a product with only Rossmann, and read it back on the add confirmation.
2. Open Tracked products and change that Rossmann URL. Confirm the list shows the new URL.
3. Add DOZ on that product, record a price for DOZ, remove DOZ, and read the confirm sentence before the page disappears.
4. Try to remove the remaining Rossmann page and see the product stay.
5. Remove the product and see the list without it.
6. Sign in as a non-staff user and check that home has neither add nor the tracked-products link.

## Performance Considerations

The tracked list is the owner's own products, a small set in this version. Sorting by casefold in Python and rendering every shop page is enough. This plan adds no pagination, cache, or extra query layer.

## Migration Notes

No schema migration. Existing products stay. A product that already has one shop page can be opened in Change. A product that already has four shop pages appears on the list and can lose pages through Remove; Change writes nothing until three or fewer pages remain. Recorded prices stay on a page until that page, or its product, is deleted.

## References

- FR-013 and the list-owner rule: `context/foundation/prd.md`
- S-05 outcome: `context/foundation/roadmap.md`
- Add flow this plan extends: `context/archive/2026-10-10-add-tracked-product/plan.md`
- Staff gate: `prices/views.py`
- Cascade and edit-safe `clean`: `prices/models.py`
- Current two-page minimum: `prices/forms.py`, `prices/tests/test_add_product.py`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Accept one shop page on add

#### Automated

- [x] 1.1 `uv run python manage.py test prices.tests.test_add_product` passes
- [x] 1.2 A staff POST with only the first shop row filled creates one product, one shop page, and zero price observations
- [x] 1.3 A staff POST with no shop row stores nothing and reports "Enter at least one shop page."
- [x] 1.4 A staff POST with the third row filled and the second row empty stores nothing
- [x] 1.5 A staff POST with two filled rows, and a staff POST with three filled rows, still stores those pages
- [x] 1.6 A half-filled shop row stores nothing

#### Manual

- [ ] 1.7 A staff user adds a product with one shop page and sees that name and page on the add confirmation
- [ ] 1.8 A staff user submits Add with no shop page, sees "Enter at least one shop page.", and the product is absent from the database

### Phase 2: Staff product list

#### Automated

- [ ] 2.1 `uv run python manage.py test prices.tests.test_product_list` passes
- [ ] 2.2 Anonymous GET `/products/` redirects to the login page
- [ ] 2.3 Non-staff GET `/products/` returns 403
- [ ] 2.4 Staff GET `/products/` lists every product by stripped casefolded name, then pk, each with its shop display names in pk order
- [ ] 2.5 Staff home links to `/products/` with the text "Tracked products"; non-staff home does not

#### Manual

- [ ] 2.6 A staff user opens home, follows "Tracked products", and sees each product name with its shops
- [ ] 2.7 With no products, the list shows "No tracked products."

### Phase 3: Change a tracked product

#### Automated

- [ ] 3.1 `uv run python manage.py test prices.tests.test_change_product` passes
- [ ] 3.2 Replacing a shop page URL with another URL for the same shop keeps that page's primary key and its price observations
- [ ] 3.3 Switching a shop that has prices writes nothing until confirm is posted, then deletes the old page's prices and leaves the new page with none
- [ ] 3.4 A rename that keeps the same shops and URLs saves with no confirm step and keeps every price observation
- [ ] 3.5 Clearing every shop row stores nothing
- [ ] 3.6 A one-page product can be renamed and saved, and switching its only shop is allowed when the new set still has one page
- [ ] 3.7 Change on a product with four shop pages writes nothing
- [ ] 3.8 Non-staff POST returns 403, and a successful change redirects to `/products/`

#### Manual

- [ ] 3.9 A staff user changes a same-shop URL, lands on the list, and that shop's recorded prices are still present
- [ ] 3.10 A staff user switches a shop that has prices, sees the product name, the shop name, and "recorded prices will be deleted", and cancel leaves the stored pages unchanged

### Phase 4: Remove a page or the product

#### Automated

- [ ] 4.1 `uv run python manage.py test prices.tests.test_remove_product` passes
- [ ] 4.2 Removing one page from a three-page product deletes that page and its prices, leaves the other pages, and redirects to `/products/`
- [ ] 4.3 Removing a page that has no prices skips confirm and deletes the page
- [ ] 4.4 Removing a page that has prices writes nothing until confirm is posted, and the confirm page includes the product name, the shop name, and "recorded prices will be deleted"
- [ ] 4.5 Removing the only page leaves the product and its prices unchanged, redirects to `/products/?kept=<pk>`, and the list shows "A tracked product must keep one shop page."
- [ ] 4.6 Removing the whole product deletes the product, its pages, and their prices, after confirm when any of those pages has a price
- [ ] 4.7 Non-staff POST returns 403, and a shop page that belongs to another product returns 404 and deletes nothing

#### Manual

- [ ] 4.8 A staff user removes one shop from a three-shop product and sees the other shops still on the list
- [ ] 4.9 A staff user tries to remove the only shop and still sees that product with its page and the sentence "A tracked product must keep one shop page."
- [ ] 4.10 A staff user removes a whole product and no longer sees it on the list
