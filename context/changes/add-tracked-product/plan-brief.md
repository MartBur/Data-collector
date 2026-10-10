# Add a tracked product with two or three shop pages — Plan Brief

> Full plan: `context/changes/add-tracked-product/plan.md`

## What & Why

The list owner needs to add a watched product and the two or three shop pages its price comes from. Those pages are what the daily price record and the later product card read. Sign-in exists, and the product tables exist, but the only way to create a product today is Django admin.

## Starting Point

`Product` is a name. `ShopPage` is one URL for one of Rossmann, DOZ, Super-Pharm, or Gemini, and the host must match the shop. The database allows one page per shop, so a product can have from one to four pages. Home after sign-in shows the username and sign-out. Any active user can sign in. Nothing in code marks a list owner.

## Desired End State

A staff user opens Add a tracked product, enters a name and two or three shop pages, and sees that product confirmed, with an empty form ready for another. Refreshing the confirmation does not save a duplicate. A name that matches an existing one after trimming and ignoring case is refused, and the typed values stay on the form. The same shop page is refused when the only difference is `www` or a trailing slash: `https://rossmann.pl/Produkt/szampon/` clashes with `https://www.rossmann.pl/Produkt/szampon`. A non-staff user has no add link and receives 403 at `/products/add/`.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| List owner | Signed-in `is_staff` user | The PRD allows one privileged account, and staff is the privilege Django admin already uses. |
| After a successful add | Confirm that product only, then an empty form | The slice proves the add; the card, the favorites list, and edit come later. |
| Duplicate name | Refuse after trim and Unicode casefold | Later screens identify a product by name, and this slice cannot rename one. |
| Same shop page | Refuse the same shop and path, ignoring `www` and one trailing slash | One page must not be tracked twice because of spelling; scheme and query still count, and a fragment does not. |
| Two or three pages | Add form only, not a schema rule | Current tests and admin already allow one page and all four shops. |
| Where it lives | `/products/add/` in the prices app, link on home for staff | The models live in `prices`; home is the only signed-in screen. |

## Scope

**In scope:**

- Staff-only add of a product with two required shop rows and an optional third
- Shared name and same-page checks on `clean()`, so admin applies them too
- Confirmation of the product just saved, via redirect, so refresh is safe
- Tests for the rules and the screen

**Out of scope:**

- Edit or remove (S-05)
- Product card, today's prices, chart, and shop link (S-03)
- Favorites and today's lowest price (S-04)
- Recording a price on add
- Forcing admin to use two or three pages
- A list of older products on the add page

## Architecture / Approach

The form saves one `Product` and two or three `ShopPage` rows in a single transaction, using the existing host check plus the new name and page-identity checks. Success redirects to `/products/add/?added=<pk>`. Failure re-renders the filled form and writes nothing. The daily recorder already reads `ShopPage` and does not change.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Name and shop-page identity | Duplicate names and the same shop page are refused, with no migration | A `clean()` change could reject a case the current tests allow |
| 2. Staff add screen | Staff can add two or three pages and see that product confirmed | The form could save a product before a page fails validation |

**Prerequisites:** Sign-in and the `Product` / `ShopPage` models are in place. Manual checks need a staff user and a second, non-staff user.
**Estimated effort:** About two sessions, one per phase.

## Open Risks & Assumptions

- Admin can still save one shop page or four. This slice does not tighten that. A mistaken URL stays until admin or S-05 removes it.
- `http` and `https`, and a different query string, count as different pages. Two fast submits from two tabs can both pass the check; refresh cannot.
- Name comparison is Unicode casefold in Python. The stored name keeps the owner's capitals. Only surrounding spaces are removed, so an internal double space is a different name.
- Whether the owner's tracked products are that account's favorites is still an S-04 question. This slice does not create favorites.

## Success Criteria (Summary)

- A staff user can add a product with two or three shop pages from the fixed shop set and see that product confirmed.
- A second product with the same folded name, or the same shop page, is refused and nothing is saved.
- A non-staff user cannot add, and no price is recorded by the add itself.
