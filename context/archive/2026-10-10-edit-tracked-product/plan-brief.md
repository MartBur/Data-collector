# Change or remove a tracked product — Plan Brief

> Full plan: `context/changes/edit-tracked-product/plan.md`

## What & Why

The list owner can change or remove a tracked product and its shop pages (FR-013). Add already stores a product, and a mistaken shop URL stays until this slice can change or remove it. Recorded prices are the point of the list, so a corrected link keeps them and a removed shop takes them away.

## Starting Point

Staff (`is_staff`) can add a product with two or three shop pages at `/products/add/`. Home links there only for staff. Prices cascade from the shop page. Nothing in the owner UI edits or deletes a product, and the add form rejects a one-page submit.

## Desired End State

Staff open Tracked products from home, see each name and its shops, and return there after a change or a remove. Add and Change accept one, two, or three shop pages. Remove can drop a shop page until one remains, or delete the whole product. A same-shop URL change keeps that page's prices. An action that would delete prices names the product and the shop and states that those prices will be deleted before it writes.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| List owner | Signed-in `is_staff` | S-02 already uses staff as the one privileged account. |
| Change | Name, URLs, and the shop set, up to three shops | The owner can correct a name, a link, or which shops are tracked. |
| Remove | One shop page, or the whole product | A three-shop product can lose one shop, and the product can also be cleared. |
| Minimum | One shop page may exist; the last page cannot be removed from the row | A product does not need a second page, and the row control must not leave zero. |
| Add | Accepts one, two, or three pages | The one-page rule applies when the product is created, not only afterward. |
| History | Same-shop URL change keeps prices; deleting a page or product deletes that page's prices | A corrected link keeps the chart; a removed shop does not leave prices behind. |
| Confirm | Only when at least one recorded price would be deleted | The warning appears when history would disappear, and a page with no prices is removed immediately. |
| Entry and landing | Staff list linked from home; change and remove return to it | The owner can find every product and see the result on the next screen. |
| Four shop pages | Change writes nothing | The form has three rows and must not drop a fourth page's prices. |
| Admin | Unchanged | S-02 left admin able to save one page or four. |

## Scope

**In scope:**

- One-to-three shop pages on add and on change
- Staff list of names and shops, linked from home
- Change, including in-place URL update and confirm before a price-deleting shop change
- Remove one page, reject removing the last page, and remove the whole product

**Out of scope:**

- Favorites and the product card
- Admin validation, soft delete, and keeping prices after a page is deleted
- Confirm when zero prices would be deleted
- Four shop pages or zero shop pages on the owner forms

## Architecture / Approach

The `prices` app keeps the staff gate from add. The list is `/products/`. Change matches each submitted shop to the existing `ShopPage` and updates that row's URL so prices stay; shops that disappeared are deleted, which cascades their prices. Confirm runs before that transaction, and only when a doomed page has a price observation.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Accept one shop page on add | Add stores one, two, or three pages | The old test expects a blank second row to fail |
| 2. Staff product list | Home links staff to a name-and-shop list | Sort has to follow casefold, not database collation |
| 3. Change a tracked product | Rename and shop edits, prices kept on a same-shop URL change | Rebuilding shop rows would wipe prices the owner chose to keep |
| 4. Remove a page or the product | Page remove, last-page rejection, product remove | The last page must stay even when it has prices |

**Prerequisites:** S-02 is done, and a staff account can sign in.
**Estimated effort:** About 2–3 sessions across 4 phases.

## Open Risks & Assumptions

- Replacing a URL on the same shop keeps the old prices even when the new URL is a different product. Dropping those prices means removing the page.
- Admin can still store four shop pages. Change refuses that product until Remove brings it to three or fewer.
- Add still finishes on its own confirmation screen. Only change and remove return to the list.

## Success Criteria (Summary)

- A staff user adds a one-shop product, sees it on the list, renames it, and corrects that shop's URL without losing its prices.
- Removing one shop from a three-shop product asks first when that shop has prices, then leaves the other shops.
- Removing the only shop leaves the product in place; removing the product takes the product and its prices off the list.
